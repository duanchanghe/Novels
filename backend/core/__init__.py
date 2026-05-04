# ===========================================
# Core 模块 - 包含核心配置和基础功能
# ===========================================

"""
Core 模块 - 核心基础设施

包含:
- config: 应用配置
- constants: 常量定义
- exceptions: 异常定义
- domain: 领域驱动设计
  - models: Pydantic 领域模型
  - services: 领域服务
  - events: 领域事件
  - repositories: 仓储接口
  - exceptions: 领域异常
- infrastructure: 基础设施
  - database: 数据库实现
  - repositories: 仓储实现
"""

default_app_config = "core.apps.CoreConfig"

# 配置
from .config import settings, get_settings

# 异常 - 从 domain.exceptions 导出
from .domain.exceptions import (
    DomainError,
    BookNotFoundError,
    BookAlreadyExistsError,
    BookInInvalidStateError,
    InvalidStateTransitionError,
    ChapterNotFoundError,
    ChapterAlreadyExistsError,
    SegmentNotFoundError,
    ChannelNotFoundError,
    PublishError,
    StorageError,
    FileNotFoundError,
    ValidationError,
    FileFormatError,
    DRMProtectedError,
)

from .domain.exceptions import (
    EPUBParseError,
    APIError,
    DeepSeekAPIError,
    MiniMaxAPIError,
    ServiceError,
)

# 别名导出（向后兼容）
AppError = ServiceError
NotFoundError = BookNotFoundError
TaskError = ServiceError
AudioProcessingError = ServiceError
DeepSeekApiError = DeepSeekAPIError
MiniMaxApiError = MiniMaxAPIError

# Domain 层
from .domain import (
    # Models
    BookModel,
    ChapterModel,
    SegmentModel,
    PublishChannelModel,
    PublishRecordModel,
    VoiceProfileModel,
    # Services
    BookDomainService,
    ChapterDomainService,
    SegmentDomainService,
    # Events
    DomainEvent,
    BookCreatedEvent,
    BookCompletedEvent,
    ChapterAnalyzedEvent,
    ChapterCompletedEvent,
    SegmentSynthesizedEvent,
    # Exceptions
    DomainError,
    BookNotFoundError,
    ChapterNotFoundError,
    SegmentNotFoundError,
    InvalidStateTransitionError,
)

# Infrastructure 层
from .infrastructure import DatabaseUnitOfWork, get_unit_of_work

__all__ = [
    # Config
    "settings",
    "get_settings",
    # Exceptions (new names)
    "DomainError",
    "BookNotFoundError",
    "BookAlreadyExistsError",
    "BookInInvalidStateError",
    "InvalidStateTransitionError",
    "ChapterNotFoundError",
    "ChapterAlreadyExistsError",
    "SegmentNotFoundError",
    "ChannelNotFoundError",
    "PublishError",
    "StorageError",
    "FileNotFoundError",
    "ValidationError",
    "FileFormatError",
    "DRMProtectedError",
    "EPUBParseError",
    "APIError",
    "DeepSeekAPIError",
    "MiniMaxAPIError",
    "ServiceError",
    # Exceptions (aliases for backward compatibility)
    "AppError",
    "NotFoundError",
    "TaskError",
    "AudioProcessingError",
    "DeepSeekApiError",
    "MiniMaxApiError",
    # Domain Models
    "BookModel",
    "ChapterModel",
    "SegmentModel",
    "PublishChannelModel",
    "PublishRecordModel",
    "VoiceProfileModel",
    # Domain Services
    "BookDomainService",
    "ChapterDomainService",
    "SegmentDomainService",
    "PipelineDomainService",
    # Domain Events
    "DomainEvent",
    "BookCreatedEvent",
    "BookCompletedEvent",
    "ChapterAnalyzedEvent",
    "ChapterCompletedEvent",
    "SegmentSynthesizedEvent",
    # Infrastructure
    "DatabaseUnitOfWork",
    "get_unit_of_work",
]
