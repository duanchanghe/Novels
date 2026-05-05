# ===========================================
# API Serializers - 章节相关
# ===========================================

"""
章节相关序列化器
"""

from typing import Optional, Any
import json
from rest_framework import serializers

from core.models import Chapter, ChapterStatus


class SafeJSONField(serializers.JSONField):
    """安全的 JSONField，处理各种输入类型"""

    def to_representation(self, value):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value


class ChapterListSerializer(serializers.ModelSerializer):
    """章节列表序列化器（简化版）"""

    class Meta:
        model = Chapter
        fields = [
            'id', 'book_id', 'chapter_index', 'title', 'status',
            'total_segments', 'completed_segments', 'audio_duration',
            'created_at', 'updated_at'
        ]


class ChapterDetailSerializer(serializers.ModelSerializer):
    """章节详情序列化器"""
    analysis_result = SafeJSONField(required=False, allow_null=True)
    characters = SafeJSONField(required=False, allow_null=True)
    progress_percentage = serializers.SerializerMethodField()
    # cleaned_text 在 DB 中存的是 MinIO 路径，需要在序列化时获取完整文本
    full_cleaned_text = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = '__all__'

    def get_progress_percentage(self, obj):
        """计算进度百分比"""
        if obj.total_segments == 0:
            return 0.0
        return round((obj.completed_segments / obj.total_segments) * 100, 2)

    def get_full_cleaned_text(self, obj):
        """
        从 MinIO 获取完整的清洗后文本

        DB 中 cleaned_text 存的是 MinIO 路径（chapters/{book_id}/{index}_cleaned.txt）
        这里自动解析路径并从 MinIO 获取完整文本。
        """
        if not obj.cleaned_text:
            return None

        # 如果 cleaned_text 不是路径（而是实际的文本内容），直接返回
        if not obj.cleaned_text.startswith("chapters/"):
            return obj.cleaned_text

        # 从 MinIO 获取完整文本
        try:
            from services.svc_minio_storage import get_storage_service
            storage = get_storage_service()
            full_text = storage.download_chapter_text(
                book_id=obj.book_id,
                chapter_index=obj.chapter_index,
            )
            return full_text
        except Exception:
            # 如果获取失败，返回路径（用于调试）
            return obj.cleaned_text


class ChapterCreateSerializer(serializers.Serializer):
    """章节创建序列化器"""
    book_id = serializers.IntegerField()
    chapter_index = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=500, required=False, allow_blank=True)
    raw_text = serializers.CharField(required=False, allow_blank=True)


class ChapterUpdateSerializer(serializers.Serializer):
    """章节更新序列化器"""
    title = serializers.CharField(max_length=500, required=False)
    status = serializers.ChoiceField(choices=ChapterStatus.choices, required=False)


class ChapterConfirmSerializer(serializers.Serializer):
    """章节确认序列化器"""
    pass


class ChapterConfirmResponseSerializer(serializers.Serializer):
    """章节确认响应序列化器"""
    chapter_id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()


class ChapterRetrySerializer(serializers.Serializer):
    """章节重试序列化器"""
    pass


class ChapterRetryResponseSerializer(serializers.Serializer):
    """章节重试响应序列化器"""
    chapter_id = serializers.IntegerField()
    title = serializers.CharField(allow_null=True)
    status = serializers.CharField()


class ChapterAudioSerializer(serializers.Serializer):
    """章节音频序列化器"""
    chapter_id = serializers.IntegerField()
    audio_url = serializers.URLField()
    duration = serializers.IntegerField(allow_null=True)
    file_size = serializers.IntegerField(allow_null=True)
    format = serializers.CharField()


class SegmentListSerializer(serializers.Serializer):
    """片段列表序列化器"""
    id = serializers.IntegerField()
    chapter_id = serializers.IntegerField()
    segment_index = serializers.IntegerField()
    text_content = serializers.CharField()
    role = serializers.CharField(allow_null=True)
    emotion = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    status_display = serializers.CharField()
    audio_url = serializers.URLField(allow_null=True)
    audio_duration_ms = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)


class ChapterSegmentsResponseSerializer(serializers.Serializer):
    """章节片段响应序列化器"""
    chapter_id = serializers.IntegerField()
    segments = SegmentListSerializer(many=True)
    total_segments = serializers.IntegerField()
    completed_segments = serializers.IntegerField()
