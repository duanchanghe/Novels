# ===========================================
# MiniMax TTS 合成任务
# ===========================================

"""
MiniMax TTS 合成 Celery 任务

处理音频片段的语音合成。
"""

import logging
from typing import Dict, Any

from celery import Task
from celery.exceptions import MaxRetriesExceededError

from tasks.celery_app import app as celery_app
from core.exceptions import MiniMaxAPIError as MiniMaxApiError


logger = logging.getLogger("audiobook")


class SynthesizeTask(Task):
    """
    TTS 合成任务基类

    提供重试逻辑和错误处理。
    """

    autoretry_for = (MiniMaxApiError, ConnectionError, TimeoutError)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=SynthesizeTask,
    name="tasks.task_synthesize.synthesize_segment",
    queue="synthesize",
    max_retries=3,
)
def synthesize_segment(self, segment_id: int) -> Dict[str, Any]:
    """
    合成单个音频片段

    Args:
        segment_id: 音频片段ID

    Returns:
        dict: 合成结果
    """
    logger.info(f"开始合成音频片段: {segment_id}")

    from core.models import AudioSegment
    from core.models.segment import SegmentStatus

    # 使用 Django ORM 直接操作
    segment = AudioSegment.objects.get(id=segment_id)

    try:
        # 更新状态为处理中
        segment.status = SegmentStatus.SYNTHESIZING
        segment.save(update_fields=['status', 'updated_at'])

        # 执行 TTS 合成
        from services.svc_minimax_tts import MiniMaxTTSService

        tts_service = MiniMaxTTSService()
        audio_data = tts_service.synthesize_sync(
            text=segment.text_content,
            voice_id=segment.voice_id,
            speed=segment.speed,
            emotion=segment.emotion,
        )

        # 保存音频文件
        from services.svc_minio_storage import get_storage_service
        from datetime import datetime
        import uuid

        storage = get_storage_service()
        object_name = f"segments/{segment.chapter_id}/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.mp3"

        storage.upload_file(
            bucket="books-audio",
            object_name=object_name,
            data=audio_data,
            content_type="audio/mpeg",
        )

        # 更新片段状态为成功
        segment.status = SegmentStatus.SUCCESS
        segment.audio_file_path = object_name
        segment.audio_url = storage.get_presigned_url("books-audio", object_name)
        segment.updated_at = datetime.utcnow()
        segment.save()

        logger.info(f"音频片段合成完成: {segment_id}")
        return {
            "segment_id": segment_id,
            "audio_file_path": object_name,
            "success": True,
        }

    except Exception as e:
        logger.error(f"音频片段合成失败: {segment_id} - {e}")
        segment.status = SegmentStatus.FAILED
        segment.error_message = str(e)
        segment.retry_count = (segment.retry_count or 0) + 1
        segment.save()

        try:
            raise self.retry(exc=e)
        except MaxRetriesExceededError:
            raise MiniMaxApiError(f"音频片段合成重试次数耗尽: {segment_id}")


@celery_app.task(
    bind=True,
    base=SynthesizeTask,
    name="tasks.task_synthesize.synthesize_chapter",
    queue="synthesize",
)
def synthesize_chapter(self, chapter_id: int) -> Dict[str, Any]:
    """
    合成整个章节的所有音频片段

    Args:
        chapter_id: 章节ID

    Returns:
        dict: 合成结果汇总
    """
    logger.info(f"开始合成章节音频: {chapter_id}")

    from django.db import transaction
    from core.models import Chapter, AudioSegment, Book
    from core.models.chapter import ChapterStatus
    from core.models.book import BookStatus
    from core.models.segment import SegmentStatus

    with transaction.atomic():
        chapter = Chapter.objects.get(id=chapter_id)
        book = Book.objects.get(id=chapter.book_id)

        # 更新状态
        chapter.status = ChapterStatus.SYNTHESIZING
        book.status = BookStatus.SYNTHESIZING
        chapter.save(update_fields=['status', 'updated_at'])
        book.save(update_fields=['status', 'updated_at'])

        # 获取所有待合成的片段
        segments = (
            AudioSegment.objects
            .filter(chapter_id=chapter_id)
            .filter(status=SegmentStatus.PENDING)
            .order_by("segment_index")
        )

        results = []
        for segment in segments:
            try:
                result = synthesize_segment.delay(segment.id)
                results.append({"segment_id": segment.id, "task_id": result.id})
            except Exception as e:
                logger.error(f"提交合成任务失败: {segment.id} - {e}")
                results.append({"segment_id": segment.id, "task_id": None, "error": str(e)})

        logger.info(f"章节 {chapter_id} 已提交 {len(results)} 个合成任务")
        return {
            "chapter_id": chapter_id,
            "total_segments": segments.count(),
            "submitted_tasks": results,
        }
