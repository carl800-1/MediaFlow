"""
搜索API路由
"""

from flask import Blueprint, request, jsonify

from mediaflow.search import get_search_engine
from mediaflow.web.auth import require_auth


search_bp = Blueprint("search", __name__)


@search_bp.route("/", methods=["GET"])
@require_auth
def search():
    """执行搜索"""
    keyword = request.args.get("keyword", "")
    if not keyword:
        return jsonify({"code": 400, "message": "Keyword is required"}), 400

    media_type = request.args.get("media_type")
    site = request.args.get("site")
    year = request.args.get("year", type=int)
    season = request.args.get("season", type=int)
    episode = request.args.get("episode", type=int)
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    engine = get_search_engine()
    results = engine.search(
        keyword=keyword,
        media_type=media_type,
        site=site,
        year=year,
        season=season,
        episode=episode,
        page=page,
        page_size=page_size
    )

    return jsonify({
        "code": 0,
        "data": {
            "keyword": keyword,
            "total": len(results),
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "title": r.title,
                    "year": r.year,
                    "media_type": r.media_type,
                    "tmdb_id": r.tmdb_id,
                    "imdb_id": r.imdb_id,
                    "poster": r.poster,
                    "overview": r.overview,
                    "score": r.score,
                    "torrents": [
                        {
                            "hash": t.hash,
                            "title": t.title,
                            "size": t.size,
                            "seeders": t.seeders,
                            "leechers": t.leechers,
                            "site_name": t.site_name,
                            "torrent_url": t.torrent_url,
                        }
                        for t in r.torrents
                    ]
                }
                for r in results
            ]
        }
    })


@search_bp.route("/history", methods=["GET"])
@require_auth
def get_history():
    """获取搜索历史"""
    limit = request.args.get("limit", 50, type=int)

    engine = get_search_engine()
    history = engine.get_search_history(limit)

    return jsonify({
        "code": 0,
        "data": [
            {
                "keyword": h.keyword,
                "media_type": h.media_type,
                "year": h.year,
                "page": h.page,
            }
            for h in history
        ]
    })


@search_bp.route("/history", methods=["DELETE"])
@require_auth
def clear_history():
    """清空搜索历史"""
    engine = get_search_engine()
    engine.clear_history()
    return jsonify({"code": 0, "message": "History cleared"})


@search_bp.route("/indexers", methods=["GET"])
@require_auth
def get_indexers():
    """获取索引器列表"""
    engine = get_search_engine()
    indexers = engine.get_indexers()
    status = engine.get_indexer_status()

    return jsonify({
        "code": 0,
        "data": [
            {
                "name": name,
                "enabled": status[name].get("enabled", True),
                "last_search": status[name].get("last_search"),
            }
            for name in indexers
        ]
    })
