"""
索引器基类

定义索引器接口规范
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import re


@dataclass
class IndexerResult:
    """索引器搜索结果"""
    title: str
    size: int
    seeders: int
    leechers: int
    download_url: str
    page_url: str
    site_name: str
    site_domain: str
    publish_date: Optional[datetime] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    free_deadline: Optional[datetime] = None
    price: Optional[float] = None
    upload_multiplier: float = 1.0
    download_multiplier: float = 1.0


@dataclass
class IndexerInfo:
    """索引器信息"""
    id: str
    name: str
    site_type: str
    base_url: str
    cookie: Optional[str] = None
    api_key: Optional[str] = None
    enabled: bool = True


class IndexerBase(ABC):
    """索引器基类"""

    def __init__(self, info: IndexerInfo) -> None:
        self.info = info
        self._session = None

    @abstractmethod
    def login(self) -> bool:
        """登录站点"""
        pass

    @abstractmethod
    def search(self, keyword: str, **kwargs) -> List[IndexerResult]:
        """搜索种子"""
        pass

    @abstractmethod
    def get_torrent_details(self, torrent_id: str) -> Optional[IndexerResult]:
        """获取种子详情"""
        pass

    def _parse_size(self, size_str: str) -> int:
        """解析文件大小字符串"""
        size_str = str(size_str).upper().strip()
        units = {
            "B": 1,
            "KB": 1024,
            "MB": 1024 ** 2,
            "GB": 1024 ** 3,
            "TB": 1024 ** 4,
        }

        for unit, multiplier in units.items():
            if unit in size_str:
                try:
                    value = float(re.sub(r"[^\d.]", "", size_str))
                    return int(value * multiplier)
                except ValueError:
                    pass
        return 0

    def _parse_number(self, num_str: str) -> int:
        """解析数字字符串"""
        try:
            return int(re.sub(r"[^\d]", "", str(num_str)))
        except ValueError:
            return 0

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _clean_title(self, title: str) -> str:
        """清理标题"""
        title = re.sub(r"\s+", " ", title)
        title = re.sub(r"\[.*?\]", "", title)
        title = re.sub(r"\(.*?\)", "", title)
        return title.strip()

    @property
    def is_logged_in(self) -> bool:
        """是否已登录"""
        return self._session is not None


class SearchOptions:
    """搜索选项"""

    def __init__(
        self,
        keyword: str,
        media_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        **kwargs
    ) -> None:
        self.keyword = keyword
        self.media_type = media_type
        self.page = page
        self.page_size = page_size
        self.site = kwargs.get("site")
        self.year = kwargs.get("year")
        self.season = kwargs.get("season")
        self.episode = kwargs.get("episode")
        self.imdb_id = kwargs.get("imdb_id")
        self.tmdb_id = kwargs.get("tmdb_id")
        self.freeleech_only = kwargs.get("freeleech_only", False)
        self.doubleup_only = kwargs.get("doubleup_only", False)
        self.hr_only = kwargs.get("hr_only", False)
