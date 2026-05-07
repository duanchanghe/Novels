# ===========================================
# 角色音色智能匹配服务
# ===========================================

"""
角色音色智能匹配服务

根据角色属性（性别、年龄、性格、说话风格）智能推荐最佳音色。

功能特性：
- 基于角色属性智能推荐音色
- 支持批量为全书角色匹配音色
- 支持音色预览和手动调整
- 自动从 MiniMax API 获取最新音色列表
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from core.constants import (
    ROLE_VOICE_MAP,
    EMOTION_PARAM_MAP,
    VoiceID,
)
from core.models import Character
from core.models.voice import VoiceProfile
from core.models.voice import RoleType as VoiceRoleType
from core.models.character import CharacterStatus, GenderType


logger = logging.getLogger("audiobook")


class VoiceMatchConfidence(Enum):
    """音色匹配置信度（数值越高优先级越高）"""
    HIGH = 3      # 高置信度 - 属性完全匹配
    MEDIUM = 2   # 中置信度 - 部分属性匹配
    LOW = 1      # 低置信度 - 推测匹配


@dataclass
class VoiceMatchResult:
    """音色匹配结果"""
    character_id: int
    character_name: str
    recommended_voice_id: str
    recommended_voice_name: str
    confidence: VoiceMatchConfidence
    match_reasons: List[str]
    gender: str
    age_group: str
    speech_style_preview: str


@dataclass
class CharacterVoiceConfig:
    """角色语音配置"""
    voice_id: str
    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0
    emotion: str = "neutral"


# ===========================================
# 音色推荐规则引擎
# ===========================================

class VoiceRecommendEngine:
    """
    音色推荐规则引擎

    基于角色属性（性别、年龄、性格、说话风格）推荐最佳音色。
    """

    # 性别 → 基础音色映射
    GENDER_BASE_VOICE = {
        GenderType.MALE: VoiceID.MALE_QN_QINGSE,
        GenderType.FEMALE: VoiceID.FEMALE_SHAON,
        "male": VoiceID.MALE_QN_QINGSE,
        "female": VoiceID.FEMALE_SHAON,
    }

    # 年龄组 → 音色映射（按性别）
    AGE_GROUP_VOICE_MAP = {
        # 儿童
        ("child", "male"): VoiceID.CLEVER_BOY,
        ("child", "female"): VoiceID.LOVELY_GIRL,
        ("child", GenderType.MALE): VoiceID.CLEVER_BOY,
        ("child", GenderType.FEMALE): VoiceID.LOVELY_GIRL,
        # 青年
        ("youth", "male"): VoiceID.MALE_QN_QINGSE,
        ("youth", "female"): VoiceID.FEMALE_SHAON,
        ("youth", GenderType.MALE): VoiceID.MALE_QN_QINGSE,
        ("youth", GenderType.FEMALE): VoiceID.FEMALE_SHAON,
        # 成年
        ("adult", "male"): VoiceID.MALE_QN_QINGSE,
        ("adult", "female"): VoiceID.FEMALE_SHAON,
        ("adult", GenderType.MALE): VoiceID.MALE_QN_QINGSE,
        ("adult", GenderType.FEMALE): VoiceID.FEMALE_SHAON,
        # 老年
        ("elderly", "male"): VoiceID.HUMOROUS_ELDER,
        ("elderly", "female"): VoiceID.KIND_ELDER,
        ("elderly", GenderType.MALE): VoiceID.HUMOROUS_ELDER,
        ("elderly", GenderType.FEMALE): VoiceID.KIND_ELDER,
    }

    # 性格/说话风格关键词 → 音色调整
    STYLE_VOICE_OVERRIDES = [
        # 关键词, 性别, 推荐音色, 置信度提升
        ("权威", "male", VoiceID.RELIABLE_EXECUTIVE, VoiceMatchConfidence.HIGH),
        ("威严", "male", VoiceID.RELIABLE_EXECUTIVE, VoiceMatchConfidence.HIGH),
        ("严肃", "male", VoiceID.MALE_QN_BADAO, VoiceMatchConfidence.MEDIUM),
        ("霸道", "male", VoiceID.MALE_QN_BADAO, VoiceMatchConfidence.HIGH),
        ("温和", "male", VoiceID.GENTLEMAN, VoiceMatchConfidence.MEDIUM),
        ("文雅", "male", VoiceID.GENTLEMAN, VoiceMatchConfidence.MEDIUM),
        ("幽默", "male", VoiceID.HUMOROUS_ELDER, VoiceMatchConfidence.HIGH),
        ("播音", "male", VoiceID.MALE_ANCHOR, VoiceMatchConfidence.HIGH),
        ("低沉", "male", VoiceID.MALE_QN_BADAO, VoiceMatchConfidence.MEDIUM),

        ("温柔", "female", VoiceID.FEMALE_TIANMEI, VoiceMatchConfidence.HIGH),
        ("甜美", "female", VoiceID.FEMALE_TIANMEI, VoiceMatchConfidence.HIGH),
        ("活泼", "female", VoiceID.FEMALE_SHAON, VoiceMatchConfidence.MEDIUM),
        ("成熟", "female", VoiceID.FEMALE_CHENGSHU, VoiceMatchConfidence.HIGH),
        ("御姐", "female", VoiceID.FEMALE_YUJIE, VoiceMatchConfidence.HIGH),
        ("亲切", "female", VoiceID.WARM_BESTIE, VoiceMatchConfidence.MEDIUM),
        ("权威", "female", VoiceID.FEMALE_CHENGSHU, VoiceMatchConfidence.MEDIUM),
        ("贵妇", "female", VoiceID.FEMALE_CHENGSHU, VoiceMatchConfidence.HIGH),
    ]

    # MiniMax 音色名称映射（用于显示）
    VOICE_NAME_MAP = {
        VoiceID.MALE_QN_QINGSE: "青涩青年音色",
        VoiceID.MALE_QN_JINGYING: "精英青年音色",
        VoiceID.MALE_QN_BADAO: "霸道青年音色",
        VoiceID.MALE_QN_DAXUESHENG: "青年大学生音色",
        VoiceID.FEMALE_SHAON: "少女音色",
        VoiceID.FEMALE_YUJIE: "御姐音色",
        VoiceID.FEMALE_CHENGSHU: "成熟女性音色",
        VoiceID.FEMALE_TIANMEI: "甜美女声音色",
        VoiceID.CLEVER_BOY: "聪明男童音色",
        VoiceID.CUTE_BOY: "可爱男童音色",
        VoiceID.LOVELY_GIRL: "萌萌女童音色",
        VoiceID.HUMOROUS_ELDER: "搞笑大爷音色",
        VoiceID.RELIABLE_EXECUTIVE: "沉稳高管音色",
        VoiceID.MALE_ANCHOR: "播报男声音色",
        VoiceID.GENTLEMAN: "温润男声音色",
        VoiceID.KIND_ELDER: "花甲奶奶音色",
        VoiceID.WARM_BESTIE: "温暖闺蜜音色",
        VoiceID.FEMALE_TIANMEI: "甜美女声音色",
    }

    def get_voice_name(self, voice_id: str) -> str:
        """获取音色的中文名称"""
        return self.VOICE_NAME_MAP.get(voice_id, voice_id)

    def recommend_voice(
        self,
        character: Character,
    ) -> VoiceMatchResult:
        """
        为单个角色推荐最佳音色

        Args:
            character: Character 模型实例

        Returns:
            VoiceMatchResult: 匹配结果
        """
        gender = character.gender or "unknown"
        age_group = character.age_group or "adult"
        speech_style = character.speech_style or ""
        personality = character.personality or ""
        voice_description = character.voice_description or ""

        # 合并所有文本用于关键词匹配
        all_text = f"{speech_style} {personality} {voice_description}"

        match_reasons = []
        recommended_voice_id = None
        confidence = VoiceMatchConfidence.MEDIUM

        # 策略1: 基于性格/说话风格关键词匹配
        for keyword, voice_gender, voice_id, conf in self.STYLE_VOICE_OVERRIDES:
            if keyword in all_text and (gender == voice_gender or gender == "unknown"):
                recommended_voice_id = voice_id
                confidence = conf
                match_reasons.append(f"说话风格包含「{keyword}」")
                break

        # 策略2: 基于年龄组+性别匹配
        if not recommended_voice_id:
            age_key = (age_group, gender)
            if age_key in self.AGE_GROUP_VOICE_MAP:
                recommended_voice_id = self.AGE_GROUP_VOICE_MAP[age_key]
                confidence = VoiceMatchConfidence.HIGH
                match_reasons.append(f"基于年龄组({age_group})和性别({gender})")
            else:
                # 尝试只用性别
                if gender in self.GENDER_BASE_VOICE:
                    recommended_voice_id = self.GENDER_BASE_VOICE[gender]
                    confidence = VoiceMatchConfidence.MEDIUM
                    match_reasons.append(f"基于性别({gender})")
                else:
                    # 默认使用清澈青年
                    recommended_voice_id = VoiceID.MALE_QN_QINGSE
                    confidence = VoiceMatchConfidence.LOW
                    match_reasons.append("使用默认音色")

        # 策略3: 角色名关键词匹配
        name = character.name or ""
        name_voice_overrides = [
            ("爷", "male", VoiceID.HUMOROUS_ELDER, "称呼包含「爷」"),
            ("奶奶", "female", VoiceID.KIND_ELDER, "称呼包含「奶奶」"),
            ("公子", "male", VoiceID.GENTLEMAN, "称呼包含「公子」"),
            ("少爷", "male", VoiceID.MALE_QN_BADAO, "称呼包含「少爷」"),
            ("仙女", "female", VoiceID.FEMALE_TIANMEI, "称呼包含「仙女」"),
            ("公主", "female", VoiceID.FEMALE_SHAON, "称呼包含「公主」"),
            ("女王", "female", VoiceID.FEMALE_CHENGSHU, "称呼包含「女王」"),
            ("老师", "male", VoiceID.RELIABLE_EXECUTIVE, "称呼包含「老师」"),
            ("医生", "male", VoiceID.MALE_ANCHOR, "称呼包含「医生」"),
            ("记者", "male", VoiceID.MALE_ANCHOR, "称呼包含「记者」"),
            ("主持人", "male", VoiceID.MALE_ANCHOR, "称呼包含「主持人」"),
            ("老板", "male", VoiceID.MALE_QN_BADAO, "称呼包含「老板」"),
            ("教授", "male", VoiceID.RELIABLE_EXECUTIVE, "称呼包含「教授」"),
        ]

        for keyword, voice_gender, voice_id, reason in name_voice_overrides:
            if keyword in name:
                recommended_voice_id = voice_id
                confidence = VoiceMatchConfidence.HIGH
                match_reasons.append(reason)
                break

        # 策略4: 特殊角色类型
        role_type = character.role_type or ""
        if "protagonist" in role_type.lower() or "主角" in name:
            if gender == GenderType.FEMALE:
                recommended_voice_id = VoiceID.FEMALE_TIANMEI
                match_reasons.append("女主角")
            else:
                recommended_voice_id = VoiceID.MALE_QN_QINGSE
                match_reasons.append("男主角")
            confidence = VoiceMatchConfidence.HIGH

        return VoiceMatchResult(
            character_id=character.id,
            character_name=character.name,
            recommended_voice_id=recommended_voice_id,
            recommended_voice_name=self.get_voice_name(recommended_voice_id),
            confidence=confidence,
            match_reasons=match_reasons,
            gender=gender,
            age_group=age_group,
            speech_style_preview=speech_style[:50] if speech_style else "",
        )


class CharacterVoiceMatcher:
    """
    角色音色批量匹配服务

    为书籍的所有角色批量匹配最佳音色。
    """

    def __init__(self):
        self.engine = VoiceRecommendEngine()

    def match_book_characters(self, book_id: int) -> List[VoiceMatchResult]:
        """
        为书籍的所有角色匹配音色

        Args:
            book_id: 书籍ID

        Returns:
            list[VoiceMatchResult]: 所有角色的匹配结果
        """
        characters = Character.objects.filter(
            book_id=book_id,
            status=CharacterStatus.ACTIVE,
        ).exclude(
            name__in=["旁白", "narrator", "叙述", "描写", "未识别", "unknown"]
        ).order_by("role_type", "name")

        results = []
        for char in characters:
            result = self.engine.recommend_voice(char)
            results.append(result)

        return results

    def apply_matches(
        self,
        results: List[VoiceMatchResult],
        min_confidence: VoiceMatchConfidence = VoiceMatchConfidence.LOW,
        create_voice_profiles: bool = True,
    ) -> Tuple[int, int]:
        """
        应用匹配结果到角色

        Args:
            results: 匹配结果列表
            min_confidence: 最低置信度阈值
            create_voice_profiles: 是否创建音色配置记录

        Returns:
            tuple: (成功更新的数量, 创建的音色配置数量)
        """
        updated_count = 0
        created_profile_count = 0

        for result in results:
            if result.confidence.value < min_confidence.value:
                continue

            try:
                character = Character.objects.get(id=result.character_id)

                # 查找或创建音色配置
                voice_profile, created = VoiceProfile.objects.get_or_create(
                    book_id=character.book_id,
                    name=f"角色配置_{character.name}",
                    defaults={
                        "role_type": VoiceRoleType.SUPPORTING,
                        "minimax_voice_id": result.recommended_voice_id,
                        "speed": 1.0,
                        "pitch": 0.0,
                        "volume": 1.0,
                        "is_system_preset": False,
                    }
                )

                if created:
                    created_profile_count += 1

                # 更新角色的语音配置
                character.voice_profile = voice_profile
                character.custom_voice_id = result.recommended_voice_id
                character.save()

                updated_count += 1
                logger.info(
                    f"角色「{result.character_name}」匹配音色「{result.recommended_voice_name}」(置信度:{result.confidence.value})"
                )

            except Character.DoesNotExist:
                logger.warning(f"角色ID {result.character_id} 不存在")

        return updated_count, created_profile_count

    def preview_matches(self, book_id: int) -> Dict[str, Any]:
        """
        预览匹配结果（不实际应用）

        Args:
            book_id: 书籍ID

        Returns:
            dict: 预览统计信息
        """
        results = self.match_book_characters(book_id)

        # 统计
        total = len(results)
        by_confidence = {}
        by_gender = {}
        by_age_group = {}
        voice_usage = {}

        for r in results:
            # 按置信度统计
            conf = r.confidence.value
            conf_name = {3: "high", 2: "medium", 1: "low"}.get(conf, str(conf))
            by_confidence[conf_name] = by_confidence.get(conf_name, 0) + 1

            # 按性别统计
            by_gender[r.gender] = by_gender.get(r.gender, 0) + 1

            # 按年龄统计
            by_age_group[r.age_group] = by_age_group.get(r.age_group, 0) + 1

            # 音色使用统计
            voice_usage[r.recommended_voice_id] = voice_usage.get(r.recommended_voice_id, 0) + 1

        # 排序音色使用
        voice_usage_sorted = sorted(
            voice_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "total_characters": total,
            "by_confidence": by_confidence,
            "by_gender": by_gender,
            "by_age_group": by_age_group,
            "voice_usage": [
                {
                    "voice_id": vid,
                    "voice_name": self.engine.get_voice_name(vid),
                    "count": count,
                }
                for vid, count in voice_usage_sorted[:10]
            ],
            "characters": [
                {
                    "id": r.character_id,
                    "name": r.character_name,
                    "gender": r.gender,
                    "age_group": r.age_group,
                    "recommended_voice": r.recommended_voice_name,
                    "confidence": {3: "high", 2: "medium", 1: "low"}.get(r.confidence.value, "unknown"),
                    "reasons": r.match_reasons,
                    "speech_style": r.speech_style_preview,
                }
                for r in results
            ],
        }
