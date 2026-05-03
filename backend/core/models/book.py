"""
书籍数据模型
"""
import uuid
from django.db import models
from django.utils import timezone


class BookStatus(models.TextChoices):
    """书籍处理状态枚举"""
    PENDING = "pending", "等待处理"
    ANALYZING = "analyzing", "正在分析"
    SYNTHESIZING = "synthesizing", "正在合成"
    POST_PROCESSING = "post_processing", "正在后处理"
    PUBLISHING = "publishing", "正在发布"
    DONE = "done", "完成"
    FAILED = "failed", "失败"


class SourceType(models.TextChoices):
    """书籍来源类型枚举"""
    MANUAL = "manual", "手动上传"
    WATCH = "watch", "文件夹监听"


class GenerationMode(models.TextChoices):
    """有声书生成模式枚举"""
    AUTO = "auto", "自动模式"
    MANUAL = "manual", "手动模式"


class Book(models.Model):
    """书籍数据模型"""

    title = models.CharField(max_length=500, verbose_name="书名")
    author = models.CharField(max_length=255, blank=True, null=True, verbose_name="作者")
    description = models.TextField(blank=True, null=True, verbose_name="书籍简介")
    language = models.CharField(max_length=50, default="zh-CN", verbose_name="语言")

    cover_image_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="封面图URL")
    cover_image_path = models.CharField(max_length=500, blank=True, null=True, verbose_name="封面图存储路径")

    file_name = models.CharField(max_length=500, verbose_name="原始文件名")
    file_size = models.BigIntegerField(blank=True, null=True, verbose_name="文件大小")
    file_hash = models.CharField(max_length=64, blank=True, null=True, verbose_name="文件MD5哈希")
    file_path = models.CharField(max_length=1000, blank=True, null=True, verbose_name="MinIO存储路径")

    status = models.CharField(
        max_length=20,
        choices=BookStatus.choices,
        default=BookStatus.PENDING,
        verbose_name="处理状态"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
        verbose_name="来源类型"
    )

    total_chapters = models.IntegerField(default=0, verbose_name="总章节数")
    processed_chapters = models.IntegerField(default=0, verbose_name="已处理章节数")
    total_duration = models.BigIntegerField(default=0, verbose_name="总音频时长")

    full_audio_path = models.CharField(max_length=1000, blank=True, null=True, verbose_name="完整有声书路径")
    full_audio_duration = models.IntegerField(blank=True, null=True, verbose_name="完整有声书时长")
    full_audio_size = models.BigIntegerField(blank=True, null=True, verbose_name="完整有声书大小")
    full_audio_format = models.CharField(max_length=20, default="m4b", verbose_name="完整有声书格式")

    generation_mode = models.CharField(
        max_length=20,
        choices=GenerationMode.choices,
        default=GenerationMode.AUTO,
        verbose_name="生成模式"
    )

    auto_publish_enabled = models.BooleanField(default=False, verbose_name="启用自动发布")
    watch_path = models.CharField(max_length=500, blank=True, null=True, verbose_name="监听路径")

    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    error_count = models.IntegerField(default=0, verbose_name="错误重试次数")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    deleted_at = models.DateTimeField(blank=True, null=True, verbose_name="软删除时间")

    class Meta:
        db_table = "books"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["source_type", "status"]),
            models.Index(fields=["deleted_at", "status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def progress_percentage(self):
        """计算处理进度百分比"""
        if self.total_chapters == 0:
            return 0.0
        return round((self.processed_chapters / self.total_chapters) * 100, 2)

    def soft_delete(self):
        """软删除"""
        self.deleted_at = timezone.now()
        self.save()

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "description": self.description,
            "language": self.language,
            "cover_image_url": self.cover_image_url,
            "cover_image_path": self.cover_image_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "file_path": self.file_path,
            "status": self.status,
            "status_display": self.get_status_display(),
            "source_type": self.source_type,
            "source_type_display": self.get_source_type_display(),
            "total_chapters": self.total_chapters,
            "processed_chapters": self.processed_chapters,
            "total_duration": self.total_duration,
            "progress_percentage": self.progress_percentage,
            "full_audio_path": self.full_audio_path,
            "full_audio_duration": self.full_audio_duration,
            "full_audio_size": self.full_audio_size,
            "full_audio_format": self.full_audio_format,
            "generation_mode": self.generation_mode,
            "auto_publish_enabled": self.auto_publish_enabled,
            "watch_path": self.watch_path,
            "error_message": self.error_message,
            "error_count": self.error_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
