"""
下载器模块

提供多下载器支持
"""

from mediaflow.downloader.manager import DownloaderManager, get_downloader_manager
from mediaflow.downloader.client import BaseDownloader, QbittorrentClient, TransmissionClient, Aria2Client

__all__ = [
    "DownloaderManager",
    "get_downloader_manager",
    "BaseDownloader",
    "QbittorrentClient",
    "TransmissionClient",
    "Aria2Client",
]
