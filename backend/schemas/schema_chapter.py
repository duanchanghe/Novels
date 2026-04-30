# ===========================================
# 章节 Schema
# ===========================================

"""
章节相关的 Pydantic 数据模型
"""

from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, Field


class ChapterBase(BaseModel):
    """章节基础模型"""
    title: Optional[str] = Field(None, description="章节标题")
    raw_text: Optional[str] = Field(None, description="原始文本")
    cleaned_text: Optional[str] = Field(None, description="清洗后文本")


class ChapterResponse(BaseModel):
    """章节响应模型"""
    id: int
    book_id: int
    chapter_index: int
    title: Optional[str] = None
    status: str
    audio_url: Optional[str] = None
    audio_duration: Optional[int] = None
    audio_format: str = "mp3"
    total_segments: int = 0
    completed_segments: int = 0
    progress_percentage: float = 0.0
    deepseek_tokens: int = 0
    minimax_characters: int = 0
    estimated_cost: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChapterDetailResponse(ChapterResponse):
    """章节详情响应模型"""
    raw_text: Optional[str] = None
    cleaned_text: Optional[str] = None
    analysis_result: Optional[Any] = None
    characters: Optional[List[dict]] = None
