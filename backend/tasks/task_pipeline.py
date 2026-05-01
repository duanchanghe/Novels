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
    retry_backoff_max = 300
    retry_jitter = True
    max_retries = 3

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

    Args:
        book_id: 书籍ID

    Returns:
        dict: 解析结果
    """
    logger.info(f"[Book {book_id}] 阶段一：开始解析 EPUB")

    with get_db_context() as db:
        from models import Book, Chapter
        from models.model_book import BookStatus
        from models.model_chapter import ChapterStatus
        from services.svc_epub_parser import EPUBParserService

        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {book_id}")

        try:
            # 更新状态
            book.status = BookStatus.PENDING
            book.updated_at = datetime.utcnow()
            db.commit()

            # 解析 EPUB
            parser = EPUBParserService()
            result = parser.parse_file(book.file_path, book_id)

            # 更新书籍信息
            book.title = result.get("title", book.title)
            book.author = result.get("author")
            book.description = result.get("description")
            book.total_chapters = result.get("chapter_count", 0)

            # 保存封面图
            if result.get("cover_image"):
                cover_path = f"covers/{book_id}/cover.jpg"
                from services.svc_minio_storage import get_storage_service
                storage = get_storage_service()
                storage.upload_file(
                    bucket="books-epub",
                    object_name=cover_path,
                    data=result["cover_image"],
                    content_type="image/jpeg",
                )
                book.cover_image_path = cover_path

            # 创建章节记录
            chapters_data = result.get("chapters", [])
            for idx, chapter_data in enumerate(chapters_data):
                chapter = Chapter(
                    book_id=book_id,
                    chapter_index=idx + 1,
                    title=chapter_data.get("title", f"第{idx + 1}章"),
                    raw_text=chapter_data.get("content"),
                    status=ChapterStatus.PENDING,
                )
                db.add(chapter)

            db.commit()

            # 获取章节 ID 列表
            chapters = db.query(Chapter).filter(Chapter.book_id == book_id).all()
            chapter_ids = [ch.id for ch in chapters]

            logger.info(f"[Book {book_id}] EPUB 解析完成，共 {len(chapter_ids)} 章节")
            return {
                "book_id": book_id,
                "chapter_ids": chapter_ids,
                "chapter_count": len(chapter_ids),
                "stage": PipelineStage.PARSING.value,
                "success": True,
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

    阶段二：对章节文本进行清洗和标准化

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

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        try:
            # 更新状态为处理中
            chapter.status = ChapterStatus.PENDING
            chapter.updated_at = datetime.utcnow()
            db.commit()

            # 执行预处理
            preprocessor = TextPreprocessorService()
            raw_text = chapter.raw_text or ""

            # 规范化文本
            normalized = preprocessor.normalize_text(raw_text)

            # 拆分段落
            paragraphs = preprocessor.split_paragraphs(normalized)

            # TTS 准备
            prepared = preprocessor.prepare_for_tts(raw_text)

            # 更新章节
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
    logger.info(f"[Chapter {chapter_id}] 阶段三：开始 DeepSeek 分析")

    with get_db_context() as db:
        from models import Chapter, Book
        from models.model_chapter import ChapterStatus
        from models.model_book import BookStatus
        from services.svc_deepseek_analyzer import DeepSeekAnalyzerService

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        book = db.query(Book).filter(Book.id == chapter.book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {chapter.book_id}")

        try:
            # 更新状态（只在第一个章节分析时更新书籍状态）
            chapter.status = ChapterStatus.ANALYZING
            db.commit()

            # 检查是否为第一个分析的章节，如果是则更新书籍状态
            analyzed_count = (
                db.query(Chapter)
                .filter(Chapter.book_id == chapter.book_id)
                .filter(Chapter.status == ChapterStatus.ANALYZED)
                .count()
            )
            if analyzed_count == 0:
                book.status = BookStatus.ANALYZING
                db.commit()

            # 执行分析
            analyzer = DeepSeekAnalyzerService()
            text = chapter.cleaned_text or chapter.raw_text or ""
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
        from services.svc_voice_mapper import VoiceMapper

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        try:
            analysis = chapter.analysis_result or {}
            paragraphs = analysis.get("paragraphs", [])

            # 声音映射器
            voice_mapper = VoiceMapper()

            segments_created = 0
            for idx, para in enumerate(paragraphs):
                # 创建音频片段
                segment = AudioSegmentModel(
                    chapter_id=chapter_id,
                    segment_index=idx,
                    text_content=para.get("text", ""),
                    role=para.get("role", "narrator"),
                    emotion=para.get("emotion", "neutral"),
                    voice_id=voice_mapper.get_voice_id(
                        para.get("role", "narrator"),
                        para.get("gender", "neutral"),
                    ),
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
    max_retries=3,
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

            # TTS 合成
            tts_service = MiniMaxTTSService()
            audio_data = tts_service.synthesize(
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
            logger.error(f"[Segment {segment_id}] TTS 合成失败: {e}")
            segment.status = SegmentStatus.FAILED
            segment.error_message = str(e)
            segment.retry_count = (segment.retry_count or 0) + 1
            db.commit()
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
    queue="pipeline",
    max_retries=1,
)
def generate_audiobook(self, book_id: int) -> Dict[str, Any]:
    """
    生成有声书完整流水线

    串联所有阶段，完成从 EPUB 到有声书的全流程：

    1. EPUB 解析 → 2. 文本预处理 → 3. DeepSeek 分析 →
    4. 创建片段 → 5. TTS 合成 → 6. 音频后处理 → 7. 发布

    Args:
        book_id: 书籍ID

    Returns:
        dict: 流水线执行结果
    """
    import time
    stage_timings = {}  # 各阶段耗时统计
    total_start_time = time.time()

    logger.info(f"=" * 60)
    logger.info(f"[Book {book_id}] 开始有声书生成流水线")
    logger.info(f"=" * 60)

    from models import Book, Chapter, AudioSegment
    from models.model_book import BookStatus
    from models.model_chapter import ChapterStatus
    from models.model_segment import SegmentStatus

    with get_db_context() as db:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {book_id}")

        book.status = BookStatus.PENDING
        book.updated_at = datetime.utcnow()
        db.commit()

    try:
        # ========== 阶段一：解析 EPUB ==========
        stage_start = time.time()
        logger.info(f"[Book {book_id}] === 阶段一：EPUB 解析 ===")
        parse_result = parse_epub(book_id)
        chapter_ids = parse_result["chapter_ids"]
        stage_timings["parsing"] = time.time() - stage_start

        if not chapter_ids:
            raise ValueError("EPUB 解析后没有找到章节")

        logger.info(f"[Book {book_id}] 阶段一完成，耗时 {stage_timings['parsing']:.2f}s，共 {len(chapter_ids)} 章节")

        # ========== 阶段二：预处理所有章节（并行） ==========
        stage_start = time.time()
        logger.info(f"[Book {book_id}] === 阶段二：文本预处理 ===")
        preprocess_group = group(
            preprocess_chapter.s(ch_id) for ch_id in chapter_ids
        )
        preprocess_result = preprocess_group.apply_async()
        logger.info(f"[Book {book_id}] 预处理任务已提交，等待完成...")

        try:
            preprocess_result.get(timeout=1800)  # 最多等待 30 分钟
        except Exception as e:
            logger.error(f"[Book {book_id}] 预处理阶段失败: {e}")
            raise

        stage_timings["preprocessing"] = time.time() - stage_start
        logger.info(f"[Book {book_id}] 阶段二完成，耗时 {stage_timings['preprocessing']:.2f}s")

        # ========== 阶段三：分析所有章节（并行） ==========
        stage_start = time.time()
        logger.info(f"[Book {book_id}] === 阶段三：DeepSeek 分析 ===")
        analyze_group = group(analyze_chapter.s(ch_id) for ch_id in chapter_ids)
        analyze_result = analyze_group.apply_async()
        logger.info(f"[Book {book_id}] DeepSeek 分析任务已提交，等待完成...")

        try:
            analyze_result.get(timeout=3600)  # 最多等待 1 小时
        except Exception as e:
            logger.error(f"[Book {book_id}] DeepSeek 分析阶段失败: {e}")
            raise

        stage_timings["analyzing"] = time.time() - stage_start
        logger.info(f"[Book {book_id}] 阶段三完成，耗时 {stage_timings['analyzing']:.2f}s")

        # ========== 阶段四：创建音频片段 ==========
        stage_start = time.time()
        logger.info(f"[Book {book_id}] === 阶段四：创建音频片段 ===")
        create_group = group(create_segments.s(ch_id) for ch_id in chapter_ids)
        create_result = create_group.apply_async()
        logger.info(f"[Book {book_id}] 创建片段任务已提交，等待完成...")

        try:
            create_result.get(timeout=600)  # 最多等待 10 分钟
        except Exception as e:
            logger.error(f"[Book {book_id}] 创建音频片段阶段失败: {e}")
            raise

        stage_timings["creating_segments"] = time.time() - stage_start
        logger.info(f"[Book {book_id}] 阶段四完成，耗时 {stage_timings['creating_segments']:.2f}s")

        # 获取所有片段 ID（确保所有片段已创建）
        with get_db_context() as db:
            segments = db.query(AudioSegment).filter(
                AudioSegment.chapter_id.in_(chapter_ids)
            ).all()
            segment_ids = [seg.id for seg in segments]

        if not segment_ids:
            raise ValueError(f"[Book {book_id}] 创建音频片段后未找到任何片段，请检查阶段三、四的执行结果")

        logger.info(f"[Book {book_id}] 共创建 {len(segment_ids)} 个音频片段")

        # ========== 阶段五：TTS 合成（并行） ==========
        stage_start = time.time()
        logger.info(f"[Book {book_id}] === 阶段五：TTS 合成 ===")
        synthesize_group = group(
            synthesize_segment.s(seg_id) for seg_id in segment_ids
        )
        synthesize_result = synthesize_group.apply_async()
        logger.info(f"[Book {book_id}] TTS 合成任务已提交，共 {len(segment_ids)} 个片段")

        try:
            synthesize_result.get(timeout=7200)  # 最多等待 2 小时
        except Exception as e:
            logger.error(f"[Book {book_id}] TTS 合成阶段失败: {e}")
            raise

        stage_timings["synthesizing"] = time.time() - stage_start
        logger.info(f"[Book {book_id}] 阶段五完成，耗时 {stage_timings['synthesizing']:.2f}s")

        # ========== 阶段六：音频后处理 ==========
        stage_start = time.time()
        logger.info(f"[Book {book_id}] === 阶段六：音频后处理 ===")
        postprocess_group = group(
            postprocess_chapter.s(ch_id) for ch_id in chapter_ids
        )
        postprocess_result = postprocess_group.apply_async()

        try:
            postprocess_result.get(timeout=3600)  # 最多等待 1 小时
        except Exception as e:
            logger.error(f"[Book {book_id}] 音频后处理阶段失败: {e}")
            raise

        stage_timings["postprocessing"] = time.time() - stage_start
        logger.info(f"[Book {book_id}] 阶段六完成，耗时 {stage_timings['postprocessing']:.2f}s")

        # ========== 阶段七：自动发布 ==========
        stage_start = time.time()
        logger.info(f"[Book {book_id}] === 阶段七：自动发布 ===")
        publish_result = publish_book(book_id)
        stage_timings["publishing"] = time.time() - stage_start
        logger.info(f"[Book {book_id}] 阶段七完成，耗时 {stage_timings['publishing']:.2f}s")

        # ========== 汇总统计 ==========
        total_duration = time.time() - total_start_time
        estimated_cost = 0

        # 更新最终状态和统计信息
        with get_db_context() as db:
            from sqlalchemy import func
            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                book.status = BookStatus.DONE
                book.updated_at = datetime.utcnow()

                # 计算总音频时长
                total_duration_audio = (
                    db.query(func.sum(Chapter.audio_duration))
                    .filter(Chapter.book_id == book_id)
                    .scalar()
                    or 0
                )
                book.total_duration = total_duration_audio

                # 计算总成本
                total_deepseek_tokens = (
                    db.query(func.sum(Chapter.deepseek_tokens))
                    .filter(Chapter.book_id == book_id)
                    .scalar()
                    or 0
                )
                total_minimax_chars = (
                    db.query(func.sum(Chapter.minimax_characters))
                    .filter(Chapter.book_id == book_id)
                    .scalar()
                    or 0
                )
                # DeepSeek: ¥1/1M tokens → 以分为单位存储
                # MiniMax: ¥0.2/千字符 → 以分为单位存储
                estimated_cost = int(
                    total_deepseek_tokens / 1_000_000 * 100 +
                    total_minimax_chars / 1000 * 0.2 * 100
                )
                book.estimated_cost = estimated_cost
                db.commit()

        logger.info(f"=" * 60)
        logger.info(f"[Book {book_id}] 有声书生成流水线完成!")
        logger.info(f"[Book {book_id}] 总耗时: {total_duration:.2f}s ({total_duration/60:.1f}分钟)")
        logger.info(f"[Book {book_id}] 各阶段耗时:")
        for stage, duration in stage_timings.items():
            percentage = (duration / total_duration) * 100
            logger.info(f"  - {stage}: {duration:.2f}s ({percentage:.1f}%)")
        logger.info(f"=" * 60)

        return {
            "book_id": book_id,
            "chapter_count": len(chapter_ids),
            "segment_count": len(segment_ids),
            "total_duration_seconds": int(total_duration),
            "total_audio_duration_seconds": total_duration_audio,
            "estimated_cost_cents": estimated_cost,
            "stage_timings": {k: round(v, 2) for k, v in stage_timings.items()},
            "pipeline_stages": [s.value for s in PipelineStage if s != PipelineStage.FAILED],
            "success": True,
        }

    except Exception as e:
        total_duration = time.time() - total_start_time
        logger.error(f"[Book {book_id}] 流水线执行失败: {e} (耗时: {total_duration:.2f}s)")
        _update_book_error(book_id, str(e))
        raise


@celery_app.task(
    bind=True,
    base=PipelineTask,
    name="tasks.task_pipeline.generate_audiobook_simple",
    queue="pipeline",
)
def generate_audiobook_simple(self, book_id: int) -> Dict[str, Any]:
    """
    简化版有声书生成（同步调用完整流水线）

    直接调用 generate_audiobook，适合不需要 Celery Chain 异步调用的场景。

    Args:
        book_id: 书籍ID

    Returns:
        dict: 执行结果
    """
    logger.info(f"[Book {book_id}] 启动简化版生成流水线")

    try:
        result = generate_audiobook(book_id)
        return {
            "book_id": book_id,
            "task_id": self.request.id,
            "status": "completed",
            "result": result,
        }
    except Exception as e:
        logger.error(f"[Book {book_id}] 简化版流水线执行失败: {e}")
        return {
            "book_id": book_id,
            "task_id": self.request.id,
            "status": "failed",
            "error": str(e),
        }


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
