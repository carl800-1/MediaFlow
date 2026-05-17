"""
数据验证工具模块
"""

import re
from typing import Optional
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """
    验证URL格式

    Args:
        url: 待验证的URL字符串

    Returns:
        是否为有效URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_torrent_hash(torrent_hash: str) -> bool:
    """
    验证种子哈希格式

    Args:
        torrent_hash: 种子哈希字符串

    Returns:
        是否为有效哈希
    """
    pattern = r'^[a-fA-F0-9]{40}$'
    return bool(re.match(pattern, torrent_hash))


def validate_media_title(title: str) -> bool:
    """
    验证媒体标题格式

    Args:
        title: 媒体标题

    Returns:
        是否为有效标题
    """
    if not title or len(title.strip()) == 0:
        return False
    if len(title) > 500:
        return False
    return True


def validate_email(email: str) -> bool:
    """
    验证邮箱格式

    Args:
        email: 邮箱地址

    Returns:
        是否为有效邮箱
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_port(port: int) -> bool:
    """
    验证端口号

    Args:
        port: 端口号

    Returns:
        是否为有效端口
    """
    return 1 <= port <= 65535


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符

    Args:
        filename: 原始文件名

    Returns:
        清理后的文件名
    """
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    return re.sub(illegal_chars, '_', filename)
