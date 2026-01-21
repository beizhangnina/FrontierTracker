"""
简单密码认证 - 使用预设密码
"""
import os
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta

# 预设密码
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "3390")

# Session 配置
SECRET_KEY = os.getenv("SECRET_KEY", "frontier-tracker-secret-key")
SESSION_EXPIRY_HOURS = 24 * 7  # 7 days


def verify_password(password: str) -> bool:
    """验证密码"""
    return password == ACCESS_PASSWORD


def create_session() -> str:
    """创建会话 token"""
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps("authenticated")


def validate_session(token: str) -> bool:
    """验证会话 token"""
    if not token:
        return False
    try:
        serializer = URLSafeTimedSerializer(SECRET_KEY)
        result = serializer.loads(token, max_age=SESSION_EXPIRY_HOURS * 3600)
        return result == "authenticated"
    except Exception:
        return False
