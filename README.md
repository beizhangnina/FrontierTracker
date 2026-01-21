# Frontier Flight Tracker

追踪 SFO/SJC ↔ LAS (Las Vegas) Frontier Airlines 航班价格的 Web 应用。

## 功能

- **Web 界面**: 极简单页面，一键查询航班
- **邮箱登录**: 简单验证码登录，自动保存登录状态
- **定时报告**: 每周二、周四自动发送报告
- **多用户支持**: 每个用户收到自己的报告
- **单程航班**: 显示 SFO/SJC→LAS 和 LAS→SFO/SJC
- **4 个舱位价格**: Basic Fare, Economy Bundle, Premium Bundle, Business Bundle
- **航班详情**: 出发时间、到达时间、飞行时长、是否直飞

## 快速开始

### 1. 本地运行 Web 服务

```bash
# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的配置
# - AMADEUS_CLIENT_ID (从 https://developers.amadeus.com/ 获取)
# - AMADEUS_CLIENT_SECRET
# - GMAIL_USER
# - GMAIL_APP_PASSWORD (Gmail 应用专用密码)
# - SECRET_KEY (session 加密密钥)

# 启动 Web 服务
python web.py
# 或
uvicorn web:app --reload

# 访问 http://localhost:8080
```

### 2. CLI 命令

```bash
# 测试 API
python main.py test

# 发送测试邮件
python main.py email

# 运行完整追踪
python main.py run

# 发送报告给所有用户
python main.py send-all

# 检查今天是否应该运行 (周二/周四)
python main.py should-run

# 显示配置
python main.py show
```

### 3. Google Cloud Run 部署

```bash
# 1. 在 Secret Manager 中配置密钥
gcloud secrets create AMADEUS_CLIENT_ID --data-file-file=client_id.txt
gcloud secrets create AMADEUS_CLIENT_SECRET --data-file-file=client_secret.txt
gcloud secrets create GMAIL_USER --data-file-file=gmail_user.txt
gcloud secrets create GMAIL_APP_PASSWORD --data-file-file=gmail_password.txt
gcloud secrets create SECRET_KEY --data-file-file=secret_key.txt

# 2. 构建 and 部署
gcloud builds submit --config cloudbuild.yaml

# 3. 获取服务 URL
gcloud run services describe frontiertracker --region=us-west1 --format='value(status.url)'
```

#### 设置定时任务 (Cloud Scheduler)

```bash
# 周二 8:00 AM PST
gcloud scheduler jobs create http frontiertracker-tuesday \
  --schedule='0 8 * * 2' \
  --time-zone='America/Los_Angeles' \
  --uri='https://frontiertracker-xxxxx.a.run.app/api/scheduled-run' \
  --http-method=POST

# 周四 8:00 AM PST
gcloud scheduler jobs create http frontiertracker-thursday \
  --schedule='0 8 * * 4' \
  --time-zone='America/Los_Angeles' \
  --uri='https://frontiertracker-xxxxx.a.run.app/api/scheduled-run' \
  --http-method=POST
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 界面 |
| `/api/me` | GET | 获取当前登录用户 |
| `/api/send-code` | POST | 发送验证码 |
| `/api/verify` | POST | 验证登录 |
| `/api/logout` | POST | 登出 |
| `/api/query` | POST | 查询航班并发送邮件 |
| `/api/scheduled-run` | POST | 定时任务端点 |
| `/health` | GET | 健康检查 |

## 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `AMADEUS_CLIENT_ID` | Amadeus API Client ID | 是 |
| `AMADEUS_CLIENT_SECRET` | Amadeus API Secret | 是 |
| `GMAIL_USER` | 发件邮箱地址 | 是 |
| `GMAIL_APP_PASSWORD` | Gmail 应用专用密码 | 是 |
| `SECRET_KEY` | Session 加密密钥 | 是 |
| `PRICE_THRESHOLD` | 价格预警阈值 | 否 (默认 50) |

## 获取 Gmail 应用密码

1. 访问 https://myaccount.google.com/security
2. 启用两步验证
3. 生成"应用专用密码"
4. 使用该 16 位密码作为 `GMAIL_APP_PASSWORD`

## 项目结构

```
frontiertracker/
├── src/
│   ├── __init__.py
│   ├── config.py           # 配置管理
│   ├── models.py           # 数据模型
│   ├── database.py         # 航班数据存储
│   ├── auth.py             # 用户认证
│   ├── api.py              # FastAPI 路由
│   ├── amadeus_client.py   # Amadeus API
│   └── emailer.py          # 邮件发送
├── static/
│   ├── index.html          # Web 界面
│   ├── style.css           # 样式
│   └── app.js              # 前端逻辑
├── data/
│   ├── flights.db          # 航班数据库
│   └── users.db            # 用户数据库
├── main.py                 # CLI 主程序
├── web.py                  # Web 服务入口
├── requirements.txt
├── Dockerfile
├── cloudbuild.yaml
├── .gitignore
└── README.md
```

## License

MIT
