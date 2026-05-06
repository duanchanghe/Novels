# ===========================================
# Django Admin 配置文件
# ===========================================

"""
核心模块的 Django 管理后台配置

本文件定义了所有核心数据模型在 Django Admin 后台的管理界面配置，
包括列表显示、筛选器、搜索、字段分组、状态徽章等功能。

主要功能：
- Book（书籍）：管理有声书的基本信息和处理状态
- Chapter（章节）：管理书籍的章节内容
- AudioSegment（音频片段）：管理每个章节的音频合成片段
- PublishChannel（发布渠道）：配置不同的发布平台
- PublishRecord（发布记录）：追踪发布历史和结果
- VoiceProfile（音色配置）：管理不同角色的语音参数
- TTSTask（TTS任务）：监控文本转语音任务的执行状态
"""

from django.contrib import admin
from django.utils.html import format_html
from .models.book import Book, BookStatus, SourceType, GenerationMode
from .models.chapter import Chapter, ChapterStatus
from .models.segment import AudioSegment, SegmentStatus
from .models.channel import PublishChannel
from .models.publish import PublishRecord, PublishStatus
from .models.voice import VoiceProfile, RoleType
from .models.task import TTSTask, TaskStatus
from .models.character import Character, CharacterStatus, GenderType
from .models.sound_effect import (
    SoundEffect, SoundEffectUsage, SoundEffectCollection, SoundEffectCollectionItem,
    SoundEffectType, SoundLayer, SoundPriority, SoundSource, SoundEffectStatus
)
from .forms import (
    CharacterForm,
    SoundEffectForm,
    SoundEffectCollectionForm,
    SoundEffectCollectionItemForm,
    SoundEffectUsageForm,
)


# ===========================================
# 状态颜色映射
# ===========================================

# 预定义的状态颜色，用于在管理界面中以不同颜色直观显示处理状态
# 颜色遵循 Bootstrap 的标准色彩语义：
# - 灰色：待处理/已取消
# - 蓝色：进行中
# - 青色：合成中
# - 黄色：等待确认/警告
# - 绿色：成功/完成
# - 红色：失败/错误

BOOK_STATUS_COLORS = {
    "PENDING": "#6c757d",          # 灰色 - 等待处理
    "ANALYZING": "#0d6efd",         # 蓝色 - 正在分析
    "SYNTHESIZING": "#0dcaf0",      # 青色 - 正在合成
    "POST_PROCESSING": "#ffc107",   # 黄色 - 正在后处理
    "PUBLISHING": "#fd7e14",        # 橙色 - 正在发布
    "DONE": "#198754",              # 绿色 - 已完成
    "FAILED": "#dc3545",            # 红色 - 失败
}

CHAPTER_STATUS_COLORS = {
    "PENDING": "#6c757d",
    "ANALYZING": "#0d6efd",
    "ANALYZED": "#6610f2",          # 紫色 - 已分析
    "SYNTHESIZING": "#0dcaf0",
    "AWAITING_CONFIRM": "#ffc107",  # 黄色 - 等待确认
    "DONE": "#198754",
    "FAILED": "#dc3545",
}

SEGMENT_STATUS_COLORS = {
    "PENDING": "#6c757d",
    "SYNTHESIZING": "#0dcaf0",
    "SUCCESS": "#198754",
    "FAILED": "#dc3545",
}

TASK_STATUS_COLORS = {
    "PENDING": "#6c757d",
    "STARTED": "#0d6efd",
    "ANALYZING": "#0d6efd",
    "SYNTHESIZING": "#0dcaf0",
    "POST_PROCESSING": "#ffc107",
    "PUBLISHING": "#fd7e14",
    "DONE": "#198754",
    "FAILED": "#dc3545",
    "CANCELLED": "#6c757d",
}

PUBLISH_STATUS_COLORS = {
    "PENDING": "#6c757d",
    "PREPARING": "#0d6efd",
    "UPLOADING": "#0dcaf0",
    "DONE": "#198754",
    "PARTIALLY_DONE": "#ffc107",
    "FAILED": "#dc3545",
}


# ===========================================
# 辅助函数
# ===========================================

def create_status_badge(status_value, status_display, color_map):
    """
    创建状态徽章的 HTML 标签

    参数:
        status_value: 状态的实际值（如 'PENDING'）
        status_display: 状态的显示名称（如 '等待处理'）
        color_map: 状态到颜色的映射字典

    返回:
        HTML 格式的状态徽章字符串，带有圆角背景色
    """
    color = color_map.get(status_value, "#6c757d")
    return format_html(
        '<span style="background-color: {}; color: white; padding: 3px 8px; '
        'border-radius: 3px; font-size: 11px;">{}</span>',
        color, status_display
    )


