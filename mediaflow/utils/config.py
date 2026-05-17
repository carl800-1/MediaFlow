"""
配置管理模块

提供配置文件的加载、验证和管理功能
"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class AppConfig:
    """应用配置"""
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 3000
    secret_key: str = "change-me-in-production"
    log_level: str = "INFO"
    timezone: str = "Asia/Shanghai"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"
    path: str = "data/mediaflow.db"
    echo: bool = False


@dataclass
class DownloaderConfig:
    """下载器配置"""
    type: str = "qbittorrent"
    host: str = "localhost"
    port: int = 8080
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class MediaServerConfig:
    """媒体服务器配置"""
    type: str = "plex"
    host: str = "localhost"
    port: int = 32400
    api_key: Optional[str] = None


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = True
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class ConfigManager:
    """配置管理器"""

    _instance: Optional["ConfigManager"] = None
    _lock = Lock()

    def __init__(self, config_path: Optional[Union[str, Path]] = None) -> None:
        self._config_path = config_path or os.getenv("MEDIAFLOW_CONFIG", "config/config.yaml")
        self._config: dict[str, Any] = {}
        self._app_config: Optional[AppConfig] = None
        self._db_config: Optional[DatabaseConfig] = None
        self._downloader_config: Optional[DownloaderConfig] = None
        self._media_server_config: Optional[MediaServerConfig] = None
        self._notification_config: Optional[NotificationConfig] = None
        self._load_config()

    @classmethod
    def get_instance(cls, config_path: Optional[Union[str, Path]] = None) -> "ConfigManager":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config_path)
        return cls._instance

    def _load_config(self) -> None:
        """加载配置文件"""
        config_file = Path(self._config_path)
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}

    def reload(self) -> None:
        """重新加载配置"""
        self._load_config()
        self._app_config = None
        self._db_config = None
        self._downloader_config = None
        self._media_server_config = None
        self._notification_config = None

    @property
    def app(self) -> AppConfig:
        """获取应用配置"""
        if self._app_config is None:
            app_data = self._config.get("app", {})
            self._app_config = AppConfig(**{
                k: v for k, v in app_data.items()
                if k in AppConfig.__dataclass_fields__
            })
        return self._app_config

    @property
    def database(self) -> DatabaseConfig:
        """获取数据库配置"""
        if self._db_config is None:
            db_data = self._config.get("database", {})
            self._db_config = DatabaseConfig(**{
                k: v for k, v in db_data.items()
                if k in DatabaseConfig.__dataclass_fields__
            })
        return self._db_config

    @property
    def downloader(self) -> DownloaderConfig:
        """获取下载器配置"""
        if self._downloader_config is None:
            dl_data = self._config.get("downloader", {})
            self._downloader_config = DownloaderConfig(**{
                k: v for k, v in dl_data.items()
                if k in DownloaderConfig.__dataclass_fields__
            })
        return self._downloader_config

    @property
    def media_server(self) -> MediaServerConfig:
        """获取媒体服务器配置"""
        if self._media_server_config is None:
            ms_data = self._config.get("media_server", {})
            self._media_server_config = MediaServerConfig(**{
                k: v for k, v in ms_data.items()
                if k in MediaServerConfig.__dataclass_fields__
            })
        return self._media_server_config

    @property
    def notification(self) -> NotificationConfig:
        """获取通知配置"""
        if self._notification_config is None:
            notif_data = self._config.get("notification", {})
            self._notification_config = NotificationConfig(**{
                k: v for k, v in notif_data.items()
                if k in NotificationConfig.__dataclass_fields__
            })
        return self._notification_config

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._config[key] = value

    def save(self) -> None:
        """保存配置到文件"""
        config_file = Path(self._config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)


_global_config: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """获取全局配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager.get_instance()
    return _global_config
