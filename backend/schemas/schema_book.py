# ===========================================
# 书籍 Schema
# ===========================================

"""
书籍相关的 Pydantic 数据模型
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class BookBase(BaseModel):
    """书籍基础模型"""
    title: str = Field(..., description="书名")
    author: Optional[str] = Field(None, description="作者")
    description: Optional[str] = Field(None, description="书籍简介")
    language: str = Field("zh-CN", description="语言")


class BookCreate(BookBase):
    """创建书籍请求模型"""
    file_path: Optional[str] = Field(None, description="文件路径")
    source_type: str = Field("manual", description="来源类型")


class BookResponse(BaseModel):
    """书籍响应模型"""
    id: int
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    language: str = "zh-CN"
    cover_image_url: Optional[str] = None
    file_name: str
    file_size: Optional[int] = None
    status: str
    source_type: str
    generation_mode: str = "auto"
    total_chapters: int = 0
    processed_chapters: int = 0
    progress_percentage: float = 0.0
    total_duration: int = 0
    auto_publish_enabled: bool = False
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BookListResponse(BaseModel):
    """书籍列表响应模型"""
    total: int
    page: int
    page_size: int
    items: List[BookResponse]
