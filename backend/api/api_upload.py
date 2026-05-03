# ===========================================
# 文件上传 API
# ===========================================

"""
文件上传 API 路由

提供 EPUB 文件上传接口。
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from core.database import get_db
from core.config import settings
from models import Book
from models.model_book import SourceType, BookStatus
from models.model_chapter import ChapterStatus
from services.svc_epub_parser import EPUBParserService
from services.svc_minio_storage import get_storage_service
from services.svc_chapter_cleaner import clean_chapter_text
from utils.util_cache import api_cache


logger = logging.getLogger("audiobook.upload")
router = APIRouter(prefix="/upload", tags=["文件上传"])


@router.post("/epub")
async def upload_epub(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    上传 EPUB 文件

    Args:
        file: EPUB 文件
        db: 数据库会话

    Returns:
        dict: 上传结果
    """
    # 验证文件类型
    if not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="只支持 EPUB 格式文件")

    # 读取文件内容
    content = await file.read()

    # 计算文件哈希
    file_hash = hashlib.md5(content).hexdigest()

    # 检查是否已存在
    existing = (
        db.query(Book)
        .filter(Book.file_hash == file_hash)
        .filter(Book.deleted_at == None)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="该文件已上传过",
        )

    # 创建书籍记录
    book = Book(
        title=os.path.splitext(file.filename)[0],
        file_name=file.filename,
        file_size=len(content),
        file_hash=file_hash,
        source_type=SourceType.MANUAL,
        status=BookStatus.PENDING,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

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

        # 保存章节+上传清洗文本到 MinIO
        from models import Chapter
        from services.svc_chapter_cleaner import clean_chapter_text

        chapters_data = result.get("chapters", [])
        for idx, ch in enumerate(chapters_data):
            chapter_index = idx + 1
            raw_content = ch.get("content", "")
            chapter_title = ch.get("title", f"第{chapter_index}章")

            # 清洗：只保留正文，去除 HTML/版权等
            cleaned_text = clean_chapter_text(raw_content, chapter_title)

            # 上传清洗后的正文到 MinIO
            try:
                minio_path = storage.upload_chapter_text(
                    book_id=book.id,
                    chapter_index=chapter_index,
                    text=cleaned_text,
                )
            except Exception as e:
                logger.warning(
                    f"章节文本上传 MinIO 失败: {e}"
                )
                minio_path = cleaned_text  # 降级：存文本

            # DB 只存预览（前500字符）+ MinIO 路径
            preview = cleaned_text[:500] if cleaned_text else ""

            chapter = Chapter(
                book_id=book.id,
                chapter_index=chapter_index,
                title=chapter_title,
                raw_text=preview,
                cleaned_text=minio_path,
            )
            db.add(chapter)

        db.commit()

        # ── 事件驱动：清理文本就绪 → 触发逐章处理 ──
        from tasks.task_pipeline import process_chapter
        for chapter in db.query(Chapter).filter(Chapter.book_id == book.id).all():
            process_chapter.delay(chapter.id)
        # 上传成功后清除书籍列表缓存
        api_cache.invalidate_pattern("books:list:*")

        logger.info(
            f"上传完成，已触发 {book.total_chapters} 章逐章处理"
        )

        return {
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "total_chapters": book.total_chapters,
            "file_size": book.file_size,
        }

    except Exception as e:
        # 解析失败，标记为失败
        book.status = BookStatus.FAILED
        book.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")


@router.get("/presigned-url")
async def get_upload_url(
    filename: str,
    db: Session = Depends(get_db),
):
    """
    获取预签名上传 URL（用于大文件分片上传）

    Args:
        filename: 文件名
        db: 数据库会话

    Returns:
        dict: 预签名 URL
    """
    storage = get_storage_service()

    # 生成唯一对象名
    import uuid
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    object_name = f"epub/uploads/{timestamp}/{uuid.uuid4().hex}_{filename}"

    # 生成预签名 PUT URL
    url = storage.client.presigned_put_object(
        bucket_name=settings.MINIO_BUCKET_EPUB,
        object_name=object_name,
        expires=timedelta(hours=1),
    )

    return {
        "upload_url": url,
        "object_name": object_name,
    }
