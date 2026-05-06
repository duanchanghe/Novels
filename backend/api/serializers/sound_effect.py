# ===========================================
# 音效库序列化器
# ===========================================

"""
音效库序列化器

提供音效库的 API 数据序列化功能。
"""

from rest_framework import serializers

from core.models import (
    SoundEffect,
    SoundEffectUsage,
    SoundEffectCollection,
    SoundEffectCollectionItem,
    SoundEffectType,
    SoundLayer,
    SoundPriority,
    SoundSource,
    SoundEffectStatus,
)


class SoundEffectSerializer(serializers.ModelSerializer):
    """音效序列化器"""

    effect_type_display = serializers.CharField(
        source="get_effect_type_display",
        read_only=True
    )
    layer_display = serializers.CharField(
        source="get_layer_display",
        read_only=True
    )
    source_display = serializers.CharField(
        source="get_source_display",
        read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )
    priority_display = serializers.CharField(
        source="get_priority_display",
        read_only=True
    )

    class Meta:
        model = SoundEffect
        fields = [
            "id",
            "name",
            "description",
            "chinese_description",
            "effect_type",
            "effect_type_display",
            "layer",
            "layer_display",
            "tags",
            "chinese_tags",
            "semantic_keywords",
            "source",
            "source_display",
            "source_id",
            "source_url",
            "license_type",
            "duration_ms",
            "file_format",
            "file_size",
            "sample_rate",
            "local_path",
            "minio_path",
            "minio_url",
            "status",
            "status_display",
            "is_favorite",
            "usage_count",
            "priority",
            "priority_display",
            "suitable_scenes",
            "recommended_volume_min",
            "recommended_volume_max",
            "recommended_fade_in_ms",
            "recommended_fade_out_ms",
            "is_verified",
            "verified_at",
            "created_at",
            "updated_at",
            "last_used_at",
        ]
        read_only_fields = [
            "id",
            "usage_count",
            "created_at",
            "updated_at",
            "last_used_at",
        ]


class SoundEffectListSerializer(serializers.ModelSerializer):
    """音效列表序列化器（简化版）"""

    effect_type_display = serializers.CharField(
        source="get_effect_type_display",
        read_only=True
    )
    source_display = serializers.CharField(
        source="get_source_display",
        read_only=True
    )

    class Meta:
        model = SoundEffect
        fields = [
            "id",
            "name",
            "chinese_description",
            "effect_type",
            "effect_type_display",
            "layer",
            "source",
            "source_display",
            "duration_ms",
            "minio_url",
            "status",
            "is_favorite",
            "usage_count",
            "priority",
        ]


