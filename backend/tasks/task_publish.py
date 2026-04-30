# ===========================================
# 发布任务
# ===========================================

"""
自动发布 Celery 任务

处理有声书发布到各个平台。
"""

import logging
from typing import Dict, Any

from celery import Task

from tasks.celery_app import celery_app
from core.database import get_db_context


logger = logging.getLogger("audiobook")


class PublishTask(Task):
    """
    发布任务基类
    """
    autoretry_for = (Exception,)
    retry_backoff = True


@celery_app.task(
    bind=True,
    base=PublishTask,
    name="tasks.task_publish.publish_to_channel",
    queue="publish",
)
def publish_to_channel(
    self,
    book_id: int,
    channel_id: int,
) -> Dict[str, Any]:
    """
    发布书籍到指定渠道

    Args:
        book_id: 书籍ID
        channel_id: 渠道ID

    Returns:
        dict: 发布结果
    """
    logger.info(f"开始发布书籍到渠道: book_id={book_id}, channel_id={channel_id}")

    with get_db_context() as db:
        from models import Book, PublishChannel, PublishRecord, BookStatus, PublishStatus
        from datetime import datetime

        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {book_id}")

        channel = db.query(PublishChannel).filter(PublishChannel.id == channel_id).first()
        if not channel:
            raise ValueError(f"发布渠道不存在: {channel_id}")

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

        try:
            # 更新状态
            record.status = PublishStatus.PREPARING
            db.commit()

            # 执行发布
            from services.svc_publisher import PublisherService

            publisher = PublisherService()
            result = publisher.publish_book(book_id, channel_id)

            # 更新记录
            record.status = PublishStatus.DONE
            record.external_album_id = result.get("album_id")
            record.external_album_url = result.get("album_url")
            record.published_at = datetime.utcnow()
            record.result_details = result
            db.commit()

            # 更新渠道统计
            channel.total_published += 1
            channel.success_count += 1
            channel.last_published_at = datetime.utcnow()
            db.commit()

            logger.info(f"书籍发布成功: book_id={book_id}, channel_id={channel_id}")
            return {
                "book_id": book_id,
                "channel_id": channel_id,
                "album_id": result.get("album_id"),
                "success": True,
            }

        except Exception as e:
            logger.error(f"书籍发布失败: book_id={book_id}, channel_id={channel_id} - {e}")

            record.status = PublishStatus.FAILED
            record.error_message = str(e)
            record.retry_count = (record.retry_count or 0) + 1
            db.commit()

            # 更新渠道统计
            channel.failure_count += 1
            db.commit()

            raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=PublishTask,
    name="tasks.task_publish.publish_book_to_all_channels",
    queue="publish",
)
def publish_book_to_all_channels(self, book_id: int) -> Dict[str, Any]:
    """
    发布书籍到所有已配置的渠道

    Args:
        book_id: 书籍ID

    Returns:
        dict: 发布结果汇总
    """
    logger.info(f"开始发布书籍到所有渠道: {book_id}")

    with get_db_context() as db:
        from models import Book, PublishChannel, BookStatus

        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"书籍不存在: {book_id}")

        # 获取所有启用的发布渠道
        channels = (
            db.query(PublishChannel)
            .filter(PublishChannel.is_enabled == True)
            .filter(PublishChannel.auto_publish == True)
            .order_by(PublishChannel.priority.desc())
            .all()
        )

        # 更新书籍状态
        book.status = BookStatus.PUBLISHING
        db.commit()

        results = []
        for channel in channels:
            try:
                result = publish_to_channel.delay(book_id, channel.id)
                results.append({
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "task_id": result.id,
                })
            except Exception as e:
                logger.error(f"提交发布任务失败: channel_id={channel.id} - {e}")
                results.append({
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "error": str(e),
                })

        return {
            "book_id": book_id,
            "total_channels": len(channels),
            "submitted_tasks": results,
        }
