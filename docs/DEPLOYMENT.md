# AI 有声书工坊 - 部署文档

## 1. 环境要求

### 1.1 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 50 GB SSD | 200 GB SSD |
| 网络 | 10 Mbps | 100 Mbps |

### 1.2 软件要求

| 软件 | 版本要求 |
|------|----------|
| Docker | ≥ 20.10 |
| Docker Compose | ≥ 2.0 |
| Git | ≥ 2.30 |

### 1.3 外部服务

- **DeepSeek API**: 用于文本分析和角色识别
- **MiniMax API**: 用于语音合成
- 两者均需自行申请并配置

## 2. 快速部署

### 2.1 克隆项目

```bash
git clone <repository-url>
cd novels
```

### 2.2 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要的 API Key：

```env
# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key

# MiniMax API
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_GROUP_ID=your_group_id

# 数据库
DB_PASSWORD=your_secure_password

# Redis
REDIS_PASSWORD=your_redis_password

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_minio_password

# 监控（可选）
GRAFANA_PASSWORD=your_grafana_password
SENTRY_DSN=your_sentry_dsn
```

### 2.3 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 2.4 验证部署

访问以下地址验证服务是否正常：

- **后端 API**: http://localhost:8000/api/docs
- **前端界面**: http://localhost:3000
- **MinIO 控制台**: http://localhost:9001
- **Grafana 监控**: http://localhost:3001 (可选)
- **Prometheus**: http://localhost:9090 (可选)

## 3. 服务架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户请求                              │
└─────────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Nginx (可选)                           │
│                   反向代理 + SSL 终止                         │
└─────────────────────────────┬───────────────────────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          │                                   │
          ▼                                   ▼
┌─────────────────────┐           ┌─────────────────────┐
│   Next.js Frontend  │           │   FastAPI Backend   │
│    (Port 3000)     │           │    (Port 8000)     │
└─────────────────────┘           └──────────┬──────────┘
                                             │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
         ┌──────────────┐        ┌──────────────┐       ┌──────────────┐
         │   Redis      │        │  PostgreSQL  │       │    MinIO    │
         │  (Celery)    │        │   Database   │       │   Storage   │
         └──────────────┘        └──────────────┘       └──────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   Celery Workers      │
         │  (Async Task Queue)  │
         └──────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  External APIs       │
         │  DeepSeek + MiniMax │
         └──────────────────────┘
```

## 4. Docker Compose 服务说明

### 4.1 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8000 | FastAPI 后端服务 |
| frontend | 3000 | Next.js 前端 |
| celery-worker | - | Celery 异步任务处理 |
| celery-beat | - | Celery 定时任务调度 |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存和消息队列 |
| minio | 9000/9001 | MinIO 对象存储 |
| watch-service | - | 文件夹监听服务 |

### 4.2 可选服务（监控）

| 服务 | 端口 | 说明 |
|------|------|------|
| prometheus | 9090 | Prometheus 监控 |
| grafana | 3001 | Grafana 可视化 |
| alertmanager | 9093 | Alertmanager 告警 |

## 5. 数据目录

部署时会创建以下数据目录：

```
data/
├── postgres/           # PostgreSQL 数据
├── redis/              # Redis 数据
├── minio/              # MinIO 存储
└── books/              # EPUB 文件
    └── incoming/       # 监听目录（放入 EPUB 自动处理）
```

## 6. 生产环境部署

### 6.1 前置准备

1. **域名配置**: 准备域名并配置 DNS
2. **SSL 证书**: 申请 SSL 证书或使用 Let's Encrypt
3. **反向代理**: 推荐使用 Nginx 或 Traefik

### 6.2 Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 前端静态文件
    location / {
        proxy_pass http://frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API 请求
    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 6.3 环境变量配置

生产环境建议使用环境变量而非 `.env` 文件：

```bash
# 使用环境变量
export DEEPSEEK_API_KEY=xxx
export MINIMAX_API_KEY=xxx
```

## 7. 更新与升级

### 7.1 版本更新

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker-compose build
docker-compose up -d

# 查看更新日志
docker-compose logs -f backend
```

### 7.2 数据库迁移

```bash
# 执行数据库迁移
docker-compose exec backend alembic upgrade head

# 查看当前版本
docker-compose exec backend alembic current
```

## 8. 备份与恢复

### 8.1 数据备份

```bash
# 备份 PostgreSQL
docker-compose exec postgres pg_dump -U audiobook_user audiobook_db > backup_$(date +%Y%m%d).sql

# 备份 MinIO（整个目录）
tar -czf minio_backup_$(date +%Y%m%d).tar.gz data/minio/

# 备份配置文件
cp .env .env.backup
```

### 8.2 数据恢复

```bash
# 恢复 PostgreSQL
cat backup_20240101.sql | docker-compose exec -T postgres psql -U audiobook_user audiobook_db

# 恢复 MinIO
tar -xzf minio_backup_20240101.tar.gz -C /
```

## 9. 故障排查

### 9.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 后端无法启动 | 数据库连接失败 | 检查数据库配置和网络 |
| 前端无法访问 | 后端 API 无响应 | 检查后端服务状态 |
| 任务不执行 | Celery Worker 未启动 | 检查 Worker 日志 |
| 文件上传失败 | MinIO 连接问题 | 检查 MinIO 配置 |

### 9.2 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f celery-worker

# 查看最近 100 行日志
docker-compose logs --tail=100 backend
```

### 9.3 重启服务

```bash
# 重启单个服务
docker-compose restart backend

# 重启所有服务
docker-compose restart

# 完全重建
docker-compose down
docker-compose up -d --build
```

## 10. 安全建议

1. **修改默认密码**: 务必修改所有默认密码
2. **启用 HTTPS**: 生产环境必须使用 HTTPS
3. **限制 API 访问**: 使用防火墙或 VPN 限制管理接口访问
4. **定期更新**: 定期更新 Docker 镜像和依赖
5. **监控告警**: 配置监控和告警以便及时发现问题
6. **数据备份**: 定期备份数据库和重要文件

## 11. 联系方式

如有问题，请参考：

- API 文档: http://localhost:8000/api/docs
- Grafana 仪表盘: http://localhost:3001 (如已启用)
- 项目 Issues: https://github.com/your-repo/issues
