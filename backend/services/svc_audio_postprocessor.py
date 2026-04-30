# ===========================================
# 音频后处理服务
# ===========================================

"""
音频后处理服务

处理音频片段的拼接、混音、格式转换等。
"""

import logging
import os
from io import BytesIO
from typing import List, Dict, Any, Optional

from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range

from core.config import settings
from core.exceptions import AppError


logger = logging.getLogger("audiobook")


class AudioPostprocessorService:
    """
    音频后处理服务

    提供专业级音频处理功能：
    - 音频拼接（交叉淡入淡出）
    - 音量均衡
    - 降噪处理
    - 格式转换
    """

    def __init__(self):
        self.sample_rate = settings.AUDIO_SAMPLE_RATE
        self.bit_rate = settings.AUDIO_BITRATE
        self.crossfade_ms = settings.AUDIO_CROSSFADE_MS

    def process_chapter(self, chapter_id: int) -> Dict[str, Any]:
        """
        处理章节音频

        Args:
            chapter_id: 章节 ID

        Returns:
            dict: 处理结果
        """
        from core.database import get_db_context
        from models import Chapter, AudioSegment as SegmentModel, SegmentStatus

        with get_db_context() as db:
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                raise AppError(f"章节不存在: {chapter_id}")

            # 获取所有成功的音频片段
            segments = (
                db.query(SegmentModel)
                .filter(SegmentModel.chapter_id == chapter_id)
                .filter(SegmentModel.status == SegmentStatus.SUCCESS)
                .order_by(SegmentModel.segment_index)
                .all()
            )

            if not segments:
                raise AppError(f"章节没有可用的音频片段: {chapter_id}")

            # 下载音频片段
            from services.svc_minio_storage import get_storage_service
            storage = get_storage_service()

            audio_segments = []
            for segment in segments:
                audio_data = storage.download_file(
                    "books-audio",
                    segment.audio_file_path,
                )
                audio_segments.append(AudioSegment.from_mp3(BytesIO(audio_data)))

            # 拼接音频
            combined = self._concatenate_segments(audio_segments)

            # 音量均衡
            normalized = self._normalize_audio(combined)

            # 导出
            output_data = normalized.export(format="mp3", bitrate=f"{self.bit_rate}k").read()

            # 上传到 MinIO
            from datetime import datetime
            import uuid

            object_name = f"chapters/{chapter.book_id}/{chapter.chapter_index:03d}_{uuid.uuid4().hex[:8]}.mp3"
            storage.upload_file(
                "books-audio",
                object_name,
                output_data,
                content_type="audio/mpeg",
            )

            return {
                "audio_file_path": object_name,
                "duration_seconds": len(normalized) / 1000,
                "file_size": len(output_data),
            }

    def _concatenate_segments(
        self,
        segments: List[AudioSegment],
        crossfade_ms: int = None,
    ) -> AudioSegment:
        """
        拼接音频片段

        Args:
            segments: 音频片段列表
            crossfade_ms: 交叉淡入淡出时长（毫秒）

        Returns:
            AudioSegment: 拼接后的音频
        """
        if not segments:
            raise AppError("没有音频片段")

        if len(segments) == 1:
            return segments[0]

        crossfade_ms = crossfade_ms or self.crossfade_ms

        result = segments[0]
        for segment in segments[1:]:
            # 应用交叉淡入淡出
            result = result.append(segment, crossfade=crossfade_ms)

        return result

    def _normalize_audio(self, audio: AudioSegment) -> AudioSegment:
        """
        音量均衡处理

        Args:
            audio: 音频对象

        Returns:
            AudioSegment: 处理后的音频
        """
        # 标准化音量
        normalized = normalize(audio)

        # 应用轻微的动态范围压缩
        compressed = compress_dynamic_range(
            normalized,
            threshold=-20,
            ratio=2,
            attack=5,
            release=50,
        )

        return compressed

    def process_book(self, book_id: int) -> Dict[str, Any]:
        """
        处理整本书籍音频

        合并所有章节为一个完整的有声书文件。

        Args:
            book_id: 书籍 ID

        Returns:
            dict: 处理结果
        """
        from core.database import get_db_context
        from models import Chapter, Book, ChapterStatus

        with get_db_context() as db:
            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                raise AppError(f"书籍不存在: {book_id}")

            # 获取所有已完成章节
            chapters = (
                db.query(Chapter)
                .filter(Chapter.book_id == book_id)
                .filter(Chapter.status == ChapterStatus.DONE)
                .order_by(Chapter.chapter_index)
                .all()
            )

            if not chapters:
                raise AppError(f"书籍没有已完成的章节: {book_id}")

            # 合并所有章节音频
            combined_audio = None
            total_duration = 0

            from services.svc_minio_storage import get_storage_service
            storage = get_storage_service()

            for chapter in chapters:
                if chapter.audio_file_path:
                    audio_data = storage.download_file("books-audio", chapter.audio_file_path)
                    chapter_audio = AudioSegment.from_mp3(BytesIO(audio_data))

                    if combined_audio is None:
                        combined_audio = chapter_audio
                    else:
                        # 章节间添加 2 秒停顿
                        silence = AudioSegment.silent(duration=2000)
                        combined_audio = combined_audio + silence + chapter_audio

                    total_duration += len(chapter_audio)

            if combined_audio is None:
                raise AppError(f"没有可用的章节音频: {book_id}")

            # 导出完整有声书
            output_data = combined_audio.export(
                format="mp3",
                bitrate=f"{self.bit_rate}k",
            ).read()

            # 上传
            import uuid
            safe_title = "".join(c for c in book.title if c.isalnum() or c in " -_").strip()
            object_name = f"full/{book_id}/{safe_title}_{uuid.uuid4().hex[:8]}.mp3"

            storage.upload_file(
                "books-audio",
                object_name,
                output_data,
                content_type="audio/mpeg",
            )

            return {
                "full_audio_path": object_name,
                "total_duration_seconds": total_duration / 1000,
                "file_size": len(output_data),
            }
