"""
绿联影视媒体服务器客户端

支持绿联 NAS 影视中心 API
"""

import requests
from typing import List, Dict, Any, Optional
import hashlib
import time

from mediaflow.utils.cli import getLogger
from mediaflow.mediaserver.client import MediaServerClient, MediaItem, LibraryInfo, ServerInfo


logger = getLogger("ugreen")


class UGreenClient(MediaServerClient):
    """绿联影视客户端"""

    def __init__(self, host: str, port: int, api_key: str = None, username: str = None, password: str = None) -> None:
        super().__init__(host, port, api_key, username)
        self._base_url = f"http://{host}:{port}"
        self._password = password
        self._token = None
        self._device_id = self._generate_device_id()

    def _generate_device_id(self) -> str:
        """生成设备ID"""
        return hashlib.md5(str(time.time()).encode()).hexdigest()[:16]

    def connect(self) -> bool:
        """连接绿联影视"""
        try:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json"
            })

            if self._api_key:
                self._token = self._api_key
                return True

            if self._username and self._password:
                return self._login()

            return True

        except Exception as e:
            logger.error(f"绿联影视连接失败: {e}")
            return False

    def _login(self) -> bool:
        """登录绿联影视"""
        try:
            password_hash = hashlib.sha256(self._password.encode()).hexdigest()

            response = self._session.post(
                f"{self._base_url}/api/v1/user/login",
                json={
                    "username": self._username,
                    "password": password_hash,
                    "device_id": self._device_id
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    self._token = data.get("data", {}).get("token")
                    return True

            return False

        except Exception as e:
            logger.error(f"绿联影视登录失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开连接"""
        self._session = None
        self._token = None
        return True

    def get_server_info(self) -> Optional[ServerInfo]:
        """获取服务器信息"""
        if not self._session:
            self.connect()
        if not self._session:
            return None

        try:
            response = self._session.get(
                f"{self._base_url}/api/v1/system/info",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return ServerInfo(
                    name=data.get("hostname", "UGREEN NAS"),
                    version=data.get("version", ""),
                    server_type="ugreen",
                    ip=self.host,
                    port=self.port,
                    is_connected=True
                )

        except Exception as e:
            logger.error(f"获取服务器信息失败: {e}")
        return None

    def get_libraries(self) -> List[LibraryInfo]:
        """获取媒体库列表"""
        if not self._session:
            return []

        libraries = []

        try:
            response = self._session.get(
                f"{self._base_url}/api/v1/media/libraries",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                for lib in data.get("data", []):
                    library = LibraryInfo(
                        id=str(lib.get("id", "")),
                        name=lib.get("name", ""),
                        media_type=self._get_library_type(lib.get("type", "")),
                        item_count=lib.get("count", 0),
                        path=lib.get("path")
                    )
                    libraries.append(library)

        except Exception as e:
            logger.error(f"获取媒体库失败: {e}")

        return libraries

    def _get_headers(self) -> Dict:
        """获取请求头"""
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _get_library_type(self, lib_type: str) -> str:
        """获取媒体库类型"""
        type_map = {
            "movie": "movie",
            "movies": "movie",
            "tv": "tv",
            "tvshow": "tv",
            "tvshows": "tv",
            "video": "video",
            "anime": "anime",
            "music": "music"
        }
        return type_map.get(lib_type.lower(), "video")

    def get_items(self, library_id: str = None, media_type: str = None) -> List[MediaItem]:
        """获取媒体项目"""
        if not self._session:
            return []

        try:
            params = self._get_headers()
            if library_id:
                params["library_id"] = library_id
            if media_type:
                params["type"] = media_type

            response = self._session.get(
                f"{self._base_url}/api/v1/media/items",
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                items = []
                for item in data.get("data", []):
                    media_item = self._parse_item(item)
                    if media_item:
                        items.append(media_item)
                return items

        except Exception as e:
            logger.error(f"获取媒体项目失败: {e}")

        return []

    def get_item_detail(self, item_id: str) -> Optional[MediaItem]:
        """获取项目详情"""
        if not self._session:
            return None

        try:
            response = self._session.get(
                f"{self._base_url}/api/v1/media/item/{item_id}",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_item(data.get("data", {}))

        except Exception as e:
            logger.error(f"获取项目详情失败: {e}")

        return None

    def _parse_item(self, item: Dict) -> Optional[MediaItem]:
        """解析媒体条目"""
        try:
            media_type = item.get("type", "video")
            if media_type in ["movie", "movies"]:
                media_type = "movie"
            elif media_type in ["tv", "tvshow", "tvshows"]:
                media_type = "tv"

            media_item = MediaItem(
                id=str(item.get("id", "")),
                title=item.get("title", item.get("name", "Unknown")),
                year=item.get("year"),
                media_type=media_type,
                overview=item.get("overview", item.get("description")),
                genres=item.get("genres", []),
                runtime=item.get("duration"),
                poster_url=self._get_image_url(item.get("poster")),
                backdrop_url=self._get_image_url(item.get("backdrop")),
                imdb_id=item.get("imdb_id"),
                tmdb_id=item.get("tmdb_id"),
            )

            if "file" in item:
                file_info = item["file"]
                if isinstance(file_info, dict):
                    media_item.file_path = file_info.get("path")
                    media_item.file_size = file_info.get("size", 0)

            return media_item

        except Exception as e:
            logger.error(f"解析项目失败: {e}")
            return None

    def _get_image_url(self, path: str) -> Optional[str]:
        """获取图片URL"""
        if not path:
            return None
        if path.startswith("http"):
            return path
        return f"{self._base_url}{path}"

    def search_media(self, keyword: str, media_type: str = None) -> List[MediaItem]:
        """搜索媒体"""
        if not self._session:
            return []

        try:
            params = {
                "keyword": keyword,
            }
            if media_type:
                params["type"] = media_type

            response = self._session.get(
                f"{self._base_url}/api/v1/media/search",
                params=params,
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                items = []
                for item in data.get("data", []):
                    media_item = self._parse_item(item)
                    if media_item:
                        items.append(media_item)
                return items

        except Exception as e:
            logger.error(f"搜索媒体失败: {e}")

        return []

    def refresh_library(self, library_id: str = None) -> bool:
        """刷新媒体库"""
        if not self._session:
            return False

        try:
            url = f"{self._base_url}/api/v1/media/refresh"
            if library_id:
                url = f"{url}/{library_id}"

            response = self._session.post(
                url,
                headers=self._get_headers(),
                timeout=30
            )

            return response.status_code in [200, 201, 204]

        except Exception as e:
            logger.error(f"刷新媒体库失败: {e}")
            return False

    def get_recently_added(self, limit: int = 20) -> List[MediaItem]:
        """获取最近添加"""
        if not self._session:
            return []

        try:
            response = self._session.get(
                f"{self._base_url}/api/v1/media/recent",
                params={"limit": limit},
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                items = []
                for item in data.get("data", [])[:limit]:
                    media_item = self._parse_item(item)
                    if media_item:
                        items.append(media_item)
                return items

        except Exception as e:
            logger.error(f"获取最近添加失败: {e}")

        return []

    def get_user_data(self, item_id: str) -> Dict[str, Any]:
        """获取用户数据"""
        if not self._session:
            return {}

        try:
            response = self._session.get(
                f"{self._base_url}/api/v1/media/progress/{item_id}",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "play_count": data.get("data", {}).get("play_count", 0),
                    "position": data.get("data", {}).get("position", 0),
                    "duration": data.get("data", {}).get("duration", 0),
                }

        except Exception as e:
            logger.error(f"获取用户数据失败: {e}")

        return {}

    def mark_watched(self, item_id: str) -> bool:
        """标记已观看"""
        return self._update_progress(item_id, watched=True)

    def mark_unwatched(self, item_id: str) -> bool:
        """标记未观看"""
        return self._update_progress(item_id, watched=False)

    def _update_progress(self, item_id: str, watched: bool = True, position: int = 0) -> bool:
        """更新观看进度"""
        if not self._session:
            return False

        try:
            response = self._session.post(
                f"{self._base_url}/api/v1/media/progress/{item_id}",
                headers=self._get_headers(),
                json={
                    "watched": watched,
                    "position": position
                },
                timeout=10
            )

            return response.status_code in [200, 201, 204]

        except Exception as e:
            logger.error(f"更新进度失败: {e}")
            return False

    def get_stream_url(self, item_id: str) -> Optional[str]:
        """获取流媒体URL"""
        if not self._session:
            return None

        try:
            response = self._session.get(
                f"{self._base_url}/api/v1/media/play/{item_id}",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("url")

        except Exception as e:
            logger.error(f"获取播放URL失败: {e}")

        return None
