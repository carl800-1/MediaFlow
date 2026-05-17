"""
系统API路由
"""

from flask import Blueprint, jsonify, request

from mediaflow.version import __version__
from mediaflow.utils.cli import getLogger
from mediaflow.message import get_message_center


system_bp = Blueprint("system", __name__)
logger = getLogger("system")


@system_bp.route("/info", methods=["GET"])
def get_info():
    """获取系统信息"""
    return jsonify({
        "code": 0,
        "data": {
            "name": "MediaFlow",
            "version": __version__,
            "description": "新一代NAS媒体库智能管理系统",
        }
    })


@system_bp.route("/config", methods=["GET"])
def get_config():
    """获取配置（公开部分）"""
    from mediaflow.utils.config import get_config
    config = get_config()

    return jsonify({
        "code": 0,
        "data": {
            "app": {
                "host": config.app.host,
                "port": config.app.port,
                "debug": config.app.debug,
                "timezone": config.app.timezone,
            },
            "database": {
                "type": config.database.type,
            },
            "notification": {
                "enabled": config.notification.enabled,
            }
        }
    })


@system_bp.route("/notification/test", methods=["POST"])
def test_notification():
    """测试通知"""
    data = request.get_json()
    title = data.get("title", "测试通知")
    content = data.get("content", "这是一条测试消息")
    channels = data.get("channels")

    center = get_message_center()
    results = center.send(title, content, channels)

    success = all(r.success for r in results)
    return jsonify({
        "code": 0,
        "data": {
            "success": success,
            "results": [
                {
                    "channel": r.channel,
                    "success": r.success,
                    "message": r.message,
                }
                for r in results
            ]
        }
    })


@system_bp.route("/notification/status", methods=["GET"])
def notification_status():
    """获取通知渠道状态"""
    center = get_message_center()
    channels = center.get_channels()
    status = center.get_channel_status()

    return jsonify({
        "code": 0,
        "data": {
            "channels": [
                {
                    "name": name,
                    "enabled": status.get(name, False),
                }
                for name in channels
            ]
        }
    })


@system_bp.route("/notification/<channel>/enable", methods=["POST"])
def enable_notification(channel: str):
    """启用通知渠道"""
    center = get_message_center()

    if center.enable_channel(channel):
        return jsonify({"code": 0, "message": "Channel enabled"})
    else:
        return jsonify({"code": 404, "message": "Channel not found"}), 404


@system_bp.route("/notification/<channel>/disable", methods=["POST"])
def disable_notification(channel: str):
    """禁用通知渠道"""
    center = get_message_center()

    if center.disable_channel(channel):
        return jsonify({"code": 0, "message": "Channel disabled"})
    else:
        return jsonify({"code": 404, "message": "Channel not found"}), 404


@system_bp.route("/log", methods=["GET"])
def get_logs():
    """获取日志"""
    lines = request.args.get("lines", 100, type=int)

    try:
        log_file = request.args.get("file", "logs/mediaflow.log")
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            return jsonify({
                "code": 0,
                "data": {
                    "logs": all_lines[-lines:],
                    "total": len(all_lines),
                }
            })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500
