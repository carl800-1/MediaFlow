"""
搜索引擎

聚合多个索引器进行搜索
"""

import re
import threading
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime

from mediaflow.utils.cli import getLogger
from mediaflow.database import get_database
from mediaflow.search.indexer import TorrentInfo, SearchQuery, SearchResult
from mediaflow.media.meta import MetaParser


logger = getLogger("search")


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    year: Optional[int]
    media_type: str
    tmdb_id: Optional[int]
    imdb_id: Optional[str]
    poster: Optional[str]
    overview: str
    torrents: List[TorrentInfo]
    score: float = 0.0

    def __post_init__(self):
        if self.torrents is None:
            self.torrents = []


class SearchEngine:
    """搜索引擎"""

    _instance: Optional["SearchEngine"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._indexers: Dict[str, Any] = {}
        self._db = get_database()
        self._meta_parser = MetaParser()
        self._search_history: List[SearchQuery] = []
        self._callbacks: List[Callable[[SearchResult], None]] = []

    @classmethod
    def get_instance(cls) -> "SearchEngine":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def register_indexer(self, name: str, indexer: Any) -> None:
        """注册索引器"""
        self._indexers[name] = indexer
        logger.info(f"注册索引器: {name}")

    def unregister_indexer(self, name: str) -> None:
        """注销索引器"""
        if name in self._indexers:
            del self._indexers[name]
            logger.info(f"注销索引器: {name}")

    def search(
        self,
        keyword: str,
        media_type: Optional[str] = None,
        site: Optional[str] = None,
        year: Optional[int] = None,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[SearchResult]:
        """
        执行搜索

        Args:
            keyword: 搜索关键词
            media_type: 媒体类型 (movie/tv)
            site: 限定站点
            year: 年份
            season: 季号
            episode: 集号
            page: 页码
            page_size: 每页数量

        Returns:
            搜索结果列表
        """
        query = SearchQuery(
            keyword=keyword,
            media_type=media_type,
            site=site,
            year=year,
            season=season,
            episode=episode,
            page=page,
            page_size=page_size,
        )

        self._search_history.append(query)
        logger.info(f"执行搜索: {keyword}")

        meta_info = self._meta_parser.parse(keyword)
        results: List[SearchResult] = []

        threads = []
        results_lock = threading.Lock()

        def search_indexer(name: str, indexer: Any) -> None:
            try:
                indexer_results = indexer.search(query)
                with results_lock:
                    results.extend(indexer_results)
            except Exception as e:
                logger.error(f"索引器 {name} 搜索失败: {e}")

        if site:
            if site in self._indexers:
                search_indexer(site, self._indexers[site])
        else:
            for name, indexer in self._indexers.items():
                thread = threading.Thread(
                    target=search_indexer,
                    args=(name, indexer),
                    daemon=True
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join(timeout=30)

        for result in results:
            result.score = self._calculate_score(result, meta_info)

        results.sort(key=lambda x: x.score, reverse=True)

        return results[:page_size]

    def _calculate_score(self, result: SearchResult, meta_info: Any) -> float:
        """计算搜索结果相关性分数"""
        score = 0.0

        if result.seeders > 1000:
            score += 10
        elif result.seeders > 100:
            score += 5

        if result.imdb_id and meta_info and hasattr(meta_info, 'imdb_id'):
            if result.imdb_id == meta_info.imdb_id:
                score += 50

        if result.tmdb_id and meta_info and hasattr(meta_info, 'tmdb_id'):
            if result.tmdb_id == meta_info.tmdb_id:
                score += 50

        title_similarity = self._calculate_title_similarity(
            result.title,
            meta_info.title if meta_info else ""
        )
        score += title_similarity * 20

        return score

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """计算标题相似度"""
        if not title1 or not title2:
            return 0.0

        title1 = re.sub(r'[^\w]', '', title1.lower())
        title2 = re.sub(r'[^\w]', '', title2.lower())

        if title1 == title2:
            return 1.0

        common_chars = set(title1) & set(title2)
        if not common_chars:
            return 0.0

        similarity = len(common_chars) / max(len(set(title1)), len(set(title2)))
        return similarity

    def get_search_history(self, limit: int = 50) -> List[SearchQuery]:
        """获取搜索历史"""
        return self._search_history[-limit:]

    def clear_history(self) -> None:
        """清空搜索历史"""
        self._search_history.clear()
        logger.info("搜索历史已清空")

    def add_callback(self, callback: Callable[[SearchResult], None]) -> None:
        """添加搜索结果回调"""
        self._callbacks.append(callback)

    def _notify_callbacks(self, result: SearchResult) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")

    def get_indexers(self) -> List[str]:
        """获取已注册的索引器列表"""
        return list(self._indexers.keys())

    def get_indexer_status(self) -> Dict[str, Dict[str, Any]]:
        """获取索引器状态"""
        status = {}
        for name, indexer in self._indexers.items():
            status[name] = {
                "name": name,
                "enabled": getattr(indexer, "enabled", True),
                "last_search": getattr(indexer, "last_search_time", None),
            }
        return status


_global_search_engine: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    """获取全局搜索引擎"""
    global _global_search_engine
    if _global_search_engine is None:
        _global_search_engine = SearchEngine.get_instance()
    return _global_search_engine
