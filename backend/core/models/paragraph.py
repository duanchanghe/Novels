# ===========================================
# Models - Paragraph
# ===========================================

"""
段落数据模型

用于存储章节的段落信息，每个段落包含文本类型、说话人、情感等。
"""

from django.db import models
from .chapter import Chapter


class ParagraphType(models.TextChoices):
    """段落类型"""
    NARRATION = "narration", "旁白"
    DIALOGUE = "dialogue", "对话"
    MIXED = "mixed", "混合"


class EmotionType(models.TextChoices):
    """情感类型"""
    CALM = "calm", "平静"
    HAPPY = "happy", "高兴"
    SAD = "sad", "悲伤"
    ANGRY = "angry", "愤怒"
    NERVOUS = "nervous", "紧张"
    SURPRISED = "surprised", "惊讶"
    GENTLE = "gentle", "温柔"
    SERIOUS = "serious", "严肃"
    COLD = "cold", "冷漠"
    SARCASTIC = "sarcastic", "嘲讽"


class EmotionIntensity(models.TextChoices):
    """情感强度"""
    WEAK = "weak", "弱"
    MEDIUM = "medium", "中"
    STRONG = "strong", "强"


class Paragraph(models.Model):
    """
    段落模型

    存储章节的每个段落，包含文本、类型、说话人、情感等信息。
    """

    # 关联信息
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="paragraphs",
        verbose_name="所属章节"
    )

    # 位置信息
    paragraph_index = models.IntegerField(verbose_name="段落序号")

    # 内容信息
    text = models.TextField(verbose_name="段落文本")
    paragraph_type = models.CharField(
        max_length=20,
        choices=ParagraphType.choices,
        default=ParagraphType.NARRATION,
        verbose_name="段落类型"
    )

    # 说话人信息
    speaker = models.CharField(max_length=100, blank=True, verbose_name="说话人")
    is_narrator = models.BooleanField(default=True, verbose_name="是否旁白")

    # 情感信息（跟着对白，不是角色）
    emotion = models.CharField(
        max_length=20,
        choices=EmotionType.choices,
        blank=True,
        null=True,
        verbose_name="情感"
    )
    emotion_intensity = models.CharField(
        max_length=20,
        choices=EmotionIntensity.choices,
        blank=True,
        null=True,
        verbose_name="情感强度"
    )

    # 多音字修正
    polyphone_fixes = models.JSONField(default=list, blank=True, verbose_name="多音字修正")

    # 特殊标记
    special_markers = models.JSONField(default=list, blank=True, verbose_name="特殊标记")
    is_ancient_text = models.BooleanField(default=False, verbose_name="古文")
    is_poetry = models.BooleanField(default=False, verbose_name="诗词")
    is_inner_thought = models.BooleanField(default=False, verbose_name="内心独白")
    is_system_prompt = models.BooleanField(default=False, verbose_name="系统提示")

    # 元数据
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "paragraphs"
        verbose_name = "段落"
        verbose_name_plural = "段落列表"
        ordering = ["chapter", "paragraph_index"]
        indexes = [
            models.Index(fields=["chapter", "paragraph_index"]),
            models.Index(fields=["paragraph_type"]),
            models.Index(fields=["emotion"]),
            models.Index(fields=["speaker"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["chapter", "paragraph_index"],
                name="uq_chapter_paragraph"
            )
        ]

    def __str__(self):
        speaker = self.speaker or "旁白"
        text_preview = self.text[:30] if self.text else ""
        return f"第{self.paragraph_index}段 [{speaker}]: {text_preview}..."

    @property
    def emotion_with_intensity(self):
        """获取带强度的情感描述"""
        if self.emotion and self.emotion_intensity:
            return f"{self.get_emotion_display()}_{self.get_emotion_intensity_display()}"
        return self.get_emotion_display() if self.emotion else ""

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "chapter_id": self.chapter_id,
            "paragraph_index": self.paragraph_index,
            "text": self.text,
            "type": self.paragraph_type,
            "type_display": self.get_paragraph_type_display(),
            "speaker": self.speaker,
            "is_narrator": self.is_narrator,
            "emotion": self.emotion,
            "emotion_display": self.get_emotion_display(),
            "emotion_intensity": self.emotion_intensity,
            "emotion_with_intensity": self.emotion_with_intensity,
            "polyphone_fixes": self.polyphone_fixes or [],
            "special_markers": self.special_markers or [],
            "is_ancient_text": self.is_ancient_text,
            "is_poetry": self.is_poetry,
            "is_inner_thought": self.is_inner_thought,
            "is_system_prompt": self.is_system_prompt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
