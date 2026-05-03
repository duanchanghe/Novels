# ===========================================
# 音色映射服务（使用共享常量）
# ===========================================

"""
音色映射服务

管理角色到音色的映射关系。
所有映射表统一来源于 core.constants 模块（唯一数据源）。

功能特性：
- 角色-音色映射：支持多种角色类型到音色ID的映射
- 情感参数映射：支持强度细分（low/medium/high）
- 音频参数生成：根据角色和情感生成完整语音参数
"""

from typing import Dict, List, Any
from copy import deepcopy

from core.constants import (
    ROLE_VOICE_MAP,
    EMOTION_PARAM_MAP,
    INTENSITY_FACTOR_MAP,
    DEFAULT_VOICE_CONFIG,
    DEFAULT_EMOTION_CONFIG,
)


class VoiceMapperService:
    """
    音色映射服务

    提供角色到音色的映射功能，支持情感强度细分。
    映射表源自 core.constants 共享常量，确保全局一致。
    """

    def __init__(self):
        # 使用深拷贝，允许实例级别自定义而不影响全局常量
        self.role_map = deepcopy(ROLE_VOICE_MAP)
        self.emotion_map = deepcopy(EMOTION_PARAM_MAP)

    def get_voice_for_role(self, role: str) -> Dict[str, Any]:
        """
        获取角色对应的音色配置

        Args:
            role: 角色名（中文或英文 key）

        Returns:
            dict: 包含 voice_id/speed/pitch/emotion 的配置
        """
        return self.role_map.get(role, DEFAULT_VOICE_CONFIG)

    def get_emotion_params(self, emotion: str) -> Dict[str, Any]:
        """
        获取情感参数（支持强度细分）

        Args:
            emotion: 情感标签（如 "悲伤_high"、"高兴_medium" 或纯 "悲伤"）

        Returns:
            dict: 包含 emotion/pitch/speed_factor 的配置
        """
        # 精确匹配
        if emotion in self.emotion_map:
            return self.emotion_map[emotion]

        # 回退：基于基础情感名称模糊匹配
        base_emotion = emotion.split("_")[0] if "_" in emotion else emotion
        for key, config in self.emotion_map.items():
            if key.startswith(base_emotion):
                return config

        return DEFAULT_EMOTION_CONFIG

    def map_analysis_to_voice_params(
        self,
        role: str,
        emotion: str = None,
        intensity: str = "medium",
    ) -> Dict[str, Any]:
        """
        将 DeepSeek 分析结果映射为 MiniMax TTS 语音参数

        Args:
            role: 角色名
            emotion: 情感标签
            intensity: 情感强度（"low" / "medium" / "high"）

        Returns:
            dict: {voice_id, speed, pitch, emotion}
        """
        voice_config = self.get_voice_for_role(role)

        # 构建完整情感标签
        if emotion:
            emotion_key = f"{emotion}_{intensity}" if intensity != "medium" else emotion
            emotion_config = self.get_emotion_params(emotion_key)
        else:
            emotion_config = DEFAULT_EMOTION_CONFIG

        intensity_factor = INTENSITY_FACTOR_MAP.get(intensity, 1.0)

        return {
            "voice_id": voice_config["voice_id"],
            "speed": voice_config["speed"] * emotion_config["speed_factor"] * intensity_factor,
            "pitch": voice_config["pitch"] + emotion_config["pitch"],
            "emotion": emotion_config["emotion"],
        }

    def add_custom_role_mapping(
        self,
        role_name: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        emotion: str = "neutral",
    ) -> None:
        """
        添加自定义角色映射

        Args:
            role_name: 角色名
            voice_id: 音色 ID
            speed: 语速
            pitch: 音调
            emotion: 默认情感
        """
        self.role_map[role_name] = {
            "voice_id": voice_id,
            "speed": speed,
            "pitch": pitch,
            "emotion": emotion,
        }

    def get_role_mappings(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有角色映射

        Returns:
            dict: 角色映射字典
        """
        return self.role_map.copy()

    def get_emotion_mappings(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有情感映射

        Returns:
            dict: 情感映射字典
        """
        return self.emotion_map.copy()

    def get_available_voices(self) -> List[Dict[str, str]]:
        """
        获取可用音色列表

        Returns:
            list: 音色列表
        """
        return [
            {"id": "male-qn", "name": "青年男声", "gender": "male", "description": "标准青年男性音色"},
            {"id": "male-yun", "name": "成熟男声", "gender": "male", "description": "成熟稳重的男性音色"},
            {"id": "male-tian", "name": "低沉男声", "gender": "male", "description": "低沉有力的男性音色"},
            {"id": "female-shaon", "name": "青年女声", "gender": "female", "description": "标准青年女性音色"},
            {"id": "female-don", "name": "成熟女声", "gender": "female", "description": "成熟女性音色"},
            {"id": "female-xiang", "name": "甜美女声", "gender": "female", "description": "甜美可爱的女性音色"},
        ]

    def get_role_categories(self) -> List[Dict[str, Any]]:
        """
        获取角色分类列表

        Returns:
            list: 角色分类
        """
        return [
            {
                "category": "旁白",
                "roles": ["旁白", "叙述", "描写"],
                "default_voice": "male-qn",
            },
            {
                "category": "男性角色",
                "roles": ["男主", "男性主角", "男", "男性", "师兄", "师弟"],
                "default_voice": "male-qn",
            },
            {
                "category": "女性角色",
                "roles": ["女主", "女性主角", "女", "女性", "少女"],
                "default_voice": "female-shaon",
            },
            {
                "category": "年长角色",
                "roles": ["老人", "老者", "师父", "师傅"],
                "default_voice": "male-yun",
            },
            {
                "category": "反派角色",
                "roles": ["反派", "坏人", "boss"],
                "default_voice": "male-tian",
            },
            {
                "category": "儿童/少年",
                "roles": ["儿童", "孩童", "少年"],
                "default_voice": "female-xiang",
            },
        ]
