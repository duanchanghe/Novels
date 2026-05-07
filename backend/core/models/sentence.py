# ===========================================
# Models - Sentence (句子级分析)
# ===========================================

"""
句子数据模型

用于存储章节的句子级分析结果，每个句子包含文本类型、说话人、情感等。
这是对传统"段落级"分析的升级，确保旁白和对话严格分离。

主要改进：
- 句子级拆分：每个句子独立存储
- 严格类型：dialogue（对话）/ narration（旁白）
- 说话人明确：对话必须有具体角色名，旁白固定为"旁白"
"""

from django.db import models
from .chapter import Chapter


class SentenceType(models.TextChoices):
    """句子类型"""
    NARRATION = "narration", "旁白"
    DIALOGUE = "dialogue", "对话"


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


class Sentence(models.Model):
    """
    句子模型

    存储章节的每个句子，包含文本、类型、说话人、情感等信息。
    替代传统的"段落级"存储，支持句子级严格拆分。
    """

    # 关联信息
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="sentences",
        verbose_name="所属章节"
    )

    # 位置信息
    sentence_index = models.IntegerField(verbose_name="句子序号")

    # 内容信息
    text = models.TextField(verbose_name="句子文本")
    sentence_type = models.CharField(
        max_length=20,
        choices=SentenceType.choices,
        default=SentenceType.NARRATION,
        verbose_name="句子类型"
    )

    # 说话人信息
    speaker = models.CharField(max_length=100, blank=True, verbose_name="说话人")
    is_narrator = models.BooleanField(default=True, verbose_name="是否旁白")

    # 情感信息（仅对话有，旁白为null）
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

    # 语音特征（从旁白提取的语音状态，如嘶哑、低沉、颤抖）
    voice_context = models.CharField(max_length=100, blank=True, verbose_name="语音特征")

    # 特殊标记
    special_markers = models.JSONField(default=list, blank=True, verbose_name="特殊标记")
    is_ancient_text = models.BooleanField(default=False, verbose_name="古文")
    is_poetry = models.BooleanField(default=False, verbose_name="诗词")
    is_inner_thought = models.BooleanField(default=False, verbose_name="内心独白")
    is_system_prompt = models.BooleanField(default=False, verbose_name="系统提示")

    # 元数据
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "sentences"
        verbose_name = "句子"
        verbose_name_plural = "句子列表"
        ordering = ["chapter", "sentence_index"]
        indexes = [
            models.Index(fields=["chapter", "sentence_index"]),
            models.Index(fields=["sentence_type"]),
            models.Index(fields=["emotion"]),
            models.Index(fields=["speaker"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["chapter", "sentence_index"],
                name="uq_chapter_sentence"
            )
        ]

    def __str__(self):
        speaker = self.speaker or "旁白"
        text_preview = self.text[:30] if self.text else ""
        return f"第{self.sentence_index}句 [{speaker}]: {text_preview}..."

    @classmethod
    def from_dict(cls, chapter, data: dict) -> "Sentence":
        """
        从分析结果字典创建 Sentence 实例

        解析 DeepSeek 返回的句子 dict，映射到 Sentence 模型字段。

        Args:
            chapter: Chapter 实例
            data: 句子字典，包含 sentence_index, text, type, speaker, emotion 等

        Returns:
            Sentence: 未保存的 Sentence 实例
        """
        # 解析 emotion 字段（格式：情感_强度，如 "愤怒_强"）
        emotion_raw = data.get("emotion") or ""
        emotion = ""
        intensity = ""
        if "_" in emotion_raw:
            parts = emotion_raw.split("_", 1)
            emotion = parts[0].strip()
            intensity = parts[1].strip()
        elif emotion_raw:
            emotion = emotion_raw.strip()

        # 确定句子类型（兼容 paragraph_index 和 sentence_index）
        sent_type = data.get("type", "narration")
        # 兼容旧结构：mixed 降级为 narration
        if sent_type == "mixed":
            sent_type = "narration"

        # 确定说话人及是否旁白
        speaker = data.get("speaker", "") or ""
        is_narrator = speaker in ("", "旁白", "narrator", "未识别", "未知")

        # 解析 special_markers → 布尔标记
        markers = data.get("special_markers") or []
        is_ancient_text = "古文朗读" in markers or "古文" in markers
        is_poetry = "诗词" in markers
        is_inner_thought = "内心独白" in markers
        is_system_prompt = "系统提示" in markers

        # 获取句子索引（兼容新旧结构）
        sentence_index = data.get("sentence_index", 0) or data.get("paragraph_index", 0) or 0

        return cls(
            chapter=chapter,
            sentence_index=sentence_index,
            text=data.get("text", ""),
            sentence_type=sent_type,
            speaker=speaker,
            is_narrator=is_narrator,
            emotion=emotion or None,
            emotion_intensity=intensity or None,
            polyphone_fixes=data.get("polyphone_fixes") or [],
            voice_context=data.get("voice_context") or "",
            special_markers=markers,
            is_ancient_text=is_ancient_text,
            is_poetry=is_poetry,
            is_inner_thought=is_inner_thought,
            is_system_prompt=is_system_prompt,
        )

    @classmethod
    def save_chapter_sentences(cls, chapter, sentences_data: list) -> list["Sentence"]:
        """
        批量保存章节句子

        删除章节原有句子，根据分析结果批量创建新句子。

        Args:
            chapter: Chapter 实例
            sentences_data: 句子字典列表

        Returns:
            list[Sentence]: 创建的 Sentence 实例列表
        """
        # 删除旧句子
        cls.objects.filter(chapter=chapter).delete()

        # 创建新句子
        instances = []
        for data in sentences_data:
            sent = cls.from_dict(chapter, data)
            sent.save()
            instances.append(sent)

        return instances

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
            "sentence_index": self.sentence_index,
            "text": self.text,
            "type": self.sentence_type,
            "type_display": self.get_sentence_type_display(),
            "speaker": self.speaker,
            "is_narrator": self.is_narrator,
            "emotion": self.emotion,
            "emotion_display": self.get_emotion_display(),
            "emotion_intensity": self.emotion_intensity,
            "emotion_with_intensity": self.emotion_with_intensity,
            "polyphone_fixes": self.polyphone_fixes or [],
            "voice_context": self.voice_context or "",
            "special_markers": self.special_markers or [],
            "is_ancient_text": self.is_ancient_text,
            "is_poetry": self.is_poetry,
            "is_inner_thought": self.is_inner_thought,
            "is_system_prompt": self.is_system_prompt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
