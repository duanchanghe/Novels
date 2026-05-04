# ===========================================
# 数据库仓储实现
# ===========================================

"""
数据库仓储实现 - Django ORM

提供具体的数据库访问实现。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from django.db.models import QuerySet, F

from core.models import (
    Book, Chapter, AudioSegment,
    PublishChannel, PublishRecord, VoiceProfile,
    BookStatus, ChapterStatus, SegmentStatus,
)


class BookRepository:
    """书籍仓储实现"""

    def __init__(self):
        self.model = Book

    def get_by_id(self, book_id: int) -> Optional[Book]:
        """根据 ID 获取书籍"""
        try:
            return Book.objects.get(id=book_id, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return None

    def get_by_hash(self, file_hash: str) -> Optional[Book]:
        """根据文件哈希获取书籍"""
        try:
            return Book.objects.get(file_hash=file_hash, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return None

    def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str = None,
        search: str = None,
        source_type: str = None,
    ) -> Dict[str, Any]:
        """获取书籍列表"""
        queryset = Book.objects.filter(deleted_at__isnull=True)

        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(title__icontains=search) | queryset.filter(author__icontains=search)
        if source_type:
            queryset = queryset.filter(source_type=source_type)

        total = queryset.count()
        offset = page_size * (page - 1)
        items = queryset.order_by("-created_at")[offset : offset + page_size]

        return {
            "items": list(items),
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_by_source_type(self, source_type: str) -> List[Book]:
        """根据来源类型获取书籍"""
        return list(
            Book.objects.filter(source_type=source_type, deleted_at__isnull=True)
        )

    def get_pending_books(self, limit: int = 100) -> List[Book]:
        """获取待处理的书籍"""
        return list(
            Book.objects.filter(status__in=[BookStatus.PENDING, BookStatus.FAILED])
            .filter(deleted_at__isnull=True)
            .order_by("created_at")[:limit]
        )

    def update_status(self, book_id: int, status: str) -> bool:
        """更新书籍状态"""
        updated = Book.objects.filter(id=book_id).update(status=status)
        return updated > 0

    def update_progress(self, book_id: int, processed_chapters: int) -> bool:
        """更新处理进度"""
        updated = Book.objects.filter(id=book_id).update(
            processed_chapters=processed_chapters,
            updated_at=datetime.now(),
        )
        return updated > 0

    def soft_delete(self, book_id: int) -> bool:
        """软删除书籍"""
        updated = Book.objects.filter(id=book_id).update(
            deleted_at=datetime.now()
        )
        return updated > 0

    def create(self, **kwargs) -> Book:
        """创建书籍"""
        return Book.objects.create(**kwargs)

    def update(self, book: Book, **kwargs) -> Book:
        """更新书籍"""
        for key, value in kwargs.items():
            setattr(book, key, value)
        book.save()
        return book


class ChapterRepository:
    """章节仓储实现"""

    def __init__(self):
        self.model = Chapter

    def get_by_id(self, chapter_id: int) -> Optional[Chapter]:
        """根据 ID 获取章节"""
        try:
            return Chapter.objects.get(id=chapter_id)
        except Chapter.DoesNotExist:
            return None

    def get_by_book(self, book_id: int) -> List[Chapter]:
        """获取书籍的所有章节"""
        return list(
            Chapter.objects.filter(book_id=book_id).order_by("chapter_index")
        )

    def get_by_book_and_index(self, book_id: int, chapter_index: int) -> Optional[Chapter]:
        """根据书籍和章节序号获取章节"""
        try:
            return Chapter.objects.get(book_id=book_id, chapter_index=chapter_index)
        except Chapter.DoesNotExist:
            return None

    def get_pending_chapters(self, book_id: int = None, limit: int = 100) -> List[Chapter]:
        """获取待处理的章节"""
        queryset = Chapter.objects.filter(status=ChapterStatus.PENDING)
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        return list(queryset.order_by("book_id", "chapter_index")[:limit])

    def get_by_status(self, status: str, book_id: int = None) -> List[Chapter]:
        """根据状态获取章节"""
        queryset = Chapter.objects.filter(status=status)
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        return list(queryset.order_by("book_id", "chapter_index"))

    def get_list(
        self,
        book_id: int,
        page: int = 1,
        page_size: int = 50,
        status: str = None,
    ) -> Dict[str, Any]:
        """获取章节列表"""
        queryset = Chapter.objects.filter(book_id=book_id)

        if status:
            queryset = queryset.filter(status=status)

        total = queryset.count()
        offset = page_size * (page - 1)
        items = queryset.order_by("chapter_index")[offset : offset + page_size]

        return {
            "items": list(items),
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def update_status(self, chapter_id: int, status: str) -> bool:
        """更新章节状态"""
        updated = Chapter.objects.filter(id=chapter_id).update(
            status=status, updated_at=datetime.now()
        )
        return updated > 0

    def update_analysis_result(self, chapter_id: int, result: Dict[str, Any]) -> bool:
        """更新分析结果"""
        updated = Chapter.objects.filter(id=chapter_id).update(
            analysis_result=result,
            characters=result.get("characters", []),
            updated_at=datetime.now(),
        )
        return updated > 0

    def update_audio_info(self, chapter_id: int, audio_path: str, duration: int) -> bool:
        """更新音频信息"""
        updated = Chapter.objects.filter(id=chapter_id).update(
            audio_file_path=audio_path,
            audio_duration=duration,
            updated_at=datetime.now(),
        )
        return updated > 0

    def update_progress(self, chapter_id: int, completed: int, failed: int = 0) -> bool:
        """更新进度"""
        updated = Chapter.objects.filter(id=chapter_id).update(
            completed_segments=completed,
            failed_segments=failed,
            updated_at=datetime.now(),
        )
        return updated > 0

    def create(self, **kwargs) -> Chapter:
        """创建章节"""
        return Chapter.objects.create(**kwargs)

    def create_bulk(self, chapters: List[Dict[str, Any]]) -> List[Chapter]:
        """批量创建章节"""
        return Chapter.objects.bulk_create(
            [Chapter(**ch) for ch in chapters]
        )


class SegmentRepository:
    """音频片段仓储实现"""

    def __init__(self):
        self.model = AudioSegment

    def get_by_id(self, segment_id: int) -> Optional[AudioSegment]:
        """根据 ID 获取片段"""
        try:
            return AudioSegment.objects.get(id=segment_id)
        except AudioSegment.DoesNotExist:
            return None

    def get_by_chapter(self, chapter_id: int) -> List[AudioSegment]:
        """获取章节的所有片段"""
        return list(
            AudioSegment.objects.filter(chapter_id=chapter_id).order_by("segment_index")
        )

    def get_pending_segments(self, chapter_id: int = None, limit: int = 100) -> List[AudioSegment]:
        """获取待处理的片段"""
        queryset = AudioSegment.objects.filter(status=SegmentStatus.PENDING)
        if chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)
        return list(queryset.order_by("chapter_id", "segment_index")[:limit])

    def get_by_status(self, status: str, chapter_id: int = None) -> List[AudioSegment]:
        """根据状态获取片段"""
        queryset = AudioSegment.objects.filter(status=status)
        if chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)
        return list(queryset.order_by("chapter_id", "segment_index"))

    def create(self, **kwargs) -> AudioSegment:
        """创建片段"""
        return AudioSegment.objects.create(**kwargs)

    def create_bulk(self, segments: List[Dict[str, Any]]) -> List[AudioSegment]:
        """批量创建片段"""
        return AudioSegment.objects.bulk_create(
            [AudioSegment(**seg) for seg in segments]
        )

    def update_status(self, segment_id: int, status: str) -> bool:
        """更新片段状态"""
        updated = AudioSegment.objects.filter(id=segment_id).update(
            status=status, updated_at=datetime.now()
        )
        return updated > 0

    def update_audio_info(
        self,
        segment_id: int,
        audio_path: str,
        duration_ms: int,
        file_size: int = None,
    ) -> bool:
        """更新音频信息"""
        kwargs = {
            "audio_file_path": audio_path,
            "audio_duration_ms": duration_ms,
            "updated_at": datetime.now(),
        }
        if file_size:
            kwargs["audio_file_size"] = file_size

        updated = AudioSegment.objects.filter(id=segment_id).update(**kwargs)
        return updated > 0

    def increment_retry(self, segment_id: int) -> bool:
        """增加重试次数"""
        updated = AudioSegment.objects.filter(id=segment_id).update(
            retry_count=F("retry_count") + 1,
            updated_at=datetime.now(),
        )
        return updated > 0


class ChannelRepository:
    """发布渠道仓储实现"""

    def __init__(self):
        self.model = PublishChannel

    def get_by_id(self, channel_id: int) -> Optional[PublishChannel]:
        """根据 ID 获取渠道"""
        try:
            return PublishChannel.objects.get(id=channel_id)
        except PublishChannel.DoesNotExist:
            return None

    def get_enabled_channels(self) -> List[PublishChannel]:
        """获取所有启用的渠道"""
        return list(
            PublishChannel.objects.filter(is_enabled=True).order_by("-priority")
        )

    def get_auto_publish_channels(self) -> List[PublishChannel]:
        """获取支持自动发布的渠道"""
        return list(
            PublishChannel.objects.filter(
                is_enabled=True, auto_publish=True
            ).order_by("-priority")
        )

    def create(self, **kwargs) -> PublishChannel:
        """创建渠道"""
        return PublishChannel.objects.create(**kwargs)

    def update(self, channel: PublishChannel, **kwargs) -> PublishChannel:
        """更新渠道"""
        for key, value in kwargs.items():
            setattr(channel, key, value)
        channel.save()
        return channel


class RecordRepository:
    """发布记录仓储实现"""

    def __init__(self):
        self.model = PublishRecord

    def get_by_id(self, record_id: int) -> Optional[PublishRecord]:
        """根据 ID 获取记录"""
        try:
            return PublishRecord.objects.get(id=record_id)
        except PublishRecord.DoesNotExist:
            return None

    def get_by_book(self, book_id: int) -> List[PublishRecord]:
        """获取书籍的所有发布记录"""
        return list(
            PublishRecord.objects.filter(book_id=book_id).order_by("-created_at")
        )

    def get_by_channel(self, channel_id: int) -> List[PublishRecord]:
        """获取渠道的所有发布记录"""
        return list(
            PublishRecord.objects.filter(channel_id=channel_id).order_by("-created_at")
        )

    def get_by_book_and_channel(self, book_id: int, channel_id: int) -> Optional[PublishRecord]:
        """根据书籍和渠道获取记录"""
        try:
            return PublishRecord.objects.get(book_id=book_id, channel_id=channel_id)
        except PublishRecord.DoesNotExist:
            return None

    def create(self, **kwargs) -> PublishRecord:
        """创建记录"""
        return PublishRecord.objects.create(**kwargs)

    def update(self, record: PublishRecord, **kwargs) -> PublishRecord:
        """更新记录"""
        for key, value in kwargs.items():
            setattr(record, key, value)
        record.save()
        return record


class VoiceProfileRepository:
    """音色配置仓储实现"""

    def __init__(self):
        self.model = VoiceProfile

    def get_by_id(self, profile_id: int) -> Optional[VoiceProfile]:
        """根据 ID 获取音色配置"""
        try:
            return VoiceProfile.objects.get(id=profile_id)
        except VoiceProfile.DoesNotExist:
            return None

    def get_system_presets(self) -> List[VoiceProfile]:
        """获取系统预设音色"""
        return list(
            VoiceProfile.objects.filter(is_system_preset=True).order_by("sort_order")
        )

    def get_by_book(self, book_id: int) -> List[VoiceProfile]:
        """获取书籍的自定义音色"""
        return list(
            VoiceProfile.objects.filter(book_id=book_id).order_by("sort_order")
        )

    def get_by_role_type(self, role_type: str) -> List[VoiceProfile]:
        """根据角色类型获取音色"""
        return list(
            VoiceProfile.objects.filter(role_type=role_type, is_active=True)
        )

    def create(self, **kwargs) -> VoiceProfile:
        """创建音色配置"""
        return VoiceProfile.objects.create(**kwargs)
