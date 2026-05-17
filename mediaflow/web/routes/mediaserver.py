"""
媒体服务器 API 路由
"""

from flask import Blueprint, request, jsonify

from mediaflow.mediaserver import get_media_server_manager
from mediaflow.web.auth import require_auth


mediaserver_bp = Blueprint("mediaserver", __name__)


@mediaserver_bp.route("/", methods=["GET"])
@require_auth
def get_servers():
    """获取所有媒体服务器"""
    manager = get_media_server_manager()
    servers = manager.get_all_servers()

    return jsonify({
        "code": 0,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "server_type": s.server_type,
                "host": s.host,
                "port": s.port,
                "enabled": s.enabled,
            }
            for s in servers
        ]
    })


@mediaserver_bp.route("/", methods=["POST"])
@require_auth
def create_server():
    """添加媒体服务器"""
    from mediaflow.mediaserver.manager import MediaServerConfig

    data = request.get_json()

    config = MediaServerConfig(
        id=0,
        name=data.get("name", ""),
        server_type=data.get("server_type", "jellyfin"),
        host=data.get("host", "localhost"),
        port=data.get("port", 8096),
        api_key=data.get("api_key", ""),
        username=data.get("username"),
        enabled=data.get("enabled", True),
    )

    manager = get_media_server_manager()
    server_id = manager.add_server(config)

    if server_id:
        return jsonify({"code": 0, "data": {"id": server_id}})
    else:
        return jsonify({"code": 500, "message": "Failed to add server"}), 500


@mediaserver_bp.route("/<int:server_id>", methods=["GET"])
@require_auth
def get_server(server_id: int):
    """获取指定服务器信息"""
    manager = get_media_server_manager()
    info = manager.get_server_info(server_id)

    if not info:
        return jsonify({"code": 404, "message": "Server not found"}), 404

    return jsonify({
        "code": 0,
        "data": {
            "name": info.name,
            "version": info.version,
            "server_type": info.server_type,
            "is_connected": info.is_connected,
        }
    })


@mediaserver_bp.route("/<int:server_id>/libraries", methods=["GET"])
@require_auth
def get_libraries(server_id: int):
    """获取媒体库列表"""
    manager = get_media_server_manager()
    libraries = manager.get_libraries(server_id)

    return jsonify({
        "code": 0,
        "data": [
            {
                "id": lib.id,
                "name": lib.name,
                "media_type": lib.media_type,
                "item_count": lib.item_count,
                "path": lib.path,
            }
            for lib in libraries
        ]
    })


@mediaserver_bp.route("/<int:server_id>/items", methods=["GET"])
@require_auth
def get_items(server_id: int):
    """获取媒体项目"""
    manager = get_media_server_manager()
    library_id = request.args.get("library_id")
    media_type = request.args.get("media_type")

    items = manager.get_items(server_id, library_id, media_type)

    return jsonify({
        "code": 0,
        "data": [
            {
                "id": item.id,
                "title": item.title,
                "year": item.year,
                "media_type": item.media_type,
                "poster_url": item.poster_url,
                "overview": item.overview,
            }
            for item in items
        ]
    })


@mediaserver_bp.route("/<int:server_id>/search", methods=["GET"])
@require_auth
def search_medias(server_id: int):
    """搜索媒体"""
    manager = get_media_server_manager()
    keyword = request.args.get("keyword", "")
    media_type = request.args.get("media_type")

    if not keyword:
        return jsonify({"code": 400, "message": "Keyword required"}), 400

    items = manager.search_media(server_id, keyword, media_type)

    return jsonify({
        "code": 0,
        "data": [
            {
                "id": item.id,
                "title": item.title,
                "year": item.year,
                "media_type": item.media_type,
                "poster_url": item.poster_url,
            }
            for item in items
        ]
    })


@mediaserver_bp.route("/<int:server_id>/refresh", methods=["POST"])
@require_auth
def refresh_library(server_id: int):
    """刷新媒体库"""
    manager = get_media_server_manager()
    library_id = request.args.get("library_id")

    if manager.refresh_library(server_id, library_id):
        return jsonify({"code": 0, "message": "Refresh started"})
    else:
        return jsonify({"code": 500, "message": "Failed to refresh"}), 500


@mediaserver_bp.route("/<int:server_id>", methods=["DELETE"])
@require_auth
def delete_server(server_id: int):
    """删除服务器"""
    manager = get_media_server_manager()

    if manager.delete_server(server_id):
        return jsonify({"code": 0, "message": "Server deleted"})
    else:
        return jsonify({"code": 500, "message": "Failed to delete server"}), 500
