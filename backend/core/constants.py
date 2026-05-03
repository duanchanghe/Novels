# ===========================================
# 共享常量定义模块
# ===========================================

"""
共享常量定义模块

集中管理项目中多处重复使用的常量定义：
- 音色映射表（svc_minimax_tts / svc_voice_mapper 原有重复）
- 情感参数映射表
- 角色映射表
- 网络小说特有角色映射
- 音频后处理配置

使用场景：
- svc_minimax_tts.py → from core.constants import VOICE_MAP
- svc_voice_mapper.py → from core.constants import ROLE_MAP, EMOTION_MAP
- svc_audio_postprocessor.py → from core.constants import PAUSE_CONFIG
- svc_deepseek_analyzer.py → from core.constants import POLYPHONE_DICT
"""

# ===========================================
# 音色 ID 常量（MiniMax 音色 ID 统一管理）
# ===========================================

class VoiceID:
    """MiniMax 音色 ID 常量"""
    # 男性音色
    MALE_QN = "male-qn"                # 青年男声（通用男主/旁白）
    MALE_QN_QINGSE = "male-qn-qingse"  # 青年男声-清澈
    MALE_YUN = "male-yun"              # 沉稳男声（老人/长辈）
    MALE_YUNQI = "male-yunqi"          # 男声-元气
    MALE_SHAON = "male-shaon"          # 少年男声
    MALE_TIAN = "male-tian"            # 低沉男声（反派）
    # 女性音色
    FEMALE_SHAON = "female-shaon"      # 少女音（通用女主）
    FEMALE_TIANMEI = "female-tianmei"  # 甜美女声
    FEMALE_SS = "female-ss"            # 成熟女声（老妇）
    FEMALE_DON = "female-don"          # 年长女声
    FEMALE_XIANG = "female-xiang"      # 童声


# ===========================================
# 角色 → 音色配置映射表（唯一来源）
# ===========================================

