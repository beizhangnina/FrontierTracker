"""
FastAPI 路由 - Web API
"""
from fastapi import APIRouter, HTTPException, Cookie, Response
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from src.auth import (
    send_verification_code,
    verify_code,
    validate_session,
    logout as auth_logout
)
from src.amadeus_client import client
from src.emailer import emailer
from src.models import FlightReport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# Request/Response 模型
class SendCodeRequest(BaseModel):
    email: EmailStr


class VerifyRequest(BaseModel):
    email: EmailStr
    code: str


class QueryRequest(BaseModel):
    email: EmailStr


class SuccessResponse(BaseModel):
    success: bool
    message: str


class VerifyResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str


class UserResponse(BaseModel):
    logged_in: bool
    email: Optional[str] = None


@router.post("/send-code", response_model=SuccessResponse)
async def send_code(request: SendCodeRequest):
    """发送验证码到用户邮箱"""
    result = send_verification_code(request.email)
    if result["success"]:
        return {"success": True, "message": "Verification code sent to your email"}
    else:
        raise HTTPException(status_code=400, detail=result["message"])


@router.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest, response: Response):
    """验证验证码并登录"""
    result = verify_code(request.email, request.code)
    if result["success"]:
        # 设置 cookie
        response.set_cookie(
            key="session_token",
            value=result["token"],
            httponly=True,
            secure=False,  # 生产环境设为 True (HTTPS)
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        return {"success": True, "token": result["token"], "message": "Login successful"}
    else:
        raise HTTPException(status_code=400, detail=result["message"])


@router.post("/logout", response_model=SuccessResponse)
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """登出"""
    if session_token:
        auth_logout(session_token)
    response.delete_cookie("session_token")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(session_token: Optional[str] = Cookie(None)):
    """获取当前登录用户"""
    if not session_token:
        return {"logged_in": False, "email": None}

    result = validate_session(session_token)
    if result["valid"]:
        return {"logged_in": True, "email": result["email"]}
    else:
        return {"logged_in": False, "email": None}


@router.post("/query", response_model=SuccessResponse)
async def query_flights(request: QueryRequest, session_token: Optional[str] = Cookie(None)):
    """
    查询航班并发送报告到用户邮箱

    注意: 此接口需要用户已登录
    """
    # 验证 session
    user_result = validate_session(session_token)
    if not user_result["valid"]:
        raise HTTPException(status_code=401, detail="Not logged in")

    # 使用登录用户的邮箱，而不是请求中的邮箱
    email = user_result["email"]
    logger.info(f"User {email} requested flight query")

    try:
        # 生成报告 - 14天
        report = client.generate_report(days_ahead=14)

        total_flights = len(report.get_all_flights())

        if total_flights == 0:
            return {"success": False, "message": "No flights found"}

        # 临时修改发送邮箱为用户邮箱
        original_to_email = emailer.to_email
        emailer.to_email = email

        # 发送邮件
        success = emailer.send_email(report)

        # 恢复原设置
        emailer.to_email = original_to_email

        if success:
            logger.info(f"Report sent to {email}")
            return {"success": True, "message": f"Report sent to {email}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled-run", response_model=SuccessResponse)
async def scheduled_run():
    """
    定时任务端点 - 给 Cloud Scheduler 调用
    发送报告给所有已验证的用户

    注意: 此端点不需要认证，但应该通过 Cloud Scheduler 内部调用
    """
    import os
    from src.database import get_db_connection

    # 验证调用来源 (简单的 API key 验证)
    api_key = os.getenv("SCHEDULER_API_KEY", "change-me-in-production")
    # 注意: 实际部署时应该在 Header 中传递 API key

    logger.info("Scheduled run started")

    try:
        # 获取所有已验证用户的邮箱
        from src.auth import get_db_connection
        conn = get_db_connection()
        cursor = conn.execute("SELECT email FROM users WHERE verified = 1")
        users = [row["email"] for row in cursor.fetchall()]
        conn.close()

        if not users:
            return {"success": True, "message": "No verified users"}

        # 生成报告
        report = client.generate_report(days_ahead=14)

        total_flights = len(report.get_all_flights())
        if total_flights == 0:
            return {"success": True, "message": "No flights found"}

        # 发送报告给所有用户
        success_count = 0
        for email in users:
            try:
                original_to_email = emailer.to_email
                emailer.to_email = email
                if emailer.send_email(report):
                    success_count += 1
                emailer.to_email = original_to_email
            except Exception as e:
                logger.error(f"Failed to send to {email}: {e}")

        logger.info(f"Scheduled run completed: sent to {success_count}/{len(users)} users")
        return {"success": True, "message": f"Sent to {success_count} users"}

    except Exception as e:
        logger.error(f"Scheduled run error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
