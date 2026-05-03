"""添加生成模式和章节链式关联字段

Revision ID: 003
Revises: 002
Create Date: 2026-05-03

新增字段：
- books.generation_mode: 生成模式（auto=自动, manual=手动）
- chapters.next_chapter_id: 下一章ID（手动模式暂停点追踪）
"""

from alembic import op
import sqlalchemy as sa


revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # books 表新增 generation_mode 字段
    op.add_column(
        'books',
        sa.Column('generation_mode', sa.String(20), nullable=False, server_default='auto'),
    )

    # chapters 表新增 next_chapter_id 字段
    op.add_column(
        'chapters',
        sa.Column('next_chapter_id', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('books', 'generation_mode')
    op.drop_column('chapters', 'next_chapter_id')
