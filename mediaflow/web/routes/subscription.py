"""
订阅API路由
"""

from flask import Blueprint, request, jsonify

from mediaflow.subscribe import get_subscription_manager, SubscriptionInfo
from mediaflow.subscribe.subscription import SubscriptionState, SubscriptionType
from mediaflow.web.auth import require_auth


subscription_bp = Blueprint("subscription", __name__)


@subscription_bp.route("/", methods=["GET"])
@require_auth
def get_subscriptions():
    """获取所有订阅"""
    manager = get_subscription_manager()
    subscriptions = manager.get_all_subscriptions()

    return jsonify({
        "code": 0,
        "data": [
            {
                "id": sub.id,
                "name": sub.name,
                "media_id": sub.media_id,
                "rss_url": sub.rss_url,
                "state": sub.state.value,
                "subscription_type": sub.subscription_type.value,
                "downloader_id": sub.downloader_id,
                "auto_download": sub.auto_download,
                "last_check_time": sub.last_check_time.isoformat() if sub.last_check_time else None,
            }
            for sub in subscriptions
        ]
    })


@subscription_bp.route("/<int:subscription_id>", methods=["GET"])
@require_auth
def get_subscription(subscription_id: int):
    """获取指定订阅"""
    manager = get_subscription_manager()
    sub = manager.get_subscription(subscription_id)

    if not sub:
        return jsonify({"code": 404, "message": "Subscription not found"}), 404

    stats = manager.get_statistics(subscription_id)

    return jsonify({
        "code": 0,
        "data": {
            "id": sub.id,
            "name": sub.name,
            "media_id": sub.media_id,
            "rss_url": sub.rss_url,
            "keywords": sub.keywords,
            "state": sub.state.value,
            "subscription_type": sub.subscription_type.value,
            "downloader_id": sub.downloader_id,
            "save_path": sub.save_path,
            "auto_download": sub.auto_download,
            "filter_rule": sub.filter_rule,
            "interval": sub.interval,
            "last_check_time": sub.last_check_time.isoformat() if sub.last_check_time else None,
            "statistics": {
                "total_items": stats.total_items if stats else 0,
                "downloaded_items": stats.downloaded_items if stats else 0,
                "failed_items": stats.failed_items if stats else 0,
            } if stats else None
        }
    })


@subscription_bp.route("/", methods=["POST"])
@require_auth
def create_subscription():
    """创建订阅"""
    data = request.get_json()

    sub = SubscriptionInfo(
        name=data.get("name", "New Subscription"),
        media_id=data.get("media_id"),
        rss_url=data.get("rss_url"),
        keywords=data.get("keywords"),
        state=SubscriptionState(data.get("state", "Y")),
        subscription_type=SubscriptionType(data.get("type", "rss")),
        downloader_id=data.get("downloader_id"),
        save_path=data.get("save_path"),
        auto_download=data.get("auto_download", True),
        filter_rule=data.get("filter_rule"),
        interval=data.get("interval", 30),
    )

    manager = get_subscription_manager()
    subscription_id = manager.create_subscription(sub)

    if subscription_id:
        return jsonify({"code": 0, "data": {"id": subscription_id}})
    else:
        return jsonify({"code": 500, "message": "Failed to create subscription"}), 500


@subscription_bp.route("/<int:subscription_id>", methods=["PUT"])
@require_auth
def update_subscription(subscription_id: int):
    """更新订阅"""
    data = request.get_json()

    manager = get_subscription_manager()
    existing = manager.get_subscription(subscription_id)
    if not existing:
        return jsonify({"code": 404, "message": "Subscription not found"}), 404

    sub = SubscriptionInfo(
        id=subscription_id,
        name=data.get("name", existing.name),
        media_id=data.get("media_id", existing.media_id),
        rss_url=data.get("rss_url", existing.rss_url),
        keywords=data.get("keywords", existing.keywords),
        state=SubscriptionState(data.get("state", existing.state.value)),
        subscription_type=SubscriptionType(data.get("type", existing.subscription_type.value)),
        downloader_id=data.get("downloader_id", existing.downloader_id),
        save_path=data.get("save_path", existing.save_path),
        auto_download=data.get("auto_download", existing.auto_download),
        filter_rule=data.get("filter_rule", existing.filter_rule),
        interval=data.get("interval", existing.interval),
    )

    if manager.update_subscription(subscription_id, sub):
        return jsonify({"code": 0, "message": "Subscription updated"})
    else:
        return jsonify({"code": 500, "message": "Failed to update subscription"}), 500


@subscription_bp.route("/<int:subscription_id>", methods=["DELETE"])
@require_auth
def delete_subscription(subscription_id: int):
    """删除订阅"""
    manager = get_subscription_manager()

    if manager.delete_subscription(subscription_id):
        return jsonify({"code": 0, "message": "Subscription deleted"})
    else:
        return jsonify({"code": 500, "message": "Failed to delete subscription"}), 500


@subscription_bp.route("/<int:subscription_id>/enable", methods=["POST"])
@require_auth
def enable_subscription(subscription_id: int):
    """启用订阅"""
    manager = get_subscription_manager()

    if manager.enable_subscription(subscription_id):
        return jsonify({"code": 0, "message": "Subscription enabled"})
    else:
        return jsonify({"code": 500, "message": "Failed to enable subscription"}), 500


@subscription_bp.route("/<int:subscription_id>/disable", methods=["POST"])
@require_auth
def disable_subscription(subscription_id: int):
    """禁用订阅"""
    manager = get_subscription_manager()

    if manager.disable_subscription(subscription_id):
        return jsonify({"code": 0, "message": "Subscription disabled"})
    else:
        return jsonify({"code": 500, "message": "Failed to disable subscription"}), 500


@subscription_bp.route("/<int:subscription_id>/refresh", methods=["POST"])
@require_auth
def refresh_subscription(subscription_id: int):
    """手动刷新订阅"""
    manager = get_subscription_manager()
    sub = manager.get_subscription(subscription_id)

    if not sub:
        return jsonify({"code": 404, "message": "Subscription not found"}), 404

    result = manager.fetch_rss(sub)

    return jsonify({
        "code": 0,
        "data": {
            "success": result.success,
            "items_count": len(result.items),
            "message": result.message,
        }
    })