# ===========================================
# 书籍管理
# ===========================================

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    """
    书籍模型的管理界面配置

    功能说明：
    - 列表页显示书籍的关键信息（标题、作者、状态、进度等）
    - 支持按状态、来源、语言、创建时间进行筛选
    - 支持按书名、作者、文件哈希进行搜索
    - 详情页将字段分组显示，便于管理
    """

    # 列表页显示的字段列
    list_display = [
        "id",                    # 书籍ID
        "title",                 # 书名
        "author",                # 作者
        "status_badge",          # 状态徽章（带颜色）
        "total_chapters",        # 总章节数
        "processed_chapters",     # 已处理章节数
        "created_at",             # 创建时间
        "updated_at",             # 更新时间
    ]

    # 列表页右侧的筛选器
    list_filter = [
        "status",        # 按处理状态筛选
        "source_type",   # 按来源类型筛选（手动上传/文件夹监听）
        "language",      # 按语言筛选
        "created_at",    # 按创建时间筛选
    ]

    # 顶部的搜索框
    search_fields = [
        "title",         # 搜索书名
        "author",        # 搜索作者
        "file_hash",     # 搜索文件哈希值
    ]

    # 只读字段（不允许在后台直接修改）
    readonly_fields = [
        "id",                    # ID 由数据库自动生成
        "file_hash",            # 文件哈希值用于去重
        "created_at",            # 创建时间
        "updated_at",            # 更新时间
        "processed_chapters",    # 已处理章节数（系统计算）
        "total_duration",        # 总音频时长（系统计算）
        "progress_percentage",   # 处理进度百分比（系统计算）
    ]

    # 默认排序方式（按创建时间倒序，最新在前）
    ordering = ["-created_at"]

    # 详情页的字段分组布局
    fieldsets = (
        # 基本信息分组
        ("基本信息", {
            "description": "书籍的基本描述信息",
            "fields": (
                "id",                    # 书籍唯一标识
                "title",                 # 书名
                "author",                # 作者名
                "description",           # 书籍简介
                "language",              # 内容语言（如 zh-CN）
            )
        }),

        # 封面图片分组
        ("封面图片", {
            "description": "书籍封面图片的存储信息",
            "fields": (
                "cover_image_url",       # 封面图URL（外部链接）
                "cover_image_path",      # 封面图存储路径（本地/MinIO）
            )
        }),

        # 文件信息分组
        ("文件信息", {
            "description": "原始EPUB/PDF文件的信息",
            "fields": (
                "file_name",             # 原始文件名
                "file_size",             # 文件大小（字节）
                "file_hash",             # 文件MD5哈希（用于去重）
                "file_path",             # MinIO存储路径
            )
        }),

        # 处理状态分组
        ("处理状态", {
            "description": "控制书籍的处理模式和发布方式",
            "fields": (
                "status",                # 当前处理状态
                "source_type",           # 来源类型
                "generation_mode",       # 生成模式（自动/手动）
                "auto_publish_enabled",  # 是否启用自动发布
            )
        }),

        # 处理进度分组
        ("处理进度", {
            "description": "书籍的处理进度统计",
            "fields": (
                "total_chapters",        # 总章节数
                "processed_chapters",    # 已处理的章节数
                "total_duration",        # 合成音频总时长
                "progress_percentage",   # 处理进度百分比
            )
        }),

        # 完整音频分组
        ("完整音频", {
            "description": "合并后的完整有声书音频信息",
            "fields": (
                "full_audio_path",       # 完整音频存储路径
                "full_audio_duration",   # 完整音频时长
                "full_audio_size",       # 完整音频文件大小
                "full_audio_format",     # 音频格式（如 mp3）
            )
        }),

        # 错误信息分组
        ("错误信息", {
            "description": "处理过程中的错误记录",
            "fields": (
                "error_message",         # 错误消息
                "error_count",           # 错误发生次数
            )
        }),

        # 文件监听分组
        ("文件监听", {
            "description": "文件夹监听模式的配置",
            "fields": (
                "watch_path",            # 监听目录路径
            )
        }),

        # 时间戳分组
        ("时间戳", {
            "description": "记录的时间信息",
            "fields": (
                "created_at",            # 创建时间
                "updated_at",            # 最后更新时间
                "deleted_at",            # 删除时间（软删除）
            )
        }),
    )

    def status_badge(self, obj):
        """
        生成状态徽章的 HTML 显示

        根据书籍的当前状态返回带有颜色背景的徽章，
        便于在列表页直观地识别每个书籍的处理状态。
        """
        return create_status_badge(
            obj.status,
            obj.get_status_display(),
            BOOK_STATUS_COLORS
        )
    status_badge.short_description = "状态"  # 列标题


