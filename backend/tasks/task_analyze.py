# ===========================================
# DeepSeek 分析任务
# ===========================================

"""
DeepSeek 文本分析 Celery 任务

处理书籍章节的 AI 分析，包括：
- 角色识别
- 情感标注
- 文本标准化
- 段落拆分
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

from celery import Task
from celery.exceptions import MaxRetriesExceededError

from tasks.celery_app import celery_app
from core.database import get_db_context
from core.exceptions import DeepSeekApiError


logger = logging.getLogger("audiobook")


class AnalyzeTask(Task):
    """
    DeepSeek 分析任务基类

    提供重试逻辑和错误处理。
    """

    autoretry_for = (DeepSeekApiError, ConnectionError, TimeoutError)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=AnalyzeTask,
    name="tasks.task_analyze.analyze_chapter",
    queue="analyze",
    max_retries=3,
)
def analyze_chapter(self, chapter_id: int) -> Dict[str, Any]:
    """
    分析单个章节

    使用 DeepSeek 对章节文本进行分析，提取：
    - 角色列表
    - 情感标注
    - 朗读参数建议

    Args:
        chapter_id: 章节ID

    Returns:
        dict: 分析结果
    """
    logger.info(f"开始分析章节: {chapter_id}")

    with get_db_context() as db:
        from models import Chapter, Book
        from models.model_book import BookStatus
        from models.model_chapter import ChapterStatus

        # 获取章节
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        # 获取书籍
        book = db.query(Book).filter(Book.id == chapter.book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {chapter.book_id}")

        try:
            # 更新书籍状态
            book.status = BookStatus.ANALYZING
            book.updated_at = datetime.utcnow()

            # 更新章节状态
            chapter.status = ChapterStatus.ANALYZING
            db.commit()

            # 执行分析（具体逻辑在服务层实现）
            from services.svc_deepseek_analyzer import DeepSeekAnalyzerService

            analyzer = DeepSeekAnalyzerService()
            result = analyzer.analyze_chapter(chapter.cleaned_text or chapter.raw_text)

            # 更新章节分析结果
            chapter.analysis_result = result
            chapter.characters = result.get("characters", [])
            chapter.status = ChapterStatus.ANALYZED
            db.commit()

            logger.info(f"章节分析完成: {chapter_id}, 识别角色: {len(chapter.characters)}")
            return {
                "chapter_id": chapter_id,
                "characters": chapter.characters,
                "success": True,
            }

        except Exception as e:
            logger.error(f"章节分析失败: {chapter_id} - {e}")
            chapter.status = ChapterStatus.FAILED
            chapter.error_message = str(e)
            db.commit()

            try:
                raise self.retry(exc=e)
            except MaxRetriesExceededError:
                raise DeepSeekApiError(f"章节分析重试次数耗尽: {chapter_id}")


@celery_app.task(
    bind=True,
    base=AnalyzeTask,
    name="tasks.task_analyze.analyze_book",
    queue="analyze",
)
def analyze_book(self, book_id: int) -> Dict[str, Any]:
    """
    分析整本书籍的所有章节

    串行分析每个章节，或可配置为并行分析。

    Args:
        book_id: 书籍ID

    Returns:
        dict: 分析结果汇总
    """
    logger.info(f"开始分析书籍: {book_id}")

    with get_db_context() as db:
        from models import Chapter, Book
        from models.model_book import BookStatus
        from models.model_chapter import ChapterStatus

        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {book_id}")

        chapters = (
            db.query(Chapter)
            .filter(Chapter.book_id == book_id)
            .filter(Chapter.status == ChapterStatus.PENDING)
            .order_by(Chapter.chapter_index)
            .all()
        )

        results = []
        for chapter in chapters:
            try:
                result = analyze_chapter.delay(chapter.id)
                results.append({"chapter_id": chapter.id, "task_id": result.id})
            except Exception as e:
                logger.error(f"提交章节分析任务失败: {chapter.id} - {e}")
                results.append({"chapter_id": chapter.id, "error": str(e)})

        return {
            "book_id": book_id,
            "total_chapters": len(chapters),
            "submitted_tasks": results,
        }
