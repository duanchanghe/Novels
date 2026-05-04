# ===========================================
# Configuration Package
# ===========================================

"""
Configuration package for AI 有声书工坊.

模块化配置设计，支持细粒度的环境变量配置。
"""

# Import all config modules for easy access
from . import celery_config
from . import storage_config
from . import ai_config
from . import watcher_config
from . import audio_config

# Re-export commonly used settings
from .celery_config import *
from .storage_config import *
from .ai_config import *
from .watcher_config import *
from .audio_config import *

__all__ = [
    "celery_config",
    "storage_config",
    "ai_config",
    "watcher_config",
    "audio_config",
]
