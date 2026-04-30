# ===========================================
# 音频后处理任务
# ===========================================

"""
音频后处理 Celery 任务

处理音频片段的拼接、混音、格式转换等。
"""

import logging
from typing import Dict, Any

from celery import Task

from tasks.celery_app import celery_app
from core.database import get_db_context


logger = logging.getLogger("audiobook")


class PostProcessTask(Task):
    """
    音频后处理任务基类
    """
    autoretry_for = (Exception,)
    retry_backoff = True


@celery_app.task(
    bind=True,
    base=PostProcessTask,
    name="tasks.task_postprocess.postprocess_chapter",
    queue="postprocess",
)
def postprocess_chapter(self, chapter_id: int) -> Dict[str, Any]:
    """
    后处理单个章节的音频

    包括：
    - 音频拼接
    - 音量均衡
    - 降噪处理
    - 格式转换

    Args:
        chapter_id: 章节ID

    Returns:
        dict: 后处理结果
    """
    logger.info(f"开始后处理章节音频: {chapter_id}")

    with get_db_context() as db:
        from models import Chapter, Book, ChapterStatus, BookStatus, SegmentStatus
        from datetime import datetime

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        book = db.query(Book).filter(Book.id == chapter.book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {chapter.book_id}")

        try:
            # 更新状态
            book.status = BookStatus.POST_PROCESSING
            db.commit()

            # 执行后处理
            from services.svc_audio_postprocessor import AudioPostprocessorService

            processor = AudioPostprocessorService()
            result = processor.process_chapter(chapter_id)

            # 更新章节状态
            chapter.status = ChapterStatus.DONE
            chapter.audio_file_path = result["audio_file_path"]
            chapter.audio_duration = result["duration_seconds"]
            chapter.audio_file_size = result["file_size"]
            chapter.updated_at = datetime.utcnow()
            db.commit()

            # 更新书籍进度
            book.processed_chapters = (
                db.query(Chapter)
                .filter(Chapter.book_id == book.id, Chapter.status == ChapterStatus.DONE)
                .count()
            )

            # 检查是否全部完成
            total = db.query(Chapter).filter(Chapter.book_id == book.id).count()
            if book.processed_chapters >= total:
                book.status = BookStatus.DONE

            db.commit()

            logger.info(f"章节音频后处理完成: {chapter_id}")
            return {
                "chapter_id": chapter_id,
                "audio_file_path": result["audio_file_path"],
                "duration_seconds": result["duration_seconds"],
                "success": True,
            }

        except Exception as e:
            logger.error(f"章节音频后处理失败: {chapter_id} - {e}")
            raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=PostProcessTask,
    name="tasks.task_postprocess.postprocess_book",
    queue="postprocess",
)
def postprocess_book(self, book_id: int) -> Dict[str, Any]:
    """
    后处理整本书籍的所有章节音频

    合并所有章节音频为一个完整的有声书文件。

    Args:
        book_id: 书籍ID

    Returns:
        dict: 后处理结果
    """
    logger.info(f"开始后处理书籍音频: {book_id}")

    with get_db_context() as db:
        from models import Chapter, Book, ChapterStatus
        from datetime import datetime

        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {book_id}")

        try:
            # 执行整书后处理
            from services.svc_audio_postprocessor import AudioPostprocessorService

            processor = AudioPostprocessorService()
            result = processor.process_book(book_id)

            # 更新书籍信息
            book.total_duration = result["total_duration_seconds"]
            book.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"书籍音频后处理完成: {book_id}")
            return {
                "book_id": book_id,
                "full_audio_path": result["full_audio_path"],
                "total_duration_seconds": result["total_duration_seconds"],
                "success": True,
            }

        except Exception as e:
            logger.error(f"书籍音频后处理失败: {book_id} - {e}")
            raise self.retry(exc=e)
