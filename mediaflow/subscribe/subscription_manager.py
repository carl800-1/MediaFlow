"""
订阅管理器

管理RSS订阅和自动下载
"""

import threading
import feedparser
from typing import Dict, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass

from mediaflow.utils.cli import getLogger
from mediaflow.database import get_database
from mediaflow.subscribe.subscription import (
    SubscriptionInfo,
    SubscriptionState,
    SubscriptionType,
    RSSItem,
    SubscriptionStatistics
)
from mediaflow.downloader import get_downloader_manager


logger = getLogger("subscribe")


@dataclass
class RSSFetchResult:
    """RSS获取结果"""
    subscription_id: int
    success: bool
    items: List[RSSItem]
    message: str = ""


class SubscriptionManager:
    """订阅管理器"""

    _instance: Optional["SubscriptionManager"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._subscriptions: Dict[int, SubscriptionInfo] = {}
        self._statistics: Dict[int, SubscriptionStatistics] = {}
        self._db = get_database()
        self._downloader_manager = get_downloader_manager()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._callbacks: List[Callable[[RSSItem], None]] = []
        self._load_subscriptions()

    @classmethod
    def get_instance(cls) -> "SubscriptionManager":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _load_subscriptions(self) -> None:
        """从数据库加载订阅"""
        try:
            rows = self._db.fetch_all("SELECT * FROM subscriptions")
            for row in rows:
                sub = SubscriptionInfo(
                    id=row["id"],
                    name=row["name"],
                    media_id=row.get("media_id"),
                    rss_url=row.get("rss_url"),
                    keywords=row.get("keywords"),
                    state=SubscriptionState(row.get("state", "Y")),
                    downloader_id=row.get("downloader_id"),
                    save_path=row.get("save_path"),
                    auto_download=bool(row.get("auto_download", True)),
                    filter_rule=row.get("filter_rule"),
                    interval=row.get("interval", 30),
                )
                self._subscriptions[sub.id] = sub
                self._statistics[sub.id] = SubscriptionStatistics()
            logger.info(f"已加载 {len(self._subscriptions)} 个订阅")
        except Exception as e:
            logger.error(f"加载订阅失败: {e}")

    def start(self) -> None:
        """启动订阅管理器"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return

        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="SubscriptionScheduler",
            daemon=True
        )
        self._scheduler_thread.start()
        logger.info("订阅管理器已启动")

    def stop(self) -> None:
        """停止订阅管理器"""
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=10)
        logger.info("订阅管理器已停止")

    def _scheduler_loop(self) -> None:
        """调度器主循环"""
        while not self._stop_event.is_set():
            try:
                for sub_id, sub in self._subscriptions.items():
                    if sub.state == SubscriptionState.ENABLED:
                        self._check_subscription(sub)
            except Exception as e:
                logger.error(f"订阅调度异常: {e}")
            self._stop_event.wait(timeout=60)

    def _check_subscription(self, sub: SubscriptionInfo) -> None:
        """检查单个订阅"""
        try:
            result = self.fetch_rss(sub)
            if result.success:
                sub.last_check_time = datetime.now()
                for item in result.items:
                    if sub.auto_download:
                        self._download_item(sub, item)
                    self._notify_callbacks(item)
        except Exception as e:
            logger.error(f"检查订阅失败: {e}")

    def fetch_rss(self, subscription: SubscriptionInfo) -> RSSFetchResult:
        """
        获取RSS内容

        Args:
            subscription: 订阅信息

        Returns:
            RSS获取结果
        """
        if not subscription.rss_url:
            return RSSFetchResult(
                subscription_id=subscription.id,
                success=False,
                items=[],
                message="未配置RSS URL"
            )

        try:
            feed = feedparser.parse(subscription.rss_url)
            items = []

            for entry in feed.entries:
                item = RSSItem(
                    title=entry.get("title", ""),
                    link=entry.get("link", ""),
                    description=entry.get("description", ""),
                    publish_date=datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") else None,
                )

                if hasattr(entry, "enclosures") and entry.enclosures:
                    item.enclosure = entry.enclosures[0].get("href")

                if hasattr(entry, "size"):
                    item.size = int(entry.size)
                elif hasattr(entry, "links"):
                    for link in entry.links:
                        if link.get("type", "").startswith("application/x-bittorrent"):
                            item.enclosure = link.get("href", "")
                            break

                items.append(item)

            logger.info(f"获取订阅 {subscription.name} RSS成功，共 {len(items)} 条")
            return RSSFetchResult(
                subscription_id=subscription.id,
                success=True,
                items=items
            )
        except Exception as e:
            logger.error(f"获取RSS失败: {e}")
            return RSSFetchResult(
                subscription_id=subscription.id,
                success=False,
                items=[],
                message=str(e)
            )

    def _download_item(self, subscription: SubscriptionInfo, item: RSSItem) -> bool:
        """下载RSS条目"""
        try:
            downloader = self._downloader_manager.get_downloader(
                subscription.downloader_id
            )
            if not downloader:
                logger.error(f"下载器不存在: {subscription.downloader_id}")
                return False

            success = downloader.add_torrent(
                url=item.enclosure or item.link,
                save_path=subscription.save_path
            )

            if success:
                self._statistics[subscription.id].downloaded_items += 1
                logger.info(f"下载成功: {item.title}")
            else:
                self._statistics[subscription.id].failed_items += 1
                logger.error(f"下载失败: {item.title}")

            return success
        except Exception as e:
            logger.error(f"下载异常: {e}")
            return False

    def add_callback(self, callback: Callable[[RSSItem], None]) -> None:
        """添加RSS条目回调"""
        self._callbacks.append(callback)

    def _notify_callbacks(self, item: RSSItem) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(item)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")

    def get_subscription(self, subscription_id: int) -> Optional[SubscriptionInfo]:
        """获取指定订阅"""
        return self._subscriptions.get(subscription_id)

    def get_all_subscriptions(self) -> List[SubscriptionInfo]:
        """获取所有订阅"""
        return list(self._subscriptions.values())

    def get_enabled_subscriptions(self) -> List[SubscriptionInfo]:
        """获取已启用的订阅"""
        return [
            sub for sub in self._subscriptions.values()
            if sub.state == SubscriptionState.ENABLED
        ]

    def get_statistics(self, subscription_id: int) -> Optional[SubscriptionStatistics]:
        """获取订阅统计"""
        return self._statistics.get(subscription_id)

    def create_subscription(self, subscription: SubscriptionInfo) -> Optional[int]:
        """创建订阅"""
        try:
            cursor = self._db.execute(
                """
                INSERT INTO subscriptions
                (name, media_id, rss_url, keywords, state, downloader_id,
                 save_path, auto_download, filter_rule, interval)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subscription.name,
                    subscription.media_id,
                    subscription.rss_url,
                    subscription.keywords,
                    subscription.state.value,
                    subscription.downloader_id,
                    subscription.save_path,
                    1 if subscription.auto_download else 0,
                    subscription.filter_rule,
                    subscription.interval,
                )
            )
            sub_id = cursor.lastrowid
            subscription.id = sub_id
            self._subscriptions[sub_id] = subscription
            self._statistics[sub_id] = SubscriptionStatistics()
            logger.info(f"创建订阅成功: {subscription.name}")
            return sub_id
        except Exception as e:
            logger.error(f"创建订阅失败: {e}")
            return None

    def update_subscription(self, subscription_id: int, subscription: SubscriptionInfo) -> bool:
        """更新订阅"""
        try:
            self._db.execute(
                """
                UPDATE subscriptions
                SET name = ?, media_id = ?, rss_url = ?, keywords = ?,
                    state = ?, downloader_id = ?, save_path = ?,
                    auto_download = ?, filter_rule = ?, interval = ?
                WHERE id = ?
                """,
                (
                    subscription.name,
                    subscription.media_id,
                    subscription.rss_url,
                    subscription.keywords,
                    subscription.state.value,
                    subscription.downloader_id,
                    subscription.save_path,
                    1 if subscription.auto_download else 0,
                    subscription.filter_rule,
                    subscription.interval,
                    subscription_id,
                )
            )
            self._subscriptions[subscription_id] = subscription
            logger.info(f"更新订阅成功: {subscription.name}")
            return True
        except Exception as e:
            logger.error(f"更新订阅失败: {e}")
            return False

    def delete_subscription(self, subscription_id: int) -> bool:
        """删除订阅"""
        try:
            self._subscriptions.pop(subscription_id, None)
            self._statistics.pop(subscription_id, None)
            self._db.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
            logger.info(f"删除订阅: {subscription_id}")
            return True
        except Exception as e:
            logger.error(f"删除订阅失败: {e}")
            return False

    def enable_subscription(self, subscription_id: int) -> bool:
        """启用订阅"""
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id].state = SubscriptionState.ENABLED
            self._db.execute(
                "UPDATE subscriptions SET state = ? WHERE id = ?",
                (SubscriptionState.ENABLED.value, subscription_id)
            )
            logger.info(f"启用订阅: {subscription_id}")
            return True
        return False

    def disable_subscription(self, subscription_id: int) -> bool:
        """禁用订阅"""
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id].state = SubscriptionState.DISABLED
            self._db.execute(
                "UPDATE subscriptions SET state = ? WHERE id = ?",
                (SubscriptionState.DISABLED.value, subscription_id)
            )
            logger.info(f"禁用订阅: {subscription_id}")
            return True
        return False


_global_subscription_manager: Optional[SubscriptionManager] = None


def get_subscription_manager() -> SubscriptionManager:
    """获取全局订阅管理器"""
    global _global_subscription_manager
    if _global_subscription_manager is None:
        _global_subscription_manager = SubscriptionManager.get_instance()
    return _global_subscription_manager
