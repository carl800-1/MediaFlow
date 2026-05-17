"""
扩展类型定义
为项目核心数据类型定义类型别名和泛型类型
"""
from typing import Any, Dict, List, Optional, Union, Tuple, Callable, TypeVar, Literal
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

# 媒体信息相关类型
@dataclass
class MediaInfo:
    """媒体信息数据结构"""
    title: str
    media_type: str
    year: Optional[str] = None
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    tvdb_id: Optional[int] = None
    douban_id: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    genres: List[str] = field(default_factory=list)
    runtime: Optional[int] = None
    tagline: Optional[str] = None
    release_date: Optional[datetime] = None
    seasons: Optional[int] = None
    episodes: Optional[int] = None

@dataclass
class TorrentInfo:
    """种子信息数据结构"""
    title: str
    subtitle: Optional[str] = None
    page_url: Optional[str] = None
    download_url: Optional[str] = None
    size: Optional[int] = None
    seeders: Optional[int] = None
    leechers: Optional[int] = None
    uploadvolumefactor: Optional[float] = None
    downloadvolumefactor: Optional[float] = None
    release_group: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    site: Optional[str] = None
    upload_time: Optional[datetime] = None
    free_deadline: Optional[datetime] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None

@dataclass
class DownloadTask:
    """下载任务数据结构"""
    download_id: str
    title: str
    torrent_url: str
    file_path: Optional[str] = None
    size: int = 0
    state: str = "pending"
    progress: float = 0.0
    speed: int = 0
    uploaded: int = 0
    ratio: float = 0.0
    seed_time: float = 0.0
    added_time: Optional[datetime] = None
    download_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None

@dataclass
class SiteUserInfo:
    """站点用户信息"""
    site_name: str
    username: str
    user_level: Optional[str] = None
    join_date: Optional[datetime] = None
    upload_size: int = 0
    download_size: int = 0
    upload_count: int = 0
    download_count: int = 0
    bonus: float = 0.0
    ratio: float = 0.0
    seeding_size: int = 0
    seeding_count: int = 0
    leeching_count: int = 0

@dataclass
class MediaServerInfo:
    """媒体服务器信息"""
    server_type: str
    server_name: str
    server_url: str
    api_key: Optional[str] = None
    library_names: List[str] = field(default_factory=list)
    user_count: int = 0
    device_count: int = 0

# 配置相关类型
ConfigDict = Dict[str, Any]
ConfigValue = Union[str, int, float, bool, List[Any], Dict[str, Any], None]

# HTTP请求相关类型
HeadersDict = Dict[str, str]
CookiesDict = Dict[str, str]
QueryParams = Dict[str, Union[str, int, float, bool]]

# API响应类型
ApiResponse = Dict[str, Any]
ApiResult = Tuple[bool, Any, Optional[str]]

# 回调函数类型
CallbackFunc = Callable[..., Any]
ProgressCallback = Callable[[float, str], None]

# 数据库相关类型
ModelClass = TypeVar('ModelClass')
DbSession = Any
FilterCondition = Dict[str, Any]
SortCondition = List[Tuple[str, str]]

# 搜索相关类型
SearchResult = List[TorrentInfo]
SearchFilter = Dict[str, Any]
IndexerConfig = Dict[str, Union[str, int, bool]]

# 刷流相关类型
BrushTaskConfig = Dict[str, Any]
BrushTaskStats = Dict[str, Union[int, float, str]]
BrushTaskStatus = Literal["running", "paused", "stopped", "completed", "error"]

# 消息通知相关类型
NotificationMessage = Dict[str, Any]
NotificationChannel = Literal["telegram", "email", "webhook", "pushdeer", "slack"]

# 插件相关类型
PluginConfig = Dict[str, Any]
PluginState = Literal["enabled", "disabled", "error"]
PluginInfo = Dict[str, Union[str, int, bool, List[str]]]

# 任务调度相关类型
ScheduledTask = Dict[str, Any]
TaskSchedule = Dict[str, Union[str, int, List[int]]]
CronExpression = str

# 文件处理相关类型
FileInfo = Dict[str, Union[str, int, datetime]]
FilePath = str
TransferMode = Literal["link", "softlink", "copy", "move", "rclone_copy", "rclone_move"]

# RSS订阅相关类型
RssFeed = Dict[str, Any]
RssItem = Dict[str, Any]
RssFilter = Dict[str, Union[str, List[str], bool]]

# 索引器相关类型
IndexerResult = Dict[str, Any]
IndexerType = Literal["builtin", "jackett", "prowlarr"]
IndexerCredential = Dict[str, str]

# 媒体库相关类型
LibraryInfo = Dict[str, Union[str, int, List[str]]]
LibraryItem = Dict[str, Any]
LibrarySyncStatus = Literal["idle", "syncing", "synced", "error"]

# Webhook事件相关类型
WebhookEvent = Dict[str, Any]
WebhookPayload = Dict[str, Any]
WebhookResponse = Tuple[int, str, Dict[str, str]]

# 缓存相关类型
CacheKey = str
CacheValue = Any
CacheTTL = Union[int, timedelta, None]

# 错误处理相关类型
ErrorCode = Union[str, int]
ErrorMessage = str
ErrorContext = Dict[str, Any]

# 通用类型别名
JsonDict = Dict[str, Any]
JsonList = List[Any]
StringOrNone = Optional[str]
IntOrNone = Optional[int]
BoolOrNone = Optional[bool]
FloatOrNone = Optional[float]

# 并发控制相关类型
ThreadPoolExecutor = Any
AsyncResult = Any
Lock = Any
Semaphore = Any

# 路径和URL相关类型
Url = str
FilePath = str
DirectoryPath = str
RelativePath = str

# 日期时间相关类型
DateTimeStr = str
TimeStamp = Union[int, float]
TimeDeltaSeconds = Union[int, float]

# 枚举类型定义
class DownloadState(Enum):
    """下载状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class TransferState(Enum):
    """文件传输状态"""
    PENDING = "pending"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class SyncState(Enum):
    """同步状态"""
    IDLE = "idle"
    SYNCING = "syncing"
    SYNCED = "synced"
    ERROR = "error"

class SearchState(Enum):
    """搜索状态"""
    IDLE = "idle"
    SEARCHING = "searching"
    FOUND = "found"
    NO_RESULT = "no_result"
    ERROR = "error"

# 类型守卫函数
def is_media_type(value: Any) -> bool:
    """判断是否为有效的媒体类型"""
    return value in ["TV", "MOVIE", "ANIME", "MOV", "TV", "电影", "电视剧", "动漫"]

def is_valid_url(url: str) -> bool:
    """判断是否为有效的URL"""
    return url.startswith(("http://", "https://", "magnet:", "ftp://"))

def is_torrent_file(path: str) -> bool:
    """判断是否为种子文件"""
    return path.endswith((".torrent", ".bit"))

def is_media_file(path: str) -> bool:
    """判断是否为媒体文件"""
    media_extensions = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.mp3', '.flac', '.wav', '.aac', '.m4a', '.ogg',
        '.srt', '.ass', '.ssa', '.sub'
    }
    return any(path.lower().endswith(ext) for ext in media_extensions)
