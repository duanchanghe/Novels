# ===========================================
# 监听 Schema
# ===========================================

"""
文件夹监听相关的 Pydantic 数据模型
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WatchStatusResponse(BaseModel):
    """监听状态响应模型"""
    enabled: bool
    running: bool
    watch_dir: str
    recent_files: List[dict] = Field(default_factory=list)


class WatchHistoryItem(BaseModel):
    """监听历史项模型"""
    id: int
    title: str
    file_name: Optional[str] = None
    status: str
    total_chapters: int = 0
    processed_chapters: int = 0
    created_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WatchHistoryResponse(BaseModel):
    """监听历史响应模型"""
    total: int
    page: int
    page_size: int
    items: List[WatchHistoryItem]
