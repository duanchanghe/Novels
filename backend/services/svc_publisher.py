# ===========================================
# 发布引擎服务 - 增强版
# ===========================================

"""
发布引擎服务 - 增强版

管理有声书到各平台的发布：
- 发布渠道抽象基类（Adapter 模式）
- 自建平台发布器
- 喜马拉雅开放平台（预留接口）
- 蜻蜓 FM（预留接口）
- 多渠道并行发布
- 发布状态追踪
- 错误重试机制
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from enum import Enum
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from core.config import settings
from core.database import get_db_context
from core.exceptions import PublishError


logger = logging.getLogger("audiobook")


class PublishStatus(str, Enum):
    """发布状态枚举"""
    PENDING = "pending"           # 等待发布
    PREPARING = "preparing"       # 准备中
    PUBLISHING = "publishing"    # 发布中
    PARTIAL_DONE = "partial_done" # 部分完成
    DONE = "done"               # 全部完成
    FAILED = "failed"           # 发布失败
    CANCELLED = "cancelled"     # 已取消


class BasePublisher(ABC):
    """
    发布渠道基类

    定义发布接口，各平台实现此接口。
    """

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """获取渠道名称"""
        pass

    @property
    @abstractmethod
    def channel_code(self) -> str:
        """获取渠道代码"""
        pass

    @abstractmethod
    async def create_album(
        self,
        book_data: Dict[str, Any],
        cover_image: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        创建专辑

        Args:
            book_data: 书籍数据
            cover_image: 封面图片

        Returns:
            dict: 包含 album_id, album_url 等
        """
        pass

    @abstractmethod
    async def upload_chapter(
        self,
        album_id: str,
        chapter_data: Dict[str, Any],
        audio_stream,
    ) -> Dict[str, Any]:
        """
        上传章节音频

        Args:
            album_id: 专辑 ID
            chapter_data: 章节数据
            audio_stream: 音频流

        Returns:
            dict: 包含 audio_id, audio_url 等
        """
        pass

    @abstractmethod
    async def publish_album(self, album_id: str) -> bool:
        """
        发布专辑

        Args:
            album_id: 专辑 ID

        Returns:
            bool: 是否发布成功
        """
        pass

    @abstractmethod
    async def get_publish_status(self, album_id: str) -> Dict[str, Any]:
        """
        获取发布状态

        Args:
            album_id: 专辑 ID

        Returns:
            dict: 状态信息
        """
        pass

    async def validate_config(self) -> bool:
        """
        验证配置是否正确

        Returns:
            bool: 配置是否有效
        """
        return True


