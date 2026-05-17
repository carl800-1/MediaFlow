"""
工具函数模块

提供通用工具函数
"""

import os
import re
import hashlib
import json
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from pathlib import Path


def ensure_dir(path: Union[str, Path]) -> Path:
    """确保目录存在"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_hash(filepath: Union[str, Path]) -> str:
    """计算文件哈希"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def format_size(size_bytes: int) -> str:
    """格式化大小显示"""
    if size_bytes is None or size_bytes == 0:
        return "0 B"

    size_bytes = float(size_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0

    while size_bytes >= 1024 and unit_index < len(units) - 1:
        size_bytes /= 1024
        unit_index += 1

    return f"{size_bytes:.2f} {units[unit_index]}"


def parse_size(size_str: str) -> int:
    """解析大小字符串到字节数"""
    if not size_str:
        return 0

    size_str = str(size_str).strip().upper()
    size_match = re.search(r'(\d+(?:\.\d+)?)\s*([A-Z]+)', size_str)

    if not size_match:
        try:
            return int(float(size_str))
        except ValueError:
            return 0

    value = float(size_match.group(1))
    unit = size_match.group(2)

    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }

    return int(value * units.get(unit, 1))


def format_speed(speed_bytes: int) -> str:
    """格式化速度显示"""
    if speed_bytes is None or speed_bytes == 0:
        return "0 B/s"

    speed_bytes = float(speed_bytes)
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    unit_index = 0

    while speed_bytes >= 1024 and unit_index < len(units) - 1:
        speed_bytes /= 1024
        unit_index += 1

    return f"{speed_bytes:.2f} {units[unit_index]}"


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}分{secs}秒"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}小时{minutes}分钟"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}天{hours}小时"


def parse_time(time_str: str) -> Optional[datetime]:
    """解析时间字符串"""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None


def time_ago(dt: datetime) -> str:
    """计算时间差描述"""
    now = datetime.now()
    diff = now - dt

    if diff.days > 30:
        months = diff.days // 30
        return f"{months}个月前"
    elif diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"


def sanitize_filename(filename: str) -> str:
    """清理文件名"""
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)
    sanitized = sanitized.strip(". ")
    return sanitized or "unnamed"


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """安全解析JSON"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: Any = None) -> str:
    """安全序列化JSON"""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps(default, ensure_ascii=False) if default is not None else "{}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本"""
    if not text or len(text) <= max_length:
        return text or ""
    return text[:max_length - len(suffix)] + suffix


def extract_year(title: str) -> Optional[int]:
    """从标题中提取年份"""
    year_match = re.search(r'\((\d{4})\)', title)
    if year_match:
        return int(year_match.group(1))

    year_match = re.search(r'(\d{4})', title)
    if year_match:
        year = int(year_match.group(1))
        if 1900 <= year <= datetime.now().year + 5:
            return year
    return None


def extract_season_episode(title: str) -> tuple[Optional[int], Optional[int]]:
    """提取季数和集数"""
    season = None
    episode = None

    s_match = re.search(r'[Ss](\d{1,2})', title)
    if s_match:
        season = int(s_match.group(1))

    e_match = re.search(r'[Ee](\d{1,2})', title)
    if e_match:
        episode = int(e_match.group(1))

    return season, episode


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """列表分块"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: Dict) -> Dict:
    """合并多个字典"""
    result = {}
    for d in dicts:
        result.update(d)
    return result


def remove_duplicates(lst: List[Any], key_func=None) -> List[Any]:
    """移除列表重复项"""
    if key_func is None:
        key_func = lambda x: x

    seen = set()
    result = []
    for item in lst:
        key = key_func(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
