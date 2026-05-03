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


# ===========================================
# Redis 分布式限流器
# ===========================================

class RedisRateLimiter:
    """
    基于 Redis 的分布式速率限制器

    解决多 Celery Worker 场景下的限流一致性问题。
    使用 Redis 的 INCR + TTL 实现滑动窗口限流。

    使用方式：
        limiter = RedisRateLimiter(redis_url="redis://localhost:6379/0", qps=10)
        if limiter.acquire():
            # 执行 API 调用
            pass
    """

    def __init__(self, redis_url: str = None, qps: float = 10.0, key_prefix: str = "rate_limit"):
        """
        初始化 Redis 分布式限流器

        Args:
            redis_url: Redis 连接 URL（默认从配置读取）
            qps: 每秒允许的请求数
            key_prefix: Redis key 前缀
        """
        self.qps = qps
        self.key_prefix = key_prefix
        self._redis_url = redis_url
        self._redis_client = None

    def _get_redis(self):
        """延迟初始化 Redis 客户端（避免导入时连接）"""
        if self._redis_client is None:
            import redis as _redis
            from core.config import settings
            url = self._redis_url or settings.REDIS_URL or settings._redis_url
            self._redis_client = _redis.from_url(url, decode_responses=False)
        return self._redis_client

    def acquire(self, key: str = "default", block: bool = False, timeout: float = 1.0) -> bool:
        """
        尝试获取请求许可（同步版）

        使用 Redis 滑动窗口算法：
        1. 获取当前秒的时间戳作为窗口标识
        2. INCR 计数器，首次设置 TTL
        3. 若计数 ≤ qps，允许请求

        Args:
            key: 限流键（不同资源可使用不同的 key）
            block: 是否阻塞等待（Redis 版不支持阻塞，会直接返回）
            timeout: 最大等待时间（秒，block=True 时有效）

        Returns:
            bool: 是否获取成功
        """
        import time as _time

        redis_client = self._get_redis()
        window_key = f"{self.key_prefix}:{key}:{int(_time.time())}"

        try:
            # 原子操作：递增计数
            current = redis_client.incr(window_key)
            if current == 1:
                # 首次设置，TTL 为 2 秒（覆盖当前窗口 + 缓冲）
                redis_client.expire(window_key, 2)

            if current <= self.qps:
                return True

            # 超出限制
            if block:
                _time.sleep(min(timeout, 0.1))  # 短暂等待后重试一次
                return self.acquire(key, block=False)

            return False
        except Exception:
            # Redis 不可用时降级：允许请求通过（避免服务完全不可用）
            return True

    async def acquire_async(self, key: str = "default", block: bool = False, timeout: float = 1.0) -> bool:
        """
        尝试获取请求许可（异步版）

        Args:
            key: 限流键
            block: 是否阻塞等待
            timeout: 最大等待时间

        Returns:
            bool: 是否获取成功
        """
        import asyncio as _asyncio

        redis_client = self._get_redis()
        window_key = f"{self.key_prefix}:{key}:{int(_asyncio.get_event_loop().time())}"

        try:
            current = redis_client.incr(window_key)
            if current == 1:
                redis_client.expire(window_key, 2)

            if current <= self.qps:
                return True

            if block:
                await _asyncio.sleep(min(timeout, 0.1))
                return await self.acquire_async(key, block=False)

            return False
        except Exception:
            return True

    def reset(self, key: str = "default") -> None:
        """重置限流计数器"""
        try:
            redis_client = self._get_redis()
            pattern = f"{self.key_prefix}:{key}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        except Exception:
            pass
