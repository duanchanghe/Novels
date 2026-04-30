# ===========================================
# 音色管理 API
# ===========================================

"""
音色管理 API 路由

提供音色配置查询接口。
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from services.svc_voice_mapper import VoiceMapperService
from services.svc_minimax_tts import MiniMaxTTSService


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
        "emotions": mapper.emotion_map,
    }


@router.get("/recommend/{book_id}")
async def recommend_voices(book_id: int):
    """
    获取书籍推荐音色配置

    Args:
        book_id: 书籍ID

    Returns:
        dict: 推荐配置
    """
    from core.database import get_db_context

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
