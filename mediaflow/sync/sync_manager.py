"""
同步管理器

管理媒体库同步任务
"""

import threading
import time
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass

from mediaflow.utils.cli import getLogger
from mediaflow.database import get_database
from mediaflow.sync.sync import (
    SyncTask,
    SyncStatus,
    SyncDirection,
    SyncAction,
    SyncStatistics,
    FileInfo,
)


logger = getLogger("sync")


class SyncManager:
    """同步管理器"""

    _instance: Optional["SyncManager"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._tasks: Dict[int, SyncTask] = {}
        self._running_tasks: Dict[int, bool] = {}
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._db = get_database()
        self._callbacks: List[Callable[[int, SyncStatistics], None]] = []
        self._load_tasks()

    @classmethod
    def get_instance(cls) -> "SyncManager":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _load_tasks(self) -> None:
        """从数据库加载同步任务"""
        try:
            rows = self._db.fetch_all("SELECT * FROM sync_tasks WHERE enabled = 1")
            for row in rows:
                task = SyncTask(
                    id=row["id"],
                    name=row["name"],
                    source_path=row["source_path"],
                    target_path=row["target_path"],
                    direction=SyncDirection(row.get("direction", "upload")),
                    action=SyncAction(row.get("action", "copy")),
                    enabled=bool(row["enabled"]),
                    auto_sync=bool(row.get("auto_sync", True)),
                    interval=row.get("interval", 60),
                    exclude_patterns=row.get("exclude_patterns", "").split(",") if row.get("exclude_patterns") else [],
                    include_patterns=row.get("include_patterns", "").split(",") if row.get("include_patterns") else [],
                    delete_orphan=bool(row.get("delete_orphan", False)),
                    status=SyncStatus(row.get("status", "idle")),
                    last_sync_time=datetime.fromisoformat(row["last_sync_time"]) if row.get("last_sync_time") else None,
                    last_sync_result=row.get("last_sync_result"),
                )
                self._tasks[task.id] = task
            logger.info(f"已加载 {len(self._tasks)} 个同步任务")
        except Exception as e:
            logger.error(f"加载同步任务失败: {e}")

    def start(self) -> None:
        """启动同步管理器"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return

        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="SyncScheduler",
            daemon=True
        )
        self._scheduler_thread.start()
        logger.info("同步管理器已启动")

    def stop(self) -> None:
        """停止同步管理器"""
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=10)
        logger.info("同步管理器已停止")

    def _scheduler_loop(self) -> None:
        """调度器主循环"""
        while not self._stop_event.is_set():
            try:
                for task_id, task in self._tasks.items():
                    if task.auto_sync and task.status != SyncStatus.RUNNING:
                        self._execute_task(task)
            except Exception as e:
                logger.error(f"同步调度异常: {e}")
            self._stop_event.wait(timeout=60)

    def _execute_task(self, task: SyncTask) -> SyncStatistics:
        """执行同步任务"""
        if self._running_tasks.get(task.id):
            return SyncStatistics()

        self._running_tasks[task.id] = True
        task.status = SyncStatus.RUNNING
        stats = SyncStatistics(start_time=datetime.now())

        try:
            source_files = self._scan_directory(Path(task.source_path), task)
            target_files = self._scan_directory(Path(task.target_path), task)

            files_to_sync = self._calculate_diff(
                source_files,
                target_files,
                task
            )

            for file_info in files_to_sync:
                try:
                    self._sync_file(file_info, task)
                    stats.synced_files += 1
                    stats.synced_size += file_info.size
                except Exception as e:
                    logger.error(f"同步文件失败: {file_info.path} - {e}")
                    stats.failed_files += 1

            if task.delete_orphan:
                orphan_files = self._find_orphan_files(
                    target_files,
                    source_files,
                    task
                )
                for file_info in orphan_files:
                    try:
                        self._delete_file(file_info, task)
                        stats.skipped_files += 1
                    except Exception as e:
                        logger.error(f"删除孤立文件失败: {file_info.path} - {e}")

            task.status = SyncStatus.COMPLETED
            task.last_sync_time = datetime.now()
            task.last_sync_result = f"成功同步 {stats.synced_files} 个文件"
            stats.end_time = datetime.now()

        except Exception as e:
            logger.error(f"同步任务执行失败: {e}")
            task.status = SyncStatus.FAILED
            task.last_sync_result = str(e)

        finally:
            self._running_tasks[task.id] = False
            self._save_task(task)
            self._notify_callbacks(task.id, stats)

        return stats

    def _scan_directory(self, directory: Path, task: SyncTask) -> Dict[str, FileInfo]:
        """扫描目录"""
        files = {}

        if not directory.exists():
            return files

        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    relative_path = str(item.relative_to(directory))
                    if self._should_sync(relative_path, task):
                        files[relative_path] = FileInfo(
                            path=str(item),
                            name=item.name,
                            size=item.stat().st_size,
                            mtime=item.stat().st_mtime,
                            is_dir=False,
                        )
        except Exception as e:
            logger.error(f"扫描目录失败 {directory}: {e}")

        return files

    def _should_sync(self, path: str, task: SyncTask) -> bool:
        """判断文件是否应该同步"""
        for pattern in task.exclude_patterns:
            if pattern in path:
                return False

        if task.include_patterns:
            for pattern in task.include_patterns:
                if pattern in path:
                    return True
            return False

        return True

    def _calculate_diff(
        self,
        source_files: Dict[str, FileInfo],
        target_files: Dict[str, FileInfo],
        task: SyncTask
    ) -> List[FileInfo]:
        """计算需要同步的文件"""
        to_sync = []

        for path, source_info in source_files.items():
            target_info = target_files.get(path)
            if target_info is None:
                to_sync.append(source_info)
            elif source_info.mtime > target_info.mtime:
                to_sync.append(source_info)
            elif source_info.size != target_info.size:
                to_sync.append(source_info)

        return to_sync

    def _find_orphan_files(
        self,
        target_files: Dict[str, FileInfo],
        source_files: Dict[str, FileInfo],
        task: SyncTask
    ) -> List[FileInfo]:
        """查找孤立文件"""
        orphans = []
        for path, target_info in target_files.items():
            if path not in source_files:
                orphans.append(target_info)
        return orphans

    def _sync_file(self, file_info: FileInfo, task: SyncTask) -> None:
        """同步单个文件"""
        source = Path(file_info.path)
        target_path = Path(task.target_path) / source.relative_to(Path(task.source_path))
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if task.action == SyncAction.COPY:
            shutil.copy2(source, target_path)
        elif task.action == SyncAction.MOVE:
            shutil.move(str(source), target_path)
        elif task.action == SyncAction.SYMLINK:
            if target_path.exists():
                target_path.unlink()
            target_path.symlink_to(source)
        elif task.action == SyncAction.HARDLINK:
            if target_path.exists():
                target_path.unlink()
            source.link_to(target_path)

    def _delete_file(self, file_info: FileInfo, task: SyncTask) -> None:
        """删除文件"""
        if task.direction == SyncDirection.DOWNLOAD:
            Path(file_info.path).unlink(missing_ok=True)

    def _save_task(self, task: SyncTask) -> None:
        """保存任务状态"""
        try:
            self._db.execute(
                """
                UPDATE sync_tasks
                SET status = ?, last_sync_time = ?, last_sync_result = ?
                WHERE id = ?
                """,
                (
                    task.status.value,
                    task.last_sync_time.isoformat() if task.last_sync_time else None,
                    task.last_sync_result,
                    task.id,
                )
            )
        except Exception as e:
            logger.error(f"保存任务状态失败: {e}")

    def add_callback(self, callback: Callable[[int, SyncStatistics], None]) -> None:
        """添加同步完成回调"""
        self._callbacks.append(callback)

    def _notify_callbacks(self, task_id: int, stats: SyncStatistics) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(task_id, stats)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")

    def get_task(self, task_id: int) -> Optional[SyncTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[SyncTask]:
        """获取所有任务"""
        return list(self._tasks.values())

    def sync_task(self, task_id: int) -> SyncStatistics:
        """手动执行同步"""
        task = self._tasks.get(task_id)
        if not task:
            return SyncStatistics()
        return self._execute_task(task)

    def create_task(self, task: SyncTask) -> Optional[int]:
        """创建任务"""
        try:
            cursor = self._db.execute(
                """
                INSERT INTO sync_tasks
                (name, source_path, target_path, direction, action,
                 enabled, auto_sync, interval, exclude_patterns, include_patterns,
                 delete_orphan)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.name,
                    task.source_path,
                    task.target_path,
                    task.direction.value,
                    task.action.value,
                    1 if task.enabled else 0,
                    1 if task.auto_sync else 0,
                    task.interval,
                    ",".join(task.exclude_patterns),
                    ",".join(task.include_patterns),
                    1 if task.delete_orphan else 0,
                )
            )
            task_id = cursor.lastrowid
            task.id = task_id
            self._tasks[task_id] = task
            logger.info(f"创建同步任务成功: {task.name}")
            return task_id
        except Exception as e:
            logger.error(f"创建同步任务失败: {e}")
            return None

    def update_task(self, task_id: int, task: SyncTask) -> bool:
        """更新任务"""
        try:
            self._db.execute(
                """
                UPDATE sync_tasks
                SET name = ?, source_path = ?, target_path = ?,
                    direction = ?, action = ?, enabled = ?,
                    auto_sync = ?, interval = ?,
                    exclude_patterns = ?, include_patterns = ?,
                    delete_orphan = ?
                WHERE id = ?
                """,
                (
                    task.name,
                    task.source_path,
                    task.target_path,
                    task.direction.value,
                    task.action.value,
                    1 if task.enabled else 0,
                    1 if task.auto_sync else 0,
                    task.interval,
                    ",".join(task.exclude_patterns),
                    ",".join(task.include_patterns),
                    1 if task.delete_orphan else 0,
                    task_id,
                )
            )
            self._tasks[task_id] = task
            logger.info(f"更新同步任务成功: {task.name}")
            return True
        except Exception as e:
            logger.error(f"更新同步任务失败: {e}")
            return False

    def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        try:
            self._tasks.pop(task_id, None)
            self._db.execute("DELETE FROM sync_tasks WHERE id = ?", (task_id,))
            logger.info(f"删除同步任务: {task_id}")
            return True
        except Exception as e:
            logger.error(f"删除同步任务失败: {e}")
            return False


_global_sync_manager: Optional[SyncManager] = None


def get_sync_manager() -> SyncManager:
    """获取全局同步管理器"""
    global _global_sync_manager
    if _global_sync_manager is None:
        _global_sync_manager = SyncManager.get_instance()
    return _global_sync_manager
