"""
音效库数据模型 - 广播级音效管理

参考 audiobookshelf 的音效库设计理念，结合 panns-inference 的音频理解能力，
使用 BBC Sound Effects 作为主要音源。

功能特性：
- 支持多种音效类型（环境音、动作音、自然音、转场音、氛围音）
- 自动打标签（基于描述文本的语义匹配）
- 与 DeepSeek 分析结果无缝集成
- 支持本地缓存和预下载
"""

from django.db import models
from django.utils import timezone


class SoundEffectType(models.TextChoices):
    """音效类型枚举"""
    ENVIRONMENT = "environment", "环境音"
    ACTION = "action", "动作音"
    TRANSITION = "transition", "转场音"
    NATURE = "nature", "自然音"
    AMBIENT = "ambient", "氛围音"
    WEATHER = "weather", "天气音"
    URBAN = "urban", "城市音"
    FANTASY = "fantasy", "玄幻/奇幻音"
    SCIFI = "scifi", "科幻音"


class SoundLayer(models.TextChoices):
    """音效层级枚举"""
    FOREGROUND = "foreground", "前景音效"
    BACKGROUND = "background", "背景音效"


class SoundPriority(models.TextChoices):
    """音效优先级枚举"""
    HIGH = "high", "高优先级"
    MEDIUM = "medium", "中优先级"
    LOW = "low", "低优先级"


class SoundSource(models.TextChoices):
    """音效来源枚举"""
    BBC = "bbc", "BBC Sound Effects"
    FSD50K = "fsd50k", "FSD50K"
    USER_UPLOAD = "user_upload", "用户上传"
    GENERATED = "generated", "AI生成"


class SoundEffectStatus(models.TextChoices):
    """音效状态枚举"""
    ACTIVE = "active", "可用"
    DOWNLOADING = "downloading", "下载中"
    UNAVAILABLE = "unavailable", "不可用"
    ARCHIVED = "archived", "已归档"


