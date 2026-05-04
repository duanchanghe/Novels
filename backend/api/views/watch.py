# ===========================================
# API Views - 文件监听视图
# ===========================================

"""
文件监听管理视图
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from core.models import Book, SourceType

logger = logging.getLogger("audiobook")


class WatchStatusView(APIView):
    """监听状态视图"""

    def get(self, request):
        """
        获取监听状态
        """
        from services.svc_file_watcher import get_watcher_service

        watcher = get_watcher_service()
        status_info = watcher.get_status()

        # 获取最近的文件
        recent_books = Book.objects.filter(
            source_type=SourceType.WATCH
        ).order_by('-created_at')[:10]

        status_info["recent_files"] = [
            {
                "id": book.id,
                "title": book.title,
                "status": book.status,
                "created_at": book.created_at.isoformat() if book.created_at else None,
            }
            for book in recent_books
        ]

        return Response(status_info)


class WatchRestartView(APIView):
    """监听重启视图"""

    def post(self, request):
        """
        重启监听服务
        """
        from services.svc_file_watcher import get_watcher_service

        watcher = get_watcher_service()
        if watcher.is_running():
            watcher.stop()
        success = watcher.start()
        return Response({
            "success": success,
            "status": watcher.get_status(),
        })


class WatchHistoryView(APIView):
    """监听历史视图"""

    def get(self, request):
        """
        获取监听历史

        Query Parameters:
            page: 页码
            page_size: 每页数量
            status: 状态过滤
        """
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        status_filter = request.GET.get('status')

        queryset = Book.objects.filter(source_type=SourceType.WATCH)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        total = queryset.count()
        books = queryset.order_by('-created_at')[page_size*(page-1):page_size*page]

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": book.id,
                    "title": book.title,
                    "file_name": book.file_name,
                    "status": book.status,
                    "total_chapters": book.total_chapters,
                    "processed_chapters": book.processed_chapters,
                    "created_at": book.created_at.isoformat() if book.created_at else None,
                    "error_message": book.error_message,
                }
                for book in books
            ],
        })
