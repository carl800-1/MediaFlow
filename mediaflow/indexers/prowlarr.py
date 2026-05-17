"""
Prowlarr 索引器
"""

import requests
from typing import List, Dict, Any, Optional

from mediaflow.utils.cli import getLogger
from mediaflow.indexers.base import IndexerBase, TorrentResult, IndexerConfig


logger = getLogger("prowlarr")


class ProwlarrIndexer(IndexerBase):
    """Prowlarr 索引器"""

    def __init__(self, config: IndexerConfig) -> None:
        super().__init__(config)
        self._session = None

    def _get_session(self) -> requests.Session:
        """获取会话"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "MediaFlow/1.0",
                "X-Api-Key": self.config.api_key
            })
        return self._session

    def search(self, keyword: str, **kwargs) -> List[TorrentResult]:
        """搜索种子"""
        try:
            params = {
                "query": keyword,
            }

            categories = kwargs.get("categories")
            if categories:
                params["categories"] = categories

            limit = kwargs.get("limit", 100)
            if limit:
                params["limit"] = limit

            response = self._get_session().get(
                f"{self.config.url}/api/v1/search",
                params=params,
                timeout=self.config.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_results(data)
            else:
                logger.error(f"Prowlarr 搜索失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Prowlarr 搜索异常: {e}")
            return []

    def _parse_results(self, data: List) -> List[TorrentResult]:
        """解析结果"""
        results = []
        for item in data if isinstance(data, list) else []:
            try:
                result = TorrentResult(
                    title=item.get("title", ""),
                    size=self.parse_size(item.get("size", "")),
                    seeders=self.parse_number(item.get("seeders", 0)),
                    leechers=self.parse_number(item.get("leechers", 0)),
                    download_url=self._get_download_url(item),
                    info_page=item.get("guid", ""),
                    indexer=item.get("indexer", self.config.name),
                    category=self._get_category(item),
                    imdb_id=item.get("imdbId"),
                    tmdb_id=item.get("tmdbId"),
                    pubdate=item.get("publishDate"),
                    description=item.get("description", ""),
                )
                results.append(result)
            except Exception as e:
                logger.error(f"解析结果失败: {e}")
                continue
        return results

    def _get_download_url(self, item: Dict) -> str:
        """获取下载链接"""
        for link in item.get("downloadUrl", []) if isinstance(item.get("downloadUrl"), list) else [item.get("downloadUrl")]:
            if link:
                return link
        return ""

    def _get_category(self, item: Dict) -> str:
        """获取分类"""
        categories = item.get("categories", [])
        if categories and isinstance(categories, list):
            return categories[0].get("label", "") if isinstance(categories[0], dict) else str(categories[0])
        return ""

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            response = self._get_session().get(
                f"{self.config.url}/api/v1/indexer",
                timeout=self.config.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Prowlarr 连接测试失败: {e}")
            return False

    def get_indexers(self) -> List[Dict[str, Any]]:
        """获取索引器列表"""
        try:
            response = self._get_session().get(
                f"{self.config.url}/api/v1/indexer",
                timeout=self.config.timeout
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"获取索引器列表失败: {e}")
        return []

    def get_categories(self) -> List[Dict[str, Any]]:
        """获取分类列表"""
        try:
            response = self._get_session().get(
                f"{self.config.url}/api/v1/indexercategory",
                timeout=self.config.timeout
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"获取分类列表失败: {e}")
        return []
