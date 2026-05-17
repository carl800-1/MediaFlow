"""
MediaFlow - 新一代NAS媒体库智能管理系统

基于NAS-Tools重构优化，提供更现代化、类型安全、可维护性更强的媒体资源管理解决方案。

核心模块:
- brushtask: 刷流任务管理
- database: 数据库管理
- downloader: 下载器管理
- media: 媒体信息处理
- message: 消息通知
- search: 搜索引擎
- sites: 站点管理
- subscribe: RSS订阅
- sync: 文件同步
- utils: 工具函数
- web: Web API
"""

from mediaflow.version import __version__
from mediaflow.utils.config import ConfigManager, get_config
from mediaflow.utils.cli import setup_logging, getLogger

__all__ = [
    "__version__",
    "ConfigManager",
    "get_config",
    "setup_logging",
    "getLogger",
]
