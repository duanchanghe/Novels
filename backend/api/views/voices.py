# ===========================================
# API Views - 音色管理视图
# ===========================================

"""
音色管理视图
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from core.models import Book, Chapter
from services.svc_minimax_tts import MiniMaxTTSService
from services.svc_voice_mapper import VoiceMapperService
from services.svc_deepseek_analyzer import DeepSeekAnalyzerService

logger = logging.getLogger("audiobook")


class VoiceListView(APIView):
    """音色列表视图"""

    def get(self, request):
        """
        获取可用音色列表
        """
        tts_service = MiniMaxTTSService()
        return Response(tts_service.get_available_voices())


class EmotionListView(APIView):
    """情感列表视图"""

    def get(self, request):
        """
        获取支持的情感列表
        """
        tts_service = MiniMaxTTSService()
        return Response(tts_service.get_emotion_list())


class RoleMappingView(APIView):
    """角色映射视图"""

    def get(self, request):
        """
        获取角色-音色映射表
        """
        mapper = VoiceMapperService()
        return Response({
            "roles": mapper.get_role_mappings(),
            "emotions": mapper.get_emotion_mappings(),
            "categories": mapper.get_role_categories(),
        })


class RateLimitView(APIView):
    """速率限制视图"""

    def get(self, request):
        """
        获取 TTS 速率限制状态
        """
        tts_service = MiniMaxTTSService()
        return Response(tts_service.get_rate_limit_status())


class CacheStatsView(APIView):
    """缓存统计视图"""

    def get(self, request):
        """
        获取分析器缓存统计
        """
        analyzer = DeepSeekAnalyzerService()
        return Response(analyzer.get_cache_stats())

    def post(self, request):
        """
        清空分析器缓存
        """
        analyzer = DeepSeekAnalyzerService()
        analyzer.clear_cache()
        return Response({"message": "缓存已清空"})


class VoiceRecommendView(APIView):
    """音色推荐视图"""

    def get(self, request, pk):
        """
        获取书籍推荐音色配置

        Path Parameters:
            pk: 书籍ID
        """
        try:
            book = Book.objects.get(id=pk, deleted_at__isnull=True)
        except Book.DoesNotExist:
            return Response(
                {"detail": "书籍不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 收集书籍中的角色
        characters = set()
        chapters = Chapter.objects.filter(book_id=pk)
        for chapter in chapters:
            if chapter.characters:
                for char in chapter.characters:
                    characters.add(char.get("name"))

        mapper = VoiceMapperService()
        available_voices = mapper.get_available_voices()

        recommendations = []
        for char in characters:
            voice_config = mapper.get_voice_for_role(char)
            recommendations.append({
                "character": char,
                "recommended_voice": voice_config,
            })

        return Response({
            "book_id": pk,
            "characters": list(characters),
            "recommendations": recommendations,
            "available_voices": available_voices,
        })
