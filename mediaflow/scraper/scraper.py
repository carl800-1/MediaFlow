"""
媒体刮削器

自动识别和获取媒体信息
"""

import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

from mediaflow.utils.cli import getLogger
from mediaflow.media.tmdb import TMDBClient
from mediaflow.media.douban import DoubanClient


logger = getLogger("scraper")


@dataclass
class ScraperMediaInfo:
    """刮削后的媒体信息"""
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    media_type: str = "movie"
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: List[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    douban_id: Optional[str] = None
    runtime: Optional[int] = None
    vote_average: Optional[float] = None
    director: Optional[str] = None
    cast: List[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    release_group: Optional[str] = None

    def __post_init__(self):
        if self.genres is None:
            self.genres = []
        if self.cast is None:
            self.cast = []


class MediaScraper:
    """媒体刮削器"""

    def __init__(self, tmdb_api_key: str = None, douban_cookie: str = None) -> None:
        self._tmdb = TMDBClient(tmdb_api_key) if tmdb_api_key else None
        self._douban = DoubanClient(douban_cookie) if douban_cookie else None

    def scrape(self, file_path: str = None, title: str = None, year: int = None,
               media_type: str = "movie", season: int = None, episode: int = None) -> Optional[ScraperMediaInfo]:
        """刮削媒体信息"""
        if file_path:
            parsed = self.parse_filename(file_path)
            title = title or parsed.get("title")
            year = year or parsed.get("year")
            media_type = media_type or parsed.get("media_type", "movie")
            season = season or parsed.get("season")
            episode = episode or parsed.get("episode")

        info = None

        if self._tmdb:
            info = self._scrape_tmdb(title, year, media_type, season, episode)

        if not info and self._douban:
            info = self._scrape_douban(title, year, media_type)

        if not info:
            info = self._create_basic_info(title, year, media_type)

        if info and file_path:
            file_info = self.parse_filename(file_path)
            info.resolution = file_info.get("resolution")
            info.video_codec = file_info.get("video_codec")
            info.audio_codec = file_info.get("audio_codec")
            info.release_group = file_info.get("release_group")

        return info

    def _scrape_tmdb(self, title: str, year: int, media_type: str, season: int = None, episode: int = None) -> Optional[ScraperMediaInfo]:
        """从TMDB刮削"""
        if not self._tmdb or not title:
            return None

        try:
            if media_type == "movie":
                results = self._tmdb.search_movies(title, year)
            else:
                results = self._tmdb.search_tvshows(title, year)

            if results:
                item = results[0]
                detail = self._tmdb.get_movie_detail(item["id"]) if media_type == "movie" else self._tmdb.get_tv_detail(item["id"])

                if detail:
                    return ScraperMediaInfo(
                        title=detail.get("title") or detail.get("name", title),
                        original_title=detail.get("original_title") or detail.get("original_name"),
                        year=int(detail.get("release_date", "")[:4]) if detail.get("release_date") else year,
                        media_type=media_type,
                        overview=detail.get("overview"),
                        poster_url=f"https://image.tmdb.org/t/p/original{detail.get('poster_path')}" if detail.get("poster_path") else None,
                        backdrop_url=f"https://image.tmdb.org/t/p/original{detail.get('backdrop_path')}" if detail.get("backdrop_path") else None,
                        genres=[g["name"] for g in detail.get("genres", [])],
                        tmdb_id=detail.get("id"),
                        imdb_id=detail.get("imdb_id"),
                        runtime=detail.get("runtime") if media_type == "movie" else None,
                        vote_average=detail.get("vote_average"),
                    )
        except Exception as e:
            logger.error(f"TMDB刮削失败: {e}")
        return None

    def _scrape_douban(self, title: str, year: int, media_type: str) -> Optional[ScraperMediaInfo]:
        """从豆瓣刮削"""
        if not self._douban or not title:
            return None

        try:
            results = self._douban.search(title, media_type)
            if results:
                item = results[0]
                detail = self._douban.get_detail(item.get("id"))

                if detail:
                    return ScraperMediaInfo(
                        title=detail.get("title", title),
                        original_title=detail.get("original_title"),
                        year=int(detail.get("year", year or 0)),
                        media_type=media_type,
                        overview=detail.get("intro") or detail.get("summary"),
                        poster_url=detail.get("cover"),
                        genres=[g.get("name") for g in detail.get("genres", [])],
                        douban_id=detail.get("id"),
                        vote_average=detail.get("rating", {}).get("value") if detail.get("rating") else None,
                    )
        except Exception as e:
            logger.error(f"豆瓣刮削失败: {e}")
        return None

    def _create_basic_info(self, title: str, year: int, media_type: str) -> ScraperMediaInfo:
        """创建基本信息"""
        return ScraperMediaInfo(
            title=title or "Unknown",
            year=year,
            media_type=media_type,
        )

    def parse_filename(self, filename: str) -> Dict[str, Any]:
        """解析文件名"""
        result = {
            "title": None,
            "year": None,
            "media_type": "movie",
            "season": None,
            "episode": None,
            "resolution": None,
            "video_codec": None,
            "audio_codec": None,
            "release_group": None,
        }

        basename = os.path.basename(filename)
        name_without_ext = os.path.splitext(basename)[0]

        patterns = {
            "movie": [
                r"(?P<title>.+?)[. ]?[\[(]?(?P<year>19\d{2}|20\d{2})[)\]]?",
                r"(?P<title>.+?)(?:[. ](?:(?:19|20)\d{2}))",
            ],
            "tv": [
                r"(?P<title>.+?)[. ]S(?P<season>\d{1,2})E(?P<episode>\d{1,2})",
                r"(?P<title>.+?)[. ](?P<season>\d{1,2})x(?P<episode>\d{1,2})",
                r"(?P<title>.+?)[. ]第(?P<season>\d+)季?[. ]?E?(?P<episode>\d+)",
            ]
        }

        for pattern in patterns["movie"]:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                result["title"] = match.group("title").replace(".", " ").strip()
                if "year" in match.groupdict():
                    try:
                        result["year"] = int(match.group("year"))
                    except (ValueError, TypeError):
                        pass
                break

        for pattern in patterns["tv"]:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                result["media_type"] = "tv"
                result["title"] = match.group("title").replace(".", " ").strip()
                try:
                    result["season"] = int(match.group("season"))
                    result["episode"] = int(match.group("episode"))
                except (ValueError, TypeError):
                    pass
                break

        resolution_patterns = [
            (r"2160[yp]|4K| UHD", "4K"),
            (r"1080[ip]", "1080p"),
            (r"720[ip]", "720p"),
            (r"576[ip]", "576p"),
            (r"480[ip]", "480p"),
        ]
        for pattern, resolution in resolution_patterns:
            if re.search(pattern, name_without_ext, re.IGNORECASE):
                result["resolution"] = resolution
                break

        video_codec_patterns = [
            (r"H(?:264|265)|HEVC", "H.265"),
            (r"AVC|x264", "H.264"),
            (r"VP9", "VP9"),
            (r"AV1", "AV1"),
        ]
        for pattern, codec in video_codec_patterns:
            if re.search(pattern, name_without_ext, re.IGNORECASE):
                result["video_codec"] = codec
                break

        audio_codec_patterns = [
            (r"DTS-HD|DTSHD", "DTS-HD"),
            (r"DTS", "DTS"),
            (r"TrueHD|DD\\+?|E-AC3", "Dolby Digital Plus"),
            (r"AC3|EAC3|DD", "Dolby Digital"),
            (r"AAC|LC-AAC", "AAC"),
            (r"MP3", "MP3"),
            (r"FLAC", "FLAC"),
            (r"PCM", "PCM"),
        ]
        for pattern, codec in audio_codec_patterns:
            if re.search(pattern, name_without_ext, re.IGNORECASE):
                result["audio_codec"] = codec
                break

        group_match = re.search(r"\[([^\]]+)\]$", name_without_ext)
        if group_match:
            result["release_group"] = group_match.group(1)

        if not result["title"]:
            result["title"] = name_without_ext.replace(".", " ").strip()

        return result
