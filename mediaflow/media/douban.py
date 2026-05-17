"""
豆瓣API客户端

提供豆瓣媒体信息查询功能
"""

import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from mediaflow.utils.cli import getLogger


logger = getLogger("douban")


@dataclass
class DoubanMedia:
    """豆瓣媒体信息"""
    id: str
    title: str
    original_title: str
    cover_url: Optional[str]
    rating: float
    vote_count: int
    year: Optional[str]
    subtype: str
    summary: str
    genres: List[str]
    directors: List[str]
    actors: List[str]


class DoubanClient:
    """豆瓣API客户端"""

    BASE_URL = "https://movie.douban.com"
    API_URL = "https://frodo.douban.com"

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": self.BASE_URL,
        })

    def search(self, keyword: str, media_type: Optional[str] = None) -> List[DoubanMedia]:
        """
        搜索豆瓣媒体

        Args:
            keyword: 搜索关键词
            media_type: 媒体类型 (movie/tv)

        Returns:
            媒体列表
        """
        params = {
            "q": keyword,
            "count": 20,
        }

        try:
            url = f"{self.API_URL}/api/v2/search/jshotels"
            response = self._session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                return self._parse_search_result(response.json())
        except requests.RequestException as e:
            logger.error(f"豆瓣搜索失败: {e}")

        return []

    def _parse_search_result(self, data: Dict[str, Any]) -> List[DoubanMedia]:
        """解析搜索结果"""
        results = []
        items = data.get("result", [])

        for item in items:
            media = DoubanMedia(
                id=str(item.get("id", "")),
                title=item.get("title", ""),
                original_title=item.get("original_title", ""),
                cover_url=item.get("cover_url"),
                rating=float(item.get("rating", 0)),
                vote_count=int(item.get("vote_count", 0)),
                year=item.get("year"),
                subtype=item.get("subtype", "movie"),
                summary=item.get("summary", ""),
                genres=item.get("genres", []),
                directors=item.get("directors", []),
                actors=item.get("actors", []),
            )
            results.append(media)

        return results

    def get_details(self, media_id: str) -> Optional[DoubanMedia]:
        """获取媒体详情"""
        try:
            url = f"{self.BASE_URL}/j/subject/{media_id}"
            response = self._session.get(url, timeout=10)

            if response.status_code == 200:
                return self._parse_detail_page(response.text)
        except requests.RequestException as e:
            logger.error(f"获取豆瓣详情失败: {e}")

        return None

    def _parse_detail_page(self, html: str) -> Optional[DoubanMedia]:
        """解析详情页面"""
        import re

        try:
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1).replace(" (豆瓣)", "") if title_match else ""

            rating_match = re.search(r'"ratingValue":\s*"?([\d.]+)"?', html)
            rating = float(rating_match.group(1)) if rating_match else 0.0

            cover_match = re.search(r'<img src="(.*?)".*?class="cover">', html)
            cover_url = cover_match.group(1) if cover_match else None

            year_match = re.search(r'"datePublished".*?(\d{4})', html)
            year = year_match.group(1) if year_match else None

            return DoubanMedia(
                id="",
                title=title,
                original_title="",
                cover_url=cover_url,
                rating=rating,
                vote_count=0,
                year=year,
                subtype="movie",
                summary="",
                genres=[],
                directors=[],
                actors=[],
            )
        except Exception as e:
            logger.error(f"解析豆瓣详情失败: {e}")
            return None


_douban_client: Optional[DoubanClient] = None


def get_douban_client() -> DoubanClient:
    """获取豆瓣客户端实例"""
    global _douban_client
    if _douban_client is None:
        _douban_client = DoubanClient()
    return _douban_client
