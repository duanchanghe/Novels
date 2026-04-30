# ===========================================
# Prometheus 指标收集
# ===========================================

"""
Prometheus 指标收集模块

提供统一的指标收集接口。
"""

import time
from functools import wraps
from typing import Callable, Any
from contextlib import contextmanager

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST


# API 请求指标
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["handler", "method", "status"]
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["handler", "method"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# MiniMax API 指标
MINIMAX_API_REQUESTS = Counter(
    "minimax_api_requests_total",
    "Total MiniMax API requests",
    ["status"]
)

MINIMAX_API_ERRORS = Counter(
    "minimax_api_errors_total",
    "Total MiniMax API errors",
    ["error_type"]
)

MINIMAX_API_DURATION = Histogram(
    "minimax_api_duration_seconds",
    "MiniMax API request duration in seconds",
    ["operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# DeepSeek API 指标
DEEPSEEK_API_REQUESTS = Counter(
    "deepseek_api_requests_total",
    "Total DeepSeek API requests",
    ["status"]
)

DEEPSEEK_API_ERRORS = Counter(
    "deepseek_api_errors_total",
    "Total DeepSeek API errors",
    ["error_type"]
)

DEEPSEEK_API_DURATION = Histogram(
    "deepseek_api_duration_seconds",
    "DeepSeek API request duration in seconds",
    ["operation"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

DEEPSEEK_TOKEN_USAGE = Counter(
    "deepseek_token_usage_total",
    "Total DeepSeek token usage",
    ["type"]  # input, output
)

# Celery 任务指标
CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"]
)

CELERY_TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

# 书籍处理指标
BOOK_PROCESSING_TOTAL = Counter(
    "book_processing_total",
    "Total books processed",
    ["status"]  # success, failed
)

BOOK_PROCESSING_DURATION = Histogram(
    "book_processing_duration_seconds",
    "Book processing duration in seconds",
    buckets=[60.0, 300.0, 600.0, 1200.0, 1800.0, 3600.0]
)

# 文件监听指标
WATCH_FILES_DETECTED = Counter(
    "watch_files_detected_total",
    "Total EPUB files detected by watcher"
)

WATCH_FILES_PROCESSED = Counter(
    "watch_files_processed_total",
    "Total EPUB files processed by watcher",
    ["status"]
)

# 音频指标
AUDIO_SEGMENTS_TOTAL = Counter(
    "audio_segments_total",
    "Total audio segments synthesized",
    ["status"]
)

AUDIO_TOTAL_DURATION = Counter(
    "audio_total_duration_seconds",
    "Total audio duration in seconds"
)

# 队列指标
QUEUE_LENGTH = Gauge(
    "celery_queue_length",
    "Current Celery queue length",
    ["queue"]
)

WORKERS_ONLINE = Gauge(
    "celery_workers_online",
    "Number of online Celery workers"
)

# 服务信息
SERVICE_INFO = Info(
    "audiobook_service",
    "Audiobook service information"
)


def set_service_info(**kwargs) -> None:
    """设置服务信息"""
    SERVICE_INFO.info(kwargs)


def track_http_request(handler: str):
    """
    HTTP 请求追踪装饰器

    Args:
        handler: 请求处理器名称
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            method = kwargs.get("method", "unknown")
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                status = "200"
                return result
            except Exception as e:
                status = "500"
                raise
            finally:
                duration = time.perf_counter() - start_time
                HTTP_REQUESTS_TOTAL.labels(
                    handler=handler,
                    method=method,
                    status=status
                ).inc()
                HTTP_REQUEST_DURATION.labels(
                    handler=handler,
                    method=method
                ).observe(duration)

        return wrapper
    return decorator


def track_minimax_request(operation: str):
    """
    MiniMax API 请求追踪装饰器

    Args:
        operation: 操作名称
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                MINIMAX_API_REQUESTS.labels(status="success").inc()
                return result
            except Exception as e:
                MINIMAX_API_ERRORS.labels(error_type=type(e).__name__).inc()
                MINIMAX_API_REQUESTS.labels(status="error").inc()
                raise
            finally:
                duration = time.perf_counter() - start_time
                MINIMAX_API_DURATION.labels(operation=operation).observe(duration)

        return wrapper
    return decorator


def track_deepseek_request(operation: str):
    """
    DeepSeek API 请求追踪装饰器

    Args:
        operation: 操作名称
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                DEEPSEEK_API_REQUESTS.labels(status="success").inc()
                return result
            except Exception as e:
                DEEPSEEK_API_ERRORS.labels(error_type=type(e).__name__).inc()
                DEEPSEEK_API_REQUESTS.labels(status="error").inc()
                raise
            finally:
                duration = time.perf_counter() - start_time
                DEEPSEEK_API_DURATION.labels(operation=operation).observe(duration)

        return wrapper
    return decorator


def track_celery_task(task_name: str):
    """
    Celery 任务追踪装饰器

    Args:
        task_name: 任务名称
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                CELERY_TASKS_TOTAL.labels(
                    task_name=task_name,
                    status="success"
                ).inc()
                return result
            except Exception as e:
                CELERY_TASKS_TOTAL.labels(
                    task_name=task_name,
                    status="failed"
                ).inc()
                raise
            finally:
                duration = time.perf_counter() - start_time
                CELERY_TASK_DURATION.labels(task_name=task_name).observe(duration)

        return wrapper
    return decorator


@contextmanager
def track_book_processing():
    """书籍处理追踪上下文"""
    start_time = time.perf_counter()

    try:
        yield
        BOOK_PROCESSING_TOTAL.labels(status="success").inc()
    except Exception:
        BOOK_PROCESSING_TOTAL.labels(status="failed").inc()
        raise
    finally:
        duration = time.perf_counter() - start_time
        BOOK_PROCESSING_DURATION.observe(duration)


def update_queue_metrics(length: int, queue: str = "default") -> None:
    """更新队列指标"""
    QUEUE_LENGTH.labels(queue=queue).set(length)


def update_worker_metrics(count: int) -> None:
    """更新 Worker 指标"""
    WORKERS_ONLINE.set(count)


def get_metrics() -> bytes:
    """获取 Prometheus 指标"""
    return generate_latest()


def get_metrics_content_type() -> str:
    """获取 Prometheus 指标内容类型"""
    return CONTENT_TYPE_LATEST
