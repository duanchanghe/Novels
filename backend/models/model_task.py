# ===========================================
# TTS 任务模型
# ===========================================

"""
TTS 任务数据模型

定义转换任务（TTSTask）的数据库结构。
用于跟踪整个书籍的TTS转换进度和成本统计。
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
)
from sqlalchemy.orm import relationship

from core.database import Base


class TaskStatus(str, enum.Enum):
    """
    任务状态枚举

    - pending: 等待执行
    - analyzing: 正在分析（DeepSeek）
    - synthesizing: 正在合成（MiniMax）
    - post_processing: 正在后处理
    - publishing: 正在发布
    - done: 完成
    - failed: 失败
    - cancelled: 已取消
    """
    PENDING = "pending"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    POST_PROCESSING = "post_processing"
    PUBLISHING = "publishing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TTSTask(Base):
    """
    TTS 任务数据模型

    跟踪整个书籍转换任务的执行状态和成本统计。
    """

    __tablename__ = "tts_tasks"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 外键关联
    book_id = Column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Celery 任务ID
    celery_task_id = Column(String(255), nullable=True, comment="Celery任务ID")
    parent_task_id = Column(String(255), nullable=True, comment="父任务ID")

    # 任务类型
    task_type = Column(String(50), default="full", comment="任务类型（full/incremental）")

    # 处理状态
    status = Column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
    )

    # 进度统计
    total_segments = Column(Integer, default=0, comment="总片段数")
    completed_segments = Column(Integer, default=0, comment="已完成片段数")
    failed_segments = Column(Integer, default=0, comment="失败片段数")

    # 成本统计
    deepseek_total_tokens = Column(Integer, default=0, comment="DeepSeek总消耗Token")
    minimax_total_characters = Column(Integer, default=0, comment="MiniMax总消耗字符")
    total_cost_estimate = Column(Integer, default=0, comment="总预估成本（分）")

    # DeepSeek 统计
    deepseek_calls = Column(Integer, default=0, comment="DeepSeek调用次数")
    deepseek_avg_latency_ms = Column(Integer, default=0, comment="DeepSeek平均延迟（毫秒）")

    # MiniMax 统计
    minimax_calls = Column(Integer, default=0, comment="MiniMax调用次数")
    minimax_avg_latency_ms = Column(Integer, default=0, comment="MiniMax平均延迟（毫秒）")

    # 音频后处理统计
    total_audio_duration_ms = Column(BigInteger, default=0, comment="总音频时长（毫秒）")
    output_format = Column(String(20), default="mp3", comment="输出格式")

    # Celery 任务执行信息
    worker_name = Column(String(255), nullable=True, comment="执行Worker名称")

    # 时间戳
    started_at = Column(DateTime, nullable=True, comment="任务开始时间")
    completed_at = Column(DateTime, nullable=True, comment="任务完成时间")

    # 预估时间
    estimated_remaining_seconds = Column(Integer, nullable=True, comment="预估剩余时间（秒）")

    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")
    error_traceback = Column(Text, nullable=True, comment="错误堆栈")

    # 创建/更新时间
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # 关联关系
    book = relationship("Book", back_populates="tts_tasks")

    # 索引
    __table_args__ = (
        Index("ix_tasks_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<TTSTask(id={self.id}, book_id={self.book_id}, status='{self.status}')>"

    @property
    def progress_percentage(self) -> float:
        """计算处理进度百分比"""
        if self.total_segments == 0:
            return 0.0
        return round((self.completed_segments / self.total_segments) * 100, 2)

    @property
    def duration_minutes(self) -> Optional[float]:
        """获取总音频时长（分钟）"""
        if self.total_audio_duration_ms:
            return self.total_audio_duration_ms / 60000
        return None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "book_id": self.book_id,
            "celery_task_id": self.celery_task_id,
            "task_type": self.task_type,
            "status": self.status.value if self.status else None,
            "total_segments": self.total_segments,
            "completed_segments": self.completed_segments,
            "failed_segments": self.failed_segments,
            "progress_percentage": self.progress_percentage,
            "deepseek_total_tokens": self.deepseek_total_tokens,
            "minimax_total_characters": self.minimax_total_characters,
            "total_cost_estimate": self.total_cost_estimate,
            "total_audio_duration_ms": self.total_audio_duration_ms,
            "duration_minutes": self.duration_minutes,
            "worker_name": self.worker_name,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_remaining_seconds": self.estimated_remaining_seconds,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
