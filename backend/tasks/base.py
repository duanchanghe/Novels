# ===========================================
# Task Base Classes and Decorators
# ===========================================

"""
Base classes and decorators for Celery tasks.

Provides consistent configuration for retry, error handling, and logging
across all task modules.
"""

import logging
from functools import wraps
from typing import Optional, Type, Tuple, Any, Dict

from celery import Task
from celery.exceptions import MaxRetriesExceededError

from core.domain.exceptions import (
    EPUBParseError,
    DeepSeekAPIError,
    MiniMaxAPIError,
    StorageError,
    ServiceError,
)


logger = logging.getLogger("audiobook.tasks")


# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 10
DEFAULT_BACKOFF_MAX = 120


class BasePipelineTask(Task):
    """
    Base class for pipeline tasks.

    Provides unified error handling, retry logic, and logging.
    """

    # Default retry configuration
    autoretry_for = (
        ConnectionError,
        TimeoutError,
        StorageError,
        ServiceError,
    )
    retry_backoff = True
    retry_backoff_max = DEFAULT_BACKOFF_MAX
    retry_jitter = True
    max_retries = DEFAULT_MAX_RETRIES
    default_retry_delay = DEFAULT_RETRY_DELAY

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Task failure callback."""
        logger.error(f"Task failed: task_id={task_id}, error={exc}, einfo={einfo}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Task retry callback."""
        logger.warning(f"Task retry: task_id={task_id}, error={exc}")


class AIAPITask(BasePipelineTask):
    """
    Base class for tasks calling external AI APIs.

    Includes specific retry handling for API errors.
    """

    autoretry_for = (
        DeepSeekAPIError,
        MiniMaxAPIError,
        ConnectionError,
        TimeoutError,
    )
    max_retries = 5

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle API task failure."""
        logger.error(f"AI API task failed: task_id={task_id}, error={exc}")
        # Check for specific errors that should not retry
        if isinstance(exc, MiniMaxAPIError):
            if "insufficient balance" in str(exc).lower() or "1008" in str(exc):
                logger.error(f"API error indicates no retry: {exc}")
                return
        super().on_failure(exc, task_id, args, kwargs, einfo)


class ParseTask(BasePipelineTask):
    """
    Base class for parsing tasks.

    Optimized for file processing with fewer retries.
    """

    autoretry_for = (
        EPUBParseError,
        ConnectionError,
        TimeoutError,
    )
    max_retries = 3


class StorageTask(BasePipelineTask):
    """
    Base class for storage operations.

    Includes retry for transient storage errors.
    """

    autoretry_for = (
        StorageError,
        ConnectionError,
        TimeoutError,
    )
    max_retries = 4
    default_retry_delay = 5


def task_retry_config(
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    backoff_max: int = DEFAULT_BACKOFF_MAX,
) -> Dict[str, Any]:
    """
    Generate retry configuration dictionary.

    Args:
        max_retries: Maximum number of retries
        retry_delay: Initial retry delay in seconds
        backoff_max: Maximum backoff time in seconds

    Returns:
        dict: Celery task configuration
    """
    return {
        "max_retries": max_retries,
        "default_retry_delay": retry_delay,
        "retry_backoff": True,
        "retry_backoff_max": backoff_max,
        "retry_jitter": True,
    }


def log_task_execution(func):
    """
    Decorator to log task execution.

    Adds consistent logging for task start, success, and failure.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        task_name = func.__name__
        task_args = ", ".join(str(a) for a in args[:3])  # Log first 3 args
        logger.info(f"[Task] {task_name} started: {task_args}")

        try:
            result = func(*args, **kwargs)
            logger.info(f"[Task] {task_name} completed")
            return result
        except Exception as e:
            logger.error(f"[Task] {task_name} failed: {e}")
            raise

    return wrapper


def track_progress(progress_callback: Optional[callable] = None):
    """
    Decorator factory for tracking task progress.

    Args:
        progress_callback: Callback function to report progress
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if progress_callback and result:
                progress_callback(result)
            return result
        return wrapper
    return decorator
