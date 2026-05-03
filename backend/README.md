# ===========================================
# AI 有声书工坊 - 本地开发指南
# ===========================================

## 环境要求

- Python 3.11+
- Redis (用于 Celery)
- PostgreSQL (可选，用于生产环境)

## 快速开始

### 1. 创建虚拟环境

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env.local

# 编辑 .env.local 填入你的 API Key
```

### 4. 创建数据库

**使用 SQLite（默认，适合开发）：**
```bash
python manage.py migrate
python manage.py createsuperuser
```

**使用 PostgreSQL：**
```bash
# 创建数据库
createdb audiobook_db

# 编辑 .env.local 启用 PostgreSQL 配置
# 然后运行迁移
python manage.py migrate
python manage.py createsuperuser
```

### 5. 启动服务

**方式一：一键启动（推荐）**
```bash
./run_local.sh
```

**方式二：手动启动**

终端 1 - Django 后端：
```bash
python manage.py runserver 0.0.0.0:8000
```

终端 2 - Celery Worker：
```bash
celery -A config worker -l info
```

终端 3 - Celery Beat（可选，定时任务）：
```bash
celery -A config beat -l info
```

## 访问地址

- **API 服务**: http://localhost:8000
- **Admin 管理后台**: http://localhost:8000/admin/
- **REST API 端点**: http://localhost:8000/api/

## 常用命令

```bash
# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 收集静态文件
python manage.py collectstatic

# 运行测试
pytest

# 代码格式化
black .
isort .
```

## 目录结构

```
backend/
├── config/          # Django 配置
│   ├── settings.py  # 主配置文件
│   ├── urls.py      # URL 路由
│   └── celery.py    # Celery 配置
├── core/            # 主应用
│   ├── models/      # 数据模型
│   ├── views.py     # API 视图
│   ├── serializers.py  # 序列化器
│   ├── services/    # 业务服务
│   └── tasks/       # Celery 任务
├── manage.py        # Django 管理脚本
└── requirements.txt # 依赖列表
```

## Docker 部署（待业务稳定后启用）

业务打磨稳定后，可以使用 Docker Compose 部署：

```bash
docker-compose up -d
```

详情请参考 `docker-compose.yml`。
