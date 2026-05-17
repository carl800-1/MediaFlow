"""
刷流任务管理器

负责刷流任务的调度、执行和监控
"""

import time
import threading
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field

from mediaflow.utils.cli import getLogger
from mediaflow.utils.config import get_config
from mediaflow.database import get_database
from mediaflow.brushtask.task import (
    BrushTaskConfig,
    BrushTaskState,
    BrushStatistics,
    TorrentInfo,
    FilterRule,
    parse_filter_rule
)
from mediaflow.downloader import get_downloader_manager
from mediaflow.sites import SiteManager


logger = getLogger("brushtask")


@dataclass
class TaskExecutionResult:
    """任务执行结果"""
    task_id: int
    success: bool
    downloaded: int = 0
    failed: int = 0
    deleted: int = 0
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class BrushTaskManager:
    """刷流任务管理器"""

    _instance: Optional["BrushTaskManager"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._tasks: Dict[int, BrushTaskConfig] = {}
        self._running_tasks: Dict[int, bool] = {}
        self._statistics: Dict[int, BrushStatistics] = {}
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._db = get_database()
        self._site_manager = SiteManager()
        self._downloader_manager = get_downloader_manager()
        self._callbacks: List[Callable[[TaskExecutionResult], None]] = []
        self._load_tasks()

    @classmethod
    def get_instance(cls) -> "BrushTaskManager":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _load_tasks(self) -> None:
        """从数据库加载刷流任务"""
        try:
            tasks = self._db.fetch_all(
                "SELECT * FROM brush_tasks WHERE enabled = 1"
            )
            for task_data in tasks:
                task = BrushTaskConfig(
                    id=task_data["id"],
                    name=task_data["name"],
                    site_id=task_data["site_id"],
                    downloader_id=task_data["downloader_id"],
                    interval=task_data["interval"],
                    state=BrushTaskState(task_data["state"]),
                    filter_rule=task_data["filter_rule"],
                    enabled=bool(task_data["enabled"]),
                )
                self._tasks[task.id] = task
                self._statistics[task.id] = BrushStatistics()
            logger.info(f"已加载 {len(self._tasks)} 个刷流任务")
        except Exception as e:
            logger.error(f"加载刷流任务失败: {e}")

    def start(self) -> None:
        """启动任务管理器"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            logger.warning("刷流任务管理器已在运行")
            return

        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="BrushTaskScheduler",
            daemon=True
        )
        self._scheduler_thread.start()
        logger.info("刷流任务管理器已启动")

    def stop(self) -> None:
        """停止任务管理器"""
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=10)
        logger.info("刷流任务管理器已停止")

    def _scheduler_loop(self) -> None:
        """调度器主循环"""
        while not self._stop_event.is_set():
            try:
                for task_id, task in self._tasks.items():
                    if task.state == BrushTaskState.RUNNING:
                        self._execute_task(task)
            except Exception as e:
                logger.error(f"调度器执行异常: {e}")
            self._stop_event.wait(timeout=60)

    def _execute_task(self, task: BrushTaskConfig) -> None:
        """执行单个刷流任务"""
        try:
            if self._running_tasks.get(task.id):
                return

            self._running_tasks[task.id] = True
            logger.info(f"开始执行刷流任务: {task.name}")

            site = self._site_manager.get_site(task.site_id)
            if not site:
                logger.error(f"站点不存在: {task.site_id}")
                return

            filter_rule = parse_filter_rule(task.filter_rule) if task.filter_rule else None

            rss_items = self._fetch_rss_items(site, filter_rule)
            if not rss_items:
                logger.info(f"任务 {task.name} 未获取到种子")
                return

            result = self._process_torrents(task, rss_items)
            self._notify_callbacks(result)

            logger.info(
                f"任务 {task.name} 执行完成: "
                f"下载 {result.downloaded}, 失败 {result.failed}, 删除 {result.deleted}"
            )
        except Exception as e:
            logger.error(f"执行任务 {task.name} 失败: {e}")
        finally:
            self._running_tasks[task.id] = False

    def _fetch_rss_items(self, site: Any, filter_rule: Optional[FilterRule]) -> List[Dict[str, Any]]:
        """获取RSS条目"""
        try:
            rss_url = site.rss_url
            if not rss_url:
                logger.warning(f"站点 {site.name} 未配置RSS地址")
                return []

            import feedparser
            feed = feedparser.parse(rss_url, request_headers={"Cookie": site.cookie})

            items = []
            for entry in feed.entries:
                item = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "size": self._parse_size(entry.get("size", "0")),
                    "seeders": self._parse_number(entry.get("seeders", "0")),
                    "leechers": self._parse_number(entry.get("leechers", "0")),
                }

                if filter_rule:
                    if not self._match_filter(item, filter_rule):
                        continue

                items.append(item)

            return items
        except Exception as e:
            logger.error(f"获取RSS失败: {e}")
            return []

    def _match_filter(self, item: Dict[str, Any], rule: FilterRule) -> bool:
        """匹配过滤规则"""
        title = item.get("title", "").lower()

        if rule.exclude_keywords:
            for keyword in rule.exclude_keywords:
                if keyword.lower() in title:
                    return False

        if rule.include_keywords:
            if not any(kw.lower() in title for kw in rule.include_keywords):
                return False

        if rule.size_min and item.get("size", 0) < rule.size_min:
            return False
        if rule.size_max and item.get("size", 0) > rule.size_max:
            return False

        if item.get("seeders", 0) < rule.seeders_min:
            return False

        return True

    def _parse_size(self, size_str: str) -> int:
        """解析文件大小"""
        size_str = str(size_str).upper().strip()
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}

        for unit, multiplier in units.items():
            if unit in size_str:
                try:
                    value = float(size_str.replace(unit, "").strip())
                    return int(value * multiplier)
                except ValueError:
                    pass
        return 0

    def _parse_number(self, num_str: str) -> int:
        """解析数字"""
        try:
            return int(num_str)
        except ValueError:
            return 0

    def _process_torrents(self, task: BrushTaskConfig, items: List[Dict[str, Any]]) -> TaskExecutionResult:
        """处理种子列表"""
        result = TaskExecutionResult(task_id=task.id, success=True)

        for item in items:
            try:
                downloader = self._downloader_manager.get_downloader(task.downloader_id)
                if not downloader:
                    continue

                success = downloader.add_torrent(
                    url=item.get("link"),
                    title=item.get("title"),
                )

                if success:
                    result.downloaded += 1
                    self._statistics[task.id].total_downloaded += 1
                else:
                    result.failed += 1
                    self._statistics[task.id].total_failed += 1

            except Exception as e:
                logger.error(f"添加种子失败: {e}")
                result.failed += 1

        return result

    def add_callback(self, callback: Callable[[TaskExecutionResult], None]) -> None:
        """添加执行结果回调"""
        self._callbacks.append(callback)

    def _notify_callbacks(self, result: TaskExecutionResult) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")

    def get_statistics(self, task_id: int) -> Optional[BrushStatistics]:
        """获取任务统计"""
        return self._statistics.get(task_id)

    def get_all_statistics(self) -> Dict[int, BrushStatistics]:
        """获取所有任务统计"""
        return self._statistics.copy()

    def create_task(self, config: BrushTaskConfig) -> Optional[int]:
        """创建新任务"""
        try:
            cursor = self._db.execute(
                """
                INSERT INTO brush_tasks (name, site_id, downloader_id, interval, state, filter_rule, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    config.name,
                    config.site_id,
                    config.downloader_id,
                    config.interval,
                    config.state.value,
                    config.filter_rule,
                    1 if config.enabled else 0,
                )
            )
            task_id = cursor.lastrowid
            config.id = task_id
            self._tasks[task_id] = config
            self._statistics[task_id] = BrushStatistics()
            logger.info(f"创建刷流任务成功: {config.name}")
            return task_id
        except Exception as e:
            logger.error(f"创建刷流任务失败: {e}")
            return None

    def update_task(self, task_id: int, config: BrushTaskConfig) -> bool:
        """更新任务"""
        try:
            self._db.execute(
                """
                UPDATE brush_tasks
                SET name = ?, site_id = ?, downloader_id = ?, interval = ?,
                    state = ?, filter_rule = ?, enabled = ?
                WHERE id = ?
                """,
                (
                    config.name,
                    config.site_id,
                    config.downloader_id,
                    config.interval,
                    config.state.value,
                    config.filter_rule,
                    1 if config.enabled else 0,
                    task_id,
                )
            )
            self._tasks[task_id] = config
            logger.info(f"更新刷流任务成功: {config.name}")
            return True
        except Exception as e:
            logger.error(f"更新刷流任务失败: {e}")
            return False

    def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        try:
            self._db.execute("DELETE FROM brush_tasks WHERE id = ?", (task_id,))
            self._tasks.pop(task_id, None)
            self._statistics.pop(task_id, None)
            logger.info(f"删除刷流任务: {task_id}")
            return True
        except Exception as e:
            logger.error(f"删除刷流任务失败: {e}")
            return False

    def start_task(self, task_id: int) -> bool:
        """启动任务"""
        if task_id in self._tasks:
            self._tasks[task_id].state = BrushTaskState.RUNNING
            self._db.execute(
                "UPDATE brush_tasks SET state = ? WHERE id = ?",
                (BrushTaskState.RUNNING.value, task_id)
            )
            logger.info(f"启动刷流任务: {self._tasks[task_id].name}")
            return True
        return False

    def stop_task(self, task_id: int) -> bool:
        """停止任务"""
        if task_id in self._tasks:
            self._tasks[task_id].state = BrushTaskState.STOPPED
            self._db.execute(
                "UPDATE brush_tasks SET state = ? WHERE id = ?",
                (BrushTaskState.STOPPED.value, task_id)
            )
            logger.info(f"停止刷流任务: {self._tasks[task_id].name}")
            return True
        return False

    def get_tasks(self) -> List[BrushTaskConfig]:
        """获取所有任务"""
        return list(self._tasks.values())

    def get_task(self, task_id: int) -> Optional[BrushTaskConfig]:
        """获取指定任务"""
        return self._tasks.get(task_id)


_global_brush_task_manager: Optional[BrushTaskManager] = None


def get_brush_task_manager() -> BrushTaskManager:
    """获取全局刷流任务管理器"""
    global _global_brush_task_manager
    if _global_brush_task_manager is None:
        _global_brush_task_manager = BrushTaskManager.get_instance()
    return _global_brush_task_manager
