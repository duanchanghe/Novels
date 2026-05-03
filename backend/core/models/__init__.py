# ===========================================
# Models
# ===========================================

"""
Core data models for AI 有声书工坊.
"""

from core.models.book import Book, BookStatus, SourceType, GenerationMode
from core.models.chapter import Chapter, ChapterStatus
from core.models.segment import AudioSegment, SegmentStatus
from core.models.task import TTSTask
from core.models.voice import VoiceProfile
from core.models.channel import PublishChannel, PlatformType
from core.models.publish import PublishRecord, PublishStatus

__all__ = [
    # Book
    "Book",
    "BookStatus",
    "SourceType",
    "GenerationMode",
    # Chapter
    "Chapter",
    "ChapterStatus",
    # Segment
    "AudioSegment",
    "SegmentStatus",
    # Task
    "TTSTask",
    # Voice
    "VoiceProfile",
    # Channel
    "PublishChannel",
    "PlatformType",
    # Publish
    "PublishRecord",
    "PublishStatus",
]
