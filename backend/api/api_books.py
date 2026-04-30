# ===========================================
# 书籍管理 API
# ===========================================

"""
书籍管理 API 路由

提供书籍的 CRUD 操作和状态查询接口。
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from models import Book, Chapter
from models.model_book import BookStatus
from models.model_chapter import ChapterStatus
from schemas import BookResponse, BookListResponse, ChapterResponse


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

    return BookListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[BookResponse.model_validate(book) for book in books],
    )


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
    db: Session = Depends(get_db),
):
    """
    触发有声书生成

    Args:
        book_id: 书籍ID
        db: 数据库会话

    Returns:
        dict: 任务信息
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    if book.status == BookStatus.DONE:
        raise HTTPException(status_code=400, detail="书籍已完成生成")

    # 提交 Celery 任务
    from tasks.task_analyze import analyze_book
    result = analyze_book.delay(book_id)

    return {
        "book_id": book_id,
        "task_id": result.id,
        "status": "pending",
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
