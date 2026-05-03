# ===========================================
# AI 有声书工坊 - 任务编排层
# ===========================================

"""
任务编排器

串联整个有声书生成流程的核心编排层：
1. EPUB 解析 → 2. 文本预处理 → 3. DeepSeek 分析 → 4. 片段创建 → 5. TTS 合成 → 6. 音频后处理 → 7. 发布

提供任务状态追踪、进度回调、错误处理和重试机制。
"""

import logging
import hashlib
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from celery import Task, chain, group, chord
from celery.exceptions import MaxRetriesExceededError

from tasks.celery_app import celery_app
from core.database import get_db_context
from core.exceptions import (
    EPUBParseError,
    DeepSeekApiError,
    MiniMaxApiError,
    AudioProcessingError,
)


logger = logging.getLogger("audiobook.pipeline")


class PipelineStage(str, Enum):
    """流水线阶段枚举"""
    PARSING = "parsing"              # EPUB 解析
    PREPROCESSING = "preprocessing"  # 文本预处理
    ANALYZING = "analyzing"          # DeepSeek 分析
    CREATING_SEGMENTS = "creating_segments"  # 创建音频片段
    SYNTHESIZING = "synthesizing"    # TTS 合成
    POSTPROCESSING = "postprocessing"  # 音频后处理
    PUBLISHING = "publishing"         # 自动发布
    DONE = "done"                    # 完成
    FAILED = "failed"                # 失败


