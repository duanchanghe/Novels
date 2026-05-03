#!/bin/bash
# ===========================================
# AI 有声书工坊 - 本地启动脚本 (Django)
# ===========================================

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 设置 Python 路径
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
export DJANGO_SETTINGS_MODULE=config.settings

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建 Python 虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖（如果需要）
if [ "$1" = "--install" ] || [ "$1" = "-i" ]; then
    echo "安装依赖..."
    pip install -r backend/requirements.txt
fi

# 创建日志目录
mkdir -p logs data/incoming data/dead-letter books books/incoming books/output

echo ""
echo "==================================="
echo "AI 有声书工坊 - 本地开发环境 (Django)"
echo "==================================="
echo ""

# 启动 PostgreSQL (Docker)
if command -v docker &> /dev/null; then
    if ! docker ps --format '{{.Names}}' | grep -q "audiobook-postgres"; then
        echo "启动 PostgreSQL..."
        docker run -d --name audiobook-postgres \
            -e POSTGRES_DB=audiobook_db \
            -e POSTGRES_USER=audiobook_user \
            -e POSTGRES_PASSWORD=dev_password \
            -p 5432:5432 \
            -v "$SCRIPT_DIR/data/postgres:/var/lib/postgresql/data" \
            postgres:16-alpine
        echo "等待 PostgreSQL 启动..."
        sleep 5
    fi

    # 启动 Redis (Docker)
    if ! docker ps --format '{{.Names}}' | grep -q "audiobook-redis"; then
        echo "启动 Redis..."
        docker run -d --name audiobook-redis \
            -p 6379:6379 \
            -v "$SCRIPT_DIR/data/redis:/data" \
            redis:7-alpine
    fi

    # 启动 MinIO (Docker)
    if ! docker ps --format '{{.Names}}' | grep -q "audiobook-minio"; then
        echo "启动 MinIO..."
        docker run -d --name audiobook-minio \
            -p 9000:9000 -p 9001:9001 \
            -e MINIO_ROOT_USER=minioadmin \
            -e MINIO_ROOT_PASSWORD=minioadmin \
            -v "$SCRIPT_DIR/data/minio:/data" \
            minio/minio server /data --console-address ":9001"
        echo "等待 MinIO 启动..."
        sleep 3
    fi
else
    echo "⚠️  Docker 未安装，跳过容器服务启动"
    echo "   请手动启动 PostgreSQL、Redis、MinIO"
fi

# 设置环境变量（开发模式）
export APP_ENV=development
export APP_DEBUG=true
export DB_ENGINE=django.db.backends.postgresql
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=audiobook_db
export DB_USER=audiobook_user
export DB_PASSWORD=dev_password
export REDIS_URL=redis://localhost:6379/0
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin

# 创建数据库（如果需要）
echo "检查数据库..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://audiobook_user:dev_password@localhost:5432/audiobook_db')
    conn.close()
    print('数据库已存在')
except:
    print('创建数据库...')
    conn = psycopg2.connect('postgresql://audiobook_user:dev_password@localhost:5432/postgres')
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(\"CREATE USER audiobook_user WITH PASSWORD 'dev_password'\")
    cur.execute('CREATE DATABASE audiobook_db OWNER audiobook_user')
    cur.close()
    conn.close()
    print('数据库创建完成')
" 2>/dev/null || echo "跳过数据库创建（请手动创建）"

# 运行 Django 迁移
echo "检查 Django 迁移..."
cd backend
python3 manage.py migrate --run-syncdb || echo "Django 迁移失败，请手动检查"
cd ..

echo ""
echo "启动服务..."
echo ""

# 启动 Django 后端
echo "[1/4] 启动 Django 后端 (0.0.0.0:8000)..."
cd backend
python3 manage.py runserver 0.0.0.0:8000 &
BACKEND_PID=$!
cd ..

# 启动 Celery Worker
echo "[2/4] 启动 Celery Worker..."
cd backend
celery -A config worker --loglevel=info --concurrency=2 -Q celery,analyze,pipeline,watch &
WORKER_PID=$!
cd ..

# 启动 Celery Beat (可选)
echo "[3/4] 启动 Celery Beat..."
cd backend
celery -A config beat --loglevel=info &
BEAT_PID=$!
cd ..

echo "[4/4] 启动完成"

echo ""
echo "==================================="
echo "✅ 所有服务已启动!"
echo "==================================="
echo ""
echo "服务地址:"
echo "  📖 Django:       http://localhost:8000"
echo "  📚 Admin:        http://localhost:8000/admin/"
echo "  🌸 Flower:       http://localhost:5555 (如已安装)"
echo ""
echo "MinIO 控制台:"
echo "  http://localhost:9001"
echo "  用户名: minioadmin"
echo "  密码: minioadmin"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 等待信号
cleanup() {
    echo ""
    echo "正在停止服务..."
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ -n "$WORKER_PID" ] && kill $WORKER_PID 2>/dev/null
    [ -n "$BEAT_PID" ] && kill $BEAT_PID 2>/dev/null
    echo "已停止所有服务"
}

trap cleanup SIGINT SIGTERM

# 等待所有后台进程
wait
