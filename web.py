"""
Frontier Tracker - Web 服务入口

运行方式:
    python web.py
    或
    uvicorn web:app --reload
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import os
from contextlib import asynccontextmanager

from src.api import router
from src.config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 初始化认证数据库
    from src.auth import init_auth_db
    init_auth_db()
    yield
    # 清理资源（如果需要）


# 创建 FastAPI 应用
app = FastAPI(
    title="Frontier Flight Tracker",
    description="Track Frontier Airlines flight prices",
    version="1.0.0",
    lifespan=lifespan
)

# 挂载静态文件目录
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """主页 - 返回前端界面"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <html>
    <head><title>Frontier Tracker</title></head>
    <body>
        <h1>Frontier Flight Tracker</h1>
        <p>Static files not found. Please run <code>python -m src.setup</code> first.</p>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "frontier-tracker"}


# 挂载 API 路由
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
