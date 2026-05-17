"""
同步任务数据模型
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SyncStatus(Enum):
    """同步状态"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncDirection(Enum):
    """同步方向"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    BIDIRECTIONAL = "bidirectional"


class SyncAction(Enum):
    """同步动作"""
    COPY = "copy"
    MOVE = "move"
    SYMLINK = "symlink"
    HARDLINK = "hardlink"


@dataclass
class SyncTask:
    """同步任务"""
    id: Optional[int] = None
    name: str = ""
    source_path: str = ""
    target_path: str = ""
    direction: SyncDirection = SyncDirection.UPLOAD
    action: SyncAction = SyncAction.COPY
    enabled: bool = True
    auto_sync: bool = True
    interval: int = 60
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    delete_orphan: bool = False
    status: SyncStatus = SyncStatus.IDLE
    last_sync_time: Optional[datetime] = None
    last_sync_result: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class SyncStatistics:
    """同步统计"""
    total_files: int = 0
    synced_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_size: int = 0
    synced_size: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    name: str
    size: int
    mtime: float
    is_dir: bool
    md5: Optional[str] = None
