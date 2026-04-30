# ===========================================
# 文件夹监听任务
# ===========================================

"""
文件夹监听 Celery 任务

提供定时扫描和健康检查功能。
"""

import logging
import os
from typing import Dict, Any, List

from celery import Task

from tasks.celery_app import celery_app
from core.config import settings
from core.database import get_db_context


logger = logging.getLogger("audiobook")


class WatchTask(Task):
    """
    监听任务基类
    """
    autoretry_for = (Exception,)
    retry_backoff = True


@celery_app.task(
    bind=True,
    base=WatchTask,
    name="tasks.task_watch.scan_incoming_directory",
    queue="watch",
)
def scan_incoming_directory(self) -> Dict[str, Any]:
    """
    扫描 incoming 目录

    检查新放入的 EPUB 文件并触发处理任务。
    作为 watchdog 的兜底方案。

    Returns:
        dict: 扫描结果
    """
    if not settings.WATCH_ENABLED:
        logger.debug("文件夹监听已禁用，跳过扫描")
        return {"enabled": False, "files_found": 0}

    watch_dir = settings.WATCH_DIR
    if not os.path.exists(watch_dir):
        logger.warning(f"监听目录不存在: {watch_dir}")
        return {"enabled": True, "files_found": 0, "error": "目录不存在"}

    logger.info(f"开始扫描监听目录: {watch_dir}")

    with get_db_context() as db:
        from models import Book, SourceType, BookStatus
        import hashlib

        processed_files = []
        errors = []

        try:
            for filename in os.listdir(watch_dir):
                if not filename.lower().endswith(".epub"):
                    continue

                file_path = os.path.join(watch_dir, filename)

                # 跳过临时文件
                if filename.endswith(".part") or filename.endswith(".tmp"):
                    continue

                # 跳过目录
                if not os.path.isfile(file_path):
                    continue

                try:
                    # 计算文件哈希
                    with open(file_path, "rb") as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()

                    # 检查是否已处理
                    existing = (
                        db.query(Book)
                        .filter(Book.file_hash == file_hash)
                        .filter(Book.status != BookStatus.FAILED)
                        .first()
                    )

                    if existing:
                        logger.info(f"文件已处理过，跳过: {filename} (hash: {file_hash})")
                        continue

                    # 触发处理任务
                    logger.info(f"发现新 EPUB 文件: {filename}")
                    result = process_new_epub.delay(file_path, file_hash)
                    processed_files.append({
                        "filename": filename,
                        "hash": file_hash,
                        "task_id": result.id,
                    })

                except Exception as e:
                    logger.error(f"处理文件失败: {filename} - {e}")
                    errors.append({"filename": filename, "error": str(e)})

            return {
                "enabled": True,
                "scan_dir": watch_dir,
                "files_found": len(processed_files),
                "processed_files": processed_files,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"扫描目录失败: {e}")
            raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=WatchTask,
    name="tasks.task_watch.process_new_epub",
    queue="watch",
)
def process_new_epub(self, file_path: str, file_hash: str = None) -> Dict[str, Any]:
    """
    处理新发现的 EPUB 文件

    Args:
        file_path: 文件路径
        file_hash: 文件哈希（可选）

    Returns:
        dict: 处理结果
    """
    import hashlib
    from datetime import datetime

    logger.info(f"开始处理新 EPUB 文件: {file_path}")

    with get_db_context() as db:
        from models import Book, SourceType, BookStatus
        from services.svc_epub_parser import EPUBParserService

        try:
            # 计算文件哈希
            if not file_hash:
                with open(file_path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()

            # 创建书籍记录
            book = Book(
                title=os.path.splitext(os.path.basename(file_path))[0],
                file_name=os.path.basename(file_path),
                file_size=os.path.getsize(file_path),
                file_hash=file_hash,
                source_type=SourceType.WATCH,
                watch_path=file_path,
                status=BookStatus.PENDING,
            )
            db.add(book)
            db.commit()
            db.refresh(book)

            # 上传到 MinIO
            from services.svc_minio_storage import get_storage_service
            storage = get_storage_service()

            with open(file_path, "rb") as f:
                file_data = f.read()

            object_name = f"epub/{book.id}/{file_hash}.epub"
            storage.upload_file(
                bucket=settings.MINIO_BUCKET_EPUB,
                object_name=object_name,
                data=file_data,
                content_type="application/epub+zip",
            )
            book.file_path = object_name

            # 解析 EPUB
            parser = EPUBParserService()
            result = parser.parse_file(file_path, book.id)

            book.title = result.get("title", book.title)
            book.author = result.get("author")
            book.total_chapters = result.get("chapter_count", 0)
            book.status = BookStatus.PENDING
            db.commit()

            logger.info(f"EPUB 文件处理完成: book_id={book.id}, chapters={book.total_chapters}")
            return {
                "book_id": book.id,
                "title": book.title,
                "chapter_count": book.total_chapters,
                "success": True,
            }

        except Exception as e:
            logger.error(f"EPUB 文件处理失败: {file_path} - {e}")

            if "book" in locals():
                book.status = BookStatus.FAILED
                book.error_message = str(e)
                db.commit()

            raise


@celery_app.task(
    bind=True,
    base=WatchTask,
    name="tasks.task_watch.check_watcher_health",
    queue="watch",
)
def check_watcher_health(self) -> Dict[str, Any]:
    """
    检查监听服务健康状态

    Returns:
        dict: 健康检查结果
    """
    logger.debug("开始检查监听服务健康状态")

    with get_db_context() as db:
        from models import Book, BookStatus, SourceType
        from datetime import datetime, timedelta

        try:
            # 检查是否有处理中的任务
            pending_count = (
                db.query(Book)
                .filter(Book.status.in_([
                    BookStatus.ANALYZING,
                    BookStatus.SYNTHESIZING,
                    BookStatus.POST_PROCESSING,
                ]))
                .count()
            )

            # 检查最近是否有新文件
            recent_cutoff = datetime.utcnow() - timedelta(hours=1)
            recent_files = (
                db.query(Book)
                .filter(Book.source_type == SourceType.WATCH)
                .filter(Book.created_at >= recent_cutoff)
                .count()
            )

            # 检查失败的书籍
            failed_count = (
                db.query(Book)
                .filter(Book.status == BookStatus.FAILED)
                .filter(Book.created_at >= recent_cutoff)
                .count()
            )

            health_status = "healthy"
            if failed_count > 3:
                health_status = "degraded"
                logger.warning(f"检测到 {failed_count} 个失败任务，服务状态降级")

            return {
                "status": health_status,
                "pending_tasks": pending_count,
                "recent_files": recent_files,
                "failed_count": failed_count,
                "watch_enabled": settings.WATCH_ENABLED,
                "watch_dir": settings.WATCH_DIR,
            }

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }
