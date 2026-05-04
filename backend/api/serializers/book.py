# ===========================================
# API Serializers - 书籍相关
# ===========================================

"""
书籍相关序列化器
"""

from typing import Optional
from rest_framework import serializers

from core.models import Book, Chapter, BookStatus, SourceType, GenerationMode


class BookListSerializer(serializers.ModelSerializer):
    """书籍列表序列化器（简化版）"""
    chapter_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'cover_image_path',
            'status', 'source_type', 'total_chapters', 'processed_chapters',
            'chapter_count', 'created_at', 'updated_at'
        ]

    def get_chapter_count(self, obj):
        """获取章节数"""
        return Chapter.objects.filter(book_id=obj.id).count()


class BookDetailSerializer(serializers.ModelSerializer):
    """书籍详情序列化器"""
    chapters = serializers.SerializerMethodField()
    chapter_count = serializers.SerializerMethodField()
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = Book
        fields = '__all__'

    def get_chapters(self, obj):
        """获取章节列表（最多5个）"""
        chapters = Chapter.objects.filter(book_id=obj.id).order_by('chapter_index')[:5]
        from .chapter import ChapterListSerializer
        return ChapterListSerializer(chapters, many=True).data

    def get_chapter_count(self, obj):
        """获取章节数"""
        return Chapter.objects.filter(book_id=obj.id).count()


class BookCreateSerializer(serializers.Serializer):
    """书籍创建序列化器"""
    title = serializers.CharField(max_length=500)
    author = serializers.CharField(max_length=255, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(max_length=50, default='zh-CN')
    source_type = serializers.ChoiceField(
        choices=SourceType.choices,
        default=SourceType.MANUAL
    )
    generation_mode = serializers.ChoiceField(
        choices=GenerationMode.choices,
        default=GenerationMode.AUTO
    )

    def validate_title(self, value):
        """验证书名"""
        if not value or not value.strip():
            raise serializers.ValidationError("书名不能为空")
        return value.strip()


class BookUpdateSerializer(serializers.Serializer):
    """书籍更新序列化器"""
    title = serializers.CharField(max_length=500, required=False)
    author = serializers.CharField(max_length=255, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(max_length=50, required=False)
    generation_mode = serializers.ChoiceField(
        choices=GenerationMode.choices,
        required=False
    )
    auto_publish_enabled = serializers.BooleanField(required=False)


class BookStatusSerializer(serializers.Serializer):
    """书籍状态序列化器"""
    book_id = serializers.IntegerField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    progress_percentage = serializers.FloatField()
    total_chapters = serializers.IntegerField()
    processed_chapters = serializers.IntegerField()
    error_message = serializers.CharField(allow_null=True)


class BookGenerateSerializer(serializers.Serializer):
    """生成请求序列化器"""
    generation_mode = serializers.ChoiceField(
        choices=GenerationMode.choices,
        default=GenerationMode.AUTO
    )


class BookGenerateResponseSerializer(serializers.Serializer):
    """生成响应序列化器"""
    book_id = serializers.IntegerField()
    task_id = serializers.CharField()
    generation_mode = serializers.CharField()
    status = serializers.CharField()


class BookRetrySerializer(serializers.Serializer):
    """重试序列化器"""
    pass


class BookRetryResponseSerializer(serializers.Serializer):
    """重试响应序列化器"""
    book_id = serializers.IntegerField()
    retried_count = serializers.IntegerField()
    chapters = serializers.ListField(child=serializers.DictField())


class BookAudioSerializer(serializers.Serializer):
    """书籍音频序列化器"""
    chapter_id = serializers.IntegerField()
    audio_url = serializers.URLField()
    duration = serializers.IntegerField(allow_null=True)
    file_size = serializers.IntegerField(allow_null=True)
    format = serializers.CharField()


class BookDownloadSerializer(serializers.Serializer):
    """书籍下载序列化器"""
    book_id = serializers.IntegerField()
    title = serializers.CharField()
    format = serializers.CharField()
    download_url = serializers.URLField()
    total_chapters = serializers.IntegerField()
    total_duration = serializers.IntegerField()
