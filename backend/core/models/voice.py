"""
音色配置数据模型
"""
from django.db import models
from django.utils import timezone

from .book import Book


class RoleType(models.TextChoices):
    """角色类型枚举"""
    NARRATOR = "narrator", "旁白"
    MALE_LEAD = "male_lead", "男主角"
    FEMALE_LEAD = "female_lead", "女主角"
    ELDERLY = "elderly", "老人"
    CHILD = "child", "儿童"
    VILLAIN = "villain", "反派"
    SUPPORTING = "supporting", "配角"
    CUSTOM = "custom", "自定义"


DEFAULT_VOICE_PROFILES = [
    {
        "name": "默认旁白",
        "role_type": RoleType.NARRATOR,
        "description": "标准的叙述者音色，适合小说旁白",
        "minimax_voice_id": "male-qn",
        "speed": 1.0,
        "is_system_preset": True,
    },
    {
        "name": "青年男性",
        "role_type": RoleType.MALE_LEAD,
        "description": "青年男性主角音色",
        "minimax_voice_id": "male-qn",
        "speed": 1.0,
        "is_system_preset": True,
    },
    {
        "name": "青年女性",
        "role_type": RoleType.FEMALE_LEAD,
        "description": "青年女性主角音色",
        "minimax_voice_id": "female-shaon",
        "speed": 1.0,
        "is_system_preset": True,
    },
    {
        "name": "老年男性",
        "role_type": RoleType.ELDERLY,
        "description": "老年男性音色，较为沉稳",
        "minimax_voice_id": "male-yun",
        "speed": 0.9,
        "is_system_preset": True,
    },
    {
        "name": "儿童",
        "role_type": RoleType.CHILD,
        "description": "儿童音色，活泼可爱",
        "minimax_voice_id": "female-xiang",
        "speed": 1.1,
        "is_system_preset": True,
    },
    {
        "name": "反派",
        "role_type": RoleType.VILLAIN,
        "description": "反派角色音色，带有威胁感",
        "minimax_voice_id": "male-tian",
        "speed": 0.95,
        "is_system_preset": True,
    },
]


class VoiceProfile(models.Model):
    """音色配置数据模型"""

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="voice_profiles",
        blank=True,
        null=True,
        verbose_name="所属书籍"
    )

    name = models.CharField(max_length=100, verbose_name="音色名称")
    description = models.TextField(blank=True, null=True, verbose_name="音色描述")

    role_type = models.CharField(
        max_length=20,
        choices=RoleType.choices,
        default=RoleType.NARRATOR,
        verbose_name="角色类型"
    )

    character_names = models.JSONField(blank=True, null=True, verbose_name="关联的角色名称")

    minimax_voice_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="MiniMax音色ID")
    minimax_model = models.CharField(max_length=50, default="speech-01-turbo", verbose_name="MiniMax模型")

    speed = models.FloatField(default=1.0, verbose_name="语速倍率")
    pitch = models.FloatField(default=0.0, verbose_name="音调")
    volume = models.FloatField(default=1.0, verbose_name="音量")

    emotion_params = models.JSONField(blank=True, null=True, verbose_name="情感参数")

    is_system_preset = models.BooleanField(default=False, verbose_name="是否系统预设")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    created_by = models.CharField(max_length=100, blank=True, null=True, verbose_name="创建者")

    sort_order = models.IntegerField(default=0, verbose_name="排序顺序")
    usage_count = models.IntegerField(default=0, verbose_name="使用次数")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "voice_profiles"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["book", "role_type"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_role_type_display()})"

    def get_minimax_params(self):
        """获取 MiniMax TTS 调用参数"""
        return {
            "model": self.minimax_model,
            "voice_id": self.minimax_voice_id,
            "speed": self.speed,
            "pitch": self.pitch,
            "volume": self.volume,
            "emotion_params": self.emotion_params or {},
        }
