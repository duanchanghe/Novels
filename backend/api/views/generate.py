"""
手动生成视图
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from core.models import Book, Character, Chapter, CharacterStatus

logger = logging.getLogger("audiobook")


class ManualGenerateView(APIView):
    """手动生成视图"""

    def post(self, request, book_id):
        """触发手动生成"""
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        chapter_ids = request.data.get("chapter_ids", [])
        if not chapter_ids:
            return Response({"detail": "请指定章节ID"}, status=status.HTTP_400_BAD_REQUEST)

        from tasks.task_pipeline import process_chapter
        for ch_id in chapter_ids:
            try:
                chapter = Chapter.objects.get(id=ch_id, book_id=book_id)
                process_chapter.delay(ch_id)
                logger.info(f"已提交章节生成任务: {ch_id}")
            except Chapter.DoesNotExist:
                logger.warning(f"章节不存在: {ch_id}")

        return Response({"message": "生成任务已提交", "chapter_count": len(chapter_ids)})


class GenerateCheckView(APIView):
    """生成前检查"""

    def get(self, request, book_id):
        """检查是否满足生成条件"""
        try:
            Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        characters = Character.objects.filter(book_id=book_id)
        chapters = Chapter.objects.filter(book_id=book_id)

        issues = []
        
        # 检查角色审核状态
        pending_chars = characters.filter(status=CharacterStatus.PENDING).count()
        rejected_chars = characters.filter(status=CharacterStatus.REJECTED).count()
        if pending_chars > 0:
            issues.append(f"{pending_chars} 个角色待审核")
        if rejected_chars > 0:
            issues.append(f"{rejected_chars} 个角色已拒绝")

        # 检查角色音色分配
        unassigned = characters.filter(voice_profile__isnull=True, custom_voice_id__isnull=True).count()
        if unassigned > 0:
            issues.append(f"{unassigned} 个角色未分配音色")

        # 检查章节分析状态
        unanalyzed = chapters.filter(status="PENDING").count()
        if unanalyzed > 0:
            issues.append(f"{unanalyzed} 个章节未分析")

        return Response({
            "can_generate": len(issues) == 0,
            "issues": issues,
            "stats": {
                "total_characters": characters.count(),
                "total_chapters": chapters.count(),
            }
        })


class CharacterSyncView(APIView):
    """角色同步视图"""

    def post(self, request, book_id):
        """同步角色到章节"""
        try:
            Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 从 DeepSeek 分析结果同步角色
        chapters = Chapter.objects.filter(book_id=book_id)
        synced = 0

        for chapter in chapters:
            if chapter.characters:
                for char_data in chapter.characters:
                    char_name = char_data.get("name")
                    if char_name:
                        char, created = Character.objects.get_or_create(
                            book_id=book_id,
                            name=char_name,
                            defaults={"source": "deepseek"}
                        )
                        if char.description is None and char_data.get("description"):
                            char.description = char_data.get("description")
                            char.save()
                        synced += 1

        return Response({"synced": synced})
