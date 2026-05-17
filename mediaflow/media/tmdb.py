"""
TMDB API客户端

提供TMDB媒体信息查询功能
"""

import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from mediaflow.utils.cli import getLogger


logger = getLogger("tmdb")


@dataclass
class TMDbMedia:
    """TMDB媒体信息"""
    id: int
    title: str
    overview: str
    poster_path: Optional[str]
    backdrop_path: Optional[str]
    release_date: Optional[str]
    vote_average: float
    vote_count: int
    media_type: str = "movie"
    genres: List[str] = None
    imdb_id: Optional[str] = None

    def __post_init__(self):
        if self.genres is None:
            self.genres = []


@dataclass
class TMDbEpisode:
    """TMDB剧集信息"""
    id: int
    name: str
    overview: str
    still_path: Optional[str]
    season_number: int
    episode_number: int
    air_date: Optional[str]
    vote_average: float


class TMDBClient:
    """TMDB API客户端"""

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

    def __init__(self, api_key: str, language: str = "zh-CN") -> None:
        self._api_key = api_key
        self._language = language
        self._session = requests.Session()

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """发送API请求"""
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["api_key"] = self._api_key
        params["language"] = self._language

        try:
            response = self._session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"TMDB API请求失败: {e}")
            return None

    def search_movie(self, query: str, year: Optional[int] = None) -> List[TMDbMedia]:
        """搜索电影"""
        params = {"query": query, "page": 1}
        if year:
            params["year"] = year

        data = self._make_request("search/movie", params)
        if not data or "results" not in data:
            return []

        return [
            TMDbMedia(
                id=m["id"],
                title=m.get("title", ""),
                overview=m.get("overview", ""),
                poster_path=m.get("poster_path"),
                backdrop_path=m.get("backdrop_path"),
                release_date=m.get("release_date"),
                vote_average=m.get("vote_average", 0),
                vote_count=m.get("vote_count", 0),
                media_type="movie",
                genres=[g["name"] for g in m.get("genres", [])],
                imdb_id=m.get("imdb_id"),
            )
            for m in data["results"]
        ]

    def search_tv(self, query: str, year: Optional[int] = None) -> List[TMDbMedia]:
        """搜索剧集"""
        params = {"query": query, "page": 1}
        if year:
            params["first_air_date_year"] = year

        data = self._make_request("search/tv", params)
        if not data or "results" not in data:
            return []

        return [
            TMDbMedia(
                id=m["id"],
                title=m.get("name", ""),
                overview=m.get("overview", ""),
                poster_path=m.get("poster_path"),
                backdrop_path=m.get("backdrop_path"),
                release_date=m.get("first_air_date"),
                vote_average=m.get("vote_average", 0),
                vote_count=m.get("vote_count", 0),
                media_type="tv",
                genres=[g["name"] for g in m.get("genres", [])],
            )
            for m in data["results"]
        ]

    def get_movie_details(self, movie_id: int) -> Optional[TMDbMedia]:
        """获取电影详情"""
        data = self._make_request(f"movie/{movie_id}")
        if not data:
            return None

        return TMDbMedia(
            id=data["id"],
            title=data.get("title", ""),
            overview=data.get("overview", ""),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            release_date=data.get("release_date"),
            vote_average=data.get("vote_average", 0),
            vote_count=data.get("vote_count", 0),
            media_type="movie",
            genres=[g["name"] for g in data.get("genres", [])],
            imdb_id=data.get("imdb_id"),
        )

    def get_tv_details(self, tv_id: int) -> Optional[TMDbMedia]:
        """获取剧集详情"""
        data = self._make_request(f"tv/{tv_id}")
        if not data:
            return None

        return TMDbMedia(
            id=data["id"],
            title=data.get("name", ""),
            overview=data.get("overview", ""),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            release_date=data.get("first_air_date"),
            vote_average=data.get("vote_average", 0),
            vote_count=data.get("vote_count", 0),
            media_type="tv",
            genres=[g["name"] for g in data.get("genres", [])],
        )

    def get_tv_season(self, tv_id: int, season_number: int) -> List[TMDbEpisode]:
        """获取剧集季信息"""
        data = self._make_request(f"tv/{tv_id}/season/{season_number}")
        if not data or "episodes" not in data:
            return []

        return [
            TMDbEpisode(
                id=e["id"],
                name=e.get("name", ""),
                overview=e.get("overview", ""),
                still_path=e.get("still_path"),
                season_number=e.get("season_number", season_number),
                episode_number=e.get("episode_number", 0),
                air_date=e.get("air_date"),
                vote_average=e.get("vote_average", 0),
            )
            for e in data["episodes"]
        ]

    @staticmethod
    def get_poster_url(poster_path: Optional[str], size: str = "w500") -> Optional[str]:
        """获取海报URL"""
        if not poster_path:
            return None
        return f"{TMDBClient.IMAGE_BASE_URL}/{size}{poster_path}"

    @staticmethod
    def get_backdrop_url(backdrop_path: Optional[str], size: str = "original") -> Optional[str]:
        """获取背景图URL"""
        if not backdrop_path:
            return None
        return f"{TMDBClient.IMAGE_BASE_URL}/{size}{backdrop_path}"


_tmdb_client: Optional[TMDBClient] = None


def get_tmdb_client(api_key: Optional[str] = None) -> Optional[TMDBClient]:
    """获取TMDB客户端实例"""
    global _tmdb_client
    if _tmdb_client is None and api_key:
        _tmdb_client = TMDBClient(api_key)
    return _tmdb_client
