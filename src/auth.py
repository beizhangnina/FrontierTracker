"""
用户认证模块 - 邮箱验证码登录
"""
import os
import sqlite3
import random
import string
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer
from src.config import config

# Session 配置
SECRET_KEY = os.getenv("SECRET_KEY", "frontier-tracker-secret-key-change-in-production")
SESSION_EXPIRY_HOURS = 24 * 7  # 7 days
CODE_EXPIRY_MINUTES = 10  # 10 minutes

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "users.db")


def get_db_connection():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    """初始化认证数据库"""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verification_codes (
            email TEXT,
            code TEXT,
            expires_at TIMESTAMP,
            PRIMARY KEY (email, code)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            email TEXT,
            expires_at TIMESTAMP
        )
    """)
    # 清理过期会话
    conn.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")
    conn.commit()
    conn.close()


def generate_verification_code():
    """生成 6 位验证码"""
    return ''.join(random.choices(string.digits, k=6))


def send_verification_code(email: str) -> dict:
    """
    发送验证码到用户邮箱

    Returns:
        dict: {"success": bool, "message": str}
    """
    try:
        # 验证邮箱格式
        if '@' not in email or '.' not in email.split('@')[1]:
            return {"success": False, "message": "Invalid email format"}

        # 生成验证码
        code = generate_verification_code()
        expires_at = datetime.now() + timedelta(minutes=CODE_EXPIRY_MINUTES)

        # 保存到数据库
        conn = get_db_connection()
        # 清除该邮箱的旧验证码
        conn.execute("DELETE FROM verification_codes WHERE email = ?", (email,))
        # 保存新验证码
        conn.execute(
            "INSERT INTO verification_codes (email, code, expires_at) VALUES (?, ?, ?)",
            (email, code, expires_at.strftime("%Y-%m-%d %H:%M:%S"))
        )

        # 确保用户存在
        conn.execute(
            "INSERT OR IGNORE INTO users (email, verified) VALUES (?, 0)",
            (email,)
        )
        conn.commit()
        conn.close()

        # 发送邮件
        _send_code_email(email, code)

        return {"success": True, "message": "Verification code sent"}

    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def _send_code_email(email: str, code: str):
    """发送验证码邮件"""
    try:
        # 使用配置的 Gmail 设置
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Frontier Tracker - Verification Code"
        msg["From"] = config.gmail_user
        msg["To"] = email

        html = f"""
        <html>
        <body>
            <h2>🔐 Frontier Tracker Login</h2>
            <p>Your verification code is:</p>
            <p style="font-size: 24px; font-weight: bold; color: #1a365d; letter-spacing: 3px;">
                {code}
            </p>
            <p style="color: #718096; font-size: 14px;">
                This code will expire in {CODE_EXPIRY_MINUTES} minutes.
            </p>
            <p style="color: #718096; font-size: 14px;">
                If you didn't request this code, please ignore this email.
            </p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(config.gmail_user, config.gmail_app_password)
            server.send_message(msg)

    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")


def verify_code(email: str, code: str) -> dict:
    """
    验证验证码并创建会话

    Returns:
        dict: {"success": bool, "token": str or None, "message": str}
    """
    try:
        conn = get_db_connection()

        # 查找验证码
        cursor = conn.execute(
            "SELECT * FROM verification_codes WHERE email = ? AND code = ? AND expires_at > datetime('now')",
            (email, code)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {"success": False, "token": None, "message": "Invalid or expired code"}

        # 删除已使用的验证码
        conn.execute("DELETE FROM verification_codes WHERE email = ? AND code = ?", (email, code))

        # 标记用户已验证
        conn.execute("UPDATE users SET verified = 1 WHERE email = ?", (email,))

        # 创建会话
        token = create_session(email)

        conn.commit()
        conn.close()

        return {"success": True, "token": token, "message": "Login successful"}

    except Exception as e:
        return {"success": False, "token": None, "message": f"Error: {str(e)}"}


def create_session(email: str) -> str:
    """创建会话 token"""
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    token = serializer.dumps(email)

    expires_at = datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)

    conn = get_db_connection()
    # 删除该用户的旧会话
    conn.execute("DELETE FROM sessions WHERE email = ?", (email,))
    # 保存新会话
    conn.execute(
        "INSERT INTO sessions (token, email, expires_at) VALUES (?, ?, ?)",
        (token, email, expires_at.strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

    return token


def validate_session(token: str) -> dict:
    """
    验证会话 token

    Returns:
        dict: {"valid": bool, "email": str or None}
    """
    try:
        if not token:
            return {"valid": False, "email": None}

        serializer = URLSafeTimedSerializer(SECRET_KEY)
        email = serializer.loads(token, max_age=SESSION_EXPIRY_HOURS * 3600)

        # 检查数据库中的会话
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE token = ? AND expires_at > datetime('now')",
            (token,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {"valid": True, "email": email}
        else:
            return {"valid": False, "email": None}

    except Exception:
        return {"valid": False, "email": None}


def logout(token: str) -> bool:
    """登出用户"""
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# 初始化数据库
init_auth_db()
