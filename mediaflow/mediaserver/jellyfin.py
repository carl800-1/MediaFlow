"""
Jellyfin 媒体服务器客户端
"""

import requests
from typing import List, Dict, Any, Optional

from mediaflow.utils.cli import getLogger
from mediaflow.mediaserver.client import MediaServerClient, MediaItem, LibraryInfo, ServerInfo


logger = getLogger("jellyfin")


class JellyfinClient(MediaServerClient):
    """Jellyfin 客户端"""

    def __init__(self, host: str, port: int, api_key: str, username: str = None) -> None:
        super().__init__(host, port, api_key, username)
        self.device_id = "MediaFlow_Client"
        self._base_url = f"http://{host}:{port}"

    def connect(self) -> bool:
        """连接服务器"""
        try:
            headers = {
                "X-Emby-Token": self.api_key,
                "X-Emby-Device-Id": self.device_id,
            }
            response = requests.get(
                f"{self._base_url}/System/Info",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                self._session = requests.Session()
                self._session.headers.update(headers)
                logger.info("Jellyfin 连接成功")
                return True
            return False
        except Exception as e:
            logger.error(f"Jellyfin 连接失败: {e}")
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
            response = self._session.get(f"{self._base_url}/System/Info")
            if response.status_code == 200:
                data = response.json()
                return ServerInfo(
                    name=data.get("ServerName", "Jellyfin"),
                    version=data.get("Version", ""),
                    server_type="jellyfin",
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
            response = self._session.get(
                f"{self._base_url}/Library/VirtualFolders",
                params={"enable-user-count": True}
            )
            if response.status_code == 200:
                libraries = []
                for item in response.json():
                    library = LibraryInfo(
                        id=item.get("LibraryId", ""),
                        name=item.get("Name", ""),
                        media_type=self._get_library_type(item),
                        item_count=item.get("ItemCount", 0),
                        path=item.get("Paths", [None])[0] if item.get("Paths") else None
                    )
                    libraries.append(library)
                return libraries
        except Exception as e:
            logger.error(f"获取媒体库失败: {e}")
        return []

    def _get_library_type(self, item: Dict) -> str:
        """获取媒体库类型"""
        collection_types = item.get("CollectionType", "")
        if collection_types in ["movies", "tvshows"]:
            return collection_types.rstrip("s")
        elif collection_types == "music":
            return "music"
        elif collection_types == "musicvideos":
            return "music"
        return "mixed"

    def get_items(self, library_id: str = None, media_type: str = None) -> List[MediaItem]:
        """获取媒体库中的项目"""
        if not self._session:
            return []

        try:
            params = {
                "recursive": True,
                "include-item-counts": True,
                "fields": "BasicSyncInfo,MediaSourceInfo,Overview"
            }

            if library_id:
                params["parentId"] = library_id
            if media_type:
                params["mediaType"] = media_type

            response = self._session.get(
                f"{self._base_url}/Items",
                params=params
            )

            if response.status_code == 200:
                items = []
                for item in response.json().get("Items", []):
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
            response = self._session.get(
                f"{self._base_url}/Items/{item_id}",
                params={
                    "fields": "MediaSources,Overview,Genres,ProviderIds"
                }
            )

            if response.status_code == 200:
                return self._parse_item(response.json())
        except Exception as e:
            logger.error(f"获取项目详情失败: {e}")
        return None

    def _parse_item(self, item: Dict) -> Optional[MediaItem]:
        """解析媒体条目"""
        try:
            media_item = MediaItem(
                id=str(item.get("Id", "")),
                title=item.get("Name", "Unknown"),
                year=item.get("ProductionYear"),
                media_type=item.get("Type", "Unknown").lower().replace("video", "movie"),
                overview=item.get("Overview"),
                genres=item.get("Genres", []),
                runtime=item.get("RunTimeTicks", 0) // 600000000 if item.get("RunTimeTicks") else None,
                poster_url=self._get_image_url(item.get("Id"), "Primary"),
                backdrop_url=self._get_image_url(item.get("Id"), "Backdrop"),
            )

            if "ProviderIds" in item:
                media_item.imdb_id = item["ProviderIds"].get("Imdb")
                tmdb = item["ProviderIds"].get("Tmdb")
                if tmdb:
                    media_item.tmdb_id = int(tmdb) if tmdb.isdigit() else None

            return media_item
        except Exception as e:
            logger.error(f"解析项目失败: {e}")
            return None

    def _get_image_url(self, item_id: str, image_type: str) -> Optional[str]:
        """获取图片URL"""
        return f"{self._base_url}/Items/{item_id}/Images/{image_type}"

    def search_media(self, keyword: str, media_type: str = None) -> List[MediaItem]:
        """搜索媒体"""
        if not self._session:
            return []

        try:
            params = {
                "searchTerm": keyword,
                "include-overview": True,
                "include-images": True
            }

            if media_type:
                params["mediaTypes"] = f'["{media_type.upper()}"]'

            response = self._session.get(
                f"{self._base_url}/Search/Hints",
                params=params
            )

            if response.status_code == 200:
                items = []
                for result in response.json().get("SearchHints", []):
                    item = MediaItem(
                        id=str(result.get("ItemId", "")),
                        title=result.get("Name", "Unknown"),
                        media_type=result.get("MediaType", "Video").lower(),
                    )
                    items.append(item)
                return items
        except Exception as e:
            logger.error(f"搜索失败: {e}")
        return []

    def refresh_library(self, library_id: str) -> bool:
        """刷新媒体库"""
        if not self._session:
            return False

        try:
            response = self._session.post(
                f"{self._base_url}/Library/VirtualFolders/Refresh",
                params={"refresh_library_id": library_id} if library_id else None
            )
            return response.status_code == 204
        except Exception as e:
            logger.error(f"刷新媒体库失败: {e}")
            return False

    def get_recently_added(self, limit: int = 20) -> List[MediaItem]:
        """获取最近添加"""
        if not self._session:
            return []

        try:
            response = self._session.get(
                f"{self._base_url}/Items",
                params={
                    "sortBy": "DateCreated",
                    "sortOrder": "Descending",
                    "limit": limit,
                    "fields": "BasicSyncInfo"
                }
            )

            if response.status_code == 200:
                items = []
                for item in response.json().get("Items", [])[:limit]:
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
            response = self._session.get(f"{self._base_url}/Users/Me/PlayingItems/{item_id}")
            if response.status_code == 200:
                data = response.json()
                return {
                    "play_count": data.get("PlayCount", 0),
                    "played": data.get("Played", False),
                    "last_played": data.get("LastPlayedDate"),
                }
        except Exception as e:
            logger.error(f"获取用户数据失败: {e}")
        return {}

    def mark_watched(self, item_id: str) -> bool:
        """标记已观看"""
        if not self._session:
            return False

        try:
            response = self._session.post(
                f"{self._base_url}/Users/Me/PlayedItems/{item_id}"
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
            response = self._session.delete(
                f"{self._base_url}/Users/Me/PlayedItems/{item_id}"
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"标记未观看失败: {e}")
            return False

    def get_download_path(self, item_id: str) -> Optional[str]:
        """获取下载路径（流地址）"""
        if not self._session:
            return None

        try:
            response = self._session.get(
                f"{self._base_url}/Items/{item_id}/PlaybackInfo",
                params={"MediaSourceId": item_id}
            )

            if response.status_code == 200:
                data = response.json()
                media_sources = data.get("MediaSources", [])
                if media_sources:
                    return media_sources[0].get("DirectStreamUrl")
        except Exception as e:
            logger.error(f"获取播放路径失败: {e}")
        return None
