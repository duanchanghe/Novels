# ===========================================
# 数据库实现 - Unit of Work 模式
# ===========================================

"""
数据库实现 - Unit of Work 模式

提供工作单元模式实现，确保数据一致性和事务管理。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

from django.db import transaction


class UnitOfWork:
    """
    工作单元

    管理数据库事务，确保数据一致性。
    """

    def __init__(self):
        self._committed = False
        self._rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        return False

    def commit(self):
        """提交事务"""
        if not self._committed:
            transaction.commit()
            self._committed = True

    def rollback(self):
        """回滚事务"""
        if not self._rolled_back:
            transaction.rollback()
            self._rolled_back = True


@contextmanager
def atomic():
    """
    原子操作上下文管理器

    Usage:
        with atomic() as uow:
            # 执行数据库操作
            uow.commit()
    """
    with transaction.atomic():
        yield UnitOfWork()


class DjangoRepositoryMixin:
    """
    Django 仓储混入类

    提供通用的 Django ORM 操作方法。
    """

    model_class = None

    def get_queryset(self):
        """获取 QuerySet"""
        return self.model_class.objects

    def filter(self, **kwargs):
        """过滤查询"""
        return self.get_queryset().filter(**kwargs)

    def exclude(self, **kwargs):
        """排除查询"""
        return self.get_queryset().exclude(**kwargs)

    def all(self):
        """获取所有"""
        return self.get_queryset().all()

    def get(self, **kwargs):
        """获取单个"""
        return self.get_queryset().get(**kwargs)

    def first(self, **kwargs):
        """获取第一个"""
        return self.get_queryset().filter(**kwargs).first()

    def last(self, **kwargs):
        """获取最后一个"""
        return self.get_queryset().filter(**kwargs).last()

    def exists(self, **kwargs) -> bool:
        """检查是否存在"""
        return self.get_queryset().filter(**kwargs).exists()

    def count(self, **kwargs) -> int:
        """计数"""
        if kwargs:
            return self.get_queryset().filter(**kwargs).count()
        return self.get_queryset().count()

    def create(self, **kwargs):
        """创建"""
        return self.get_queryset().create(**kwargs)

    def get_or_create(self, defaults: dict = None, **kwargs):
        """获取或创建"""
        return self.get_queryset().get_or_create(defaults=defaults, **kwargs)

    def update_or_create(self, defaults: dict = None, **kwargs):
        """更新或创建"""
        return self.get_queryset().update_or_create(defaults=defaults, **kwargs)

    def bulk_create(self, objs: List, batch_size: int = 100):
        """批量创建"""
        return self.get_queryset().bulk_create(objs, batch_size=batch_size)

    def bulk_update(self, objs: List, fields: List, batch_size: int = 100):
        """批量更新"""
        return self.get_queryset().bulk_update(objs, fields=fields, batch_size=batch_size)


class DatabaseUnitOfWork:
    """
    数据库工作单元

    管理所有仓储的生命周期和事务。
    """

    def __init__(self):
        self._books: Optional["BookRepository"] = None
        self._chapters: Optional["ChapterRepository"] = None
        self._segments: Optional["SegmentRepository"] = None
        self._channels: Optional["ChannelRepository"] = None
        self._records: Optional["RecordRepository"] = None
        self._voice_profiles: Optional["VoiceProfileRepository"] = None
        self._transaction = None

    def __enter__(self):
        self._transaction = transaction.atomic()
        self._transaction.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._transaction.__exit__(exc_type, exc_val, exc_tb)
        else:
            self._transaction.__exit__(None, None, None)
        return False

    @property
    def books(self) -> "BookRepository":
        """获取书籍仓储"""
        if self._books is None:
            from .repositories import BookRepository
            self._books = BookRepository()
        return self._books

    @property
    def chapters(self) -> "ChapterRepository":
        """获取章节仓储"""
        if self._chapters is None:
            from .repositories import ChapterRepository
            self._chapters = ChapterRepository()
        return self._chapters

    @property
    def segments(self) -> "SegmentRepository":
        """获取片段仓储"""
        if self._segments is None:
            from .repositories import SegmentRepository
            self._segments = SegmentRepository()
        return self._segments

    @property
    def channels(self) -> "ChannelRepository":
        """获取渠道仓储"""
        if self._channels is None:
            from .repositories import ChannelRepository
            self._channels = ChannelRepository()
        return self._channels

    @property
    def records(self) -> "RecordRepository":
        """获取记录仓储"""
        if self._records is None:
            from .repositories import RecordRepository
            self._records = RecordRepository()
        return self._records

    @property
    def voice_profiles(self) -> "VoiceProfileRepository":
        """获取音色仓储"""
        if self._voice_profiles is None:
            from .repositories import VoiceProfileRepository
            self._voice_profiles = VoiceProfileRepository()
        return self._voice_profiles


# 全局单例
_uow: Optional[DatabaseUnitOfWork] = None


def get_unit_of_work() -> DatabaseUnitOfWork:
    """获取工作单元实例"""
    global _uow
    if _uow is None:
        _uow = DatabaseUnitOfWork()
    return _uow


@contextmanager
def unit_of_work():
    """
    工作单元上下文管理器

    Usage:
        with unit_of_work() as uow:
            book = uow.books.get(id=1)
            book.title = "New Title"
            uow.books.save(book)
    """
    uow = get_unit_of_work()
    with uow:
        yield uow
