# ===========================================
# 自动发布 API
# ===========================================

"""
自动发布 API 路由

提供发布渠道管理和发布操作接口。
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models import Book
from models.model_book import BookStatus
from models.model_channel import PublishChannel, PlatformType
from models.model_publish import PublishRecord, PublishStatus


router = APIRouter(prefix="/publish", tags=["自动发布"])


@router.get("/channels")
async def list_channels(
    db: Session = Depends(get_db),
):
    """
    获取发布渠道列表

    Args:
        db: 数据库会话

    Returns:
        list: 渠道列表
    """
    channels = db.query(PublishChannel).all()
    return [ch.to_dict() for ch in channels]


@router.post("/channels")
async def create_channel(
    name: str,
    platform_type: str,
    api_config: dict = None,
    auto_publish: bool = False,
    db: Session = Depends(get_db),
):
    """
    创建发布渠道

    Args:
        name: 渠道名称
        platform_type: 平台类型
        api_config: API配置
        auto_publish: 是否自动发布
        db: 数据库会话

    Returns:
        dict: 创建结果
    """
    try:
        pt = PlatformType(platform_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的平台类型")

    channel = PublishChannel(
        name=name,
        platform_type=pt,
        api_config=api_config,
        auto_publish=auto_publish,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    return channel.to_dict()


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: int,
    name: str = None,
    api_config: dict = None,
    is_enabled: bool = None,
    auto_publish: bool = None,
    db: Session = Depends(get_db),
):
    """
    更新发布渠道

    Args:
        channel_id: 渠道ID
        name: 渠道名称
        api_config: API配置
        is_enabled: 是否启用
        auto_publish: 是否自动发布
        db: 数据库会话

    Returns:
        dict: 更新结果
    """
    channel = db.query(PublishChannel).filter(PublishChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")

    if name is not None:
        channel.name = name
    if api_config is not None:
        channel.api_config = api_config
    if is_enabled is not None:
        channel.is_enabled = is_enabled
    if auto_publish is not None:
        channel.auto_publish = auto_publish

    db.commit()
    db.refresh(channel)

    return channel.to_dict()


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: Session = Depends(get_db),
):
    """
    删除发布渠道

    Args:
        channel_id: 渠道ID
        db: 数据库会话

    Returns:
        dict: 删除结果
    """
    channel = db.query(PublishChannel).filter(PublishChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")

    db.delete(channel)
    db.commit()

    return {"message": "删除成功"}


@router.post("/books/{book_id}/publish")
async def publish_book(
    book_id: int,
    channel_ids: List[int] = None,
    db: Session = Depends(get_db),
):
    """
    发布书籍到渠道

    Args:
        book_id: 书籍ID
        channel_ids: 指定渠道ID列表（为空则发布到所有启用渠道）
        db: 数据库会话

    Returns:
        dict: 发布结果
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    if book.status != BookStatus.DONE:
        raise HTTPException(status_code=400, detail="书籍尚未生成完成")

    # 获取要发布的渠道
    if channel_ids:
        channels = (
            db.query(PublishChannel)
            .filter(PublishChannel.id.in_(channel_ids))
            .filter(PublishChannel.is_enabled == True)
            .all()
        )
    else:
        channels = (
            db.query(PublishChannel)
            .filter(PublishChannel.is_enabled == True)
            .all()
        )

    if not channels:
        raise HTTPException(status_code=400, detail="没有可用的发布渠道")

    # 提交发布任务
    from tasks.task_publish import publish_book_to_all_channels
    result = publish_book_to_all_channels.delay(book_id)

    return {
        "book_id": book_id,
        "task_id": result.id,
        "channels": [ch.id for ch in channels],
        "status": "pending",
    }


@router.get("/books/{book_id}/status")
async def get_publish_status(
    book_id: int,
    db: Session = Depends(get_db),
):
    """
    获取书籍发布状态

    Args:
        book_id: 书籍ID
        db: 数据库会话

    Returns:
        dict: 发布状态
    """
    records = (
        db.query(PublishRecord)
        .filter(PublishRecord.book_id == book_id)
        .all()
    )

    return {
        "book_id": book_id,
        "records": [r.to_dict() for r in records],
    }


@router.get("/records/{record_id}")
async def get_publish_record(
    record_id: int,
    db: Session = Depends(get_db),
):
    """
    获取发布记录详情

    Args:
        record_id: 记录ID
        db: 数据库会话

    Returns:
        dict: 记录详情
    """
    record = db.query(PublishRecord).filter(PublishRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return record.to_dict()


@router.get("/records")
async def list_publish_records(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    db: Session = Depends(get_db),
):
    """
    获取发布记录列表

    Args:
        page: 页码
        page_size: 每页数量
        status: 按状态筛选
        db: 数据库会话

    Returns:
        dict: 记录列表
    """
    query = db.query(PublishRecord)

    # 状态筛选
    if status:
        try:
            status_enum = PublishStatus(status)
            query = query.filter(PublishRecord.status == status_enum)
        except ValueError:
            pass

    # 总数
    total = query.count()

    # 分页
    records = (
        query
        .order_by(PublishRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 获取渠道名称
    channel_ids = list(set(r.channel_id for r in records))
    channels = (
        db.query(PublishChannel)
        .filter(PublishChannel.id.in_(channel_ids))
        .all()
    )
    channel_map = {ch.id: ch.name for ch in channels}

    # 获取书籍信息
    book_ids = list(set(r.book_id for r in records))
    books = (
        db.query(Book)
        .filter(Book.id.in_(book_ids))
        .all()
    )
    book_map = {b.id: b.title for b in books}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                **r.to_dict(),
                "channel_name": channel_map.get(r.channel_id, f"渠道 #{r.channel_id}"),
                "book_title": book_map.get(r.book_id, f"书籍 #{r.book_id}"),
            }
            for r in records
        ],
    }
