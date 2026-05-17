"""
索引器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class TorrentResult:
    """种子搜索结果"""
    title: str
    size: int
    seeders: int
    leechers: int
    download_url: str
    info_page: str
    indexer: str
    category: str = ""
    pubdate: Optional[datetime] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    free_deadline: Optional[datetime] = None
    upload_multiplier: float = 1.0
    download_multiplier: float = 1.0
    download_volume_factor: float = 1.0
    upload_volume_factor: float = 1.0
    tags: List[str] = field(default_factory=list)
    files: int = 0
    description: Optional[str] = None


@dataclass
class IndexerConfig:
    """索引器配置"""
    id: int
    name: str
    indexer_type: str
    url: str
    api_key: Optional[str] = None
    enabled: bool = True
    timeout: int = 30


class IndexerBase(ABC):
    """索引器基类"""

    def __init__(self, config: IndexerConfig) -> None:
        self.config = config

    @abstractmethod
    def search(self, keyword: str, **kwargs) -> List[TorrentResult]:
        """搜索种子"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """测试连接"""
        pass

    def parse_size(self, size_str: str) -> int:
        """解析大小"""
        if not size_str:
            return 0

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
                    value = float("".join(filter(lambda x: x.isdigit() or x == ".", size_str)))
                    return int(value * multiplier)
                except ValueError:
                    return 0
        return 0

    def parse_number(self, num_str: str) -> int:
        """解析数字"""
        if not num_str:
            return 0
        try:
            return int("".join(filter(str.isdigit, str(num_str))))
        except ValueError:
            return 0
