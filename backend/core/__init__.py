# ===========================================
# 核心配置模块
# ===========================================

"""
核心配置模块

包含应用的核心配置、数据库连接、中间件等基础设施代码。
"""

from .config import settings
from .database import get_db, engine, Base, SessionLocal
from .exceptions import (
    AppError,
    FileError,
    EPUBParseError,
    TTSApiError,
    DeepSeekApiError,
    StorageError,
    PublishError,
)
from .constants import (
    ROLE_VOICE_MAP,
    EMOTION_PARAM_MAP,
    VOICE_MAP_SIMPLE,
    PAUSE_CONFIG,
    EQ_CONFIG,
    TARGET_LUFS,
    DEFAULT_VOICE_CONFIG,
    DEFAULT_EMOTION_CONFIG,
)

__all__ = [
    "settings",
    "get_db",
    "engine",
    "Base",
    "SessionLocal",
    "AppError",
    "FileError",
    "EPUBParseError",
    "TTSApiError",
    "DeepSeekApiError",
    "StorageError",
    "PublishError",
]
