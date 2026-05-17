"""
Web路由模块
"""

from mediaflow.web.routes import register_routes
from mediaflow.web import brushtask, downloader, search, site, subscription, system

__all__ = [
    "register_routes",
    "brushtask",
    "downloader",
    "search",
    "site",
    "subscription",
    "system",
]
