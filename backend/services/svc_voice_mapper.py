# ===========================================
# 音色映射服务
# ===========================================

"""
音色映射服务

管理角色到音色的映射关系。

功能特性：
- 角色-音色映射：支持多种角色类型到音色ID的映射
- 情感参数映射：支持强度细分（low/medium/high）
- 音频参数生成：根据角色和情感生成完整语音参数
"""

from typing import Dict, List, Optional, Any


class VoiceMapperService:
    """
    音色映射服务

    提供角色到音色的映射功能，支持情感强度细分。
    """

    # ===========================================
    # 角色映射表
    # ===========================================
    DEFAULT_ROLE_MAP = {
        # 旁白/叙述
        "旁白": {"voice_id": "male-qn", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        "叙述": {"voice_id": "male-qn", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        "描写": {"voice_id": "male-qn", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        # 男性角色
        "男主": {"voice_id": "male-qn", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        "男性主角": {"voice_id": "male-qn", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        "男": {"voice_id": "male-qn", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        "男性": {"voice_id": "male-qn", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        # 女性角色
        "女主": {"voice_id": "female-shaon", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        "女性主角": {"voice_id": "female-shaon", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        "女": {"voice_id": "female-shaon", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        "女性": {"voice_id": "female-shaon", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        # 年长角色
        "老人": {"voice_id": "male-yun", "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
        "老者": {"voice_id": "male-yun", "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
        "老者女性": {"voice_id": "female-don", "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
        "老妇": {"voice_id": "female-don", "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
        # 儿童角色
        "儿童": {"voice_id": "female-xiang", "speed": 1.1, "pitch": 0.2, "emotion": "happy"},
        "孩童": {"voice_id": "female-xiang", "speed": 1.1, "pitch": 0.2, "emotion": "happy"},
        "少年": {"voice_id": "male-qn", "speed": 1.05, "pitch": 0.1, "emotion": "neutral"},
        "少女": {"voice_id": "female-shaon", "speed": 1.05, "pitch": 0.1, "emotion": "happy"},
        # 反派角色
        "反派": {"voice_id": "male-tian", "speed": 0.95, "pitch": 0.1, "emotion": "serious"},
        "坏人": {"voice_id": "male-tian", "speed": 0.95, "pitch": 0.1, "emotion": "serious"},
        "boss": {"voice_id": "male-tian", "speed": 0.9, "pitch": 0.15, "emotion": "serious"},
        # 特殊角色
        "师父": {"voice_id": "male-yun", "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
        "师傅": {"voice_id": "male-yun", "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
        "师兄": {"voice_id": "male-qn", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
        "师弟": {"voice_id": "male-qn", "speed": 1.05, "pitch": 0.05, "emotion": "neutral"},
        # 默认
        "未识别": {"voice_id": "male-qn", "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    }

    # ===========================================
    # 情感参数映射（支持强度细分）
    # ===========================================
    EMOTION_MAP = {
        # 平静（中性）
        "平静": {"emotion": "neutral", "pitch": 0, "speed_factor": 1.0},
        "平静_low": {"emotion": "neutral", "pitch": 0, "speed_factor": 0.95},
        "平静_medium": {"emotion": "neutral", "pitch": 0, "speed_factor": 1.0},
        "平静_high": {"emotion": "neutral", "pitch": 0, "speed_factor": 1.05},
        # 高兴
        "高兴": {"emotion": "happy", "pitch": 0.15, "speed_factor": 1.05},
        "高兴_low": {"emotion": "happy", "pitch": 0.1, "speed_factor": 1.05},
        "高兴_medium": {"emotion": "happy", "pitch": 0.2, "speed_factor": 1.1},
        "高兴_high": {"emotion": "happy", "pitch": 0.3, "speed_factor": 1.15},
        "开心": {"emotion": "happy", "pitch": 0.15, "speed_factor": 1.05},
        "开心_low": {"emotion": "happy", "pitch": 0.1, "speed_factor": 1.05},
        "开心_medium": {"emotion": "happy", "pitch": 0.2, "speed_factor": 1.1},
        "开心_high": {"emotion": "happy", "pitch": 0.3, "speed_factor": 1.15},
        "快乐": {"emotion": "happy", "pitch": 0.15, "speed_factor": 1.05},
        "喜悦": {"emotion": "happy", "pitch": 0.15, "speed_factor": 1.05},
        # 悲伤
        "悲伤": {"emotion": "sad", "pitch": -0.25, "speed_factor": 0.9},
        "悲伤_low": {"emotion": "sad", "pitch": -0.2, "speed_factor": 0.95},
        "悲伤_medium": {"emotion": "sad", "pitch": -0.25, "speed_factor": 0.9},
        "悲伤_high": {"emotion": "sad", "pitch": -0.3, "speed_factor": 0.85},
        "伤心": {"emotion": "sad", "pitch": -0.25, "speed_factor": 0.9},
        "难过": {"emotion": "sad", "pitch": -0.2, "speed_factor": 0.95},
        "痛苦": {"emotion": "sad", "pitch": -0.3, "speed_factor": 0.85},
        # 愤怒
        "愤怒": {"emotion": "angry", "pitch": 0.35, "speed_factor": 1.15},
        "愤怒_low": {"emotion": "angry", "pitch": 0.3, "speed_factor": 1.1},
        "愤怒_medium": {"emotion": "angry", "pitch": 0.4, "speed_factor": 1.15},
        "愤怒_high": {"emotion": "angry", "pitch": 0.5, "speed_factor": 1.2},
        "生气": {"emotion": "angry", "pitch": 0.35, "speed_factor": 1.15},
        "恼怒": {"emotion": "angry", "pitch": 0.3, "speed_factor": 1.1},
        "暴怒": {"emotion": "angry", "pitch": 0.5, "speed_factor": 1.2},
        # 紧张/害怕
        "紧张": {"emotion": "fearful", "pitch": 0.15, "speed_factor": 1.15},
        "紧张_low": {"emotion": "fearful", "pitch": 0.1, "speed_factor": 1.1},
        "紧张_medium": {"emotion": "fearful", "pitch": 0.15, "speed_factor": 1.15},
        "紧张_high": {"emotion": "fearful", "pitch": 0.2, "speed_factor": 1.2},
        "害怕": {"emotion": "fearful", "pitch": 0.15, "speed_factor": 1.15},
        "恐惧": {"emotion": "fearful", "pitch": 0.2, "speed_factor": 1.2},
        "惊恐": {"emotion": "fearful", "pitch": 0.25, "speed_factor": 1.25},
        # 惊讶
        "惊讶": {"emotion": "surprise", "pitch": 0.35, "speed_factor": 1.15},
        "震惊": {"emotion": "surprise", "pitch": 0.4, "speed_factor": 1.2},
        "诧异": {"emotion": "surprise", "pitch": 0.3, "speed_factor": 1.15},
        "惊愕": {"emotion": "surprise", "pitch": 0.4, "speed_factor": 1.2},
        # 温柔
        "温柔": {"emotion": "gentle", "pitch": -0.1, "speed_factor": 0.9},
        "柔和": {"emotion": "gentle", "pitch": -0.1, "speed_factor": 0.9},
        "轻柔": {"emotion": "gentle", "pitch": -0.15, "speed_factor": 0.85},
        "温情": {"emotion": "gentle", "pitch": -0.1, "speed_factor": 0.9},
        # 严肃
        "严肃": {"emotion": "serious", "pitch": -0.1, "speed_factor": 0.9},
        "正经": {"emotion": "serious", "pitch": -0.1, "speed_factor": 0.9},
        "郑重": {"emotion": "serious", "pitch": -0.15, "speed_factor": 0.85},
        # 默认
        "neutral": {"emotion": "neutral", "pitch": 0, "speed_factor": 1.0},
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
        获取情感参数（支持强度细分）

        Args:
            emotion: 情感标签（如"悲伤_high"、"高兴_medium"）

        Returns:
            dict: 情感参数
        """
        # 精确匹配
        if emotion in self.emotion_map:
            return self.emotion_map[emotion]

        # 尝试基础情感匹配
        base_emotion = emotion.split("_")[0] if "_" in emotion else emotion
        for key, config in self.emotion_map.items():
            if key.startswith(base_emotion):
                return config

        # 默认返回平静
        return self.emotion_map["平静"]

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

        # 构建完整情感标签
        if emotion:
            emotion_key = f"{emotion}_{intensity}" if intensity != "medium" else emotion
            emotion_config = self.get_emotion_params(emotion_key)
        else:
            emotion_config = self.get_emotion_params("平静")

        # 强度因子
        intensity_factor = {
            "low": 0.8,
            "medium": 1.0,
            "high": 1.2,
        }.get(intensity, 1.0)

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
