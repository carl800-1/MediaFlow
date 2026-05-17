"""
Plex 媒体服务器客户端
"""

import requests
from typing import List, Dict, Any, Optional

from mediaflow.utils.cli import getLogger
from mediaflow.mediaserver.client import MediaServerClient, MediaItem, LibraryInfo, ServerInfo


logger = getLogger("plex")


class PlexClient(MediaServerClient):
    """Plex 客户端"""

    def __init__(self, host: str, port: int, api_key: str, username: str = None) -> None:
        super().__init__(host, port, api_key, username)
        self._base_url = f"http://{host}:{port}"
        self.machine_id = None

    def connect(self) -> bool:
        """连接服务器"""
        try:
            params = {
                "X-Plex-Token": self.api_key
            }
            response = requests.get(
                f"{self._base_url}/identity",
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                self._session = requests.Session()
                self._session.headers.update({
                    "X-Plex-Token": self.api_key,
                    "Accept": "application/json"
                })

                identity = response.xml().find(" Plex/")
                if identity is not None:
                    self.machine_id = identity.get("machineIdentifier")
                logger.info("Plex 连接成功")
                return True
            return False
        except Exception as e:
            logger.error(f"Plex 连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开连接"""
        self._session = None
        return True

    def get_server_info(self) -> Optional[ServerInfo]:
        """获取服务器信息"""
        if not self._session:
            self.connect()
        if not self._session:
            return None

        try:
            response = self._session.get(
                f"{self._base_url}/",
                params={"X-Plex-Token": self.api_key}
            )
            if response.status_code == 200:
                data = response.json().get("MediaContainer", {})
                return ServerInfo(
                    name=data.get("friendlyName", "Plex"),
                    version=data.get("version", ""),
                    server_type="plex",
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

        try:
            response = self._session.get(f"{self._base_url}/library/sections")
            if response.status_code == 200:
                libraries = []
                data = response.json().get("MediaContainer", {})
                for section in data.get("Directory", []):
                    library = LibraryInfo(
                        id=section.get("key", ""),
                        name=section.get("title", ""),
                        media_type=self._get_library_type(section.get("type", "")),
                        item_count=section.get("totalSize", 0)
                    )
                    libraries.append(library)
                return libraries
        except Exception as e:
            logger.error(f"获取媒体库失败: {e}")
        return []

    def _get_library_type(self, lib_type: str) -> str:
        """获取媒体库类型"""
        type_map = {
            "movie": "movie",
            "show": "tv",
            "artist": "music",
            "photo": "photo"
        }
        return type_map.get(lib_type, lib_type)

    def get_items(self, library_id: str = None, media_type: str = None) -> List[MediaItem]:
        """获取媒体库中的项目"""
        if not self._session:
            return []

        try:
            endpoint = "/library/all"
            if library_id:
                endpoint = f"/library/sections/{library_id}"

            if media_type:
                params = {"type": 1 if media_type == "movie" else 2}
            else:
                params = {}

            response = self._session.get(f"{self._base_url}{endpoint}", params=params)

            if response.status_code == 200:
                items = []
                data = response.json().get("MediaContainer", {})
                for item in data.get("Metadata", []):
                    media_item = self._parse_item(item)
                    if media_item:
                        items.append(media_item)
                return items
        except Exception as e:
            logger.error(f"获取项目失败: {e}")
        return []

    def get_item_detail(self, item_id: str) -> Optional[MediaItem]:
        """获取项目详情"""
        if not self._session:
            return None

        try:
            response = self._session.get(f"{self._base_url}/library/metadata/{item_id}")
            if response.status_code == 200:
                data = response.json().get("MediaContainer", {})
                items = data.get("Metadata", [])
                if items:
                    return self._parse_item(items[0])
        except Exception as e:
            logger.error(f"获取项目详情失败: {e}")
        return None

    def _parse_item(self, item: Dict) -> Optional[MediaItem]:
        """解析媒体条目"""
        try:
            media_type = item.get("type", "movie")
            if media_type == "movie":
                media_type = "movie"
            elif media_type == "show":
                media_type = "tv"
            elif media_type == "track":
                media_type = "music"

            media_item = MediaItem(
                id=str(item.get("ratingKey", "")),
                title=item.get("title", "Unknown"),
                year=item.get("year"),
                media_type=media_type,
                overview=item.get("summary"),
                genres=item.get("Genre", []) if isinstance(item.get("Genre"), list) else [],
                runtime=item.get("duration", 0) // 1000 if item.get("duration") else None,
                poster_url=self._get_poster_url(item),
                backdrop_url=self._get_art_url(item),
            )

            if item.get("Guid"):
                for guid in item.get("Guid", []):
                    if isinstance(guid, dict):
                        id_value = guid.get("id", "")
                        if "imdb" in str(id_value).lower():
                            media_item.imdb_id = id_value.split("://")[-1] if "://" in id_value else id_value
                        elif "tmdb" in str(id_value).lower():
                            try:
                                media_item.tmdb_id = int(id_value.split("://")[-1])
                            except ValueError:
                                pass

            media_sources = item.get("Media", [])
            if media_sources:
                media = media_sources[0]
                if isinstance(media, dict):
                    for part in media.get("Part", []):
                        if isinstance(part, dict):
                            media_item.file_path = part.get("file")
                            media_item.file_size = int(part.get("size", 0))
                            break

            return media_item
        except Exception as e:
            logger.error(f"解析项目失败: {e}")
            return None

    def _get_poster_url(self, item: Dict) -> Optional[str]:
        """获取海报URL"""
        rating_key = item.get("ratingKey")
        if rating_key:
            return f"{self._base_url}/library/metadata/{rating_key}/thumb?X-Plex-Token={self.api_key}"
        return None

    def _get_art_url(self, item: Dict) -> Optional[str]:
        """获取背景图URL"""
        rating_key = item.get("ratingKey")
        if rating_key:
            return f"{self._base_url}/library/metadata/{rating_key}/art?X-Plex-Token={self.api_key}"
        return None

    def search_media(self, keyword: str, media_type: str = None) -> List[MediaItem]:
        """搜索媒体"""
        if not self._session:
            return []

        try:
            params = {
                "query": keyword,
                "X-Plex-Token": self.api_key
            }

            response = self._session.get(f"{self._base_url}/search", params=params)

            if response.status_code == 200:
                items = []
                data = response.json().get("MediaContainer", {})
                for result in data.get("Metadata", []):
                    media_item = self._parse_item(result)
                    if media_item:
                        if media_type is None or media_item.media_type == media_type:
                            items.append(media_item)
                return items
        except Exception as e:
            logger.error(f"搜索失败: {e}")
        return []

    def refresh_library(self, library_id: str) -> bool:
        """刷新媒体库"""
        if not self._session:
            return False

        try:
            response = self._session.get(
                f"{self._base_url}/library/sections/{library_id}/refresh"
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"刷新媒体库失败: {e}")
            return False

    def get_recently_added(self, limit: int = 20) -> List[MediaItem]:
        """获取最近添加"""
        if not self._session:
            return []

        try:
            params = {"X-Plex-Token": self.api_key, "limit": limit}
            response = self._session.get(
                f"{self._base_url}/library/recentlyAdded",
                params=params
            )

            if response.status_code == 200:
                items = []
                data = response.json().get("MediaContainer", {})
                for item in data.get("Metadata", []):
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
                f"{self._base_url}/library/metadata/{item_id}/markPlayed"
            )
            return {"status": response.status_code == 200}
        except Exception as e:
            logger.error(f"获取用户数据失败: {e}")
        return {}

    def mark_watched(self, item_id: str) -> bool:
        """标记已观看"""
        if not self._session:
            return False

        try:
            response = self._session.get(
                f"{self._base_url}/:/scrobble",
                params={"key": item_id, "identifier": "com.plexapp.plugins.library"}
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"标记已观看失败: {e}")
            return False

    def mark_unwatched(self, item_id: str) -> bool:
        """标记未观看"""
        if not self._session:
            return False

        try:
            response = self._session.get(
                f"{self._base_url}:/unscrobble",
                params={"key": item_id, "identifier": "com.plexapp.plugins.library"}
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"标记未观看失败: {e}")
            return False
