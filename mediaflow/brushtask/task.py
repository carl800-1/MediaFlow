"""
刷流任务数据模型
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class BrushTaskState(Enum):
    """刷流任务状态"""
    RUNNING = "Y"
    STOPPED = "S"
    PAUSED = "P"


class DeleteType(Enum):
    """删除类型"""
    TIME = "time"
    RATIO = "ratio"
    SEED_TIME = "seed_time"
    SEEDERS = "seeders"
    MANUAL = "manual"


@dataclass
class BrushTaskConfig:
    """刷流任务配置"""
    id: Optional[int] = None
    name: str = "默认刷流任务"
    site_id: int = 0
    downloader_id: int = 0
    interval: str = "30"
    state: BrushTaskState = BrushTaskState.STOPPED
    filter_rule: Optional[str] = None
    delete_type: DeleteType = DeleteType.TIME
    delete_value: int = 72
    download_limit: Optional[float] = None
    upload_limit: Optional[float] = None
    enabled: bool = True
    max_download_count: int = 0
    free_limit_enabled: bool = False
    free_limit_hours: int = 0
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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


@dataclass
class BrushStatistics:
    """刷流统计"""
    total_downloaded: int = 0
    total_uploaded: int = 0
    total_seeding: int = 0
    total_deleted: int = 0
    total_failed: int = 0
    current_download_speed: float = 0.0
    current_upload_speed: float = 0.0
    total_size_downloaded: int = 0
    total_size_uploaded: int = 0


@dataclass
class FilterRule:
    """过滤规则"""
    name: str
    size_min: Optional[int] = None
    size_max: Optional[int] = None
    seeders_min: int = 0
    leechers_min: int = 0
    include_keywords: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    free_only: bool = False
    hr_only: bool = False


def parse_filter_rule(rule_json: str) -> FilterRule:
    """解析过滤规则JSON"""
    import json
    try:
        rule_dict = json.loads(rule_json)
        return FilterRule(
            name=rule_dict.get("name", ""),
            size_min=rule_dict.get("size_min"),
            size_max=rule_dict.get("size_max"),
            seeders_min=rule_dict.get("seeders_min", 0),
            leechers_min=rule_dict.get("leechers_min", 0),
            include_keywords=rule_dict.get("include_keywords", []),
            exclude_keywords=rule_dict.get("exclude_keywords", []),
            free_only=rule_dict.get("free_only", False),
            hr_only=rule_dict.get("hr_only", False),
        )
    except Exception:
        return FilterRule(name="默认规则")