ROLE_VOICE_MAP = {
    # ── 旁白/叙述 ──
    "旁白":     {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "叙述":     {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "描写":     {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "narrator": {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},

    # ── 男性角色 ──
    "男主":       {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "男性主角":   {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "男":         {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "男性":       {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "male":       {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "male-young": {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "male-adult": {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},

    # ── 女性角色 ──
    "女主":         {"voice_id": VoiceID.FEMALE_SHAON, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "女性主角":     {"voice_id": VoiceID.FEMALE_SHAON, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "女":           {"voice_id": VoiceID.FEMALE_SHAON, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "女性":         {"voice_id": VoiceID.FEMALE_SHAON, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "female":       {"voice_id": VoiceID.FEMALE_SHAON, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "female-young": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "female-adult": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 1.0, "pitch": 0, "emotion": "neutral"},

    # ── 年长角色 ──
    "老人":     {"voice_id": VoiceID.MALE_YUN, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "老者":     {"voice_id": VoiceID.MALE_YUN, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "老者女性": {"voice_id": VoiceID.FEMALE_DON, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "老妇":     {"voice_id": VoiceID.FEMALE_DON, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "male-elderly":   {"voice_id": VoiceID.MALE_YUNQI, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "female-elderly": {"voice_id": VoiceID.FEMALE_SS, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},

    # ── 儿童/少年角色 ──
    "儿童":   {"voice_id": VoiceID.FEMALE_XIANG, "speed": 1.1, "pitch": 0.2, "emotion": "happy"},
    "孩童":   {"voice_id": VoiceID.FEMALE_XIANG, "speed": 1.1, "pitch": 0.2, "emotion": "happy"},
    "少年":   {"voice_id": VoiceID.MALE_QN, "speed": 1.05, "pitch": 0.1, "emotion": "neutral"},
    "少女":   {"voice_id": VoiceID.FEMALE_SHAON, "speed": 1.05, "pitch": 0.1, "emotion": "happy"},
    "female-child": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 1.1, "pitch": 0.2, "emotion": "happy"},

    # ── 反派角色 ──
    "反派":       {"voice_id": VoiceID.MALE_TIAN, "speed": 0.95, "pitch": 0.1, "emotion": "serious"},
    "坏人":       {"voice_id": VoiceID.MALE_TIAN, "speed": 0.95, "pitch": 0.1, "emotion": "serious"},
    "boss":       {"voice_id": VoiceID.MALE_TIAN, "speed": 0.9, "pitch": 0.15, "emotion": "serious"},
    "male-deep":  {"voice_id": VoiceID.MALE_SHAON, "speed": 0.95, "pitch": 0.1, "emotion": "serious"},
    "male-villain": {"voice_id": VoiceID.MALE_SHAON, "speed": 0.95, "pitch": 0.1, "emotion": "serious"},

    # ── 网络小说特有角色 ──
    "仙尊": {"voice_id": VoiceID.MALE_YUNQI, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "魔帝": {"voice_id": VoiceID.MALE_SHAON, "speed": 0.95, "pitch": 0.05, "emotion": "serious"},
    "剑圣": {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "道祖": {"voice_id": VoiceID.MALE_YUNQI, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "长老": {"voice_id": VoiceID.MALE_YUNQI, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "宗主": {"voice_id": VoiceID.MALE_YUNQI, "speed": 0.9, "pitch": -0.05, "emotion": "serious"},
    "掌门": {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 0.95, "pitch": -0.05, "emotion": "serious"},
    "前辈": {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 0.95, "pitch": -0.05, "emotion": "neutral"},
    "师兄": {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "师弟": {"voice_id": VoiceID.MALE_QN, "speed": 1.05, "pitch": 0.05, "emotion": "neutral"},
    "师父": {"voice_id": VoiceID.MALE_YUN, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "师傅": {"voice_id": VoiceID.MALE_YUN, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "徒弟": {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "圣女": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 0.95, "pitch": -0.05, "emotion": "gentle"},
    "仙女": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 0.95, "pitch": 0, "emotion": "gentle"},
    "仙子": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 0.95, "pitch": 0, "emotion": "gentle"},
    "妖女": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 1.05, "pitch": 0.05, "emotion": "happy"},
    "魔女": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 1.0, "pitch": 0.05, "emotion": "serious"},
    "女帝": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 0.95, "pitch": -0.05, "emotion": "serious"},

    # ── 主角别名 ──
    "male-hero":         {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "male-protagonist":  {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "female-heroine":    {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "female-protagonist":{"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "female-sweet":      {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 1.0, "pitch": 0, "emotion": "happy"},

    # ── 旁白别名（英文） ──
    "male-narrator":   {"voice_id": VoiceID.MALE_QN_QINGSE, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "female-narrator": {"voice_id": VoiceID.FEMALE_TIANMEI, "speed": 1.0, "pitch": 0, "emotion": "neutral"},

    # ── 默认映射 ──
    "未识别": {"voice_id": VoiceID.MALE_QN, "speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "male-old": {"voice_id": VoiceID.MALE_YUNQI, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
    "female-old": {"voice_id": VoiceID.FEMALE_SS, "speed": 0.9, "pitch": -0.1, "emotion": "neutral"},
}

# 默认配置（未识别角色时使用）
DEFAULT_VOICE_CONFIG = ROLE_VOICE_MAP["未识别"]


# ===========================================
# 情感 → MiniMax 参数映射表（唯一来源）
# ===========================================

EMOTION_PARAM_MAP = {
    # ── 平静/中性 ──
    "平静":         {"emotion": "neutral",  "pitch": 0,     "speed_factor": 1.0},
    "平静_low":     {"emotion": "neutral",  "pitch": 0,     "speed_factor": 0.95},
    "平静_medium":  {"emotion": "neutral",  "pitch": 0,     "speed_factor": 1.0},
    "平静_high":    {"emotion": "neutral",  "pitch": 0,     "speed_factor": 1.05},
    "neutral":      {"emotion": "neutral",  "pitch": 0,     "speed_factor": 1.0},

    # ── 高兴 ──
    "高兴":         {"emotion": "happy",    "pitch": 0.15,  "speed_factor": 1.05},
    "高兴_low":     {"emotion": "happy",    "pitch": 0.1,   "speed_factor": 1.05},
    "高兴_medium":  {"emotion": "happy",    "pitch": 0.2,   "speed_factor": 1.1},
    "高兴_high":    {"emotion": "happy",    "pitch": 0.3,   "speed_factor": 1.15},
    "开心":         {"emotion": "happy",    "pitch": 0.15,  "speed_factor": 1.05},
    "开心_low":     {"emotion": "happy",    "pitch": 0.1,   "speed_factor": 1.05},
    "开心_medium":  {"emotion": "happy",    "pitch": 0.2,   "speed_factor": 1.1},
    "开心_high":    {"emotion": "happy",    "pitch": 0.3,   "speed_factor": 1.15},
    "快乐":         {"emotion": "happy",    "pitch": 0.15,  "speed_factor": 1.05},
    "喜悦":         {"emotion": "happy",    "pitch": 0.15,  "speed_factor": 1.05},

    # ── 悲伤 ──
    "悲伤":         {"emotion": "sad",      "pitch": -0.25, "speed_factor": 0.9},
    "悲伤_low":     {"emotion": "sad",      "pitch": -0.2,  "speed_factor": 0.95},
    "悲伤_medium":  {"emotion": "sad",      "pitch": -0.25, "speed_factor": 0.9},
    "悲伤_high":    {"emotion": "sad",      "pitch": -0.3,  "speed_factor": 0.85},
    "伤心":         {"emotion": "sad",      "pitch": -0.25, "speed_factor": 0.9},
    "难过":         {"emotion": "sad",      "pitch": -0.2,  "speed_factor": 0.95},
    "痛苦":         {"emotion": "sad",      "pitch": -0.3,  "speed_factor": 0.85},

    # ── 愤怒 ──
    "愤怒":         {"emotion": "angry",    "pitch": 0.35,  "speed_factor": 1.15},
    "愤怒_low":     {"emotion": "angry",    "pitch": 0.3,   "speed_factor": 1.1},
    "愤怒_medium":  {"emotion": "angry",    "pitch": 0.4,   "speed_factor": 1.15},
    "愤怒_high":    {"emotion": "angry",    "pitch": 0.5,   "speed_factor": 1.2},
    "生气":         {"emotion": "angry",    "pitch": 0.35,  "speed_factor": 1.15},
    "恼怒":         {"emotion": "angry",    "pitch": 0.3,   "speed_factor": 1.1},
    "暴怒":         {"emotion": "angry",    "pitch": 0.5,   "speed_factor": 1.2},

    # ── 紧张/害怕 ──
    "紧张":         {"emotion": "fearful",  "pitch": 0.15,  "speed_factor": 1.15},
    "紧张_low":     {"emotion": "fearful",  "pitch": 0.1,   "speed_factor": 1.1},
    "紧张_medium":  {"emotion": "fearful",  "pitch": 0.15,  "speed_factor": 1.15},
    "紧张_high":    {"emotion": "fearful",  "pitch": 0.2,   "speed_factor": 1.2},
    "害怕":         {"emotion": "fearful",  "pitch": 0.15,  "speed_factor": 1.15},
    "恐惧":         {"emotion": "fearful",  "pitch": 0.2,   "speed_factor": 1.2},
    "惊恐":         {"emotion": "fearful",  "pitch": 0.25,  "speed_factor": 1.25},

    # ── 惊讶 ──
    "惊讶":         {"emotion": "surprise", "pitch": 0.35,  "speed_factor": 1.15},
    "震惊":         {"emotion": "surprise", "pitch": 0.4,   "speed_factor": 1.2},
    "诧异":         {"emotion": "surprise", "pitch": 0.3,   "speed_factor": 1.15},
    "惊愕":         {"emotion": "surprise", "pitch": 0.4,   "speed_factor": 1.2},

    # ── 温柔 ──
    "温柔":         {"emotion": "gentle",   "pitch": -0.1,  "speed_factor": 0.9},
    "柔和":         {"emotion": "gentle",   "pitch": -0.1,  "speed_factor": 0.9},
    "轻柔":         {"emotion": "gentle",   "pitch": -0.15, "speed_factor": 0.85},
    "温情":         {"emotion": "gentle",   "pitch": -0.1,  "speed_factor": 0.9},

    # ── 严肃 ──
    "严肃":         {"emotion": "serious",  "pitch": -0.1,  "speed_factor": 0.9},
    "正经":         {"emotion": "serious",  "pitch": -0.1,  "speed_factor": 0.9},
    "郑重":         {"emotion": "serious",  "pitch": -0.15, "speed_factor": 0.85},
}

# 默认情感配置
DEFAULT_EMOTION_CONFIG = EMOTION_PARAM_MAP["平静"]


# ===========================================
# MiniMax TTS 兼容的 VOICE_MAP（英文 key → 简化的5角色映射）
# ===========================================
# 用于 svc_minimax_tts.py 中直接按 key 查找 voice_id

VOICE_MAP_SIMPLE = {
    "narrator":         VoiceID.MALE_QN_QINGSE,
    "male-narrator":    VoiceID.MALE_QN_QINGSE,
    "female-narrator":  VoiceID.FEMALE_TIANMEI,
    "male":             VoiceID.MALE_QN_QINGSE,
    "male-young":       VoiceID.MALE_QN_QINGSE,
    "male-adult":       VoiceID.MALE_QN_QINGSE,
    "male-elderly":     VoiceID.MALE_YUNQI,
    "male-old":         VoiceID.MALE_YUNQI,
    "male-deep":        VoiceID.MALE_SHAON,
    "male-villain":     VoiceID.MALE_SHAON,
    "male-hero":        VoiceID.MALE_QN_QINGSE,
    "male-protagonist": VoiceID.MALE_QN_QINGSE,
    "female":           VoiceID.FEMALE_SHAON,
    "female-young":     VoiceID.FEMALE_TIANMEI,
    "female-adult":     VoiceID.FEMALE_TIANMEI,
    "female-elderly":   VoiceID.FEMALE_SS,
    "female-old":       VoiceID.FEMALE_SS,
    "female-child":     VoiceID.FEMALE_TIANMEI,
    "female-sweet":     VoiceID.FEMALE_TIANMEI,
    "female-heroine":   VoiceID.FEMALE_TIANMEI,
    "female-protagonist": VoiceID.FEMALE_TIANMEI,
}


# ===========================================
# 强度因子映射
# ===========================================

INTENSITY_FACTOR_MAP = {
    "low": 0.8,
    "medium": 1.0,
    "high": 1.2,
}


# ===========================================
# 音频后处理配置（唯一来源）
# ===========================================

PAUSE_CONFIG = {
    "sentence_end": 500,      # 句号/问号/感叹号后停顿（毫秒）
    "paragraph_end": 1000,    # 段落结束停顿
    "chapter_end": 2500,      # 章节结束停顿
    "emotion_pause": 300,     # 情感切换停顿
    "dialogue_break": 200,    # 对话间隔停顿
}

EQ_CONFIG = {
    "low_cut": 80,            # 低频切除（Hz）
    "high_boost": 3000,       # 高频提升起始点（Hz）
    "high_boost_db": 2,       # 高频提升量（dB）
    "low_cut_db": -3,         # 低频切除量（dB）
}

# 音频质量标准
TARGET_LUFS = -16.0           # Spotify/YouTube 标准响度
PEAK_LIMIT_DB = -1.0          # 峰值限制（dB TP）
DEFAULT_SAMPLE_RATE = 44100   # CD 标准采样率
DEFAULT_BITRATE_HIGH = "320k" # 高品质比特率
DEFAULT_BITRATE_STANDARD = "192k"  # 标准比特率


# ===========================================
# 常用多音字消歧规则库
# ===========================================

POLYPHONE_DICT = {
    "行": {"银行": "háng", "行为": "xíng", "行吗": "xíng", "一行": "xíng"},
    "说": {"说服": "shuō", "游说": "shuì", "说客": "shuō"},
    "了": {"了解": "liǎo", "走了": "le", "了结": "liǎo"},
    "着": {"看着": "zhe", "着急": "zháo", "衣着": "zhuó"},
    "得": {"得到": "dé", "跑得快": "de", "必须": "děi"},
    "为": {"因为": "wèi", "作为": "wéi"},
    "还": {"还有": "hái", "归还": "huán"},
    "只": {"只要": "zhǐ", "一只": "zhī"},
    "长": {"成长": "zhǎng", "长度": "cháng", "长大": "zhǎng"},
    "重": {"重要": "zhòng", "重新": "chóng", "重量": "zhòng"},
    "传": {"传说": "chuán", "传记": "zhuàn"},
}
