"""添加数据库性能优化索引

Revision ID: 002
Revises: 001
Create Date: 2026-05-03

优化内容：
- books: 添加 (deleted_at, status) 复合索引（软删除+状态筛选）
- chapters: 添加 (book_id, status) 和 (status) 索引
- audio_segments: 添加 (chapter_id, status) 和 (status) 索引
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建性能优化索引"""
    # books 表
    op.create_index(
        'ix_books_deleted_status',
        'books',
        ['deleted_at', 'status'],
        if_not_exists=True,
    )
    # 确保 ix_books_status_created 和 ix_books_source_type_status 已存在
    op.create_index(
        'ix_books_status_created',
        'books',
        ['status', 'created_at'],
        if_not_exists=True,
    )
    op.create_index(
        'ix_books_source_type_status',
        'books',
        ['source_type', 'status'],
        if_not_exists=True,
    )

    # chapters 表
    op.create_index(
        'ix_chapters_book_status',
        'chapters',
        ['book_id', 'status'],
        if_not_exists=True,
    )
    op.create_index(
        'ix_chapters_status',
        'chapters',
        ['status'],
        if_not_exists=True,
    )

    # audio_segments 表
    op.create_index(
        'ix_segments_chapter_status',
        'audio_segments',
        ['chapter_id', 'status'],
        if_not_exists=True,
    )
    op.create_index(
        'ix_segments_status',
        'audio_segments',
        ['status'],
        if_not_exists=True,
    )


def downgrade() -> None:
    """回滚索引变更"""
    op.drop_index('ix_books_deleted_status', table_name='books', if_exists=True)
    op.drop_index('ix_books_status_created', table_name='books', if_exists=True)
    op.drop_index('ix_books_source_type_status', table_name='books', if_exists=True)
    op.drop_index('ix_chapters_book_status', table_name='chapters', if_exists=True)
    op.drop_index('ix_chapters_status', table_name='chapters', if_exists=True)
    op.drop_index('ix_segments_chapter_status', table_name='audio_segments', if_exists=True)
    op.drop_index('ix_segments_status', table_name='audio_segments', if_exists=True)
