# ===========================================
# API Views - 书籍相关视图
# ===========================================

"""
书籍管理视图
"""

import logging
from typing import Optional

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from core.models import Book, Chapter, BookStatus, ChapterStatus, SourceType, GenerationMode
from tasks.task_pipeline import generate_audiobook_simple, process_chapter
from api.serializers import (
    BookListSerializer,
    BookDetailSerializer,
)

logger = logging.getLogger("audiobook")


class BookListView(APIView):
    """书籍列表视图"""

    def get(self, request):
        """
        获取书籍列表

        Query Parameters:
            page: 页码 (default: 1)
            page_size: 每页数量 (default: 20)
            status: 状态过滤
            search: 搜索关键词
        """
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        status_filter = request.GET.get('status')
        search = request.GET.get('search')

        queryset = Book.objects.filter(deleted_at__isnull=True)

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(
                title__icontains=search
            ) | queryset.filter(author__icontains=search)

        total = queryset.count()
        books = queryset.order_by('-created_at')[page_size*(page-1):page_size*page]

        serializer = BookListSerializer(books, many=True)
        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': serializer.data
        })


class BookDetailView(APIView):
    """书籍详情视图"""

    def get(self, request, pk):
        """
        获取书籍详情

        Path Parameters:
            pk: 书籍ID
        """
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BookDetailSerializer(book)
        return Response(serializer.data)


class BookChaptersView(APIView):
    """书籍章节视图"""

    def get(self, request, pk):
        """
        获取书籍章节列表

        Path Parameters:
            pk: 书籍ID
        """
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        chapters = Chapter.objects.filter(book_id=pk).order_by('chapter_index')
        from api.serializers import ChapterListSerializer
        serializer = ChapterListSerializer(chapters, many=True)
        return Response(serializer.data)


class BookStatusView(APIView):
    """书籍状态视图"""

    def get(self, request, pk):
        """
        获取书籍处理状态

        Path Parameters:
            pk: 书籍ID
        """
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "book_id": book.id,
            "status": book.status,
            "progress_percentage": book.progress_percentage,
            "total_chapters": book.total_chapters,
            "processed_chapters": book.processed_chapters,
            "error_message": book.error_message,
        })


class BookGenerateView(APIView):
    """书籍生成视图"""

    def post(self, request, pk):
        """
        触发有声书生成

        Path Parameters:
            pk: 书籍ID

        Query Parameters:
            generation_mode: 生成模式 (auto/manual)
        """
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        if book.status == BookStatus.DONE:
            return Response(
                {"detail": "书籍已完成生成"},
                status=status.HTTP_400_BAD_REQUEST
            )

        generation_mode = request.GET.get('generation_mode', 'auto')
        try:
            mode = GenerationMode(generation_mode)
        except ValueError:
            return Response(
                {"detail": "无效的生成模式"},
                status=status.HTTP_400_BAD_REQUEST
            )

        book.generation_mode = mode
        book.save()

        result = generate_audiobook_simple.delay(book.id)

        return Response({
            "book_id": book.id,
            "task_id": result.id,
            "generation_mode": mode,
            "status": "pending",
        })


