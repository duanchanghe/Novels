# ===========================================
# Domain 层 - 领域模型定义
# ===========================================

"""
Domain 层 - 领域驱动设计核心

包含:
- domain/models.py: Pydantic 领域模型
- domain/services.py: 领域服务
- domain/repositories.py: 仓储接口
- domain/events.py: 领域事件
- domain/exceptions.py: 领域异常
"""

from .models import (
    BookModel,
    ChapterModel,
    SegmentModel,
    PublishChannelModel,
    PublishRecordModel,
    VoiceProfileModel,
)

from .services import (
    BookDomainService,
    ChapterDomainService,
    SegmentDomainService,
)

from .events import (
    DomainEvent,
    BookCreatedEvent,
    BookCompletedEvent,
    ChapterAnalyzedEvent,
    ChapterCompletedEvent,
    SegmentSynthesizedEvent,
)

from .exceptions import (
    DomainError,
    BookNotFoundError,
    ChapterNotFoundError,
    SegmentNotFoundError,
    InvalidStateTransitionError,
)

__all__ = [
    # Models
    "BookModel",
    "ChapterModel",
    "SegmentModel",
    "PublishChannelModel",
    "PublishRecordModel",
    "VoiceProfileModel",
    # Services
    "BookDomainService",
    "ChapterDomainService",
    "SegmentDomainService",
    # Events
    "DomainEvent",
    "BookCreatedEvent",
    "BookCompletedEvent",
    "ChapterAnalyzedEvent",
    "ChapterCompletedEvent",
    "SegmentSynthesizedEvent",
    # Exceptions
    "DomainError",
    "BookNotFoundError",
    "ChapterNotFoundError",
    "SegmentNotFoundError",
    "InvalidStateTransitionError",
]
