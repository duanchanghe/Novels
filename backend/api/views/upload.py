# ===========================================
# API Views - 文件上传视图
# ===========================================

"""
文件上传视图
"""

import hashlib
import logging
import os

from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from core.models import Book, Chapter, SourceType, BookStatus, ChapterStatus
from services.svc_epub_parser import EPUBParserService
from services.svc_minio_storage import get_storage_service
from services.svc_chapter_cleaner import clean_chapter_text
from tasks.task_pipeline import process_chapter

logger = logging.getLogger("audiobook")


class UploadView(APIView):
    """文件上传视图"""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """
        上传 EPUB 文件

        上传 EPUB 文件后，自动解析并创建书籍记录。
        """
        if 'file' not in request.FILES:
            return Response(
                {"detail": "没有上传文件"},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['file']
        filename = uploaded_file.name

        # 检查文件格式
        if not filename.lower().endswith('.epub'):
            return Response(
                {"detail": "只支持 EPUB 格式文件"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 读取文件内容
        content = uploaded_file.read()
        file_hash = hashlib.md5(content).hexdigest()

        # 检查是否已存在
        if Book.objects.filter(file_hash=file_hash, deleted_at__isnull=True).exists():
            return Response(
                {"detail": "该文件已上传过"},
                status=status.HTTP_400_BAD_REQUEST
            )

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

                # 清洗文本
                cleaned_text = clean_chapter_text(raw_content, chapter_title)

                # 上传到 MinIO
                try:
                    minio_path = storage.upload_chapter_text(
                        book_id=book.id,
                        chapter_index=chapter_index,
                        text=cleaned_text,
                    )
                except Exception as e:
                    logger.warning(f"章节文本上传 MinIO 失败: {e}")
                    minio_path = cleaned_text

                # 预览文本
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
            return Response(
                {"detail": f"文件处理失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PresignedUrlView(APIView):
    """预签名上传 URL 视图"""

    def get(self, request):
        """
        获取预签名上传 URL

        用于大文件直传场景。

        Query Parameters:
            filename: 文件名
        """
        import uuid
        from datetime import timedelta

        filename = request.GET.get('filename')
        if not filename:
            return Response(
                {"detail": "缺少 filename"},
                status=status.HTTP_400_BAD_REQUEST
            )

        storage = get_storage_service()
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


# 添加缺失的 import
from django.utils import timezone
