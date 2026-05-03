# ===========================================
# 数据模型模块
# ===========================================

"""
数据模型模块

包含所有 SQLAlchemy 数据模型定义。
"""

from .model_book import Book, BookStatus, SourceType
from .model_chapter import Chapter, ChapterStatus
from .model_segment import AudioSegment, SegmentStatus
from .model_task import TTSTask
from .model_voice import VoiceProfile
from .model_channel import PublishChannel
from .model_publish import PublishRecord

__all__ = [
    "Book",
    "BookStatus",
    "SourceType",
    "Chapter",
    "ChapterStatus",
    "AudioSegment",
    "TTSTask",
    "VoiceProfile",
    "PublishChannel",
    "PublishRecord",
]
