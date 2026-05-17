"""
下载器管理器

管理多个下载器实例
"""

import threading
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

from mediaflow.utils.cli import getLogger
from mediaflow.database import get_database
from mediaflow.downloader.client import BaseDownloader, DownloaderConfig, TorrentDetail


logger = getLogger("downloader")


@dataclass
class DownloaderInfo:
    """下载器信息"""
    id: int
    name: str
    type: str
    host: str
    port: int
    enabled: bool
    torrents_count: int = 0
    download_speed: float = 0.0
    upload_speed: float = 0.0


class DownloaderManager:
    """下载器管理器"""

    _instance: Optional["DownloaderManager"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._downloaders: Dict[int, BaseDownloader] = {}
        self._downloader_configs: Dict[int, DownloaderConfig] = {}
        self._db = get_database()
        self._load_downloaders()

    @classmethod
    def get_instance(cls) -> "DownloaderManager":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _load_downloaders(self) -> None:
        """从数据库加载下载器"""
        try:
            rows = self._db.fetch_all("SELECT * FROM downloaders WHERE enabled = 1")
            for row in rows:
                config = DownloaderConfig(
                    name=row["name"],
                    type=row["type"],
                    host=row["host"],
                    port=row["port"],
                    username=row.get("username"),
                    password=row.get("password"),
                    enabled=bool(row["enabled"]),
                )
                self._downloader_configs[row["id"]] = config
                self._create_downloader(row["id"], config)
            logger.info(f"已加载 {len(self._downloader_configs)} 个下载器")
        except Exception as e:
            logger.error(f"加载下载器失败: {e}")

    def _create_downloader(self, downloader_id: int, config: DownloaderConfig) -> Optional[BaseDownloader]:
        """创建下载器实例"""
        try:
            if config.type == "qbittorrent":
                from mediaflow.downloader.client import QbittorrentClient
                downloader = QbittorrentClient(config)
            elif config.type == "transmission":
                from mediaflow.downloader.client import TransmissionClient
                downloader = TransmissionClient(config)
            elif config.type == "aria2":
                from mediaflow.downloader.client import Aria2Client
                downloader = Aria2Client(config)
            else:
                logger.error(f"不支持的下载器类型: {config.type}")
                return None

            if downloader.connect():
                self._downloaders[downloader_id] = downloader
                logger.info(f"连接下载器成功: {config.name}")
                return downloader
            else:
                logger.error(f"连接下载器失败: {config.name}")
                return None
        except Exception as e:
            logger.error(f"创建下载器失败: {e}")
            return None

    def get_downloader(self, downloader_id: int) -> Optional[BaseDownloader]:
        """获取下载器实例"""
        if downloader_id not in self._downloaders:
            config = self._downloader_configs.get(downloader_id)
            if config:
                self._create_downloader(downloader_id, config)
        return self._downloaders.get(downloader_id)

    def get_downloader_info(self, downloader_id: int) -> Optional[DownloaderInfo]:
        """获取下载器信息"""
        config = self._downloader_configs.get(downloader_id)
        if not config:
            return None

        downloader = self.get_downloader(downloader_id)
        torrents_count = 0
        download_speed = 0.0
        upload_speed = 0.0

        if downloader and downloader.is_connected:
            try:
                torrents = downloader.get_torrents()
                torrents_count = len(torrents)
                download_speed, upload_speed = downloader.get_total_speed()
            except Exception as e:
                logger.error(f"获取下载器状态失败: {e}")

        return DownloaderInfo(
            id=downloader_id,
            name=config.name,
            type=config.type,
            host=config.host,
            port=config.port,
            enabled=config.enabled,
            torrents_count=torrents_count,
            download_speed=download_speed,
            upload_speed=upload_speed,
        )

    def get_all_downloaders_info(self) -> List[DownloaderInfo]:
        """获取所有下载器信息"""
        return [
            self.get_downloader_info(did)
            for did in self._downloader_configs.keys()
        ]

    def add_downloader(self, config: DownloaderConfig) -> Optional[int]:
        """添加下载器"""
        try:
            cursor = self._db.execute(
                """
                INSERT INTO downloaders (name, type, host, port, username, password, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (config.name, config.type, config.host, config.port,
                 config.username, config.password, 1 if config.enabled else 0)
            )
            downloader_id = cursor.lastrowid
            self._downloader_configs[downloader_id] = config
            self._create_downloader(downloader_id, config)
            logger.info(f"添加下载器成功: {config.name}")
            return downloader_id
        except Exception as e:
            logger.error(f"添加下载器失败: {e}")
            return None

    def update_downloader(self, downloader_id: int, config: DownloaderConfig) -> bool:
        """更新下载器"""
        try:
            self._db.execute(
                """
                UPDATE downloaders
                SET name = ?, type = ?, host = ?, port = ?,
                    username = ?, password = ?, enabled = ?
                WHERE id = ?
                """,
                (config.name, config.type, config.host, config.port,
                 config.username, config.password,
                 1 if config.enabled else 0, downloader_id)
            )
            self._downloader_configs[downloader_id] = config
            if downloader_id in self._downloaders:
                self._downloaders[downloader_id].disconnect()
            self._create_downloader(downloader_id, config)
            logger.info(f"更新下载器成功: {config.name}")
            return True
        except Exception as e:
            logger.error(f"更新下载器失败: {e}")
            return False

    def delete_downloader(self, downloader_id: int) -> bool:
        """删除下载器"""
        try:
            if downloader_id in self._downloaders:
                self._downloaders[downloader_id].disconnect()
                del self._downloaders[downloader_id]
            self._downloader_configs.pop(downloader_id, None)
            self._db.execute("DELETE FROM downloaders WHERE id = ?", (downloader_id,))
            logger.info(f"删除下载器: {downloader_id}")
            return True
        except Exception as e:
            logger.error(f"删除下载器失败: {e}")
            return False

    def refresh_connections(self) -> None:
        """刷新所有下载器连接"""
        for downloader_id, downloader in list(self._downloaders.items()):
            try:
                if not downloader.is_connected:
                    config = self._downloader_configs.get(downloader_id)
                    if config:
                        self._create_downloader(downloader_id, config)
            except Exception as e:
                logger.error(f"刷新下载器连接失败: {e}")


_global_downloader_manager: Optional[DownloaderManager] = None


def get_downloader_manager() -> DownloaderManager:
    """获取全局下载器管理器"""
    global _global_downloader_manager
    if _global_downloader_manager is None:
        _global_downloader_manager = DownloaderManager.get_instance()
    return _global_downloader_manager
