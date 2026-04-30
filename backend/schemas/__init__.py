# ===========================================
# Pydantic 数据模型模块
# ===========================================

"""
Pydantic 数据模型模块

包含所有 API 请求/响应的数据模型定义。
"""

from .schema_book import BookBase, BookCreate, BookResponse, BookListResponse
from .schema_chapter import ChapterBase, ChapterResponse
from .schema_voice import VoiceProfileResponse, VoiceListResponse
from .schema_watch import WatchStatusResponse, WatchHistoryResponse
from .schema_publish import PublishChannelResponse, PublishRecordResponse

__all__ = [
    "BookBase",
    "BookCreate",
    "BookResponse",
    "BookListResponse",
    "ChapterBase",
    "ChapterResponse",
    "VoiceProfileResponse",
    "VoiceListResponse",
    "WatchStatusResponse",
    "WatchHistoryResponse",
    "PublishChannelResponse",
    "PublishRecordResponse",
]
