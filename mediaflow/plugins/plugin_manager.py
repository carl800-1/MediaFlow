"""
插件管理器

管理插件的加载、启用和执行
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from threading import Lock

from mediaflow.utils.cli import getLogger
from mediaflow.plugins.base import (
    PluginBase,
    PluginInfo,
    PluginType,
    PluginState,
    PluginMeta,
)


logger = getLogger("plugin")


class PluginManager:
    """插件管理器"""

    _instance: Optional["PluginManager"] = None
    _lock = Lock()

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginBase] = {}
        self._plugin_classes: Dict[str, Type[PluginBase]] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._event_handlers: Dict[str, List[callable]] = {}
        self._scan_plugins()

    @classmethod
    def get_instance(cls) -> "PluginManager":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _scan_plugins(self) -> None:
        """扫描内置插件"""
        built_in_plugins = [
            ("autosignin", "AutoSigninPlugin"),
        ]

        for plugin_module, plugin_class_name in built_in_plugins:
            try:
                module = importlib.import_module(f"mediaflow.plugins.{plugin_module}")
                if hasattr(module, plugin_class_name):
                    plugin_class = getattr(module, plugin_class_name)
                    if hasattr(plugin_class, "plugin_info"):
                        plugin_id = plugin_class.plugin_info.id
                        self._plugin_classes[plugin_id] = plugin_class
                        self._plugin_info[plugin_id] = plugin_class.plugin_info
                        logger.info(f"扫描到插件: {plugin_id}")
            except ImportError:
                pass

        logger.info(f"共扫描到 {len(self._plugin_classes)} 个插件")

    def load_plugin(self, plugin_id: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        加载插件

        Args:
            plugin_id: 插件ID
            config: 插件配置

        Returns:
            加载是否成功
        """
        if plugin_id not in self._plugin_classes:
            logger.error(f"插件不存在: {plugin_id}")
            return False

        if plugin_id in self._plugins:
            logger.warning(f"插件已加载: {plugin_id}")
            return True

        try:
            plugin_class = self._plugin_classes[plugin_id]
            plugin_instance = plugin_class()

            if config is None:
                config = plugin_instance.get_default_config()

            if not plugin_instance.initialize(config):
                logger.error(f"插件初始化失败: {plugin_id}")
                return False

            self._plugins[plugin_id] = plugin_instance
            logger.info(f"插件加载成功: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"加载插件失败: {plugin_id} - {e}")
            return False

    def enable_plugin(self, plugin_id: str) -> bool:
        """
        启用插件

        Args:
            plugin_id: 插件ID

        Returns:
            启用是否成功
        """
        if plugin_id not in self._plugins:
            return self.load_plugin(plugin_id)

        plugin = self._plugins[plugin_id]
        if plugin.enable():
            self._plugin_info[plugin_id].state = PluginState.ENABLED
            logger.info(f"插件启用成功: {plugin_id}")
            return True
        return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """
        禁用插件

        Args:
            plugin_id: 插件ID

        Returns:
            禁用是否成功
        """
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]
        if plugin.disable():
            self._plugin_info[plugin_id].state = PluginState.DISABLED
            logger.info(f"插件禁用成功: {plugin_id}")
            return True
        return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件

        Args:
            plugin_id: 插件ID

        Returns:
            卸载是否成功
        """
        if plugin_id in self._plugins:
            plugin = self._plugins[plugin_id]
            if plugin.is_enabled:
                plugin.disable()
            del self._plugins[plugin_id]
            logger.info(f"插件已卸载: {plugin_id}")
            return True
        return False

    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """获取插件实例"""
        return self._plugins.get(plugin_id)

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self._plugin_info.get(plugin_id)

    def get_all_plugins(self) -> Dict[str, PluginInfo]:
        """获取所有插件信息"""
        return self._plugin_info.copy()

    def get_enabled_plugins(self) -> List[PluginBase]:
        """获取所有已启用的插件"""
        return [p for p in self._plugins.values() if p.is_enabled]

    def execute_plugin(self, plugin_id: str, *args, **kwargs) -> Any:
        """
        执行插件

        Args:
            plugin_id: 插件ID
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            执行结果
        """
        plugin = self._plugins.get(plugin_id)
        if not plugin or not plugin.is_enabled:
            logger.error(f"插件未启用: {plugin_id}")
            return None

        try:
            return plugin.execute(*args, **kwargs)
        except Exception as e:
            logger.error(f"执行插件失败: {plugin_id} - {e}")
            return None

    def register_event_handler(self, event: str, handler: callable) -> None:
        """
        注册事件处理器

        Args:
            event: 事件名称
            handler: 事件处理函数
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
        logger.info(f"注册事件处理器: {event}")

    def emit_event(self, event: str, data: Any = None) -> None:
        """
        触发事件

        Args:
            event: 事件名称
            data: 事件数据
        """
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"事件处理失败: {event} - {e}")

        for plugin in self._plugins.values():
            if plugin.is_enabled:
                try:
                    plugin.on_event(event, data)
                except Exception as e:
                    logger.error(f"插件事件处理失败: {plugin} - {e}")

    def load_external_plugin(self, plugin_path: str) -> bool:
        """
        加载外部插件

        Args:
            plugin_path: 插件路径

        Returns:
            加载是否成功
        """
        try:
            plugin_file = Path(plugin_path)
            if not plugin_file.exists():
                logger.error(f"插件文件不存在: {plugin_path}")
                return False

            module_name = plugin_file.stem
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, PluginBase) and obj != PluginBase:
                    if hasattr(obj, "plugin_info"):
                        plugin_id = obj.plugin_info.id
                        self._plugin_classes[plugin_id] = obj
                        self._plugin_info[plugin_id] = obj.plugin_info
                        logger.info(f"加载外部插件: {plugin_id}")
                        return True

            logger.error(f"未找到有效的插件类: {plugin_path}")
            return False

        except Exception as e:
            logger.error(f"加载外部插件失败: {plugin_path} - {e}")
            return False


_global_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _global_plugin_manager
    if _global_plugin_manager is None:
        _global_plugin_manager = PluginManager.get_instance()
    return _global_plugin_manager
