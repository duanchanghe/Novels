# ===========================================
# API Views
# ===========================================

"""
Django REST Framework Views for AI 有声书工坊.
"""

import hashlib
import logging
import os
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from core.models import (
    Book, Chapter, AudioSegment, TTSTask,
    VoiceProfile, PublishChannel, PublishRecord,
    BookStatus, ChapterStatus, SourceType, GenerationMode, PublishStatus, PlatformType
)
from tasks.task_pipeline import (
    generate_audiobook_simple, process_chapter
)
from tasks.task_publish import publish_book_to_all_channels
from services.svc_epub_parser import EPUBParserService
from services.svc_minio_storage import get_storage_service
from services.svc_chapter_cleaner import clean_chapter_text
from services.svc_voice_mapper import VoiceMapperService
from services.svc_minimax_tts import MiniMaxTTSService
from services.svc_deepseek_analyzer import DeepSeekAnalyzerService
from services.svc_file_watcher import get_watcher_service

logger = logging.getLogger("audiobook")


class HealthCheckView(views.APIView):
    """健康检查视图"""
    
    def get(self, request):
        return Response({
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": "1.0.0",
        })


class BookViewSet(viewsets.ModelViewSet):
    """书籍管理视图集"""
    queryset = Book.objects.filter(deleted_at__isnull=True)
    serializer_class = None  # Will be defined based on action

    def get_serializer_class(self):
        from api.serializers import BookSerializer, BookListSerializer
        if self.action == "list":
            return BookListSerializer
        return BookSerializer

    def list(self, request):
        """获取书籍列表"""
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        status_filter = request.GET.get('status')
        search = request.GET.get('search')

        queryset = Book.objects.filter(deleted_at__isnull=True)

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(title__icontains=search) | queryset.filter(author__icontains=search)

        total = queryset.count()
        books = queryset.order_by('-created_at')[page_size*(page-1):page_size*page]

        from api.serializers import BookListSerializer
        serializer = BookListSerializer(books, many=True)
        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': serializer.data
        })

    def retrieve(self, request, pk=None):
        """获取书籍详情"""
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)
        
        from api.serializers import BookSerializer
        serializer = BookSerializer(book)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def chapters(self, request, pk=None):
        """获取书籍章节列表"""
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        chapters = Chapter.objects.filter(book_id=pk).order_by('chapter_index')
        from api.serializers import ChapterSerializer
        serializer = ChapterSerializer(chapters, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def status_info(self, request, pk=None):
        """获取书籍处理状态"""
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "book_id": book.id,
            "status": book.status,
            "progress_percentage": book.progress_percentage,
            "total_chapters": book.total_chapters,
            "processed_chapters": book.processed_chapters,
            "error_message": book.error_message,
        })

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """触发有声书生成"""
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        if book.status == BookStatus.DONE:
            return Response({"detail": "书籍已完成生成"}, status=status.HTTP_400_BAD_REQUEST)

        generation_mode = request.GET.get('generation_mode', 'auto')
        try:
            mode = GenerationMode(generation_mode)
        except ValueError:
            return Response({"detail": "无效的生成模式"}, status=status.HTTP_400_BAD_REQUEST)

        book.generation_mode = mode
        book.save()

        result = generate_audiobook_simple.delay(book.id)

        return Response({
            "book_id": book.id,
            "task_id": result.id,
            "generation_mode": mode,
            "status": "pending",
        })

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """重试失败的章节"""
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        failed_chapters = Chapter.objects.filter(
            book_id=pk, status=ChapterStatus.FAILED
        )
        if not failed_chapters.exists():
            return Response({"detail": "没有失败的章节"}, status=status.HTTP_400_BAD_REQUEST)

        retried = []
        for ch in failed_chapters:
            ch.status = ChapterStatus.PENDING
            ch.error_message = None
            ch.failed_segments = 0
            retried.append({"chapter_id": ch.id, "title": ch.title, "index": ch.chapter_index})
            process_chapter.delay(ch.id)

        Book.objects.filter(id=pk).update(status=BookStatus.PENDING)

        return Response({"book_id": pk, "retried_count": len(retried), "chapters": retried})

    @action(detail=True, methods=['get'])
    def audio(self, request, pk=None):
        """获取章节音频URL"""
        chapter_id = request.GET.get('chapter_id')
        if not chapter_id:
            return Response({"detail": "缺少 chapter_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            chapter = Chapter.objects.get(id=chapter_id, book_id=pk)
        except Chapter.DoesNotExist:
            return Response({"detail": "章节不存在"}, status=status.HTTP_404_NOT_FOUND)

        if not chapter.audio_file_path:
            return Response({"detail": "章节音频尚未生成"}, status=status.HTTP_404_NOT_FOUND)

        storage = get_storage_service()
        presigned_url = storage.get_presigned_url(
            bucket=settings.MINIO_BUCKET_AUDIO,
            object_name=chapter.audio_file_path,
            expires=timedelta(hours=1),
        )

        return Response({
            "chapter_id": chapter.id,
            "audio_url": presigned_url,
            "duration": chapter.audio_duration,
            "file_size": chapter.audio_file_size,
            "format": "mp3",
        })

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """获取有声书下载链接"""
        download_format = request.GET.get('format', 'mp3')

        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        if book.status != BookStatus.DONE:
            return Response({"detail": "书籍尚未生成完成"}, status=status.HTTP_400_BAD_REQUEST)

        storage = get_storage_service()
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in book.title)
        
        if download_format == "m4b":
            object_name = f"books/{pk}/audio/full/{safe_title}.m4b"
        else:
            object_name = f"books/{pk}/audio/{safe_title}_complete.zip"

        try:
            presigned_url = storage.get_presigned_url(
                bucket=settings.MINIO_BUCKET_AUDIO,
                object_name=object_name,
                expires=timedelta(hours=1),
            )
        except Exception as e:
            return Response({"detail": f"文件不存在或尚未生成: {str(e)}"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "book_id": book.id,
            "title": book.title,
            "format": download_format,
            "download_url": presigned_url,
            "total_chapters": book.total_chapters,
            "total_duration": book.total_duration,
        })

    def destroy(self, request, pk=None):
        """软删除书籍"""
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        book.deleted_at = timezone.now()
        book.save()
        return Response({"message": "删除成功"})


class ChapterViewSet(viewsets.ModelViewSet):
    """章节视图集"""
    queryset = Chapter.objects.all()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """确认开始处理（手动模式）"""
        try:
            chapter = Chapter.objects.get(id=pk)
        except Chapter.DoesNotExist:
            return Response({"detail": "章节不存在"}, status=status.HTTP_404_NOT_FOUND)

        if chapter.status != ChapterStatus.AWAITING_CONFIRM:
            return Response({"detail": f"章节状态为 {chapter.status}，无需确认"}, status=status.HTTP_400_BAD_REQUEST)

        chapter.status = ChapterStatus.PENDING
        chapter.save()
        process_chapter.delay(chapter.id)

        return Response({
            "chapter_id": chapter.id,
            "status": "processing",
            "message": f"第 {chapter.chapter_index} 章已开始处理",
        })

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """重试单个失败章节"""
        try:
            chapter = Chapter.objects.get(id=pk)
        except Chapter.DoesNotExist:
            return Response({"detail": "章节不存在"}, status=status.HTTP_404_NOT_FOUND)

        if chapter.status != ChapterStatus.FAILED:
            return Response({"detail": "章节不是 FAILED 状态"}, status=status.HTTP_400_BAD_REQUEST)

        AudioSegment.objects.filter(chapter_id=chapter.id).delete()
        chapter.status = ChapterStatus.PENDING
        chapter.error_message = None
        chapter.failed_segments = 0
        chapter.total_segments = 0
        chapter.completed_segments = 0
        chapter.save()

        process_chapter.delay(chapter.id)
        return Response({
            "chapter_id": chapter.id,
            "title": chapter.title,
            "status": "retrying",
        })


class UploadViewSet(View):
    """文件上传视图"""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """上传 EPUB 文件"""
        if 'file' not in request.FILES:
            return Response({"detail": "没有上传文件"}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES['file']
        filename = uploaded_file.name

        if not filename.lower().endswith('.epub'):
            return Response({"detail": "只支持 EPUB 格式文件"}, status=status.HTTP_400_BAD_REQUEST)

        # 读取文件内容
        content = uploaded_file.read()
        file_hash = hashlib.md5(content).hexdigest()

        # 检查是否已存在
        if Book.objects.filter(file_hash=file_hash, deleted_at__isnull=True).exists():
            return Response({"detail": "该文件已上传过"}, status=status.HTTP_400_BAD_REQUEST)

        # 创建书籍记录
        book = Book(
            title=os.path.splitext(filename)[0],
            file_name=filename,
            file_size=len(content),
            file_hash=file_hash,
            source_type=SourceType.MANUAL,
            status=BookStatus.PENDING,
        )
        book.save()

        try:
            # 上传到 MinIO
            storage = get_storage_service()
            object_name = f"epub/{book.id}/{file_hash}.epub"
            storage.upload_file(
                bucket=settings.MINIO_BUCKET_EPUB,
                object_name=object_name,
                data=content,
                content_type="application/epub+zip",
            )
            book.file_path = object_name

            # 解析 EPUB
            parser = EPUBParserService()
            result = parser.parse_bytes(content, book.id)

            book.title = result.get("title", book.title)
            book.author = result.get("author")
            book.total_chapters = result.get("chapter_count", 0)

            # 保存章节
            chapters_data = result.get("chapters", [])
            for idx, ch in enumerate(chapters_data):
                chapter_index = idx + 1
                raw_content = ch.get("content", "")
                chapter_title = ch.get("title", f"第{chapter_index}章")

                cleaned_text = clean_chapter_text(raw_content, chapter_title)

                try:
                    minio_path = storage.upload_chapter_text(
                        book_id=book.id,
                        chapter_index=chapter_index,
                        text=cleaned_text,
                    )
                except Exception as e:
                    logger.warning(f"章节文本上传 MinIO 失败: {e}")
                    minio_path = cleaned_text

                preview = cleaned_text[:500] if cleaned_text else ""
                chapter = Chapter(
                    book_id=book.id,
                    chapter_index=chapter_index,
                    title=chapter_title,
                    raw_text=preview,
                    cleaned_text=minio_path,
                )
                chapter.save()

            book.save()

            # 触发逐章处理
            chapters = Chapter.objects.filter(book_id=book.id)
            for chapter in chapters:
                process_chapter.delay(chapter.id)

            logger.info(f"上传完成，已触发 {book.total_chapters} 章逐章处理")

            return Response({
                "book_id": book.id,
                "title": book.title,
                "author": book.author,
                "total_chapters": book.total_chapters,
                "file_size": book.file_size,
            })

        except Exception as e:
            book.status = BookStatus.FAILED
            book.error_message = str(e)
            book.save()
            return Response({"detail": f"文件处理失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """获取预签名上传 URL"""
        filename = request.GET.get('filename')
        if not filename:
            return Response({"detail": "缺少 filename"}, status=status.HTTP_400_BAD_REQUEST)

        storage = get_storage_service()
        import uuid
        timestamp = timezone.now().strftime("%Y%m%d")
        object_name = f"epub/uploads/{timestamp}/{uuid.uuid4().hex}_{filename}"

        url = storage.client.presigned_put_object(
            bucket_name=settings.MINIO_BUCKET_EPUB,
            object_name=object_name,
            expires=timedelta(hours=1),
        )

        return Response({
            "upload_url": url,
            "object_name": object_name,
        })


class VoiceViewSet(viewsets.ViewSet):
    """音色管理视图集"""

    def list(self, request):
        """获取可用音色列表"""
        tts_service = MiniMaxTTSService()
        return Response(tts_service.get_available_voices())

    @action(detail=False, methods=['get'])
    def emotions(self, request):
        """获取支持的情感列表"""
        tts_service = MiniMaxTTSService()
        return Response(tts_service.get_emotion_list())

    @action(detail=False, methods=['get'])
    def roles(self, request):
        """获取角色-音色映射表"""
        mapper = VoiceMapperService()
        return Response({
            "roles": mapper.get_role_mappings(),
            "emotions": mapper.get_emotion_mappings(),
            "categories": mapper.get_role_categories(),
        })

    @action(detail=False, methods=['get'])
    def rate_limit(self, request):
        """获取 TTS 速率限制状态"""
        tts_service = MiniMaxTTSService()
        return Response(tts_service.get_rate_limit_status())

    @action(detail=False, methods=['get'])
    def analyzer_cache(self, request):
        """获取分析器缓存统计"""
        analyzer = DeepSeekAnalyzerService()
        return Response(analyzer.get_cache_stats())

    @action(detail=False, methods=['post'])
    def clear_cache(self, request):
        """清空分析器缓存"""
        analyzer = DeepSeekAnalyzerService()
        analyzer.clear_cache()
        return Response({"message": "缓存已清空"})

    @action(detail=True, methods=['get'])
    def recommend(self, request, pk=None):
        """获取书籍推荐音色配置"""
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        characters = set()
        chapters = Chapter.objects.filter(book_id=pk)
        for chapter in chapters:
            if chapter.characters:
                for char in chapter.characters:
                    characters.add(char.get("name"))

        mapper = VoiceMapperService()
        available_voices = mapper.get_available_voices()

        recommendations = []
        for char in characters:
            voice_config = mapper.get_voice_for_role(char)
            recommendations.append({
                "character": char,
                "recommended_voice": voice_config,
            })

        return Response({
            "book_id": pk,
            "characters": list(characters),
            "recommendations": recommendations,
            "available_voices": available_voices,
        })


class WatchViewSet(viewsets.ViewSet):
    """文件夹监听视图集"""

    def list(self, request):
        """获取监听状态"""
        watcher = get_watcher_service()
        status_info = watcher.get_status()

        recent_books = Book.objects.filter(
            source_type=SourceType.WATCH
        ).order_by('-created_at')[:10]

        status_info["recent_files"] = [
            {
                "id": book.id,
                "title": book.title,
                "status": book.status,
                "created_at": book.created_at.isoformat() if book.created_at else None,
            }
            for book in recent_books
        ]

        return Response(status_info)

    @action(detail=False, methods=['post'])
    def restart(self, request):
        """重启监听服务"""
        watcher = get_watcher_service()
        if watcher.is_running():
            watcher.stop()
        success = watcher.start()
        return Response({
            "success": success,
            "status": watcher.get_status(),
        })

    @action(detail=False, methods=['get'])
    def history(self, request):
        """获取监听历史"""
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        status_filter = request.GET.get('status')

        queryset = Book.objects.filter(source_type=SourceType.WATCH)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        total = queryset.count()
        books = queryset.order_by('-created_at')[page_size*(page-1):page_size*page]

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": book.id,
                    "title": book.title,
                    "file_name": book.file_name,
                    "status": book.status,
                    "total_chapters": book.total_chapters,
                    "processed_chapters": book.processed_chapters,
                    "created_at": book.created_at.isoformat() if book.created_at else None,
                    "error_message": book.error_message,
                }
                for book in books
            ],
        })


class PublishViewSet(viewsets.ViewSet):
    """发布管理视图集"""

    def list(self, request):
        """获取发布渠道列表"""
        channels = PublishChannel.objects.all()
        return Response([ch.to_dict() for ch in channels])

    def create(self, request):
        """创建发布渠道"""
        name = request.data.get('name')
        platform_type = request.data.get('platform_type')
        api_config = request.data.get('api_config', {})
        auto_publish = request.data.get('auto_publish', False)

        try:
            pt = PlatformType(platform_type)
        except ValueError:
            return Response({"detail": "无效的平台类型"}, status=status.HTTP_400_BAD_REQUEST)

        channel = PublishChannel(
            name=name,
            platform_type=pt,
            api_config=api_config,
            auto_publish=auto_publish,
        )
        channel.save()
        return Response(channel.to_dict())

    def update(self, request, pk=None):
        """更新发布渠道"""
        try:
            channel = PublishChannel.objects.get(id=pk)
        except PublishChannel.DoesNotExist:
            return Response({"detail": "渠道不存在"}, status=status.HTTP_404_NOT_FOUND)

        if 'name' in request.data:
            channel.name = request.data['name']
        if 'api_config' in request.data:
            channel.api_config = request.data['api_config']
        if 'is_enabled' in request.data:
            channel.is_enabled = request.data['is_enabled']
        if 'auto_publish' in request.data:
            channel.auto_publish = request.data['auto_publish']

        channel.save()
        return Response(channel.to_dict())

    def destroy(self, request, pk=None):
        """删除发布渠道"""
        try:
            channel = PublishChannel.objects.get(id=pk)
        except PublishChannel.DoesNotExist:
            return Response({"detail": "渠道不存在"}, status=status.HTTP_404_NOT_FOUND)

        channel.delete()
        return Response({"message": "删除成功"})

    @action(detail=True, methods=['post'])
    def publish_book(self, request, pk=None):
        """发布书籍"""
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        if book.status != BookStatus.DONE:
            return Response({"detail": "书籍尚未生成完成"}, status=status.HTTP_400_BAD_REQUEST)

        channel_ids = request.data.get('channel_ids')
        if channel_ids:
            channels = PublishChannel.objects.filter(
                id__in=channel_ids, is_enabled=True
            )
        else:
            channels = PublishChannel.objects.filter(is_enabled=True)

        if not channels.exists():
            return Response({"detail": "没有可用的发布渠道"}, status=status.HTTP_400_BAD_REQUEST)

        result = publish_book_to_all_channels.delay(pk)

        return Response({
            "book_id": pk,
            "task_id": result.id,
            "channels": [ch.id for ch in channels],
            "status": "pending",
        })

    @action(detail=True, methods=['get'])
    def publish_status(self, request, pk=None):
        """获取发布状态"""
        records = PublishRecord.objects.filter(book_id=pk)
        return Response({
            "book_id": pk,
            "records": [r.to_dict() for r in records],
        })

    @action(detail=True, methods=['get'])
    def record(self, request, pk=None):
        """获取发布记录"""
        try:
            record = PublishRecord.objects.get(id=pk)
        except PublishRecord.DoesNotExist:
            return Response({"detail": "记录不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(record.to_dict())

    @action(detail=False, methods=['get'])
    def records(self, request):
        """获取发布记录列表"""
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        status_filter = request.GET.get('status')

        queryset = PublishRecord.objects.all()

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        total = queryset.count()
        records = queryset.order_by('-created_at')[page_size*(page-1):page_size*page]

        channel_ids = list(set(r.channel_id for r in records))
        channel_map = {}
        if channel_ids:
            channels = PublishChannel.objects.filter(id__in=channel_ids)
            channel_map = {ch.id: ch.name for ch in channels}

        book_ids = list(set(r.book_id for r in records))
        book_map = {}
        if book_ids:
            books = Book.objects.filter(id__in=book_ids)
            book_map = {b.id: b.title for b in books}

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    **r.to_dict(),
                    "channel_name": channel_map.get(r.channel_id, f"渠道 #{r.channel_id}"),
                    "book_title": book_map.get(r.book_id, f"书籍 #{r.book_id}"),
                }
                for r in records
            ],
        })
