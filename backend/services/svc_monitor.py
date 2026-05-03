# ===========================================
# 监控告警服务
# ===========================================

"""
监控告警服务

提供系统级监控和告警功能：
- API 服务可用性监控
- 任务队列积压监控
- TTS 服务质量监控
- 存储容量监控
- 成本预算监控
- 告警通知（支持多渠道）
"""

import time
import logging
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from core.config import settings
from core.database import get_db_context

logger = logging.getLogger("audiobook.monitor")


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """告警通知渠道"""
    CONSOLE = "console"
    LOG = "log"
    WEBHOOK = "webhook"
    EMAIL = "email"


@dataclass
class Alert:
    """告警实体"""
    level: AlertLevel
    title: str
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class AlertHandler(ABC):
    """告警处理器基类"""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """发送告警"""
        pass

    @abstractmethod
    def close(self):
        """关闭处理器"""
        pass


class ConsoleAlertHandler(AlertHandler):
    """控制台告警处理器"""

    def send(self, alert: Alert) -> bool:
        level_icon = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨",
        }
        icon = level_icon.get(alert.level, "📢")

        logger.info(
            f"{icon} [{alert.level.value.upper()}] {alert.title}\n"
            f"   来源: {alert.source}\n"
            f"   消息: {alert.message}"
        )
        return True

    def close(self):
        pass


class LogAlertHandler(AlertHandler):
    """日志告警处理器"""

    def send(self, alert: Alert) -> bool:
        log_method = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical,
        }
        method = log_method.get(alert.level, logger.info)

        method(
            f"[ALERT:{alert.level.value.upper()}] {alert.title} - "
            f"{alert.message} (source={alert.source})"
        )
        return True

    def close(self):
        pass


