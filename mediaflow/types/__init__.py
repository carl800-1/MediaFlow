"""
类型定义扩展模块

提供项目中使用的自定义类型别名和协议定义
"""

from typing import TypeAlias, Callable, Awaitable, Any
from pathlib import Path
from enum import Enum


class DownloaderType(Enum):
    """下载器类型枚举"""
    QBITTORRENT = "qbittorrent"
    TRANSMISSION = "transmission"
    ARIA2 = "aria2"
    PAN115 = "pan115"
    PIKPAK = "pikpak"


class MediaType(Enum):
    """媒体类型枚举"""
    MOVIE = "movie"
    TV = "tv"
    ANIME = "anime"
    UNKNOWN = "unknown"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SiteType(Enum):
    """站点类型枚举"""
    PRIVATE = "private"
    PUBLIC = "public"
    INDEXER = "indexer"


class MessageChannel(Enum):
    """消息渠道枚举"""
    TELEGRAM = "telegram"
    WECHAT = "wechat"
    EMAIL = "email"
    PUSHPLUS = "pushplus"
    BARK = "bark"
    SERVERCHAN = "serverchan"
    SLACK = "slack"
    WEBHOOK = "webhook"


CallbackFunc: TypeAlias = Callable[..., Any]
AsyncCallbackFunc: TypeAlias = Awaitable[CallbackFunc[Any]]

ConfigDict: TypeAlias = dict[str, Any]
TorrentInfo: TypeAlias = dict[str, Any]
MediaInfo: TypeAlias = dict[str, Any]

FilePath: TypeAlias = Path | str
