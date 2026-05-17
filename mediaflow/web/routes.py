"""
API路由注册
"""

from flask import Flask, jsonify, request
from typing import Callable

from mediaflow.utils.cli import getLogger
from mediaflow.web.routes import (
    brush_task_bp,
    downloader_bp,
    search_bp,
    site_bp,
    subscription_bp,
    system_bp,
)


logger = getLogger("web")


def register_routes(app: Flask) -> None:
    """注册所有路由"""

    app.register_blueprint(brush_task_bp, url_prefix="/api/brushtask")
    app.register_blueprint(downloader_bp, url_prefix="/api/downloader")
    app.register_blueprint(search_bp, url_prefix="/api/search")
    app.register_blueprint(site_bp, url_prefix="/api/site")
    app.register_blueprint(subscription_bp, url_prefix="/api/subscription")
    app.register_blueprint(system_bp, url_prefix="/api/system")

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """健康检查"""
        return jsonify({
            "status": "healthy",
            "service": "MediaFlow"
        })

    @app.errorhandler(404)
    def not_found(error):
        """404错误处理"""
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found"
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """500错误处理"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "An internal error occurred"
        }), 500

    logger.info("API routes registered")
