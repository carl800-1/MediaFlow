"""
数据库模型定义

使用dataclass定义数据库模型
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MediaType(Enum):
    """媒体类型"""
    MOVIE = "movie"
    TV = "tv"
    ANIME = "anime"
    UNKNOWN = "unknown"


class TorrentStatus(Enum):
    """种子状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskState(Enum):
    """任务状态"""
    ENABLED = "Y"
    STOPPED = "S"
    PAUSED = "P"


@dataclass
class Media:
    """媒体信息模型"""
    id: Optional[int] = None
    title: str = ""
    year: Optional[int] = None
    media_type: str = "unknown"
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    imdb_rating: Optional[float] = None
    poster_path: Optional[str] = None
    overview: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Torrent:
    """种子信息模型"""
    id: Optional[int] = None
    hash: str = ""
    title: str = ""
    size: int = 0
    site_id: Optional[int] = None
    seeders: int = 0
    leechers: int = 0
    download_speed: float = 0.0
    upload_speed: float = 0.0
    completed: int = 0
    status: str = "pending"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Site:
    """站点信息模型"""
    id: Optional[int] = None
    name: str = ""
    url: str = ""
    cookie: Optional[str] = None
    sign_url: Optional[str] = None
    rss_url: Optional[str] = None
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Downloader:
    """下载器信息模型"""
    id: Optional[int] = None
    name: str = ""
    type: str = "qbittorrent"
    host: str = "localhost"
    port: int = 8080
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: bool = True
    created_at: Optional[datetime] = None


@dataclass
class BrushTask:
    """刷流任务模型"""
    id: Optional[int] = None
    name: str = ""
    site_id: Optional[int] = None
    downloader_id: Optional[int] = None
    interval: str = "30"
    state: str = "S"
    filter_rule: Optional[str] = None
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Subscription:
    """订阅任务模型"""
    id: Optional[int] = None
    name: str = ""
    media_id: Optional[int] = None
    rss_url: Optional[str] = None
    keywords: Optional[str] = None
    state: str = "Y"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class SearchResult:
    """搜索结果模型"""
    id: Optional[int] = None
    title: str = ""
    size: int = 0
    seeders: int = 0
    leechers: int = 0
    site_name: str = ""
    site_url: str = ""
    torrent_url: str = ""
    created_at: Optional[datetime] = None


class Base:
    """模型基类"""

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Base":
        """从字典创建实例"""
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__annotations__
        })
