# ===========================================
# 发布渠道模型
# ===========================================

"""
发布渠道数据模型

定义发布渠道（PublishChannel）的数据库结构。
存储有声书发布的目标平台配置。
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
    Index,
    JSON,
)
from sqlalchemy.orm import relationship

from core.database import Base


class PlatformType(str, enum.Enum):
    """
    平台类型枚举

    - self_hosted: 自建平台（MinIO直链）
    - ximalaya: 喜马拉雅
    - qingting: 蜻蜓FM
    -荔枝: 荔枝FM
    - custom: 自定义平台
    """
    SELF_HOSTED = "self_hosted"
    XIMALAYA = "ximalaya"
    QINGTING = "qingting"
    LIZHI = "lizhi"
    CUSTOM = "custom"


class PublishChannel(Base):
    """
    发布渠道数据模型

    存储有声书发布目标平台的配置信息。
    """

    __tablename__ = "publish_channels"

    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 渠道名称
    name = Column(String(100), nullable=False, comment="渠道名称")
    description = Column(Text, nullable=True, comment="渠道描述")

    # 平台类型
    platform_type = Column(
        Enum(PlatformType),
        default=PlatformType.SELF_HOSTED,
        nullable=False,
        comment="平台类型",
    )

    # API 配置（加密存储）
    api_config = Column(JSON, nullable=True, comment="API配置（加密存储）")

    # OAuth 配置（部分平台需要）
    oauth_client_id = Column(String(255), nullable=True, comment="OAuth客户端ID")
    oauth_access_token = Column(String(1000), nullable=True, comment="OAuth访问令牌")
    oauth_refresh_token = Column(String(1000), nullable=True, comment="OAuth刷新令牌")
    oauth_expires_at = Column(DateTime, nullable=True, comment="令牌过期时间")

    # 渠道配置
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    auto_publish = Column(Boolean, default=False, nullable=False, comment="是否自动发布")
    priority = Column(Integer, default=0, comment="发布优先级")

    # 发布设置
    publish_as_draft = Column(Boolean, default=True, comment="是否发布为草稿")
    category = Column(String(100), nullable=True, comment="分类")
    tags = Column(JSON, nullable=True, comment="标签列表")

    # 统计
    total_published = Column(Integer, default=0, comment="已发布书籍数")
    success_count = Column(Integer, default=0, comment="成功次数")
    failure_count = Column(Integer, default=0, comment="失败次数")
    last_published_at = Column(DateTime, nullable=True, comment="最后发布时间")

    # 用户配置
    user_id = Column(String(100), nullable=True, comment="用户ID（多用户支持）")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # 关联关系
    publish_records = relationship(
        "PublishRecord",
        back_populates="channel",
        cascade="all, delete-orphan",
    )

    # 索引
    __table_args__ = (
        Index("ix_publish_channels_type_enabled", "platform_type", "is_enabled"),
        Index("ix_publish_channels_user", "user_id", "is_enabled"),
    )

    def __repr__(self) -> str:
        return f"<PublishChannel(id={self.id}, name='{self.name}', type='{self.platform_type}')>"

    @property
    def is_oauth_expired(self) -> bool:
        """检查 OAuth 令牌是否过期"""
        if self.oauth_expires_at:
            return datetime.utcnow() >= self.oauth_expires_at
        return False

    def get_api_config(self) -> Dict[str, Any]:
        """
        获取 API 配置

        Returns:
            dict: API 配置字典
        """
        return self.api_config or {}

    def to_dict(self, include_secrets: bool = False) -> dict:
        """
        转换为字典格式

        Args:
            include_secrets: 是否包含敏感信息

        Returns:
            dict: 配置字典
        """
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "platform_type": self.platform_type.value if self.platform_type else None,
            "is_enabled": self.is_enabled,
            "auto_publish": self.auto_publish,
            "priority": self.priority,
            "publish_as_draft": self.publish_as_draft,
            "category": self.category,
            "tags": self.tags,
            "total_published": self.total_published,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_published_at": self.last_published_at.isoformat() if self.last_published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_secrets:
            data["api_config"] = self.api_config
            data["oauth_access_token"] = self.oauth_access_token

        return data
