# ===========================================
# API Serializers - 模块导出
# ===========================================

"""
API 序列化器模块

包含：
- book.py: 书籍相关序列化器
- chapter.py: 章节相关序列化器
- common.py: 通用序列化器
"""

from .book import (
    BookListSerializer,
    BookDetailSerializer,
    BookCreateSerializer,
    BookUpdateSerializer,
    BookStatusSerializer,
    BookGenerateSerializer,
    BookGenerateResponseSerializer,
    BookRetrySerializer,
    BookRetryResponseSerializer,
    BookAudioSerializer,
    BookDownloadSerializer,
)

from .chapter import (
    SafeJSONField,
    ChapterListSerializer,
    ChapterDetailSerializer,
    ChapterCreateSerializer,
    ChapterUpdateSerializer,
    ChapterConfirmSerializer,
    ChapterConfirmResponseSerializer,
    ChapterRetrySerializer,
    ChapterRetryResponseSerializer,
    ChapterAudioSerializer,
    SegmentListSerializer,
    ChapterSegmentsResponseSerializer,
)

from .common import (
    PaginationSerializer,
    ErrorSerializer,
    SuccessResponseSerializer,
    ErrorResponseSerializer,
    HealthSerializer,
    FileUploadSerializer,
    VoiceSerializer,
    EmotionSerializer,
    VoiceMappingSerializer,
    VoiceConfigResponseSerializer,
    WatchStatusSerializer,
    PublishChannelSerializer,
    PublishChannelCreateSerializer,
    PublishChannelUpdateSerializer,
    PublishRecordSerializer,
    PublishRequestSerializer,
    PublishResponseSerializer,
    PublishStatusResponseSerializer,
    StatisticSerializer,
)

__all__ = [
    # Book
    "BookListSerializer",
    "BookDetailSerializer",
    "BookCreateSerializer",
    "BookUpdateSerializer",
    "BookStatusSerializer",
    "BookGenerateSerializer",
    "BookGenerateResponseSerializer",
    "BookRetrySerializer",
    "BookRetryResponseSerializer",
    "BookAudioSerializer",
    "BookDownloadSerializer",
    # Chapter
    "SafeJSONField",
    "ChapterListSerializer",
    "ChapterDetailSerializer",
    "ChapterCreateSerializer",
    "ChapterUpdateSerializer",
    "ChapterConfirmSerializer",
    "ChapterConfirmResponseSerializer",
    "ChapterRetrySerializer",
    "ChapterRetryResponseSerializer",
    "ChapterAudioSerializer",
    "SegmentListSerializer",
    "ChapterSegmentsResponseSerializer",
    # Common
    "PaginationSerializer",
    "ErrorSerializer",
    "SuccessResponseSerializer",
    "ErrorResponseSerializer",
    "HealthSerializer",
    "FileUploadSerializer",
    "VoiceSerializer",
    "EmotionSerializer",
    "VoiceMappingSerializer",
    "VoiceConfigResponseSerializer",
    "WatchStatusSerializer",
    "PublishChannelSerializer",
    "PublishChannelCreateSerializer",
    "PublishChannelUpdateSerializer",
    "PublishRecordSerializer",
    "PublishRequestSerializer",
    "PublishResponseSerializer",
    "PublishStatusResponseSerializer",
    "StatisticSerializer",
]