class SoundEffectCreateSerializer(serializers.Serializer):
    """音效创建序列化器"""

    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    chinese_description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )
    effect_type = serializers.ChoiceField(
        choices=SoundEffectType.choices,
        default=SoundEffectType.ENVIRONMENT
    )
    layer = serializers.ChoiceField(
        choices=SoundLayer.choices,
        default=SoundLayer.FOREGROUND
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    chinese_tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    semantic_keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    source = serializers.ChoiceField(
        choices=SoundSource.choices,
        default=SoundSource.USER_UPLOAD
    )
    source_id = serializers.CharField(required=False, allow_blank=True)
    source_url = serializers.URLField(required=False, allow_blank=True)
    duration_ms = serializers.IntegerField(required=False, allow_null=True)
    file_format = serializers.CharField(required=False, allow_blank=True)
    local_path = serializers.CharField(required=False, allow_blank=True)
    minio_path = serializers.CharField(required=False, allow_blank=True)
    suitable_scenes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    recommended_volume_min = serializers.FloatField(
        required=False,
        allow_null=True
    )
    recommended_volume_max = serializers.FloatField(
        required=False,
        allow_null=True
    )
    recommended_fade_in_ms = serializers.IntegerField(
        required=False,
        allow_null=True
    )
    recommended_fade_out_ms = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    def validate(self, attrs):
        """验证数据"""
        if attrs.get("recommended_volume_min") and attrs.get("recommended_volume_max"):
            if attrs["recommended_volume_min"] > attrs["recommended_volume_max"]:
                raise serializers.ValidationError(
                    "推荐音量下限不能大于上限"
                )
        return attrs


class SoundEffectUpdateSerializer(serializers.Serializer):
    """音效更新序列化器"""

    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    chinese_description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )
    effect_type = serializers.ChoiceField(
        choices=SoundEffectType.choices,
        required=False
    )
    layer = serializers.ChoiceField(
        choices=SoundLayer.choices,
        required=False
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    chinese_tags = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    semantic_keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    priority = serializers.ChoiceField(
        choices=SoundPriority.choices,
        required=False
    )
    suitable_scenes = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    recommended_volume_min = serializers.FloatField(
        required=False,
        allow_null=True
    )
    recommended_volume_max = serializers.FloatField(
        required=False,
        allow_null=True
    )
    recommended_fade_in_ms = serializers.IntegerField(
        required=False,
        allow_null=True
    )
    recommended_fade_out_ms = serializers.IntegerField(
        required=False,
        allow_null=True
    )
    status = serializers.ChoiceField(
        choices=SoundEffectStatus.choices,
        required=False
    )
    is_favorite = serializers.BooleanField(required=False)
    is_verified = serializers.BooleanField(required=False)


class SoundEffectSearchSerializer(serializers.Serializer):
    """音效搜索序列化器"""

    query = serializers.CharField(max_length=500)
    effect_type = serializers.ChoiceField(
        choices=SoundEffectType.choices,
        required=False
    )
    layer = serializers.ChoiceField(
        choices=SoundLayer.choices,
        required=False
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    limit = serializers.IntegerField(default=10, min_value=1, max_value=100)
    include_bbc = serializers.BooleanField(default=True)


class SoundEffectMatchSerializer(serializers.Serializer):
    """音效匹配结果序列化器"""

    sound_effect = SoundEffectSerializer()
    match_score = serializers.FloatField()
    match_reason = serializers.CharField()
    suggested_volume = serializers.FloatField()
    suggested_fade_in_ms = serializers.IntegerField()
    suggested_fade_out_ms = serializers.IntegerField()


class SoundEffectRecommendSerializer(serializers.Serializer):
    """章节音效推荐序列化器"""

    book_id = serializers.IntegerField(required=False, allow_null=True)
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)


class SoundEffectUsageSerializer(serializers.ModelSerializer):
    """音效使用记录序列化器"""

    sound_effect_name = serializers.CharField(
        source="sound_effect.name",
        read_only=True
    )

    class Meta:
        model = SoundEffectUsage
        fields = [
            "id",
            "sound_effect_id",
            "sound_effect_name",
            "book_id",
            "chapter_id",
            "trigger_at_ms",
            "volume",
            "fade_in_ms",
            "fade_out_ms",
            "loop",
            "matched_from_query",
            "match_score",
            "created_at",
        ]


class SoundEffectUsageCreateSerializer(serializers.Serializer):
    """音效使用记录创建序列化器"""

    sound_effect_id = serializers.IntegerField()
    book_id = serializers.IntegerField(required=False, allow_null=True)
    chapter_id = serializers.IntegerField(required=False, allow_null=True)
    trigger_at_ms = serializers.IntegerField(required=False, allow_null=True)
    volume = serializers.FloatField(required=False, allow_null=True)
    fade_in_ms = serializers.IntegerField(required=False, allow_null=True)
    fade_out_ms = serializers.IntegerField(required=False, allow_null=True)
    loop = serializers.BooleanField(default=False)
    matched_from_query = serializers.CharField(
        required=False,
        allow_blank=True
    )
    match_score = serializers.FloatField(required=False, allow_null=True)


class SoundEffectCollectionSerializer(serializers.ModelSerializer):
    """音效收藏集序列化器"""

    sound_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SoundEffectCollection
        fields = [
            "id",
            "name",
            "description",
            "scene_type",
            "sound_count",
            "is_public",
            "is_default",
            "created_at",
            "updated_at",
        ]


class SoundEffectCollectionDetailSerializer(serializers.ModelSerializer):
    """音效收藏集详情序列化器"""

    sound_effects = SoundEffectListSerializer(many=True, read_only=True)
    sound_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SoundEffectCollection
        fields = [
            "id",
            "name",
            "description",
            "scene_type",
            "sound_effects",
            "sound_count",
            "is_public",
            "is_default",
            "created_at",
            "updated_at",
        ]


class SoundEffectCollectionCreateSerializer(serializers.Serializer):
    """音效收藏集创建序列化器"""

    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    scene_type = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50
    )
    is_public = serializers.BooleanField(default=False)
    sound_effect_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )


