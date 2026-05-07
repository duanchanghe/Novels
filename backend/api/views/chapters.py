# ===========================================
# API Views - 章节相关视图
# ===========================================

"""
章节管理视图
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from core.models import Chapter, AudioSegment, ChapterStatus
from tasks.task_pipeline import process_chapter

logger = logging.getLogger("audiobook")


class ChapterDetailView(APIView):
    """章节详情视图"""

    def get(self, request, pk):
        """
        获取章节详情

        Path Parameters:
            pk: 章节ID
        """
        try:
            chapter = Chapter.objects.get(id=pk)
        except Chapter.DoesNotExist:
            return Response(
                {"detail": "章节不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        from api.serializers import ChapterDetailSerializer
        serializer = ChapterDetailSerializer(chapter)
        return Response(serializer.data)


class ChapterConfirmView(APIView):
    """章节确认视图"""

    def post(self, request, pk):
        """
        确认开始处理（手动模式）

        Path Parameters:
            pk: 章节ID
        """
        try:
            chapter = Chapter.objects.get(id=pk)
        except Chapter.DoesNotExist:
            return Response(
                {"detail": "章节不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        if chapter.status != ChapterStatus.AWAITING_CONFIRM:
            return Response(
                {"detail": f"章节状态为 {chapter.status}，无需确认"},
                status=status.HTTP_400_BAD_REQUEST
            )

        chapter.status = ChapterStatus.PENDING
        chapter.save()
        process_chapter.delay(chapter.id)

        return Response({
            "chapter_id": chapter.id,
            "status": "processing",
            "message": f"第 {chapter.chapter_index} 章已开始处理",
        })


class ChapterRetryView(APIView):
    """章节重试视图"""

    def post(self, request, pk):
        """
        重试单个失败章节

        Path Parameters:
            pk: 章节ID
        """
        try:
            chapter = Chapter.objects.get(id=pk)
        except Chapter.DoesNotExist:
            return Response(
                {"detail": "章节不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        if chapter.status != ChapterStatus.FAILED:
            return Response(
                {"detail": "章节不是 FAILED 状态"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 删除原有片段
        AudioSegment.objects.filter(chapter_id=chapter.id).delete()

        # 重置状态
        chapter.status = ChapterStatus.PENDING
        chapter.error_message = None
        chapter.failed_segments = 0
        chapter.total_segments = 0
        chapter.completed_segments = 0
        chapter.save()

        # 触发处理
        process_chapter.delay(chapter.id)

        return Response({
            "chapter_id": chapter.id,
            "title": chapter.title,
            "status": "retrying",
        })


class ChapterSegmentsView(APIView):
    """章节片段视图"""

    def get(self, request, pk):
        """
        获取章节片段列表

        Path Parameters:
            pk: 章节ID
        """
        try:
            chapter = Chapter.objects.get(id=pk)
        except Chapter.DoesNotExist:
            return Response(
                {"detail": "章节不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        segments = AudioSegment.objects.filter(
            chapter_id=chapter.id
        ).order_by('segment_index')

        segment_data = []
        for seg in segments:
            segment_data.append({
                "id": seg.id,
                "chapter_id": seg.chapter_id,
                "segment_index": seg.segment_index,
                "text_content": seg.text_content,
                "speaker": seg.speaker,
                "emotion": seg.emotion,
                "status": seg.status,
                "status_display": seg.get_status_display(),
                "audio_url": seg.audio_url,
                "audio_duration_ms": seg.audio_duration_ms,
                "created_at": seg.created_at.isoformat() if seg.created_at else None,
            })

        return Response({
            "chapter_id": chapter.id,
            "segments": segment_data,
            "total_segments": chapter.total_segments,
            "completed_segments": chapter.completed_segments,
        })
