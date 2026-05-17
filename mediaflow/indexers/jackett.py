"""
Jackett 索引器
"""

import requests
from typing import List, Dict, Any, Optional

from mediaflow.utils.cli import getLogger
from mediaflow.indexers.base import IndexerBase, TorrentResult, IndexerConfig


logger = getLogger("jackett")


class JackettIndexer(IndexerBase):
    """Jackett 索引器"""

    def __init__(self, config: IndexerConfig) -> None:
        super().__init__(config)
        self._session = None

    def _get_session(self) -> requests.Session:
        """获取会话"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "MediaFlow/1.0"
            })
        return self._session

    def search(self, keyword: str, **kwargs) -> List[TorrentResult]:
        """搜索种子"""
        try:
            params = {
                "apikey": self.config.api_key,
                "Query": keyword,
                "Category": kwargs.get("category", ""),
            }

            limit = kwargs.get("limit", 100)
            if limit:
                params["Limit"] = limit

            response = self._get_session().get(
                f"{self.config.url}/api/v2.0/indexers/all/results",
                params=params,
                timeout=self.config.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_results(data)
            else:
                logger.error(f"Jackett 搜索失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Jackett 搜索异常: {e}")
            return []

    def _parse_results(self, data: Dict) -> List[TorrentResult]:
        """解析结果"""
        results = []
        for item in data.get("Results", []):
            try:
                result = TorrentResult(
                    title=item.get("Title", ""),
                    size=self.parse_size(item.get("Size", "")),
                    seeders=self.parse_number(item.get("Seeders", 0)),
                    leechers=self.parse_number(item.get("Peers", 0)),
                    download_url=item.get("Link", ""),
                    info_page=item.get("Guid", ""),
                    indexer=item.get("Indexer", self.config.name),
                    category=item.get("CategoryDesc", ""),
                    imdb_id=self._extract_imdb(item.get("Imdb")),
                    tags=item.get("Tags", "").split(",") if item.get("Tags") else [],
                    description=item.get("Description", ""),
                )
                results.append(result)
            except Exception as e:
                logger.error(f"解析结果失败: {e}")
                continue
        return results

    def _extract_imdb(self, imdb_str: str) -> Optional[str]:
        """提取IMDb ID"""
        if not imdb_str:
            return None
        imdb_str = str(imdb_str).strip()
        if imdb_str.startswith("tt"):
            return imdb_str
        return f"tt{imdb_str.zfill(7)}" if imdb_str.isdigit() else None

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            response = self._get_session().get(
                f"{self.config.url}/api/v2.0/indexers/all/results",
                params={"apikey": self.config.api_key, "Query": "test"},
                timeout=self.config.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Jackett 连接测试失败: {e}")
            return False

    def get_indexers(self) -> List[str]:
        """获取可用索引器列表"""
        try:
            response = self._get_session().get(
                f"{self.config.url}/api/v2.0/indexers",
                params={"apikey": self.config.api_key},
                timeout=self.config.timeout
            )
            if response.status_code == 200:
                data = response.json()
                return [idx.get("id") for idx in data]
        except Exception as e:
            logger.error(f"获取索引器列表失败: {e}")
        return []

    def search_specific_indexer(self, indexer_id: str, keyword: str, **kwargs) -> List[TorrentResult]:
        """在指定索引器搜索"""
        try:
            params = {
                "apikey": self.config.api_key,
                "Query": keyword,
                "Tracker": indexer_id,
            }

            limit = kwargs.get("limit", 100)
            if limit:
                params["Limit"] = limit

            response = self._get_session().get(
                f"{self.config.url}/api/v2.0/indexers/all/results",
                params=params,
                timeout=self.config.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_results(data)
            return []

        except Exception as e:
            logger.error(f"指定索引器搜索失败: {e}")
            return []
