# ===========================================
# API Serializers - 通用和公共模型
# ===========================================

"""
通用序列化器和响应模型
"""

from typing import Optional, Dict, Any, List
from rest_framework import serializers


class PaginationSerializer(serializers.Serializer):
    """分页序列化器"""
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    items = serializers.ListField()


class ErrorSerializer(serializers.Serializer):
    """错误响应序列化器"""
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)


class SuccessResponseSerializer(serializers.Serializer):
    """通用成功响应序列化器"""
    success = serializers.BooleanField(default=True)
    data = serializers.DictField(required=False)
    meta = serializers.DictField(required=False)


class ErrorResponseSerializer(serializers.Serializer):
    """通用错误响应序列化器"""
    success = serializers.BooleanField(default=False)
    error = ErrorSerializer()


class HealthSerializer(serializers.Serializer):
    """健康检查序列化器"""
    status = serializers.CharField()
    service = serializers.CharField()
    version = serializers.CharField()
    database = serializers.CharField()
    redis = serializers.CharField()
    minio = serializers.CharField()


class FileUploadSerializer(serializers.Serializer):
    """文件上传序列化器"""
    file = serializers.FileField()

    def validate_file(self, value):
        """验证文件"""
        # 检查文件扩展名
        if not value.name.lower().endswith('.epub'):
            raise serializers.ValidationError("只支持 EPUB 格式文件")
        # 检查文件大小（限制 500MB）
        max_size = 500 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(f"文件大小不能超过 500MB")
        return value


class VoiceSerializer(serializers.Serializer):
    """音色序列化器"""
    id = serializers.CharField()
    name = serializers.CharField()
    gender = serializers.CharField()
    description = serializers.CharField(required=False)
    age_range = serializers.CharField(required=False)
    suitable_roles = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class EmotionSerializer(serializers.Serializer):
    """情感序列化器"""
    id = serializers.CharField()
    name = serializers.CharField()
    intensity_levels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True
    )
    aliases = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class VoiceMappingSerializer(serializers.Serializer):
    """音色映射序列化器"""
    character = serializers.CharField()
    recommended_voice = serializers.DictField()


class VoiceConfigResponseSerializer(serializers.Serializer):
    """音色配置响应序列化器"""
    book_id = serializers.IntegerField()
    characters = serializers.ListField(child=serializers.CharField())
    recommendations = VoiceMappingSerializer(many=True)
    available_voices = VoiceSerializer(many=True)


class WatchStatusSerializer(serializers.Serializer):
    """监听状态序列化器"""
    is_running = serializers.BooleanField()
    watch_dir = serializers.CharField()
    watched_dirs = serializers.ListField(child=serializers.CharField())
    interval = serializers.IntegerField()
    concurrent = serializers.IntegerField()
    recent_files = serializers.ListField(required=False)


class PublishChannelSerializer(serializers.Serializer):
    """发布渠道序列化器"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    platform_type = serializers.CharField()
    platform_type_display = serializers.CharField()
    is_enabled = serializers.BooleanField()
    auto_publish = serializers.BooleanField()
    priority = serializers.IntegerField()
    description = serializers.CharField(allow_null=True)
    total_published = serializers.IntegerField()
    success_count = serializers.IntegerField()
    failure_count = serializers.IntegerField()
    last_published_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class PublishChannelCreateSerializer(serializers.Serializer):
    """创建发布渠道序列化器"""
    name = serializers.CharField(max_length=100)
    platform_type = serializers.CharField()
    api_config = serializers.DictField(required=False)
    auto_publish = serializers.BooleanField(default=False)
    description = serializers.CharField(required=False, allow_blank=True)


class PublishChannelUpdateSerializer(serializers.Serializer):
    """更新发布渠道序列化器"""
    name = serializers.CharField(max_length=100, required=False)
    api_config = serializers.DictField(required=False)
    is_enabled = serializers.BooleanField(required=False)
    auto_publish = serializers.BooleanField(required=False)


class PublishRecordSerializer(serializers.Serializer):
    """发布记录序列化器"""
    id = serializers.IntegerField()
    book_id = serializers.IntegerField()
    channel_id = serializers.IntegerField()
    channel_name = serializers.CharField(required=False)
    book_title = serializers.CharField(required=False)
    status = serializers.CharField()
    status_display = serializers.CharField()
    external_album_id = serializers.CharField(allow_null=True)
    external_album_url = serializers.URLField(allow_null=True)
    total_chapters = serializers.IntegerField()
    published_chapters = serializers.IntegerField()
    failed_chapters = serializers.IntegerField()
    progress_percentage = serializers.FloatField()
    error_message = serializers.CharField(allow_null=True)
    published_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class PublishRequestSerializer(serializers.Serializer):
    """发布请求序列化器"""
    channel_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )


class PublishResponseSerializer(serializers.Serializer):
    """发布响应序列化器"""
    book_id = serializers.IntegerField()
    task_id = serializers.CharField()
    channels = serializers.ListField(child=serializers.IntegerField())
    status = serializers.CharField()


class PublishStatusResponseSerializer(serializers.Serializer):
    """发布状态响应序列化器"""
    book_id = serializers.IntegerField()
    records = PublishRecordSerializer(many=True)


class StatisticSerializer(serializers.Serializer):
    """统计信息序列化器"""
    total_books = serializers.IntegerField()
    processing_books = serializers.IntegerField()
    completed_books = serializers.IntegerField()
    failed_books = serializers.IntegerField()
    total_chapters = serializers.IntegerField()
    total_audio_hours = serializers.FloatField()
