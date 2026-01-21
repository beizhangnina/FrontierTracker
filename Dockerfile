# Frontier Tracker - Dockerfile for Google Cloud Run
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 设置 Python 路径
ENV PYTHONPATH=/app

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8080

# 默认命令 - 运行 Web 服务器
CMD ["uvicorn", "web:app", "--host", "0.0.0.0", "--port", "8080"]
