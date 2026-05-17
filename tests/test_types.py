"""
类型注解测试
"""

import pytest
from mediaflow.types import (
    DownloaderType,
    MediaType,
    TaskStatus,
    SiteType,
    MessageChannel,
)


class TestTypeDefinitions:
    """类型定义测试"""

    def test_downloader_type_enum(self):
        """测试下载器类型枚举"""
        assert DownloaderType.QBITTORRENT.value == "qbittorrent"
        assert DownloaderType.TRANSMISSION.value == "transmission"
        assert DownloaderType.ARIA2.value == "aria2"
        assert DownloaderType.PAN115.value == "pan115"
        assert DownloaderType.PIKPAK.value == "pikpak"

    def test_media_type_enum(self):
        """测试媒体类型枚举"""
        assert MediaType.MOVIE.value == "movie"
        assert MediaType.TV.value == "tv"
        assert MediaType.ANIME.value == "anime"
        assert MediaType.UNKNOWN.value == "unknown"

    def test_task_status_enum(self):
        """测试任务状态枚举"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.PAUSED.value == "paused"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_site_type_enum(self):
        """测试站点类型枚举"""
        assert SiteType.PRIVATE.value == "private"
        assert SiteType.PUBLIC.value == "public"
        assert SiteType.INDEXER.value == "indexer"

    def test_message_channel_enum(self):
        """测试消息渠道枚举"""
        assert MessageChannel.TELEGRAM.value == "telegram"
        assert MessageChannel.WECHAT.value == "wechat"
        assert MessageChannel.EMAIL.value == "email"
        assert MessageChannel.PUSHPLUS.value == "pushplus"
        assert MessageChannel.BARK.value == "bark"
