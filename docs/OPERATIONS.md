# AI 有声书工坊 - 运维手册

## 1. 日常运维

### 1.1 每日检查清单

- [ ] 检查所有服务状态：`docker-compose ps`
- [ ] 检查 API 健康状态：`curl http://localhost:8000/api/health`
- [ ] 检查前端可访问性：访问 http://localhost:3000
- [ ] 查看错误日志：`docker-compose logs --tail=50 | grep -i error`
- [ ] 检查监控仪表盘（Grafana）

### 1.2 每周检查清单

- [ ] 检查磁盘使用率：`df -h`
- [ ] 检查内存使用：`docker stats`
- [ ] 检查 API 使用量和成本
- [ ] 检查失败任务数量
- [ ] 备份数据库

### 1.3 每月检查清单

- [ ] 检查 Docker 镜像更新
- [ ] 更新依赖包版本
- [ ] 清理临时文件和日志
- [ ] 审查安全配置
- [ ] 容量评估和规划

## 2. 监控与告警

### 2.1 监控指标

| 类别 | 指标 | 正常范围 | 告警阈值 |
|------|------|----------|----------|
| **API** | 响应时间 P95 | < 2s | > 5s |
| **API** | 错误率 | < 1% | > 5% |
| **队列** | 积压任务数 | < 100 | > 500 |
| **API** | MiniMax 错误率 | < 5% | > 10% |
| **API** | DeepSeek 错误率 | < 5% | > 10% |
| **系统** | CPU 使用率 | < 70% | > 90% |
| **系统** | 内存使用率 | < 80% | > 90% |
| **存储** | 磁盘使用率 | < 70% | > 85% |

### 2.2 告警处理流程

1. **接收告警**: 收到 PagerDuty/邮件/钉钉通知
2. **评估影响**: 判断告警影响的范围
3. **初步处理**: 尝试常见解决方案
4. **升级处理**: 如无法解决，升级到对应负责人
5. **记录事件**: 在事件记录系统中记录处理过程

### 2.3 常见告警处理

#### API 响应时间过长
```bash
# 1. 检查后端日志
docker-compose logs -f backend | grep -i slow

# 2. 检查数据库连接
docker-compose exec backend python -c "from core.database import engine; print(engine.execute('SELECT 1').scalar())"

# 3. 重启后端服务
docker-compose restart backend
```

#### 任务队列积压
```bash
# 1. 检查 Worker 状态
docker-compose ps celery-worker

# 2. 查看队列长度
docker-compose exec redis redis-cli LLEN celery

# 3. 扩展 Worker
docker-compose up -d --scale celery-worker=3

# 4. 检查失败任务
docker-compose logs celery-worker | grep -i failed
```

#### MiniMax API 错误率升高
```bash
# 1. 检查 API 状态
curl -I https://api.minimax.chat

# 2. 检查配额
# 登录 MiniMax 控制台查看

# 3. 如配额耗尽，等待重置或联系客服
```

## 3. 性能优化

### 3.1 数据库优化

```sql
-- 定期 VACUUM
VACUUM ANALYZE;

-- 查看慢查询
SELECT * FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- 查看表大小
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### 3.2 缓存优化

Redis 缓存键管理：
- `book:{id}` - 书籍缓存，TTL 1小时
- `chapter:{id}` - 章节缓存，TTL 1小时
- `analysis:{hash}` - 分析结果缓存，TTL 24小时

清理缓存：
```bash
# 清理所有缓存
docker-compose exec redis redis-cli FLUSHDB

# 清理过期缓存
docker-compose exec redis redis-cli BGREWRITEAOF
```

### 3.3 队列优化

```bash
# 查看队列状态
docker-compose exec celery-worker celery -A app inspect stats

# 调整 Worker 数量
docker-compose up -d --scale celery-worker=5

# 调整并发数（在 docker-compose.yml 中配置）
CELERY_WORKER_CONCURRENCY=4
```

## 4. 容量规划

### 4.1 资源估算

| 指标 | 单本书消耗 | 100本书消耗 |
|------|-----------|--------------|
| DeepSeek Token | ~50,000 | ~5,000,000 |
| MiniMax 字符 | ~500,000 | ~50,000,000 |
| 磁盘空间 | ~500MB | ~50GB |
| 处理时间 | ~15分钟 | ~25小时 |

### 4.2 扩容操作

#### 扩容后端
```bash
docker-compose up -d --scale backend=2
```

#### 扩容 Worker
```bash
docker-compose up -d --scale celery-worker=4
```

#### 扩容数据库（需要 DBA 协助）
```bash
# 升级 PostgreSQL 配置
# 在 docker-compose.yml 中调整资源限制
```

## 5. 数据管理

### 5.1 数据生命周期

| 数据类型 | 保留期限 | 清理策略 |
|----------|----------|----------|
| 处理中的书籍 | 直到完成 | 自动清理 |
| 已删除书籍 | 30天 | 软删除后清理 |
| 失败任务记录 | 90天 | 自动清理 |
| 操作日志 | 180天 | 归档后清理 |
| 成功的有声书 | 永久 | 手动清理 |

### 5.2 清理脚本

```bash
#!/bin/bash
# cleanup.sh - 定期清理脚本

# 清理 30 天前的失败任务
docker-compose exec -T postgres psql -U audiobook_user -d audiobook_db -c \
    "DELETE FROM books WHERE status = 'failed' AND created_at < NOW() - INTERVAL '30 days';"

# 清理临时文件
rm -rf /tmp/audiobook_*

# 清理日志文件（保留最近 7 天）
find /var/log/audiobook -name "*.log" -mtime +7 -delete

