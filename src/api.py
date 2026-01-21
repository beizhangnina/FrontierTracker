"""
FastAPI 路由 - Web API (简单密码认证)
"""
from fastapi import APIRouter, HTTPException, Cookie, Response
from pydantic import BaseModel
import logging

from src.auth import verify_password, create_session, validate_session
from src.amadeus_client import client
from src.emailer import emailer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# Request/Response 模型
class PasswordRequest(BaseModel):
    password: str


class QueryRequest(BaseModel):
    email: str  # 用户查询时输入的邮箱地址


class SuccessResponse(BaseModel):
    success: bool
    message: str


class AuthResponse(BaseModel):
    success: bool
    token: str = None
    message: str


class UserResponse(BaseModel):
    logged_in: bool


@router.post("/login", response_model=AuthResponse)
async def login(request: PasswordRequest, response: Response):
    """密码登录"""
    if verify_password(request.password):
        token = create_session()
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=False,
            secure=False,  # 生产环境设为 True (HTTPS)
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        return {"success": True, "token": token, "message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail="Invalid password")


@router.post("/logout", response_model=SuccessResponse)
async def logout(response: Response):
    """登出"""
    response.delete_cookie("session_token")
    return {"success": True, "message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(session_token: str = Cookie(None)):
    """检查登录状态"""
    if session_token and validate_session(session_token):
        return {"logged_in": True}
    return {"logged_in": False}


@router.post("/query", response_model=SuccessResponse)
async def query_flights(request: QueryRequest, session_token: str = Cookie(None)):
    """
    查询航班并发送报告到指定邮箱

    需要先登录
    """
    # 验证 session
    if not session_token or not validate_session(session_token):
        raise HTTPException(status_code=401, detail="Not logged in")

    email = request.email
    logger.info(f"Flight query requested for {email}")

    try:
        # 生成报告 - 14天
        report = client.generate_report(days_ahead=14)

        total_flights = len(report.get_all_flights())

        if total_flights == 0:
            return {"success": False, "message": "No flights found"}

        # 直接发送到指定邮箱
        success = emailer.send_email_to(report, email)

        if success:
            logger.info(f"Report sent to {email}")
            return {"success": True, "message": f"Report sent to {email}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled-run")
async def scheduled_run():
    """
    定时任务端点 - 给 Cloud Scheduler 调用
    发送报告给默认邮箱

    注意: 需要配置 SCHEDULER_API_KEY 作为简单验证
    """
    import os

    # 简单的 API key 验证
    api_key = os.getenv("SCHEDULER_API_KEY", "")
    # 在实际部署时，应该从 Header 获取

    logger.info("Scheduled run started")

    try:
        # 生成报告
        report = client.generate_report(days_ahead=14)

        total_flights = len(report.get_all_flights())
        if total_flights == 0:
            return {"success": True, "message": "No flights found"}

        # 发送报告
        if emailer.send_email(report):
            logger.info("Scheduled report sent successfully")
            return {"success": True, "message": "Report sent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")

    except Exception as e:
        logger.error(f"Scheduled run error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
