# ===========================================
# Celery Configuration
# ===========================================

"""
Celery configuration for AI 有声书工坊.
Works with Django and uses Redis as broker.
"""

import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Create the Celery app
app = Celery("audiobook")

# Load config from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# Celery Beat schedule (periodic tasks)
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks for Celery Beat."""
    sender.add_periodic_task(
        300.0,  # 5 minutes
        scan_incoming_directory.s(),
        name="scan-incoming-directory",
    )
    sender.add_periodic_task(
        600.0,  # 10 minutes
        check_watcher_health.s(),
        name="check-watcher-health",
    )
    sender.add_periodic_task(
        3600.0,  # 1 hour
        cleanup_old_records.s(),
        name="cleanup-old-records",
    )
    sender.add_periodic_task(
        crontab(hour=3, minute=0),  # Daily at 3 AM
        daily_stats.s(),
        name="daily-stats",
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f"Request: {self.request!r}")


# Periodic task placeholders
@app.task
def scan_incoming_directory():
    """Scan incoming directory for new files."""
    from tasks.task_watch import scan_incoming_directory as scan
    scan.delay()


@app.task
def check_watcher_health():
    """Check watcher service health."""
    from tasks.task_watch import check_watcher_health as check
    check.delay()


@app.task
def cleanup_old_records():
    """Cleanup old processing records."""
    from tasks.task_watch import cleanup_old_records as cleanup
    cleanup.delay()


@app.task
def daily_stats():
    """Generate daily statistics."""
    from tasks.task_analyze import daily_stats as stats
    stats.delay()
