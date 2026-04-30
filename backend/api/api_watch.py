# ===========================================
# 文件夹监听 API
# ===========================================

"""
文件夹监听 API 路由

提供文件夹监听服务的管理接口。
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db, get_db_context
from services.svc_file_watcher import get_watcher_service
from models import Book, Chapter
from models.model_book import BookStatus, SourceType


router = APIRouter(prefix="/watch", tags=["文件夹监听"])


@router.get("/status")
async def get_watch_status():
    """
    获取文件夹监听状态

    Returns:
        dict: 监听状态
    """
    watcher = get_watcher_service()
    status = watcher.get_status()

    # 获取最近处理的文件
    with get_db_context() as db:
        recent_books = (
            db.query(Book)
            .filter(Book.source_type == SourceType.WATCH)
            .order_by(Book.created_at.desc())
            .limit(10)
            .all()
        )

        status["recent_files"] = [
            {
                "id": book.id,
                "title": book.title,
                "status": book.status.value,
                "created_at": book.created_at.isoformat() if book.created_at else None,
            }
            for book in recent_books
        ]

    return status


@router.post("/restart")
async def restart_watcher():
    """
    重启文件夹监听服务

    Returns:
        dict: 重启结果
    """
    watcher = get_watcher_service()

    # 停止当前服务
    if watcher.is_running():
        watcher.stop()

    # 重新启动
    success = watcher.start()

    return {
        "success": success,
        "status": watcher.get_status(),
    }


@router.get("/history")
async def get_watch_history(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
):
    """
    获取监听触发的任务历史

    Args:
        page: 页码
        page_size: 每页数量
        status: 按状态筛选

    Returns:
        dict: 历史记录
    """
    with get_db_context() as db:
        query = db.query(Book).filter(Book.source_type == SourceType.WATCH)

        if status:
            try:
                status_enum = BookStatus(status)
                query = query.filter(Book.status == status_enum)
            except ValueError:
                pass

        total = query.count()

        books = (
            query
            .order_by(Book.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": book.id,
                    "title": book.title,
                    "file_name": book.file_name,
                    "status": book.status.value,
                    "total_chapters": book.total_chapters,
                    "processed_chapters": book.processed_chapters,
                    "created_at": book.created_at.isoformat() if book.created_at else None,
                    "error_message": book.error_message,
                }
                for book in books
            ],
        }
