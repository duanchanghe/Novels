# ===========================================
# 应用配置模块
# ===========================================

"""
应用配置模块

从环境变量加载所有配置，实现 12-Factor App 原则。
使用 Pydantic Settings 进行配置管理。
"""

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类

    所有配置项均从环境变量读取，支持 .env 文件自动加载。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- 应用基础配置 ----------
    APP_NAME: str = "ai-audiobook-workshop"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = "change-me-in-production"

    # ---------- 数据库配置 ----------
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "audiobook_db"
    DB_USER: str = "audiobook_user"
    DB_PASSWORD: str = "your-db-password"
    DATABASE_URL: str = ""

    # ---------- Redis 配置 ----------
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = ""

    # ---------- MinIO 对象存储配置 ----------
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_EPUB: str = "books-epub"
    MINIO_BUCKET_AUDIO: str = "books-audio"

    # ---------- DeepSeek API 配置 ----------
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_MAX_TOKENS: int = 4096
    DEEPSEEK_TEMPERATURE: float = 0.7

    # ---------- MiniMax TTS API 配置 ----------
    MINIMAX_API_KEY: str = ""
    MINIMAX_API_HOST: str = "https://api.minimax.chat"
    MINIMAX_GROUP_ID: str = ""

    # ---------- Celery 配置 ----------
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    @property
    def _redis_url(self) -> str:
        """构建 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ---------- 文件夹监听配置 ----------
    WATCH_DIR: str = "/books/incoming"
    WATCH_INTERVAL: int = 60
    WATCH_ENABLED: bool = True

    # ---------- 音频处理配置 ----------
    AUDIO_SAMPLE_RATE: int = 44100
    AUDIO_BITRATE: int = 192
    AUDIO_CROSSFADE_MS: int = 20

    # ---------- 日志配置 ----------
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # ---------- CORS 配置 ----------
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """CORS 允许的来源列表"""
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
        ]

    # ---------- 环境判断 ----------
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
