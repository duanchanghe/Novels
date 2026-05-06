"""
Character 角色库视图
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from core.models import Character, CharacterStatus, Book, VoiceProfile

logger = logging.getLogger("audiobook")


class CharacterListView(APIView):
    """角色列表视图"""

    def get(self, request, book_id):
        """获取书籍的所有角色"""
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        characters = Character.objects.filter(book_id=book_id).order_by("sort_order", "name")
        
        data = [{
            "id": c.id,
            "name": c.name,
            "gender": c.gender,
            "status": c.status,
            "voice_profile_id": c.voice_profile_id,
            "dialogue_count": c.dialogue_count,
            "usage_count": c.usage_count,
        } for c in characters]

        return Response({"total": len(data), "items": data})

    def post(self, request, book_id):
        """创建角色"""
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get("name")
        if not name:
            return Response({"detail": "角色名称不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        character = Character.objects.create(
            book_id=book_id,
            name=name,
            gender=request.data.get("gender", "unknown"),
            description=request.data.get("description", ""),
        )

        return Response({"id": character.id, "name": character.name}, status=status.HTTP_201_CREATED)


class CharacterDetailView(APIView):
    """角色详情视图"""

    def get(self, request, book_id, character_id):
        """获取角色详情"""
        try:
            character = Character.objects.get(id=character_id, book_id=book_id)
        except Character.DoesNotExist:
            return Response({"detail": "角色不存在"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "id": character.id,
            "name": character.name,
            "aliases": character.aliases,
            "gender": character.gender,
            "description": character.description,
            "voice_description": character.voice_description,
            "role_type": character.role_type,
            "emotions": character.emotions,
            "voice_profile_id": character.voice_profile_id,
            "custom_voice_id": character.custom_voice_id,
            "status": character.status,
            "dialogue_count": character.dialogue_count,
        })

    def put(self, request, book_id, character_id):
        """更新角色"""
        try:
            character = Character.objects.get(id=character_id, book_id=book_id)
        except Character.DoesNotExist:
            return Response({"detail": "角色不存在"}, status=status.HTTP_404_NOT_FOUND)

        if "name" in request.data:
            character.name = request.data["name"]
        if "gender" in request.data:
            character.gender = request.data["gender"]
        if "status" in request.data:
            character.status = request.data["status"]
        if "voice_profile_id" in request.data:
            character.voice_profile_id = request.data["voice_profile_id"]
        if "custom_voice_id" in request.data:
            character.custom_voice_id = request.data["custom_voice_id"]

        character.save()
        return Response({"message": "更新成功"})


class CharacterBatchAssignVoiceView(APIView):
    """批量分配音色视图"""

    def post(self, request, book_id):
        """批量分配音色"""
        character_ids = request.data.get("character_ids", [])
        voice_profile_id = request.data.get("voice_profile_id")
        custom_voice_id = request.data.get("custom_voice_id")

        updated = Character.objects.filter(id__in=character_ids, book_id=book_id).update(
            voice_profile_id=voice_profile_id,
            custom_voice_id=custom_voice_id,
        )

        return Response({"updated": updated})


class CharacterApproveView(APIView):
    """角色审核视图"""

    def post(self, request, book_id, character_id):
        """审核通过角色"""
        try:
            character = Character.objects.get(id=character_id, book_id=book_id)
        except Character.DoesNotExist:
            return Response({"detail": "角色不存在"}, status=status.HTTP_404_NOT_FOUND)

        character.status = CharacterStatus.APPROVED
        character.save()
        return Response({"message": "审核通过"})


class CharacterApproveAllView(APIView):
    """批量审核视图"""

    def post(self, request, book_id):
        """批量审核通过所有角色"""
        updated = Character.objects.filter(book_id=book_id).update(
            status=CharacterStatus.APPROVED
        )
        return Response({"approved": updated})


class CharacterSummaryView(APIView):
    """角色汇总视图"""

    def get(self, request, book_id):
        """获取角色统计汇总"""
        try:
            Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        qs = Character.objects.filter(book_id=book_id)
        return Response({
            "total": qs.count(),
            "approved": qs.filter(status=CharacterStatus.APPROVED).count(),
            "pending": qs.filter(status=CharacterStatus.PENDING).count(),
            "rejected": qs.filter(status=CharacterStatus.REJECTED).count(),
            "male": qs.filter(gender="male").count(),
            "female": qs.filter(gender="female").count(),
            "unknown": qs.filter(gender="unknown").count(),
            "assigned_voice": qs.exclude(voice_profile_id__isnull=True).exclude(voice_profile_id=0).count(),
            "unassigned_voice": qs.filter(voice_profile_id__isnull=True) | qs.filter(voice_profile_id=0),
        })


class CharacterCanGenerateView(APIView):
    """检查是否可以生成"""

    def get(self, request, book_id):
        """检查角色是否满足生成条件"""
        try:
            Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        characters = Character.objects.filter(book_id=book_id)
        pending = characters.filter(status=CharacterStatus.PENDING).count()
        rejected = characters.filter(status=CharacterStatus.REJECTED).count()
        unassigned = characters.filter(voice_profile__isnull=True, custom_voice_id__isnull=True).count()

        can_generate = pending == 0 and rejected == 0 and unassigned == 0

        return Response({
            "can_generate": can_generate,
            "pending_count": pending,
            "rejected_count": rejected,
            "unassigned_count": unassigned,
        })


class VoiceProfileOptionsView(APIView):
    """音色选项视图"""

    def get(self, request, book_id=None):
        """获取可用的音色列表"""
        if book_id:
            profiles = VoiceProfile.objects.filter(book_id=book_id, is_active=True)
        else:
            profiles = VoiceProfile.objects.filter(is_active=True)

        data = [{
            "id": p.id,
            "name": p.name,
            "role_type": p.role_type,
            "minimax_voice_id": p.minimax_voice_id,
            "speed": p.speed,
            "pitch": p.pitch,
            "volume": p.volume,
        } for p in profiles]

        return Response({"items": data})
