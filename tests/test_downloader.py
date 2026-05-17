"""
下载器集成测试
"""

import pytest
from mediaflow.downloader.client import DownloaderConfig, QbittorrentClient


class TestDownloaderClient:
    """下载器客户端测试"""

    def test_qbittorrent_client_config(self):
        """测试Qbittorrent客户端配置"""
        config = DownloaderConfig(
            name="Test Qbittorrent",
            type="qbittorrent",
            host="localhost",
            port=8080,
            username="admin",
            password="admin"
        )

        client = QbittorrentClient(config)
        assert client.config.type == "qbittorrent"
        assert client.config.host == "localhost"
        assert client.config.port == 8080


class TestDownloaderManager:
    """下载器管理器测试"""

    def test_downloader_info_creation(self):
        """测试下载器信息创建"""
        from mediaflow.downloader.manager import DownloaderInfo

        info = DownloaderInfo(
            id=1,
            name="Test Downloader",
            type="qbittorrent",
            host="localhost",
            port=8080,
            enabled=True,
            torrents_count=10,
            download_speed=1024000,
            upload_speed=512000
        )

        assert info.torrents_count == 10
        assert info.download_speed == 1024000
