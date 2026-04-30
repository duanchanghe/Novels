# ===========================================
# 音色配置模型
# ===========================================

"""
音色配置数据模型

定义音色配置（VoiceProfile）的数据库结构。
存储系统预设和用户定制的音色配置。
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
    Float,
)
from sqlalchemy.orm import relationship

from core.database import Base


class RoleType(str, enum.Enum):
    """
    角色类型枚举

    - narrator: 旁白/叙述者
    - male_lead: 男主角
    - female_lead: 女主角
    - elderly: 老人
    - child: 儿童
    - villain: 反派
    - supporting: 配角
    - custom: 自定义
    """
    NARRATOR = "narrator"
    MALE_LEAD = "male_lead"
    FEMALE_LEAD = "female_lead"
    ELDERLY = "elderly"
    CHILD = "child"
    VILLAIN = "villain"
    SUPPORTING = "supporting"
    CUSTOM = "custom"


class VoiceProfile(Base):
    """
    音色配置数据模型

    存储音色配置信息，包括系统预设和用户自定义配置。
    """

    __tablename__ = "voice_profiles"

    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 关联书籍（可选，系统预设的音色不关联书籍）
    book_id = Column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 音色名称
    name = Column(String(100), nullable=False, comment="音色名称")
    description = Column(Text, nullable=True, comment="音色描述")

    # 角色类型
    role_type = Column(
        Enum(RoleType),
        default=RoleType.NARRATOR,
        nullable=False,
        comment="角色类型",
    )

    # 角色名称（用于匹配的角色名）
    character_names = Column(JSON, nullable=True, comment="关联的角色名称列表")

    # MiniMax 音色配置
    minimax_voice_id = Column(String(100), nullable=True, comment="MiniMax音色ID")
    minimax_model = Column(String(50), default="speech-01-turbo", comment="MiniMax模型")

    # 朗读参数
    speed = Column(Float, default=1.0, comment="语速倍率（0.5~2.0）")
    pitch = Column(Float, default=0.0, comment="音调（-1.0~1.0）")
    volume = Column(Float, default=1.0, comment="音量（0.0~1.0）")

    # 情感参数（JSON格式）
    emotion_params = Column(JSON, nullable=True, comment="情感参数配置")

    # 系统预设标识
    is_system_preset = Column(Boolean, default=False, nullable=False, comment="是否系统预设")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 用户信息（创建者）
    created_by = Column(String(100), nullable=True, comment="创建者")

    # 排序
    sort_order = Column(Integer, default=0, comment="排序顺序")

    # 统计
    usage_count = Column(Integer, default=0, comment="使用次数")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # 关联关系
    book = relationship("Book", back_populates="voice_profiles")

    # 索引
    __table_args__ = (
        Index("ix_voice_profiles_book_role", "book_id", "role_type"),
    )

    def __repr__(self) -> str:
        return f"<VoiceProfile(id={self.id}, name='{self.name}', role_type='{self.role_type}')>"

    def get_minimax_params(self) -> Dict[str, Any]:
        """
        获取 MiniMax TTS 调用参数

        Returns:
            dict: MiniMax API 调用参数字典
        """
        return {
            "model": self.minimax_model,
            "voice_id": self.minimax_voice_id,
            "speed": self.speed,
            "pitch": self.pitch,
            "volume": self.volume,
            "emotion_params": self.emotion_params or {},
        }

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "book_id": self.book_id,
            "name": self.name,
            "description": self.description,
            "role_type": self.role_type.value if self.role_type else None,
            "character_names": self.character_names,
            "minimax_voice_id": self.minimax_voice_id,
            "minimax_model": self.minimax_model,
            "speed": self.speed,
            "pitch": self.pitch,
            "volume": self.volume,
            "emotion_params": self.emotion_params,
            "is_system_preset": self.is_system_preset,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# 系统预设音色配置
DEFAULT_VOICE_PROFILES = [
    {
        "name": "默认旁白",
        "role_type": RoleType.NARRATOR,
        "description": "标准的叙述者音色，适合小说旁白",
        "minimax_voice_id": "male-qn",
        "speed": 1.0,
        "is_system_preset": True,
    },
    {
        "name": "青年男性",
        "role_type": RoleType.MALE_LEAD,
        "description": "青年男性主角音色",
        "minimax_voice_id": "male-qn",
        "speed": 1.0,
        "is_system_preset": True,
    },
    {
        "name": "青年女性",
        "role_type": RoleType.FEMALE_LEAD,
        "description": "青年女性主角音色",
        "minimax_voice_id": "female-shaon",
        "speed": 1.0,
        "is_system_preset": True,
    },
    {
        "name": "老年男性",
        "role_type": RoleType.ELDERLY,
        "description": "老年男性音色，较为沉稳",
        "minimax_voice_id": "male-yun",
        "speed": 0.9,
        "is_system_preset": True,
    },
    {
        "name": "儿童",
        "role_type": RoleType.CHILD,
        "description": "儿童音色，活泼可爱",
        "minimax_voice_id": "female-xiang",
        "speed": 1.1,
        "is_system_preset": True,
    },
    {
        "name": "反派",
        "role_type": RoleType.VILLAIN,
        "description": "反派角色音色，带有威胁感",
        "minimax_voice_id": "male-tian",
        "speed": 0.95,
        "is_system_preset": True,
    },
]
