# ===========================================
# 限流工具
# ===========================================

"""
限流工具模块

提供令牌桶等限流算法实现。
"""

import time
import threading
from typing import Optional


class TokenBucket:
    """
    令牌桶限流器

    用于控制 API 调用速率。
    """

    def __init__(
        self,
        rate: float,
        capacity: Optional[float] = None,
    ):
        """
        初始化令牌桶

        Args:
            rate: 每秒产生的令牌数
            capacity: 桶容量（默认为 rate）
        """
        self.rate = rate
        self.capacity = capacity or rate
        self.tokens = self.capacity
        self.last_update = time.time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """重新填充令牌"""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def acquire(self, tokens: float = 1.0, block: bool = True) -> bool:
        """
        获取令牌

        Args:
            tokens: 要获取的令牌数
            block: 是否阻塞等待

        Returns:
            bool: 是否获取成功
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            if not block:
                return False

            # 计算需要等待的时间
            wait_time = (tokens - self.tokens) / self.rate

        # 在锁外等待
        time.sleep(wait_time)

        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def acquire_async(self, tokens: float = 1.0, block: bool = True) -> bool:
        """
        异步获取令牌

        Args:
            tokens: 要获取的令牌数
            block: 是否阻塞等待

        Returns:
            bool: 是否获取成功
        """
        import asyncio

        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            if not block:
                return False

            wait_time = (tokens - self.tokens) / self.rate

        await asyncio.sleep(wait_time)

        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def reset(self) -> None:
        """重置令牌桶"""
        with self._lock:
            self.tokens = self.capacity
            self.last_update = time.time()


class RateLimiter:
    """
    速率限制器

    基于令牌桶实现的简单速率限制器。
    """

    def __init__(self, qps: float):
        """
        初始化速率限制器

        Args:
            qps: 每秒请求数
        """
        self.bucket = TokenBucket(rate=qps, capacity=qps)

    def acquire(self, block: bool = True) -> bool:
        """
        获取许可

        Args:
            block: 是否阻塞等待

        Returns:
            bool: 是否获取成功
        """
        return self.bucket.acquire(1.0, block)
