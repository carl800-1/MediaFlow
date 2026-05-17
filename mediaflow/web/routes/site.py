"""
站点API路由
"""

from flask import Blueprint, request, jsonify

from mediaflow.sites import get_site_manager, SiteInfo
from mediaflow.web.auth import require_auth


site_bp = Blueprint("site", __name__)


@site_bp.route("/", methods=["GET"])
@require_auth
def get_sites():
    """获取所有站点"""
    manager = get_site_manager()
    sites = manager.get_all_sites()
    stats = manager.get_statistics()

    return jsonify({
        "code": 0,
        "data": {
            "statistics": {
                "total": stats.total_sites,
                "enabled": stats.enabled_sites,
            },
            "sites": [
                {
                    "id": site.id,
                    "name": site.name,
                    "url": site.url,
                    "enabled": site.enabled,
                    "user_class": site.user_class,
                    "user_level": site.user_level,
                    "bonus": site.bonus,
                    "upload": site.upload,
                    "download": site.download,
                    "ratio": site.ratio,
                    "seeding": site.seeding,
                    "leeching": site.leeching,
                }
                for site in sites
            ]
        }
    })


@site_bp.route("/<int:site_id>", methods=["GET"])
@require_auth
def get_site(site_id: int):
    """获取指定站点"""
    manager = get_site_manager()
    site = manager.get_site(site_id)

    if not site:
        return jsonify({"code": 404, "message": "Site not found"}), 404

    return jsonify({
        "code": 0,
        "data": {
            "id": site.id,
            "name": site.name,
            "url": site.url,
            "sign_url": site.sign_url,
            "rss_url": site.rss_url,
            "enabled": site.enabled,
            "user_class": site.user_class,
            "user_level": site.user_level,
            "bonus": site.bonus,
            "upload": site.upload,
            "download": site.download,
            "ratio": site.ratio,
            "seeding": site.seeding,
            "leeching": site.leeching,
            "uploaded_size": site.uploaded_size,
            "downloaded_size": site.downloaded_size,
        }
    })


@site_bp.route("/", methods=["POST"])
@require_auth
def create_site():
    """添加站点"""
    data = request.get_json()

    site = SiteInfo(
        id=0,
        name=data.get("name", ""),
        url=data.get("url", ""),
        cookie=data.get("cookie"),
        sign_url=data.get("sign_url"),
        rss_url=data.get("rss_url"),
        enabled=data.get("enabled", True),
    )

    manager = get_site_manager()
    site_id = manager.add_site(site)

    if site_id:
        return jsonify({"code": 0, "data": {"id": site_id}})
    else:
        return jsonify({"code": 500, "message": "Failed to add site"}), 500


@site_bp.route("/<int:site_id>", methods=["PUT"])
@require_auth
def update_site(site_id: int):
    """更新站点"""
    data = request.get_json()

    manager = get_site_manager()
    existing = manager.get_site(site_id)
    if not existing:
        return jsonify({"code": 404, "message": "Site not found"}), 404

    site = SiteInfo(
        id=site_id,
        name=data.get("name", existing.name),
        url=data.get("url", existing.url),
        cookie=data.get("cookie", existing.cookie),
        sign_url=data.get("sign_url", existing.sign_url),
        rss_url=data.get("rss_url", existing.rss_url),
        enabled=data.get("enabled", existing.enabled),
    )

    if manager.update_site(site_id, site):
        return jsonify({"code": 0, "message": "Site updated"})
    else:
        return jsonify({"code": 500, "message": "Failed to update site"}), 500


@site_bp.route("/<int:site_id>", methods=["DELETE"])
@require_auth
def delete_site(site_id: int):
    """删除站点"""
    manager = get_site_manager()

    if manager.delete_site(site_id):
        return jsonify({"code": 0, "message": "Site deleted"})
    else:
        return jsonify({"code": 500, "message": "Failed to delete site"}), 500


@site_bp.route("/<int:site_id>/signin", methods=["POST"])
@require_auth
def signin(site_id: int):
    """站点签到"""
    manager = get_site_manager()
    result = manager.sign_in(site_id)

    return jsonify({
        "code": 0,
        "data": {
            "site_name": result.site_name,
            "success": result.success,
            "message": result.message,
            "bonus": result.bonus,
        }
    })


@site_bp.route("/signin/all", methods=["POST"])
@require_auth
def signin_all():
    """批量签到所有站点"""
    manager = get_site_manager()
    results = manager.sign_in_all()

    return jsonify({
        "code": 0,
        "data": [
            {
                "site_name": r.site_name,
                "success": r.success,
                "message": r.message,
                "bonus": r.bonus,
            }
            for r in results
        ]
    })


@site_bp.route("/<int:site_id>/cookie", methods=["PUT"])
@require_auth
def update_cookie(site_id: int):
    """更新站点Cookie"""
    data = request.get_json()
    cookie = data.get("cookie", "")

    manager = get_site_manager()
    if manager.update_site_cookie(site_id, cookie):
        return jsonify({"code": 0, "message": "Cookie updated"})
    else:
        return jsonify({"code": 500, "message": "Failed to update cookie"}), 500


@site_bp.route("/statistics", methods=["GET"])
@require_auth
def get_statistics():
    """获取站点统计"""
    manager = get_site_manager()
    stats = manager.get_statistics()

    return jsonify({
        "code": 0,
        "data": {
            "total_sites": stats.total_sites,
            "enabled_sites": stats.enabled_sites,
            "total_upload": stats.total_upload,
            "total_download": stats.total_download,
            "total_seeding": stats.total_seeding,
        }
    })
