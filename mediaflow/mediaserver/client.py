"""
媒体服务器客户端基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class MediaItem:
    """媒体条目"""
    id: str
    title: str
    year: Optional[int] = None
    media_type: str = "movie"
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    overview: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    runtime: Optional[int] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    file_path: Optional[str] = None
    file_size: int = 0
    last_played: Optional[datetime] = None
    play_count: int = 0
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None


@dataclass
class LibraryInfo:
    """媒体库信息"""
    id: str
    name: str
    media_type: str
    item_count: int = 0
    path: Optional[str] = None


@dataclass
class ServerInfo:
    """服务器信息"""
    name: str
    version: str
    server_type: str
    ip: str
    port: int
    username: Optional[str] = None
    is_connected: bool = False


class MediaServerClient(ABC):
    """媒体服务器客户端基类"""

    def __init__(self, host: str, port: int, api_key: str, username: str = None) -> None:
        self.host = host
        self.port = port
        self.api_key = api_key
        self.username = username
        self._session = None

    @abstractmethod
    def connect(self) -> bool:
        """连接服务器"""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass

    @abstractmethod
    def get_server_info(self) -> Optional[ServerInfo]:
        """获取服务器信息"""
        pass

    @abstractmethod
    def get_libraries(self) -> List[LibraryInfo]:
        """获取媒体库列表"""
        pass

    @abstractmethod
    def get_items(self, library_id: str, media_type: str = None) -> List[MediaItem]:
        """获取媒体库中的项目"""
        pass

    @abstractmethod
    def get_item_detail(self, item_id: str) -> Optional[MediaItem]:
        """获取项目详情"""
        pass

    @abstractmethod
    def search_media(self, keyword: str, media_type: str = None) -> List[MediaItem]:
        """搜索媒体"""
        pass

    @abstractmethod
    def refresh_library(self, library_id: str) -> bool:
        """刷新媒体库"""
        pass

    @abstractmethod
    def get_recently_added(self, limit: int = 20) -> List[MediaItem]:
        """获取最近添加"""
        pass

    @abstractmethod
    def get_user_data(self, item_id: str) -> Dict[str, Any]:
        """获取用户数据"""
        pass

    @abstractmethod
    def mark_watched(self, item_id: str) -> bool:
        """标记已观看"""
        pass

    @abstractmethod
    def mark_unwatched(self, item_id: str) -> bool:
        """标记未观看"""
        pass

    def get_base_url(self) -> str:
        """获取基础URL"""
        return f"http://{self.host}:{self.port}"

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._session is not None
