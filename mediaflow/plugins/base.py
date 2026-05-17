"""
插件基类

定义插件接口规范
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from datetime import datetime


class PluginType(Enum):
    """插件类型"""
    AUTOSIGNIN = "autosignin"
    INDEXER = "indexer"
    NOTIFICATION = "notification"
    DOWNLOADER = "downloader"
    MEDIA = "media"
    SYNC = "sync"
    CUSTOM = "custom"


class PluginState(Enum):
    """插件状态"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"


@dataclass
class PluginInfo:
    """插件信息"""
    id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    state: PluginState = PluginState.DISABLED
    loaded_at: Optional[datetime] = None
    error_message: Optional[str] = None


class PluginBase(ABC):
    """插件基类"""

    plugin_info: PluginInfo = None

    def __init__(self) -> None:
        self._enabled = False
        self._config: Dict[str, Any] = {}

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化插件

        Args:
            config: 插件配置

        Returns:
            初始化是否成功
        """
        pass

    @abstractmethod
    def enable(self) -> bool:
        """启用插件"""
        pass

    @abstractmethod
    def disable(self) -> bool:
        """禁用插件"""
        pass

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        执行插件

        Returns:
            执行结果
        """
        pass

    @property
    def is_enabled(self) -> bool:
        """是否启用"""
        return self._enabled

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证配置

        Args:
            config: 待验证的配置

        Returns:
            配置是否有效
        """
        if not self.plugin_info:
            return False

        required_fields = self.plugin_info.config_schema.get("required", [])
        for field in required_fields:
            if field not in config:
                return False

        return True

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return self.plugin_info.config_schema.get("defaults", {}) if self.plugin_info else {}

    def on_event(self, event: str, data: Any) -> None:
        """
        事件处理

        Args:
            event: 事件名称
            data: 事件数据
        """
        pass


class PluginMeta(type):
    """插件元类"""

    _plugins: Dict[str, PluginBase] = {}

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)

        if "plugin_info" in namespace:
            plugin_id = namespace["plugin_info"].id
            PluginMeta._plugins[plugin_id] = cls

        return cls

    @classmethod
    def get_plugin(mcs, plugin_id: str) -> Optional[PluginBase]:
        """获取插件类"""
        return PluginMeta._plugins.get(plugin_id)

    @classmethod
    def get_all_plugins(mcs) -> Dict[str, PluginBase]:
        """获取所有插件"""
        return PluginMeta._plugins.copy()


def register_plugin(plugin_class: type) -> None:
    """
    注册插件

    Args:
        plugin_class: 插件类
    """
    if hasattr(plugin_class, "plugin_info"):
        plugin_id = plugin_class.plugin_info.id
        PluginMeta._plugins[plugin_id] = plugin_class
