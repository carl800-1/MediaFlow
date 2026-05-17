"""
插件系统模块

提供插件加载、注册和执行功能
"""

from mediaflow.plugins.plugin_manager import PluginManager, get_plugin_manager
from mediaflow.plugins.base import PluginBase, PluginMeta

__all__ = [
    "PluginManager",
    "get_plugin_manager",
    "PluginBase",
    "PluginMeta",
]
