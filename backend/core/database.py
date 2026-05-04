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


class DjangoCompatDB:
    """
    兼容层：模拟 SQLAlchemy 的 db.session 以支持旧代码
    
    Django 使用 Model.objects 而非 db.query()
    这个类将 db.query(Model) 转换为 Model.objects
    """
    
    def query(self, model):
        return model.objects
    
    def add(self, obj):
        pass  # Django ORM 不需要
    
    def commit(self):
        pass  # Django ORM 自动提交
    
    def refresh(self, obj):
        obj.refresh_from_db()
    
    def close(self):
        pass


_db = DjangoCompatDB()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    返回一个兼容对象，支持 db.query(Model) 语法
    """
    yield _db
