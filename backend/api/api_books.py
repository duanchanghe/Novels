# ===========================================
# 书籍管理 API
# ===========================================

"""
书籍管理 API 路由

提供书籍的 CRUD 操作和状态查询接口。
"""

from datetime import timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.config import settings
from models import Book, Chapter
from models.model_book import BookStatus, SourceType, GenerationMode
from models.model_chapter import ChapterStatus
from schemas import BookResponse, BookListResponse, ChapterResponse
from services.svc_minio_storage import get_storage_service
from utils.util_cache import api_cache


router = APIRouter(prefix="/books", tags=["书籍管理"])


@router.get("", response_model=BookListResponse)
async def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    获取书籍列表

    Args:
        page: 页码
        page_size: 每页数量
        status: 按状态筛选
        search: 搜索关键词（书名/作者）
        db: 数据库会话

    Returns:
        BookListResponse: 书籍列表
    """
    # 缓存键（仅对无搜索条件的结果缓存）
    use_cache = not search
    if use_cache:
        cache_key = f"books:list:{page}:{page_size}:{status}"
        cached = api_cache.get(cache_key)
        if cached is not None:
            return cached

    query = db.query(Book).filter(Book.deleted_at == None)

    # 状态筛选
    if status:
        try:
            status_enum = BookStatus(status)
            query = query.filter(Book.status == status_enum)
        except ValueError:
            pass

    # 搜索
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Book.title.ilike(search_pattern)) |
            (Book.author.ilike(search_pattern))
        )

    # 总数
    total = query.count()

    # 分页
    books = (
        query
        .order_by(Book.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 无搜索条件时缓存结果
    result = BookListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[BookResponse.model_validate(book) for book in books],
    )
    if use_cache:
        api_cache.set(cache_key, result.model_dump(mode="json"), ttl=60)
    return result


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: Session = Depends(get_db),
):
    """
    获取书籍详情

    Args:
        book_id: 书籍ID
        db: 数据库会话

    Returns:
        BookResponse: 书籍详情
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    return BookResponse.model_validate(book)


@router.get("/{book_id}/chapters")
async def get_book_chapters(
    book_id: int,
    db: Session = Depends(get_db),
):
    """
    获取书籍章节列表

    Args:
        book_id: 书籍ID
        db: 数据库会话

    Returns:
        list: 章节列表
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    chapters = (
        db.query(Chapter)
        .filter(Chapter.book_id == book_id)
        .order_by(Chapter.chapter_index)
        .all()
    )

    return [ChapterResponse.model_validate(ch) for ch in chapters]


@router.get("/{book_id}/status")
async def get_book_status(
    book_id: int,
    db: Session = Depends(get_db),
):
    """
    获取书籍处理状态

    Args:
        book_id: 书籍ID
        db: 数据库会话

    Returns:
        dict: 状态信息
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    return {
        "book_id": book.id,
        "status": book.status.value,
        "progress_percentage": book.progress_percentage,
        "total_chapters": book.total_chapters,
        "processed_chapters": book.processed_chapters,
        "error_message": book.error_message,
    }