@dataclass
class PipelineContext:
    """
    流水线执行上下文

    贯穿整个流水线的状态容器，包含：
    - 书籍/章节基本信息
    - 各阶段执行结果
    - 错误信息和重试状态
    """
    book_id: int
    chapter_ids: List[int] = field(default_factory=list)
    current_stage: PipelineStage = PipelineStage.PARSING

    # 执行结果存储
    parse_result: Optional[Dict[str, Any]] = None
    preprocess_result: Optional[Dict[str, Any]] = None
    analysis_results: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    # 错误处理
    errors: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0

    # 统计信息
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 回调函数
    progress_callback: Optional[Callable] = None

    def add_error(self, stage: PipelineStage, error: Exception, context: Dict = None):
        """记录错误"""
        self.errors.append({
            "stage": stage.value,
            "error": str(error),
            "error_type": type(error).__name__,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
        })

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "book_id": self.book_id,
            "chapter_ids": self.chapter_ids,
            "current_stage": self.current_stage.value,
            "errors": self.errors,
            "retry_count": self.retry_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class PipelineTask(Task):
    """
    流水线任务基类

    提供统一的错误处理、重试和进度追踪机制。
    """

    autoretry_for = (
        EPUBParseError,
        DeepSeekApiError,
        MiniMaxApiError,
        AudioProcessingError,
        ConnectionError,
        TimeoutError,
    )
    retry_backoff = True
    retry_backoff_max = 120            # 最大退避时间（秒）
    retry_jitter = True
    max_retries = 8                    # 最多重试8次
    default_retry_delay = 10           # 初始重试延迟10秒

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败回调"""
        logger.error(f"流水线任务失败: task_id={task_id}, error={exc}")
        book_id = kwargs.get("book_id") or (args[0] if args else None)
        if book_id:
            _update_book_error(book_id, str(exc))

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """任务重试回调"""
        logger.warning(f"流水线任务重试: task_id={task_id}, error={exc}")
        book_id = kwargs.get("book_id") or (args[0] if args else None)
        if book_id:
            _update_book_progress(book_id, f"重试中: {exc}")


def _update_book_progress(book_id: int, message: str = None):
    """更新书籍处理进度"""
    try:
        with get_db_context() as db:
            from models import Book
            from models.model_book import BookStatus

            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                book.updated_at = datetime.utcnow()
                if message:
                    logger.info(f"[Book {book_id}] {message}")
                db.commit()
    except Exception as e:
        logger.error(f"更新书籍进度失败: {e}")


def _update_book_error(book_id: int, error_message: str):
    """更新书籍错误状态"""
    try:
        with get_db_context() as db:
            from models import Book
            from models.model_book import BookStatus

            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                book.status = BookStatus.FAILED
                book.error_message = error_message
                book.updated_at = datetime.utcnow()
                db.commit()
                logger.error(f"[Book {book_id}] 状态更新为 FAILED: {error_message}")
    except Exception as e:
        logger.error(f"更新书籍错误状态失败: {e}")


# ===========================================
# 阶段一：EPUB 解析
# ===========================================

@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.parse_epub",
    queue="pipeline",
    max_retries=3,
)
def parse_epub(self, book_id: int) -> Dict[str, Any]:
    """
    解析 EPUB 文件

    阶段一：解析 EPUB 文件，提取元数据和章节内容
    支持从 MinIO 或本地路径读取文件。

    Args:
        book_id: 书籍ID

    Returns:
        dict: 解析结果
    """
    logger.info(f"[Book {book_id}] 阶段一：开始解析 EPUB")

    import tempfile
    import shutil

    with get_db_context() as db:
        from models import Book, Chapter
        from models.model_book import BookStatus
        from models.model_chapter import ChapterStatus
        from services.svc_epub_parser import EPUBParserService
        from services.svc_chapter_cleaner import clean_chapter_text, clean_chapter_with_report
        from services.svc_minio_storage import get_storage_service

        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {book_id}")

        # ── 检查章节是否已存在（上传时可能已解析） ──
        existing_chapters = (
            db.query(Chapter)
            .filter(Chapter.book_id == book_id)
            .count()
        )
        if existing_chapters > 0:
            chapters = db.query(Chapter).filter(Chapter.book_id == book_id).all()
            chapter_ids = [ch.id for ch in chapters]
            logger.info(
                f"[Book {book_id}] 章节已存在 ({existing_chapters} 章)，跳过解析"
            )

            # 检查并确保每章的清洗文本已上传到 MinIO
            storage = get_storage_service()
            for ch in chapters:
                # 如果 cleaned_text 是文本内容而非路径，上传到 MinIO
                if ch.cleaned_text and not ch.cleaned_text.startswith("chapters/"):
                    try:
                        path = storage.upload_chapter_text(
                            book_id=book_id,
                            chapter_index=ch.chapter_index,
                            text=ch.cleaned_text,
                        )
                        ch.cleaned_text = path
                        logger.debug(
                            f"[Chapter {ch.id}] 清洗文本已上传 MinIO: {path}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"[Chapter {ch.id}] MinIO 上传失败: {e}"
                        )
            db.commit()

            return {
                "book_id": book_id,
                "chapter_ids": chapter_ids,
                "chapter_count": len(chapter_ids),
                "stage": PipelineStage.PARSING.value,
                "success": True,
                "skipped": True,
            }

        try:
            # 更新状态
            book.status = BookStatus.PENDING
            book.updated_at = datetime.utcnow()
            db.commit()

            # 获取文件内容
            file_content = None
            file_path = book.file_path
            storage = None

            if file_path and file_path.startswith("epub/"):
                storage = get_storage_service()
                try:
                    file_content = storage.download_file(
                        bucket="books-epub",
                        object_name=file_path,
                    )
                    logger.info(f"[Book {book_id}] 从 MinIO 下载文件成功")
                except Exception as e:
                    logger.error(f"[Book {book_id}] 从 MinIO 下载文件失败: {e}")
                    raise EPUBParseError(f"无法从存储获取文件: {e}")
            elif file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    file_content = f.read()
            else:
                raise EPUBParseError(f"无效的文件路径: {file_path}")

            # 使用 BytesIO 解析
            parser = EPUBParserService()
            result = parser.parse_bytes(file_content, book.id)

            # 更新书籍信息
            book.title = result.get("title", book.title)
            book.author = result.get("author")
            book.description = result.get("description")
            book.total_chapters = result.get("chapter_count", 0)

            # 保存封面图
            if result.get("cover_image"):
                cover_path = f"covers/{book_id}/cover.jpg"
                if storage is None:
                    storage = get_storage_service()
                storage.upload_file(
                    bucket="books-epub",
                    object_name=cover_path,
                    data=result["cover_image"],
                    content_type="image/jpeg",
                )
                book.cover_image_path = cover_path

            # ── 优化：章节拆分 + 正文清洗 + 上传 MinIO ──
            chapters_data = result.get("chapters", [])
            total_uploaded = 0
            total_removed_chars = 0

            if storage is None:
                storage = get_storage_service()

            for idx, chapter_data in enumerate(chapters_data):
                chapter_index = idx + 1
                raw_content = chapter_data.get("content", "")
                chapter_title = chapter_data.get("title", f"第{chapter_index}章")

                # 清洗文本：只保留正文，丢弃页眉页脚/版权/广告等
                cleaned_text, clean_report = clean_chapter_with_report(
                    raw_content, chapter_title
                )

                # 上传清洗后的正文到 MinIO（供后续 DeepSeek 分析读取）
                minio_path = storage.upload_chapter_text(
                    book_id=book_id,
                    chapter_index=chapter_index,
                    text=cleaned_text,
                )

                # 数据库只存预览（前500字符）和 MinIO 路径
                preview_text = cleaned_text[:500] if cleaned_text else ""

                chapter = Chapter(
                    book_id=book_id,
                    chapter_index=chapter_index,
                    title=chapter_title,
                    raw_text=preview_text,                     # 仅预览
                    cleaned_text=minio_path,                    # 存 MinIO 路径
                    status=ChapterStatus.PENDING,
                )
                db.add(chapter)

                total_uploaded += 1
                total_removed_chars += clean_report.removed_chars

                if clean_report.quality_score < 0.5:
                    logger.warning(
                        f"[Book {book_id}] 章节 {chapter_index} 清洗质量偏低: "
                        f"score={clean_report.quality_score:.2f}"
                    )

            db.commit()

            # 获取章节 ID 列表
            chapters = db.query(Chapter).filter(Chapter.book_id == book_id).all()
            chapter_ids = [ch.id for ch in chapters]

            logger.info(
                f"[Book {book_id}] EPUB 解析完成: {len(chapter_ids)} 章节, "
                f"已上传 {total_uploaded} 个清洗文本到 MinIO, "
                f"去除 {total_removed_chars} 非正文字符"
            )

            # ── 事件驱动：清洗文本就绪 → 触发逐章处理 ──
            logger.info(
                f"[Book {book_id}] 清洗文本已就绪，"
                f"触发 {len(chapter_ids)} 章逐章处理..."
            )
            for ch_id in chapter_ids:
                process_chapter.delay(ch_id)

            return {
                "book_id": book_id,
                "chapter_ids": chapter_ids,
                "chapter_count": len(chapter_ids),
                "stage": PipelineStage.PARSING.value,
                "success": True,
                "chapters_uploaded": total_uploaded,
                "removed_chars": total_removed_chars,
            }

        except Exception as e:
            logger.error(f"[Book {book_id}] EPUB 解析失败: {e}")
            book.status = BookStatus.FAILED
            book.error_message = f"EPUB 解析失败: {str(e)}"
            db.commit()
            raise


# ===========================================
# 阶段二：文本预处理
# ===========================================

@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.preprocess_chapter",
    queue="pipeline",
    max_retries=3,
)
def preprocess_chapter(self, chapter_id: int) -> Dict[str, Any]:
    """
    预处理单个章节文本

    阶段二：对章节文本进行清洗和标准化。
    如果章节文本已在解析阶段上传到 MinIO，则跳过（避免重复清洗）。

    Args:
        chapter_id: 章节ID

    Returns:
        dict: 预处理结果
    """
    logger.info(f"[Chapter {chapter_id}] 阶段二：开始预处理")

    with get_db_context() as db:
        from models import Chapter
        from models.model_chapter import ChapterStatus
        from services.svc_text_preprocessor import TextPreprocessorService
        from services.svc_minio_storage import get_storage_service

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        try:
            # ── 优化：检查文本是否已在 MinIO（解析阶段已清洗+上传） ──
            if chapter.cleaned_text and chapter.cleaned_text.startswith("chapters/"):
                logger.info(
                    f"[Chapter {chapter_id}] 文本已在 MinIO, 跳过预处理 "
                    f"(path={chapter.cleaned_text})"
                )
                return {
                    "chapter_id": chapter_id,
                    "paragraph_count": 0,
                    "stage": PipelineStage.PREPROCESSING.value,
                    "success": True,
                    "skipped": True,
                }

            # 兼容旧数据：从 DB raw_text 做预处理
            chapter.status = ChapterStatus.PENDING
            chapter.updated_at = datetime.utcnow()
            db.commit()

            preprocessor = TextPreprocessorService()
            raw_text = chapter.raw_text or ""

            # 规范化文本
            normalized = preprocessor.normalize_text(raw_text)

            # 拆分段落
            paragraphs = preprocessor.split_paragraphs(normalized)

            # TTS 准备
            prepared = preprocessor.prepare_for_tts(raw_text)

            # 对于旧数据，也尝试上传到 MinIO
            try:
                storage = get_storage_service()
                minio_path = storage.upload_chapter_text(
                    book_id=chapter.book_id,
                    chapter_index=chapter.chapter_index,
                    text=prepared.get("processed_text", normalized),
                )
                chapter.cleaned_text = minio_path
            except Exception as e:
                logger.warning(f"[Chapter {chapter_id}] MinIO 上传失败，仅存 DB: {e}")
                chapter.cleaned_text = prepared.get("processed_text", normalized)

            chapter.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"[Chapter {chapter_id}] 预处理完成，段落数: {len(paragraphs)}")
            return {
                "chapter_id": chapter_id,
                "paragraph_count": len(paragraphs),
                "stage": PipelineStage.PREPROCESSING.value,
                "success": True,
            }

        except Exception as e:
            logger.error(f"[Chapter {chapter_id}] 预处理失败: {e}")
            chapter.status = ChapterStatus.FAILED
            chapter.error_message = str(e)
            db.commit()
            raise


@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.preprocess_book",
    queue="pipeline",
)
def preprocess_book(self, book_id: int) -> Dict[str, Any]:
    """
    预处理整本书籍的所有章节

    串行预处理每个章节

    Args:
        book_id: 书籍ID

    Returns:
        dict: 预处理结果汇总
    """
    logger.info(f"[Book {book_id}] 批量预处理章节")

    with get_db_context() as db:
        from models import Chapter, Book
        from models.model_chapter import ChapterStatus
        from models.model_book import BookStatus

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
                result = preprocess_chapter.delay(chapter.id)
                results.append({"chapter_id": chapter.id, "task_id": result.id})
            except Exception as e:
                logger.error(f"提交预处理任务失败: {chapter.id} - {e}")
                results.append({"chapter_id": chapter.id, "error": str(e)})

        return {
            "book_id": book_id,
            "total_chapters": len(chapters),
            "submitted_tasks": results,
        }


# ===========================================
# 阶段三：DeepSeek 分析
# ===========================================

@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.analyze_chapter",
    queue="pipeline",
    max_retries=3,
)
def analyze_chapter(self, chapter_id: int) -> Dict[str, Any]:
    """
    分析单个章节

    阶段三：使用 DeepSeek 进行角色识别、情感标注

    Args:
        chapter_id: 章节ID

    Returns:
        dict: 分析结果
    """
    logger.info(f"[Chapter {chapter_id}] 阶段三：开始 DeepSeek 分析（从 MinIO 读取文本）")

    with get_db_context() as db:
        from models import Chapter, Book
        from models.model_chapter import ChapterStatus
        from models.model_book import BookStatus
        from services.svc_deepseek_analyzer import DeepSeekAnalyzerService
        from services.svc_minio_storage import get_storage_service

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        book = db.query(Book).filter(Book.id == chapter.book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {chapter.book_id}")

        try:
            # 更新状态
            chapter.status = ChapterStatus.ANALYZING
            db.commit()

            # 检查是否为第一个分析的章节
            analyzed_count = (
                db.query(Chapter)
                .filter(Chapter.book_id == chapter.book_id)
                .filter(Chapter.status == ChapterStatus.ANALYZED)
                .count()
            )
            if analyzed_count == 0:
                book.status = BookStatus.ANALYZING
                db.commit()

            # ── 读取章节文本（优先 MinIO，回退 DB） ──
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
                chapter.analysis_result = {"paragraphs": [], "characters": []}
                db.commit()
                return {
                    "chapter_id": chapter_id,
                    "warning": "文本内容过短",
                    "stage": PipelineStage.ANALYZING.value,
                    "success": True,
                }

            # 执行分析
            analyzer = DeepSeekAnalyzerService()
            result = analyzer.analyze_chapter(text)

            # 更新章节
            chapter.analysis_result = result
            chapter.characters = result.get("characters", [])
            chapter.status = ChapterStatus.ANALYZED
            chapter.updated_at = datetime.utcnow()

            # 更新成本统计
            if result.get("token_usage"):
                chapter.deepseek_tokens = result["token_usage"]

            # 更新 MiniMax 字符消耗（基于处理后的文本长度）
            if result.get("processed_text"):
                chapter.minimax_characters = len(result["processed_text"])

            db.commit()

            logger.info(
                f"[Chapter {chapter_id}] DeepSeek 分析完成，角色数: {len(chapter.characters)}"
            )
            return {
                "chapter_id": chapter_id,
                "characters": chapter.characters,
                "stage": PipelineStage.ANALYZING.value,
                "success": True,
            }

        except Exception as e:
            logger.error(f"[Chapter {chapter_id}] DeepSeek 分析失败: {e}")
            chapter.status = ChapterStatus.FAILED
            chapter.error_message = str(e)
            db.commit()
            raise


# ===========================================
# 阶段四：创建音频片段
# ===========================================

@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.create_segments",
    queue="pipeline",
)
def create_segments(self, chapter_id: int) -> Dict[str, Any]:
    """
    为章节创建音频片段

    阶段四：根据分析结果创建 TTS 合成片段

    Args:
        chapter_id: 章节ID

    Returns:
        dict: 创建结果
    """
    logger.info(f"[Chapter {chapter_id}] 阶段四：创建音频片段")

    with get_db_context() as db:
        from models import Chapter, AudioSegment
        from models.model_chapter import ChapterStatus
        from models.model_segment import SegmentStatus, AudioSegment as AudioSegmentModel
        from services.svc_voice_mapper import VoiceMapperService

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        try:
            analysis = chapter.analysis_result or {}
            paragraphs = analysis.get("paragraphs", [])

            # 调试日志
            logger.info(f"[Chapter {chapter_id}] 分析结果包含 {len(paragraphs)} 个段落")
            if paragraphs and len(paragraphs) > 0:
                logger.info(f"[Chapter {chapter_id}] 第一个段落示例: {paragraphs[0] if paragraphs else 'N/A'}")

            # 如果没有段落，尝试使用 raw_text 拆分
            if not paragraphs:
                logger.warning(f"[Chapter {chapter_id}] 分析结果中没有段落，使用 raw_text 拆分")
                raw_text = chapter.raw_text or ""
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                paragraphs = [
                    {
                        "text": line,
                        "role": "narrator",
                        "emotion": "neutral",
                        "speaker": "旁白"
                    }
                    for line in lines
                ]
                logger.info(f"[Chapter {chapter_id}] 从 raw_text 拆分了 {len(paragraphs)} 个段落")

            # 声音映射器
            voice_mapper = VoiceMapperService()

            segments_created = 0
            for idx, para in enumerate(paragraphs):
                # 创建音频片段
                role = para.get("role", "narrator")
                gender = para.get("gender", "neutral")

                # 获取音色
                voice_params = voice_mapper.get_voice_for_role(role)
                voice_id = voice_params.get("voice_id", "female-shaonv")

                segment = AudioSegmentModel(
                    chapter_id=chapter_id,
                    segment_index=idx,
                    text_content=para.get("text", ""),
                    role=role,
                    emotion=para.get("emotion", "neutral"),
                    voice_id=voice_id,
                    speed=para.get("speed", 1.0),
                    status=SegmentStatus.PENDING,
                )
                db.add(segment)
                segments_created += 1

            # 更新章节统计
            chapter.total_segments = segments_created
            chapter.status = ChapterStatus.ANALYZED
            chapter.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"[Chapter {chapter_id}] 创建了 {segments_created} 个音频片段")
            return {
                "chapter_id": chapter_id,
                "segments_created": segments_created,
                "stage": PipelineStage.CREATING_SEGMENTS.value,
                "success": True,
            }

        except Exception as e:
            logger.error(f"[Chapter {chapter_id}] 创建音频片段失败: {e}")
            chapter.error_message = str(e)
            db.commit()
            raise


# ===========================================
# 阶段五：TTS 合成
# ===========================================

@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.synthesize_segment",
    queue="pipeline",
    max_retries=6,
    default_retry_delay=10,       # 首次重试等10秒，后续指数递增
    autoretry_for=(MiniMaxApiError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=120,         # 最大退避120秒
    retry_jitter=True,
)
def synthesize_segment(self, segment_id: int) -> Dict[str, Any]:
    """
    合成单个音频片段

    阶段五：调用 MiniMax TTS 合成语音

    Args:
        segment_id: 音频片段ID

    Returns:
        dict: 合成结果
    """
    logger.info(f"[Segment {segment_id}] 阶段五：开始 TTS 合成")

    with get_db_context() as db:
        from models import AudioSegment, Chapter
        from models.model_segment import SegmentStatus
        from models.model_chapter import ChapterStatus
        from services.svc_minimax_tts import MiniMaxTTSService
        from services.svc_minio_storage import get_storage_service

        segment = db.query(AudioSegment).filter(AudioSegment.id == segment_id).first()
        if not segment:
            raise ValueError(f"音频片段不存在: {segment_id}")

        chapter = db.query(Chapter).filter(Chapter.id == segment.chapter_id).first()

        try:
            # 更新状态
            segment.status = SegmentStatus.SYNTHESIZING
            if chapter:
                chapter.status = ChapterStatus.SYNTHESIZING
            db.commit()

            # TTS 合成（使用同步方法）
            tts_service = MiniMaxTTSService()
            audio_data = tts_service.synthesize_sync(
                text=segment.text_content,
                voice_id=segment.voice_id,
                speed=segment.speed,
                emotion=segment.emotion,
            )

            # 保存到 MinIO
            storage = get_storage_service()
            import uuid
            object_name = f"segments/{segment.chapter_id}/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.mp3"

            storage.upload_file(
                bucket="books-audio",
                object_name=object_name,
                data=audio_data,
                content_type="audio/mpeg",
            )

            # 更新片段状态
            segment.status = SegmentStatus.SUCCESS
            segment.audio_file_path = object_name
            segment.audio_url = storage.get_presigned_url("books-audio", object_name)
            segment.audio_bytes_size = len(audio_data)
            segment.updated_at = datetime.utcnow()

            # 更新章节进度
            if chapter:
                chapter.completed_segments = (
                    db.query(AudioSegment)
                    .filter(
                        AudioSegment.chapter_id == chapter.id,
                        AudioSegment.status == SegmentStatus.SUCCESS,
                    )
                    .count()
                )

            db.commit()

            logger.info(f"[Segment {segment_id}] TTS 合成完成")
            return {
                "segment_id": segment_id,
                "audio_file_path": object_name,
                "stage": PipelineStage.SYNTHESIZING.value,
                "success": True,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[Segment {segment_id}] TTS 合成失败: {error_msg}")

            segment.status = SegmentStatus.FAILED
            segment.error_message = error_msg
            segment.retry_count = (segment.retry_count or 0) + 1
            db.commit()

            # 余额不足不重试
            if "insufficient balance" in error_msg or "1008" in error_msg:
                logger.error(
                    f"[Segment {segment_id}] MiniMax 余额不足，放弃重试"
                )
                return {
                    "segment_id": segment_id,
                    "stage": PipelineStage.SYNTHESIZING.value,
                    "success": False,
                    "error": error_msg,
                }

            raise


# ===========================================
# 阶段六：音频后处理
# ===========================================

@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.postprocess_chapter",
    queue="pipeline",
    max_retries=3,
)
def postprocess_chapter(self, chapter_id: int) -> Dict[str, Any]:
    """
    后处理章节音频

    阶段六：音频拼接、音量均衡、格式转换

    Args:
        chapter_id: 章节ID

    Returns:
        dict: 后处理结果
    """
    logger.info(f"[Chapter {chapter_id}] 阶段六：开始音频后处理")

    with get_db_context() as db:
        from models import Chapter, Book
        from models.model_chapter import ChapterStatus
        from models.model_book import BookStatus
        from services.svc_audio_postprocessor import AudioPostprocessorService

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
            processor = AudioPostprocessorService()
            result = processor.process_chapter(chapter_id)

            # 更新章节
            chapter.status = ChapterStatus.DONE
            chapter.audio_file_path = result["audio_file_path"]
            chapter.audio_duration = result["duration_seconds"]
            chapter.audio_file_size = result["file_size"]
            chapter.updated_at = datetime.utcnow()

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

            logger.info(f"[Chapter {chapter_id}] 音频后处理完成")
            return {
                "chapter_id": chapter_id,
                "audio_file_path": result["audio_file_path"],
                "duration_seconds": result["duration_seconds"],
                "stage": PipelineStage.POSTPROCESSING.value,
                "success": True,
            }

        except Exception as e:
            logger.error(f"[Chapter {chapter_id}] 音频后处理失败: {e}")
            raise


# ===========================================
# 章节处理流水线（事件驱动）
# ===========================================

@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.process_chapter",
    queue="pipeline",
    max_retries=3,
)
def process_chapter(self, chapter_id: int) -> Dict[str, Any]:
    """
    处理单个章节的完整流水线（事件驱动）

    当清洗后的文本就绪时自动触发：
    阶段三 DeepSeek 分析 → 阶段四创建片段 → 阶段五 TTS 合成 → 阶段六后处理

    这是事件驱动的核心：每章独立串行，一章完成自动触发下一阶段。

    Args:
        chapter_id: 章节 ID

    Returns:
        dict: 处理结果
    """
    logger.info(f"[Chapter {chapter_id}] === 事件触发：开始逐章处理 ===")

    from models import AudioSegment, Book
    from models.model_book import BookStatus, GenerationMode
    from models.model_chapter import ChapterStatus
    from models.model_segment import SegmentStatus

    try:
        # 阶段三：DeepSeek 分析
        logger.info(f"[Chapter {chapter_id}] 阶段三：DeepSeek 分析")
        analyze_chapter(chapter_id)

        # 阶段四：创建音频片段
        logger.info(f"[Chapter {chapter_id}] 阶段四：创建音频片段")
        create_segments(chapter_id)

        # 阶段五：TTS 合成（逐段）
        logger.info(f"[Chapter {chapter_id}] 阶段五：TTS 合成")
        with get_db_context() as db:
            seg_list = (
                db.query(AudioSegment)
                .filter(AudioSegment.chapter_id == chapter_id)
                .order_by(AudioSegment.segment_index)
                .all()
            )
            seg_ids = [s.id for s in seg_list]

        if seg_ids:
            for seg_id in seg_ids:
                synthesize_segment(seg_id)
            logger.info(f"[Chapter {chapter_id}] 阶段五完成（{len(seg_ids)} 片段）")
        else:
            logger.warning(f"[Chapter {chapter_id}] 无音频片段，跳过 TTS")

        # 阶段六：音频后处理
        logger.info(f"[Chapter {chapter_id}] 阶段六：音频后处理")
        postprocess_chapter(chapter_id)

        # ── 检查是否所有章节都完成 → 触发发布 ──
        _try_publish_book(chapter_id)

        # ── 根据生成模式决定是否自动触发下一章 ──
        with get_db_context() as db:
            from models import Chapter
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                return {"chapter_id": chapter_id, "success": True}

            book = db.query(Book).filter(Book.id == chapter.book_id).first()
            next_chapter = (
                db.query(Chapter)
                .filter(Chapter.book_id == chapter.book_id)
                .filter(Chapter.chapter_index == chapter.chapter_index + 1)
                .first()
            )

            if not next_chapter:
                # 没有下一章 → 标记当前章完成
                chapter.status = ChapterStatus.DONE
                db.commit()
                logger.info(f"[Chapter {chapter_id}] ✅ 章节全部处理完成")
                return {"chapter_id": chapter_id, "success": True}

            if book and book.generation_mode == GenerationMode.MANUAL:
                # ── 手动模式：暂停，等待用户确认 ──
                chapter.status = ChapterStatus.DONE
                # 找出下下章
                next_next = (
                    db.query(Chapter)
                    .filter(Chapter.book_id == chapter.book_id)
                    .filter(Chapter.chapter_index == next_chapter.chapter_index + 1)
                    .first()
                )
                next_chapter.status = ChapterStatus.AWAITING_CONFIRM
                next_chapter.next_chapter_id = next_next.id if next_next else None
                db.commit()
                logger.info(
                    f"[Chapter {chapter_id}] ⏸ 手动模式：第 {chapter.chapter_index} 章完成，"
                    f"第 {next_chapter.chapter_index} 章等待确认"
                )
                return {
                    "chapter_id": chapter_id,
                    "success": True,
                    "mode": "manual",
                    "next_chapter_id": next_chapter.id,
                }
            else:
                # ── 自动模式：自动触发下一章 ──
                chapter.status = ChapterStatus.DONE
                db.commit()
                process_chapter.delay(next_chapter.id)
                logger.info(
                    f"[Chapter {chapter_id}] ✅ 自动模式：第 {chapter.chapter_index} 章完成，"
                    f"自动触发第 {next_chapter.chapter_index} 章"
                )
                return {
                    "chapter_id": chapter_id,
                    "success": True,
                    "mode": "auto",
                    "next_chapter_id": next_chapter.id,
                }

    except Exception as e:
        logger.error(f"[Chapter {chapter_id}] 章节处理失败: {e}")
        with get_db_context() as db:
            from models import Chapter
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if chapter:
                retry_count = (chapter.failed_segments or 0) + 1
                if retry_count >= 3:
                    chapter.status = ChapterStatus.FAILED
                    chapter.error_message = f"[{retry_count}次重试] {str(e)}"
                    logger.warning(
                        f"[Chapter {chapter_id}] 已达重试上限 ({retry_count}), "
                        f"标记为失败，继续处理其他章节"
                    )
                else:
                    chapter.failed_segments = retry_count
                    chapter.status = ChapterStatus.PENDING
                    chapter.error_message = str(e)
                db.commit()
                _try_publish_book(chapter_id, retry_count >= 3)

        logger.info(f"[Chapter {chapter_id}] 章节失败但不影响其他章节继续处理")
        return {
            "chapter_id": chapter_id,
            "success": False,
            "error": str(e),
        }


def _try_publish_book(
    chapter_id: int, force_check: bool = False
) -> None:
    """
    检查并触发书籍发布

    当所有章节都完成或失败时，自动触发发布（部分完成）。

    Args:
        chapter_id: 任意章节 ID（用于反查 book_id）
        force_check: 是否强制检查（章节失败时也检查）
    """
    from models import Chapter, Book
    from models.model_chapter import ChapterStatus
    from models.model_book import BookStatus
    from sqlalchemy import func

    with get_db_context() as db:
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            return

        book_id = chapter.book_id
        total = (
            db.query(func.count(Chapter.id))
            .filter(Chapter.book_id == book_id)
            .scalar()
            or 0
        )
        done = (
            db.query(func.count(Chapter.id))
            .filter(
                Chapter.book_id == book_id,
                Chapter.status == ChapterStatus.DONE,
            )
            .scalar()
            or 0
        )
        failed = (
            db.query(func.count(Chapter.id))
            .filter(
                Chapter.book_id == book_id,
                Chapter.status == ChapterStatus.FAILED,
            )
            .scalar()
            or 0
        )

        # 所有章节都处于终态（DONE 或 FAILED）→ 触发发布
        if done + failed >= total:
            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                book.processed_chapters = done
                book.status = BookStatus.PUBLISHING
                if failed > 0:
                    logger.warning(
                        f"[Book {book_id}] 部分章节失败: "
                        f"{done}/{total} 成功, {failed} 失败, 继续发布"
                    )
                else:
                    logger.info(
                        f"[Book {book_id}] 全部 {total} 章完成，触发发布"
                    )
                db.commit()
                from tasks.task_pipeline import publish_book
                publish_book.delay(book_id)


# ===========================================
# 阶段七：自动发布
# ===========================================

@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.publish_book",
    queue="pipeline",
)
def publish_book(self, book_id: int) -> Dict[str, Any]:
    """
    发布书籍到已配置渠道

    阶段七：自动发布到各渠道

    Args:
        book_id: 书籍ID

    Returns:
        dict: 发布结果
    """
    logger.info(f"[Book {book_id}] 阶段七：开始自动发布")

    with get_db_context() as db:
        from models import Book, PublishChannel
        from models.model_book import BookStatus
        from tasks.task_publish import publish_book_to_all_channels

        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {book_id}")

        # 检查是否启用自动发布
        if not book.auto_publish_enabled:
            logger.info(f"[Book {book_id}] 自动发布未启用，跳过")
            return {
                "book_id": book_id,
                "auto_publish": False,
                "message": "自动发布未启用",
            }

        # 检查是否有启用且配置自动发布的渠道
        channels = (
            db.query(PublishChannel)
            .filter(PublishChannel.is_enabled == True)
            .filter(PublishChannel.auto_publish == True)
            .all()
        )

        if not channels:
            logger.info(f"[Book {book_id}] 没有已配置的发布渠道")
            return {
                "book_id": book_id,
                "channels": 0,
                "message": "没有已配置的发布渠道",
            }

        # 更新状态
        book.status = BookStatus.PUBLISHING
        db.commit()

        # 触发发布任务
        try:
            result = publish_book_to_all_channels.delay(book_id)
            logger.info(f"[Book {book_id}] 发布任务已提交: {result.id}")
            return {
                "book_id": book_id,
                "channels": len(channels),
                "task_id": result.id,
                "stage": PipelineStage.PUBLISHING.value,
                "success": True,
            }
        except Exception as e:
            logger.error(f"[Book {book_id}] 发布任务提交失败: {e}")
            book.status = BookStatus.FAILED  # 修正：失败时应该设置 FAILED 而不是 DONE
            book.error_message = f"发布任务提交失败: {str(e)}"
            db.commit()
            raise


# ===========================================
# 主流水线：完整链路编排
# ===========================================

@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.generate_audiobook",
    ignore_result=False,
    queue="pipeline",
    max_retries=1,
)
def generate_audiobook(self, book_id: int) -> Dict[str, Any]:
    """
    生成有声书（事件驱动版本）

    仅触发阶段一：EPUB 解析。
    解析完成后自动触发逐章处理（process_chapter），
    所有章节完成后自动触发发布（_try_publish_book）。

    Args:
        book_id: 书籍ID

    Returns:
        dict: 执行结果
    """
    logger.info(f"=" * 60)
    logger.info(f"[Book {book_id}] 触发有声书生成（事件驱动）")
    logger.info(f"=" * 60)

    from models.model_book import BookStatus

    try:
        # 阶段一：EPUB 解析（process_chapter 会在此后自动触发）
        parse_result = parse_epub(book_id)
        chapter_ids = parse_result.get("chapter_ids", [])

        logger.info(
            f"[Book {book_id}] 流水线已启动: "
            f"{len(chapter_ids)} 章清洗文本已就绪，逐章处理已排队"
        )

        # 不需要等待 - process_chapter 会在 celery 中自动执行
        return {
            "book_id": book_id,
            "chapter_count": len(chapter_ids),
            "status": "processing",
            "note": "逐章处理已自动触发",
        }

    except Exception as e:
        logger.error(f"[Book {book_id}] 流水线启动失败: {e}")
        with get_db_context() as db:
            from models import Book
            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                book.status = BookStatus.FAILED
                book.error_message = str(e)
                db.commit()
        raise
        logger.info(f"=" * 60)
        logger.info(f"[Book {book_id}] 有声书生成流水线完成!")
        logger.info(f"[Book {book_id}] 总耗时: {total_time:.1f}s")
        logger.info(f"=" * 60)

        return {
            "book_id": book_id,
            "chapter_count": len(chapter_ids),
            "segment_count": len(segment_ids),
            "total_time_seconds": int(total_time),
            "status": "completed",
        }

    except Exception as e:
        total_time = time.time() - total_start
        logger.error(f"[Book {book_id}] 流水线执行失败: {e} (耗时: {total_time:.1f}s)")
        _update_book_error(book_id, str(e))
        raise


def _wait_for_result(async_result, timeout: int = 300):
    """
    轮询等待异步结果（替代 .get()）

    Celery 不允许在任务内调用 .get()，所以使用轮询方式等待结果。
    这是一个 hacky 的解决方案，生产环境应该使用 Chain 的回调机制。

    Args:
        async_result: Celery AsyncResult 或 GroupResult 对象
        timeout: 超时时间（秒）
    """
    import time

    start_time = time.time()
    while not async_result.ready():
        if time.time() - start_time > timeout:
            raise TimeoutError(f"等待任务完成超时: {timeout}s")
        time.sleep(1)

    # 检查是否有异常
    if async_result.failed():
        # GroupResult 没有 .result 属性，需要特殊处理
        raise Exception("任务执行失败")

    # 对于 GroupResult，返回结果列表
    if hasattr(async_result, 'results'):
        return async_result.results

    return async_result.result


@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.generate_audiobook_simple",
    ignore_result=False,
    queue="pipeline",
)
def generate_audiobook_simple(self, book_id: int) -> Dict[str, Any]:
    """
    简化版有声书生成（直接调用编排器）

    Args:
        book_id: 书籍ID

    Returns:
        dict: 执行结果
    """
    return generate_audiobook(book_id)


# ===========================================
# 辅助任务
# ===========================================

@celery_app.task(
    name="tasks.task_pipeline.check_pipeline_status",
    queue="pipeline",
)
def check_pipeline_status(book_id: int) -> Dict[str, Any]:
    """
    检查流水线执行状态

    用于前端轮询或监控查询

    Args:
        book_id: 书籍ID

    Returns:
        dict: 状态信息
    """
    with get_db_context() as db:
        from models import Book, Chapter, AudioSegment
        from models.model_book import BookStatus
        from models.model_chapter import ChapterStatus
        from models.model_segment import SegmentStatus
        from sqlalchemy import func

        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return {"error": "书籍不存在", "book_id": book_id}

        chapters = db.query(Chapter).filter(Chapter.book_id == book_id).all()

        # 统计各状态章节数
        status_counts = {}
        for ch in chapters:
            status = ch.status.value if ch.status else "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1

        # 统计音频片段
        total_segments = 0
        completed_segments = 0
        for ch in chapters:
            total_segments += ch.total_segments or 0
            completed_segments += ch.completed_segments or 0

        # 成本统计
        deepseek_tokens = sum(ch.deepseek_tokens or 0 for ch in chapters)
        minimax_chars = sum(ch.minimax_characters or 0 for ch in chapters)
        estimated_cost = int(
            deepseek_tokens / 1_000_000 * 100 +
            minimax_chars / 1000 * 0.2 * 100
        )

        return {
            "book_id": book_id,
            "title": book.title,
            "book_status": book.status.value if book.status else "unknown",
            "progress_percentage": book.progress_percentage,
            "total_chapters": len(chapters),
            "chapter_status": status_counts,
            "total_segments": total_segments,
            "completed_segments": completed_segments,
            "estimated_cost_cents": estimated_cost,
            "deepseek_tokens": deepseek_tokens,
            "minimax_characters": minimax_chars,
            "error_message": book.error_message,
            "created_at": book.created_at.isoformat() if book.created_at else None,
            "updated_at": book.updated_at.isoformat() if book.updated_at else None,
        }


@celery_app.task(
    name="tasks.task_pipeline.retry_failed_chapters",
    queue="pipeline",
)
def retry_failed_chapters(book_id: int) -> Dict[str, Any]:
    """
    重试失败的章节处理

    重新执行失败章节的所有处理步骤

    Args:
        book_id: 书籍ID

    Returns:
        dict: 重试结果
    """
    logger.info(f"[Book {book_id}] 重试失败的章节")

    with get_db_context() as db:
        from models import Chapter
        from models.model_chapter import ChapterStatus

        failed_chapters = (
            db.query(Chapter)
            .filter(Chapter.book_id == book_id)
            .filter(Chapter.status == ChapterStatus.FAILED)
            .all()
        )

        results = []
        for chapter in failed_chapters:
            try:
                # 重置状态
                chapter.status = ChapterStatus.PENDING
                chapter.error_message = None
                db.commit()

                # 重新执行
                result = analyze_chapter.delay(chapter.id)
                results.append({"chapter_id": chapter.id, "task_id": result.id})
            except Exception as e:
                logger.error(f"重试章节 {chapter.id} 失败: {e}")
                results.append({"chapter_id": chapter.id, "error": str(e)})

        return {
            "book_id": book_id,
            "failed_chapters": len(failed_chapters),
            "retried": len(results),
        }


@celery_app.task(
    name="tasks.task_pipeline.get_pipeline_history",
    queue="pipeline",
)
def get_pipeline_history(
    book_id: Optional[int] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    获取流水线执行历史

    Args:
        book_id: 可选，书籍ID，用于筛选特定书籍的历史记录
        limit: 返回记录数量限制

    Returns:
        dict: 历史记录列表
    """
    # 从 Celery Result Backend 获取历史
    # 这里简化处理，实际项目中应该使用专门的数据库表存储历史
    from tasks.celery_app import celery_app

    history = []

    try:
        # 获取最近的流水线任务
        inspector = celery_app.control.inspect()
        reserved = inspector.reserved() or {}
        active = inspector.active() or {}

        # 收集正在执行的任务
        all_tasks = []
        for worker, tasks in reserved.items():
            all_tasks.extend(tasks)
        for worker, tasks in active.items():
            all_tasks.extend(tasks)

        # 过滤流水线任务
        pipeline_tasks = [
            t for t in all_tasks
            if t.get("name", "").startswith("tasks.task_pipeline.generate_audiobook")
        ]

        for task in pipeline_tasks[:limit]:
            history.append({
                "task_id": task.get("id"),
                "name": task.get("name"),
                "worker": task.get("hostname"),
                "time_start": task.get("time_start"),
            })

    except Exception as e:
        logger.warning(f"获取流水线历史失败: {e}")

    return {
        "count": len(history),
        "tasks": history,
    }


@celery_app.task(
    name="tasks.task_pipeline.cancel_pipeline",
    queue="pipeline",
)
def cancel_pipeline(book_id: int) -> Dict[str, Any]:
    """
    取消正在执行的流水线

    Args:
        book_id: 书籍ID

    Returns:
        dict: 取消结果
    """
    from models import Book
    from models.model_book import BookStatus

    logger.info(f"[Book {book_id}] 尝试取消流水线执行")

    with get_db_context() as db:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return {"success": False, "message": "书籍不存在"}

        # 更新状态
        book.status = BookStatus.FAILED
        book.error_message = "用户主动取消"
        book.updated_at = datetime.utcnow()
        db.commit()

    # TODO: 实际取消正在执行的 Celery 任务需要更强的机制
    # 可以通过发送取消信号或使用 revoke

    logger.info(f"[Book {book_id}] 流水线已标记为取消")
    return {
        "success": True,
        "book_id": book_id,
        "message": "流水线已标记为取消",
    }
