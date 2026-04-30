# ===========================================
# 发布引擎服务
# ===========================================

"""
发布引擎服务

管理有声书到各平台的发布。
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from core.config import settings
from core.database import get_db_context
from core.exceptions import PublishError


logger = logging.getLogger("audiobook")


class BasePublisher(ABC):
    """
    发布渠道基类

    定义发布接口，各平台实现此接口。
    """

    @abstractmethod
    def get_channel_name(self) -> str:
        """获取渠道名称"""
        pass

    @abstractmethod
    async def create_album(self, book_data: Dict[str, Any]) -> str:
        """
        创建专辑

        Args:
            book_data: 书籍数据

        Returns:
            str: 外部专辑 ID
        """
        pass

    @abstractmethod
    async def upload_chapter(
        self,
        album_id: str,
        chapter_data: Dict[str, Any],
        audio_url: str,
    ) -> str:
        """
        上传章节音频

        Args:
            album_id: 专辑 ID
            chapter_data: 章节数据
            audio_url: 音频 URL

        Returns:
            str: 外部音频 ID
        """
        pass

    @abstractmethod
    async def publish(self, album_id: str) -> bool:
        """
        发布专辑

        Args:
            album_id: 专辑 ID

        Returns:
            bool: 是否发布成功
        """
        pass


class SelfHostedPublisher(BasePublisher):
    """
    自建平台发布器

    生成 MinIO 预签名 URL，无需实际发布操作。
    """

    def get_channel_name(self) -> str:
        return "自建平台"

    async def create_album(self, book_data: Dict[str, Any]) -> str:
        """自建平台无需创建专辑"""
        return "self-hosted"

    async def upload_chapter(
        self,
        album_id: str,
        chapter_data: Dict[str, Any],
        audio_url: str,
    ) -> str:
        """自建平台直接使用预签名 URL"""
        return audio_url

    async def publish(self, album_id: str) -> bool:
        """自建平台无需发布操作"""
        return True


class PublisherService:
    """
    发布服务

    管理发布流程和渠道调度。
    """

    # 渠道注册表
    PUBLISHERS = {
        "self_hosted": SelfHostedPublisher,
        # 可扩展其他平台
        # "ximalaya": XimalayaPublisher,
        # "qingting": QingtingPublisher,
    }

    def __init__(self):
        self.publishers = {name: cls() for name, cls in self.PUBLISHERS.items()}

    def get_publisher(self, platform_type: str) -> Optional[BasePublisher]:
        """
        获取发布器

        Args:
            platform_type: 平台类型

        Returns:
            BasePublisher: 发布器实例
        """
        return self.publishers.get(platform_type)

    async def publish_book(
        self,
        book_id: int,
        channel_id: int,
    ) -> Dict[str, Any]:
        """
        发布书籍到指定渠道

        Args:
            book_id: 书籍 ID
            channel_id: 渠道 ID

        Returns:
            dict: 发布结果
        """
        from models import Book, Chapter, PublishChannel, ChapterStatus

        with get_db_context() as db:
            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                raise PublishError(f"书籍不存在: {book_id}")

            channel = db.query(PublishChannel).filter(PublishChannel.id == channel_id).first()
            if not channel:
                raise PublishError(f"发布渠道不存在: {channel_id}")

            # 获取发布器
            publisher = self.get_publisher(channel.platform_type.value)
            if not publisher:
                raise PublishError(f"不支持的平台类型: {channel.platform_type}")

            # 准备书籍数据
            book_data = {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "description": book.description,
                "cover_url": book.cover_image_url,
                "total_chapters": book.total_chapters,
            }

            # 创建专辑
            album_id = await publisher.create_album(book_data)

            # 获取所有已完成的章节
            chapters = (
                db.query(Chapter)
                .filter(Chapter.book_id == book_id)
                .filter(Chapter.status == ChapterStatus.DONE)
                .order_by(Chapter.chapter_index)
                .all()
            )

            # 上传章节
            published_chapters = []
            for chapter in chapters:
                chapter_data = {
                    "id": chapter.id,
                    "title": chapter.title,
                    "index": chapter.chapter_index,
                    "duration": chapter.audio_duration,
                }

                # 获取音频 URL
                from services.svc_minio_storage import get_storage_service
                storage = get_storage_service()

                if chapter.audio_file_path:
                    audio_url = storage.get_presigned_url(
                        settings.MINIO_BUCKET_AUDIO,
                        chapter.audio_file_path,
                    )
                else:
                    audio_url = None

                if audio_url:
                    external_id = await publisher.upload_chapter(
                        album_id,
                        chapter_data,
                        audio_url,
                    )
                    published_chapters.append({
                        "chapter_id": chapter.id,
                        "external_id": external_id,
                    })

            # 发布专辑
            await publisher.publish(album_id)

            logger.info(
                f"书籍发布完成: book_id={book_id}, "
                f"channel={channel.name}, "
                f"chapters={len(published_chapters)}"
            )

            return {
                "album_id": album_id,
                "album_url": f"/books/{book_id}/player",
                "published_chapters": len(published_chapters),
            }

    def get_publish_status(self, book_id: int) -> Dict[str, Any]:
        """
        获取发布状态

        Args:
            book_id: 书籍 ID

        Returns:
            dict: 发布状态
        """
        from models import PublishRecord, PublishStatus

        with get_db_context() as db:
            records = db.query(PublishRecord).filter(
                PublishRecord.book_id == book_id
            ).all()

            return {
                "book_id": book_id,
                "channels": [
                    {
                        "channel_id": r.channel_id,
                        "status": r.status.value,
                        "progress": r.progress_percentage,
                        "published_chapters": r.published_chapters,
                        "total_chapters": r.total_chapters,
                    }
                    for r in records
                ],
            }
