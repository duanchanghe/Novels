# ===========================================
# 音色映射服务
# ===========================================

"""
音色映射服务

管理角色到音色的映射关系。
"""

from typing import Dict, List, Optional, Any


class VoiceMapperService:
    """
    音色映射服务

    提供角色到音色的映射功能。
    """

    # 默认角色映射
    DEFAULT_ROLE_MAP = {
        "旁白": {"voice_id": "male-qn", "speed": 1.0, "emotion": "neutral"},
        "叙述": {"voice_id": "male-qn", "speed": 1.0, "emotion": "neutral"},
        "描写": {"voice_id": "male-qn", "speed": 1.0, "emotion": "neutral"},
        "男主": {"voice_id": "male-qn", "speed": 1.0, "emotion": "neutral"},
        "男性主角": {"voice_id": "male-qn", "speed": 1.0, "emotion": "neutral"},
        "女主": {"voice_id": "female-shaon", "speed": 1.0, "emotion": "neutral"},
        "女性主角": {"voice_id": "female-shaon", "speed": 1.0, "emotion": "neutral"},
        "老人": {"voice_id": "male-yun", "speed": 0.9, "emotion": "neutral"},
        "老者": {"voice_id": "male-yun", "speed": 0.9, "emotion": "neutral"},
        "儿童": {"voice_id": "female-xiang", "speed": 1.1, "emotion": "happy"},
        "反派": {"voice_id": "male-tian", "speed": 0.95, "emotion": "neutral"},
        "坏人": {"voice_id": "male-tian", "speed": 0.95, "emotion": "neutral"},
        "未识别": {"voice_id": "female-shaon", "speed": 1.0, "emotion": "neutral"},
    }

    # 情感参数映射
    EMOTION_MAP = {
        "平静": {"emotion": "neutral", "pitch": 0, "speed_factor": 1.0},
        "高兴": {"emotion": "happy", "pitch": 0.1, "speed_factor": 1.05},
        "开心": {"emotion": "happy", "pitch": 0.1, "speed_factor": 1.05},
        "快乐": {"emotion": "happy", "pitch": 0.1, "speed_factor": 1.05},
        "悲伤": {"emotion": "sad", "pitch": -0.2, "speed_factor": 0.95},
        "伤心": {"emotion": "sad", "pitch": -0.2, "speed_factor": 0.95},
        "愤怒": {"emotion": "angry", "pitch": 0.3, "speed_factor": 1.1},
        "生气": {"emotion": "angry", "pitch": 0.3, "speed_factor": 1.1},
        "紧张": {"emotion": "fearful", "pitch": 0.1, "speed_factor": 1.1},
        "害怕": {"emotion": "fearful", "pitch": 0.1, "speed_factor": 1.1},
        "惊讶": {"emotion": "surprise", "pitch": 0.3, "speed_factor": 1.15},
        "震惊": {"emotion": "surprise", "pitch": 0.3, "speed_factor": 1.15},
        "温柔": {"emotion": "gentle", "pitch": -0.1, "speed_factor": 0.9},
        "柔和": {"emotion": "gentle", "pitch": -0.1, "speed_factor": 0.9},
        "严肃": {"emotion": "serious", "pitch": -0.1, "speed_factor": 0.9},
    }

    def __init__(self):
        self.role_map = self.DEFAULT_ROLE_MAP.copy()
        self.emotion_map = self.EMOTION_MAP.copy()

    def get_voice_for_role(self, role: str) -> Dict[str, Any]:
        """
        获取角色对应的音色

        Args:
            role: 角色名

        Returns:
            dict: 音色配置
        """
        return self.role_map.get(role, self.role_map["未识别"])

    def get_emotion_params(self, emotion: str) -> Dict[str, Any]:
        """
        获取情感参数

        Args:
            emotion: 情感标签

        Returns:
            dict: 情感参数
        """
        return self.emotion_map.get(emotion, self.emotion_map["平静"])

    def map_analysis_to_voice_params(
        self,
        role: str,
        emotion: str = None,
        intensity: str = "medium",
    ) -> Dict[str, Any]:
        """
        将分析结果映射为语音参数

        Args:
            role: 角色名
            emotion: 情感
            intensity: 情感强度

        Returns:
            dict: 完整的语音参数
        """
        voice_config = self.get_voice_for_role(role)

        if emotion:
            emotion_config = self.get_emotion_params(emotion)
        else:
            emotion_config = self.get_emotion_params("平静")

        # 根据强度调整
        intensity_factor = {
            "low": 0.8,
            "medium": 1.0,
            "high": 1.2,
        }.get(intensity, 1.0)

        return {
            "voice_id": voice_config["voice_id"],
            "speed": voice_config["speed"] * emotion_config["speed_factor"] * intensity_factor,
            "pitch": emotion_config["pitch"],
            "emotion": emotion_config["emotion"],
        }

    def add_custom_role_mapping(
        self,
        role_name: str,
        voice_id: str,
        speed: float = 1.0,
        emotion: str = "neutral",
    ) -> None:
        """
        添加自定义角色映射

        Args:
            role_name: 角色名
            voice_id: 音色 ID
            speed: 语速
            emotion: 情感
        """
        self.role_map[role_name] = {
            "voice_id": voice_id,
            "speed": speed,
            "emotion": emotion,
        }

    def get_role_mappings(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有角色映射

        Returns:
            dict: 角色映射字典
        """
        return self.role_map.copy()

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
