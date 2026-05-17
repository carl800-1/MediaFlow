"""
搜索结果数据模型
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class TorrentInfo:
    """种子信息"""
    hash: str
    title: str
    size: int
    seeders: int = 0
    leechers: int = 0
    download_speed: float = 0.0
    upload_speed: float = 0.0
    progress: float = 0.0
    ratio: float = 0.0
    seed_time: float = 0.0
    added_time: Optional[datetime] = None
    site_name: str = ""
    site_url: str = ""
    torrent_url: str = ""
    page_url: str = ""
    description: str = ""
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None


@dataclass
class SearchResult:
    """搜索结果"""
    id: Optional[int] = None
    title: str = ""
    year: Optional[int] = None
    media_type: str = "unknown"
    poster: Optional[str] = None
    overview: str = ""
    torrents: List[TorrentInfo] = None

    def __post_init__(self):
        if self.torrents is None:
            self.torrents = []


@dataclass
class SearchQuery:
    """搜索查询"""
    keyword: str
    media_type: Optional[str] = None
    year: Optional[int] = None
    site: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    page: int = 1
    page_size: int = 20
