"""
刷流任务API路由
"""

from flask import Blueprint, request, jsonify

from mediaflow.brushtask import get_brush_task_manager, BrushTaskConfig
from mediaflow.brushtask.task import BrushTaskState
from mediaflow.web.auth import require_auth


brush_task_bp = Blueprint("brushtask", __name__)


@brush_task_bp.route("/", methods=["GET"])
@require_auth
def get_tasks():
    """获取所有刷流任务"""
    manager = get_brush_task_manager()
    tasks = manager.get_tasks()

    return jsonify({
        "code": 0,
        "data": [
            {
                "id": task.id,
                "name": task.name,
                "site_id": task.site_id,
                "downloader_id": task.downloader_id,
                "interval": task.interval,
                "state": task.state.value,
                "enabled": task.enabled,
            }
            for task in tasks
        ]
    })


@brush_task_bp.route("/<int:task_id>", methods=["GET"])
@require_auth
def get_task(task_id: int):
    """获取指定任务"""
    manager = get_brush_task_manager()
    task = manager.get_task(task_id)

    if not task:
        return jsonify({"code": 404, "message": "Task not found"}), 404

    stats = manager.get_statistics(task_id)

    return jsonify({
        "code": 0,
        "data": {
            "id": task.id,
            "name": task.name,
            "site_id": task.site_id,
            "downloader_id": task.downloader_id,
            "interval": task.interval,
            "state": task.state.value,
            "filter_rule": task.filter_rule,
            "enabled": task.enabled,
            "statistics": {
                "total_downloaded": stats.total_downloaded if stats else 0,
                "total_seeding": stats.total_seeding if stats else 0,
                "total_deleted": stats.total_deleted if stats else 0,
                "total_failed": stats.total_failed if stats else 0,
            } if stats else None
        }
    })


@brush_task_bp.route("/", methods=["POST"])
@require_auth
def create_task():
    """创建刷流任务"""
    data = request.get_json()

    task = BrushTaskConfig(
        name=data.get("name", "新任务"),
        site_id=data.get("site_id", 0),
        downloader_id=data.get("downloader_id", 0),
        interval=data.get("interval", "30"),
        state=BrushTaskState(data.get("state", "S")),
        filter_rule=data.get("filter_rule"),
        enabled=data.get("enabled", True),
    )

    manager = get_brush_task_manager()
    task_id = manager.create_task(task)

    if task_id:
        return jsonify({"code": 0, "data": {"id": task_id}})
    else:
        return jsonify({"code": 500, "message": "Failed to create task"}), 500


@brush_task_bp.route("/<int:task_id>", methods=["PUT"])
@require_auth
def update_task(task_id: int):
    """更新刷流任务"""
    data = request.get_json()

    manager = get_brush_task_manager()
    existing = manager.get_task(task_id)
    if not existing:
        return jsonify({"code": 404, "message": "Task not found"}), 404

    task = BrushTaskConfig(
        id=task_id,
        name=data.get("name", existing.name),
        site_id=data.get("site_id", existing.site_id),
        downloader_id=data.get("downloader_id", existing.downloader_id),
        interval=data.get("interval", existing.interval),
        state=BrushTaskState(data.get("state", existing.state.value)),
        filter_rule=data.get("filter_rule", existing.filter_rule),
        enabled=data.get("enabled", existing.enabled),
    )

    if manager.update_task(task_id, task):
        return jsonify({"code": 0, "message": "Task updated"})
    else:
        return jsonify({"code": 500, "message": "Failed to update task"}), 500


@brush_task_bp.route("/<int:task_id>", methods=["DELETE"])
@require_auth
def delete_task(task_id: int):
    """删除刷流任务"""
    manager = get_brush_task_manager()

    if manager.delete_task(task_id):
        return jsonify({"code": 0, "message": "Task deleted"})
    else:
        return jsonify({"code": 500, "message": "Failed to delete task"}), 500


@brush_task_bp.route("/<int:task_id>/start", methods=["POST"])
@require_auth
def start_task(task_id: int):
    """启动任务"""
    manager = get_brush_task_manager()

    if manager.start_task(task_id):
        return jsonify({"code": 0, "message": "Task started"})
    else:
        return jsonify({"code": 500, "message": "Failed to start task"}), 500


@brush_task_bp.route("/<int:task_id>/stop", methods=["POST"])
@require_auth
def stop_task(task_id: int):
    """停止任务"""
    manager = get_brush_task_manager()

    if manager.stop_task(task_id):
        return jsonify({"code": 0, "message": "Task stopped"})
    else:
        return jsonify({"code": 500, "message": "Failed to stop task"}), 500


@brush_task_bp.route("/statistics", methods=["GET"])
@require_auth
def get_statistics():
    """获取所有任务统计"""
    manager = get_brush_task_manager()
    stats = manager.get_all_statistics()

    return jsonify({
        "code": 0,
        "data": {
            task_id: {
                "total_downloaded": s.total_downloaded,
                "total_seeding": s.total_seeding,
                "total_deleted": s.total_deleted,
                "total_failed": s.total_failed,
            }
            for task_id, s in stats.items()
        }
    })
