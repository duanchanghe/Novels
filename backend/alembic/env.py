# ===========================================
# Alembic 环境配置
# ===========================================

"""
Alembic 迁移脚本环境配置

提供数据库连接和迁移上下文配置。
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
import sys

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.config import settings
from core.database import Base

# 导入所有模型，确保它们被注册到 Base.metadata
from models import (
    Book,
    Chapter,
    AudioSegment,
    TTSTask,
    VoiceProfile,
    PublishChannel,
    PublishRecord,
)

# Alembic Config 对象
config = context.config

# 设置数据库连接 URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线模式运行迁移

    生成 SQL 脚本，不实际连接数据库。
    用于：
    - 生成迁移脚本文件
    - 检查迁移历史
    - 验证模型定义
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # 支持 SQLite 的 ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在线模式运行迁移

    直接连接数据库执行迁移操作。
    用于：
    - 开发环境实时迁移
    - 生产环境部署
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