class WebhookAlertHandler(AlertHandler):
    """Webhook 告警处理器"""

    def __init__(self, webhook_url: str, timeout: int = 10):
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, alert: Alert) -> bool:
        try:
            import requests

            payload = {
                "msg_type": "text",
                "content": {
                    "text": f"[{alert.level.value.upper()}] {alert.title}\n{alert.message}"
                },
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                logger.info(f"Webhook 告警发送成功: {self.webhook_url}")
                return True
            else:
                logger.warning(f"Webhook 告警发送失败: {response.status_code}")
                return False

        except ImportError:
            logger.warning("requests 库未安装，无法发送 Webhook 告警")
            return False
        except Exception as e:
            logger.error(f"Webhook 告警发送异常: {e}")
            return False

    def close(self):
        pass


class AlertManager:
    """
    告警管理器

    管理告警处理器和告警发送。
    """

    def __init__(self):
        self.handlers: List[AlertHandler] = []
        self.alert_history: List[Alert] = []
        self.max_history = 1000

    def add_handler(self, handler: AlertHandler):
        """添加告警处理器"""
        self.handlers.append(handler)
        logger.info(f"添加告警处理器: {handler.__class__.__name__}")

    def remove_handler(self, handler: AlertHandler):
        """移除告警处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
            handler.close()

    def send_alert(self, alert: Alert):
        """发送告警"""
        # 记录历史
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]

        # 发送到所有处理器
        for handler in self.handlers:
            try:
                handler.send(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")

    def alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        source: str = "system",
        metadata: Dict[str, Any] = None,
    ):
        """快捷告警方法"""
        alert = Alert(
            level=level,
            title=title,
            message=message,
            source=source,
            metadata=metadata or {},
        )
        self.send_alert(alert)

    def get_history(
        self,
        level: Optional[AlertLevel] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """获取告警历史"""
        history = self.alert_history

        if level:
            history = [a for a in history if a.level == level]

        if since:
            history = [a for a in history if a.timestamp >= since]

        return history[-limit:]


# 全局告警管理器
alert_manager = AlertManager()

# 添加默认处理器
alert_manager.add_handler(ConsoleAlertHandler())
alert_manager.add_handler(LogAlertHandler())


# ===========================================
# 监控指标收集器
# ===========================================

class MetricsCollector:
    """
    指标收集器

    收集系统运行指标，包括：
    - 服务可用性
    - 任务队列状态
    - API 调用统计
    - 成本消耗统计
    """

    def collect_all(self) -> Dict[str, Any]:
        """收集所有指标"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services": self.collect_service_metrics(),
            "tasks": self.collect_task_metrics(),
            "storage": self.collect_storage_metrics(),
            "costs": self.collect_cost_metrics(),
        }

    def collect_service_metrics(self) -> Dict[str, Any]:
        """收集服务指标"""
        metrics = {
            "backend": self._check_backend_health(),
            "database": self._check_database_health(),
            "minio": self._check_minio_health(),
            "redis": self._check_redis_health(),
        }
        return metrics

    def _check_backend_health(self) -> Dict[str, Any]:
        """检查后端服务健康状态"""
        try:
            import requests

            backend_url = settings.APP_URL or "http://localhost:8000"
            start = time.time()
            response = requests.get(f"{backend_url}/api/health", timeout=5)
            duration = time.time() - start

            return {
                "available": response.status_code == 200,
                "response_time_ms": round(duration * 1000, 2),
                "status_code": response.status_code,
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
            }

    def _check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            with get_db_context() as db:
                start = time.time()
                db.execute("SELECT 1")
                duration = time.time() - start

                # 获取表统计
                from models import Book
                total_books = db.query(Book).count()

                return {
                    "available": True,
                    "response_time_ms": round(duration * 1000, 2),
                    "total_books": total_books,
                }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
            }

    def _check_minio_health(self) -> Dict[str, Any]:
        """检查 MinIO 健康状态"""
        try:
            from services.svc_minio_storage import get_storage_service

            storage = get_storage_service()
            storage.initialize()

            buckets = storage.list_buckets()

            return {
                "available": True,
                "buckets": buckets,
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
            }

    def _check_redis_health(self) -> Dict[str, Any]:
        """检查 Redis 健康状态"""
        try:
            import redis

            redis_url = getattr(settings, "REDIS_URL", "redis://redis:6379/0")
            r = redis.from_url(redis_url)
            r.ping()

            # 获取队列信息
            info = r.info()
            used_memory = info.get("used_memory_human", "N/A")

            return {
                "available": True,
                "used_memory": used_memory,
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
            }

    def collect_task_metrics(self) -> Dict[str, Any]:
        """收集任务队列指标"""
        try:
            from tasks.celery_app import celery_app
            from celery.app.control import Inspect

            inspector = Inspect()

            # 获取 Worker 统计
            stats = inspector.stats() or {}

            # 获取活跃任务
            active = inspector.active() or {}

            # 获取预约任务
            reserved = inspector.reserved() or {}

            # 队列长度
            try:
                import redis
                redis_url = getattr(settings, "REDIS_URL", "redis://redis:6379/0")
                r = redis.from_url(redis_url)

                queue_lengths = {}
                for queue in ["pipeline", "analyze", "synthesize", "postprocess", "publish", "watch"]:
                    try:
                        queue_lengths[queue] = r.llen(f"celery.queue.{queue}")
                    except Exception:
                        queue_lengths[queue] = -1
            except Exception:
                queue_lengths = {}

            return {
                "workers": {
                    "count": len(stats),
                    "details": {
                        worker: {
                            "status": "online",
                            "pool": stats[worker].get("pool", {}).get("max-concurrency", "N/A"),
                        }
                        for worker in stats
                    },
                },
                "active_tasks": sum(len(tasks) for tasks in active.values()),
                "reserved_tasks": sum(len(tasks) for tasks in reserved.values()),
                "queue_lengths": queue_lengths,
            }
        except Exception as e:
            return {
                "error": str(e),
            }

    def collect_storage_metrics(self) -> Dict[str, Any]:
        """收集存储指标"""
        try:
            from services.svc_minio_storage import get_storage_service

            storage = get_storage_service()

            # 获取各 bucket 使用情况
            buckets_usage = {}

            for bucket in ["books-epub", "books-audio"]:
                try:
                    usage = storage.get_bucket_usage(bucket)
                    buckets_usage[bucket] = usage
                except Exception:
                    buckets_usage[bucket] = {"error": "无法获取"}

            return {
                "buckets": buckets_usage,
            }
        except Exception as e:
            return {
                "error": str(e),
            }

    def collect_cost_metrics(self) -> Dict[str, Any]:
        """收集成本指标"""
        try:
            with get_db_context() as db:
                from models import Book, Chapter
                from sqlalchemy import func

                # 统计 DeepSeek Token 消耗
                deepseek_total = (
                    db.query(func.sum(Chapter.deepseek_tokens))
                    .filter(Chapter.deepseek_tokens > 0)
                    .scalar()
                    or 0
                )

                # 统计 MiniMax 字符消耗
                minimax_total = (
                    db.query(func.sum(Chapter.minimax_characters))
                    .filter(Chapter.minimax_characters > 0)
                    .scalar()
                    or 0
                )

                # 预估成本
                deepseek_cost = deepseek_total / 1_000_000 * 1  # ¥1/1M tokens
                minimax_cost = minimax_total / 1000 * 0.2  # ¥0.2/千字符

                return {
                    "deepseek": {
                        "total_tokens": deepseek_total,
                        "estimated_cost_yuan": round(deepseek_cost, 2),
                    },
                    "minimax": {
                        "total_characters": minimax_total,
                        "estimated_cost_yuan": round(minimax_cost, 2),
                    },
                    "total_estimated_cost_yuan": round(
                        deepseek_cost + minimax_cost, 2
                    ),
                }
        except Exception as e:
            return {
                "error": str(e),
            }


