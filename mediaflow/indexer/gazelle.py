"""
Gazelle站点索引器

用于Gazelle架构的站点（如EMP/PTGEN等）
"""

import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import requests

from mediaflow.indexer.indexer_base import IndexerBase, IndexerResult, IndexerInfo


logger = logging.getLogger(__name__)


class GazelleIndexer(IndexerBase):
    """Gazelle索引器"""

    def __init__(self, info: IndexerInfo) -> None:
        super().__init__(info)
        self._logged_in = False

    def login(self) -> bool:
        """登录站点"""
        if not self.info.cookie:
            logger.error("未提供Cookie")
            return False

        try:
            self._session = requests.Session()
            self._session.headers.update({
                "Cookie": self.info.cookie,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            response = self._session.get(
                f"{self.info.base_url}/index.php",
                timeout=10
            )

            if response.status_code == 200:
                if "logout" in response.text.lower() or "login" not in response.url.lower():
                    self._logged_in = True
                    logger.info(f"登录成功: {self.info.name}")
                    return True

            return False

        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False

    def search(self, keyword: str, **kwargs) -> List[IndexerResult]:
        """搜索种子"""
        if not self._logged_in:
            if not self.login():
                return []

        try:
            search_url = f"{self.info.base_url}/torrents.php"
            params = {
                "searchtext": keyword,
                "filter_cat[0]": 1,
            }

            response = self._session.get(search_url, params=params, timeout=30)
            if response.status_code != 200:
                return []

            return self._parse_results(response.text)

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def _parse_results(self, html: str) -> List[IndexerResult]:
        """解析搜索结果"""
        results = []
        soup = BeautifulSoup(html, "html.parser")

        torrent_rows = soup.select("table.torrent_table tr.torrent-row, table.torrent_table tr.group")
        for row in torrent_rows:
            try:
                title_elem = row.select_one("a.torrent-name, a.title")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                page_url = title_elem.get("href", "")

                size_elem = row.select_one("td.size")
                size = self._parse_size(size_elem.get_text() if size_elem else "0")

                seeders_elem = row.select_one("td.seeders a, span.seeders")
                seeders = self._parse_number(seeders_elem.get_text() if seeders_elem else "0")

                leechers_elem = row.select_one("td.leechers a, span.leechers")
                leechers = self._parse_number(leechers_elem.get_text() if leechers_elem else "0")

                download_links = row.select("a[href*='torrents.php?action=download']")
                download_url = ""
                if download_links:
                    href = download_links[0].get("href", "")
                    if href:
                        if not href.startswith("http"):
                            href = f"{self.info.base_url}/{href}"
                        download_url = href

                result = IndexerResult(
                    title=title,
                    size=size,
                    seeders=seeders,
                    leechers=leechers,
                    download_url=download_url,
                    page_url=page_url,
                    site_name=self.info.name,
                    site_domain=self.info.base_url,
                )
                results.append(result)

            except Exception as e:
                logger.error(f"解析结果行失败: {e}")
                continue

        return results

    def get_torrent_details(self, torrent_id: str) -> Optional[IndexerResult]:
        """获取种子详情"""
        if not self._logged_in:
            if not self.login():
                return None

        try:
            url = f"{self.info.base_url}/torrents.php?torrentid={torrent_id}"
            response = self._session.get(url, timeout=30)

            if response.status_code != 200:
                return None

            return self._parse_details(response.text, torrent_id)

        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return None

    def _parse_details(self, html: str, torrent_id: str) -> Optional[IndexerResult]:
        """解析详情页"""
        soup = BeautifulSoup(html, "html.parser")

        title_elem = soup.select_one("h2.title, h1.title")
        title = title_elem.get_text(strip=True) if title_elem else ""

        return IndexerResult(
            title=title,
            size=0,
            seeders=0,
            leechers=0,
            download_url="",
            page_url=f"{self.info.base_url}/torrents.php?torrentid={torrent_id}",
            site_name=self.info.name,
            site_domain=self.info.base_url,
        )
