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
from core.models.character import Character, CharacterStatus, GenderType
from core.models.paragraph import (
    Paragraph,
    ParagraphType,
    EmotionType,
    EmotionIntensity,
)
from core.models.sound_effect import (
    SoundEffect,
    SoundEffectUsage,
    SoundEffectCollection,
    SoundEffectCollectionItem,
    SoundEffectType,
    SoundLayer,
    SoundPriority,
    SoundSource,
    SoundEffectStatus,
)

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
    # Character
    "Character",
    "CharacterStatus",
    "GenderType",
    # Paragraph
    "Paragraph",
    "ParagraphType",
    "EmotionType",
    "EmotionIntensity",
    # Sound Effect
    "SoundEffect",
    "SoundEffectUsage",
    "SoundEffectCollection",
    "SoundEffectCollectionItem",
    "SoundEffectType",
    "SoundLayer",
    "SoundPriority",
    "SoundSource",
    "SoundEffectStatus",
]
