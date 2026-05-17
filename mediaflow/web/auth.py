"""
认证和权限控制
"""

from functools import wraps
from flask import request, jsonify, g
from typing import Callable


def require_auth(f: Callable) -> Callable:
    """
    认证装饰器
    用于需要认证的API
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({
                "code": 401,
                "message": "Authorization header is required"
            }), 401

        if not auth_header.startswith("Bearer "):
            return jsonify({
                "code": 401,
                "message": "Invalid authorization header format"
            }), 401

        token = auth_header[7:]

        if not validate_token(token):
            return jsonify({
                "code": 401,
                "message": "Invalid or expired token"
            }), 401

        g.current_user = get_user_from_token(token)
        return f(*args, **kwargs)

    return decorated_function


def require_admin(f: Callable) -> Callable:
    """
    管理员权限装饰器
    用于需要管理员权限的API
    """
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        user = getattr(g, "current_user", None)

        if not user or not user.get("is_admin"):
            return jsonify({
                "code": 403,
                "message": "Admin permission required"
            }), 403

        return f(*args, **kwargs)

    return decorated_function


def validate_token(token: str) -> bool:
    """
    验证Token
    """
    from mediaflow.utils.config import get_config
    config = get_config()
    expected_token = config.get("auth_token") or "mediaflow-default-token"
    return token == expected_token


def get_user_from_token(token: str) -> dict:
    """
    从Token获取用户信息
    """
    return {
        "id": 1,
        "username": "admin",
        "is_admin": True,
    }


def generate_token() -> str:
    """
    生成Token
    """
    import secrets
    return secrets.token_urlsafe(32)
