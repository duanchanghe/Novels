# ===========================================
# API Views - 发布管理视图
# ===========================================

"""
发布管理视图
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from core.models import (
    Book, PublishChannel, PublishRecord,
    BookStatus, PlatformType, PublishStatus
)
from tasks.task_publish import publish_book_to_all_channels

logger = logging.getLogger("audiobook")


class PublishChannelListView(APIView):
    """发布渠道列表视图"""

    def get(self, request):
        """
        获取发布渠道列表
        """
        channels = PublishChannel.objects.all()
        return Response([ch.to_dict() for ch in channels])


class PublishChannelCreateView(APIView):
    """创建发布渠道视图"""

    def post(self, request):
        """
        创建发布渠道

        Request Body:
            name: 渠道名称
            platform_type: 平台类型
            api_config: API配置
            auto_publish: 是否自动发布
        """
        name = request.data.get('name')
        platform_type = request.data.get('platform_type')
        api_config = request.data.get('api_config', {})
        auto_publish = request.data.get('auto_publish', False)

        try:
            pt = PlatformType(platform_type)
        except ValueError:
            return Response(
                {"detail": "无效的平台类型"},
                status=status.HTTP_400_BAD_REQUEST
            )

        channel = PublishChannel(
            name=name,
            platform_type=pt,
            api_config=api_config,
            auto_publish=auto_publish,
        )
        channel.save()
        return Response(channel.to_dict())


class PublishChannelDetailView(APIView):
    """发布渠道详情视图"""

    def get(self, request, pk):
        """
        获取发布渠道详情
        """
        try:
            channel = PublishChannel.objects.get(id=pk)
        except PublishChannel.DoesNotExist:
            return Response(
                {"detail": "渠道不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(channel.to_dict())

    def put(self, request, pk):
        """
        更新发布渠道
        """
        try:
            channel = PublishChannel.objects.get(id=pk)
        except PublishChannel.DoesNotExist:
            return Response(
                {"detail": "渠道不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        if 'name' in request.data:
            channel.name = request.data['name']
        if 'api_config' in request.data:
            channel.api_config = request.data['api_config']
        if 'is_enabled' in request.data:
            channel.is_enabled = request.data['is_enabled']
        if 'auto_publish' in request.data:
            channel.auto_publish = request.data['auto_publish']

        channel.save()
        return Response(channel.to_dict())

    def delete(self, request, pk):
        """
        删除发布渠道
        """
        try:
            channel = PublishChannel.objects.get(id=pk)
        except PublishChannel.DoesNotExist:
            return Response(
                {"detail": "渠道不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        channel.delete()
        return Response({"message": "删除成功"})


class PublishBookView(APIView):
    """发布书籍视图"""

    def post(self, request, pk):
        """
        发布书籍

        Path Parameters:
            pk: 书籍ID

        Request Body:
            channel_ids: 渠道ID列表（可选）
        """
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        if book.status != BookStatus.DONE:
            return Response(
                {"detail": "书籍尚未生成完成"},
                status=status.HTTP_400_BAD_REQUEST
            )

        channel_ids = request.data.get('channel_ids')
        if channel_ids:
            channels = PublishChannel.objects.filter(
                id__in=channel_ids, is_enabled=True
            )
        else:
            channels = PublishChannel.objects.filter(is_enabled=True)

        if not channels.exists():
            return Response(
                {"detail": "没有可用的发布渠道"},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = publish_book_to_all_channels.delay(pk)

        return Response({
            "book_id": pk,
            "task_id": result.id,
            "channels": [ch.id for ch in channels],
            "status": "pending",
        })


class PublishStatusView(APIView):
    """发布状态视图"""

    def get(self, request, pk):
        """
        获取发布状态

        Path Parameters:
            pk: 书籍ID
        """
        records = PublishRecord.objects.filter(book_id=pk)
        return Response({
            "book_id": pk,
            "records": [r.to_dict() for r in records],
        })


class PublishRecordView(APIView):
    """发布记录视图"""

    def get(self, request, pk):
        """
        获取发布记录详情

        Path Parameters:
            pk: 记录ID
        """
        try:
            record = PublishRecord.objects.get(id=pk)
        except PublishRecord.DoesNotExist:
            return Response(
                {"detail": "记录不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(record.to_dict())


class PublishRecordListView(APIView):
    """发布记录列表视图"""

    def get(self, request):
        """
        获取发布记录列表

        Query Parameters:
            page: 页码
            page_size: 每页数量
            status: 状态过滤
        """
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        status_filter = request.GET.get('status')

        queryset = PublishRecord.objects.all()

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        total = queryset.count()
        records = queryset.order_by('-created_at')[page_size*(page-1):page_size*page]

        # 获取渠道和书籍映射
        channel_ids = list(set(r.channel_id for r in records))
        channel_map = {}
        if channel_ids:
            channels = PublishChannel.objects.filter(id__in=channel_ids)
            channel_map = {ch.id: ch.name for ch in channels}

        book_ids = list(set(r.book_id for r in records))
        book_map = {}
        if book_ids:
            books = Book.objects.filter(id__in=book_ids)
            book_map = {b.id: b.title for b in books}

        items = []
        for r in records:
            item = r.to_dict()
            item["channel_name"] = channel_map.get(r.channel_id, f"渠道 #{r.channel_id}")
            item["book_title"] = book_map.get(r.book_id, f"书籍 #{r.book_id}")
            items.append(item)

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        })
