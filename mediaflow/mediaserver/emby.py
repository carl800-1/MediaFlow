"""
Emby 媒体服务器客户端
"""

import requests
from typing import List, Dict, Any, Optional

from mediaflow.utils.cli import getLogger
from mediaflow.mediaserver.client import MediaServerClient, MediaItem, LibraryInfo, ServerInfo


logger = getLogger("emby")


class EmbyClient(MediaServerClient):
    """Emby 客户端"""

    def __init__(self, host: str, port: int, api_key: str, username: str = None) -> None:
        super().__init__(host, port, api_key, username)
        self._base_url = f"http://{host}:{port}"

    def connect(self) -> bool:
        """连接服务器"""
        try:
            headers = {"X-Emby-Token": self.api_key}
            response = requests.get(
                f"{self._base_url}/System/Info",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                self._session = requests.Session()
                self._session.headers.update(headers)
                logger.info("Emby 连接成功")
                return True
            return False
        except Exception as e:
            logger.error(f"Emby 连接失败: {e}")
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
                    name=data.get("ServerName", "Emby"),
                    version=data.get("Version", ""),
                    server_type="emby",
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
            response = self._session.get(f"{self._base_url}/Library/VirtualFolders")
            if response.status_code == 200:
                libraries = []
                for item in response.json():
                    library = LibraryInfo(
                        id=item.get("LibraryId", ""),
                        name=item.get("Name", ""),
                        media_type=self._get_library_type(item),
                        item_count=item.get("ItemCount", 0),
                    )
                    libraries.append(library)
                return libraries
        except Exception as e:
            logger.error(f"获取媒体库失败: {e}")
        return []

    def _get_library_type(self, item: Dict) -> str:
        """获取媒体库类型"""
        collection_type = item.get("CollectionType", "")
        type_map = {
            "movies": "movie",
            "tvshows": "tv",
            "music": "music",
            "musicvideos": "music"
        }
        return type_map.get(collection_type, "mixed")

    def get_items(self, library_id: str = None, media_type: str = None) -> List[MediaItem]:
        """获取媒体库中的项目"""
        if not self._session:
            return []

        try:
            params = {
                "Recursive": True,
                "Fields": "BasicSyncInfo,MediaSourceInfo,ProviderIds"
            }

            if library_id:
                params["ParentId"] = library_id
            if media_type:
                params["MediaType"] = media_type.upper()

            response = self._session.get(f"{self._base_url}/Items", params=params)

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
                    "Fields": "MediaSources,Overview,Genres,ProviderIds,PremiereDate"
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
            item_type = item.get("Type", "Video")

            if item_type == "Movie":
                media_type = "movie"
            elif item_type == "Series":
                media_type = "tv"
            elif item_type == "MusicAlbum":
                media_type = "music"
            else:
                media_type = "video"

            media_item = MediaItem(
                id=str(item.get("Id", "")),
                title=item.get("Name", "Unknown"),
                year=item.get("ProductionYear"),
                media_type=media_type,
                overview=item.get("Overview"),
                genres=item.get("Genres", []),
                runtime=item.get("RunTimeTicks", 0) // 600000000 if item.get("RunTimeTicks") else None,
                poster_url=self._get_image_url(item.get("Id"), "Primary"),
                backdrop_url=self._get_image_url(item.get("Id"), "Backdrop"),
            )

            if "ProviderIds" in item:
                provider_ids = item["ProviderIds"]
                if isinstance(provider_ids, dict):
                    media_item.imdb_id = provider_ids.get("Imdb")
                    tmdb = provider_ids.get("Tmdb")
                    if tmdb:
                        try:
                            media_item.tmdb_id = int(tmdb)
                        except ValueError:
                            pass

            media_sources = item.get("MediaSources", [])
            if media_sources and isinstance(media_sources[0], dict):
                media = media_sources[0]
                media_item.file_path = media.get("Path")
                media_item.file_size = int(media.get("Size", 0))

                for stream in media.get("MediaStreams", []):
                    if isinstance(stream, dict):
                        if stream.get("Type") == 1:
                            media_item.resolution = f"{stream.get('Width', 0)}x{stream.get('Height', 0)}"
                            media_item.video_codec = stream.get("Codec", "")
                        elif stream.get("Type") == 2:
                            media_item.audio_codec = stream.get("Codec", "")

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
                "IncludeOverview": True,
                "IncludeImages": True
            }

            if media_type:
                params["MediaTypes"] = f'["{media_type.upper()}"]'

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

    def refresh_library(self, library_id: str = None) -> bool:
        """刷新媒体库"""
        if not self._session:
            return False

        try:
            if library_id:
                response = self._session.post(
                    f"{self._base_url}/Library/VirtualFolders/Refresh",
                    params={"RefreshLibraryId": library_id}
                )
            else:
                response = self._session.get(f"{self._base_url}/Library/Refresh")
            return response.status_code in [200, 204, 202]
        except Exception as e:
            logger.error(f"刷新媒体库失败: {e}")
            return False

    def get_recently_added(self, limit: int = 20) -> List[MediaItem]:
        """获取最近添加"""
        if not self._session:
            return []

        try:
            params = {
                "SortBy": "DateCreated",
                "SortOrder": "Descending",
                "Limit": limit,
                "Fields": "BasicSyncInfo"
            }

            response = self._session.get(
                f"{self._base_url}/Items",
                params=params
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
            response = self._session.get(
                f"{self._base_url}/Users/Me/PlayingItems/{item_id}"
            )
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
