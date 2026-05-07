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
    VoiceID,
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

    def get_voice_for_speaker(self, speaker: str) -> Dict[str, Any]:
        """
        根据说话人名称智能获取音色配置

        支持多种匹配策略：
        1. 精确匹配 ROLE_VOICE_MAP（如"旁白"、"男主"、"仙尊"）
        2. 通过常见称呼推断（如"公子"→男声、"小姐"→女声）
        3. 通过姓氏+称谓推断
        4. 默认映射到通用男声

        Args:
            speaker: 说话人名称（如"张三"、"旁白"、"林公子"）

        Returns:
            dict: 包含 voice_id/speed/pitch/emotion 的配置
        """
        if not speaker:
            return DEFAULT_VOICE_CONFIG

        # 策略1：精确匹配
        if speaker in self.role_map:
            return self.role_map[speaker]

        # 策略2：别名映射（检查角色映射表中的值）
        for canonical_name, config in self.role_map.items():
            if speaker.startswith(canonical_name) or canonical_name.startswith(speaker):
                return config

        # 策略3：通过关键词推断角色类型
        speaker_lower = speaker.lower()

        # 女性关键词
        female_keywords = [
            "女", "姐", "妹", "娘", "妈", "母", "太", "婆", "姑", "婶",
            "小姐", "夫人", "太太", "奶奶", "公主", "王妃", "皇后",
            "仙女", "圣女", "仙子", "妖女", "魔女", "女帝", "帝女",
            "女儿", "孙女", "女友", "girl", "woman", "female",
        ]
        # 男性关键词
        male_keywords = [
            "男", "哥", "弟", "爷", "爹", "父", "叔", "伯", "舅", "姑父",
            "公子", "少爷", "老爷", "先生", "陛下", "皇上",
            "仙尊", "魔尊", "帝君", "宗主", "掌门", "长老", "前辈",
            "师父", "师傅", "师尊", "师兄", "师弟", "徒弟",
            "儿子", "孙子", "男友", "boy", "man", "male",
        ]
        # 年长关键词
        elder_keywords = ["老", "祖", "爷", "奶", "婆", "翁", "叟", "long"]
        # 年幼关键词
        child_keywords = ["小", "童", "儿", "孩", "baby", "child", "kid"]

        # 先判断性别倾向
        is_female = any(kw in speaker for kw in female_keywords)
        is_male = any(kw in speaker for kw in male_keywords)
        is_elder = any(kw in speaker for kw in elder_keywords)
        is_child = any(kw in speaker for kw in child_keywords)

        # 如果同时匹配男性和女性关键词（如"小公主"→女性优先）
        if is_female and is_male:
            is_male = False

        # 策略4：通过角色类型选择音色
        if is_female:
            if is_child:
                return self.role_map.get("孩童", self.role_map.get("少女", DEFAULT_VOICE_CONFIG))
            elif is_elder:
                return self.role_map.get("老妇", self.role_map.get("female-elderly", DEFAULT_VOICE_CONFIG))
            else:
                return self.role_map.get("女主", self.role_map.get("female", DEFAULT_VOICE_CONFIG))
        elif is_male:
            if is_child:
                return self.role_map.get("少年", self.role_map.get("male-young", DEFAULT_VOICE_CONFIG))
            elif is_elder:
                return self.role_map.get("老人", self.role_map.get("male-elderly", DEFAULT_VOICE_CONFIG))
            else:
                return self.role_map.get("男主", self.role_map.get("male", DEFAULT_VOICE_CONFIG))

        # 策略5：通过常见姓氏推断（姓氏后加"某"可能是角色名）
        common_surnames = {
            "张", "李", "王", "赵", "刘", "陈", "杨", "周", "吴", "郑",
            "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗", "梁",
            "宋", "谢", "韩", "唐", "冯", "于", "董", "萧", "程", "曹",
            "袁", "邓", "许", "傅", "沈", "曾", "彭", "吕", "苏", "卢",
            "蒋", "蔡", "贾", "丁", "魏", "薛", "叶", "阎", "余", "潘",
            "杜", "戴", "夏", "钟", "汪", "田", "任", "姜", "范", "方",
            "石", "姚", "谭", "廖", "邹", "熊", "金", "陆", "郝", "孔",
            "白", "崔", "康", "毛", "邱", "秦", "江", "史", "顾", "侯",
            "邵", "孟", "龙", "万", "段", "雷", "钱", "汤", "尹", "黎",
            "易", "常", "武", "乔", "贺", "赖", "龚", "文",
        }

        if len(speaker) >= 2 and speaker[0] in common_surnames:
            # 姓氏开头 → 很可能是具体角色名，用通用男声（小说男主为主）
            return self.role_map.get("男主", DEFAULT_VOICE_CONFIG)

        # 策略6：英文角色名检查
        if speaker_lower in ("narrator", "narration", "description"):
            return self.role_map.get("narrator", DEFAULT_VOICE_CONFIG)

        # 策略7：长度判断——2字及以上无名角色默认男主
        if len(speaker) >= 2:
            return self.role_map.get("男主", DEFAULT_VOICE_CONFIG)

        return DEFAULT_VOICE_CONFIG

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
            # ── 男性音色 ──
            {"id": VoiceID.MALE_QN_QINGSE, "name": "青涩青年", "gender": "male", "description": "清澈青年音色，适合旁白和男主角"},
            {"id": VoiceID.MALE_QN_JINGYING, "name": "精英青年", "gender": "male", "description": "精英青年音色，适合商务人士"},
            {"id": VoiceID.MALE_QN_BADAO, "name": "霸道青年", "gender": "male", "description": "霸道青年音色，适合反派或强势角色"},
            {"id": VoiceID.MALE_QN_DAXUESHENG, "name": "青年大学生", "gender": "male", "description": "大学生音色，适合学生角色"},

            # ── 女性音色 ──
            {"id": VoiceID.FEMALE_SHAON, "name": "少女音色", "gender": "female", "description": "少女音色，适合女主角"},
            {"id": VoiceID.FEMALE_YUJIE, "name": "御姐音色", "gender": "female", "description": "御姐音色，适合成熟女性"},
            {"id": VoiceID.FEMALE_CHENGSHU, "name": "成熟女性", "gender": "female", "description": "成熟女性音色，适合年长女性角色"},
            {"id": VoiceID.FEMALE_TIANMEI, "name": "甜美女声", "gender": "female", "description": "甜美女性音色，适合仙女、温柔女主"},

            # ── 儿童音色 ──
            {"id": VoiceID.CLEVER_BOY, "name": "聪明男童", "gender": "male", "description": "聪明男童音色，适合儿童角色"},
            {"id": VoiceID.CUTE_BOY, "name": "可爱男童", "gender": "male", "description": "可爱男童音色"},
            {"id": VoiceID.LOVELY_GIRL, "name": "萌萌女童", "gender": "female", "description": "萌萌女童音色，适合女童角色"},

            # ── 特色音色 ──
            {"id": VoiceID.RELIABLE_EXECUTIVE, "name": "沉稳高管", "gender": "male", "description": "沉稳可靠的中年男性高管"},
            {"id": VoiceID.MALE_ANCHOR, "name": "播报男声", "gender": "male", "description": "富有磁性的播报员男声"},
            {"id": VoiceID.GENTLEMAN, "name": "温润男声", "gender": "male", "description": "温润磁性的青年男声"},
            {"id": VoiceID.HUMOROUS_ELDER, "name": "搞笑大爷", "gender": "male", "description": "幽默老年男性，适合老人角色"},
            {"id": VoiceID.KIND_ELDER, "name": "花甲奶奶", "gender": "female", "description": "慈祥和蔼的老年女性奶奶"},
            {"id": VoiceID.WARM_BESTIE, "name": "温暖闺蜜", "gender": "female", "description": "温暖清脆的女性闺蜜声音"},
            {"id": VoiceID.MATERNAL_GENTLE, "name": "温柔大婶", "gender": "female", "description": "温和善良的中年大婶"},
            {"id": VoiceID.RADIO_HOST, "name": "电台男主播", "gender": "male", "description": "富有诗意的电台主播"},
            {"id": VoiceID.NEWS_ANCHOR, "name": "新闻女声", "gender": "female", "description": "专业新闻女主播"},
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
