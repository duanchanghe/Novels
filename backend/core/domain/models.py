# ===========================================
# Pydantic 领域模型
# ===========================================

"""
Pydantic 领域模型定义

这些模型用于：
1. API 请求/响应验证
2. 服务层数据传递
3. 跨层数据传输

注意：这些不是 Django ORM 模型，而是纯数据对象。
Django ORM 模型定义在 core.models 中。
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# ===========================================
# 枚举定义
# ===========================================

class BookStatus(str, Enum):
    """书籍处理状态"""
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    SYNTHESIZING = "SYNTHESIZING"
    POST_PROCESSING = "POST_PROCESSING"
    PUBLISHING = "PUBLISHING"
    DONE = "DONE"
    FAILED = "FAILED"


class SourceType(str, Enum):
    """书籍来源类型"""
    MANUAL = "manual"
    WATCH = "watch"


class GenerationMode(str, Enum):
    """有声书生成模式"""
    AUTO = "auto"
    MANUAL = "manual"


class ChapterStatus(str, Enum):
    """章节处理状态"""
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    SYNTHESIZING = "SYNTHESIZING"
    AWAITING_CONFIRM = "AWAITING_CONFIRM"
    DONE = "DONE"
    FAILED = "FAILED"


class SegmentStatus(str, Enum):
    """片段处理状态"""
    PENDING = "PENDING"
    SYNTHESIZING = "SYNTHESIZING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PublishStatus(str, Enum):
    """发布状态"""
    PENDING = "pending"
    PREPARING = "preparing"
    UPLOADING = "uploading"
    DONE = "done"
    FAILED = "failed"
    PARTIALLY_DONE = "partially_done"


class PlatformType(str, Enum):
    """平台类型"""
    SELF_HOSTED = "self_hosted"
    XIMALAYA = "ximalaya"
    QINGTING = "qingting"
    LIZHI = "lizhi"
    CUSTOM = "custom"


class RoleType(str, Enum):
    """角色类型"""
    NARRATOR = "narrator"
    MALE_LEAD = "male_lead"
    FEMALE_LEAD = "female_lead"
    ELDERLY = "elderly"
    CHILD = "child"
    VILLAIN = "villain"
    SUPPORTING = "supporting"
    CUSTOM = "custom"


# ===========================================
# 领域模型定义
# ===========================================

class CharacterInfo(BaseModel):
    """角色信息"""
    name: str
    aliases: List[str] = Field(default_factory=list)
    role_type: Optional[str] = None
    dialogue_count: int = 0
    emotions: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """DeepSeek 分析结果"""
    paragraphs: List[Dict[str, Any]] = Field(default_factory=list)
    characters: List[CharacterInfo] = Field(default_factory=list)
    statistics: Optional[Dict[str, Any]] = None
    token_usage: int = 0


class BookModel(BaseModel):
    """书籍领域模型"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    language: str = "zh-CN"

    cover_image_url: Optional[str] = None
    cover_image_path: Optional[str] = None

    file_name: str
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    file_path: Optional[str] = None

    status: BookStatus = BookStatus.PENDING
    source_type: SourceType = SourceType.MANUAL
    generation_mode: GenerationMode = GenerationMode.AUTO

    total_chapters: int = 0
    processed_chapters: int = 0
    total_duration: int = 0

    full_audio_path: Optional[str] = None
    full_audio_duration: Optional[int] = None
    full_audio_size: Optional[int] = None
    full_audio_format: str = "m4b"

    auto_publish_enabled: bool = False
    watch_path: Optional[str] = None

    error_message: Optional[str] = None
    error_count: int = 0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @property
    def progress_percentage(self) -> float:
        """计算处理进度百分比"""
        if self.total_chapters == 0:
            return 0.0
        return round((self.processed_chapters / self.total_chapters) * 100, 2)

    class Meta:
        """元信息"""
        from_attributes = True


class ChapterModel(BaseModel):
    """章节领域模型"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    book_id: int
    chapter_index: int
    title: Optional[str] = None

    raw_text: Optional[str] = None
    cleaned_text: Optional[str] = None

    analysis_result: Optional[Dict[str, Any]] = None
    characters: Optional[List[Dict[str, Any]]] = None

    status: ChapterStatus = ChapterStatus.PENDING

    next_chapter_id: Optional[int] = None

    audio_file_path: Optional[str] = None
    audio_url: Optional[str] = None
    audio_duration: Optional[int] = None
    audio_file_size: Optional[int] = None
    audio_format: str = "mp3"

    total_segments: int = 0
    completed_segments: int = 0
    failed_segments: int = 0

    deepseek_tokens: int = 0
    minimax_characters: int = 0
    estimated_cost: int = 0

    error_message: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def progress_percentage(self) -> float:
        """计算处理进度百分比"""
        if self.total_segments == 0:
            return 0.0
        return round((self.completed_segments / self.total_segments) * 100, 2)


class SegmentModel(BaseModel):
    """音频片段领域模型"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    chapter_id: int
    segment_index: int

    text_content: str
    raw_text: Optional[str] = None

    role: Optional[str] = None
    emotion: Optional[str] = None
    emotion_intensity: Optional[str] = None

    speed: str = "normal"
    pause_after: Optional[str] = None
    voice_id: Optional[str] = None

    status: SegmentStatus = SegmentStatus.PENDING

    minimax_request_id: Optional[str] = None
    minimax_cost: int = 0
    deepseek_cost: int = 0

    audio_file_path: Optional[str] = None
    audio_url: Optional[str] = None
    audio_duration_ms: Optional[int] = None
    audio_file_size: Optional[int] = None

    retry_count: int = 0
    error_message: Optional[str] = None

    extra_params: Optional[Dict[str, Any]] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def audio_duration_seconds(self) -> Optional[float]:
        """获取音频时长（秒）"""
        if self.audio_duration_ms:
            return self.audio_duration_ms / 1000
        return None