@router.post("/{book_id}/generate")
async def trigger_generation(
    book_id: int,
    generation_mode: str = Query("auto", description="生成模式: auto=自动, manual=手动"),
    db: Session = Depends(get_db),
):
    """
    触发有声书生成

    Args:
        book_id: 书籍ID
        generation_mode: 生成模式（auto=自动模式，manual=手动模式）
        db: 数据库会话

    Returns:
        dict: 任务信息
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    if book.status == BookStatus.DONE:
        raise HTTPException(status_code=400, detail="书籍已完成生成")

    # 保存生成模式
    try:
        mode = GenerationMode(generation_mode)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的生成模式，只能是 auto 或 manual")
    book.generation_mode = mode
    db.commit()

    # 提交完整流水线 Celery 任务
    from tasks.task_pipeline import generate_audiobook_simple
    result = generate_audiobook_simple.delay(book_id)

    return {
        "book_id": book_id,
        "task_id": result.id,
        "generation_mode": mode.value,
        "status": "pending",
    }


@router.post("/{book_id}/chapters/{chapter_id}/confirm")
async def confirm_chapter(
    book_id: int,
    chapter_id: int,
    db: Session = Depends(get_db),
):
    """
    确认开始下一章（手动模式）

    当章节状态为 AWAITING_CONFIRM 时，调用此接口开始处理下一章。

    Args:
        book_id: 书籍ID
        chapter_id: 待确认的章节ID（需为 AWAITING_CONFIRM 状态）
        db: 数据库会话

    Returns:
        dict: 确认结果
    """
    from tasks.task_pipeline import process_chapter

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    # 获取待确认的章节（应该是 AWAITING_CONFIRM 状态）
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.book_id == book_id,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if chapter.status != ChapterStatus.AWAITING_CONFIRM:
        raise HTTPException(
            status_code=400,
            detail=f"章节状态为 {chapter.status.value}，无需确认"
        )

    # 重置章节状态为 PENDING
    chapter.status = ChapterStatus.PENDING
    db.commit()

    # 直接触发该章节的处理流程
    process_chapter.delay(chapter.id)

    return {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "chapter_title": chapter.title,
        "chapter_index": chapter.chapter_index,
        "status": "processing",
        "message": f"第 {chapter.chapter_index} 章已开始处理",
    }


@router.delete("/{book_id}")
async def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
):
    """
    删除书籍（软删除）

    Args:
        book_id: 书籍ID
        db: 数据库会话

    Returns:
        dict: 删除结果
    """
    from datetime import datetime

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    # 软删除
    book.deleted_at = datetime.utcnow()
    db.commit()

    return {"message": "删除成功"}


@router.get("/{book_id}/chapters/{chapter_id}/audio")
async def get_chapter_audio(
    book_id: int,
    chapter_id: int,
    db: Session = Depends(get_db),
):
    """
    获取章节音频URL

    Args:
        book_id: 书籍ID
        chapter_id: 章节ID
        db: 数据库会话

    Returns:
        dict: 音频URL和元数据
    """
    # 验证书籍存在
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    # 获取章节
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if chapter.book_id != book_id:
        raise HTTPException(status_code=400, detail="章节不属于该书籍")

    if not chapter.audio_file_path:
        raise HTTPException(status_code=404, detail="章节音频尚未生成")

    # 获取预签名URL
    storage = get_storage_service()
    presigned_url = storage.get_presigned_url(
        bucket=settings.MINIO_BUCKET_AUDIO,
        object_name=chapter.audio_file_path,
        expires=timedelta(hours=1),
    )

    return {
        "chapter_id": chapter.id,
        "audio_url": presigned_url,
        "duration": chapter.audio_duration,
        "file_size": chapter.audio_file_size,
        "format": "mp3",
    }


@router.get("/{book_id}/download")
async def download_audiobook(
    book_id: int,
    format: str = "mp3",
    db: Session = Depends(get_db),
):
    """
    获取有声书下载链接

    Args:
        book_id: 书籍ID
        format: 下载格式（mp3/m4b）
        db: 数据库会话

    Returns:
        dict: 下载URL和元数据
    """
    # 验证书籍存在
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    if book.status != BookStatus.DONE:
        raise HTTPException(status_code=400, detail="书籍尚未生成完成")

    storage = get_storage_service()

    # 确定文件路径（移除书名中的非法字符）
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in book.title)
    if format == "m4b":
        # 完整有声书 M4B 格式
        object_name = f"books/{book_id}/audio/full/{safe_title}.m4b"
    else:
        # 打包下载所有章节 MP3
        object_name = f"books/{book_id}/audio/{safe_title}_complete.zip"

    try:
        # 获取预签名URL
        presigned_url = storage.get_presigned_url(
            bucket=settings.MINIO_BUCKET_AUDIO,
            object_name=object_name,
            expires=timedelta(hours=1),
        )

        return {
            "book_id": book.id,
            "title": book.title,
            "format": format,
            "download_url": presigned_url,
            "total_chapters": book.total_chapters,
            "total_duration": book.total_duration,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"文件不存在或尚未生成: {str(e)}")


@router.post("/{book_id}/retry")
async def retry_failed_chapters(
    book_id: int,
    db: Session = Depends(get_db),
):
    """
    重试所有失败的章节

    将 FAILED 状态的章节重置为 PENDING，
    并重新触发 process_chapter。
    """
    from models.model_chapter import ChapterStatus
    from tasks.task_pipeline import process_chapter

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    failed_chapters = (
        db.query(Chapter)
        .filter(Chapter.book_id == book_id)
        .filter(Chapter.status == ChapterStatus.FAILED)
        .all()
    )
    if not failed_chapters:
        raise HTTPException(status_code=400, detail="没有失败的章节")

    retried = []
    for ch in failed_chapters:
        ch.status = ChapterStatus.PENDING
        ch.error_message = None
        ch.failed_segments = 0
        retried.append({"chapter_id": ch.id, "title": ch.title, "index": ch.chapter_index})

    # 统一提交所有更新
    db.commit()

    # 提交后触发处理任务
    for ch in failed_chapters:
        process_chapter.delay(ch.id)

    book.status = BookStatus.PENDING
    db.commit()

    return {"book_id": book_id, "retried_count": len(retried), "chapters": retried}


@router.post("/{book_id}/chapters/{chapter_id}/retry")
async def retry_single_chapter(
    book_id: int,
    chapter_id: int,
    db: Session = Depends(get_db),
):
    """
    重试单个失败的章节
    """
    from models.model_chapter import ChapterStatus
    from tasks.task_pipeline import process_chapter

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if chapter.status != ChapterStatus.FAILED:
        raise HTTPException(status_code=400, detail="章节不是 FAILED 状态，无需重试")

    from models import AudioSegment
    db.query(AudioSegment).filter(AudioSegment.chapter_id == chapter.id).delete()
    chapter.status = ChapterStatus.PENDING
    chapter.error_message = None
    chapter.failed_segments = 0
    chapter.total_segments = 0
    chapter.completed_segments = 0
    db.commit()

    process_chapter.delay(chapter.id)
    return {"book_id": book_id, "chapter_id": chapter_id, "title": chapter.title, "status": "retrying"}
