"""
媒体服务器管理器
"""

import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from mediaflow.utils.cli import getLogger
from mediaflow.database import get_database
from mediaflow.mediaserver.client import (
    MediaServerClient,
    MediaItem,
    LibraryInfo,
    ServerInfo,
    JellyfinClient,
    PlexClient,
    EmbyClient,
    UGreenClient,
)


logger = getLogger("mediaserver")


@dataclass
class MediaServerConfig:
    """媒体服务器配置"""
    id: int
    name: str
    server_type: str
    host: str
    port: int
    api_key: str
    username: Optional[str] = None
    enabled: bool = True
    auto_refresh: bool = False
    refresh_interval: int = 3600


class MediaServerManager:
    """媒体服务器管理器"""

    _instance: Optional["MediaServerManager"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._servers: Dict[int, Dict[str, Any]] = {}
        self._clients: Dict[int, MediaServerClient] = {}
        self._db = get_database()
        self._load_servers()

    @classmethod
    def get_instance(cls) -> "MediaServerManager":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _load_servers(self) -> None:
        """从数据库加载服务器配置"""
        try:
            rows = self._db.fetch_all("SELECT * FROM media_servers WHERE enabled = 1")
            for row in rows:
                config = MediaServerConfig(
                    id=row["id"],
                    name=row["name"],
                    server_type=row["server_type"],
                    host=row["host"],
                    port=row["port"],
                    api_key=row["api_key"],
                    username=row.get("username"),
                    enabled=bool(row["enabled"]),
                )
                self._servers[config.id] = config
                self._connect_server(config)
            logger.info(f"已加载 {len(self._servers)} 个媒体服务器")
        except Exception as e:
            logger.error(f"加载媒体服务器失败: {e}")

    def _connect_server(self, config: MediaServerConfig) -> bool:
        """连接服务器"""
        try:
            client = self._create_client(config)
            if client.connect():
                self._clients[config.id] = client
                logger.info(f"连接媒体服务器成功: {config.name}")
                return True
        except Exception as e:
            logger.error(f"连接媒体服务器失败: {config.name} - {e}")
        return False

    def _create_client(self, config: MediaServerConfig) -> MediaServerClient:
        """创建客户端"""
        if config.server_type == "jellyfin":
            return JellyfinClient(
                host=config.host,
                port=config.port,
                api_key=config.api_key,
                username=config.username
            )
        elif config.server_type == "plex":
            return PlexClient(
                host=config.host,
                port=config.port,
                api_key=config.api_key,
                username=config.username
            )
        elif config.server_type == "emby":
            return EmbyClient(
                host=config.host,
                port=config.port,
                api_key=config.api_key,
                username=config.username
            )
        elif config.server_type == "ugreen":
            return UGreenClient(
                host=config.host,
                port=config.port,
                api_key=config.api_key,
                username=config.username,
                password=config.api_key
            )
        else:
            raise ValueError(f"不支持的服务器类型: {config.server_type}")

    def add_server(self, config: MediaServerConfig) -> Optional[int]:
        """添加服务器"""
        try:
            cursor = self._db.execute(
                """
                INSERT INTO media_servers (name, server_type, host, port, api_key, username, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (config.name, config.server_type, config.host, config.port,
                 config.api_key, config.username, 1 if config.enabled else 0)
            )
            server_id = cursor.lastrowid
            config.id = server_id
            self._servers[server_id] = config

            if config.enabled:
                self._connect_server(config)

            logger.info(f"添加媒体服务器: {config.name}")
            return server_id
        except Exception as e:
            logger.error(f"添加媒体服务器失败: {e}")
            return None

    def update_server(self, server_id: int, config: MediaServerConfig) -> bool:
        """更新服务器"""
        try:
            self._db.execute(
                """
                UPDATE media_servers
                SET name = ?, server_type = ?, host = ?, port = ?,
                    api_key = ?, username = ?, enabled = ?
                WHERE id = ?
                """,
                (config.name, config.server_type, config.host, config.port,
                 config.api_key, config.username,
                 1 if config.enabled else 0, server_id)
            )
            self._servers[server_id] = config

            if server_id in self._clients:
                self._clients[server_id].disconnect()
                del self._clients[server_id]

            if config.enabled:
                self._connect_server(config)

            logger.info(f"更新媒体服务器: {config.name}")
            return True
        except Exception as e:
            logger.error(f"更新媒体服务器失败: {e}")
            return False

    def delete_server(self, server_id: int) -> bool:
        """删除服务器"""
        try:
            if server_id in self._clients:
                self._clients[server_id].disconnect()
                del self._clients[server_id]

            self._servers.pop(server_id, None)
            self._db.execute("DELETE FROM media_servers WHERE id = ?", (server_id,))
            logger.info(f"删除媒体服务器: {server_id}")
            return True
        except Exception as e:
            logger.error(f"删除媒体服务器失败: {e}")
            return False

    def get_server(self, server_id: int) -> Optional[MediaServerConfig]:
        """获取服务器配置"""
        return self._servers.get(server_id)

    def get_all_servers(self) -> List[MediaServerConfig]:
        """获取所有服务器"""
        return list(self._servers.values())

    def get_client(self, server_id: int) -> Optional[MediaServerClient]:
        """获取客户端"""
        if server_id not in self._clients:
            config = self._servers.get(server_id)
            if config and config.enabled:
                self._connect_server(config)
        return self._clients.get(server_id)

    def get_server_info(self, server_id: int) -> Optional[ServerInfo]:
        """获取服务器信息"""
        client = self.get_client(server_id)
        if client:
            return client.get_server_info()
        return None

    def get_libraries(self, server_id: int) -> List[LibraryInfo]:
        """获取媒体库列表"""
        client = self.get_client(server_id)
        if client:
            return client.get_libraries()
        return []

    def get_items(self, server_id: int, library_id: str = None, media_type: str = None) -> List[MediaItem]:
        """获取媒体项目"""
        client = self.get_client(server_id)
        if client:
            return client.get_items(library_id, media_type)
        return []

    def search_media(self, server_id: int, keyword: str, media_type: str = None) -> List[MediaItem]:
        """搜索媒体"""
        client = self.get_client(server_id)
        if client:
            return client.search_media(keyword, media_type)
        return []

    def refresh_library(self, server_id: int, library_id: str = None) -> bool:
        """刷新媒体库"""
        client = self.get_client(server_id)
        if client:
            return client.refresh_library(library_id)
        return False

    def sync_to_media_server(self, server_id: int, media_info: Dict) -> bool:
        """同步到媒体服务器"""
        client = self.get_client(server_id)
        if not client:
            return False

        try:
            title = media_info.get("title", "")
            year = media_info.get("year")
            media_type = media_info.get("media_type", "movie")
            file_path = media_info.get("file_path")

            if not title or not file_path:
                return False

            search_results = client.search_media(title, media_type)
            for item in search_results:
                if item.year and year and abs(item.year - year) <= 1:
                    logger.info(f"找到匹配的媒体: {item.title}")
                    return True

            logger.warning(f"未找到匹配的媒体: {title}")
            return False
        except Exception as e:
            logger.error(f"同步到媒体服务器失败: {e}")
            return False


_global_media_server_manager: Optional[MediaServerManager] = None


def get_media_server_manager() -> MediaServerManager:
    """获取全局媒体服务器管理器"""
    global _global_media_server_manager
    if _global_media_server_manager is None:
        _global_media_server_manager = MediaServerManager.get_instance()
    return _global_media_server_manager
