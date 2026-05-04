# ===========================================
# 工具函数模块
# ===========================================

"""
工具函数模块

包含各种辅助工具：
- util_logger: 日志工具
- util_retry: 重试/退避工具
- util_rate_limiter: 令牌桶限流器
- util_audio: 音频处理辅助函数
- util_file: 文件校验/哈希工具
"""

from .util_logger import setup_logger, get_logger
from .util_retry import retry_async, retry_sync, exponential_backoff
from .util_rate_limiter import TokenBucket
from .util_file import calculate_file_hash, validate_file_type

# pydub 依赖 audioop，在 Python 3.14 上不兼容，延迟导入
try:
    from .util_audio import calculate_audio_duration, normalize_audio_path
except ImportError:
    # 提供降级实现
    def calculate_audio_duration(audio_data: bytes) -> float:
        return 0.0
    
    def normalize_audio_path(path: str) -> str:
        import os
        return os.path.normpath(path)

__all__ = [
    "setup_logger",
    "get_logger",
    "retry_async",
    "retry_sync",
    "exponential_backoff",
    "TokenBucket",
    "calculate_audio_duration",
    "normalize_audio_path",
    "calculate_file_hash",
    "validate_file_type",
]
