# ===========================================
# 发布记录模型
# ===========================================

"""
发布记录数据模型

定义发布记录（PublishRecord）的数据库结构。
跟踪每本书籍在每个发布渠道的发布状态。
"""

import enum
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Enum,
    Text,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship

from core.database import Base


class PublishStatus(str, enum.Enum):
    """
    发布状态枚举

    - pending: 等待发布
    - preparing: 准备中
    - uploading: 上传中
    - done: 发布成功
    - failed: 发布失败
    - partially_done: 部分成功
    """
    PENDING = "pending"
    PREPARING = "preparing"
    UPLOADING = "uploading"
    DONE = "done"
    FAILED = "failed"
    PARTIALLY_DONE = "partially_done"


class PublishRecord(Base):
    """
    发布记录数据模型

    跟踪每本书籍在每个发布渠道的具体发布状态和结果。
    """

    __tablename__ = "publish_records"

    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 外键关联
    book_id = Column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_id = Column(
        Integer,
        ForeignKey("publish_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 外部平台信息
    external_album_id = Column(String(255), nullable=True, comment="外部专辑ID")
    external_album_url = Column(String(1000), nullable=True, comment="外部专辑URL")
    external_category_id = Column(String(255), nullable=True, comment="外部分类ID")

    # 发布状态
    status = Column(
        Enum(PublishStatus),
        default=PublishStatus.PENDING,
        nullable=False,
        index=True,
    )

    # 章节发布映射
    chapters_published = Column(JSON, nullable=True, comment="章节发布映射")

    # 发布统计
    total_chapters = Column(Integer, default=0, comment="总章节数")
    published_chapters = Column(Integer, default=0, comment="已发布章节数")
    failed_chapters = Column(Integer, default=0, comment="失败章节数")

    # 成本统计
    api_calls = Column(Integer, default=0, comment="API调用次数")
    estimated_cost = Column(Integer, default=0, comment="预估成本（分）")

    # 发布结果详情
    result_details = Column(JSON, nullable=True, comment="发布结果详情")

    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")
    error_code = Column(String(50), nullable=True, comment="错误代码")
    retry_count = Column(Integer, default=0, comment="重试次数")

    # Celery 任务ID
    celery_task_id = Column(String(255), nullable=True, index=True, comment="Celery任务ID")

    # 时间戳
    published_at = Column(DateTime, nullable=True, comment="发布时间")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # 关联关系
    book = relationship("Book", back_populates="publish_records")
    channel = relationship("PublishChannel", back_populates="publish_records")

    # 索引
    __table_args__ = (
        Index("ix_publish_records_book_channel", "book_id", "channel_id", unique=True),
        Index("ix_publish_records_status", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<PublishRecord(id={self.id}, book_id={self.book_id}, channel_id={self.channel_id}, status='{self.status}')>"

    @property
    def progress_percentage(self) -> float:
        """计算发布进度百分比"""
        if self.total_chapters == 0:
            return 0.0
        return round((self.published_chapters / self.total_chapters) * 100, 2)

    @property
    def is_complete(self) -> bool:
        """是否完成发布"""
        return self.status in [PublishStatus.DONE, PublishStatus.PARTIALLY_DONE]

    @property
    def is_success(self) -> bool:
        """是否发布成功"""
        return self.status == PublishStatus.DONE

    def get_chapter_status(self, chapter_id: int) -> Optional[str]:
        """
        获取指定章节的发布状态

        Args:
            chapter_id: 章节ID

        Returns:
            str: 章节发布状态
        """
        if self.chapters_published:
            return self.chapters_published.get(str(chapter_id))
        return None

    def set_chapter_status(self, chapter_id: int, status: str) -> None:
        """
        设置指定章节的发布状态

        Args:
            chapter_id: 章节ID
            status: 发布状态
        """
        if self.chapters_published is None:
            self.chapters_published = {}
        self.chapters_published[str(chapter_id)] = status

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "book_id": self.book_id,
            "channel_id": self.channel_id,
            "external_album_id": self.external_album_id,
            "external_album_url": self.external_album_url,
            "status": self.status.value if self.status else None,
            "chapters_published": self.chapters_published,
            "total_chapters": self.total_chapters,
            "published_chapters": self.published_chapters,
            "failed_chapters": self.failed_chapters,
            "progress_percentage": self.progress_percentage,
            "api_calls": self.api_calls,
            "estimated_cost": self.estimated_cost,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "retry_count": self.retry_count,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
