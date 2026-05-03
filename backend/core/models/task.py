"""
TTS 任务数据模型
"""
from django.db import models
from django.utils import timezone

from .book import Book


class TaskStatus(models.TextChoices):
    """任务状态枚举"""
    PENDING = "pending", "等待执行"
    ANALYZING = "analyzing", "正在分析"
    SYNTHESIZING = "synthesizing", "正在合成"
    POST_PROCESSING = "post_processing", "正在后处理"
    PUBLISHING = "publishing", "正在发布"
    DONE = "done", "完成"
    FAILED = "failed", "失败"
    CANCELLED = "cancelled", "已取消"


class TTSTask(models.Model):
    """TTS 任务数据模型"""

    book = models.OneToOneField(
        Book,
        on_delete=models.CASCADE,
        related_name="tts_task",
        verbose_name="所属书籍"
    )

    celery_task_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="Celery任务ID")
    parent_task_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="父任务ID")

    task_type = models.CharField(max_length=50, default="full", verbose_name="任务类型")

    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        verbose_name="处理状态"
    )

    total_segments = models.IntegerField(default=0, verbose_name="总片段数")
    completed_segments = models.IntegerField(default=0, verbose_name="已完成片段数")
    failed_segments = models.IntegerField(default=0, verbose_name="失败片段数")

    deepseek_total_tokens = models.IntegerField(default=0, verbose_name="DeepSeek总消耗Token")
    minimax_total_characters = models.IntegerField(default=0, verbose_name="MiniMax总消耗字符")
    total_cost_estimate = models.IntegerField(default=0, verbose_name="总预估成本")

    deepseek_calls = models.IntegerField(default=0, verbose_name="DeepSeek调用次数")
    deepseek_avg_latency_ms = models.IntegerField(default=0, verbose_name="DeepSeek平均延迟")

    minimax_calls = models.IntegerField(default=0, verbose_name="MiniMax调用次数")
    minimax_avg_latency_ms = models.IntegerField(default=0, verbose_name="MiniMax平均延迟")

    total_audio_duration_ms = models.BigIntegerField(default=0, verbose_name="总音频时长")
    output_format = models.CharField(max_length=20, default="mp3", verbose_name="输出格式")

    worker_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="执行Worker")

    started_at = models.DateTimeField(blank=True, null=True, verbose_name="任务开始时间")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="任务完成时间")

    estimated_remaining_seconds = models.IntegerField(blank=True, null=True, verbose_name="预估剩余时间")

    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    error_traceback = models.TextField(blank=True, null=True, verbose_name="错误堆栈")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "tts_tasks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"任务 {self.id} - {self.book.title}"

    @property
    def progress_percentage(self):
        """计算处理进度百分比"""
        if self.total_segments == 0:
            return 0.0
        return round((self.completed_segments / self.total_segments) * 100, 2)

    @property
    def duration_minutes(self):
        """获取总音频时长（分钟）"""
        if self.total_audio_duration_ms:
            return self.total_audio_duration_ms / 60000
        return None

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "book_id": self.book_id,
            "celery_task_id": self.celery_task_id,
            "parent_task_id": self.parent_task_id,
            "task_type": self.task_type,
            "status": self.status,
            "status_display": self.get_status_display(),
            "total_segments": self.total_segments,
            "completed_segments": self.completed_segments,
            "failed_segments": self.failed_segments,
            "progress_percentage": self.progress_percentage,
            "deepseek_total_tokens": self.deepseek_total_tokens,
            "minimax_total_characters": self.minimax_total_characters,
            "total_cost_estimate": self.total_cost_estimate,
            "deepseek_calls": self.deepseek_calls,
            "deepseek_avg_latency_ms": self.deepseek_avg_latency_ms,
            "minimax_calls": self.minimax_calls,
            "minimax_avg_latency_ms": self.minimax_avg_latency_ms,
            "total_audio_duration_ms": self.total_audio_duration_ms,
            "duration_minutes": self.duration_minutes,
            "output_format": self.output_format,
            "worker_name": self.worker_name,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "error_traceback": self.error_traceback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