class SoundEffectCollectionUpdateSerializer(serializers.Serializer):
    """音效收藏集更新序列化器"""

    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    scene_type = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50
    )
    is_public = serializers.BooleanField(required=False)
    is_default = serializers.BooleanField(required=False)


class SoundEffectCollectionItemSerializer(serializers.ModelSerializer):
    """音效收藏集项目序列化器"""

    sound_effect = SoundEffectListSerializer(read_only=True)

    class Meta:
        model = SoundEffectCollectionItem
        fields = [
            "id",
            "sound_effect",
            "custom_volume",
            "custom_fade_in_ms",
            "custom_fade_out_ms",
            "sort_order",
            "added_at",
        ]


class SoundEffectStatisticsSerializer(serializers.Serializer):
    """音效库统计序列化器"""

    total_sound_effects = serializers.IntegerField()
    by_source = serializers.DictField()
    by_type = serializers.DictField()
    total_usage_count = serializers.IntegerField()
    downloaded_count = serializers.IntegerField()


class BBSSyncSerializer(serializers.Serializer):
    """BBC 同步序列化器"""

    keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    effect_type = serializers.ChoiceField(
        choices=SoundEffectType.choices,
        required=False
    )
    limit = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=1000
    )


class ChapterSoundDesignSerializer(serializers.Serializer):
    """章节音效设计序列化器"""

    chapter_id = serializers.IntegerField()
    sound_effects = SoundEffectMatchSerializer(many=True)
    background_music = serializers.ListField(child=serializers.DictField())
    audio_bridge = serializers.DictField()
    total_duration_ms = serializers.IntegerField()
    warnings = serializers.ListField(child=serializers.CharField())


class SoundEffectImportExportSerializer(serializers.Serializer):
    """音效导入导出序列化器"""

    book_id = serializers.IntegerField()
    overwrite = serializers.BooleanField(default=False)


class ChapterSoundEffectsSerializer(serializers.Serializer):
    """
    章节音效数据序列化器

    用于处理 DeepSeek 分析结果中的 sound_effects 字段。
    """

    index = serializers.IntegerField(required=False)
    type = serializers.ChoiceField(
        choices=[
            "environment",
            "action",
            "transition",
            "nature",
            "ambient",
            "weather",
            "urban",
            "fantasy",
            "scifi",
        ]
    )
    description = serializers.CharField(max_length=500)
    trigger_at = serializers.CharField(max_length=20, required=False)
    duration_ms = serializers.IntegerField(required=False, allow_null=True)
    volume = serializers.FloatField(required=False, allow_null=True)
    fade_in_ms = serializers.IntegerField(required=False, allow_null=True)
    fade_out_ms = serializers.IntegerField(required=False, allow_null=True)
    loop = serializers.BooleanField(default=False)
    priority = serializers.ChoiceField(
        choices=["high", "medium", "low"],
        default="medium"
    )
    layer = serializers.ChoiceField(
        choices=["foreground", "background"],
        default="foreground"
    )
    text_anchor = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="关联的原文片段"
    )


class BackgroundMusicSerializer(serializers.Serializer):
    """
    背景音乐数据序列化器

    用于处理 DeepSeek 分析结果中的 background_music 字段。
    """

    index = serializers.IntegerField(required=False)
    type = serializers.ChoiceField(
        choices=[
            "theme",
            "epic",
            "romantic",
            "mysterious",
            "tension",
            "calm",
            "adventure",
            "sad",
            "heroic",
        ]
    )
    mood = serializers.CharField(max_length=255)
    trigger_at = serializers.CharField(max_length=20)
    end_at = serializers.CharField(max_length=20, required=False)
    duration_ms = serializers.IntegerField(required=False, allow_null=True)
    volume = serializers.FloatField(default=0.3)
    fade_in_ms = serializers.IntegerField(default=2000)
    fade_out_ms = serializers.IntegerField(default=3000)
    crossfade_with_next = serializers.BooleanField(default=True)
    intensity = serializers.IntegerField(min_value=1, max_value=5, default=3)
    scene_context = serializers.CharField(
        required=False,
        allow_blank=True
    )
    suggested_keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )


class AudioBridgeSerializer(serializers.Serializer):
    """音频桥接设计序列化器"""

    opening = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="开场音效描述"
    )
    chapter_transitions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="章节过渡音效建议"
    )
    ending = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="结尾音效描述"
    )
    silence_markers = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="需要留白的时刻"
    )