class SoundEffect(models.Model):
    """
    音效库

    存储所有可用的音效资源，支持：
    - 多种来源（BBC Sound Effects, FSD50K, 用户上传）
    - 智能标签和分类
    - 语义搜索
    - 音频特征向量（用于 panns-inference 相似度匹配）
    """

    # ── 基本信息 ──
    name = models.CharField(max_length=255, verbose_name="音效名称")
    description = models.TextField(blank=True, null=True, verbose_name="音效描述")
    chinese_description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="中文描述"
    )

    # ── 分类信息 ──
    effect_type = models.CharField(
        max_length=20,
        choices=SoundEffectType.choices,
        default=SoundEffectType.ENVIRONMENT,
        verbose_name="音效类型",
        db_index=True,
    )
    layer = models.CharField(
        max_length=20,
        choices=SoundLayer.choices,
        default=SoundLayer.FOREGROUND,
        verbose_name="音效层级",
    )

    # ── 标签系统 ──
    tags = models.JSONField(
        blank=True,
        null=True,
        verbose_name="标签列表",
        help_text="如：['rain', 'heavy', 'outdoor', 'night']"
    )
    chinese_tags = models.JSONField(
        blank=True,
        null=True,
        verbose_name="中文标签",
        help_text="如：['雨声', '大雨', '户外', '夜晚']"
    )

    # ── 语义匹配 ──
    semantic_keywords = models.JSONField(
        blank=True,
        null=True,
        verbose_name="语义关键词",
        help_text="用于语义搜索的关键词列表"
    )

    # 音频特征向量（用于 panns-inference 相似度匹配）
    # 存储为 JSON 格式，长度为 2048 维
    audio_embedding = models.JSONField(
        blank=True,
        null=True,
        verbose_name="音频特征向量",
    )

    # ── 来源信息 ──
    source = models.CharField(
        max_length=20,
        choices=SoundSource.choices,
        default=SoundSource.BBC,
        verbose_name="音效来源",
    )
    source_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="来源ID",
        help_text="BBC Sound Effects 的资源ID"
    )
    source_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name="原始URL",
    )
    license_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="许可证类型",
        help_text="如：BBC License, CC0, Creative Commons"
    )

    # ── 音频属性 ──
    duration_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="时长(毫秒)",
    )
    file_format = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="文件格式",
    )
    file_size = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="文件大小(字节)",
    )
    sample_rate = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="采样率",
    )

    # ── 存储信息 ──
    local_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="本地存储路径",
    )
    minio_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="MinIO存储路径",
    )
    minio_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name="MinIO访问URL",
    )

    # ── 状态管理 ──
    status = models.CharField(
        max_length=20,
        choices=SoundEffectStatus.choices,
        default=SoundEffectStatus.ACTIVE,
        verbose_name="状态",
    )
    is_favorite = models.BooleanField(
        default=False,
        verbose_name="收藏",
    )
    usage_count = models.IntegerField(
        default=0,
        verbose_name="使用次数",
    )

    # ── 元信息 ──
    priority = models.CharField(
        max_length=20,
        choices=SoundPriority.choices,
        default=SoundPriority.MEDIUM,
        verbose_name="推荐优先级",
    )

    # 适用于有声书的场景
    suitable_scenes = models.JSONField(
        blank=True,
        null=True,
        verbose_name="适用场景",
        help_text="如：['武侠', '仙侠', '都市', '玄幻']"
    )

    # 推荐的音量范围
    recommended_volume_min = models.FloatField(
        blank=True,
        null=True,
        verbose_name="推荐音量下限",
    )
    recommended_volume_max = models.FloatField(
        blank=True,
        null=True,
        verbose_name="推荐音量上限",
    )

    # 推荐的淡入淡出时间
    recommended_fade_in_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="推荐淡入时间(ms)",
    )
    recommended_fade_out_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="推荐淡出时间(ms)",
    )

    # ── 审核信息 ──
    is_verified = models.BooleanField(
        default=False,
        verbose_name="已审核",
    )
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="审核时间",
    )

    # ── 时间戳 ──
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="创建时间",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )
    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="最后使用时间",
    )

    class Meta:
        db_table = "sound_effects"
        ordering = ["-usage_count", "-priority", "name"]
        verbose_name = "音效"
        verbose_name_plural = "音效库"
        indexes = [
            models.Index(fields=["effect_type", "status"]),
            models.Index(fields=["source", "status"]),
            models.Index(fields=["-usage_count"]),
            models.Index(fields=["-priority"]),
            models.Index(fields=["is_verified", "status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_effect_type_display()})"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "chinese_description": self.chinese_description,
            "effect_type": self.effect_type,
            "effect_type_display": self.get_effect_type_display(),
            "layer": self.layer,
            "layer_display": self.get_layer_display(),
            "tags": self.tags,
            "chinese_tags": self.chinese_tags,
            "semantic_keywords": self.semantic_keywords,
            "source": self.source,
            "source_display": self.get_source_display(),
            "source_id": self.source_id,
            "source_url": self.source_url,
            "license_type": self.license_type,
            "duration_ms": self.duration_ms,
            "file_format": self.file_format,
            "file_size": self.file_size,
            "sample_rate": self.sample_rate,
            "local_path": self.local_path,
            "minio_path": self.minio_path,
            "minio_url": self.minio_url,
            "status": self.status,
            "status_display": self.get_status_display(),
            "is_favorite": self.is_favorite,
            "usage_count": self.usage_count,
            "priority": self.priority,
            "priority_display": self.get_priority_display(),
            "suitable_scenes": self.suitable_scenes,
            "recommended_volume_min": self.recommended_volume_min,
            "recommended_volume_max": self.recommended_volume_max,
            "recommended_fade_in_ms": self.recommended_fade_in_ms,
            "recommended_fade_out_ms": self.recommended_fade_out_ms,
            "is_verified": self.is_verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    def increment_usage(self):
        """增加使用次数"""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=["usage_count", "last_used_at"])

    def verify(self):
        """审核通过"""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save(update_fields=["is_verified", "verified_at"])

    def toggle_favorite(self):
        """切换收藏状态"""
        self.is_favorite = not self.is_favorite
        self.save(update_fields=["is_favorite"])

    def match_score(self, query: str, query_tags: list = None) -> float:
        """
        计算与查询的匹配分数

        用于语义搜索和推荐排序。

        Args:
            query: 查询文本（如 DeepSeek 生成的音效描述）
            query_tags: 查询标签列表

        Returns:
            float: 匹配分数 (0.0 - 1.0)
        """
        score = 0.0
        total_weight = 0.0

        # 1. 名称匹配 (权重: 0.3)
        if query.lower() in self.name.lower():
            score += 0.3
        elif any(word.lower() in self.name.lower() for word in query.split()):
            score += 0.15
        total_weight += 0.3

        # 2. 描述匹配 (权重: 0.2)
        if self.description:
            if query.lower() in self.description.lower():
                score += 0.2
            elif any(word.lower() in self.description.lower() for word in query.split()):
                score += 0.1
        if self.chinese_description:
            if query in self.chinese_description:
                score += 0.2
        total_weight += 0.2

        # 3. 标签匹配 (权重: 0.3)
        if query_tags:
            matching_tags = 0
            all_tags = (self.tags or []) + (self.chinese_tags or [])
            for qt in query_tags:
                if any(qt.lower() in tag.lower() for tag in all_tags):
                    matching_tags += 1
            if query_tags:
                score += 0.3 * (matching_tags / len(query_tags))
        elif self.tags:
            if any(word.lower() in " ".join(self.tags).lower() for word in query.split()):
                score += 0.15
        total_weight += 0.3

        # 4. 语义关键词匹配 (权重: 0.2)
        if self.semantic_keywords:
            matching_keywords = 0
            for keyword in self.semantic_keywords:
                if keyword.lower() in query.lower():
                    matching_keywords += 1
            score += 0.2 * (matching_keywords / len(self.semantic_keywords))
        total_weight += 0.2

        return score / total_weight if total_weight > 0 else 0.0


class SoundEffectUsage(models.Model):
    """
    音效使用记录

    跟踪音效的使用情况，用于分析和优化推荐。
    """

    sound_effect = models.ForeignKey(
        SoundEffect,
        on_delete=models.CASCADE,
        related_name="usage_records",
        verbose_name="音效"
    )

    # 使用场景
    book_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="书籍ID",
    )
    chapter_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="章节ID",
    )

    # 使用参数
    trigger_at_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="触发时间(ms)",
    )
    volume = models.FloatField(
        blank=True,
        null=True,
        verbose_name="音量",
    )
    fade_in_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="淡入时间(ms)",
    )
    fade_out_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="淡出时间(ms)",
    )
    loop = models.BooleanField(
        default=False,
        verbose_name="是否循环",
    )

    # 来源信息
    matched_from_query = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="匹配查询",
    )
    match_score = models.FloatField(
        blank=True,
        null=True,
        verbose_name="匹配分数",
    )

    # 时间戳
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="使用时间",
    )

    class Meta:
        db_table = "sound_effect_usages"
        ordering = ["-created_at"]
        verbose_name = "音效使用记录"
        verbose_name_plural = "音效使用记录"
        indexes = [
            models.Index(fields=["sound_effect", "created_at"]),
            models.Index(fields=["book_id", "chapter_id"]),
        ]

    def __str__(self):
        return f"{self.sound_effect.name} @ {self.created_at}"


