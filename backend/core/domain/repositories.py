# ===========================================
# 仓储接口定义
# ===========================================

"""
仓储接口 - 数据访问抽象

仓储模式将数据访问逻辑抽象为接口，
使得领域逻辑与具体的数据存储技术解耦。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from datetime import datetime

from .models import (
    BookModel,
    ChapterModel,
    SegmentModel,
    PublishChannelModel,
    PublishRecordModel,
    VoiceProfileModel,
)

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """
    仓储基类接口

    定义通用的 CRUD 操作。
    """

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        """根据 ID 获取单个实体"""
        pass

    @abstractmethod
    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """获取所有实体"""
        pass

    @abstractmethod
    def create(self, entity: T) -> T:
        """创建实体"""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """更新实体"""
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    def count(self) -> int:
        """统计数量"""
        pass


class IBookRepository(IRepository[BookModel]):
    """
    书籍仓储接口

    定义书籍相关的数据访问操作。
    """

    @abstractmethod
    def get_by_id(self, book_id: int) -> Optional[BookModel]:
        """根据 ID 获取书籍"""
        pass

    @abstractmethod
    def get_by_hash(self, file_hash: str) -> Optional[BookModel]:
        """根据文件哈希获取书籍"""
        pass

    @abstractmethod
    def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str = None,
        search: str = None,
        source_type: str = None,
    ) -> Dict[str, Any]:
        """
        获取书籍列表

        Returns:
            dict: {
                "items": List[BookModel],
                "total": int,
                "page": int,
                "page_size": int,
            }
        """
        pass

    @abstractmethod
    def get_by_source_type(self, source_type: str) -> List[BookModel]:
        """根据来源类型获取书籍"""
        pass

    @abstractmethod
    def get_pending_books(self, limit: int = 100) -> List[BookModel]:
        """获取待处理的书籍"""
        pass

    @abstractmethod
    def update_status(self, book_id: int, status: str) -> bool:
        """更新书籍状态"""
        pass

    @abstractmethod
    def update_progress(self, book_id: int, processed_chapters: int) -> bool:
        """更新处理进度"""
        pass

    @abstractmethod
    def soft_delete(self, book_id: int) -> bool:
        """软删除书籍"""
        pass


class IChapterRepository(IRepository[ChapterModel]):
    """
    章节仓储接口

    定义章节相关的数据访问操作。
    """

    @abstractmethod
    def get_by_id(self, chapter_id: int) -> Optional[ChapterModel]:
        """根据 ID 获取章节"""
        pass

    @abstractmethod
    def get_by_book(self, book_id: int) -> List[ChapterModel]:
        """获取书籍的所有章节"""
        pass

    @abstractmethod
    def get_by_book_and_index(self, book_id: int, chapter_index: int) -> Optional[ChapterModel]:
        """根据书籍和章节序号获取章节"""
        pass

    @abstractmethod
    def get_pending_chapters(self, book_id: int = None, limit: int = 100) -> List[ChapterModel]:
        """获取待处理的章节"""
        pass

    @abstractmethod
    def get_by_status(self, status: str, book_id: int = None) -> List[ChapterModel]:
        """根据状态获取章节"""
        pass

    @abstractmethod
    def get_list(
        self,
        book_id: int,
        page: int = 1,
        page_size: int = 50,
        status: str = None,
    ) -> Dict[str, Any]:
        """
        获取章节列表

        Returns:
            dict: {
                "items": List[ChapterModel],
                "total": int,
                "page": int,
                "page_size": int,
            }
        """
        pass

    @abstractmethod
    def update_status(self, chapter_id: int, status: str) -> bool:
        """更新章节状态"""
        pass

    @abstractmethod
    def update_analysis_result(self, chapter_id: int, result: Dict[str, Any]) -> bool:
        """更新分析结果"""
        pass

    @abstractmethod
    def update_audio_info(self, chapter_id: int, audio_path: str, duration: int) -> bool:
        """更新音频信息"""
        pass

    @abstractmethod
    def update_progress(self, chapter_id: int, completed: int, failed: int = 0) -> bool:
        """更新进度"""
        pass


class ISegmentRepository(IRepository[SegmentModel]):
    """
    音频片段仓储接口

    定义音频片段相关的数据访问操作。
    """

    @abstractmethod
    def get_by_id(self, segment_id: int) -> Optional[SegmentModel]:
        """根据 ID 获取片段"""
        pass

    @abstractmethod
    def get_by_chapter(self, chapter_id: int) -> List[SegmentModel]:
        """获取章节的所有片段"""
        pass

    @abstractmethod
    def get_pending_segments(self, chapter_id: int = None, limit: int = 100) -> List[SegmentModel]:
        """获取待处理的片段"""
        pass

    @abstractmethod
    def get_by_status(self, status: str, chapter_id: int = None) -> List[SegmentModel]:
        """根据状态获取片段"""
        pass

    @abstractmethod
    def create_bulk(self, segments: List[SegmentModel]) -> List[SegmentModel]:
        """批量创建片段"""
        pass

    @abstractmethod
    def update_status(self, segment_id: int, status: str) -> bool:
        """更新片段状态"""
        pass

    @abstractmethod
    def update_audio_info(
        self,
        segment_id: int,
        audio_path: str,
        duration_ms: int,
        file_size: int = None,
    ) -> bool:
        """更新音频信息"""
        pass

    @abstractmethod
    def increment_retry(self, segment_id: int) -> bool:
        """增加重试次数"""
        pass


class IPublishChannelRepository(IRepository[PublishChannelModel]):
    """
    发布渠道仓储接口

    定义发布渠道相关的数据访问操作。
    """

    @abstractmethod
    def get_enabled_channels(self) -> List[PublishChannelModel]:
        """获取所有启用的渠道"""
        pass

    @abstractmethod
    def get_auto_publish_channels(self) -> List[PublishChannelModel]:
        """获取支持自动发布的渠道"""
        pass


class IPublishRecordRepository(IRepository[PublishRecordModel]):
    """
    发布记录仓储接口

    定义发布记录相关的数据访问操作。
    """

    @abstractmethod
    def get_by_book(self, book_id: int) -> List[PublishRecordModel]:
        """获取书籍的所有发布记录"""
        pass

    @abstractmethod
    def get_by_channel(self, channel_id: int) -> List[PublishRecordModel]:
        """获取渠道的所有发布记录"""
        pass

    @abstractmethod
    def get_by_book_and_channel(self, book_id: int, channel_id: int) -> Optional[PublishRecordModel]:
        """根据书籍和渠道获取记录"""
        pass


class IVoiceProfileRepository(IRepository[VoiceProfileModel]):
    """
    音色配置仓储接口

    定义音色配置相关的数据访问操作。
    """

    @abstractmethod
    def get_system_presets(self) -> List[VoiceProfileModel]:
        """获取系统预设音色"""
        pass

    @abstractmethod
    def get_by_book(self, book_id: int) -> List[VoiceProfileModel]:
        """获取书籍的自定义音色"""
        pass

    @abstractmethod
    def get_by_role_type(self, role_type: str) -> List[VoiceProfileModel]:
        """根据角色类型获取音色"""
        pass
