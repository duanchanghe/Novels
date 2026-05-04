# ===========================================
# API Serializers
# ===========================================

"""
Django REST Framework Serializers for AI 有声书工坊.
"""

import json
from rest_framework import serializers
from django.db import models
from core.models import Book, Chapter, AudioSegment, TTSTask


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


class AudioSegmentSerializer(serializers.ModelSerializer):
    """音频片段序列化器"""
    
    class Meta:
        model = AudioSegment
        exclude = []


class ChapterSerializer(serializers.ModelSerializer):
    """章节序列化器"""
    # 使用 SafeJSONField 确保能处理各种类型的输入
    analysis_result = SafeJSONField(required=False, allow_null=True)
    characters = SafeJSONField(required=False, allow_null=True)
    
    class Meta:
        model = Chapter
        fields = '__all__'


class ChapterListSerializer(serializers.ModelSerializer):
    """章节列表序列化器（简化版）"""
    
    class Meta:
        model = Chapter
        fields = [
            'id', 'book_id', 'chapter_index', 'title', 'status',
            'total_segments', 'completed_segments', 'audio_duration',
            'created_at', 'updated_at'
        ]


class BookSerializer(serializers.ModelSerializer):
    """书籍序列化器"""
    chapters = serializers.SerializerMethodField()
    
    class Meta:
        model = Book
        fields = '__all__'
    
    def get_chapters(self, obj):
        """获取章节列表"""
        chapters = Chapter.objects.filter(book_id=obj.id).order_by('chapter_index')[:5]
        return ChapterListSerializer(chapters, many=True).data


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


class TTSTaskSerializer(serializers.ModelSerializer):
    """TTS任务序列化器"""
    
    class Meta:
        model = TTSTask
        fields = '__all__'