# ===========================================
# 章节管理
# ===========================================

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    """
    章节模型的管理界面配置

    功能说明：
    - 列表页显示章节的书籍归属、序号、标题、状态等
    - 支持按状态、创建时间筛选
    - 支持按章节标题、所属书籍搜索
    - 可查看章节的原始文本和分析结果
    """

    list_display = [
        "id",                    # 章节ID
        "book_title",            # 所属书籍标题（自定义列）
        "chapter_index",         # 章节序号
        "title",                 # 章节标题
        "status_badge",          # 状态徽章
        "audio_duration",        # 音频时长
        "created_at",            # 创建时间
    ]

    list_filter = [
        "status",        # 按处理状态筛选
        "created_at",    # 按创建时间筛选
    ]

    search_fields = [
        "title",         # 搜索章节标题
        "book__title",   # 搜索所属书籍标题
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "analysis_result",   # 分析结果（JSON格式，由AI生成）
    ]

    ordering = ["book", "chapter_index"]  # 按书籍分组，再按章节序号排序

    fieldsets = (
        ("基本信息", {
            "fields": (
                "id",
                "book",               # 所属书籍（外键）
                "chapter_index",       # 章节序号
                "title",              # 章节标题
            )
        }),

        ("文本内容", {
            "description": "章节的原始文本和清洗后的文本",
            "fields": (
                "raw_text",           # 从EPUB提取的原始文本
                "cleaned_text",       # 清洗处理后的文本
            )
        }),

        ("分析结果", {
            "description": "DeepSeek AI 分析得出的章节信息",
            "fields": (
                "analysis_result",    # AI 分析结果（JSON格式）
                "characters",         # 识别出的角色列表
            )
        }),

        ("音频信息", {
            "description": "合成后的音频文件信息",
            "fields": (
                "audio_file_path",    # 音频文件存储路径
                "audio_url",          # 音频访问URL
                "audio_duration",     # 音频时长（秒）
                "audio_file_size",    # 音频文件大小
                "audio_format",       # 音频格式（如 mp3）
            )
        }),

        ("处理信息", {
            "description": "处理过程中的消耗和错误信息",
            "fields": (
                "status",
                "error_message",      # 错误消息
                "deepseek_tokens",    # DeepSeek API 消耗的 token 数
                "minimax_characters", # MiniMax API 消耗的字符数
            )
        }),

        ("片段进度", {
            "description": "音频片段的合成进度",
            "fields": (
                "completed_segments", # 已完成的片段数
                "total_segments",    # 总片段数
            )
        }),

        ("时间戳", {
            "fields": (
                "created_at",
                "updated_at",
                "next_chapter_id",    # 下一章节ID（用于顺序播放）
            )
        }),
    )

    def book_title(self, obj):
        """获取章节所属书籍的标题"""
        return obj.book.title if obj.book else "-"
    book_title.short_description = "所属书籍"

    def audio_duration(self, obj):
        """格式化显示音频时长"""
        if obj.audio_duration:
            return f"{obj.audio_duration}秒"
        return "-"
    audio_duration.short_description = "音频时长"

    def status_badge(self, obj):
        """生成章节状态徽章"""
        return create_status_badge(
            obj.status,
            obj.get_status_display(),
            CHAPTER_STATUS_COLORS
        )
    status_badge.short_description = "状态"


# ===========================================
# 音频片段管理
# ===========================================

