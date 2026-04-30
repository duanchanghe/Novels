# ===========================================
# 音频片段模型
# ===========================================

"""
音频片段数据模型

定义音频片段（AudioSegment）的数据库结构。
每个章节包含多个音频片段，片段是最小的TTS合成单元。
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
    Float,
)
from sqlalchemy.orm import relationship

from core.database import Base


class SegmentStatus(str, enum.Enum):
    """
    片段处理状态枚举

    - pending: 等待处理
    - synthesizing: 正在合成
    - success: 成功
    - failed: 失败
    """
    PENDING = "pending"
    SYNTHESIZING = "synthesizing"
    SUCCESS = "success"
    FAILED = "failed"


class AudioSegment(Base):
    """
    音频片段数据模型

    存储每个TTS合成片段的详细信息。
    是最小的音频处理单元。
    """

    __tablename__ = "audio_segments"

    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 外键关联
    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 片段序号
    segment_index = Column(Integer, nullable=False, comment="片段序号")

    # 文本内容
    text_content = Column(Text, nullable=False, comment="文本内容")
    raw_text = Column(Text, nullable=True, comment="原始文本（未经预处理）")

    # 角色与情感标注
    role = Column(String(100), nullable=True, comment="角色名（旁白/角色名）")
    emotion = Column(String(50), nullable=True, comment="情感标注")
    emotion_intensity = Column(String(20), nullable=True, comment="情感强度（low/medium/high）")

    # 朗读参数
    speed = Column(String(20), default="normal", comment="语速（slow/normal/fast）")
    pause_after = Column(String(20), nullable=True, comment="段后停顿时长")
    voice_id = Column(String(100), nullable=True, comment="使用的音色ID")

    # 处理状态
    status = Column(
        Enum(SegmentStatus),
        default=SegmentStatus.PENDING,
        nullable=False,
        index=True,
    )

    # MiniMax 调用信息
    minimax_request_id = Column(String(255), nullable=True, comment="MiniMax请求ID")
    minimax_cost = Column(Integer, default=0, comment="MiniMax消耗字符数")
    deepseek_cost = Column(Integer, default=0, comment="DeepSeek消耗Token数")

    # 音频文件信息
    audio_file_path = Column(String(1000), nullable=True, comment="MinIO存储路径")
    audio_url = Column(String(1000), nullable=True, comment="预签名访问URL")
    audio_duration_ms = Column(Integer, nullable=True, comment="音频时长（毫秒）")
    audio_file_size = Column(BigInteger, nullable=True, comment="文件大小（字节）")

    # 重试信息
    retry_count = Column(Integer, default=0, comment="重试次数")
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 额外参数（JSON格式存储）
    extra_params = Column(JSON, nullable=True, comment="额外参数")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # 关联关系
    chapter = relationship("Chapter", back_populates="segments")

    # 索引
    __table_args__ = (
        Index("ix_segments_chapter_index", "chapter_id", "segment_index", unique=True),
    )

    def __repr__(self) -> str:
        return f"<AudioSegment(id={self.id}, chapter_id={self.chapter_id}, index={self.segment_index}, status='{self.status}')>"

    @property
    def audio_duration_seconds(self) -> Optional[float]:
        """获取音频时长（秒）"""
        if self.audio_duration_ms:
            return self.audio_duration_ms / 1000
        return None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "chapter_id": self.chapter_id,
            "segment_index": self.segment_index,
            "text_content": self.text_content,
            "role": self.role,
            "emotion": self.emotion,
            "emotion_intensity": self.emotion_intensity,
            "speed": self.speed,
            "voice_id": self.voice_id,
            "status": self.status.value if self.status else None,
            "audio_url": self.audio_url,
            "audio_duration_ms": self.audio_duration_ms,
            "audio_duration_seconds": self.audio_duration_seconds,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
