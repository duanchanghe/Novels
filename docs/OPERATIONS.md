# AI 有声书工坊 - 运维手册

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户访问层                                 │
│   Web UI (http://localhost:3000) / API (http://localhost:8000)  │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                        后端服务层                                 │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────────────┐  │
│  │ Backend  │  │ Celery Worker│  │   Celery Beat           │  │
│  │ (FastAPI)│  │ (异步任务)    │  │   (定时任务调度器)       │  │
│  └──────────┘  └──────────────┘  └─────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Watchdog Service                      │   │
│  │                    (文件夹监听)                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                        数据存储层                                 │
│  ┌────────────┐  ┌─────────┐  ┌────────────────────────────┐  │
│  │ PostgreSQL │  │  Redis  │  │        MinIO              │  │
│  │  (主数据库) │  │ (队列)  │  │  (EPUB/音频文件存储)      │  │
│  └────────────┘  └─────────┘  └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 服务组件

| 服务名称 | 容器名称 | 端口 | 说明 |
|---------|---------|------|------|
| Backend API | audiobook-backend | 8000 | FastAPI 后端服务 |
| Celery Worker | audiobook-celery-worker | - | 异步任务处理器 |
| Celery Beat | audiobook-celery-beat | - | 定时任务调度器 |
| Watchdog | audiobook-watchdog | - | 文件夹监听服务 |
| Flower | audiobook-flower | 5555 | Celery 监控面板 |
| PostgreSQL | audiobook-postgres | 5432 | 主数据库 |
| Redis | audiobook-redis | 6379 | 缓存和消息队列 |
| MinIO | audiobook-minio | 9000/9001 | 对象存储 |

## 3. 快速开始

### 3.1 部署服务

```bash
# 完整部署
./deploy.sh deploy

# 仅启动核心服务
docker-compose up -d

# 启动核心服务 + 监控 (Flower)
docker-compose --profile monitoring up -d

# 启动核心服务 + 文件夹监听
docker-compose --profile watch up -d
```

### 3.2 查看服务状态

```bash
# 查看所有服务状态
./deploy.sh status

# 查看容器状态
docker-compose ps

# 查看资源使用
docker stats

# 查看日志
./deploy.sh logs backend
```

### 3.3 健康检查

```bash
# 执行健康检查
./deploy.sh health

# API 健康检查
curl http://localhost:8000/api/health

# MinIO 健康检查
curl http://localhost:9000/minio/health/live
```

## 4. 核心功能使用

### 4.1 上传 EPUB 生成有声书

**方式一：通过 Web 界面**
1. 访问 http://localhost:3000
2. 点击「上传 EPUB」按钮
3. 选择 EPUB 文件并上传
4. 点击「生成语音」触发处理
5. 等待处理完成，在线试听或下载

**方式二：通过 API**
```bash
# 1. 上传 EPUB
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/book.epub"

# 2. 获取书籍 ID（响应中包含）
# 假设返回 {"book_id": 1}

# 3. 触发生成
curl -X POST http://localhost:8000/api/books/1/generate

# 4. 查看状态
curl http://localhost:8000/api/books/1/status

# 5. 获取音频
curl http://localhost:8000/api/books/1/chapters/1/audio
```

**方式三：通过文件夹监听（自动）**
1. 将 EPUB 文件放入 `./books/incoming/` 目录
2. 系统自动检测并开始处理
3. 无需任何手动操作

### 4.2 管理发布渠道

```bash
# 获取发布渠道列表
curl http://localhost:8000/api/channels

# 添加发布渠道
curl -X POST http://localhost:8000/api/channels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "自建平台",
    "platform_type": "self_hosted",
    "is_enabled": true,
    "auto_publish": true
  }'

# 触发发布
curl -X POST http://localhost:8000/api/books/1/publish
```

### 4.3 监控任务执行

**通过 Flower Web 界面**
- 访问 http://localhost:5555
- 查看活跃任务、队列状态、Worker 信息

**通过 API**
```bash
# 查看任务状态
curl http://localhost:8000/api/books/1/status

# 查看监听状态
curl http://localhost:8000/api/watch/status

# 查看发布状态
curl http://localhost:8000/api/books/1/publish/status
```

## 5. 流水线执行流程

有声书生成的完整流水线包含以下阶段：

```
1. EPUB 解析 → 2. 文本预处理 → 3. DeepSeek 分析
   → 4. 创建片段 → 5. TTS 合成 → 6. 音频后处理 → 7. 发布
```

### 5.1 各阶段说明

| 阶段 | 任务名称 | 说明 | 典型耗时 |
|------|---------|------|---------|
| 解析 | parse_epub | 提取 EPUB 元数据和章节 | ~5s/书 |
| 预处理 | preprocess_chapter | 文本清洗和标准化 | ~1s/章 |
| 分析 | analyze_chapter | DeepSeek 角色/情感识别 | ~3s/章 |
| 片段创建 | create_segments | 创建 TTS 合成片段 | ~0.5s/章 |
| 合成 | synthesize_segment | MiniMax TTS 合成 | ~2s/片段 |
| 后处理 | postprocess_chapter | 音频拼接/均衡 | ~5s/章 |
| 发布 | publish_book | 发送到各渠道 | ~10s/渠道 |

### 5.2 触发流水线

```python
# 在 Celery Worker 中执行
from tasks.task_pipeline import generate_audiobook

# 触发完整流水线
result = generate_audiobook.delay(book_id)

# 查看结果
print(result.get())
```

## 6. 监控与告警

### 6.1 监控指标

| 指标类别 | 监控项 | 告警阈值 | 处理方式 |
|---------|--------|---------|---------|
| 服务可用性 | Backend API | 响应失败 | 立即告警 |
| 服务可用性 | PostgreSQL | 连接失败 | 立即告警 |
| 任务队列 | 队列长度 | >100 | 立即告警 |
| 任务队列 | Worker 数量 | =0 | 立即告警 |
| 成本 | 每日消耗 | >¥50 | 警告 |
| 存储 | 磁盘使用率 | >80% | 警告 |

### 6.2 查看监控数据

```bash
# 获取完整监控报告
curl http://localhost:8000/api/monitoring/report

# 获取健康状态
curl http://localhost:8000/api/monitoring/health

# 获取告警历史
curl http://localhost:8000/api/monitoring/alerts
```

### 6.3 配置告警渠道

系统默认使用 Console 和 Log 告警处理器。可通过配置添加 Webhook 告警：

```python
from services.svc_monitor import alert_manager, WebhookAlertHandler

# 添加 Webhook 告警
webhook = WebhookAlertHandler("https://your-webhook-url.com/alert")
alert_manager.add_handler(webhook)
```

## 7. 日志管理

### 7.1 查看各服务日志

```bash
# 后端 API 日志
docker-compose logs -f backend

# Celery Worker 日志
docker-compose logs -f celery-worker

# Celery Beat 日志
docker-compose logs -f celery-beat

# 文件夹监听日志
docker-compose logs -f watchdog

# 所有日志
docker-compose logs -f
```

### 7.2 日志级别配置

在 `.env` 文件中配置：

```bash
APP_DEBUG=false  # 生产环境设为 false
LOG_LEVEL=INFO   # DEBUG/INFO/WARNING/ERROR
```

### 7.3 日志分析

```bash
# 查看错误日志
docker-compose logs backend | grep ERROR

# 查看最近 100 条日志
docker-compose logs --tail=100 backend

# 搜索特定关键词
docker-compose logs | grep "book_id=123"
```

## 8. 故障排查

### 8.1 常见问题

**Q: EPUB 文件放入监听目录后没有自动处理？**

```bash
# 1. 检查 watchdog 服务是否运行
docker-compose ps watchdog

# 2. 检查监听目录是否正确
docker-compose exec watchdog env | grep WATCH_DIR

# 3. 检查 Celery Beat 任务是否调度
curl http://localhost:5555/api/task/active  # Flower 中查看

# 4. 手动触发扫描
docker-compose exec celery-worker python -c "from tasks.task_watch import scan_incoming_directory; scan_incoming_directory.delay()"
```

**Q: TTS 合成失败？**

```bash
# 1. 检查 MiniMax API Key 配置
docker-compose exec backend env | grep MINIMAX

# 2. 检查 MiniMax API 配额
# 登录 MiniMax 控制台查看

# 3. 查看详细错误日志
docker-compose logs celery-worker | grep -A 5 "minimax"
```

**Q: 任务卡在某个阶段不动？**

```bash
# 1. 检查 Celery Worker 是否正常运行
docker-compose ps celery-worker

# 2. 查看 Worker 日志
docker-compose logs celery-worker

# 3. 重启 Worker
docker-compose restart celery-worker

# 4. 清理卡住的任务
docker-compose exec celery-worker celery purge -A tasks.celery_app
```

**Q: 数据库连接失败？**

```bash
# 1. 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 2. 检查数据库健康状态
docker-compose exec postgres pg_isready

# 3. 查看数据库日志
docker-compose logs postgres
```

### 8.2 数据恢复

**从备份恢复数据库：**

```bash
# 1. 停止服务
docker-compose stop backend celery-worker

# 2. 恢复数据库
docker-compose exec -T postgres psql -U audiobook_user -d audiobook_db < backup.sql

# 3. 重启服务
docker-compose start backend celery-worker
```

**重新处理失败的书籍：**

```bash
# 通过 API
curl -X POST http://localhost:8000/api/books/1/generate

# 或通过 Celery
docker-compose exec celery-worker python -c "from tasks.task_pipeline import retry_failed_chapters; retry_failed_chapters.delay(1)"
```

## 9. 性能优化

### 9.1 调整 Worker 并发数

```bash
# 修改 docker-compose.yml 中的 Worker 并发数
command: celery -A tasks.celery_app worker --loglevel=info --concurrency=8

# 或通过环境变量
CELERY_WORKER_CONCURRENCY=8
```

### 9.2 调整队列优先级

系统使用以下队列：

| 队列名 | 用途 | 优先级 |
|-------|------|-------|
| pipeline | 主流水线任务 | 高 |
| analyze | DeepSeek 分析 | 中 |
| synthesize | TTS 合成 | 中 |
| postprocess | 音频后处理 | 低 |
| publish | 发布任务 | 低 |
| watch | 监听任务 | 低 |

### 9.3 缓存优化

Redis 用于缓存和队列，可通过以下配置优化：

```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

## 10. 安全配置

### 10.1 修改默认密码

在 `.env` 文件中修改以下配置：

```bash
DB_PASSWORD=your-secure-db-password
REDIS_PASSWORD=your-secure-redis-password
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key
```

### 10.2 API 密钥管理

```bash
# DeepSeek API Key
DEEPSEEK_API_KEY=your-deepseek-api-key

# MiniMax API Key
MINIMAX_API_KEY=your-minimax-api-key
MINIMAX_GROUP_ID=your-minimax-group-id
```

### 10.3 CORS 配置

修改 `.env` 中的 CORS 来源：

```bash
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
```

## 11. 备份与恢复

### 11.1 数据库备份

```bash
# 创建备份
docker-compose exec -T postgres pg_dump -U audiobook_user audiobook_db > backup_$(date +%Y%m%d).sql

# 自动备份脚本
#!/bin/bash
BACKUP_DIR=/path/to/backups
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U audiobook_user audiobook_db > $BACKUP_DIR/backup_$DATE.sql
```

### 11.2 文件存储备份

```bash
# 备份 MinIO 数据
tar -czf minio_backup_$(date +%Y%m%d).tar.gz data/minio/

# 备份 EPUB 文件
tar -czf epub_backup_$(date +%Y%m%d).tar.gz books/epub/
```

## 12. 扩展部署

### 12.1 水平扩展 Worker

```bash
# 启动多个 Worker 实例
docker-compose up -d --scale celery-worker=3
```

### 12.2 独立部署 Watchdog

```bash
# 在独立服务器上运行 watchdog
docker run -d \
  --name audiobook-watchdog \
  -e WATCH_DIR=/data/incoming \
  -e DATABASE_URL=postgresql://... \
  audiobook-backend:latest \
  python -c "from services.svc_file_watcher import main; main()"
```

### 12.3 负载均衡

使用 Nginx 作为反向代理：

```nginx
upstream backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 13. 联系与支持

- **项目地址**: https://github.com/your-org/audiobook-workshop
- **问题反馈**: https://github.com/your-org/audiobook-workshop/issues
- **文档更新**: 欢迎提交 PR 完善本文档
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key
```

### 10.2 API 密钥管理

```bash
# DeepSeek API Key
DEEPSEEK_API_KEY=your-deepseek-api-key

# MiniMax API Key
MINIMAX_API_KEY=your-minimax-api-key
MINIMAX_GROUP_ID=your-minimax-group-id
```

### 10.3 CORS 配置

修改 `.env` 中的 CORS 来源：

```bash
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
```

## 11. 备份与恢复

### 11.1 数据库备份

```bash
# 创建备份
docker-compose exec -T postgres pg_dump -U audiobook_user audiobook_db > backup_$(date +%Y%m%d).sql

# 自动备份脚本
#!/bin/bash
BACKUP_DIR=/path/to/backups
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U audiobook_user audiobook_db > $BACKUP_DIR/backup_$DATE.sql
```

### 11.2 文件存储备份

```bash
# 备份 MinIO 数据
tar -czf minio_backup_$(date +%Y%m%d).tar.gz data/minio/

# 备份 EPUB 文件
tar -czf epub_backup_$(date +%Y%m%d).tar.gz books/epub/
```

## 12. 扩展部署

### 12.1 水平扩展 Worker

```bash
# 启动多个 Worker 实例
docker-compose up -d --scale celery-worker=3
```

### 12.2 独立部署 Watchdog

```bash
# 在独立服务器上运行 watchdog
docker run -d \
  --name audiobook-watchdog \
  -e WATCH_DIR=/data/incoming \
  -e DATABASE_URL=postgresql://... \
  audiobook-backend:latest \
  python -c "from services.svc_file_watcher import main; main()"
```

### 12.3 负载均衡

使用 Nginx 作为反向代理：

```nginx
upstream backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 13. 联系与支持

- **项目地址**: https://github.com/your-org/audiobook-workshop
- **问题反馈**: https://github.com/your-org/audiobook-workshop/issues
- **文档更新**: 欢迎提交 PR 完善本文档
