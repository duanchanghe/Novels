# ===========================================
# Sentry 错误监控配置
# ===========================================

"""
Sentry 配置

用于后端和前端的错误追踪。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def setup_sentry() -> Optional[Any]:
    """
    配置 Sentry 错误追踪

    Returns:
        Sentry SDK 实例或 None（如果未配置）
    """
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlAlchemyIntegration
        from core.config import settings

        if not settings.SENTRY_DSN:
            logger.warning("Sentry DSN 未配置，跳过 Sentry 初始化")
            return None

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            integrations=[
                FastApiIntegration(),
                CeleryIntegration(),
                SqlAlchemyIntegration(),
            ],
            # 设置采样率（生产环境降低采样）
            traces_sample_rate=0.1 if settings.IS_PRODUCTION else 1.0,
            # 设置错误采样率
            sample_rate=0.5 if settings.IS_PRODUCTION else 1.0,
            # 忽略特定错误
            ignore_errors=[
                "KeyboardInterrupt",
                "SystemExit",
                "ValidationError",
            ],
            # 添加额外标签
            default_tags={
                "app": settings.APP_NAME,
                "environment": settings.APP_ENV,
            },
        )

        logger.info("Sentry 错误追踪已初始化")
        return sentry_sdk

    except ImportError:
        logger.warning("Sentry SDK 未安装，跳过 Sentry 初始化")
        return None
    except Exception as e:
        logger.error(f"Sentry 初始化失败: {e}")
        return None


def capture_exception(exc: Exception, **kwargs) -> None:
    """
    捕获并上报异常

    Args:
        exc: 异常对象
        **kwargs: 额外参数
    """
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(exc, **kwargs)
    except Exception as e:
        logger.warning(f"上报异常失败: {e}")


def capture_message(message: str, **kwargs) -> None:
    """
    捕获并上报消息

    Args:
        message: 消息内容
        **kwargs: 额外参数
    """
    try:
        import sentry_sdk
        sentry_sdk.capture_message(message, **kwargs)
    except Exception as e:
        logger.warning(f"上报消息失败: {e}")


def add_breadcrumb(message: str, category: str = "default", **kwargs) -> None:
    """
    添加面包屑（记录操作轨迹）

    Args:
        message: 消息内容
        category: 类别
        **kwargs: 额外参数
    """
    try:
        import sentry_sdk
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            **kwargs
        )
    except Exception as e:
        logger.warning(f"添加面包屑失败: {e}")


def set_user_context(user_id: int, email: str = None, **kwargs) -> None:
    """
    设置用户上下文

    Args:
        user_id: 用户 ID
        email: 用户邮箱
        **kwargs: 额外参数
    """
    try:
        import sentry_sdk
        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
            **kwargs
        })
    except Exception as e:
        logger.warning(f"设置用户上下文失败: {e}")


def set_extra_context(**kwargs) -> None:
    """
    设置额外上下文

    Args:
        **kwargs: 上下文键值对
    """
    try:
        import sentry_sdk
        for key, value in kwargs.items():
            sentry_sdk.set_extra(key, value)
    except Exception as e:
        logger.warning(f"设置额外上下文失败: {e}")


def set_tag(key: str, value: str) -> None:
    """
    设置标签

    Args:
        key: 标签键
        value: 标签值
    """
    try:
        import sentry_sdk
        sentry_sdk.set_tag(key, value)
    except Exception as e:
        logger.warning(f"设置标签失败: {e}")
