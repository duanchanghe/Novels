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

from tasks.celery_app import app as celery_app
from core.database import get_db_context
from core.exceptions import DeepSeekAPIError as DeepSeekApiError


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
        from core.models import Chapter, Book
        from core.models.book import BookStatus
        from core.models.chapter import ChapterStatus

        # 获取章节
        chapter = db.query(Chapter).filter(id=chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        # 获取书籍
        book = db.query(Book).filter(id=chapter.book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {chapter.book_id}")

        try:
            # 更新书籍状态
            book.status = BookStatus.ANALYZING
            book.updated_at = datetime.utcnow()

            # 更新章节状态
            chapter.status = ChapterStatus.ANALYZING
            db.commit()

            # ── 读取章节文本（优先 MinIO，回退 DB） ──
            from services.svc_minio_storage import get_storage_service
            storage = get_storage_service()
            text = ""

            # 策略1: cleaned_text 是 MinIO 路径 → 从 MinIO 读取
            if chapter.cleaned_text and chapter.cleaned_text.startswith("chapters/"):
                try:
                    text = storage.download_chapter_text(
                        book_id=chapter.book_id,
                        chapter_index=chapter.chapter_index,
                    )
                    logger.debug(
                        f"[Chapter {chapter_id}] 从 MinIO 读取文本: {len(text)} 字符"
                    )
                except Exception as e:
                    logger.warning(
                        f"[Chapter {chapter_id}] MinIO 读取失败，回退到 DB: {e}"
                    )

            # 策略2: cleaned_text 是实际文本内容（非路径）→ 直接使用
            if not text and chapter.cleaned_text:
                if not chapter.cleaned_text.startswith("chapters/"):
                    text = chapter.cleaned_text
                    logger.debug(
                        f"[Chapter {chapter_id}] 使用 DB cleaned_text: {len(text)} 字符"
                    )

            # 策略3: 回退到 raw_text
            if not text and chapter.raw_text:
                text = chapter.raw_text
                logger.debug(
                    f"[Chapter {chapter_id}] 使用 DB raw_text: {len(text)} 字符"
                )

            if not text or len(text.strip()) < 10:
                logger.warning(f"[Chapter {chapter_id}] 文本内容过短，跳过分析")
                chapter.status = ChapterStatus.ANALYZED
                chapter.analysis_result = {"sentences": [], "characters": []}
                db.commit()
                return {
                    "chapter_id": chapter_id,
                    "warning": "文本内容过短",
                    "success": True,
                }

            # 执行分析（具体逻辑在服务层实现）
            from services.svc_deepseek_analyzer import DeepSeekAnalyzerService

            analyzer = DeepSeekAnalyzerService()
            result = analyzer.analyze_chapter(text)

            # ── 保存句子到 Sentence 模型 ──
            from core.models.sentence import Sentence
            sentences_data = result.get("sentences", [])
            Sentence.save_chapter_sentences(chapter, sentences_data)
            logger.info(
                f"[Chapter {chapter_id}] 已保存 {len(sentences_data)} 个句子到 Sentence 模型"
            )

            # ── 保存角色到 Character 模型 ──
            from core.models.character import Character
            characters_data = result.get("characters", [])
            Character.save_chapter_characters(chapter, characters_data)
            logger.info(
                f"[Chapter {chapter_id}] 已保存 {len(characters_data)} 个角色"
            )

            # 更新章节分析结果
            chapter.analysis_result = result
            chapter.characters = result.get("characters", [])
            chapter.status = ChapterStatus.ANALYZED
            db.commit()

            logger.info(f"章节分析完成: {chapter_id}, 识别角色: {len(chapter.characters)}, 句子数: {len(sentences_data)}")
            return {
                "chapter_id": chapter_id,
                "characters": chapter.characters,
                "sentences_count": len(sentences_data),
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
        from core.models import Chapter, Book
        from core.models.book import BookStatus
        from core.models.chapter import ChapterStatus

        book = db.query(Book).filter(id=book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {book_id}")

        chapters = (
            db.query(Chapter)
            .filter(book_id=book_id)
            .filter(status=ChapterStatus.PENDING)
            .order_by("chapter_index")
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
