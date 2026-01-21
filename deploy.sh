#!/bin/bash
# Frontier Flight Tracker - 部署脚本

set -e

PROJECT_ID="your-project-id"  # 替换为你的 Google Cloud 项目 ID
REGION="us-west1"
SERVICE_NAME="frontier-tracker"
REPO_NAME="frontier-tracker"

echo "=== Frontier Flight Tracker 部署 ==="

# 检查 gcloud 是否已安装
if ! command -v gcloud &> /dev/null; then
    echo "错误: gcloud 未安装"
    echo "请访问: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# 显示当前配置
echo "项目 ID: $PROJECT_ID"
echo "区域: $REGION"
echo "服务名: $SERVICE_NAME"

# 询问是否继续
read -p "继续部署? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# 创建 Artifact Registry 仓库（如果不存在）
echo "检查 Artifact Registry..."
gcloud artifacts repositories describe $REPO_NAME --location=$REGION --project=$PROJECT_ID 2>/dev/null || \
gcloud artifacts repositories create $REPO_NAME --repository-format=docker --location=$REGION --project=$PROJECT_ID

# 构建 Docker 镜像
echo "构建 Docker 镜像..."
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:latest .

# 部署到 Cloud Run
echo "部署到 Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:latest \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --timeout=900 \
    --command="python,main.py,run" \
    --set-env-vars=AMADEUS_CLIENT_ID=$AMADEUS_CLIENT_ID \
    --set-env-vars=AMADEUS_CLIENT_SECRET=$AMADEUS_CLIENT_SECRET \
    --set-env-vars=GMAIL_USER=$GMAIL_USER \
    --set-env-vars=GMAIL_APP_PASSWORD=$GMAIL_APP_PASSWORD \
    --set-env-vars=TO_EMAIL=$TO_EMAIL

# 获取服务 URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo "=== 部署完成 ==="
echo "服务 URL: $SERVICE_URL"
echo ""
echo "设置 Cloud Scheduler 来每日运行:"
echo "  gcloud scheduler jobs create http frontier-tracker-daily \\"
echo "    --schedule='0 8 * * *' \\"
echo "    --time-zone='America/Los_Angeles' \\"
echo "    --uri=$SERVICE_URL \\"
echo "    --http-method=GET"
