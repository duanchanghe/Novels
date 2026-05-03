"""
发布记录数据模型
"""
from django.db import models
from django.utils import timezone

from .book import Book
from .channel import PublishChannel


class PublishStatus(models.TextChoices):
    """发布状态枚举"""
    PENDING = "pending", "等待发布"
    PREPARING = "preparing", "准备中"
    UPLOADING = "uploading", "上传中"
    DONE = "done", "发布成功"
    FAILED = "failed", "发布失败"
    PARTIALLY_DONE = "partially_done", "部分成功"


class PublishRecord(models.Model):
    """发布记录数据模型"""

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="publish_records",
        verbose_name="所属书籍"
    )
    channel = models.ForeignKey(
        PublishChannel,
        on_delete=models.CASCADE,
        related_name="publish_records",
        verbose_name="发布渠道"
    )

    external_album_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="外部专辑ID")
    external_album_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="外部专辑URL")
    external_category_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="外部分类ID")

    status = models.CharField(
        max_length=20,
        choices=PublishStatus.choices,
        default=PublishStatus.PENDING,
        verbose_name="发布状态"
    )

    chapters_published = models.JSONField(blank=True, null=True, verbose_name="章节发布映射")

    total_chapters = models.IntegerField(default=0, verbose_name="总章节数")
    published_chapters = models.IntegerField(default=0, verbose_name="已发布章节数")
    failed_chapters = models.IntegerField(default=0, verbose_name="失败章节数")

    api_calls = models.IntegerField(default=0, verbose_name="API调用次数")
    estimated_cost = models.IntegerField(default=0, verbose_name="预估成本")

    result_details = models.JSONField(blank=True, null=True, verbose_name="发布结果详情")

    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    error_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="错误代码")
    retry_count = models.IntegerField(default=0, verbose_name="重试次数")

    celery_task_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="Celery任务ID")

    published_at = models.DateTimeField(blank=True, null=True, verbose_name="发布时间")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "publish_records"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["book", "channel"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["book", "channel"], name="uq_book_channel")
        ]

    def __str__(self):
        return f"{self.book.title} -> {self.channel.name}"

    @property
    def progress_percentage(self):
        """计算发布进度百分比"""
        if self.total_chapters == 0:
            return 0.0
        return round((self.published_chapters / self.total_chapters) * 100, 2)

    @property
    def is_complete(self):
        """是否完成发布"""
        return self.status in [PublishStatus.DONE, PublishStatus.PARTIALLY_DONE]

    @property
    def is_success(self):
        """是否发布成功"""
        return self.status == PublishStatus.DONE
