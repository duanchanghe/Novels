# ===========================================
# API Serializers
# ===========================================

"""
Django REST Framework Serializers for AI 有声书工坊.
"""

from rest_framework import serializers
from core.models import Book, Chapter, AudioSegment, TTSTask


class AudioSegmentSerializer(serializers.ModelSerializer):
    """音频片段序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AudioSegment
        fields = [
            'id', 'chapter_id', 'segment_index', 'text_content', 'role',
            'emotion', 'voice_id', 'speed', 'status', 'status_display',
            'audio_file_path', 'audio_url', 'audio_duration_ms', 'audio_bytes_size',
            'minimax_cost', 'deepseek_cost', 'retry_count', 'error_message',
            'created_at', 'updated_at'
        ]


class ChapterSerializer(serializers.ModelSerializer):
    """章节序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    characters_list = serializers.SerializerMethodField()
    
    class Meta:
        model = Chapter
        fields = [
            'id', 'book_id', 'chapter_index', 'title', 'raw_text',
            'cleaned_text', 'analysis_result', 'characters', 'characters_list',
            'status', 'status_display', 'total_segments', 'completed_segments',
            'failed_segments', 'audio_file_path', 'audio_duration',
            'audio_file_size', 'deepseek_tokens', 'minimax_characters',
            'error_message', 'created_at', 'updated_at'
        ]
    
    def get_characters_list(self, obj):
        """获取角色列表"""
        if obj.characters:
            return [c.get('name') for c in obj.characters if isinstance(obj.characters, list)]
        return []


class ChapterListSerializer(serializers.ModelSerializer):
    """章节列表序列化器（简化版）"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Chapter
        fields = [
            'id', 'chapter_index', 'title', 'status', 'status_display',
            'total_segments', 'completed_segments', 'audio_duration',
            'created_at', 'updated_at'
        ]


class BookSerializer(serializers.ModelSerializer):
    """书籍序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    chapters = serializers.SerializerMethodField()
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'description', 'cover_image_path',
            'file_name', 'file_size', 'file_hash', 'file_path',
            'source_type', 'source_type_display', 'status', 'status_display',
            'total_chapters', 'processed_chapters', 'total_duration',
            'generation_mode', 'auto_publish_enabled', 'error_message',
            'created_at', 'updated_at', 'chapters'
        ]
    
    def get_chapters(self, obj):
        """获取章节列表"""
        chapters = Chapter.objects.filter(book_id=obj.id).order_by('chapter_index')
        return ChapterListSerializer(chapters, many=True).data


class BookListSerializer(serializers.ModelSerializer):
    """书籍列表序列化器（简化版）"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    chapter_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'cover_image_path',
            'status', 'status_display', 'source_type', 'source_type_display',
            'total_chapters', 'processed_chapters', 'chapter_count',
            'created_at', 'updated_at'
        ]
    
    def get_chapter_count(self, obj):
        """获取章节数"""
        return Chapter.objects.filter(book_id=obj.id).count()


class TTSTaskSerializer(serializers.ModelSerializer):
    """TTS任务序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = TTSTask
        fields = [
            'id', 'book_id', 'task_name', 'status', 'status_display',
            'total_segments', 'completed_segments', 'failed_segments',
            'deepseek_total_tokens', 'minimax_total_characters',
            'started_at', 'completed_at', 'error_message', 'created_at'
        ]
