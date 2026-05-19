"""
绿联影视客户端 - 完整实现。

对标 moviepilot 的绿联影视模块，适配 mediaflow/nastool 架构。

功能：
- RSA + AES-GCM 双层加密通信
- 会话持久化与自动重连
- 媒体库列表获取
- 媒体搜索与详情查询
- 媒体库刷新（支持按项目精确刷新）
- 继续观看、最近更新
- 图片代理（解决 scraper.ugnas.com 签名过期问题）
- BFS 目录遍历获取媒体库所有项目
"""

import hashlib
from collections import deque
from datetime import datetime
from typing import Any, Dict, Generator, List, Mapping, Optional, Union
from urllib.parse import parse_qs, urlparse

import log
from app.mediaserver.client._base import _IMediaClient
from app.mediaserver.client.ugreen_api import UgreenApi
from app.utils import ExceptionUtils, IpUtils
from app.utils.types import MediaType, MediaServerType
from config import Config


class Ugreen(_IMediaClient):
    """
    绿联影视客户端（完整实现）。

    对标 moviepilot 的 Ugreen 模块，使用 RSA+AES-GCM 加密通信，
    支持会话持久化、自动重连、媒体库完整管理。
    """

    # 媒体服务器ID
    client_id = "ugreen"
    # 媒体服务器类型
    client_type = MediaServerType.UGREEN
    # 媒体服务器名称
    client_name = MediaServerType.UGREEN.value

    # 媒体库目录分页上限（防止固件分页异常导致无限循环）
    LIBRARY_PATH_PAGE_LIMIT = 200
    # BFS 遍历路径上限
    MAX_PATH_VISITS = 20000

    def __init__(self, config=None):
        if config:
            self._client_config = config
        else:
            self._client_config = Config().get_config('ugreen')
        self.init_config()

    def init_config(self):
        """初始化配置并建立连接"""
        if not self._client_config:
            return

        self._host = self._client_config.get('host')
        if self._host:
            if not self._host.startswith('http'):
                self._host = "https://" + self._host
            self._host = self._host.rstrip("/")

        self._play_host = self._client_config.get('play_host')
        if self._play_host:
            if not self._play_host.startswith('http'):
                self._play_host = "https://" + self._play_host
            self._play_host = self._play_host.rstrip("/")

        self._username = self._client_config.get('username')
        self._password = self._client_config.get('password')

        # 扫描模式：1 新添加和修改、2 补充缺失、3 覆盖扫描
        self._scan_type = self._resolve_scan_type(
            self._client_config.get('scan_mode'),
            self._client_config.get('scan_type')
        )

        # SSL 证书校验
        self._verify_ssl = self._resolve_verify_ssl(
            self._client_config.get('verify_ssl', True)
        )

        # 同步媒体库列表
        self._sync_libraries = self._client_config.get('sync_libraries') or []

        # 内部状态
        self._api: Optional[UgreenApi] = None
        self._userinfo: Optional[dict] = None
        self._libraries: Dict[str, dict] = {}
        self._library_paths: Dict[str, str] = {}

        # 尝试连接
        if self._host and self._username and self._password:
            if not self.reconnect():
                log.error(f"【{self.client_name}】连接失败，请检查服务端地址 {self._host}")

    # ==================== 连接管理 ====================

    def is_configured(self) -> bool:
        """是否已配置"""
        return bool(self._host and self._username and self._password)

    def is_authenticated(self) -> bool:
        """是否已认证"""
        return (
            self.is_configured()
            and self._api is not None
            and self._api.token is not None
            and self._userinfo is not None
        )

    def is_inactive(self) -> bool:
        """检查会话是否已失效"""
        if not self.is_authenticated():
            return True
        try:
            self._userinfo = self._api.current_user() if self._api else None
        except Exception:
            self._userinfo = None
        return self._userinfo is None

    def __session_cache_key(self) -> str:
        """生成会话缓存键（基于 host + username）"""
        normalized_host = (self._host or "").strip().lower().rstrip("/")
        username = (self._username or "").strip().lower()
        raw = f"{normalized_host}|{username}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def __password_digest(self) -> str:
        """密码摘要（用于检测配置变更）"""
        return hashlib.sha256((self._password or "").encode("utf-8")).hexdigest()

    def __save_persisted_session(self):
        """持久化会话到系统配置"""
        if not self._api:
            return
        session_state = self._api.export_session_state()
        if not session_state:
            return
        try:
            from mediaflow.conf.systemconfig import SystemConfig
            from app.utils.types import SystemConfigKey
            sys_config = SystemConfig()
            cache_key = self.__session_cache_key()
            # 获取现有缓存
            existing = sys_config.get(SystemConfigKey.UgreenSessionCache) or {}
            if not isinstance(existing, dict):
                existing = {}
            existing[cache_key] = {
                **session_state,
                "host": self._host,
                "username": self._username,
                "password_digest": self.__password_digest(),
                "updated_at": int(datetime.now().timestamp()),
            }
            sys_config.set(SystemConfigKey.UgreenSessionCache, existing)
        except Exception as e:
            log.debug(f"【{self.client_name}】持久化会话失败（非致命）：{str(e)}")

    def __restore_persisted_session(self) -> bool:
        """从系统配置恢复会话"""
        try:
            from app.helper import SystemConfig
            from app.utils.types import SystemConfigKey
            sys_config = SystemConfig()
            sessions = sys_config.get(SystemConfigKey.UgreenSessionCache)
            if not isinstance(sessions, dict):
                return False

            cache_key = self.__session_cache_key()
            cached = sessions.get(cache_key)
            if not isinstance(cached, Mapping):
                return False

            # 密码变更后不复用旧会话
            if cached.get("password_digest") != self.__password_digest():
                log.info(f"【{self.client_name}】检测到密码变更，清理旧会话缓存")
                sessions.pop(cache_key, None)
                sys_config.set(SystemConfigKey.UgreenSessionCache, sessions)
                return False

            api = UgreenApi(host=self._host, verify_ssl=self._verify_ssl)
            if not api.import_session_state(cached):
                api.close()
                return False

            userinfo = api.current_user()
            if not userinfo:
                api.close()
                sessions.pop(cache_key, None)
                sys_config.set(SystemConfigKey.UgreenSessionCache, sessions)
                log.info(f"【{self.client_name}】持久化会话已失效，准备重新登录")
                return False

            self._api = api
            self._userinfo = userinfo
            log.debug(f"【{self.client_name}】已复用持久化会话")
            return True
        except Exception as e:
            log.debug(f"【{self.client_name}】恢复会话失败（非致命）：{str(e)}")
            return False

    def reconnect(self) -> bool:
        """重新连接绿联影视"""
        if not self.is_configured():
            return False

        self._libraries = {}
        self._library_paths = {}

        # 关闭旧连接（不主动登出，避免破坏可复用会话）
        if self._api:
            self._api.close()
            self._api = None
            self._userinfo = None

        # 优先尝试恢复持久化会话
        if self.__restore_persisted_session():
            return True

        # 正常登录
        self._api = UgreenApi(host=self._host, verify_ssl=self._verify_ssl)
        if self._api.login(self._username, self._password) is None:
            return False

        self._userinfo = self._api.current_user()
        if not self._userinfo:
            return False

        # 登录成功后持久化会话
        self.__save_persisted_session()
        log.debug(f"【{self.client_name}】{self._username} 成功登录")
        return True

    def disconnect(self, logout: bool = False):
        """断开连接"""
        if self._api:
            if logout:
                self._api.logout()
            self._api.close()
            self._api = None
            self._userinfo = None
        self._libraries = {}
        self._library_paths = {}

    # ==================== 辅助方法 ====================

    @staticmethod
    def _resolve_scan_type(scan_mode=None, scan_type=None) -> int:
        """解析扫描模式"""
        for value in (scan_type, scan_mode):
            try:
                parsed = int(value)
                if parsed in (1, 2, 3):
                    return parsed
            except Exception:
                pass
        mode = str(scan_mode or "").strip().lower()
        mode_map = {
            "new_and_modified": 1, "new_modified": 1, "add": 1,
            "new": 1, "scan_new_modified": 1,
            "supplement_missing": 2, "supplement": 2,
            "additional": 2, "missing": 2,
            "full_override": 3, "override": 3,
            "cover": 3, "replace": 3,
        }
        return mode_map.get(mode, 2)

    @staticmethod
    def _resolve_verify_ssl(verify_ssl) -> bool:
        """解析 SSL 校验配置"""
        if isinstance(verify_ssl, bool):
            return verify_ssl
        if verify_ssl is None:
            return True
        value = str(verify_ssl).strip().lower()
        if value in {"0", "false", "no", "off"}:
            return False
        return True

    @staticmethod
    def _normalize_dir_path(path) -> str:
        """标准化目录路径"""
        if path is None:
            return ""
        return str(path).replace("\\", "/").rstrip("/")

    @staticmethod
    def _is_subpath(path, parent) -> bool:
        """判断 path 是否是 parent 的子路径"""
        path_str = Ugreen._normalize_dir_path(path)
        parent_str = Ugreen._normalize_dir_path(parent)
        if not path_str or not parent_str:
            return False
        return path_str == parent_str or path_str.startswith(parent_str + "/")

    def __build_image_stream_url(self, source_url: str, size: int = 1) -> Optional[str]:
        """通过绿联 getImaStream 中转图片，规避 scraper.ugnas.com 403"""
        if not self._api:
            return None
        auth_token = self._api.static_token or self._api.token
        if not auth_token:
            return None
        params = {"app_name": "web", "name": source_url, "size": size}
        if self._api.is_ugk:
            params["ugk"] = auth_token
        else:
            params["token"] = auth_token
        return f"{self._api.host}/ugreen/v2/video/getImaStream?app_name=web&name={source_url}&size={size}&{'ugk' if self._api.is_ugk else 'token'}={auth_token}"

    def __resolve_image(self, path: Optional[str]) -> Optional[str]:
        """解析图片 URL（处理绿联特殊图片路径）"""
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            parsed = urlparse(path)
            if parsed.netloc.lower() == "scraper.ugnas.com":
                # scraper 链接优先改为本机 getImaStream
                stream_url = self.__build_image_stream_url(path)
                if stream_url:
                    return stream_url
            # 检查签名是否过期
            if self.__is_expired_signed_image(path):
                return None
            return path
        # 本地图片路径需要额外鉴权头，暂不支持
        return None

    @staticmethod
    def __is_expired_signed_image(url: str) -> bool:
        """判断绿联 scraper 签名图是否已过期"""
        try:
            parsed = urlparse(url)
            if parsed.netloc.lower() != "scraper.ugnas.com":
                return False
            auth_key = parse_qs(parsed.query).get("auth_key", [None])[0]
            if not auth_key:
                return False
            expire_part = str(auth_key).split("-", 1)[0]
            expire_ts = int(expire_part)
            now_ts = int(datetime.now().timestamp())
            return expire_ts <= now_ts
        except Exception:
            return False

    @staticmethod
    def __parse_year(video_info: dict) -> Optional[Union[str, int]]:
        """从视频信息中提取年份"""
        year = video_info.get("year")
        if isinstance(year, int) and year > 0:
            return year
        release_date = video_info.get("release_date")
        if isinstance(release_date, (int, float)) and release_date > 0:
            try:
                return datetime.fromtimestamp(release_date).year
            except Exception:
                return None
        return None

    @staticmethod
    def __map_item_type(video_type: Any) -> Optional[str]:
        """映射绿联视频类型到媒体服务器类型"""
        type_map = {2: "Series", 1: "Movie", 3: "Collection", 0: "Folder"}
        return type_map.get(video_type, "Video")

    def __is_library_blocked(self, library_id: str) -> bool:
        """检查媒体库是否被同步过滤排除"""
        if not self._sync_libraries or "all" in self._sync_libraries:
            return False
        return str(library_id) not in self._sync_libraries

    @staticmethod
    def __infer_library_type(name: str, path: Optional[str]) -> str:
        """根据名称和路径推断媒体库类型"""
        name = name or ""
        path = path or ""
        if "电视剧" in path or any(key in name for key in ["剧", "综艺", "动漫", "纪录片"]):
            return MediaType.TV.value
        if "电影" in path or "电影" in name:
            return MediaType.MOVIE.value
        return MediaType.UNKNOWN.value

    def __build_root_url(self) -> str:
        """统一返回 NAS Web 根地址作为跳转链接"""
        host = self._play_host or (self._api.host if self._api else "")
        if not host:
            return ""
        return f"{host.rstrip('/')}/"

    def __scan_library(self, library_id: str, scan_type: Optional[int] = None) -> bool:
        """扫描指定媒体库"""
        if not self._api:
            return False
        return self._api.scan(
            media_lib_set_id=library_id,
            scan_type=scan_type or self._scan_type,
            op_type=2,
        )

    def __load_library_paths(self) -> dict:
        """加载所有媒体库目录路径"""
        if not self._api:
            return {}
        paths = {}
        page = 1
        while page <= self.LIBRARY_PATH_PAGE_LIMIT:
            data = self._api.poster_wall_get_folder(page=page, page_size=100)
            if not data:
                break
            for folder in data.get("folder_arr") or []:
                lib_id = folder.get("media_lib_set_id")
                lib_path = folder.get("path")
                if lib_id is not None and lib_path:
                    paths[str(lib_id)] = str(lib_path)
            if data.get("is_last_page"):
                break
            page += 1
        return paths

    @staticmethod
    def __extract_video_info_list(bucket: Any) -> list:
        """从搜索结果中提取视频信息列表"""
        if not isinstance(bucket, Mapping):
            return []
        video_arr = bucket.get("video_arr")
        if not isinstance(video_arr, list):
            return []
        result = []
        for item in video_arr:
            if not isinstance(item, Mapping):
                continue
            info = item.get("video_info")
            if isinstance(info, Mapping):
                result.append(dict(info))
        return result

    def __search_tv_item(self, title: str, year=None, tmdb_id=None) -> Optional[dict]:
        """搜索电视剧项目"""
        if not self._api:
            return None
        data = self._api.search(title)
        if not data:
            return None
        for info in self.__extract_video_info_list(data.get("tv_list")):
            if tmdb_id and tmdb_id != info.get("tmdb_id"):
                continue
            if title not in [info.get("name"), info.get("original_name")]:
                continue
            item_year = info.get("year")
            if year and str(item_year) != str(year):
                continue
            return info
        return None

    def _iter_library_videos(self, root_path: str, page_size: int = 100):
        """BFS 遍历媒体库目录获取所有视频"""
        if not self._api or not root_path:
            return
        queue = deque([root_path])
        visited = set()

        while queue and len(visited) < self.MAX_PATH_VISITS:
            current_path = queue.popleft()
            if current_path in visited:
                continue
            visited.add(current_path)

            page = 1
            while True:
                data = self._api.poster_wall_get_folder(
                    path=current_path,
                    page=page,
                    page_size=page_size,
                    sort_type=1,
                    order_type=1,
                )
                if not data:
                    break
                for video in data.get("video_arr") or []:
                    if isinstance(video, dict):
                        yield video
                for folder in data.get("folder_arr") or []:
                    if not isinstance(folder, dict):
                        continue
                    sub_path = folder.get("path")
                    if sub_path and sub_path not in visited:
                        queue.append(str(sub_path))
                if data.get("is_last_page"):
                    break
                page += 1

    def __match_library_id_by_path(self, path) -> Optional[str]:
        """根据路径匹配媒体库 ID"""
        if path is None:
            return None
        path_str = self._normalize_dir_path(path)
        if not self._library_paths:
            self.get_libraries()
        for lib_id, lib_path in self._library_paths.items():
            if self._is_subpath(path_str, lib_path):
                return lib_id
        return None

    # ==================== 基类接口实现 ====================

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.client_id, cls.client_type, cls.client_name] else False

    def get_type(self):
        return self.client_type

    def get_status(self):
        """测试连通性"""
        if not self.is_authenticated():
            if not self.reconnect():
                return False
        return self.is_authenticated()

    def get_user_count(self):
        """获得用户数量"""
        if not self.is_authenticated() or not self._api:
            return 0
        users = self._api.media_lib_users()
        return len(users)

    def get_activity_log(self, num):
        """获取活动记录（绿联暂不支持）"""
        return []

    def get_medias_count(self):
        """获得电影、电视剧媒体数量"""
        if not self.is_authenticated() or not self._api:
            return {}
        try:
            movie_data = self._api.video_all(classification=-102, page=1, page_size=1) or {}
            tv_data = self._api.video_all(classification=-103, page=1, page_size=1) or {}
            return {
                "MovieCount": int(movie_data.get("total_num") or 0),
                "SeriesCount": int(tv_data.get("total_num") or 0),
                "SongCount": 0,
            }
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取媒体数量出错：{str(e)}")
            return {}

    def get_movies(self, title, year=None):
        """
        根据标题和年份，检查电影是否存在
        返回匹配的电影列表
        """
        if not self.is_authenticated() or not self._api or not title:
            return None

        # 会话失效时尝试重连
        if self.is_inactive():
            if not self.reconnect():
                return None

        data = self._api.search(title)
        if not data:
            return []

        ret_movies = []
        for info in self.__extract_video_info_list(data.get("movies_list")):
            info_title = info.get("name") or info.get("original_name")
            if title not in [info.get("name"), info.get("original_name")]:
                continue
            item_year = info.get("year")
            if year and str(item_year) != str(year):
                continue
            ret_movies.append({
                "title": info.get("name"),
                "year": str(info.get("year", "")),
                "id": info.get("ug_video_info_id"),
            })
        return ret_movies

    def get_tv_episodes(self, item_id=None, title=None, year=None, tmdbid=None, season=None):
        """
        根据标题、年份、季查询电视剧所有集信息
        返回格式: [{"season_num": 1, "episode_num": 1}, ...]
        """
        if not self.is_authenticated() or not self._api:
            return None

        # 会话失效时尝试重连
        if self.is_inactive():
            if not self.reconnect():
                return None

        cached_item_id = item_id
        if not item_id:
            if not title:
                return []
            tv_info = self.__search_tv_item(title, year, tmdbid)
            if not tv_info:
                return []
            found_id = tv_info.get("ug_video_info_id")
            if found_id is None:
                return []
            item_id = str(found_id)
        else:
            item_id = str(item_id)

        # 获取剧集详情
        tv_detail = self._api.get_tv(item_id, folder_path="ALL")
        if not tv_detail:
            # 缓存 ID 失效时回退到标题搜索
            if cached_item_id and title:
                log.warning(f"【{self.client_name}】缓存的电视剧 ID {cached_item_id} 已失效，尝试按标题重新搜索：{title}")
                tv_info = self.__search_tv_item(title, year, tmdbid)
                if not tv_info:
                    return []
                found_id = tv_info.get("ug_video_info_id")
                if found_id is None:
                    return []
                item_id = str(found_id)
                tv_detail = self._api.get_tv(item_id, folder_path="ALL")
                if not tv_detail:
                    return []
            else:
                return []

        # 解析季集映射
        season_map = {}
        for info in tv_detail.get("season_info") or []:
            if not isinstance(info, dict):
                continue
            category_id = info.get("category_id")
            season_num = info.get("season_num")
            if category_id and isinstance(season_num, int):
                season_map[str(category_id)] = season_num

        # 解析集数
        exists_episodes = []
        for ep in tv_detail.get("tv_info") or []:
            if not isinstance(ep, dict):
                continue
            episode = ep.get("episode")
            if not isinstance(episode, int):
                continue
            season_num = season_map.get(str(ep.get("category_id")), 1)
            if season is not None and season_num != season:
                continue
            exists_episodes.append({
                "season_num": season_num,
                "episode_num": episode,
            })

        return exists_episodes

    def get_no_exists_episodes(self, meta_info, season, total_num):
        """根据标题、年份、季、总集数，查询缺少哪几集"""
        if not season:
            season = 1
        exists_episodes = self.get_tv_episodes(
            title=meta_info.title,
            year=meta_info.year,
            season=season,
        )
        if not isinstance(exists_episodes, list):
            return None
        exists_set = {ep.get("episode_num") for ep in exists_episodes
                     if ep.get("season_num") == season}
        total_episodes = set(range(1, total_num + 1))
        return sorted(total_episodes - exists_set)

    def get_remote_image_by_id(self, item_id, image_type):
        """根据 ItemId 查询远程图片地址（绿联暂不支持）"""
        return None

    def get_local_image_by_id(self, item_id):
        """
        根据 ItemId 查询本地图片地址。
        """
        if not self.is_authenticated() or not self._api or not item_id:
            return None
        try:
            info = self._api.recently_played_info(item_id)
            if not info:
                return None
            video_info = info.get("video_info") if isinstance(info.get("video_info"), dict) else None
            if not video_info:
                return None
            image_path = video_info.get("poster_path") or video_info.get("backdrop_path")
            image_url = self.__resolve_image(image_path)
            if image_url:
                host = self._play_host or self._host
                if IpUtils.is_internal(host):
                    return self.get_nt_image_url(url=image_url, remote=True)
                return image_url
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取图片地址出错：{str(e)}")
        return None

    def get_iteminfo(self, itemid):
        """
        根据 ItemId 从媒体服务器查询项目详情。
        新增方法，修复原实现缺失问题。
        """
        if not self.is_authenticated() or not self._api or not itemid:
            return None
        try:
            info = self._api.recently_played_info(itemid)
            if not info:
                return None
            video_info = info.get("video_info") if isinstance(info.get("video_info"), dict) else None
            if not video_info or not video_info.get("ug_video_info_id"):
                return None
            return {
                "id": video_info.get("ug_video_info_id"),
                "title": video_info.get("name"),
                "originalTitle": video_info.get("original_name"),
                "year": self.__parse_year(video_info),
                "tmdbid": video_info.get("tmdb_id"),
                "type": self.__map_item_type(video_info.get("type")),
                "json": str(video_info),
            }
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取项目详情出错：{str(e)}")
        return None

    def get_episode_image_by_id(self, item_id, season_id, episode_id):
        """
        根据 itemid、season_id、episode_id 查询剧集图片地址。
        新增方法，修复原实现缺失问题。
        """
        if not self.is_authenticated() or not self._api:
            return None
        if not item_id or not season_id or not episode_id:
            return None
        # 绿联暂不支持按集获取图片，返回 None
        return None

    def refresh_root_library(self):
        """刷新整个媒体库"""
        if not self.is_authenticated() or not self._api:
            return False

        # 会话失效时尝试重连
        if self.is_inactive():
            if not self.reconnect():
                return False

        # 确保已加载媒体库列表
        if not self._libraries:
            self.get_libraries()

        log.info(f"【{self.client_name}】开始刷新所有媒体库...")
        results = []
        for lib_id, lib_info in self._libraries.items():
            lib_name = lib_info.get("name", lib_id)
            log.info(f"【{self.client_name}】刷新媒体库：{lib_name}（扫描模式: {self._scan_type}）")
            results.append(self.__scan_library(library_id=lib_id))

        success = all(results) if results else True
        if success:
            log.info(f"【{self.client_name}】所有媒体库刷新完成")
        else:
            log.warning(f"【{self.client_name}】部分媒体库刷新失败")
        return success

    def refresh_library_by_items(self, items):
        """
        按类型、名称、年份来刷新媒体库。
        支持按项目路径精确匹配媒体库。
        """
        if not items:
            return

        if not self.is_authenticated() or not self._api:
            return

        # 会话失效时尝试重连
        if self.is_inactive():
            if not self.reconnect():
                return

        log.info(f"【{self.client_name}】开始按项目刷新媒体库...")

        library_ids = set()
        for item in items:
            # 尝试匹配目标路径对应的媒体库
            target_path = item.get("target_path") if isinstance(item, dict) else None
            library_id = self.__match_library_id_by_path(target_path)
            if library_id is None:
                # 无法匹配时回退到刷新全部
                self.refresh_root_library()
                return
            library_ids.add(library_id)

        for library_id in library_ids:
            lib_name = self._libraries.get(library_id, {}).get("name", library_id)
            log.info(f"【{self.client_name}】刷新媒体库：{lib_name}（扫描模式: {self._scan_type}）")
            if not self.__scan_library(library_id=library_id):
                # 单个媒体库扫描失败时回退到刷新全部
                log.warning(f"【{self.client_name}】媒体库 {lib_name} 刷新失败，回退到刷新全部")
                self.refresh_root_library()
                return

        log.info(f"【{self.client_name}】按项目刷新媒体库完成")

    def get_libraries(self):
        """获取媒体服务器所有媒体库列表"""
        if not self.is_authenticated() or not self._api:
            return []

        # 会话失效时尝试重连
        if self.is_inactive():
            if not self.reconnect():
                return []

        try:
            media_libs = self._api.media_list()
            self._library_paths = self.__load_library_paths()
            libraries = []
            self._libraries = {}

            for lib in media_libs:
                lib_id = str(lib.get("media_lib_set_id"))
                lib_name = lib.get("media_name") or ""
                lib_path = self._library_paths.get(lib_id)
                library_type = self.__infer_library_type(lib_name, lib_path)

                # 处理图片
                poster_paths = lib.get("poster_paths") or []
                backdrop_paths = lib.get("backdrop_paths") or []
                image = None
                for p in [*poster_paths, *backdrop_paths]:
                    resolved = self.__resolve_image(p)
                    if resolved:
                        image = resolved
                        break

                self._libraries[lib_id] = {
                    "id": lib_id,
                    "name": lib_name,
                    "path": lib_path,
                    "type": library_type,
                    "video_count": lib.get("video_count") or 0,
                }

                libraries.append({
                    "id": lib_id,
                    "name": lib_name,
                    "path": lib_path,
                    "type": library_type,
                    "image": image,
                    "link": self.__build_root_url(),
                })

            return libraries
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取媒体库列表出错：{str(e)}")
            return []

    def get_items(self, parent):
        """获取媒体库中的所有媒体（生成器）"""
        if not parent:
            yield {}
            return

        if not self.is_authenticated() or not self._api:
            yield {}
            return

        # 会话失效时尝试重连
        if self.is_inactive():
            if not self.reconnect():
                yield {}
                return

        library_id = str(parent)
        if not self._library_paths:
            self.get_libraries()

        root_path = self._library_paths.get(library_id)
        if not root_path:
            yield {}
            return

        try:
            for video in self._iter_library_videos(root_path=root_path):
                video_type = video.get("type")
                if video_type not in [1, 2]:
                    continue

                item_id = video.get("ug_video_info_id")
                if not item_id:
                    continue

                yield {
                    "id": str(item_id),
                    "library": library_id,
                    "type": self.__map_item_type(video_type),
                    "title": video.get("name"),
                    "originalTitle": video.get("original_name"),
                    "year": self.__parse_year(video),
                    "tmdbid": video.get("tmdb_id"),
                    "path": video.get("path"),
                    "json": str(video),
                }
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取媒体列表出错：{str(e)}")

        yield {}

    def get_play_url(self, item_id):
        """拼装媒体播放链接"""
        if not self.is_authenticated():
            return None
        # 绿联深链在部分版本会失效，统一回落到 NAS 根地址
        return self.__build_root_url()

    def get_playing_sessions(self):
        """获取正在播放的会话（绿联暂不支持）"""
        return []

    def get_webhook_message(self, message):
        """解析 Webhook 报文（绿联暂不支持）"""
        return {}

    def get_resume(self, num=12):
        """获得继续观看"""
        if not self.is_authenticated() or not self._api:
            return []

        # 会话失效时尝试重连
        if self.is_inactive():
            if not self.reconnect():
                return []

        try:
            page_size = max(1, num)
            data = self._api.recently_played(page=1, page_size=page_size)
            if not data:
                return []

            ret_resume = []
            for item in data.get("video_arr") or []:
                if len(ret_resume) >= page_size:
                    break
                if not isinstance(item, dict):
                    continue

                video_info = item.get("video_info") if isinstance(item.get("video_info"), dict) else {}
                if not video_info:
                    continue

                library_id = str(video_info.get("media_lib_set_id") or "")
                if self.__is_library_blocked(library_id):
                    continue

                item_id = video_info.get("ug_video_info_id")
                if item_id is None:
                    continue

                play_status = item.get("play_status") if isinstance(item.get("play_status"), dict) else {}
                progress = play_status.get("progress") if isinstance(play_status.get("progress"), (int, float)) else 0

                video_type = video_info.get("type")
                if video_type == 2:
                    subtitle = play_status.get("tv_name") or "剧集"
                    media_type = MediaType.TV.value
                else:
                    subtitle = "电影"
                    media_type = MediaType.MOVIE.value

                image = self.__resolve_image(video_info.get("poster_path")) or self.__resolve_image(
                    video_info.get("backdrop_path")
                )

                ret_resume.append({
                    "id": str(item_id),
                    "name": video_info.get("name"),
                    "type": media_type,
                    "image": image,
                    "link": self.__build_root_url(),
                    "percent": max(0.0, min(100.0, progress * 100.0)),
                    "subtitle": subtitle,
                })

            return ret_resume
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取继续观看出错：{str(e)}")
            return []

    def get_latest(self, num=20):
        """获得最近更新"""
        if not self.is_authenticated() or not self._api:
            return []

        # 会话失效时尝试重连
        if self.is_inactive():
            if not self.reconnect():
                return []

        try:
            page_size = max(1, num)
            data = self._api.recently_updated(page=1, page_size=page_size)
            if not data:
                return []

            ret_latest = []
            for item in data.get("video_arr") or []:
                if len(ret_latest) >= page_size:
                    break
                if not isinstance(item, dict):
                    continue

                video_info = item.get("video_info") if isinstance(item.get("video_info"), dict) else {}
                if not video_info:
                    continue

                library_id = str(video_info.get("media_lib_set_id") or "")
                if self.__is_library_blocked(library_id):
                    continue

                item_id = video_info.get("ug_video_info_id")
                if item_id is None:
                    continue

                video_type = video_info.get("type")
                if video_type == 2:
                    media_type = MediaType.TV.value
                elif video_type == 1:
                    media_type = MediaType.MOVIE.value
                else:
                    continue

                image = self.__resolve_image(video_info.get("poster_path")) or self.__resolve_image(
                    video_info.get("backdrop_path")
                )

                ret_latest.append({
                    "id": str(item_id),
                    "name": video_info.get("name"),
                    "type": media_type,
                    "image": image,
                    "link": self.__build_root_url(),
                })

            return ret_latest
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取最近更新出错：{str(e)}")
            return []

    def get_host(self):
        """获取 host 地址"""
        return self._host