class PublishChannelModel(BaseModel):
    """发布渠道领域模型"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    platform_type: PlatformType = PlatformType.SELF_HOSTED

    api_config: Optional[Dict[str, Any]] = None

    oauth_client_id: Optional[str] = None
    oauth_access_token: Optional[str] = None
    oauth_refresh_token: Optional[str] = None
    oauth_expires_at: Optional[datetime] = None

    is_enabled: bool = True
    auto_publish: bool = False
    priority: int = 0

    publish_as_draft: bool = True
    category: Optional[str] = None
    tags: Optional[List[str]] = None

    total_published: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_published_at: Optional[datetime] = None

    user_id: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_oauth_expired(self) -> bool:
        """检查 OAuth 令牌是否过期"""
        if self.oauth_expires_at:
            return datetime.now() >= self.oauth_expires_at
        return False


class PublishRecordModel(BaseModel):
    """发布记录领域模型"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    book_id: int
    channel_id: int

    external_album_id: Optional[str] = None
    external_album_url: Optional[str] = None
    external_category_id: Optional[str] = None

    status: PublishStatus = PublishStatus.PENDING

    chapters_published: Optional[Dict[str, Any]] = None

    total_chapters: int = 0
    published_chapters: int = 0
    failed_chapters: int = 0

    api_calls: int = 0
    estimated_cost: int = 0

    result_details: Optional[Dict[str, Any]] = None

    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_count: int = 0

    celery_task_id: Optional[str] = None

    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def progress_percentage(self) -> float:
        """计算发布进度百分比"""
        if self.total_chapters == 0:
            return 0.0
        return round((self.published_chapters / self.total_chapters) * 100, 2)

    @property
    def is_complete(self) -> bool:
        """是否完成发布"""
        return self.status in [PublishStatus.DONE, PublishStatus.PARTIALLY_DONE]

    @property
    def is_success(self) -> bool:
        """是否发布成功"""
        return self.status == PublishStatus.DONE


class VoiceProfileModel(BaseModel):
    """音色配置领域模型"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    book_id: Optional[int] = None

    name: str
    description: Optional[str] = None

    role_type: RoleType = RoleType.NARRATOR

    character_names: Optional[List[str]] = None

    minimax_voice_id: Optional[str] = None
    minimax_model: str = "speech-01-turbo"

    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0

    emotion_params: Optional[Dict[str, Any]] = None

    is_system_preset: bool = False
    is_active: bool = True

    created_by: Optional[str] = None

    sort_order: int = 0
    usage_count: int = 0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ===========================================
# 请求/响应模型
# ===========================================

class BookListRequest(BaseModel):
    """书籍列表请求"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[BookStatus] = None
    search: Optional[str] = None
    source_type: Optional[SourceType] = None


class BookListResponse(BaseModel):
    """书籍列表响应"""
    items: List[BookModel]
    total: int
    page: int
    page_size: int
    total_pages: int


class BookCreateRequest(BaseModel):
    """书籍创建请求"""
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    language: str = "zh-CN"
    source_type: SourceType = SourceType.MANUAL
    generation_mode: GenerationMode = GenerationMode.AUTO


class ChapterListRequest(BaseModel):
    """章节列表请求"""
    book_id: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    status: Optional[ChapterStatus] = None


class ChapterListResponse(BaseModel):
    """章节列表响应"""
    items: List[ChapterModel]
    total: int
    page: int
    page_size: int


class GenerateRequest(BaseModel):
    """生成请求"""
    book_id: int
    generation_mode: GenerationMode = GenerationMode.AUTO


class GenerateResponse(BaseModel):
    """生成响应"""
    book_id: int
    task_id: str
    generation_mode: GenerationMode
    status: str


class UploadResponse(BaseModel):
    """上传响应"""
    book_id: int
    title: str
    author: Optional[str]
    total_chapters: int
    file_size: int


class ErrorResponse(BaseModel):
    """错误响应"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    service: str
    version: str
    database: str = "connected"
    redis: str = "connected"
    minio: str = "connected"
