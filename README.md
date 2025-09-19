# JTrace Backend (FastAPI)

## 本地运行

1. 创建虚拟环境并安装依赖
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

2. 配置 `backend/config.yaml`
- `mysql.url`: 替换为你的 MySQL 连接串
- `redis.url`: 配置 Redis 连接（用于存储登录 token）
- `jwt.secret_key`: 替换为随机字符串

3. 启动 Redis 与 MySQL
- Redis: 默认 `redis://localhost:6379/0`
- MySQL: 确保数据库已创建（库名 `jtrace`）

4. 启动后端（首次启动自动建表，种子管理员 `admin/admin123`）
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## 认证与会话
- 登录成功后，后端会把 JWT token 写入 Redis（key: `auth:token:<username>`），并设置过期时间
- 受保护接口会校验请求头携带的 token 是否与 Redis 中一致，不一致/过期即拒绝

## 目录结构
- `backend/app/core`: 配置、JWT、安全、Redis 客户端
- `backend/app/db`: 会话与 Base
- `backend/app/models`: SQLAlchemy 模型
- `backend/app/schemas`: Pydantic 模型
- `backend/app/api`: 路由与依赖
- `backend/main.py`: 应用入口
