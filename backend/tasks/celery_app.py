# ===========================================
# Celery Application
# ===========================================

"""
Celery application configuration for AI 有声书工坊.

This module initializes the Celery app and loads configuration from Django settings.
"""

import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Create Celery app
app = Celery("audiobook")

# Auto-discover tasks from installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery connectivity."""
    print(f"Request: {self.request!r}")
