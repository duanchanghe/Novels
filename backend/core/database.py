# ===========================================
# 数据库连接模块
# ===========================================

"""
数据库连接模块

提供 SQLAlchemy 引擎、会话管理器和基础模型的创建。
支持 PostgreSQL 数据库连接。
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import settings


# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.APP_DEBUG,
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """
    基础模型类

    所有数据库模型都需要继承此类。
    提供统一的表创建和基础功能。
    """
    pass


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数

    用于 FastAPI 路由中获取数据库会话。
    会话会在请求结束后自动关闭。

    Args:
        无

    Yields:
        Session: SQLAlchemy 数据库会话

    Example:
        @app.get("/books")
        def get_books(db: Session = Depends(get_db)):
            return db.query(Book).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    获取数据库会话的上下文管理器

    用于非 FastAPI 上下文中（如 Celery 任务、脚本等）获取数据库会话。

    Yields:
        Session: SQLAlchemy 数据库会话

    Example:
        with get_db_context() as db:
            book = db.query(Book).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """
    创建所有数据库表

    仅在开发环境使用，生产环境应使用 Alembic 迁移。
    """
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """
    删除所有数据库表

    危险操作，仅在开发环境使用。
    """
    Base.metadata.drop_all(bind=engine)
