# ===========================================
# Database utilities for Django
# ===========================================

"""
Database utilities for AI 有声书工坊.

This module provides a compatibility layer for SQLAlchemy-style syntax
to work with Django ORM.
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
    
    def __init__(self):
        self._dirty_objects = set()
    
    def query(self, model):
        return DjangoQuerySetProxy(model)
    
    def add(self, obj):
        """添加并保存 Django 模型对象"""
        if hasattr(obj, 'save') and callable(obj.save):
            obj.save()
        self._dirty_objects.add(obj)
    
    def track_dirty(self, obj):
        """追踪被修改的对象"""
        self._dirty_objects.add(obj)
    
    def commit(self):
        """提交事务，保存所有被修改的对象"""
        for obj in self._dirty_objects:
            try:
                if hasattr(obj, 'save') and callable(obj.save):
                    obj.save(update_fields=None)
            except Exception:
                pass
        self._dirty_objects.clear()
    
    def refresh(self, obj):
        if hasattr(obj, 'refresh_from_db'):
            obj.refresh_from_db()
    
    def close(self):
        pass


class DjangoQuerySetProxy:
    """
    代理 Django QuerySet，支持链式调用
    
    支持方法：
    - filter(**kwargs): 过滤
    - count(): 计数
    - all(): 获取所有
    - first(): 获取第一个
    - order_by(*fields): 排序
    """
    
    def __init__(self, model):
        self._model = model
        self._queryset = model.objects.all()
    
    def filter(self, **kwargs):
        """过滤查询"""
        self._queryset = self._queryset.filter(**kwargs)
        return self
    
    def exclude(self, **kwargs):
        """排除查询"""
        self._queryset = self._queryset.exclude(**kwargs)
        return self
    
    def count(self):
        """返回数量"""
        return self._queryset.count()
    
    def all(self):
        """返回所有结果列表"""
        return list(self._queryset.all())
    
    def first(self):
        """返回第一个结果"""
        return self._queryset.first()
    
    def order_by(self, *fields):
        """排序"""
        self._queryset = self._queryset.order_by(*fields)
        return self
    
    def __iter__(self):
        return iter(self._queryset)


# 全局数据库上下文实例
_db = DjangoCompatDB()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    返回一个兼容对象，支持 db.query(Model).filter(field=value) 语法
    
    Usage:
        with get_db_context() as db:
            book = db.query(Book).filter(id=1).first()
    """
    # Create a fresh tracker for each context
    original_dirty = _db._dirty_objects.copy() if hasattr(_db, '_dirty_objects') else set()
    _db._dirty_objects = set()
    try:
        yield _db
        _db.commit()
    finally:
        _db._dirty_objects = original_dirty
