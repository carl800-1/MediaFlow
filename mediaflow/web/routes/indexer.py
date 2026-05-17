"""
索引器 API 路由
"""

from flask import Blueprint, request, jsonify

from mediaflow.indexers import JackettIndexer, ProwlarrIndexer
from mediaflow.indexers.base import IndexerConfig
from mediaflow.web.auth import require_auth


indexer_bp = Blueprint("indexer", __name__)

_indexers = {}


@indexer_bp.route("/", methods=["GET"])
@require_auth
def get_indexers():
    """获取所有索引器"""
    return jsonify({
        "code": 0,
        "data": [
            {
                "id": idx_id,
                "name": idx.config.name,
                "type": idx.config.indexer_type,
                "url": idx.config.url,
                "enabled": idx.config.enabled,
            }
            for idx_id, idx in _indexers.items()
        ]
    })


@indexer_bp.route("/", methods=["POST"])
@require_auth
def create_indexer():
    """添加索引器"""
    data = request.get_json()

    config = IndexerConfig(
        id=len(_indexers) + 1,
        name=data.get("name", ""),
        indexer_type=data.get("type", "jackett"),
        url=data.get("url", ""),
        api_key=data.get("api_key"),
        enabled=data.get("enabled", True),
    )

    if config.indexer_type == "jackett":
        indexer = JackettIndexer(config)
    elif config.indexer_type == "prowlarr":
        indexer = ProwlarrIndexer(config)
    else:
        return jsonify({"code": 400, "message": "Unsupported indexer type"}), 400

    if indexer.test_connection():
        _indexers[config.id] = indexer
        return jsonify({"code": 0, "data": {"id": config.id}})
    else:
        return jsonify({"code": 500, "message": "Failed to connect"}), 500


@indexer_bp.route("/<int:indexer_id>/search", methods=["GET"])
@require_auth
def search(indexer_id: int):
    """搜索"""
    indexer = _indexers.get(indexer_id)
    if not indexer:
        return jsonify({"code": 404, "message": "Indexer not found"}), 404

    keyword = request.args.get("keyword", "")
    if not keyword:
        return jsonify({"code": 400, "message": "Keyword required"}), 400

    results = indexer.search(keyword)

    return jsonify({
        "code": 0,
        "data": [
            {
                "title": r.title,
                "size": r.size,
                "seeders": r.seeders,
                "leechers": r.leechers,
                "download_url": r.download_url,
                "indexer": r.indexer,
                "category": r.category,
            }
            for r in results
        ]
    })


@indexer_bp.route("/<int:indexer_id>", methods=["DELETE"])
@require_auth
def delete_indexer(indexer_id: int):
    """删除索引器"""
    if indexer_id in _indexers:
        del _indexers[indexer_id]
        return jsonify({"code": 0, "message": "Indexer deleted"})
    return jsonify({"code": 404, "message": "Indexer not found"}), 404