# ===========================================
# 监控服务
# ===========================================

class MonitoringService:
    """
    监控服务

    定期执行监控检查，收集指标并发送告警。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.collector = MetricsCollector()
        self.alerts_enabled = True
        # 默认告警阈值，可通过 config 覆盖
        self._alert_thresholds = {
            "queue_length_warning": 50,
            "queue_length_critical": 100,
            "api_response_time_ms": 2000,
            "error_rate_percent": 5,
            "daily_cost_warning_yuan": 50,
            "daily_cost_critical_yuan": 100,
            "storage_usage_percent_warning": 70,
            "storage_usage_percent_critical": 85,
            "worker_min_count": 1,
        }
        if config:
            self._alert_thresholds.update(config)

    def set_threshold(self, key: str, value: Any):
        """设置告警阈值"""
        self._alert_thresholds[key] = value

    def set_thresholds(self, thresholds: Dict[str, Any]):
        """批量设置告警阈值"""
        self._alert_thresholds.update(thresholds)

    def check_and_alert(self):
        """执行检查并发送告警"""
        if not self.alerts_enabled:
            return

        metrics = self.collector.collect_all()

        # 检查服务可用性
        self._check_services(metrics.get("services", {}))

        # 检查任务队列
        self._check_tasks(metrics.get("tasks", {}))

        # 检查存储
        self._check_storage(metrics.get("storage", {}))

        # 检查成本
        self._check_costs(metrics.get("costs", {}))

    def _check_services(self, services: Dict[str, Any]):
        """检查服务可用性"""
        for service_name, service_metrics in services.items():
            if isinstance(service_metrics, dict):
                if not service_metrics.get("available", False):
                    alert_manager.alert(
                        level=AlertLevel.ERROR,
                        title=f"{service_name} 服务不可用",
                        message=service_metrics.get("error", "未知错误"),
                        source="monitoring",
                    )

                # 检查响应时间
                response_time = service_metrics.get("response_time_ms", 0)
                threshold = self._alert_thresholds.get("api_response_time_ms", 2000)
                if response_time > threshold:
                    alert_manager.alert(
                        level=AlertLevel.WARNING,
                        title=f"{service_name} 响应时间过长",
                        message=f"响应时间: {response_time}ms (阈值: {threshold}ms)",
                        source="monitoring",
                    )

    def _check_tasks(self, tasks: Dict[str, Any]):
        """检查任务队列"""
        queue_lengths = tasks.get("queue_lengths", {})

        for queue_name, length in queue_lengths.items():
            if length < 0:
                continue

            warning_threshold = self._alert_thresholds.get("queue_length_warning", 50)
            critical_threshold = self._alert_thresholds.get("queue_length_critical", 100)

            if length > critical_threshold:
                alert_manager.alert(
                    level=AlertLevel.CRITICAL,
                    title=f"队列积压严重: {queue_name}",
                    message=f"队列长度: {length} (临界值: {critical_threshold})",
                    source="monitoring",
                )
            elif length > warning_threshold:
                alert_manager.alert(
                    level=AlertLevel.WARNING,
                    title=f"队列积压: {queue_name}",
                    message=f"队列长度: {length} (阈值: {warning_threshold})",
                    source="monitoring",
                )

        # 检查 Worker 状态
        workers = tasks.get("workers", {})
        if workers.get("count", 0) == 0:
            alert_manager.alert(
                level=AlertLevel.CRITICAL,
                title="无在线 Worker",
                message="所有 Celery Worker 已离线",
                source="monitoring",
            )

    def _check_storage(self, storage: Dict[str, Any]):
        """检查存储"""
        buckets = storage.get("buckets", {})

        for bucket_name, usage in buckets.items():
            if isinstance(usage, dict):
                # 检查错误
                if "error" in usage:
                    alert_manager.alert(
                        level=AlertLevel.WARNING,
                        title=f"存储桶 {bucket_name} 状态异常",
                        message=usage["error"],
                        source="monitoring",
                    )

    def _check_costs(self, costs: Dict[str, Any]):
        """检查成本预算"""
        total_cost = costs.get("total_estimated_cost_yuan", 0)

        warning_threshold = self._alert_thresholds.get("daily_cost_warning_yuan", 50)
        critical_threshold = self._alert_thresholds.get("daily_cost_critical_yuan", 100)

        if total_cost > critical_threshold:
            alert_manager.alert(
                level=AlertLevel.CRITICAL,
                title="成本超临界值",
                message=f"当前预估成本: ¥{total_cost:.2f} (临界值: ¥{critical_threshold})",
                source="monitoring",
                metadata=costs,
            )
        elif total_cost > warning_threshold:
            alert_manager.alert(
                level=AlertLevel.WARNING,
                title="成本超预警值",
                message=f"当前预估成本: ¥{total_cost:.2f} (预警值: ¥{warning_threshold})",
                source="monitoring",
                metadata=costs,
            )

        # DeepSeek 成本检查
        deepseek_cost = costs.get("deepseek", {}).get("estimated_cost_yuan", 0)
        if deepseek_cost > 10:  # DeepSeek 单日超过 ¥10 告警
            alert_manager.alert(
                level=AlertLevel.INFO,
                title="DeepSeek 成本偏高",
                message=f"DeepSeek 当前成本: ¥{deepseek_cost:.2f}",
                source="monitoring",
                metadata=costs.get("deepseek", {}),
            )

        # MiniMax 成本检查
        minimax_cost = costs.get("minimax", {}).get("estimated_cost_yuan", 0)
        if minimax_cost > 30:  # MiniMax 单日超过 ¥30 告警
            alert_manager.alert(
                level=AlertLevel.INFO,
                title="MiniMax 成本偏高",
                message=f"MiniMax 当前成本: ¥{minimax_cost:.2f}",
                source="monitoring",
                metadata=costs.get("minimax", {}),
            )

    def get_full_report(self) -> Dict[str, Any]:
        """获取完整监控报告"""
        metrics = self.collector.collect_all()

        # 添加最近告警
        alerts = alert_manager.get_history(limit=50)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "recent_alerts": [a.to_dict() for a in alerts],
            "thresholds": self._alert_thresholds,
        }


# ===========================================
# Celery 监控任务
# ===========================================

from tasks.celery_app import celery_app


@celery_app.task(
    name="tasks.svc_monitor.check_system_health",
    bind=True,
)
def check_system_health(self) -> Dict[str, Any]:
    """
    系统健康检查任务

    Celery Beat 定时调度，定期检查系统健康状态。
    """
    logger.info("开始执行系统健康检查...")

    monitor = MonitoringService()
    report = monitor.get_full_report()

    # 执行告警检查
    monitor.check_and_alert()

    # 记录关键指标
    services = report.get("metrics", {}).get("services", {})
    tasks = report.get("metrics", {}).get("tasks", {})

    health_status = "healthy"
    if not all(s.get("available", False) for s in services.values() if isinstance(s, dict)):
        health_status = "degraded"

    if tasks.get("workers", {}).get("count", 0) == 0:
        health_status = "unhealthy"

    logger.info(f"系统健康检查完成: {health_status}")

    return {
        "status": health_status,
        "timestamp": report["timestamp"],
        "services": services,
        "workers": tasks.get("workers", {}),
    }


@celery_app.task(
    name="tasks.svc_monitor.check_cost_budget",
    bind=True,
)
def check_cost_budget(self) -> Dict[str, Any]:
    """
    成本预算检查任务

    检查当前成本消耗情况，发送告警。
    """
    logger.info("开始执行成本预算检查...")

    collector = MetricsCollector()
    costs = collector.collect_cost_metrics()

    daily_limit = getattr(settings, "COST_DAILY_LIMIT", 50)

    total_cost = costs.get("total_estimated_cost_yuan", 0)

    if total_cost > daily_limit:
        alert_manager.alert(
            level=AlertLevel.WARNING,
            title="成本超限",
            message=f"当前成本 ¥{total_cost} 超过每日限额 ¥{daily_limit}",
            source="cost_monitor",
            metadata=costs,
        )

    return {
        "total_cost_yuan": total_cost,
        "daily_limit_yuan": daily_limit,
        "over_budget": total_cost > daily_limit,
    }



# ===========================================
# 健康检查端点 (Django 兼容)
# ===========================================

def get_health_status():
    """
    获取系统健康状态

    Returns:
        dict: 健康状态
    """
    collector = MetricsCollector()
    services = collector.collect_service_metrics()

    all_healthy = all(
        s.get("available", False)
        for s in services.values()
        if isinstance(s, dict)
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services,
    }


def get_metrics():
    """获取完整监控指标"""
    collector = MetricsCollector()
    return collector.collect_all()


def get_report():
    """获取监控报告"""
    monitor = MonitoringService()
    return monitor.get_full_report()


def get_alerts(level: str = None, since: str = None, limit: int = 100):
    """获取告警历史"""
    from core.models.alert import AlertLevel
    from datetime import datetime

    alert_level = AlertLevel(level) if level else None
    since_dt = datetime.fromisoformat(since) if since else None

    alerts = alert_manager.get_history(
        level=alert_level,
        since=since_dt,
        limit=limit,
    )

    return {
        "count": len(alerts),
        "alerts": [a.to_dict() for a in alerts],
    }
