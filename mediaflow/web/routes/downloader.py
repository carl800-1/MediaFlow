"""
下载器API路由
"""

from flask import Blueprint, request, jsonify

from mediaflow.downloader import get_downloader_manager
from mediaflow.downloader.client import DownloaderConfig
from mediaflow.web.auth import require_auth


downloader_bp = Blueprint("downloader", __name__)


@downloader_bp.route("/", methods=["GET"])
@require_auth
def get_downloaders():
    """获取所有下载器"""
    manager = get_downloader_manager()
    downloaders = manager.get_all_downloaders_info()

    return jsonify({
        "code": 0,
        "data": [
            {
                "id": d.id,
                "name": d.name,
                "type": d.type,
                "host": d.host,
                "port": d.port,
                "enabled": d.enabled,
                "torrents_count": d.torrents_count,
                "download_speed": d.download_speed,
                "upload_speed": d.upload_speed,
            }
            for d in downloaders
        ]
    })


@downloader_bp.route("/<int:downloader_id>", methods=["GET"])
@require_auth
def get_downloader(downloader_id: int):
    """获取指定下载器"""
    manager = get_downloader_manager()
    info = manager.get_downloader_info(downloader_id)

    if not info:
        return jsonify({"code": 404, "message": "Downloader not found"}), 404

    return jsonify({
        "code": 0,
        "data": {
            "id": info.id,
            "name": info.name,
            "type": info.type,
            "host": info.host,
            "port": info.port,
            "enabled": info.enabled,
            "torrents_count": info.torrents_count,
            "download_speed": info.download_speed,
            "upload_speed": info.upload_speed,
        }
    })


@downloader_bp.route("/", methods=["POST"])
@require_auth
def create_downloader():
    """添加下载器"""
    data = request.get_json()

    config = DownloaderConfig(
        name=data.get("name", "New Downloader"),
        type=data.get("type", "qbittorrent"),
        host=data.get("host", "localhost"),
        port=data.get("port", 8080),
        username=data.get("username"),
        password=data.get("password"),
        enabled=data.get("enabled", True),
    )

    manager = get_downloader_manager()
    downloader_id = manager.add_downloader(config)

    if downloader_id:
        return jsonify({"code": 0, "data": {"id": downloader_id}})
    else:
        return jsonify({"code": 500, "message": "Failed to add downloader"}), 500


@downloader_bp.route("/<int:downloader_id>", methods=["PUT"])
@require_auth
def update_downloader(downloader_id: int):
    """更新下载器"""
    data = request.get_json()

    config = DownloaderConfig(
        name=data.get("name"),
        type=data.get("type"),
        host=data.get("host"),
        port=data.get("port"),
        username=data.get("username"),
        password=data.get("password"),
        enabled=data.get("enabled", True),
    )

    manager = get_downloader_manager()
    if manager.update_downloader(downloader_id, config):
        return jsonify({"code": 0, "message": "Downloader updated"})
    else:
        return jsonify({"code": 500, "message": "Failed to update downloader"}), 500


@downloader_bp.route("/<int:downloader_id>", methods=["DELETE"])
@require_auth
def delete_downloader(downloader_id: int):
    """删除下载器"""
    manager = get_downloader_manager()

    if manager.delete_downloader(downloader_id):
        return jsonify({"code": 0, "message": "Downloader deleted"})
    else:
        return jsonify({"code": 500, "message": "Failed to delete downloader"}), 500


@downloader_bp.route("/<int:downloader_id>/torrents", methods=["GET"])
@require_auth
def get_torrents(downloader_id: int):
    """获取下载器中的种子"""
    manager = get_downloader_manager()
    downloader = manager.get_downloader(downloader_id)

    if not downloader:
        return jsonify({"code": 404, "message": "Downloader not found"}), 404

    try:
        torrents = downloader.get_torrents()
        return jsonify({
            "code": 0,
            "data": [
                {
                    "hash": t.hash,
                    "name": t.name,
                    "size": t.size,
                    "progress": t.progress,
                    "state": t.state,
                    "seeds": t.seeds,
                    "peers": t.peers,
                    "download_speed": t.download_speed,
                    "upload_speed": t.upload_speed,
                    "ratio": t.ratio,
                    "save_path": t.save_path,
                    "tags": t.tags,
                }
                for t in torrents
            ]
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500


@downloader_bp.route("/<int:downloader_id>/torrent/<hash>/pause", methods=["POST"])
@require_auth
def pause_torrent(downloader_id: int, hash: str):
    """暂停种子"""
    manager = get_downloader_manager()
    downloader = manager.get_downloader(downloader_id)

    if not downloader:
        return jsonify({"code": 404, "message": "Downloader not found"}), 404

    if downloader.pause_torrent(hash):
        return jsonify({"code": 0, "message": "Torrent paused"})
    else:
        return jsonify({"code": 500, "message": "Failed to pause torrent"}), 500


@downloader_bp.route("/<int:downloader_id>/torrent/<hash>/resume", methods=["POST"])
@require_auth
def resume_torrent(downloader_id: int, hash: str):
    """恢复种子"""
    manager = get_downloader_manager()
    downloader = manager.get_downloader(downloader_id)

    if not downloader:
        return jsonify({"code": 404, "message": "Downloader not found"}), 404

    if downloader.resume_torrent(hash):
        return jsonify({"code": 0, "message": "Torrent resumed"})
    else:
        return jsonify({"code": 500, "message": "Failed to resume torrent"}), 500


@downloader_bp.route("/<int:downloader_id>/torrent/<hash>", methods=["DELETE"])
@require_auth
def delete_torrent(downloader_id: int, hash: str):
    """删除种子"""
    data = request.get_json() or {}
    delete_files = data.get("delete_files", False)

    manager = get_downloader_manager()
    downloader = manager.get_downloader(downloader_id)

    if not downloader:
        return jsonify({"code": 404, "message": "Downloader not found"}), 404

    if downloader.delete_torrent(hash, delete_files):
        return jsonify({"code": 0, "message": "Torrent deleted"})
    else:
        return jsonify({"code": 500, "message": "Failed to delete torrent"}), 500