class BookRetryView(APIView):
    """书籍重试视图"""

    def post(self, request, pk):
        """
        重试失败的章节

        Path Parameters:
            pk: 书籍ID
        """
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        failed_chapters = Chapter.objects.filter(
            book_id=pk, status=ChapterStatus.FAILED
        )
        if not failed_chapters.exists():
            return Response(
                {"detail": "没有失败的章节"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 重置失败章节状态
        for ch in failed_chapters:
            ch.status = ChapterStatus.PENDING
            ch.error_message = None
            ch.failed_segments = 0

        Chapter.objects.bulk_update(failed_chapters, ["status", "error_message", "failed_segments"])
        Book.objects.filter(id=pk).update(status=BookStatus.PENDING)

        # 使用新流程：先全部分析 → 统一角色 → 再逐章生成
        from tasks.task_pipeline import analyze_all_chapters
        analyze_all_chapters.delay(pk)

        retried = [
            {"chapter_id": ch.id, "title": ch.title, "index": ch.chapter_index}
            for ch in failed_chapters
        ]

        return Response({
            "book_id": pk,
            "retried_count": len(retried),
            "chapters": retried
        })


class BookAudioView(APIView):
    """书籍音频视图"""

    def get(self, request, pk):
        """
        获取章节音频URL

        Path Parameters:
            pk: 书籍ID

        Query Parameters:
            chapter_id: 章节ID
        """
        chapter_id = request.GET.get('chapter_id')
        if not chapter_id:
            return Response(
                {"detail": "缺少 chapter_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            chapter = Chapter.objects.get(id=chapter_id, book_id=pk)
        except Chapter.DoesNotExist:
            return Response(
                {"detail": "章节不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not chapter.audio_file_path:
            return Response(
                {"detail": "章节音频尚未生成"},
                status=status.HTTP_404_NOT_FOUND
            )

        from datetime import timedelta
        from services.svc_minio_storage import get_storage_service

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


class BookDownloadView(APIView):
    """书籍下载视图"""

    def get(self, request, pk):
        """
        获取有声书下载链接

        Path Parameters:
            pk: 书籍ID

        Query Parameters:
            format: 下载格式 (mp3/m4b)
        """
        download_format = request.GET.get('format', 'mp3')

        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        if book.status != BookStatus.DONE:
            return Response(
                {"detail": "书籍尚未生成完成"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from datetime import timedelta
        from services.svc_minio_storage import get_storage_service

        storage = get_storage_service()
        safe_title = "".join(
            c if c.isalnum() or c in " -_" else "_"
            for c in book.title
        )

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
            return Response(
                {"detail": f"文件不存在或尚未生成: {str(e)}"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "book_id": book.id,
            "title": book.title,
            "format": download_format,
            "download_url": presigned_url,
            "total_chapters": book.total_chapters,
            "total_duration": book.total_duration,
        })


class BookSubtitleView(APIView):
    """章节字幕下载视图"""

    def get(self, request, pk):
        """
        获取章节字幕

        Path Parameters:
            pk: 书籍ID
        Query Parameters:
            chapter_id: 章节ID（可选，不传则返回所有章节字幕列表）
        """
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        chapter_id = request.GET.get('chapter_id')
        chapters_query = Chapter.objects.filter(book_id=pk).order_by('chapter_index')

        if chapter_id:
            chapters_query = chapters_query.filter(id=chapter_id)

        result = []
        for ch in chapters_query:
            subtitle_info = {
                "chapter_id": ch.id,
                "chapter_index": ch.chapter_index,
                "title": ch.title,
                "subtitle_url": ch.subtitle_url,
            }
            if ch.audio_duration:
                subtitle_info["duration_seconds"] = ch.audio_duration
            result.append(subtitle_info)

        return Response(result)


class BookDeleteView(APIView):
    """书籍删除视图"""

    def delete(self, request, pk):
        """
        软删除书籍

        Path Parameters:
            pk: 书籍ID
        """
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        book.deleted_at = timezone.now()
        book.save()
        return Response({"message": "删除成功"})


class BookStopAllView(APIView):
    """停止所有有声书制作视图"""

    def post(self, request):
        """
        停止所有正在处理的有声书制作

        查找所有处于处理中的书籍，将其状态标记为 FAILED，
        相关章节也一并标记为 FAILED，并尝试撤销 Celery 任务。
        """
        processing_statuses = [
            BookStatus.PENDING,
            BookStatus.ANALYZING,
            BookStatus.SYNTHESIZING,
            BookStatus.POST_PROCESSING,
            BookStatus.PUBLISHING,
        ]

        books = Book.objects.filter(
            deleted_at__isnull=True,
            status__in=processing_statuses,
        )

        total = books.count()
        stopped = []
        errors = []

        for book in books:
            try:
                # 撤销 Celery 任务
                try:
                    from tasks.celery_app import app as celery_app
                    inspector = celery_app.control.inspect()

                    # 收集所有相关任务 ID
                    task_ids = []
                    for worker_tasks in [inspector.active() or {}, inspector.reserved() or {}]:
                        for worker, tasks in worker_tasks.items():
                            for t in tasks:
                                t_name = t.get("name", "")
                                t_args = t.get("args", [])
                                if ("generate_audiobook" in t_name or
                                    "process_chapter" in t_name or
                                    "publish_book" in t_name) and (
                                    str(book.id) in str(t_args)
                                ):
                                    task_ids.append(t["id"])

                    # 撤销任务
                    for tid in task_ids:
                        celery_app.control.revoke(tid, terminate=True)
                        logger.info(f"[StopAll] 已撤销任务 {tid}")
                except Exception as e:
                    logger.warning(f"[StopAll] 撤销任务失败: {e}")

                # 更新所有处理中的章节
                from core.models import Chapter, ChapterStatus
                chapter_processing = [
                    ChapterStatus.PENDING,
                    ChapterStatus.ANALYZING,
                    ChapterStatus.ANALYZED,
                    ChapterStatus.SYNTHESIZING,
                    ChapterStatus.AWAITING_CONFIRM,
                ]

                updated_chapters = Chapter.objects.filter(
                    book_id=book.id,
                    status__in=chapter_processing,
                ).update(
                    status=ChapterStatus.FAILED,
                    error_message="用户主动取消 - 已停止所有制作",
                )

                # 更新书籍状态
                old_status = book.status
                book.status = BookStatus.FAILED
                book.error_message = "用户主动取消 - 已停止所有制作"
                book.save()

                stopped.append({
                    "book_id": book.id,
                    "title": book.title,
                    "old_status": old_status,
                    "chapters_stopped": updated_chapters,
                })
                logger.info(
                    f"[StopAll] 已停止书籍 #{book.id} '{book.title}' "
                    f"(原状态: {old_status}, 停止章节: {updated_chapters})"
                )
            except Exception as e:
                logger.error(f"[StopAll] 停止书籍 #{book.id} 失败: {e}")
                errors.append({"book_id": book.id, "error": str(e)})

        return Response({
            "success": True,
            "message": f"已停止 {len(stopped)} 本书籍的制作",
            "total_stopped": len(stopped),
            "total_errors": len(errors),
            "stopped_books": stopped,
            "errors": errors if errors else None,
        })