class SelfHostedPublisher(BasePublisher):
    """
    自建平台发布器

    生成 MinIO 预签名 URL，无需实际发布操作。
    """

    @property
    def channel_name(self) -> str:
        return "自建平台"

    @property
    def channel_code(self) -> str:
        return "self_hosted"

    async def create_album(
        self,
        book_data: Dict[str, Any],
        cover_image: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        自建平台创建专辑

        生成预签名 URL 作为访问入口。
        """
        book_id = book_data.get("id")
        return {
            "album_id": f"self_{book_id}",
            "album_url": f"/books/{book_id}/player",
            "internal": True,
        }

    async def upload_chapter(
        self,
        album_id: str,
        chapter_data: Dict[str, Any],
        audio_stream,
    ) -> Dict[str, Any]:
        """
        自建平台上传章节

        返回预签名 URL。
        """
        from services.svc_minio_storage import get_storage_service
        storage = get_storage_service()

        chapter_path = chapter_data.get("audio_file_path")
        if not chapter_path:
            raise PublishError("章节音频路径不存在")

        presigned_url = storage.get_presigned_url(
            settings.MINIO_BUCKET_AUDIO,
            chapter_path,
        )

        return {
            "audio_id": f"audio_{chapter_data.get('id')}",
            "audio_url": presigned_url,
            "internal": True,
        }

    async def publish_album(self, album_id: str) -> bool:
        """自建平台无需发布"""
        return True

    async def get_publish_status(self, album_id: str) -> Dict[str, Any]:
        """自建平台状态查询"""
        return {
            "status": "done",
            "message": "自建平台无需发布",
        }


class XimalayaPublisher(BasePublisher):
    """
    喜马拉雅开放平台发布器

    待实现：需申请开发者 API 权限
    """

    @property
    def channel_name(self) -> str:
        return "喜马拉雅"

    @property
    def channel_code(self) -> str:
        return "ximalaya"

    async def create_album(
        self,
        book_data: Dict[str, Any],
        cover_image: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        创建喜马拉雅专辑

        TODO: 实现喜马拉雅 API 调用
        """
        raise NotImplementedError("喜马拉雅 API 尚未实现")

    async def upload_chapter(
        self,
        album_id: str,
        chapter_data: Dict[str, Any],
        audio_stream,
    ) -> Dict[str, Any]:
        """上传章节音频"""
        raise NotImplementedError("喜马拉雅 API 尚未实现")

    async def publish_album(self, album_id: str) -> bool:
        """发布专辑"""
        raise NotImplementedError("喜马拉雅 API 尚未实现")

    async def get_publish_status(self, album_id: str) -> Dict[str, Any]:
        """获取发布状态"""
        raise NotImplementedError("喜马拉雅 API 尚未实现")


class QingtingPublisher(BasePublisher):
    """
    蜻蜓 FM 发布器

    待实现：需申请开发者 API 权限
    """

    @property
    def channel_name(self) -> str:
        return "蜻蜓 FM"

    @property
    def channel_code(self) -> str:
        return "qingting"

    async def create_album(
        self,
        book_data: Dict[str, Any],
        cover_image: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """创建蜻蜓 FM 专辑"""
        raise NotImplementedError("蜻蜓 FM API 尚未实现")

    async def upload_chapter(
        self,
        album_id: str,
        chapter_data: Dict[str, Any],
        audio_stream,
    ) -> Dict[str, Any]:
        """上传章节音频"""
        raise NotImplementedError("蜻蜓 FM API 尚未实现")

    async def publish_album(self, album_id: str) -> bool:
        """发布专辑"""
        raise NotImplementedError("蜻蜓 FM API 尚未实现")

    async def get_publish_status(self, album_id: str) -> Dict[str, Any]:
        """获取发布状态"""
        raise NotImplementedError("蜻蜓 FM API 尚未实现")


class PublisherService:
    """
    发布服务

    管理发布流程和渠道调度。
    """

    # 渠道注册表
    PUBLISHERS: Dict[str, Type[BasePublisher]] = {
        "self_hosted": SelfHostedPublisher,
        "ximalaya": XimalayaPublisher,
        "qingting": QingtingPublisher,
        "lizhi": QingtingPublisher,  # 荔枝 FM 使用与蜻蜓 FM 相同的接口结构
        "custom": SelfHostedPublisher,  # 自定义平台使用自建平台模式
    }

    def __init__(self):
        self._publisher_instances: Dict[str, BasePublisher] = {}

    def get_publisher(self, platform_type: str) -> Optional[BasePublisher]:
        """
        获取发布器实例

        Args:
            platform_type: 平台类型

        Returns:
            BasePublisher: 发布器实例
        """
        if platform_type not in self._publisher_instances:
            publisher_class = self.PUBLISHERS.get(platform_type)
            if publisher_class:
                self._publisher_instances[platform_type] = publisher_class()

        return self._publisher_instances.get(platform_type)

    def list_available_channels(self) -> List[Dict[str, Any]]:
        """
        列出可用的发布渠道

        Returns:
            list: 渠道列表
        """
        return [
            {
                "code": code,
                "name": cls().channel_name,
                "available": True,
            }
            for code, cls in self.PUBLISHERS.items()
        ]

    async def publish_book(
        self,
        book_id: int,
        channel_id: int,
        auto_retry: bool = True,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        发布书籍到指定渠道（异步版本）

        Args:
            book_id: 书籍 ID
            channel_id: 渠道 ID
            auto_retry: 是否自动重试
            max_retries: 最大重试次数

        Returns:
            dict: 发布结果
        """
        from models import Book, Chapter, PublishChannel, PublishRecord, ChapterStatus

        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                return await self._do_publish(book_id, channel_id)
            except Exception as e:
                last_error = e
                retry_count += 1

                if not auto_retry or retry_count > max_retries:
                    break

                # 指数退避
                wait_time = min(60 * (2 ** retry_count), 600)
                logger.warning(
                    f"发布失败，等待 {wait_time} 秒后重试 "
                    f"({retry_count}/{max_retries}): {e}"
                )
                await asyncio.sleep(wait_time)

        # 记录失败
        raise PublishError(f"发布失败（已重试 {max_retries} 次）: {last_error}")

    def publish_book_sync(
        self,
        book_id: int,
        channel_id: int,
        auto_retry: bool = True,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        发布书籍到指定渠道（同步版本）

        用于 Celery 任务中调用异步方法。

        Args:
            book_id: 书籍 ID
            channel_id: 渠道 ID
            auto_retry: 是否自动重试
            max_retries: 最大重试次数

        Returns:
            dict: 发布结果
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.publish_book(book_id, channel_id, auto_retry, max_retries)
            )
            result["success"] = True
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            loop.close()

    async def _do_publish(
        self,
        book_id: int,
        channel_id: int,
    ) -> Dict[str, Any]:
        """
        执行发布

        Args:
            book_id: 书籍 ID
            channel_id: 渠道 ID

        Returns:
            dict: 发布结果
        """
        from models import Book, Chapter, PublishChannel, PublishRecord, ChapterStatus

        with get_db_context() as db:
            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                raise PublishError(f"书籍不存在: {book_id}")

            channel = db.query(PublishChannel).filter(
                PublishChannel.id == channel_id
            ).first()
            if not channel:
                raise PublishError(f"发布渠道不存在: {channel_id}")

            publisher = self.get_publisher(channel.platform_type)
            if not publisher:
                raise PublishError(f"不支持的平台类型: {channel.platform_type}")

            # 获取或创建发布记录
            record = (
                db.query(PublishRecord)
                .filter(
                    PublishRecord.book_id == book_id,
                    PublishRecord.channel_id == channel_id,
                )
                .first()
            )

            if not record:
                record = PublishRecord(
                    book_id=book_id,
                    channel_id=channel_id,
                    status=PublishStatus.PENDING,
                    total_chapters=book.total_chapters,
                )
                db.add(record)

            record.status = PublishStatus.PREPARING
            db.commit()

            # 准备书籍数据
            book_data = {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "description": book.description,
                "total_chapters": book.total_chapters,
            }

            # 获取封面
            cover_image = None
            if book.cover_image:
                from services.svc_minio_storage import get_storage_service
                storage = get_storage_service()
                cover_image = storage.download_file(
                    settings.MINIO_BUCKET_EPUB,
                    book.cover_image,
                )

            # 创建专辑
            album_result = await publisher.create_album(book_data, cover_image)
            record.external_album_id = album_result.get("album_id")
            record.external_album_url = album_result.get("album_url")
            db.commit()

            # 上传章节
            chapters = (
                db.query(Chapter)
                .filter(Chapter.book_id == book_id)
                .filter(Chapter.status == ChapterStatus.DONE)
                .order_by(Chapter.chapter_index)
                .all()
            )

            record.status = PublishStatus.PUBLISHING
            db.commit()

            published_chapters = []
            failed_chapters = []

            for chapter in chapters:
                try:
                    chapter_data = {
                        "id": chapter.id,
                        "title": chapter.title,
                        "index": chapter.chapter_index,
                        "duration": chapter.audio_duration,
                        "audio_file_path": chapter.audio_file_path,
                    }

                    # 获取音频流
                    from services.svc_minio_storage import get_storage_service
                    storage = get_storage_service()

                    audio_data = storage.download_file(
                        settings.MINIO_BUCKET_AUDIO,
                        chapter.audio_file_path,
                    )

                    # 上传
                    audio_result = await publisher.upload_chapter(
                        album_result["album_id"],
                        chapter_data,
                        audio_data,
                    )

                    published_chapters.append({
                        "chapter_id": chapter.id,
                        "external_id": audio_result.get("audio_id"),
                        "external_url": audio_result.get("audio_url"),
                    })

                    # 更新发布记录中的章节映射
                    if not record.chapters_published:
                        record.chapters_published = {}
                    record.chapters_published[str(chapter.id)] = audio_result.get("audio_id")

                    record.published_chapters = len(published_chapters)
                    db.commit()

                except Exception as e:
                    logger.error(f"章节发布失败: {chapter.id} - {e}")
                    failed_chapters.append({"chapter_id": chapter.id, "error": str(e)})

            # 发布专辑
            try:
                await publisher.publish_album(album_result["album_id"])
                record.status = (
                    PublishStatus.DONE if not failed_chapters
                    else PublishStatus.PARTIAL_DONE
                )
            except Exception as e:
                logger.warning(f"专辑发布失败: {e}")
                record.status = PublishStatus.PARTIAL_DONE

            record.published_at = datetime.utcnow()
            db.commit()

            # 更新渠道统计
            channel.total_published += 1
            if record.status == PublishStatus.DONE:
                channel.success_count += 1
            channel.last_published_at = datetime.utcnow()
            db.commit()

            result = {
                "album_id": album_result.get("album_id"),
                "album_url": album_result.get("album_url"),
                "published_chapters": len(published_chapters),
                "failed_chapters": len(failed_chapters),
                "status": record.status.value,
            }

            logger.info(
                f"书籍发布完成: book_id={book_id}, "
                f"channel={channel.name}, "
                f"chapters={len(published_chapters)}/{len(chapters)}"
            )

            return result

    async def publish_book_to_all_channels(
        self,
        book_id: int,
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """
        发布书籍到所有已配置的渠道

        Args:
            book_id: 书籍 ID
            parallel: 是否并行发布

        Returns:
            dict: 发布结果汇总
        """
        from models import Book, PublishChannel

        with get_db_context() as db:
            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                raise PublishError(f"书籍不存在: {book_id}")

            # 获取所有启用的发布渠道
            channels = (
                db.query(PublishChannel)
                .filter(PublishChannel.is_enabled == True)
                .filter(PublishChannel.auto_publish == True)
                .order_by(PublishChannel.priority.desc())
                .all()
            )

            if not channels:
                logger.warning(f"没有配置发布渠道: book_id={book_id}")
                return {"book_id": book_id, "channels": [], "message": "没有配置发布渠道"}

        results = []

        if parallel:
            # 并行发布
            with ThreadPoolExecutor(max_workers=len(channels)) as executor:
                futures = [
                    executor.submit(
                        self._publish_to_channel_sync,
                        book_id,
                        channel.id,
                    )
                    for channel in channels
                ]

                for future in futures:
                    try:
                        results.append(future.result())
                    except Exception as e:
                        results.append({"error": str(e)})
        else:
            # 串行发布
            for channel in channels:
                try:
                    result = await self.publish_book(book_id, channel.id)
                    results.append({
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                        **result,
                    })
                except Exception as e:
                    results.append({
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                        "error": str(e),
                    })

        return {
            "book_id": book_id,
            "total_channels": len(channels),
            "results": results,
        }

    def _publish_to_channel_sync(
        self,
        book_id: int,
        channel_id: int,
    ) -> Dict[str, Any]:
        """同步发布（用于线程池）"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.publish_book(book_id, channel_id)
            )
            loop.close()
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_publish_status(self, book_id: int) -> Dict[str, Any]:
        """
        获取发布状态

        Args:
            book_id: 书籍 ID

        Returns:
            dict: 发布状态
        """
        from models import PublishRecord

        with get_db_context() as db:
            records = (
                db.query(PublishRecord)
                .filter(PublishRecord.book_id == book_id)
                .all()
            )

            return {
                "book_id": book_id,
                "channels": [
                    {
                        "record_id": r.id,
                        "channel_id": r.channel_id,
                        "status": r.status.value,
                        "progress": self._calculate_progress(r),
                        "published_chapters": r.published_chapters or 0,
                        "total_chapters": r.total_chapters or 0,
                        "published_at": r.published_at.isoformat() if r.published_at else None,
                        "error_message": r.error_message,
                    }
                    for r in records
                ],
            }

    def _calculate_progress(self, record) -> float:
        """
        计算发布进度

        Args:
            record: 发布记录

        Returns:
            float: 进度百分比
        """
        if not record.total_chapters:
            return 0.0

        published = record.published_chapters or 0
        total = record.total_chapters

        return round((published / total) * 100, 2)

    def cancel_publish(self, book_id: int, channel_id: int) -> bool:
        """
        取消发布

        Args:
            book_id: 书籍 ID
            channel_id: 渠道 ID

        Returns:
            bool: 是否取消成功
        """
        from models import PublishRecord

        with get_db_context() as db:
            record = (
                db.query(PublishRecord)
                .filter(
                    PublishRecord.book_id == book_id,
                    PublishRecord.channel_id == channel_id,
                )
                .first()
            )

            if not record:
                return False

            if record.status in [PublishStatus.DONE, PublishStatus.CANCELLED]:
                return False

            record.status = PublishStatus.CANCELLED
            record.error_message = "用户取消"
            db.commit()

            return True
