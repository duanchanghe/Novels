# ===========================================
# Config package initialization
# ===========================================

"""
Configuration module for AI 有声书工坊.
"""

# This will make sure the app is always imported when Django starts
# so that shared_task will use this app.
from config.celery import app as celery_app

__all__ = ("celery_app",)
