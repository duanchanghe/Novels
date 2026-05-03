# ===========================================
# Database utilities for Django
# ===========================================

"""
Database utilities for AI 有声书工坊.

This module provides utilities for working with Django ORM.
For Celery tasks, Django models can be accessed directly.
"""

from django.db import transaction
from contextlib import contextmanager


@contextmanager
def atomic():
    """
    Context manager for database transactions.
    
    Usage:
        with atomic():
            Book.objects.create(...)
    """
    with transaction.atomic():
        yield


def get_db_context():
    """
    Context manager for database sessions.
    
    In Django, models are accessed directly through their managers.
    This is kept for backward compatibility with FastAPI code.
    """
    yield None  # Django doesn't need explicit session management
