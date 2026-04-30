# ===========================================
# 中文网络小说文本处理器
# ===========================================

"""
中文网络小说文本处理器

专门处理网络小说的特殊格式和表达，包括：
- 玄幻/都市/仙侠小说的特有格式
- 内心独白识别（心想、暗道）
- 系统提示识别（[系统提示]、[任务发布]）
- 古文/诗词识别
- 特殊符号处理
- 角色称呼识别

这个模块是 DeepSeek 分析服务的补充，提供更精准的网络小说文本理解能力。
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict


logger = logging.getLogger("audiobook")


# ===========================================
# 数据结构定义
# ===========================================

class TextType(str, Enum):
    """文本类型枚举"""
    NARRATION = "narration"           # 旁白/叙述
    DIALOGUE = "dialogue"           # 对话
    INNER_THOUGHT = "inner_thought" # 内心独白
    SYSTEM提示 = "system"            # 系统提示
    POETRY = "poetry"               # 诗词/古文
    SCENE_DESC = "scene_desc"       # 场景描述
    ACTION = "action"               # 动作描写
    UNKNOWN = "unknown"              # 未知类型


class NovelGenre(str, Enum):
    """小说类型枚举"""
    XUANHUAN = "xuanhuan"           # 玄幻
    YUSHIXIA = "yushixia"           # 都市
    XIANXIA = "xianxia"             # 仙侠
    LIXIA = "lixia"                # 历史/穿越
    KEHUN = "kehuan"               # 科幻
    QINGXU = "qingxu"              # 青春校园
    DUSHANG = "dushang"            # 都市商战
    TIANEG = "tianyi"              # 甜文/宠文
    ANTU = "antu"                  # 虐文
    GUZHUAN = "guzhuan"            # 古言/古穿


@dataclass
class NovelTextSegment:
    """小说文本片段"""
    text: str
    text_type: TextType
    speaker: Optional[str] = None
    emotion: Optional[str] = None
    genre_tags: List[str] = None
    special_markers: List[str] = None
    
    def __post_init__(self):
        if self.genre_tags is None:
            self.genre_tags = []
        if self.special_markers is None:
            self.special_markers = []


@dataclass
class Character:
    """角色信息"""
    name: str
    role_type: str  # 男主/女主/反派/配角/配角
    aliases: List[str]
    gender: str  # male/female/unknown
    age_range: str  # young/adult/elderly/unknown
    first_appearance: Optional[str] = None
    dialogue_count: int = 0
    emotions: Set[str] = None
    
    def __post_init__(self):
        if self.emotions is None:
            self.emotions = set()


# ===========================================
# 内心独白识别模式
# ===========================================

INNER_THOUGHT_PATTERNS = [
    # 中文括号类
    (r"^（(.*?)）$", "round"),        # （心想）
    (r"^\((.*?)\)$", "round"),        # (心想)
    (r"^\[（(.*?)）\]$", "bracket"),  # [（暗道）]
    (r"^\[（(.*?)）\]$", "bracket"),  # [（心道）]
    
    # 星号类（常用于强调）
    (r"^\*\*((?:(?!\*\*).)*)\*\*$", "bold"),  # **内心独白**
    (r"^\*((?:(?!\*).)*)\*$", "star"),  # *内心独白*
    
    # 常见内心独白关键词
    (r"^(?:心想|心道|暗道|暗想|思忖|思虑|思考|想着)[:：]?\s*", "keyword"),
    (r"^(?:暗暗|暗自|悄悄|默默)(?:想|道|忖|思|嘀咕)[:：]?\s*", "keyword"),
    
    # 网络小说特有
    (r"^\[内心OS[：:]\s*(.*?)\]$", "os"),  # [内心OS: ...]
    (r"^\[独白[：:]\s*(.*?)\]$", "monologue"),
    (r"^(?:与此同时|与此同时)[:：]?\s*", "Meanwhile"),
]

# ===========================================
# 系统提示识别模式
# ===========================================

SYSTEM_PROMPT_PATTERNS = [
    # 标准系统提示
    (r"^\[系统提示[：:]\s*(.*?)\]$", "system"),
    (r"^\[系统[：:]\s*(.*?)\]$", "system"),
    (r"^\[系统公告[：:]\s*(.*?)\]$", "system"),
    
    # 游戏系统提示
    (r"^\[任务发布[：:]\s*(.*?)\]$", "quest"),
    (r"^\[任务完成[：:]\s*(.*?)\]$", "quest"),
    (r"^\[获得奖励[：:]\s*(.*?)\]$", "reward"),
    (r"^\[技能升级[：:]\s*(.*?)\]$", "skill"),
    (r"^\[属性变化[：:]\s*(.*?)\]$", "attribute"),
    
    # 修仙系统提示
    (r"^\[突破成功[：:]\s*(.*?)\]$", "breakthrough"),
    (r"^\[境界提升[：:]\s*(.*?)\]$", "breakthrough"),
    (r"^\[灵根觉醒[：:]\s*(.*?)\]$", "talent"),
    (r"^\[获得(?:逆天)?(?:机缘|传承|秘术)[：:]\s*(.*?)\]$", "reward"),
    
    # 现代都市系统
    (r"^\[好感度[+↑][：:]\s*(.*?)\]$", "affection"),
    (r"^\[人气值[+↑][：:]\s*(.*?)\]$", "popularity"),
    (r"^\[财富值[+↑][：:]\s*(.*?)\]$", "wealth"),
    
    # 通用括号提示
    (r"^\[【(.*?)】\]$", "bracket"),
    (r"^\[『(.*?)』\]$", "bracket"),
]


# ===========================================
# 诗词/古文识别模式
# ===========================================

POETRY_PATTERNS = [
    # 标准词牌名
    (r"^(?:《([^》]+)》)$", "ci"),  # 《沁园春》
    
    # 诗词格式（每行分开）
    (r"^(.{5,7})\s*[，,。]$", "poetry_line"),  # 五言/七言诗句
    
    # 古文引用
    (r"^(?:古人云|古人言|书云)[:：]\s*", "quote"),
    (r"^(?:有道是|常言道|俗话说)[:：]\s*", "proverb"),
    
    # 修仙特有
    (r"^\[功法口诀[：:]\s*(.*?)\]$", "technique"),
    (r"^\[心法要诀[：:]\s*(.*?)\]$", "technique"),
]


# ===========================================
# 玄幻/仙侠特有词汇
# ===========================================

CULTIVATION_TERMS = {
    # 境界
    "境界": ["炼气", "筑基", "金丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫", "地仙", "天仙", "金仙", "太乙", "大罗", "混元"],
    "体质": ["天灵根", "地灵根", "杂灵根", "特殊体质", "先天道体", "混沌体", "轮回体"],
    "功法": ["基础功法", "黄阶功法", "玄阶功法", "地阶功法", "天阶功法", "仙法"],
    "技能": ["基础法术", "初级法术", "中级法术", "高级法术", "禁术", "神通"],
    # 元素
    "元素": ["金", "木", "水", "火", "土", "雷", "风", "冰", "光", "暗"],
    # 其他
    "灵草": ["灵芝", "灵草", "仙草", "圣药"],
    "灵石": ["下品灵石", "中品灵石", "上品灵石", "极品灵石"],
}


# ===========================================
# 角色称呼识别
# ===========================================

ROLE_TITLES = {
    # 仙侠/玄幻
    "xianxia": {
        "前辈": "senior_cultivator",
        "道兄": "fellow_cultivator",
        "道友好": "fellow_cultivator",
        "仙尊": "immortal_venerable",
        "仙帝": "immortal_emperor",
        "仙王": "immortal_king",
        "魔尊": "demon_lord",
        "魔帝": "demon_emperor",
        "魔王": "demon_king",
        "宗主": "sect_master",
        "掌门": "sect_leader",
        "长老": "elder",
        "圣子": "holy_son",
        "圣女": "holy_daughter",
        "弟子": "disciple",
        "师兄": "senior_brother",
        "师弟": "junior_brother",
        "师姐": "senior_sister",
        "师妹": "junior_sister",
        "师父": "master",
        "师尊": "master",
        "师娘": "master_wife",
    },
    # 都市
    "urban": {
        "总裁": "ceo",
        "董事长": "chairman",
        "老板": "boss",
        "上司": "superior",
        "下属": "subordinate",
        "同事": "colleague",
        "闺蜜": "best_friend",
        "兄弟": "brother",
        "老婆": "wife",
        "老公": "husband",
        "媳妇": "wife",
        "相公": "husband",
        "岳父": "father_in_law",
        "岳母": "mother_in_law",
    },
    # 皇室
    "royal": {
        "陛下": "your_majesty",
        "皇上": "your_majesty",
        "皇": "emperor",
        "皇帝": "emperor",
        "皇后": "empress",
        "太子": "crown_prince",
        "公主": "princess",
        "王爷": "prince",
        "王妃": "princess_consort",
        "世子": "young_prince",
        "郡主": "county_princess",
        "父皇": "father_emperor",
        "母后": "mother_empress",
    },
    # 古代
    "ancient": {
        "老爷": "master",
        "少爷": "young_master",
        "夫人": "lady",
        "少奶奶": "young_madam",
        "小姐": "miss",
        "公子": "young_gentleman",
        "大人": "official",
        "老爷": "master",
    },
}


# ===========================================
# 主要处理器类
# ===========================================

class NovelTextProcessor:
    """
    中文网络小说文本处理器
    
    提供网络小说特有的文本分析和处理功能。
    """
    
    def __init__(self, genre: NovelGenre = None):
        """
        初始化处理器
        
        Args:
            genre: 小说类型（可选，用于特定优化）
        """
        self.genre = genre or NovelGenre.XUANHUAN
        self._init_patterns()
    
    def _init_patterns(self):
        """初始化编译后的正则表达式"""
        self._inner_thought_re = []
        for pattern, pattern_type in INNER_THOUGHT_PATTERNS:
            self._inner_thought_re.append((re.compile(pattern), pattern_type))
        
        self._system_prompt_re = []
        for pattern, pattern_type in SYSTEM_PROMPT_PATTERNS:
            self._system_prompt_re.append((re.compile(pattern), pattern_type))
        
        self._poetry_re = []
        for pattern, pattern_type in POETRY_PATTERNS:
            self._poetry_re.append((re.compile(pattern), pattern_type))
    
    def detect_text_type(self, text: str) -> Tuple[TextType, Optional[str]]:
        """
        检测文本类型
        
        Args:
            text: 待检测文本
            
        Returns:
            tuple: (文本类型, 提取的内容或speaker)
        """
        text = text.strip()
        if not text:
            return TextType.UNKNOWN, None
        
        # 检测内心独白
        for pattern, ptype in self._inner_thought_re:
            match = pattern.match(text)
            if match:
                content = match.group(1) if match.lastindex else text
                return TextType.INNER_THOUGHT, content
        
        # 检测系统提示
        for pattern, ptype in self._system_prompt_re:
            match = pattern.match(text)
            if match:
                content = match.group(1) if match.lastindex else text
                return TextType.SYSTEM提示, content
        
        # 检测诗词/古文
        for pattern, ptype in self._poetry_re:
            match = pattern.match(text)
            if match:
                content = match.group(1) if match.lastindex else text
                return TextType.POETRY, content
        
        # 检测对话（引号括起）
        if self._is_dialogue(text):
            speaker = self._extract_dialogue_speaker(text)
            return TextType.DIALOGUE, speaker
        
        # 默认作为旁白处理
        return TextType.NARRATION, None
    
    def _is_dialogue(self, text: str) -> bool:
        """判断是否为对话"""
        dialogue_markers = ['"', '"', '"', '"', '"', "'", "'", "「", "」", "『", "』", "【", "】"]
        for marker in dialogue_markers:
            if marker in text:
                return True
        return False
    
    def _extract_dialogue_speaker(self, text: str) -> Optional[str]:
        """提取对话的说话人"""
        # 模式1: "说话人道：..."
        pattern1 = re.compile(r'^[""「『【]([^」』】]*)[""」』】][：:]\s*')
        match = pattern1.match(text)
        if match:
            return match.group(1)
        
        # 模式2: "说话人"道：...
        pattern2 = re.compile(r'^[""「『【]([^」』】]*)[""」』】][：:]\s*')
        match = pattern2.match(text)
        if match:
            return match.group(1)
        
        # 模式3: 说话人：...
        pattern3 = re.compile(r'^([^：:]+)[:：]\s*[""「『【]')
        match = pattern3.match(text)
        if match:
            return match.group(1)
        
        return None
    
    def detect_character_title(self, text: str) -> Optional[str]:
        """
        检测角色称呼
        
        Args:
            text: 文本内容
            
        Returns:
            str: 角色称呼类型，或 None
        """
        # 获取当前类型的称呼映射
        title_maps = []
        
        # 添加通用映射
        for genre_titles in ROLE_TITLES.values():
            title_maps.extend(genre_titles.keys())
        
        # 检测常见称呼
        for title in title_maps:
            if title in text:
                return title
        
        return None
    
    def extract_cultivation_terms(self, text: str) -> List[Dict[str, Any]]:
        """
        提取修炼术语
        
        Args:
            text: 文本内容
            
        Returns:
            list: 提取的修炼术语列表
        """
        results = []
        
        for category, terms in CULTIVATION_TERMS.items():
            for term in terms:
                if term in text:
                    # 找到位置
                    for match in re.finditer(re.escape(term), text):
                        results.append({
                            "term": term,
                            "category": category,
                            "start": match.start(),
                            "end": match.end(),
                            "context": text[max(0, match.start()-10):min(len(text), match.end()+10)],
                        })
        
        return results
    
    def extract_system_prompts(self, text: str) -> List[Dict[str, Any]]:
        """
        提取所有系统提示
        
        Args:
            text: 文本内容（可能是多行）
            
        Returns:
            list: 系统提示列表
        """
        results = []
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            for pattern, ptype in self._system_prompt_re:
                match = pattern.match(line)
                if match:
                    content = match.group(1) if match.lastindex else line
                    results.append({
                        "text": line,
                        "content": content,
                        "prompt_type": ptype,
                    })
                    break
        
        return results
    
    def extract_inner_thoughts(self, text: str) -> List[Dict[str, Any]]:
        """
        提取所有内心独白
        
        Args:
            text: 文本内容（可能是多行）
            
        Returns:
            list: 内心独白列表
        """
        results = []
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            for pattern, ptype in self._inner_thought_re:
                match = pattern.match(line)
                if match:
                    content = match.group(1) if match.lastindex else line
                    results.append({
                        "text": line,
                        "content": content,
                        "thought_type": ptype,
                    })
                    break
        
        return results
    
    def process_segment(self, text: str, role_list: List[str] = None) -> NovelTextSegment:
        """
        处理单个文本片段
        
        Args:
            text: 文本内容
            role_list: 已知的角色列表
            
        Returns:
            NovelTextSegment: 处理后的片段
        """
        text_type, speaker = self.detect_text_type(text)
        
        # 识别说话人
        if speaker is None and role_list:
            speaker = self._match_role_from_text(text, role_list)
        
        # 提取特殊标记
        special_markers = []
        if text_type == TextType.INNER_THOUGHT:
            special_markers.append("内心独白")
        elif text_type == TextType.SYSTEM提示:
            special_markers.append("系统提示")
        elif text_type == TextType.POETRY:
            special_markers.append("诗词/古文")
        
        # 提取修炼术语
        cultivation_terms = self.extract_cultivation_terms(text)
        if cultivation_terms:
            special_markers.append("修炼术语")
        
        # 识别情感（简单关键词匹配）
        emotion = self._detect_emotion(text)
        
        return NovelTextSegment(
            text=text,
            text_type=text_type,
            speaker=speaker,
            emotion=emotion,
            genre_tags=self._detect_genre_tags(text),
            special_markers=special_markers,
        )
    
    def _match_role_from_text(self, text: str, role_list: List[str]) -> Optional[str]:
        """从文本中匹配角色"""
        for role in role_list:
            if role in text:
                return role
        return None
    
    def _detect_emotion(self, text: str) -> Optional[str]:
        """检测情感（简单关键词）"""
        emotion_keywords = {
            "高兴": ["开心", "高兴", "喜悦", "兴奋", "快乐"],
            "悲伤": ["悲伤", "伤心", "难过", "痛苦", "哭泣"],
            "愤怒": ["愤怒", "生气", "恼火", "大怒"],
            "惊讶": ["惊讶", "震惊", "意外", "吃惊"],
            "温柔": ["温柔", "柔和", "轻声", "细语"],
            "紧张": ["紧张", "忐忑", "不安", "焦急"],
        }
        
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return emotion
        
        return None
    
    def _detect_genre_tags(self, text: str) -> List[str]:
        """检测小说类型标签"""
        tags = []
        
        # 仙侠/玄幻关键词
        xuanhuan_keywords = ["修炼", "筑基", "金丹", "灵气", "灵根", "仙侠", "玄幻", "功法", "法术", "秘境", "妖兽"]
        if any(kw in text for kw in xuanhuan_keywords):
            tags.append("xuanhuan")
        
        # 都市关键词
        urban_keywords = ["总裁", "老板", "公司", "职场", "都市", "豪门", "都市", "商业"]
        if any(kw in text for kw in urban_keywords):
            tags.append("urban")
        
        # 穿越关键词
        time_travel_keywords = ["穿越", "重生", "回到", "末世", "未来"]
        if any(kw in text for kw in time_travel_keywords):
            tags.append("time_travel")
        
        return tags
    
    def batch_process(self, texts: List[str], role_list: List[str] = None) -> List[NovelTextSegment]:
        """
        批量处理文本片段
        
        Args:
            texts: 文本列表
            role_list: 已知的角色列表
            
        Returns:
            list: 处理后的片段列表
        """
        return [self.process_segment(text, role_list) for text in texts]


# ===========================================
# 便捷函数
# ===========================================

def quick_detect_type(text: str) -> TextType:
    """快速检测文本类型"""
    processor = NovelTextProcessor()
    text_type, _ = processor.detect_text_type(text)
    return text_type


def quick_extract_system_prompts(text: str) -> List[Dict[str, Any]]:
    """快速提取系统提示"""
    processor = NovelTextProcessor()
    return processor.extract_system_prompts(text)


def quick_extract_inner_thoughts(text: str) -> List[Dict[str, Any]]:
    """快速提取内心独白"""
    processor = NovelTextProcessor()
    return processor.extract_inner_thoughts(text)


def quick_extract_cultivation_terms(text: str) -> List[Dict[str, Any]]:
    """快速提取修炼术语"""
    processor = NovelTextProcessor()
    return processor.extract_cultivation_terms(text)
