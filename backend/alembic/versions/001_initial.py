# ===========================================
# 初始数据库迁移
# ===========================================

"""
初始数据库迁移

创建所有数据表：
- books: 书籍表
- chapters: 章节表
- audio_segments: 音频片段表
- tts_tasks: TTS 任务表
- voice_profiles: 音色配置表
- publish_channels: 发布渠道表
- publish_records: 发布记录表

Revision ID: 001_initial
Revises: None
创建时间: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 books 表
    op.create_table(
        'books',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('cover_image_url', sa.String(length=1000), nullable=True),
        sa.Column('cover_image_path', sa.String(length=500), nullable=True),
        sa.Column('file_name', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('file_path', sa.String(length=1000), nullable=True),
        sa.Column('status', sa.Enum('pending', 'analyzing', 'synthesizing', 'post_processing', 'publishing', 'done', 'failed', name='bookstatus'), nullable=False),
        sa.Column('source_type', sa.Enum('manual', 'watch', name='sourcetype'), nullable=False),
        sa.Column('total_chapters', sa.Integer(), nullable=True),
        sa.Column('processed_chapters', sa.Integer(), nullable=True),
        sa.Column('total_duration', sa.BigInteger(), nullable=True),
        sa.Column('auto_publish_enabled', sa.Boolean(), nullable=True),
        sa.Column('watch_path', sa.String(length=500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_books_id', 'books', ['id'])
    op.create_index('ix_books_title', 'books', ['title'])
    op.create_index('ix_books_author', 'books', ['author'])
    op.create_index('ix_books_file_hash', 'books', ['file_hash'])
    op.create_index('ix_books_status', 'books', ['status'])
    op.create_index('ix_books_status_created', 'books', ['status', 'created_at'])
    op.create_index('ix_books_source_type_status', 'books', ['source_type', 'status'])

    # 创建 chapters 表
    op.create_table(
        'chapters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('chapter_index', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('cleaned_text', sa.Text(), nullable=True),
        sa.Column('analysis_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('characters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Enum('pending', 'analyzed', 'synthesizing', 'done', 'failed', name='chapterstatus'), nullable=False),
        sa.Column('audio_file_path', sa.String(length=1000), nullable=True),
        sa.Column('audio_url', sa.String(length=1000), nullable=True),
        sa.Column('audio_duration', sa.Integer(), nullable=True),
        sa.Column('audio_file_size', sa.BigInteger(), nullable=True),
        sa.Column('audio_format', sa.String(length=20), nullable=True),
        sa.Column('total_segments', sa.Integer(), nullable=True),
        sa.Column('completed_segments', sa.Integer(), nullable=True),
        sa.Column('failed_segments', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('deepseek_tokens', sa.Integer(), nullable=True),
        sa.Column('minimax_characters', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chapters_id', 'chapters', ['id'])
    op.create_index('ix_chapters_book_id', 'chapters', ['book_id'])
    op.create_index('ix_chapters_status', 'chapters', ['status'])
    op.create_index('ix_chapters_book_index', 'chapters', ['book_id', 'chapter_index'], unique=True)

    # 创建 audio_segments 表
    op.create_table(
        'audio_segments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('segment_index', sa.Integer(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('emotion', sa.String(length=50), nullable=True),
        sa.Column('emotion_intensity', sa.String(length=20), nullable=True),
        sa.Column('speed', sa.String(length=20), nullable=True),
        sa.Column('pause_after', sa.String(length=20), nullable=True),
        sa.Column('voice_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('pending', 'synthesizing', 'success', 'failed', name='segmentstatus'), nullable=False),
        sa.Column('minimax_request_id', sa.String(length=255), nullable=True),
        sa.Column('minimax_cost', sa.Integer(), nullable=True),
        sa.Column('deepseek_cost', sa.Integer(), nullable=True),
        sa.Column('audio_file_path', sa.String(length=1000), nullable=True),
        sa.Column('audio_url', sa.String(length=1000), nullable=True),
        sa.Column('audio_duration_ms', sa.Integer(), nullable=True),
        sa.Column('audio_file_size', sa.BigInteger(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audio_segments_id', 'audio_segments', ['id'])
    op.create_index('ix_audio_segments_chapter_id', 'audio_segments', ['chapter_id'])
    op.create_index('ix_audio_segments_status', 'audio_segments', ['status'])
    op.create_index('ix_audio_segments_chapter_index', 'audio_segments', ['chapter_id', 'segment_index'], unique=True)

    # 创建 tts_tasks 表
    op.create_table(
        'tts_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.Column('parent_task_id', sa.String(length=255), nullable=True),
        sa.Column('task_type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.Enum('pending', 'analyzing', 'synthesizing', 'post_processing', 'publishing', 'done', 'failed', 'cancelled', name='taskstatus'), nullable=False),
        sa.Column('total_segments', sa.Integer(), nullable=True),
        sa.Column('completed_segments', sa.Integer(), nullable=True),
        sa.Column('failed_segments', sa.Integer(), nullable=True),
        sa.Column('deepseek_total_tokens', sa.Integer(), nullable=True),
        sa.Column('minimax_total_characters', sa.Integer(), nullable=True),
        sa.Column('total_cost_estimate', sa.Integer(), nullable=True),
        sa.Column('deepseek_calls', sa.Integer(), nullable=True),
        sa.Column('deepseek_avg_latency_ms', sa.Integer(), nullable=True),
        sa.Column('minimax_calls', sa.Integer(), nullable=True),
        sa.Column('minimax_avg_latency_ms', sa.Integer(), nullable=True),
        sa.Column('total_audio_duration_ms', sa.BigInteger(), nullable=True),
        sa.Column('output_format', sa.String(length=20), nullable=True),
        sa.Column('worker_name', sa.String(length=255), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_remaining_seconds', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tts_tasks_id', 'tts_tasks', ['id'])
    op.create_index('ix_tts_tasks_book_id', 'tts_tasks', ['book_id'])
    op.create_index('ix_tts_tasks_celery_task_id', 'tts_tasks', ['celery_task_id'])
    op.create_index('ix_tts_tasks_status', 'tts_tasks', ['status'])
    op.create_index('ix_tts_tasks_status_created', 'tts_tasks', ['status', 'created_at'])

    # 创建 voice_profiles 表
    op.create_table(
        'voice_profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('role_type', sa.Enum('narrator', 'male_lead', 'female_lead', 'elderly', 'child', 'villain', 'supporting', 'custom', name='roletype'), nullable=False),
        sa.Column('character_names', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('minimax_voice_id', sa.String(length=100), nullable=True),
        sa.Column('minimax_model', sa.String(length=50), nullable=True),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('pitch', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('emotion_params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_system_preset', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_voice_profiles_id', 'voice_profiles', ['id'])
    op.create_index('ix_voice_profiles_book_id', 'voice_profiles', ['book_id'])
    op.create_index('ix_voice_profiles_book_role', 'voice_profiles', ['book_id', 'role_type'])

    # 创建 publish_channels 表
    op.create_table(
        'publish_channels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('platform_type', sa.Enum('self_hosted', 'ximalaya', 'qingting', 'lizhi', 'custom', name='platformtype'), nullable=False),
        sa.Column('api_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('oauth_client_id', sa.String(length=255), nullable=True),
        sa.Column('oauth_access_token', sa.String(length=1000), nullable=True),
        sa.Column('oauth_refresh_token', sa.String(length=1000), nullable=True),
        sa.Column('oauth_expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False),
        sa.Column('auto_publish', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('publish_as_draft', sa.Boolean(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('total_published', sa.Integer(), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=True),
        sa.Column('failure_count', sa.Integer(), nullable=True),
        sa.Column('last_published_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_publish_channels_id', 'publish_channels', ['id'])
    op.create_index('ix_publish_channels_type_enabled', 'publish_channels', ['platform_type', 'is_enabled'])
    op.create_index('ix_publish_channels_user', 'publish_channels', ['user_id', 'is_enabled'])

    # 创建 publish_records 表
    op.create_table(
        'publish_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('external_album_id', sa.String(length=255), nullable=True),
        sa.Column('external_album_url', sa.String(length=1000), nullable=True),
        sa.Column('external_category_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('pending', 'preparing', 'uploading', 'done', 'failed', 'partially_done', name='publishstatus'), nullable=False),
        sa.Column('chapters_published', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('total_chapters', sa.Integer(), nullable=True),
        sa.Column('published_chapters', sa.Integer(), nullable=True),
        sa.Column('failed_chapters', sa.Integer(), nullable=True),
        sa.Column('api_calls', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Integer(), nullable=True),
        sa.Column('result_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['channel_id'], ['publish_channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_publish_records_id', 'publish_records', ['id'])
    op.create_index('ix_publish_records_book_id', 'publish_records', ['book_id'])
    op.create_index('ix_publish_records_channel_id', 'publish_records', ['channel_id'])
    op.create_index('ix_publish_records_book_channel', 'publish_records', ['book_id', 'channel_id'], unique=True)
    op.create_index('ix_publish_records_status', 'publish_records', ['status', 'created_at'])
    op.create_index('ix_publish_records_celery_task_id', 'publish_records', ['celery_task_id'])


def downgrade() -> None:
    # 删除所有表（按依赖关系反向顺序）
    op.drop_table('publish_records')
    op.drop_table('publish_channels')
    op.drop_table('voice_profiles')
    op.drop_table('tts_tasks')
    op.drop_table('audio_segments')
    op.drop_table('chapters')
    op.drop_table('books')

    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS bookstatus')
    op.execute('DROP TYPE IF EXISTS sourcetype')
    op.execute('DROP TYPE IF EXISTS chapterstatus')
    op.execute('DROP TYPE IF EXISTS segmentstatus')
    op.execute('DROP TYPE IF EXISTS taskstatus')
    op.execute('DROP TYPE IF EXISTS roletype')
    op.execute('DROP TYPE IF EXISTS platformtype')
    op.execute('DROP TYPE IF EXISTS publishstatus')