echo "Cleanup completed at $(date)"
```

### 5.3 归档策略

对于超过 1 年的历史数据：

1. 导出到归档存储（冷存储）
2. 删除数据库中的记录
3. 保留 MinIO 中的音频文件（设置生命周期策略）

## 6. 安全运维

### 6.1 密钥轮换

定期更换以下密钥：

```bash
# 1. 生成新密钥
openssl rand -base64 32

# 2. 更新环境变量
# 编辑 .env 或使用 secret management

# 3. 重启服务
docker-compose restart
```

### 6.2 审计日志

查看操作日志：
```bash
# 查看 API 访问日志
docker-compose logs backend | grep "POST\|GET" | tail -100

# 查看文件操作日志
docker-compose logs minio | grep -i upload

# 查看用户操作
docker-compose logs backend | grep -i "user\|auth"
```

### 6.3 入侵检测

```bash
# 检查异常登录
docker-compose logs backend | grep -i "login\|failed"

# 检查异常文件访问
docker-compose logs minio | grep -i "denied"

# 检查异常 API 调用
docker-compose logs backend | grep -i "unauthorized"
```

## 7. 灾难恢复

### 7.1 服务中断恢复

1. **评估影响**: 确定中断范围和时长
2. **快速恢复**: 使用 `docker-compose restart` 重启服务
3. **深入排查**: 查看日志定位根因
4. **预防措施**: 记录并实施预防方案

### 7.2 数据损坏恢复

```bash
# 1. 停止所有服务
docker-compose down

# 2. 恢复数据库
cat backup_20240101.sql | docker-compose exec -T postgres psql -U audiobook_user audiobook_db

# 3. 检查数据完整性
docker-compose exec postgres psql -U audiobook_user -d audiobook_db -c "SELECT COUNT(*) FROM books;"

# 4. 重启服务
docker-compose up -d
```

### 7.3 完整灾难恢复

1. **从备份恢复所有数据**
2. **重新构建所有服务**：`docker-compose down && docker-compose up -d --build`
3. **验证服务完整性**
4. **通知相关方**

## 8. 成本控制

### 8.1 API 成本监控

| API | 单价 | 1000 本消耗 | 成本 |
|-----|------|-------------|------|
| DeepSeek | ¥1/1M tokens | 50M tokens | ¥50 |
| MiniMax | ¥0.2/千字符 | 500M 字符 | ¥100 |

### 8.2 成本优化建议

1. **启用缓存**: 相同文本不重复调用 API
2. **批量处理**: 积累多本书一起处理
3. **低谷时段**: 在 API 价格优惠时段处理
4. **质量选择**: 非关键场景使用标准质量

### 8.3 预算告警配置

在 Grafana 中配置：
- DeepSeek 月度消费 > ¥50 → 告警
- MiniMax 月度消费 > ¥200 → 告警

## 9. 运维工具

### 9.1 常用命令

```bash
# 服务管理
docker-compose up -d                    # 启动所有服务
docker-compose restart <service>         # 重启服务
docker-compose logs -f <service>      # 查看日志
docker-compose exec <service> <cmd>    # 执行命令

# 数据库操作
docker-compose exec postgres psql -U audiobook_user -d audiobook_db  # 连接数据库
pg_dump -U audiobook_user audiobook_db > backup.sql                  # 备份

# Redis 操作
docker-compose exec redis redis-cli   # 连接 Redis
redis-cli KEYS "*"                 # 查看所有键
redis-cli FLUSHDB                   # 清空数据库

# Celery 操作
docker-compose exec celery-worker celery -A app inspect stats  # 查看状态
docker-compose exec celery-worker celery -A app purge <queue> # 清空队列
```

### 9.2 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

# 检查后端
if curl -sf http://localhost:8000/api/health > /dev/null; then
    echo "✅ Backend: OK"
else
    echo "❌ Backend: FAILED"
fi

# 检查前端
if curl -sf http://localhost:3000 > /dev/null; then
    echo "✅ Frontend: OK"
else
    echo "❌ Frontend: FAILED"
fi

# 检查数据库
if docker-compose exec -T postgres pg_isready -U audiobook_user > /dev/null; then
    echo "✅ Database: OK"
else
    echo "❌ Database: FAILED"
fi

# 检查 Redis
if docker-compose exec -T redis redis-cli ping > /dev/null; then
    echo "✅ Redis: OK"
else
    echo "❌ Redis: FAILED"
fi

# 检查 Worker
if docker-compose ps celery-worker | grep -q "Up"; then
    echo "✅ Celery Worker: OK"
else
    echo "❌ Celery Worker: FAILED"
fi
```

## 10. 联系方式

| 角色 | 职责 | 联系方式 |
|------|------|----------|
| 值班工程师 | 日常运维支持 | oncall@example.com |
| 技术负责人 | 重大问题升级 | tech-lead@example.com |
| DBA | 数据库问题 | dba@example.com |
| 安全团队 | 安全事件 | security@example.com |

## 附录

### A. 日志位置

- 后端日志: `docker-compose logs backend`
- 前端日志: `docker-compose logs frontend`
- Worker 日志: `docker-compose logs celery-worker`
- Nginx 日志（如果使用）: `/var/log/nginx/`

### B. 端口映射

| 端口 | 服务 | 外部访问 |
|------|------|----------|
| 3000 | 前端 | 需要 |
| 8000 | 后端 API | 需要（通过 Nginx） |
| 5432 | PostgreSQL | 否 |
| 6379 | Redis | 否 |
| 9000 | MinIO API | 否 |
| 9001 | MinIO Console | 可选 |
| 9090 | Prometheus | 可选 |
| 3001 | Grafana | 可选 |

### C. 关键配置文件

- `docker-compose.yml` - 主配置文件
- `.env` - 环境变量
- `backend/core/config.py` - 后端配置
- `monitoring/prometheus/prometheus.yml` - 监控配置
