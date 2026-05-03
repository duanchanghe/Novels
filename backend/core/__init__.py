# ===========================================
# Core 模块
# ===========================================

"""
Core 模块 - 包含核心配置和基础功能
"""

default_app_config = "core.apps.CoreConfig"

from .config import settings, get_settings
from .exceptions import AppError, EPUBParseError, StorageError, APIError

__all__ = [
    "settings",
    "get_settings",
    "AppError",
    "EPUBParseError",
    "StorageError",
    "APIError",
]
