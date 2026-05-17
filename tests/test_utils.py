"""
工具函数测试
"""

import pytest
from mediaflow.utils.validators import (
    validate_url,
    validate_torrent_hash,
    validate_media_title,
    validate_email,
    validate_port,
    sanitize_filename,
)


class TestValidators:
    """验证器测试"""

    def test_validate_url(self):
        """测试URL验证"""
        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com/path") is True
        assert validate_url("not-a-url") is False
        assert validate_url("") is False

    def test_validate_torrent_hash(self):
        """测试种子哈希验证"""
        assert validate_torrent_hash("A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0") is True
        assert validate_torrent_hash("a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0") is True
        assert validate_torrent_hash("invalid") is False
        assert validate_torrent_hash("123") is False

    def test_validate_media_title(self):
        """测试媒体标题验证"""
        assert validate_media_title("Movie Name 2023") is True
        assert validate_media_title("A") is True
        assert validate_media_title("") is False
        assert validate_media_title("   ") is False
        assert validate_media_title("a" * 501) is False

    def test_validate_email(self):
        """测试邮箱验证"""
        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.co.uk") is True
        assert validate_email("invalid-email") is False
        assert validate_email("@example.com") is False

    def test_validate_port(self):
        """测试端口验证"""
        assert validate_port(80) is True
        assert validate_port(443) is True
        assert validate_port(8080) is True
        assert validate_port(0) is False
        assert validate_port(65536) is False
        assert validate_port(-1) is False

    def test_sanitize_filename(self):
        """测试文件名清理"""
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"
        assert sanitize_filename("file<with>invalid:chars.txt") == "file_with_invalid_chars.txt"
        assert sanitize_filename("file|with|pipes.txt") == "file_with_pipes.txt"
