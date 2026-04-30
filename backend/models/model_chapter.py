# ===========================================
# 章节模型
# ===========================================

"""
章节数据模型

定义章节（Chapter）的数据库结构。
每个书籍包含多个章节，章节包含原始文本和处理后的分析结果。
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
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship

from core.database import Base


class ChapterStatus(str, enum.Enum):
    """
    章节处理状态枚举

    - pending: 等待处理
    - analyzed: 已分析（DeepSeek分析完成）
    - synthesizing: 正在合成（TTS进行中）
    - done: 完成
    - failed: 失败
    """
    PENDING = "pending"
    ANALYZED = "analyzed"
    SYNTHESIZING = "synthesizing"
    DONE = "done"
    FAILED = "failed"


class Chapter(Base):
    """
    章节数据模型

    存储章节的文本内容、分析结果和音频文件信息。
    """

    __tablename__ = "chapters"

    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 外键关联
    book_id = Column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 章节基本信息
    chapter_index = Column(Integer, nullable=False, comment="章节序号（从1开始）")
    title = Column(String(500), nullable=True, comment="章节标题")

    # 文本内容
    raw_text = Column(Text, nullable=True, comment="原始文本（清洗前）")
    cleaned_text = Column(Text, nullable=True, comment="清洗后文本")

    # DeepSeek 分析结果（JSON格式）
    analysis_result = Column(JSON, nullable=True, comment="分析结果JSON")

    # 识别到的角色列表
    characters = Column(JSON, nullable=True, comment="角色列表")

    # 处理状态
    status = Column(
        Enum(ChapterStatus),
        default=ChapterStatus.PENDING,
        nullable=False,
        index=True,
    )

    # 音频文件信息
    audio_file_path = Column(String(1000), nullable=True, comment="MinIO音频文件路径")
    audio_url = Column(String(1000), nullable=True, comment="预签名访问URL")
    audio_duration = Column(Integer, nullable=True, comment="音频时长（秒）")
    audio_file_size = Column(BigInteger, nullable=True, comment="音频文件大小（字节）")
    audio_format = Column(String(20), default="mp3", comment="音频格式")

    # 统计信息
    total_segments = Column(Integer, default=0, comment="总片段数")
    completed_segments = Column(Integer, default=0, comment="已完成片段数")
    failed_segments = Column(Integer, default=0, comment="失败片段数")

    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 成本统计
    deepseek_tokens = Column(Integer, default=0, comment="DeepSeek消耗Token数")
    minimax_characters = Column(Integer, default=0, comment="MiniMax消耗字符数")
    estimated_cost = Column(Integer, default=0, comment="预估成本（分）")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # 关联关系
    book = relationship("Book", back_populates="chapters")
    segments = relationship(
        "AudioSegment",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="AudioSegment.segment_index",
    )

    # 索引
    __table_args__ = (
        Index("ix_chapters_book_index", "book_id", "chapter_index", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Chapter(id={self.id}, book_id={self.book_id}, index={self.chapter_index}, title='{self.title}')>"

    @property
    def progress_percentage(self) -> float:
        """计算处理进度百分比"""
        if self.total_segments == 0:
            return 0.0
        return round((self.completed_segments / self.total_segments) * 100, 2)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "book_id": self.book_id,
            "chapter_index": self.chapter_index,
            "title": self.title,
            "status": self.status.value if self.status else None,
            "audio_url": self.audio_url,
            "audio_duration": self.audio_duration,
            "audio_format": self.audio_format,
            "total_segments": self.total_segments,
            "completed_segments": self.completed_segments,
            "progress_percentage": self.progress_percentage,
            "deepseek_tokens": self.deepseek_tokens,
            "minimax_characters": self.minimax_characters,
            "estimated_cost": self.estimated_cost,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
