# ===========================================
# 重试工具
# ===========================================

"""
重试工具模块

提供异步和同步重试装饰器。
"""

import asyncio
import functools
import logging
import time
from typing import Callable, Type, Tuple, Optional

from core.exceptions import AppError


logger = logging.getLogger("audiobook")


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """
    计算指数退避延迟时间

    Args:
        attempt: 当前重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        jitter: 是否添加随机抖动

    Returns:
        float: 延迟时间（秒）
    """
    import random

    delay = min(base_delay * (2 ** attempt), max_delay)

    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)

    return delay


def retry_sync(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    同步重试装饰器

    Args:
        max_attempts: 最大重试次数
        delay: 基础延迟（秒）
        backoff: 是否使用指数退避
        exceptions: 要重试的异常类型
        on_retry: 重试时的回调函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        raise

                    if backoff:
                        wait_time = exponential_backoff(attempt, delay)
                    else:
                        wait_time = delay

                    logger.warning(
                        f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_attempts}): {e}, "
                        f"{wait_time:.1f}秒后重试"
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    time.sleep(wait_time)

            raise last_exception

        return wrapper

    return decorator


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    异步重试装饰器

    Args:
        max_attempts: 最大重试次数
        delay: 基础延迟（秒）
        backoff: 是否使用指数退避
        exceptions: 要重试的异常类型
        on_retry: 重试时的回调函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        raise

                    if backoff:
                        wait_time = exponential_backoff(attempt, delay)
                    else:
                        wait_time = delay

                    logger.warning(
                        f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_attempts}): {e}, "
                        f"{wait_time:.1f}秒后重试"
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    await asyncio.sleep(wait_time)

            raise last_exception

        return wrapper

    return decorator