class SoundEffectCollection(models.Model):
    """
    音效收藏集

    用户可以创建自定义的音效收藏集，方便管理和使用。
    """

    name = models.CharField(max_length=100, verbose_name="收藏集名称")
    description = models.TextField(blank=True, null=True, verbose_name="收藏集描述")

    # 音效列表（ManyToMany）
    sound_effects = models.ManyToManyField(
        SoundEffect,
        through="SoundEffectCollectionItem",
        related_name="collections",
        verbose_name="音效列表"
    )

    # 适用场景
    scene_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="场景类型",
        help_text="如：武侠、仙侠、玄幻、都市"
    )

    # 统计
    sound_count = models.IntegerField(
        default=0,
        verbose_name="音效数量",
    )

    # 元信息
    is_public = models.BooleanField(
        default=False,
        verbose_name="公开收藏集",
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name="默认收藏集",
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="创建时间",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        db_table = "sound_effect_collections"
        ordering = ["-is_default", "-sound_count", "name"]
        verbose_name = "音效收藏集"
        verbose_name_plural = "音效收藏集"

    def __str__(self):
        return self.name


class SoundEffectCollectionItem(models.Model):
    """
    音效收藏集项目

    连接收藏集和音效的多对多中间表，支持自定义排序。
    """

    collection = models.ForeignKey(
        SoundEffectCollection,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="收藏集"
    )
    sound_effect = models.ForeignKey(
        SoundEffect,
        on_delete=models.CASCADE,
        related_name="collection_items",
        verbose_name="音效"
    )

    # 自定义配置
    custom_volume = models.FloatField(
        blank=True,
        null=True,
        verbose_name="自定义音量",
    )
    custom_fade_in_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="自定义淡入时间",
    )
    custom_fade_out_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="自定义淡出时间",
    )

    # 排序
    sort_order = models.IntegerField(
        default=0,
        verbose_name="排序顺序",
    )

    # 时间戳
    added_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="添加时间",
    )

    class Meta:
        db_table = "sound_effect_collection_items"
        ordering = ["sort_order", "added_at"]
        verbose_name = "音效收藏集项目"
        verbose_name_plural = "音效收藏集项目"
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "sound_effect"],
                name="uq_collection_sound_effect"
            ),
        ]

    def __str__(self):
        return f"{self.collection.name} - {self.sound_effect.name}"
