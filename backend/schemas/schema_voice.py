# ===========================================
# 音色 Schema
# ===========================================

"""
音色相关的 Pydantic 数据模型
"""

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class VoiceProfileResponse(BaseModel):
    """音色配置响应模型"""
    id: int
    name: str
    description: Optional[str] = None
    role_type: str
    minimax_voice_id: Optional[str] = None
    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0
    is_system_preset: bool = False
    is_active: bool = True
    usage_count: int = 0

    model_config = {"from_attributes": True}


class VoiceListResponse(BaseModel):
    """音色列表响应模型"""
    voices: List[VoiceProfileResponse]
    total: int


class VoiceRecommendationResponse(BaseModel):
    """音色推荐响应模型"""
    character: str
    recommended_voice: Dict[str, Any]
    available_options: List[Dict[str, Any]]
