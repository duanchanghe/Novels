"""
Character 序列化器
"""

from rest_framework import serializers
from core.models import Character, CharacterStatus, GenderType


class CharacterSerializer(serializers.ModelSerializer):
    """角色序列化器"""
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    effective_voice_id = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = [
            "id", "book_id", "name", "aliases", "gender", "gender_display",
            "description", "voice_description", "role_type", "emotions",
            "dialogue_count", "voice_profile_id", "voice_profile",
            "custom_voice_id", "custom_speed", "custom_pitch", "custom_volume",
            "effective_voice_id", "status", "status_display", "source",
            "sort_order", "usage_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "usage_count", "created_at", "updated_at"]

    def get_effective_voice_id(self, obj):
        return obj.get_effective_voice_id()


class CharacterListSerializer(serializers.ModelSerializer):
    """角色列表序列化器（简化版）"""
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Character
        fields = [
            "id", "name", "gender", "role_type", "status", "status_display",
            "dialogue_count", "usage_count",
        ]


class CharacterCreateSerializer(serializers.Serializer):
    """角色创建序列化器"""
    name = serializers.CharField(max_length=100)
    gender = serializers.ChoiceField(choices=GenderType.choices, default=GenderType.UNKNOWN)
    description = serializers.CharField(required=False, allow_blank=True)
    voice_description = serializers.CharField(required=False, allow_blank=True)


class CharacterUpdateSerializer(serializers.Serializer):
    """角色更新序列化器"""
    name = serializers.CharField(max_length=100, required=False)
    gender = serializers.ChoiceField(choices=GenderType.choices, required=False)
    voice_profile_id = serializers.IntegerField(required=False, allow_null=True)
    custom_voice_id = serializers.CharField(required=False, allow_blank=True)
    custom_speed = serializers.FloatField(required=False, allow_null=True)
    custom_pitch = serializers.FloatField(required=False, allow_null=True)
    custom_volume = serializers.FloatField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=CharacterStatus.choices, required=False)


class CharacterBatchAssignSerializer(serializers.Serializer):
    """批量分配音色序列化器"""
    character_ids = serializers.ListField(child=serializers.IntegerField())
    voice_profile_id = serializers.IntegerField(required=False, allow_null=True)
    custom_voice_id = serializers.CharField(required=False, allow_blank=True)


class CharacterSummarySerializer(serializers.Serializer):
    """角色汇总序列化器"""
    total = serializers.IntegerField()
    approved = serializers.IntegerField()
    pending = serializers.IntegerField()
    rejected = serializers.IntegerField()
    male = serializers.IntegerField()
    female = serializers.IntegerField()
    unknown = serializers.IntegerField()
    assigned_voice = serializers.IntegerField()
    unassigned_voice = serializers.IntegerField()