@admin.register(AudioSegment)
class AudioSegmentAdmin(admin.ModelAdmin):
    """
    音频片段模型的管理界面配置

    功能说明：
    - 管理每个章节的音频合成片段
    - 可以查看文本内容、情感标注、语音参数
    - 追踪每个片段的合成状态和成本
    """

    list_display = [
        "id",
        "chapter_info",       # 所属章节信息（自定义列）
        "segment_index",      # 片段序号
        "text_preview",       # 文本预览（自定义列）
        "status_badge",       # 状态徽章
        "emotion",            # 情感标注
        "voice_id",           # 音色ID
    ]

    list_filter = [
        "status",        # 按处理状态筛选
        "emotion",       # 按情感标注筛选
        "created_at",    # 按创建时间筛选
    ]

    search_fields = [
        "text_content",  # 搜索文本内容
        "voice_id",      # 搜索音色ID
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]

    ordering = ["chapter", "segment_index"]

    fieldsets = (
        ("基本信息", {
            "fields": (
                "id",
                "chapter",             # 所属章节（外键）
                "segment_index",        # 片段在章节中的序号
                "text_content",         # 要合成语音的文本内容
            )
        }),

        ("角色与情感", {
            "description": "AI 分析得出的角色和情感信息",
            "fields": (
                "role",                 # 说话角色名（如"旁白"、"张三"）
                "emotion",              # 情感标注（如"平静"、"激动"）
                "emotion_intensity",    # 情感强度（如"high"、"medium"）
            )
        }),

        ("语音参数", {
            "description": "MiniMax TTS 语音合成的参数配置",
            "fields": (
                "voice_id",             # MiniMax 音色ID
                "speed",                # 语速（normal/fast/slow）
                "pause_after",          # 片段后的停顿时长
            )
        }),

        ("音频信息", {
            "description": "合成后的音频文件信息",
            "fields": (
                "audio_file_path",      # 音频文件存储路径
                "audio_url",            # 音频访问URL
                "audio_duration_ms",    # 音频时长（毫秒）
                "audio_file_size",      # 音频文件大小
            )
        }),

        ("处理状态", {
            "description": "片段的处理状态和错误信息",
            "fields": (
                "status",
                "error_message",       # 错误消息
                "retry_count",         # 重试次数
            )
        }),

        ("API消耗", {
            "description": "API 调用成本统计",
            "fields": (
                "minimax_cost",         # MiniMax API 消耗字符数
                "deepseek_cost",        # DeepSeek API 消耗 token 数
            )
        }),

        ("时间戳", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def chapter_info(self, obj):
        """获取章节的完整信息描述"""
        if obj.chapter:
            title = obj.chapter.book.title if obj.chapter.book else "未知书籍"
            return f"{title[:20]}... - 第{obj.chapter.chapter_index}章"
        return "-"
    chapter_info.short_description = "所属章节"

    def text_preview(self, obj):
        """显示文本内容的前50个字符"""
        if obj.text_content:
            return obj.text_content[:50] + "..." if len(obj.text_content) > 50 else obj.text_content
        return "-"
    text_preview.short_description = "文本预览"

    def status_badge(self, obj):
        """生成片段状态徽章"""
        return create_status_badge(
            obj.status,
            obj.get_status_display(),
            SEGMENT_STATUS_COLORS
        )
    status_badge.short_description = "状态"


# ===========================================
# 发布渠道管理
# ===========================================

@admin.register(PublishChannel)
class PublishChannelAdmin(admin.ModelAdmin):
    """
    发布渠道模型的管理界面配置

    功能说明：
    - 配置和管理不同的发布平台（如喜马拉雅、蜻蜓FM等）
    - 设置OAuth认证信息
    - 追踪发布统计信息
    """

    list_display = [
        "id",
        "name",                # 渠道名称
        "platform_type",       # 平台类型
        "is_enabled",          # 是否启用
        "auto_publish",        # 是否自动发布
        "priority",            # 发布优先级
        "total_published",     # 已发布书籍数
    ]

    list_filter = [
        "is_enabled",    # 按是否启用筛选
        "auto_publish",  # 按是否自动发布筛选
        "platform_type", # 按平台类型筛选
    ]

    search_fields = [
        "name",          # 搜索渠道名称
        "platform_type", # 搜索平台类型
    ]

    ordering = ["-priority", "-total_published"]

    fieldsets = (
        ("基本信息", {
            "fields": (
                "id",
                "name",                # 渠道名称
                "platform_type",       # 平台类型
                "description",         # 渠道描述
            )
        }),

        ("功能配置", {
            "description": "控制渠道的功能开关和行为",
            "fields": (
                "is_enabled",          # 是否启用该渠道
                "auto_publish",        # 是否自动发布到该渠道
                "priority",            # 发布优先级（数字越大越优先）
                "api_config",          # 平台特定的API配置（JSON格式）
            )
        }),

        ("OAuth认证", {
            "description": "第三方平台的OAuth认证信息",
            "fields": (
                "oauth_client_id",             # OAuth客户端ID
                "oauth_access_token",          # 访问令牌
                "oauth_refresh_token",         # 刷新令牌
                "oauth_expires_at",            # 令牌过期时间
            )
        }),

        ("发布设置", {
            "description": "发布时的默认设置",
            "fields": (
                "publish_as_draft",   # 是否发布为草稿
                "category",          # 默认分类
                "tags",              # 默认标签列表
            )
        }),

        ("统计信息", {
            "description": "发布统计和历史",
            "fields": (
                "total_published",    # 总发布书籍数
                "success_count",      # 成功发布次数
                "failure_count",     # 发布失败次数
                "last_published_at", # 最后发布时间
            )
        }),

        ("用户关联", {
            "fields": (
                "user_id",           # 关联的用户ID
            )
        }),
    )


# ===========================================
# 发布记录管理
# ===========================================

@admin.register(PublishRecord)
class PublishRecordAdmin(admin.ModelAdmin):
    """
    发布记录模型的管理界面配置

    功能说明：
    - 追踪每次发布的历史记录
    - 查看发布到各渠道的状态和结果
    - 管理和重试失败的发布任务
    """

    list_display = [
        "id",
        "book_title",          # 书籍标题
        "channel_name",         # 渠道名称
        "status_badge",        # 状态徽章
        "published_chapters",   # 已发布章节数
        "total_chapters",      # 总章节数
        "published_at",         # 发布时间
    ]

    list_filter = [
        "status",       # 按发布状态筛选
        "created_at",   # 按创建时间筛选
    ]

    search_fields = [
        "book__title",    # 搜索书籍标题
        "channel__name",  # 搜索渠道名称
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]

    ordering = ["-created_at"]

    fieldsets = (
        ("基本信息", {
            "fields": (
                "id",
                "book",               # 发布的书籍
                "channel",             # 发布的目标渠道
                "status",              # 发布状态
            )
        }),

        ("外部平台信息", {
            "description": "在目标平台上的专辑和章节信息",
            "fields": (
                "external_album_id",   # 外部平台的专辑ID
                "external_album_url",  # 外部平台的专辑URL
                "external_category_id", # 外部平台的分类ID
            )
        }),

        ("章节发布映射", {
            "description": "本地章节与外部平台章节的映射关系",
            "fields": (
                "chapters_published",  # JSON格式，记录每个章节的发布状态
            )
        }),

        ("发布进度", {
            "description": "发布进度的统计",
            "fields": (
                "total_chapters",      # 要发布的总章节数
                "published_chapters",  # 已成功发布的章节数
                "failed_chapters",     # 发布失败的章节数
            )
        }),

        ("成本统计", {
            "description": "API 调用成本估算",
            "fields": (
                "api_calls",           # 总API调用次数
                "estimated_cost",      # 预估成本（积分/费用）
            )
        }),

        ("结果详情", {
            "description": "发布的详细结果和错误信息",
            "fields": (
                "result_details",      # 发布结果的详细信息（JSON）
                "error_message",       # 错误消息
                "error_code",          # 错误代码
                "retry_count",         # 重试次数
            )
        }),

        ("Celery任务", {
            "description": "关联的后台任务信息",
            "fields": (
                "celery_task_id",      # Celery任务ID
            )
        }),

        ("时间戳", {
            "fields": (
                "created_at",          # 创建时间
                "updated_at",          # 更新时间
                "published_at",        # 成功发布时间
            )
        }),
    )

    def book_title(self, obj):
        """获取书籍标题"""
        return obj.book.title if obj.book else "-"
    book_title.short_description = "书籍"

    def channel_name(self, obj):
        """获取渠道名称"""
        return obj.channel.name if obj.channel else "-"
    channel_name.short_description = "渠道"

    def status_badge(self, obj):
        """生成发布状态徽章"""
        return create_status_badge(
            obj.status,
            obj.get_status_display(),
            PUBLISH_STATUS_COLORS
        )
    status_badge.short_description = "状态"


# ===========================================
# 音色配置管理
# ===========================================

@admin.register(VoiceProfile)
class VoiceProfileAdmin(admin.ModelAdmin):
    """
    音色配置模型的管理界面配置

    功能说明：
    - 管理不同角色的语音参数预设
    - 配置 MiniMax TTS 的音色和参数
    - 支持系统预设和用户自定义两种类型
    """

    list_display = [
        "id",
        "name",                    # 音色名称
        "role_type",               # 角色类型
        "minimax_voice_id",        # MiniMax音色ID
        "minimax_model",           # MiniMax模型
        "speed",                   # 语速
        "is_active",               # 是否启用
    ]

    list_filter = [
        "is_active",         # 按是否启用筛选
        "role_type",         # 按角色类型筛选
        "is_system_preset",  # 按是否系统预设筛选
    ]

    search_fields = [
        "name",             # 搜索音色名称
        "minimax_voice_id", # 搜索MiniMax音色ID
    ]

    ordering = ["-is_system_preset", "sort_order", "name"]

    fieldsets = (
        ("基本信息", {
            "fields": (
                "id",
                "name",                # 音色名称
                "description",         # 音色描述
                "role_type",           # 角色类型（旁白/男主角/女主角等）
            )
        }),

        ("MiniMax配置", {
            "description": "MiniMax TTS 语音合成服务的配置",
            "fields": (
                "minimax_voice_id",    # MiniMax音色ID
                "minimax_model",       # MiniMax模型名称
            )
        }),

        ("语音参数", {
            "description": "语音合成时的参数设置",
            "fields": (
                "speed",               # 语速倍率（1.0为正常速度）
                "pitch",              # 音调调整
                "volume",              # 音量调整
            )
        }),

        ("关联信息", {
            "description": "音色与书籍/角色的关联",
            "fields": (
                "book",                # 所属书籍（为空表示全局预设）
                "character_names",     # 关联的角色名称列表
                "emotion_params",      # 情感参数配置
            )
        }),

        ("管理设置", {
            "description": "音色的管理和排序设置",
            "fields": (
                "is_system_preset",   # 是否为系统预设（系统预设不可删除）
                "is_active",           # 是否启用
                "sort_order",          # 排序顺序
                "created_by",          # 创建者
            )
        }),

        ("使用统计", {
            "fields": (
                "usage_count",        # 使用次数统计
            )
        }),
    )


# ===========================================
# TTS任务管理
# ===========================================

@admin.register(TTSTask)
class TTSTaskAdmin(admin.ModelAdmin):
    """
    TTS任务模型的管理界面配置

    功能说明：
    - 监控文本转语音任务的执行状态
    - 查看任务的处理进度和消耗统计
    - 管理失败的任务和错误信息
    """

    list_display = [
        "id",
        "book_title",          # 书籍标题
        "task_type",           # 任务类型
        "status_badge",        # 状态徽章
        "progress_display",    # 进度百分比（自定义列）
        "created_at",          # 创建时间
        "completed_at",        # 完成时间
    ]

    list_filter = [
        "status",       # 按任务状态筛选
        "task_type",    # 按任务类型筛选
        "created_at",   # 按创建时间筛选
    ]

    search_fields = [
        "book__title",        # 搜索书籍标题
        "celery_task_id",     # 搜索Celery任务ID
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "progress_percentage",
    ]

    ordering = ["-created_at"]

    fieldsets = (
        ("基本信息", {
            "fields": (
                "id",
                "book",                # 关联的书籍
                "task_type",           # 任务类型（full/incremental等）
                "status",              # 任务状态
            )
        }),

        ("Celery任务", {
            "description": "Celery 分布式任务队列的信息",
            "fields": (
                "celery_task_id",      # Celery 任务ID
                "parent_task_id",      # 父任务ID（用于任务链）
            )
        }),

        ("处理进度", {
            "description": "任务的处理进度统计",
            "fields": (
                "total_segments",              # 总片段数
                "completed_segments",           # 已完成片段数
                "failed_segments",              # 失败片段数
                "progress_percentage",          # 进度百分比（自动计算）
                "estimated_remaining_seconds",  # 预估剩余时间（秒）
            )
        }),

        ("API成本统计", {
            "description": "各API服务的调用成本统计",
            "fields": (
                "deepseek_total_tokens",       # DeepSeek 总消耗Token
                "minimax_total_characters",    # MiniMax 总消耗字符
                "total_cost_estimate",          # 总预估成本
                "deepseek_calls",              # DeepSeek 调用次数
                "minimax_calls",               # MiniMax 调用次数
            )
        }),

        ("性能指标", {
            "description": "API 调用的性能统计数据",
            "fields": (
                "deepseek_avg_latency_ms",     # DeepSeek 平均延迟（毫秒）
                "minimax_avg_latency_ms",      # MiniMax 平均延迟（毫秒）
                "total_audio_duration_ms",     # 总音频时长（毫秒）
                "output_format",               # 输出音频格式
            )
        }),

        ("错误信息", {
            "description": "任务执行中的错误记录",
            "fields": (
                "error_message",       # 错误消息
                "error_traceback",     # 错误堆栈信息
            )
        }),

        ("执行信息", {
            "description": "任务执行环境的信息",
            "fields": (
                "worker_name",         # 执行的Worker名称
            )
        }),

        ("时间戳", {
            "fields": (
                "created_at",          # 任务创建时间
                "updated_at",          # 最后更新时间
                "started_at",          # 任务开始时间
                "completed_at",        # 任务完成时间
            )
        }),
    )

    def book_title(self, obj):
        """获取书籍标题"""
        return obj.book.title if obj.book else "-"
    book_title.short_description = "书籍"

    def status_badge(self, obj):
        """生成任务状态徽章"""
        return create_status_badge(
            obj.status,
            obj.get_status_display(),
            TASK_STATUS_COLORS
        )
    status_badge.short_description = "状态"

    def progress_display(self, obj):
        """格式化显示进度百分比"""
        return f"{obj.progress_percentage}%"
    progress_display.short_description = "处理进度"


# ===========================================
# 角色库管理
# ===========================================

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    """
    角色库模型的管理界面配置

    功能说明：
    - 管理从 DeepSeek 分析出的角色
    - 配置音色分配
    - 审核角色信息
    """

    form = CharacterForm

    list_display = [
        "id",
        "name",
        "book_title",
        "gender_badge",
        "role_type",
        "voice_profile_name",
        "status_badge",
        "dialogue_count",
        "usage_count",
    ]

    list_filter = [
        "status",
        "gender",
        "role_type",
        "created_at",
    ]

    search_fields = [
        "name",
        "book__title",
        "description",
        "voice_description",
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "usage_count",
    ]

    ordering = ["book", "sort_order", "name"]

    fieldsets = (
        ("基本信息", {
            "fields": (
                "id",
                "book",
                "name",
                "aliases",
                "gender",
                "description",
            )
        }),

        ("声音特征", {
            "description": "角色的声音特征描述",
            "fields": (
                "voice_description",
                "role_type",
                "emotions",
            )
        }),

        ("音色分配", {
            "description": "音色配置",
            "fields": (
                "voice_profile",
                "custom_voice_id",
                "custom_speed",
                "custom_pitch",
                "custom_volume",
            )
        }),

        ("统计信息", {
            "fields": (
                "dialogue_count",
                "usage_count",
                "source",
            )
        }),

        ("审核状态", {
            "fields": (
                "status",
                "sort_order",
            )
        }),

        ("时间戳", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    actions = ["approve_characters", "reject_characters"]

    def book_title(self, obj):
        """获取书籍标题"""
        return obj.book.title if obj.book else "-"
    book_title.short_description = "所属书籍"

    def voice_profile_name(self, obj):
        """获取音色名称"""
        return obj.voice_profile.name if obj.voice_profile else "-"
    voice_profile_name.short_description = "音色"

    def gender_badge(self, obj):
        """生成性别徽章"""
        colors = {"male": "#0d6efd", "female": "#dc3545", "unknown": "#6c757d"}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.gender, "#6c757d"),
            obj.get_gender_display()
        )
    gender_badge.short_description = "性别"

    def status_badge(self, obj):
        """生成状态徽章"""
        colors = {
            "pending": "#ffc107",
            "approved": "#198754",
            "rejected": "#dc3545",
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, "#6c757d"),
            obj.get_status_display()
        )
    status_badge.short_description = "状态"

    @admin.action(description="审核通过选中角色")
    def approve_characters(self, request, queryset):
        count = queryset.update(status=CharacterStatus.APPROVED)
        self.message_user(request, f"已审核通过 {count} 个角色")

    @admin.action(description="审核拒绝选中角色")
    def reject_characters(self, request, queryset):
        count = queryset.update(status=CharacterStatus.REJECTED)
        self.message_user(request, f"已拒绝 {count} 个角色")


# ===========================================
# 音效库管理
# ===========================================

@admin.register(SoundEffect)
class SoundEffectAdmin(admin.ModelAdmin):
    """
    音效库模型的管理界面配置

    功能说明：
    - 管理音效资源
    - 配置音效分类和标签
    - 追踪使用统计
    """

    form = SoundEffectForm

    list_display = [
        "id",
        "name",
        "type_badge",
        "layer",
        "source",
        "status",
        "duration_display",
        "usage_count",
        "is_favorite",
    ]

    list_filter = [
        "effect_type",
        "layer",
        "source",
        "status",
        "priority",
        "is_verified",
        "is_favorite",
    ]

    search_fields = [
        "name",
        "description",
        "chinese_description",
        "tags",
        "chinese_tags",
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "usage_count",
        "verified_at",
    ]

    ordering = ["-usage_count", "-priority", "name"]

    fieldsets = (
        ("基本信息", {
            "fields": (
                "id",
                "name",
                "description",
                "chinese_description",
            )
        }),

        ("分类信息", {
            "fields": (
                "effect_type",
                "layer",
                "priority",
            )
        }),

        ("标签系统", {
            "fields": (
                "tags",
                "chinese_tags",
                "semantic_keywords",
            )
        }),

        ("来源信息", {
            "fields": (
                "source",
                "source_id",
                "source_url",
                "license_type",
            )
        }),

        ("音频属性", {
            "fields": (
                "duration_ms",
                "file_format",
                "file_size",
                "sample_rate",
            )
        }),

        ("存储信息", {
            "fields": (
                "local_path",
                "minio_path",
                "minio_url",
            )
        }),

        ("状态管理", {
            "fields": (
                "status",
                "is_favorite",
                "is_verified",
                "verified_at",
            )
        }),

        ("推荐配置", {
            "fields": (
                "suitable_scenes",
                "recommended_volume_min",
                "recommended_volume_max",
                "recommended_fade_in_ms",
                "recommended_fade_out_ms",
            )
        }),

        ("统计信息", {
            "fields": (
                "usage_count",
                "last_used_at",
            )
        }),

        ("时间戳", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    actions = ["verify_sound_effects", "toggle_favorites"]

    def duration_display(self, obj):
        """格式化显示时长"""
        if obj.duration_ms:
            seconds = obj.duration_ms / 1000
            return f"{seconds:.1f}s"
        return "-"
    duration_display.short_description = "时长"

    def type_badge(self, obj):
        """生成类型徽章"""
        colors = {
            "environment": "#17a2b8",
            "action": "#fd7e14",
            "transition": "#6f42c1",
            "nature": "#28a745",
            "ambient": "#20c997",
            "weather": "#6610f2",
            "urban": "#6c757d",
            "fantasy": "#e83e8c",
            "scifi": "#007bff",
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.effect_type, "#6c757d"),
            obj.get_effect_type_display()
        )
    type_badge.short_description = "类型"

    @admin.action(description="审核通过选中音效")
    def verify_sound_effects(self, request, queryset):
        count = queryset.count()
        for se in queryset:
            se.verify()
        self.message_user(request, f"已审核通过 {count} 个音效")

    @admin.action(description="切换收藏状态")
    def toggle_favorites(self, request, queryset):
        for se in queryset:
            se.toggle_favorite()
        self.message_user(request, f"已更新 {queryset.count()} 个音效的收藏状态")


@admin.register(SoundEffectUsage)
class SoundEffectUsageAdmin(admin.ModelAdmin):
    """音效使用记录管理"""

    form = SoundEffectUsageForm

    list_display = [
        "id",
        "sound_effect_name",
        "book_id",
        "chapter_id",
        "trigger_at_ms",
        "volume",
        "match_score",
        "created_at",
    ]

    list_filter = [
        "created_at",
    ]

    search_fields = [
        "sound_effect__name",
        "matched_from_query",
    ]

    readonly_fields = [
        "id",
        "created_at",
    ]

    ordering = ["-created_at"]

    def sound_effect_name(self, obj):
        return obj.sound_effect.name if obj.sound_effect else "-"
    sound_effect_name.short_description = "音效"


@admin.register(SoundEffectCollection)
class SoundEffectCollectionAdmin(admin.ModelAdmin):
    """音效收藏集管理"""

    form = SoundEffectCollectionForm

    list_display = [
        "id",
        "name",
        "scene_type",
        "sound_count",
        "is_public",
        "is_default",
        "created_at",
    ]

    list_filter = [
        "scene_type",
        "is_public",
        "is_default",
    ]

    search_fields = [
        "name",
        "description",
    ]

    ordering = ["-is_default", "-sound_count", "name"]


@admin.register(SoundEffectCollectionItem)
class SoundEffectCollectionItemAdmin(admin.ModelAdmin):
    """音效收藏集项目管理"""

    form = SoundEffectCollectionItemForm

    list_display = [
        "id",
        "collection_name",
        "sound_effect_name",
        "custom_volume",
        "sort_order",
        "added_at",
    ]

    list_filter = [
        "added_at",
    ]

    search_fields = [
        "collection__name",
        "sound_effect__name",
    ]

    ordering = ["collection", "sort_order"]

    def collection_name(self, obj):
        return obj.collection.name if obj.collection else "-"
    collection_name.short_description = "收藏集"

    def sound_effect_name(self, obj):
        return obj.sound_effect.name if obj.sound_effect else "-"
    sound_effect_name.short_description = "音效"
