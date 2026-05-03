"""
音频片段数据模型
"""
from django.db import models
from django.utils import timezone

from .chapter import Chapter


class SegmentStatus(models.TextChoices):
    """片段处理状态枚举"""
    PENDING = "pending", "等待处理"
    SYNTHESIZING = "synthesizing", "正在合成"
    SUCCESS = "success", "成功"
    FAILED = "failed", "失败"


class AudioSegment(models.Model):
    """音频片段数据模型"""

    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="segments",
        verbose_name="所属章节"
    )
    segment_index = models.IntegerField(verbose_name="片段序号")

    text_content = models.TextField(verbose_name="文本内容")
    raw_text = models.TextField(blank=True, null=True, verbose_name="原始文本")

    role = models.CharField(max_length=100, blank=True, null=True, verbose_name="角色名")
    emotion = models.CharField(max_length=50, blank=True, null=True, verbose_name="情感标注")
    emotion_intensity = models.CharField(max_length=20, blank=True, null=True, verbose_name="情感强度")

    speed = models.CharField(max_length=20, default="normal", verbose_name="语速")
    pause_after = models.CharField(max_length=20, blank=True, null=True, verbose_name="段后停顿")
    voice_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="音色ID")

    status = models.CharField(
        max_length=20,
        choices=SegmentStatus.choices,
        default=SegmentStatus.PENDING,
        verbose_name="处理状态"
    )

    minimax_request_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="MiniMax请求ID")
    minimax_cost = models.IntegerField(default=0, verbose_name="MiniMax消耗字符")
    deepseek_cost = models.IntegerField(default=0, verbose_name="DeepSeek消耗Token")

    audio_file_path = models.CharField(max_length=1000, blank=True, null=True, verbose_name="音频文件路径")
    audio_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="音频URL")
    audio_duration_ms = models.IntegerField(blank=True, null=True, verbose_name="音频时长")
    audio_file_size = models.BigIntegerField(blank=True, null=True, verbose_name="文件大小")

    retry_count = models.IntegerField(default=0, verbose_name="重试次数")
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")

    extra_params = models.JSONField(blank=True, null=True, verbose_name="额外参数")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "audio_segments"
        ordering = ["segment_index"]
        indexes = [
            models.Index(fields=["chapter", "segment_index"]),
            models.Index(fields=["chapter", "status"]),
            models.Index(fields=["status"], name="ix_segments_status"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["chapter", "segment_index"], name="uq_chapter_segment")
        ]

    def __str__(self):
        return f"片段{self.segment_index} ({self.get_status_display()})"

    @property
    def audio_duration_seconds(self):
        """获取音频时长（秒）"""
        if self.audio_duration_ms:
            return self.audio_duration_ms / 1000
        return None

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "chapter_id": self.chapter_id,
            "segment_index": self.segment_index,
            "text_content": self.text_content,
            "raw_text": self.raw_text,
            "role": self.role,
            "emotion": self.emotion,
            "emotion_intensity": self.emotion_intensity,
            "speed": self.speed,
            "pause_after": self.pause_after,
            "voice_id": self.voice_id,
            "status": self.status,
            "status_display": self.get_status_display(),
            "audio_file_path": self.audio_file_path,
            "audio_url": self.audio_url,
            "audio_duration_ms": self.audio_duration_ms,
            "audio_duration_seconds": self.audio_duration_seconds,
            "audio_file_size": self.audio_file_size,
            "minimax_cost": self.minimax_cost,
            "deepseek_cost": self.deepseek_cost,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
