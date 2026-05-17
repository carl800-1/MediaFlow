"""
Flask应用工厂
"""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS


def create_app(config_path: str = "config/config.yaml") -> Flask:
    """
    创建Flask应用

    Args:
        config_path: 配置文件路径

    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "mediaflow-secret-key"
    app.config["JSON_AS_ASCII"] = False

    frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
    static_path = os.path.join(frontend_path, "static")
    templates_path = os.path.join(frontend_path, "templates")

    @app.route("/")
    def index():
        return send_from_directory(templates_path, "index.html")

    @app.route("/static/<path:filename>")
    def serve_static(filename):
        return send_from_directory(static_path, filename)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from mediaflow.web.routes import register_routes
    register_routes(app)

    return app


def run_app(host: str = "0.0.0.0", port: int = 3000, debug: bool = False) -> None:
    """
    运行应用

    Args:
        host: 主机地址
        port: 端口号
        debug: 调试模式
    """
    app = create_app()
    app.run(host=host, port=port, debug=debug)
