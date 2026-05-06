"""
Django Forms - 核心模块表单定义

提供所有核心数据模型的 ModelForm，用于 Django Admin 和 API。
"""

from django import forms
from .models.character import Character, CharacterStatus, GenderType
from .models.sound_effect import (
    SoundEffect, SoundEffectUsage, SoundEffectCollection, SoundEffectCollectionItem,
    SoundEffectType, SoundLayer, SoundPriority, SoundSource, SoundEffectStatus
)


# ===========================================
# Character Forms
# ===========================================

class CharacterForm(forms.ModelForm):
    """角色 ModelForm"""

    class Meta:
        model = Character
        fields = [
            "book", "name", "aliases", "gender", "description",
            "voice_description", "role_type", "emotions", "dialogue_count",
            "voice_profile", "custom_voice_id", "custom_speed", "custom_pitch",
            "custom_volume", "status", "source", "sort_order"
        ]
        widgets = {
            "aliases": forms.Textarea(attrs={"rows": 2}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "emotions": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_aliases(self):
        """验证并转换别名列表"""
        aliases = self.cleaned_data.get("aliases")
        if aliases and isinstance(aliases, str):
            import json
            try:
                aliases = json.loads(aliases)
            except json.JSONDecodeError:
                pass
        return aliases

    def clean_emotions(self):
        """验证并转换情感列表"""
        emotions = self.cleaned_data.get("emotions")
        if emotions and isinstance(emotions, str):
            import json
            try:
                emotions = json.loads(emotions)
            except json.JSONDecodeError:
                pass
        return emotions


class CharacterBulkActionForm(forms.Form):
    """角色批量操作表单"""

    ACTION_CHOICES = [
        ("approve", "审核通过"),
        ("reject", "审核拒绝"),
        ("delete", "删除"),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES, label="操作")
    character_ids = forms.CharField(widget=forms.HiddenInput())


# ===========================================
# SoundEffect Forms
# ===========================================

class SoundEffectForm(forms.ModelForm):
    """音效 ModelForm"""

    class Meta:
        model = SoundEffect
        fields = [
            "name", "description", "chinese_description",
            "effect_type", "layer", "priority",
            "tags", "chinese_tags", "semantic_keywords",
            "source", "source_id", "source_url", "license_type",
            "duration_ms", "file_format", "file_size", "sample_rate",
            "local_path", "minio_path", "minio_url",
            "status", "is_favorite", "is_verified",
            "suitable_scenes",
            "recommended_volume_min", "recommended_volume_max",
            "recommended_fade_in_ms", "recommended_fade_out_ms",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "chinese_description": forms.Textarea(attrs={"rows": 2}),
            "tags": forms.Textarea(attrs={"rows": 2}),
            "chinese_tags": forms.Textarea(attrs={"rows": 2}),
            "semantic_keywords": forms.Textarea(attrs={"rows": 2}),
            "suitable_scenes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_tags(self):
        """验证并转换标签列表"""
        tags = self.cleaned_data.get("tags")
        if tags and isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                pass
        return tags

    def clean_chinese_tags(self):
        """验证并转换中文标签列表"""
        tags = self.cleaned_data.get("chinese_tags")
        if tags and isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                pass
        return tags

    def clean_semantic_keywords(self):
        """验证并转换语义关键词列表"""
        keywords = self.cleaned_data.get("semantic_keywords")
        if keywords and isinstance(keywords, str):
            import json
            try:
                keywords = json.loads(keywords)
            except json.JSONDecodeError:
                pass
        return keywords

    def clean_suitable_scenes(self):
        """验证并转换适用场景列表"""
        scenes = self.cleaned_data.get("suitable_scenes")
        if scenes and isinstance(scenes, str):
            import json
            try:
                scenes = json.loads(scenes)
            except json.JSONDecodeError:
                pass
        return scenes


class SoundEffectImportForm(forms.Form):
    """音效批量导入表单"""

    source = forms.ChoiceField(
        choices=SoundSource.choices,
        label="音效来源"
    )
    effect_type = forms.ChoiceField(
        choices=SoundEffectType.choices,
        label="音效类型"
    )
    csv_file = forms.FileField(
        label="CSV 文件",
        help_text="上传包含音效信息的 CSV 文件"
    )


class SoundEffectSearchForm(forms.Form):
    """音效搜索表单"""

    keyword = forms.CharField(
        max_length=200,
        required=False,
        label="关键词",
        widget=forms.TextInput(attrs={"placeholder": "搜索音效名称、描述..."})
    )
    effect_type = forms.ChoiceField(
        choices=[("", "全部")] + list(SoundEffectType.choices),
        required=False,
        label="音效类型"
    )
    layer = forms.ChoiceField(
        choices=[("", "全部")] + list(SoundLayer.choices),
        required=False,
        label="音效层级"
    )
    source = forms.ChoiceField(
        choices=[("", "全部")] + list(SoundSource.choices),
        required=False,
        label="来源"
    )
    status = forms.ChoiceField(
        choices=[("", "全部")] + list(SoundEffectStatus.choices),
        required=False,
        label="状态"
    )
    is_verified = forms.ChoiceField(
        choices=[("", "全部"), ("1", "已审核"), ("0", "未审核")],
        required=False,
        label="审核状态"
    )
    min_duration = forms.IntegerField(required=False, label="最小时长(秒)")
    max_duration = forms.IntegerField(required=False, label="最大时长(秒)")


# ===========================================
# SoundEffectCollection Forms
# ===========================================

class SoundEffectCollectionForm(forms.ModelForm):
    """音效收藏集 ModelForm"""

    class Meta:
        model = SoundEffectCollection
        fields = ["name", "description", "scene_type", "is_public", "is_default"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class SoundEffectCollectionItemForm(forms.ModelForm):
    """音效收藏集项目 ModelForm"""

    class Meta:
        model = SoundEffectCollectionItem
        fields = ["sound_effect", "custom_volume", "custom_fade_in_ms", "custom_fade_out_ms", "sort_order"]


# ===========================================
# SoundEffectUsage Forms
# ===========================================

class SoundEffectUsageForm(forms.ModelForm):
    """音效使用记录 ModelForm（仅用于展示/搜索）"""

    class Meta:
        model = SoundEffectUsage
        fields = ["sound_effect", "book_id", "chapter_id", "trigger_at_ms", "volume"]
        readonly_fields = ["created_at"]
