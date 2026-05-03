# ===========================================
# 书籍模型
# ===========================================

"""
书籍数据模型

定义书籍（Book）的数据库结构。
包含书籍元数据、文件信息和处理状态。
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    BigInteger,
    Enum,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from core.database import Base
from core.config import settings


class BookStatus(str, enum.Enum):
    """
    书籍处理状态枚举

    - pending: 等待处理
    - analyzing: 正在分析（DeepSeek）
    - synthesizing: 正在合成（TTS）
    - post_processing: 正在后处理
    - publishing: 正在发布
    - done: 完成
    - failed: 失败
    """
    PENDING = "pending"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    POST_PROCESSING = "post_processing"
    PUBLISHING = "publishing"
    DONE = "done"
    FAILED = "failed"


class SourceType(str, enum.Enum):
    """
    书籍来源类型枚举

    - manual: 手动上传
    - watch: 文件夹监听自动导入
    """
    MANUAL = "manual"
    WATCH = "watch"


class GenerationMode(str, enum.Enum):
    """
    有声书生成模式枚举

    - auto: 自动模式（章节完成后自动开始下一章）
    - manual: 手动模式（每章完成后需用户确认才开始下一章）
    """
    AUTO = "auto"
    MANUAL = "manual"


class Book(Base):
    """
    书籍数据模型

    存储书籍的元数据、文件信息和处理状态。
    """

    __tablename__ = "books"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 书籍基本信息
    title = Column(String(500), nullable=False, comment="书名")
    author = Column(String(255), nullable=True, comment="作者")
    description = Column(Text, nullable=True, comment="书籍简介")
    language = Column(String(50), default="zh-CN", comment="语言")

    # 封面图片
    cover_image_url = Column(String(1000), nullable=True, comment="封面图URL")
    cover_image_path = Column(String(500), nullable=True, comment="封面图存储路径")

    @property
    def cover_image(self) -> Optional[bytes]:
        """从 MinIO 获取封面图片字节数据"""
        if self.cover_image_path:
            try:
                from services.svc_minio_storage import get_storage_service
                storage = get_storage_service()
                return storage.download_file(settings.MINIO_BUCKET_EPUB, self.cover_image_path)
            except Exception:
                return None
        return None

    # 文件信息
    file_name = Column(String(500), nullable=False, comment="原始文件名")
    file_size = Column(BigInteger, nullable=True, comment="文件大小（字节）")
    file_hash = Column(String(64), nullable=True, comment="文件MD5哈希")
    file_path = Column(String(1000), nullable=True, comment="MinIO存储路径")

    # 处理状态
    status = Column(
        Enum(BookStatus),
        default=BookStatus.PENDING,
        nullable=False,
        comment="处理状态",
    )
    source_type = Column(
        Enum(SourceType),
        default=SourceType.MANUAL,
        nullable=False,
        comment="来源类型",
    )

    # 统计信息
    total_chapters = Column(Integer, default=0, comment="总章节数")
    processed_chapters = Column(Integer, default=0, comment="已处理章节数")
    total_duration = Column(BigInteger, default=0, comment="总音频时长（秒）")

    # 完整有声书信息
    full_audio_path = Column(String(1000), nullable=True, comment="完整有声书存储路径")
    full_audio_duration = Column(Integer, nullable=True, comment="完整有声书时长（秒）")
    full_audio_size = Column(BigInteger, nullable=True, comment="完整有声书大小（字节）")
    full_audio_format = Column(String(20), default="m4b", comment="完整有声书格式")

    # 生成模式
    generation_mode = Column(
        String(20),
        default="auto",
        nullable=False,
        comment="生成模式：auto=自动, manual=手动",
    )

    # 自动发布配置
    auto_publish_enabled = Column(Boolean, default=False, comment="是否启用自动发布")
    watch_path = Column(String(500), nullable=True, comment="监听路径")

    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")
    error_count = Column(Integer, default=0, comment="错误重试次数")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间",
    )
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # 关联关系
    chapters = relationship(
        "Chapter",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="Chapter.chapter_index",
    )
    tts_tasks = relationship(
        "TTSTask",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    voice_profiles = relationship(
        "VoiceProfile",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    publish_records = relationship(
        "PublishRecord",
        back_populates="book",
        cascade="all, delete-orphan",
    )

    # 索引：优化常见查询组合
    __table_args__ = (
        Index("ix_books_status_created", "status", "created_at"),           # 按状态+时间排序
        Index("ix_books_source_type_status", "source_type", "status"),      # 按来源+状态筛选
        Index("ix_books_deleted_status", "deleted_at", "status"),           # 软删除+状态（最常用查询）
    )

    def __repr__(self) -> str:
        return f"<Book(id={self.id}, title='{self.title}', status='{self.status}')>"

    @property
    def progress_percentage(self) -> float:
        """计算处理进度百分比"""
        if self.total_chapters == 0:
            return 0.0
        return round((self.processed_chapters / self.total_chapters) * 100, 2)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "description": self.description,
            "language": self.language,
            "cover_image_url": self.cover_image_url,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "status": self.status.value if self.status else None,
            "source_type": self.source_type.value if self.source_type else None,
            "total_chapters": self.total_chapters,
            "processed_chapters": self.processed_chapters,
            "progress_percentage": self.progress_percentage,
            "total_duration": self.total_duration,
            "full_audio_path": self.full_audio_path,
            "full_audio_duration": self.full_audio_duration,
            "full_audio_size": self.full_audio_size,
            "full_audio_format": self.full_audio_format,
            "generation_mode": self.generation_mode or "auto",
            "auto_publish_enabled": self.auto_publish_enabled,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
