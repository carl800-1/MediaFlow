"""
订阅信息数据模型
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SubscriptionState(Enum):
    """订阅状态"""
    ENABLED = "Y"
    DISABLED = "N"
    PAUSED = "P"


class SubscriptionType(Enum):
    """订阅类型"""
    RSS = "rss"
    TORRENT = "torrent"
    SEARCH = "search"


@dataclass
class SubscriptionInfo:
    """订阅信息"""
    id: Optional[int] = None
    name: str = ""
    media_id: Optional[int] = None
    rss_url: Optional[str] = None
    keywords: Optional[str] = None
    state: SubscriptionState = SubscriptionState.ENABLED
    subscription_type: SubscriptionType = SubscriptionType.RSS
    downloader_id: Optional[int] = None
    save_path: Optional[str] = None
    auto_download: bool = True
    filter_rule: Optional[str] = None
    interval: int = 30
    last_check_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class RSSItem:
    """RSS条目"""
    title: str
    link: str
    description: Optional[str] = None
    size: int = 0
    seeders: int = 0
    leechers: int = 0
    publish_date: Optional[datetime] = None
    enclosure: Optional[str] = None


@dataclass
class SubscriptionStatistics:
    """订阅统计"""
    total_items: int = 0
    downloaded_items: int = 0
    failed_items: int = 0
    last_check_time: Optional[datetime] = None
