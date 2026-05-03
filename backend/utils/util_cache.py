# ===========================================
# API 缓存工具模块
# ===========================================

"""
API 缓存工具

基于 Redis 提供 API 响应缓存功能。
用于加速频繁访问的只读接口（如书籍列表、章节列表、音色列表等）。

使用方式：
    from utils.util_cache import api_cache

    @router.get("/books")
    async def list_books(db=Depends(get_db)):
        cache_key = f"books:list:{page}:{page_size}:{status}"
        return await api_cache.get_or_set(cache_key, lambda: query_books(), ttl=60)
"""

import json
import functools
import hashlib
import logging
from typing import Callable, Optional, Any

logger = logging.getLogger("audiobook.cache")


class APICache:
    """
    API 响应缓存管理器

    特性：
    - 基于 Redis 的分布式缓存
    - 自动序列化/反序列化
    - Redis 不可用时自动降级（跳过缓存）
    - 支持 TTL 和主动失效
    """

    def __init__(self, redis_url: str = None):
        self._redis_url = redis_url
        self._redis_client = None

    def _get_redis(self):
        """延迟初始化 Redis 客户端"""
        if self._redis_client is None:
            try:
                import redis as _redis
                from core.config import settings
                url = self._redis_url or settings.REDIS_URL or settings._redis_url
                self._redis_client = _redis.from_url(url, decode_responses=True,
                    socket_connect_timeout=2, socket_timeout=2)
            except Exception as e:
                logger.warning(f"Redis 缓存不可用，将跳过缓存: {e}")
                self._redis_client = False  # 标记为不可用
        return self._redis_client if self._redis_client is not False else None

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        raw = f"{prefix}:{json.dumps(args, sort_keys=True, default=str)}:{json.dumps(kwargs, sort_keys=True, default=str)}"
        return f"api_cache:{hashlib.md5(raw.encode()).hexdigest()[:16]}"

    def get(self, key: str) -> Optional[Any]:
        """从缓存获取值"""
        redis_client = self._get_redis()
        if not redis_client:
            return None
        try:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.debug(f"缓存读取失败: {e}")
        return None

    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """写入缓存"""
        redis_client = self._get_redis()
        if not redis_client:
            return False
        try:
            serialized = json.dumps(value, default=str)
            redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.debug(f"缓存写入失败: {e}")
            return False

    def get_or_set(self, key: str, factory: Callable, ttl: int = 60) -> Any:
        """
        缓存穿透保护：先查缓存，未命中则调用 factory 并缓存结果

        Args:
            key: 缓存键
            factory: 数据生成函数（缓存未命中时调用）
            ttl: 缓存过期时间（秒）

        Returns:
            factory 的返回值
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        result = factory()
        if result is not None:
            self.set(key, result, ttl)
        return result

    def invalidate(self, key: str) -> bool:
        """主动使缓存失效"""
        redis_client = self._get_redis()
        if not redis_client:
            return False
        try:
            redis_client.delete(key)
            return True
        except Exception:
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """按模式批量使缓存失效（如 'api_cache:books:*'）"""
        redis_client = self._get_redis()
        if not redis_client:
            return 0
        try:
            keys = redis_client.keys(pattern)
            if keys:
                return redis_client.delete(*keys)
            return 0
        except Exception:
            return 0


# 全局缓存实例
api_cache = APICache()


def cached(prefix: str, ttl: int = 60):
    """
    装饰器：自动缓存函数返回值

    用法：
        @cached("books:list", ttl=30)
        async def list_books(page: int, status: str = None):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = api_cache._make_key(prefix, *args, **kwargs)
            return api_cache.get_or_set(key, lambda: func(*args, **kwargs), ttl)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = api_cache._make_key(prefix, *args, **kwargs)
            return api_cache.get_or_set(key, lambda: func(*args, **kwargs), ttl)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
