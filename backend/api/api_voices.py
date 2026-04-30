# ===========================================
# 音色管理 API
# ===========================================

"""
音色管理 API 路由

提供音色配置查询接口。
"""

from fastapi import APIRouter, Depends, HTTPException

from core.database import get_db_context
from services.svc_voice_mapper import VoiceMapperService
from services.svc_minimax_tts import MiniMaxTTSService
from services.svc_deepseek_analyzer import DeepSeekAnalyzerService


router = APIRouter(prefix="/voices", tags=["音色管理"])


@router.get("")
async def list_voices():
    """
    获取可用音色列表

    Returns:
        list: 音色列表
    """
    tts_service = MiniMaxTTSService()
    return tts_service.get_available_voices()


@router.get("/emotions")
async def list_emotions():
    """
    获取支持的情感列表

    Returns:
        list: 情感列表（含强度级别）
    """
    tts_service = MiniMaxTTSService()
    return tts_service.get_emotion_list()


@router.get("/roles")
async def get_role_mappings():
    """
    获取角色-音色映射表

    Returns:
        dict: 映射表
    """
    mapper = VoiceMapperService()
    return {
        "roles": mapper.get_role_mappings(),
        "emotions": mapper.get_emotion_mappings(),
        "categories": mapper.get_role_categories(),
    }


@router.get("/roles/categories")
async def get_role_categories():
    """
    获取角色分类列表

    Returns:
        list: 角色分类
    """
    mapper = VoiceMapperService()
    return mapper.get_role_categories()


@router.get("/recommend/{book_id}")
async def recommend_voices(book_id: int):
    """
    获取书籍推荐音色配置

    Args:
        book_id: 书籍ID

    Returns:
        dict: 推荐配置
    """
    with get_db_context() as db:
        from models import Book, Chapter

        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")

        # 获取识别到的角色
        characters = set()
        chapters = db.query(Chapter).filter(Chapter.book_id == book_id).all()

        for chapter in chapters:
            if chapter.characters:
                for char in chapter.characters:
                    characters.add(char.get("name"))

        # 生成推荐配置
        mapper = VoiceMapperService()
        available_voices = mapper.get_available_voices()

        recommendations = []
        for char in characters:
            voice_config = mapper.get_voice_for_role(char)
            recommendations.append({
                "character": char,
                "recommended_voice": voice_config,
            })

        return {
            "book_id": book_id,
            "characters": list(characters),
            "recommendations": recommendations,
            "available_voices": available_voices,
        }


@router.get("/status/rate-limit")
async def get_rate_limit_status():
    """
    获取 TTS 速率限制状态

    Returns:
        dict: 限流器状态
    """
    tts_service = MiniMaxTTSService()
    return tts_service.get_rate_limit_status()


@router.get("/analyzer/cache")
async def get_analyzer_cache_stats():
    """
    获取分析器缓存统计

    Returns:
        dict: 缓存统计信息
    """
    analyzer = DeepSeekAnalyzerService()
    return analyzer.get_cache_stats()


@router.post("/analyzer/cache/clear")
async def clear_analyzer_cache():
    """
    清空分析器缓存

    Returns:
        dict: 操作结果
    """
    analyzer = DeepSeekAnalyzerService()
    analyzer.clear_cache()
    return {"message": "缓存已清空"}
