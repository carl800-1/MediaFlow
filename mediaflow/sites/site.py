"""
站点信息数据模型
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class SiteInfo:
    """站点信息"""
    id: int
    name: str
    url: str
    cookie: Optional[str] = None
    sign_url: Optional[str] = None
    rss_url: Optional[str] = None
    enabled: bool = True
    user_class: Optional[str] = None
    user_level: int = 0
    bonus: Optional[float] = None
    upload: Optional[int] = None
    download: Optional[int] = None
    ratio: Optional[float] = None
    seeding: int = 0
    leeching: int = 0
    uploaded_size: int = 0
    downloaded_size: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class SiteStatistics:
    """站点统计"""
    total_sites: int = 0
    enabled_sites: int = 0
    total_upload: int = 0
    total_download: int = 0
    total_seeding: int = 0


@dataclass
class SignInResult:
    """签到结果"""
    site_name: str
    success: bool
    message: str
    bonus: Optional[float] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
