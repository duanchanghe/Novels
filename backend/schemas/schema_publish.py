# ===========================================
# 发布 Schema
# ===========================================

"""
发布相关的 Pydantic 数据模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class PublishChannelResponse(BaseModel):
    """发布渠道响应模型"""
    id: int
    name: str
    description: Optional[str] = None
    platform_type: str
    is_enabled: bool = True
    auto_publish: bool = False
    priority: int = 0
    total_published: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PublishRecordResponse(BaseModel):
    """发布记录响应模型"""
    id: int
    book_id: int
    channel_id: int
    external_album_id: Optional[str] = None
    external_album_url: Optional[str] = None
    status: str
    chapters_published: Optional[Dict[str, str]] = None
    total_chapters: int = 0
    published_chapters: int = 0
    failed_chapters: int = 0
    progress_percentage: float = 0.0
    error_message: Optional[str] = None
    retry_count: int = 0
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PublishStatusResponse(BaseModel):
    """发布状态响应模型"""
    book_id: int
    records: List[PublishRecordResponse]
