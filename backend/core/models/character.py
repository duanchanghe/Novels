# ===========================================
# Models - Character
# ===========================================

"""
人物角色模型
"""

import json
from django.db import models
from django.utils import timezone


class GenderType(models.TextChoices):
    """性别类型"""
    MALE = "male", "男"
    FEMALE = "female", "女"
    UNKNOWN = "unknown", "未知"


class CharacterStatus(models.TextChoices):
    """角色状态"""
    ACTIVE = "active", "活跃"
    INACTIVE = "inactive", "未激活"
    ARCHIVED = "archived", "已归档"


class RoleType(models.TextChoices):
    """角色类型"""
    PROTAGONIST = "protagonist", "主角"
    SUPPORTING = "supporting", "配角"
    MINOR = "minor", "龙套"
    NARRATOR = "narrator", "旁白"


class Character(models.Model):
    """
    人物角色模型

    用于存储有声书中的人物角色信息，支持语音映射。
    """

    # 基本信息
    name = models.CharField(max_length=100, verbose_name="角色名称")
    aliases = models.JSONField(default=list, blank=True, verbose_name="别名列表")
    gender = models.CharField(
        max_length=20,
        choices=GenderType.choices,
        default=GenderType.UNKNOWN,
        verbose_name="性别"
    )
    role_type = models.CharField(
        max_length=20,
        choices=RoleType.choices,
        default=RoleType.SUPPORTING,
        verbose_name="角色类型"
    )

    # 描述信息
    description = models.TextField(blank=True, verbose_name="角色描述")
    personality = models.TextField(blank=True, verbose_name="性格特征")
    speech_style = models.TextField(blank=True, verbose_name="说话风格")
    voice_description = models.TextField(blank=True, verbose_name="声音描述")
    emotions = models.JSONField(default=list, blank=True, verbose_name="常用情感")

    # 统计数据
    dialogue_count = models.IntegerField(default=0, verbose_name="对话数量")

    # 关联信息
    book = models.ForeignKey(
        "Book",
        on_delete=models.CASCADE,
        related_name="characters",
        verbose_name="所属书籍",
        null=True,
        blank=True,
    )

    # 语音配置
    voice_profile = models.ForeignKey(
        "VoiceProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="characters",
        verbose_name="关联语音"
    )
    voice_prompt = models.TextField(blank=True, verbose_name="语音提示词")
    custom_voice_id = models.CharField(max_length=100, blank=True, verbose_name="自定义语音ID")
    custom_speed = models.FloatField(default=1.0, verbose_name="语速调整")
    custom_pitch = models.FloatField(default=0.0, verbose_name="音调调整")
    custom_volume = models.FloatField(default=1.0, verbose_name="音量调整")

    # 来源信息
    source = models.CharField(max_length=50, blank=True, verbose_name="来源")
    minio_path = models.CharField(max_length=500, blank=True, verbose_name="MinIO存储路径")
    minio_url = models.URLField(max_length=1000, blank=True, verbose_name="MinIO URL")

    # 排序
    sort_order = models.IntegerField(default=0, verbose_name="排序")

    # 状态
    status = models.CharField(
        max_length=20,
        choices=CharacterStatus.choices,
        default=CharacterStatus.ACTIVE,
        verbose_name="状态"
    )

    # 元数据
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "characters"
        verbose_name = "角色"
        verbose_name_plural = "角色列表"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["book", "name"]),
            models.Index(fields=["status"]),
            models.Index(fields=["role_type"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "aliases": self.aliases or [],
            "gender": self.gender,
            "gender_display": self.get_gender_display(),
            "role_type": self.role_type,
            "role_type_display": self.get_role_type_display() if self.role_type else None,
            "description": self.description,
            "personality": self.personality,
            "speech_style": self.speech_style,
            "voice_description": self.voice_description,
            "emotions": self.emotions or [],
            "dialogue_count": self.dialogue_count,
            "usage_count": self.usage_count,
            "book_id": self.book_id,
            "voice_profile_id": self.voice_profile_id,
            "voice_prompt": self.voice_prompt,
            "custom_voice_id": self.custom_voice_id,
            "custom_speed": self.custom_speed,
            "custom_pitch": self.custom_pitch,
            "custom_volume": self.custom_volume,
            "source": self.source,
            "minio_path": self.minio_path,
            "minio_url": self.minio_url,
            "sort_order": self.sort_order,
            "status": self.status,
            "status_display": self.get_status_display(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def usage_count(self):
        """使用次数（通过关联统计）"""
        return self.dialogue_count or 0
