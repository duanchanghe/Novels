# ===========================================
# 领域事件
# ===========================================

"""
领域事件 - 发布-订阅模式实现

事件用于解耦业务逻辑，当某个业务操作完成时发布事件，
订阅者可以响应事件执行相应的处理逻辑。
"""

from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import json


@dataclass
class DomainEvent:
    """
    领域事件基类

    所有领域事件都应继承此类。

    Attributes:
        event_id: 事件唯一标识
        occurred_on: 事件发生时间
        event_type: 事件类型
    """

    event_id: str = field(default_factory=lambda: f"{datetime.now().timestamp()}")
    occurred_on: datetime = field(default_factory=datetime.utcnow)
    event_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_on": self.occurred_on.isoformat(),
            **self._to_dict(),
        }

    def _to_dict(self) -> Dict[str, Any]:
        """子类实现的具体数据"""
        return {}

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict())


# ===========================================
# 书籍事件
# ===========================================

@dataclass
class BookCreatedEvent(DomainEvent):
    """书籍创建事件"""

    event_type: str = "book.created"
    aggregate_id: Optional[int] = None
    title: str = ""
    author: Optional[str] = None
    source_type: str = "manual"

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "title": self.title,
            "author": self.author,
            "source_type": self.source_type,
        }


@dataclass
class BookUpdatedEvent(DomainEvent):
    """书籍更新事件"""

    event_type: str = "book.updated"
    aggregate_id: Optional[int] = None
    title: Optional[str] = None
    status: Optional[str] = None
    changes: Dict[str, Any] = field(default_factory=dict)

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "title": self.title,
            "status": self.status,
            "changes": self.changes,
        }


@dataclass
class BookDeletedEvent(DomainEvent):
    """书籍删除事件"""

    event_type: str = "book.deleted"
    aggregate_id: Optional[int] = None
    title: str = ""

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "title": self.title,
        }


@dataclass
class BookCompletedEvent(DomainEvent):
    """书籍生成完成事件"""

    event_type: str = "book.completed"
    aggregate_id: Optional[int] = None
    title: str = ""
    total_chapters: int = 0
    total_duration: int = 0

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "title": self.title,
            "total_chapters": self.total_chapters,
            "total_duration": self.total_duration,
        }


@dataclass
class BookFailedEvent(DomainEvent):
    """书籍生成失败事件"""

    event_type: str = "book.failed"
    aggregate_id: Optional[int] = None
    title: str = ""
    error_message: str = ""
    error_count: int = 0

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "title": self.title,
            "error_message": self.error_message,
            "error_count": self.error_count,
        }


# ===========================================
# 章节事件
# ===========================================

@dataclass
class ChapterCreatedEvent(DomainEvent):
    """章节创建事件"""

    event_type: str = "chapter.created"
    aggregate_id: Optional[int] = None
    book_id: int = 0
    chapter_index: int = 0
    title: str = ""

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "book_id": self.book_id,
            "chapter_index": self.chapter_index,
            "title": self.title,
        }


@dataclass
class ChapterAnalyzedEvent(DomainEvent):
    """章节分析完成事件"""

    event_type: str = "chapter.analyzed"
    aggregate_id: Optional[int] = None
    book_id: int = 0
    chapter_index: int = 0
    character_count: int = 0

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "book_id": self.book_id,
            "chapter_index": self.chapter_index,
            "character_count": self.character_count,
        }


@dataclass
class ChapterCompletedEvent(DomainEvent):
    """章节生成完成事件"""

    event_type: str = "chapter.completed"
    aggregate_id: Optional[int] = None
    book_id: int = 0
    chapter_index: int = 0
    audio_duration: int = 0
    segment_count: int = 0

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "book_id": self.book_id,
            "chapter_index": self.chapter_index,
            "audio_duration": self.audio_duration,
            "segment_count": self.segment_count,
        }


@dataclass
class ChapterFailedEvent(DomainEvent):
    """章节生成失败事件"""

    event_type: str = "chapter.failed"
    aggregate_id: Optional[int] = None
    book_id: int = 0
    chapter_index: int = 0
    error_message: str = ""

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "book_id": self.book_id,
            "chapter_index": self.chapter_index,
            "error_message": self.error_message,
        }


# ===========================================
# 片段事件
# ===========================================

@dataclass
class SegmentCreatedEvent(DomainEvent):
    """片段创建事件"""

    event_type: str = "segment.created"
    aggregate_id: Optional[int] = None
    chapter_id: int = 0
    segment_index: int = 0
    speaker: str = ""

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "chapter_id": self.chapter_id,
            "segment_index": self.segment_index,
            "speaker": self.speaker,
        }


@dataclass
class SegmentSynthesizedEvent(DomainEvent):
    """片段合成完成事件"""

    event_type: str = "segment.synthesized"
    aggregate_id: Optional[int] = None
    chapter_id: int = 0
    segment_index: int = 0
    audio_duration_ms: int = 0
    voice_id: str = ""

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "chapter_id": self.chapter_id,
            "segment_index": self.segment_index,
            "audio_duration_ms": self.audio_duration_ms,
            "voice_id": self.voice_id,
        }


@dataclass
class SegmentFailedEvent(DomainEvent):
    """片段合成失败事件"""

    event_type: str = "segment.failed"
    aggregate_id: Optional[int] = None
    chapter_id: int = 0
    segment_index: int = 0
    error_message: str = ""
    retry_count: int = 0

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "chapter_id": self.chapter_id,
            "segment_index": self.segment_index,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }


# ===========================================
# 发布事件
# ===========================================

@dataclass
class PublishStartedEvent(DomainEvent):
    """发布开始事件"""

    event_type: str = "publish.started"
    book_id: int = 0
    channel_ids: list = field(default_factory=list)

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "book_id": self.book_id,
            "channel_ids": self.channel_ids,
        }


@dataclass
class PublishCompletedEvent(DomainEvent):
    """发布完成事件"""

    event_type: str = "publish.completed"
    book_id: int = 0
    channel_id: int = 0
    external_album_id: str = ""
    success: bool = True

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "book_id": self.book_id,
            "channel_id": self.channel_id,
            "external_album_id": self.external_album_id,
            "success": self.success,
        }


# ===========================================
# 事件总线（简单实现）
# ===========================================


class EventBus:
    """
    事件总线

    实现简单的发布-订阅模式。
    生产环境中建议使用 Redis 或 Kafka。
    """

    _handlers: Dict[str, list] = {}

    @classmethod
    def subscribe(cls, event_type: str, handler: callable):
        """
        订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)

    @classmethod
    def unsubscribe(cls, event_type: str, handler: callable):
        """
        取消订阅

        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type in cls._handlers:
            cls._handlers[event_type] = [
                h for h in cls._handlers[event_type] if h != handler
            ]

    @classmethod
    def publish(cls, event: DomainEvent):
        """
        发布事件

        Args:
            event: 领域事件
        """
        handlers = cls._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # 记录错误但不影响主流程
                import logging
                logger = logging.getLogger("audiobook.events")
                logger.error(f"事件处理失败: {event.event_type} - {e}")
