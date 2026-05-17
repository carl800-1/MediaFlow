"""
命名服务

提供标准化的媒体文件命名规范
"""

from typing import Optional, List, Dict
from dataclasses import dataclass

from mediaflow.scraper.scraper import ScraperMediaInfo


@dataclass
class NamingRule:
    """命名规则"""
    name: str
    pattern: str
    media_type: str
    enabled: bool = True


class NamingService:
    """媒体命名服务"""

    MOVIE_TEMPLATE = "{title} ({year})"

    TV_TEMPLATE = "{title}/Season {season}/{title} S{season:02d}E{episode:02d}"

    DEFAULT_RULES = [
        NamingRule(
            name="蓝光原盘",
            pattern="{title} ({year}) [BluRay]",
            media_type="movie"
        ),
        NamingRule(
            name="4K标准",
            pattern="{title} ({year}) [4K]",
            media_type="movie"
        ),
        NamingRule(
            name="蓝光剧集",
            pattern="{title}/Season {season}/{title} S{season:02d}E{episode:02d} [BluRay]",
            media_type="tv"
        ),
    ]

    def __init__(self, custom_rules: List[NamingRule] = None) -> None:
        self._rules = custom_rules or self.DEFAULT_RULES.copy()

    def add_rule(self, rule: NamingRule) -> None:
        """添加命名规则"""
        self._rules.append(rule)

    def remove_rule(self, name: str) -> bool:
        """移除命名规则"""
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                del self._rules[i]
                return True
        return False

    def get_rule(self, name: str) -> Optional[NamingRule]:
        """获取命名规则"""
        for rule in self._rules:
            if rule.name == name:
                return rule
        return None

    def get_rules(self, media_type: str = None) -> List[NamingRule]:
        """获取所有规则"""
        if media_type:
            return [r for r in self._rules if r.media_type == media_type]
        return self._rules.copy()

    def apply_rule(self, rule: NamingRule, media_info: ScraperMediaInfo) -> str:
        """应用命名规则"""
        pattern = rule.pattern

        replacements = {
            "{title}": self._clean_title(media_info.title or "Unknown"),
            "{year}": str(media_info.year or ""),
            "{season}": str(media_info.season or 1),
            "{episode}": str(media_info.episode or 1),
            "{episode_title}": self._clean_title(media_info.episode_title or ""),
            "{resolution}": media_info.resolution or "",
            "{video_codec}": media_info.video_codec or "",
            "{audio_codec}": media_info.audio_codec or "",
            "{release_group}": media_info.release_group or "",
            "{quality}": self._build_quality(media_info),
        }

        for key, value in replacements.items():
            pattern = pattern.replace(key, value)

        return pattern

    def _clean_title(self, title: str) -> str:
        """清理标题"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            title = title.replace(char, '_')
        return title.strip()

    def _build_quality(self, media_info: ScraperMediaInfo) -> str:
        """构建质量标识"""
        parts = []
        if media_info.resolution:
            parts.append(media_info.resolution)
        if media_info.video_codec:
            parts.append(media_info.video_codec)
        if media_info.audio_codec:
            parts.append(media_info.audio_codec)
        return '-'.join(parts) if parts else ""

    def get_movie_path(self, media_info: ScraperMediaInfo, base_dir: str, rule_name: str = None) -> str:
        """获取电影文件路径"""
        if rule_name:
            rule = self.get_rule(rule_name)
        else:
            rule = self._rules[0] if self._rules else None

        if not rule:
            return f"{base_dir}/{media_info.title}"

        filename = self.apply_rule(rule, media_info)
        return f"{base_dir}/{filename}{self._get_extension(media_info)}"

    def get_tv_path(self, media_info: ScraperMediaInfo, base_dir: str, rule_name: str = None) -> str:
        """获取剧集文件路径"""
        if rule_name:
            rule = self.get_rule(rule_name)
        else:
            rule = self._rules[0] if self._rules else None

        if not rule:
            return f"{base_dir}/{media_info.title}/Season {media_info.season}/{media_info.title}"

        filename = self.apply_rule(rule, media_info)
        return f"{base_dir}/{filename}{self._get_extension(media_info)}"

    def _get_extension(self, media_info: ScraperMediaInfo) -> str:
        """获取文件扩展名"""
        return ".mkv"

    def validate_naming(self, filename: str) -> bool:
        """验证文件名"""
        if not filename:
            return False

        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            if char in filename:
                return False

        return True
