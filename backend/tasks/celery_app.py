# ===========================================
# AI 有声书工坊 - 后端主模块
# ===========================================

"""
Celery 异步任务框架配置

配置 Celery 消息代理、任务路由、序列化方式、定时任务调度等。
"""

import os
from celery import Celery
from celery.schedules import crontab

# 从环境变量获取配置
def _get_broker_url():
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    redis_password = os.getenv("REDIS_PASSWORD", "")
    if redis_password:
        return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    return f"redis://{redis_host}:{redis_port}/{redis_db}"


# 创建 Celery 应用
celery_app = Celery(
    "audiobook",
    broker=_get_broker_url(),
    backend=_get_broker_url(),
    include=[
        "tasks.task_analyze",
        "tasks.task_synthesize",
        "tasks.task_postprocess",
        "tasks.task_publish",
        "tasks.task_watch",
        "tasks.task_pipeline",
        "tasks.svc_monitor",
    ],
)

# 配置
celery_app.conf.update(
    # 任务序列化方式
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # 任务执行配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,

    # 重试配置
    task_default_retry_delay=60,
    task_max_retries=3,

    # 结果配置
    result_expires=3600,

    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=True,

    # Celery Beat 定时任务调度
    beat_schedule={
        # 每 5 分钟扫描监听目录（作为 watchdog 的兜底方案）
        "scan-incoming-directory": {
            "task": "tasks.task_watch.scan_incoming_directory",
            "schedule": 300.0,  # 5 分钟
            "options": {"queue": "watch"},
        },
        # 每 10 分钟检查监听服务健康状态
        "check-watcher-health": {
            "task": "tasks.task_watch.check_watcher_health",
            "schedule": 600.0,  # 10 分钟
            "options": {"queue": "watch"},
        },
        # 每小时清理过期的处理记录
        "cleanup-old-records": {
            "task": "tasks.task_watch.cleanup_old_records",
            "schedule": 3600.0,  # 1 小时
            "options": {"queue": "watch"},
        },
        # 每 5 分钟执行系统健康检查
        "system-health-check": {
            "task": "tasks.svc_monitor.check_system_health",
            "schedule": 300.0,  # 5 分钟
            "options": {"queue": "default"},
        },
        # 每小时检查成本预算
        "check-cost-budget": {
            "task": "tasks.svc_monitor.check_cost_budget",
            "schedule": 3600.0,  # 1 小时
            "options": {"queue": "default"},
        },
        # 每天凌晨 3 点执行数据统计
        "daily-stats": {
            "task": "tasks.task_analyze.daily_stats",
            "schedule": crontab(hour=3, minute=0),  # 每天 3:00 AM
            "options": {"queue": "default"},
        },
    },
)
