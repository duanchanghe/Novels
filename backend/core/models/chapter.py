"""
章节数据模型
"""
from django.db import models
from django.utils import timezone

from .book import Book


class ChapterStatus(models.TextChoices):
    """章节处理状态枚举"""
    PENDING = "pending", "等待处理"
    ANALYZING = "analyzing", "正在分析"
    ANALYZED = "analyzed", "已分析"
    SYNTHESIZING = "synthesizing", "正在合成"
    AWAITING_CONFIRM = "awaiting_confirm", "等待确认"
    DONE = "done", "完成"
    FAILED = "failed", "失败"


class Chapter(models.Model):
    """章节数据模型"""

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="chapters",
        verbose_name="所属书籍"
    )
    chapter_index = models.IntegerField(verbose_name="章节序号")
    title = models.CharField(max_length=500, blank=True, null=True, verbose_name="章节标题")

    raw_text = models.TextField(blank=True, null=True, verbose_name="原始文本")
    cleaned_text = models.TextField(blank=True, null=True, verbose_name="清洗后文本")

    analysis_result = models.JSONField(blank=True, null=True, verbose_name="分析结果JSON")
    characters = models.JSONField(blank=True, null=True, verbose_name="角色列表")

    status = models.CharField(
        max_length=20,
        choices=ChapterStatus.choices,
        default=ChapterStatus.PENDING,
        verbose_name="处理状态"
    )

    next_chapter_id = models.IntegerField(blank=True, null=True, verbose_name="下一章ID")

    audio_file_path = models.CharField(max_length=1000, blank=True, null=True, verbose_name="音频文件路径")
    audio_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="音频URL")
    audio_duration = models.IntegerField(blank=True, null=True, verbose_name="音频时长")
    audio_file_size = models.BigIntegerField(blank=True, null=True, verbose_name="音频文件大小")
    audio_format = models.CharField(max_length=20, default="mp3", verbose_name="音频格式")

    total_segments = models.IntegerField(default=0, verbose_name="总片段数")
    completed_segments = models.IntegerField(default=0, verbose_name="已完成片段数")
    failed_segments = models.IntegerField(default=0, verbose_name="失败片段数")

    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")

    deepseek_tokens = models.IntegerField(default=0, verbose_name="DeepSeek消耗Token")
    minimax_characters = models.IntegerField(default=0, verbose_name="MiniMax消耗字符")
    estimated_cost = models.IntegerField(default=0, verbose_name="预估成本")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "chapters"
        ordering = ["chapter_index"]
        indexes = [
            models.Index(fields=["book", "chapter_index"]),
            models.Index(fields=["book", "status"]),
            models.Index(fields=["status"], name="ix_chapters_status"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["book", "chapter_index"], name="uq_book_chapter")
        ]

    def __str__(self):
        return f"{self.book.title} - 第{self.chapter_index}章 {self.title}"

    @property
    def progress_percentage(self):
        """计算处理进度百分比"""
        if self.total_segments == 0:
            return 0.0
        return round((self.completed_segments / self.total_segments) * 100, 2)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "book_id": self.book_id,
            "chapter_index": self.chapter_index,
            "title": self.title,
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "analysis_result": self.analysis_result,
            "characters": self.characters,
            "status": self.status,
            "status_display": self.get_status_display(),
            "audio_file_path": self.audio_file_path,
            "audio_url": self.audio_url,
            "audio_duration": self.audio_duration,
            "audio_file_size": self.audio_file_size,
            "audio_format": self.audio_format,
            "total_segments": self.total_segments,
            "completed_segments": self.completed_segments,
            "failed_segments": self.failed_segments,
            "progress_percentage": self.progress_percentage,
            "error_message": self.error_message,
            "deepseek_tokens": self.deepseek_tokens,
            "minimax_characters": self.minimax_characters,
            "estimated_cost": self.estimated_cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
