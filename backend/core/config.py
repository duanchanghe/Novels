# ===========================================
# 应用配置模块
# ===========================================

"""
应用配置模块

从环境变量加载所有配置，实现 12-FACTOR APP 原则。

注意：对于 Django 应用，推荐直接使用 django.conf.settings。
此模块主要用于 Celery 任务和非 Django 代码。
"""

import os
from functools import lru_cache
from typing import List, Optional

# 尝试从 Django settings 导入，如果失败则使用本地配置
try:
    from django.conf import settings as django_settings
    _USE_DJANGO = True
except ImportError:
    _USE_DJANGO = False


class Settings:
    """
    应用配置类

    所有配置项均从环境变量读取，支持 .env 文件自动加载。
    如果 Django 已初始化，则从 Django settings 读取。
    """

    def __init__(self):
        if _USE_DJANGO:
            self._load_from_django()
        else:
            self._load_from_env()

    def _load_from_django(self):
        """从 Django settings 加载配置"""
        # 基础配置
        self.APP_NAME = getattr(django_settings, 'APP_NAME', 'AI 有声书工坊')
        self.APP_ENV = os.getenv('APP_ENV', 'development')
        self.APP_DEBUG = getattr(django_settings, 'DEBUG', True)
        self.APP_HOST = getattr(django_settings, 'APP_HOST', '0.0.0.0')
        self.APP_PORT = getattr(django_settings, 'APP_PORT', 8000)
        self.SECRET_KEY = getattr(django_settings, 'SECRET_KEY', 'change-me')

        # 数据库配置
        db = getattr(django_settings, 'DATABASES', {}).get('default', {})
        self.DB_HOST = os.getenv('DB_HOST', db.get('HOST', 'localhost'))
        self.DB_PORT = int(os.getenv('DB_PORT', db.get('PORT', 5432)))
        self.DB_NAME = os.getenv('DB_NAME', db.get('NAME', 'audiobook_db'))
        self.DB_USER = os.getenv('DB_USER', db.get('USER', 'audiobook_user'))
        self.DB_PASSWORD = os.getenv('DB_PASSWORD', db.get('PASSWORD', ''))

        # Redis 配置
        self.REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        self.REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
        self.REDIS_DB = int(os.getenv('REDIS_DB', 0))
        self.REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
        self.REDIS_URL = os.getenv('REDIS_URL', '')

        # MinIO 配置
        self.MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        self.MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        self.MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() in ('true', '1', 'yes')
        self.MINIO_BUCKET_EPUB = os.getenv('MINIO_BUCKET_EPUB', 'books-epub')
        self.MINIO_BUCKET_AUDIO = os.getenv('MINIO_BUCKET_AUDIO', 'books-audio')

        # DeepSeek API 配置
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
        self.DEEPSEEK_BASE_URL = os.getenv('DEEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        self.DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        self.DEEPSEEK_MAX_TOKENS = int(os.getenv('DEEPSEEK_MAX_TOKENS', 8192))
        self.DEEPSEEK_TEMPERATURE = float(os.getenv('DEEPSEEK_TEMPERATURE', 0.7))

        # MiniMax TTS API 配置
        self.MINIMAX_API_KEY = os.getenv('MINIMAX_API_KEY', '')
        self.MINIMAX_API_HOST = os.getenv('MINIMAX_API_HOST', 'https://api.minimax.chat')
        self.MINIMAX_GROUP_ID = os.getenv('MINIMAX_GROUP_ID', '')

        # 文件夹监听配置
        self.WATCH_DIR = os.getenv('WATCH_DIR', '/books/incoming')
        self.WATCH_DIRS = os.getenv('WATCH_DIRS', '')
        self.WATCH_INTERVAL = int(os.getenv('WATCH_INTERVAL', 60))
        self.WATCH_ENABLED = os.getenv('WATCH_ENABLED', 'true').lower() in ('true', '1', 'yes')

        # 音频处理配置
        self.AUDIO_SAMPLE_RATE = int(os.getenv('AUDIO_SAMPLE_RATE', 44100))
        self.AUDIO_BITRATE = int(os.getenv('AUDIO_BITRATE', 192))

        # 日志配置
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

        # CORS 配置
        self.CORS_ORIGINS = getattr(django_settings, 'CORS_ALLOWED_ORIGINS', [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
        ])

    def _load_from_env(self):
        """从环境变量加载配置"""
        # 基础配置
        self.APP_NAME = os.getenv('APP_NAME', 'AI 有声书工坊')
        self.APP_ENV = os.getenv('APP_ENV', 'development')
        self.APP_DEBUG = os.getenv('APP_DEBUG', 'true').lower() in ('true', '1', 'yes')
        self.APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
        self.APP_PORT = int(os.getenv('APP_PORT', '8000'))
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')

        # 数据库配置
        self.DB_HOST = os.getenv('DB_HOST', 'localhost')
        self.DB_PORT = int(os.getenv('DB_PORT', '5432'))
        self.DB_NAME = os.getenv('DB_NAME', 'audiobook_db')
        self.DB_USER = os.getenv('DB_USER', 'audiobook_user')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD', '')

        # Redis 配置
        self.REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        self.REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
        self.REDIS_DB = int(os.getenv('REDIS_DB', '0'))
        self.REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
        self.REDIS_URL = os.getenv('REDIS_URL', '')

        # MinIO 配置
        self.MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        self.MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        self.MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() in ('true', '1', 'yes')
        self.MINIO_BUCKET_EPUB = os.getenv('MINIO_BUCKET_EPUB', 'books-epub')
        self.MINIO_BUCKET_AUDIO = os.getenv('MINIO_BUCKET_AUDIO', 'books-audio')

        # DeepSeek API 配置
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
        self.DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        self.DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        self.DEEPSEEK_MAX_TOKENS = int(os.getenv('DEEPSEEK_MAX_TOKENS', '8192'))
        self.DEEPSEEK_TEMPERATURE = float(os.getenv('DEEPSEEK_TEMPERATURE', '0.7'))

        # MiniMax TTS API 配置
        self.MINIMAX_API_KEY = os.getenv('MINIMAX_API_KEY', '')
        self.MINIMAX_API_HOST = os.getenv('MINIMAX_API_HOST', 'https://api.minimax.chat')
        self.MINIMAX_GROUP_ID = os.getenv('MINIMAX_GROUP_ID', '')

        # 文件夹监听配置
        self.WATCH_DIR = os.getenv('WATCH_DIR', '/books/incoming')
        self.WATCH_DIRS = os.getenv('WATCH_DIRS', '')
        self.WATCH_INTERVAL = int(os.getenv('WATCH_INTERVAL', '60'))
        self.WATCH_ENABLED = os.getenv('WATCH_ENABLED', 'true').lower() in ('true', '1', 'yes')

        # 音频处理配置
        self.AUDIO_SAMPLE_RATE = int(os.getenv('AUDIO_SAMPLE_RATE', '44100'))
        self.AUDIO_BITRATE = int(os.getenv('AUDIO_BITRATE', '192'))

        # 日志配置
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

        # CORS 配置
        self.CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')

    @property
    def _redis_url(self) -> str:
        """构建 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def IS_PRODUCTION(self) -> bool:
        """是否生产环境"""
        return self.APP_ENV == "production"

    @property
    def IS_DEVELOPMENT(self) -> bool:
        """是否开发环境"""
        return self.APP_ENV == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例（使用 lru_cache 缓存）

    Returns:
        Settings: 应用配置实例
    """
    return Settings()


# 全局配置实例
settings = get_settings()
