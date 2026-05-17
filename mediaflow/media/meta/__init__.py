"""
媒体元信息解析模块

提供媒体标题、年份、类型等信息的解析
"""

from dataclasses import dataclass
from typing import Optional, List
import re


@dataclass
class MetaInfo:
    """元信息"""
    title: str = ""
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    part: Optional[int] = None
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    media_type: str = "unknown"
    release_group: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    raw_title: str = ""


@dataclass
class EpisodeInfo:
    """集信息"""
    season: int
    episode: int
    title: Optional[str] = None


class MetaParser:
    """元信息解析器"""

    SEASON_EPISODE_PATTERNS = [
        r'S(\d{1,2})E(\d{1,2})',
        r'S(\d{1,2})\s*-\s*E(\d{1,2})',
        r'S(\d{1,2})\s*第(\d{1,2})集',
        r'第(\d{1,2})季\s*第(\d{1,2})集',
        r'S(\d{1,2})\s*(\d{2})',
        r'S(\d{1,2})e(\d{1,2})',
        r'S(\d+)E(\d+)(?:-E(\d+))?',
    ]

    YEAR_PATTERN = r'(19|20)\d{2}'
    RESOLUTION_PATTERNS = [
        r'(\d{3,4})[pP]',
        r'[xX](\d{3,4})',
        r'2160[Pp]',
        r'4[Kk]',
        r'8[Kk]',
    ]
    CODEC_PATTERNS = {
        'video': [
            r'[xh]?26[45]',
            r'[xh]?265',
            r'HEVC',
            r'AV1',
            r'VP9',
            r'Xvid',
            r'DivX',
        ],
        'audio': [
            r'DTS[- ]?HD',
            r'Dolby[\s-]?Atmos',
            r'TrueHD',
            r'FLAC',
            r'AAC',
            r'MP3',
            r'AC3',
            r'EAC3',
        ],
    }

    def __init__(self) -> None:
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """编译正则表达式"""
        self._season_episode_re = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SEASON_EPISODE_PATTERNS
        ]
        self._year_re = re.compile(self.YEAR_PATTERN)
        self._resolution_res = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.RESOLUTION_PATTERNS
        ]
        self._codec_res = {
            key: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for key, patterns in self.CODEC_PATTERNS.items()
        }

    def parse(self, title: str) -> MetaInfo:
        """
        解析标题

        Args:
            title: 原始标题

        Returns:
            解析后的元信息
        """
        meta = MetaInfo(raw_title=title, title=title)

        meta.season, meta.episode = self._parse_season_episode(title)
        if meta.season is not None:
            meta.media_type = "tv"
        else:
            meta.media_type = "movie"

        meta.year = self._parse_year(title)

        meta.resolution = self._parse_resolution(title)
        meta.video_codec = self._parse_codec(title, 'video')
        meta.audio_codec = self._parse_codec(title, 'audio')

        meta.release_group = self._parse_release_group(title)

        meta.title = self._clean_title(title)

        return meta

    def _parse_season_episode(self, title: str) -> tuple:
        """解析季和集"""
        for pattern in self._season_episode_re:
            match = pattern.search(title)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    try:
                        season = int(groups[0])
                        episode = int(groups[1])
                        return season, episode
                    except ValueError:
                        pass
        return None, None

    def _parse_year(self, title: str) -> Optional[int]:
        """解析年份"""
        match = self._year_re.search(title)
        if match:
            year = int(match.group())
            if 1900 <= year <= 2030:
                return year
        return None

    def _parse_resolution(self, title: str) -> Optional[str]:
        """解析分辨率"""
        for pattern in self._resolution_res:
            match = pattern.search(title)
            if match:
                res = match.group(1) or match.group()
                if res.lower() in ['4k', '8k']:
                    return res.upper()
                return f"{res}p"
        return None

    def _parse_codec(self, title: str, codec_type: str) -> Optional[str]:
        """解析编码"""
        if codec_type not in self._codec_res:
            return None

        for pattern in self._codec_res[codec_type]:
            if pattern.search(title):
                return pattern.search(title).group()
        return None

    def _parse_release_group(self, title: str) -> Optional[str]:
        """解析发布组"""
        group_patterns = [
            r'\[([^\]]+)\]$',
            r'-([A-Za-z0-9]+)$',
            r'\(([A-Za-z0-9]+)\)$',
        ]

        for pattern in group_patterns:
            match = re.search(pattern, title)
            if match:
                potential_group = match.group(1)
                if len(potential_group) >= 2 and len(potential_group) <= 15:
                    return potential_group
        return None

    def _clean_title(self, title: str) -> str:
        """清理标题"""
        cleaned = title

        for pattern in self._season_episode_re:
            cleaned = pattern.sub('', cleaned)

        cleaned = self._year_re.sub('', cleaned)

        for pattern in self._resolution_res:
            cleaned = pattern.sub('', cleaned)

        for codec_type in self._codec_res:
            for pattern in self._codec_res[codec_type]:
                cleaned = pattern.sub('', cleaned)

        cleaned = re.sub(r'\[.*?\]', '', cleaned)
        cleaned = re.sub(r'\(.*?\)', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip('.-_ ')

        return cleaned

    def parse_batch(self, titles: List[str]) -> List[MetaInfo]:
        """批量解析"""
        return [self.parse(title) for title in titles]

    def normalize_title(self, title: str) -> str:
        """标准化标题"""
        normalized = title.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def match(self, title1: str, title2: str) -> bool:
        """判断两个标题是否匹配"""
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        return norm1 == norm2 or norm1 in norm2 or norm2 in norm1
