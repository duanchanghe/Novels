# ===========================================
# DeepSeek 分析服务 - 增强版
# ===========================================

"""
DeepSeek 分析服务 - 增强版

调用 DeepSeek API 进行文本分析，包括：
- 角色识别（支持中文网络小说特色称呼）
- 情感标注（细分强度）
- 多音字消歧（常用字+网络小说特有词）
- 段落拆分（旁白/对话/混合）
- 古文诗词处理
- 网络小说特有格式处理

支持 3 阶段递进分析：
1. 文本标准化：数字/日期/英文转为朗读友好格式
2. 角色情感识别：对话分析 + 说话人归因
3. 音频参数建议：根据角色和情感推荐音色参数

功能特性：
- 角色消歧：自动合并同一角色的不同称呼（扩展中文网络小说特色称呼）
- 混合段落拆分：旁白+对话混合段拆分为独立片段
- 智能缓存：避免重复分析相同文本
- 长文本分片：自动切分适配上下文限制
- 成本追踪：记录 Token 消耗
- 古文处理：识别诗词、词牌、古文引用
- 网络小说特色：识别玄幻/都市/仙侠等类型小说的特有表达
"""

import json
import hashlib
import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import threading

import httpx

from core.config import settings
from core.exceptions import DeepSeekApiError


logger = logging.getLogger("audiobook")


# ===========================================
# 数据结构定义
# ===========================================

@dataclass
class CostStats:
    """成本统计"""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0
    cache_hit_count: int = 0
    error_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, tokens: int, cost: float, is_cache_hit: bool = False):
        with self._lock:
            self.total_tokens += tokens
            self.request_count += 1
            self.total_cost += cost
            if is_cache_hit:
                self.cache_hit_count += 1

    def add_error(self):
        with self._lock:
            self.error_count += 1

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_tokens": self.total_tokens,
                "total_requests": self.request_count,
                "cache_hits": self.cache_hit_count,
                "cache_hit_rate": round(self.cache_hit_count / max(self.request_count, 1) * 100, 2),
                "estimated_cost": round(self.total_cost, 4),
                "error_count": self.error_count,
            }


# 全局成本统计
_cost_stats = CostStats()


# ===========================================
# 角色消歧映射表（扩展版 - 包含中文网络小说特色称呼）
# ===========================================

# 基础称呼映射
BASE_ROLE_ALIAS_MAP = {
    # 经典称呼
    "老爷": "老爷", "老爷子": "老爷", "老爷大人": "老爷",
    "公子": "公子", "少爷": "公子", "公子哥儿": "公子",
    "大人": "大人", "大人爷": "大人", "大人阁下": "大人",
    "师父": "师父", "师傅": "师父", "师尊": "师父", "师父大人": "师父",
    "师兄": "师兄", "师兄兄": "师兄", "大师兄": "师兄",
    "师弟": "师弟", "小师弟": "师弟",
    "姐姐": "姐姐", "小姐姐": "姐姐", "姐儿": "姐姐",
    "妹妹": "妹妹", "小妹妹": "妹妹", "妹儿": "妹妹",
}

# 常见姓氏角色映射
ROLE_ALIAS_MAP = {
    **BASE_ROLE_ALIAS_MAP,
    # 常见男性称呼（姓氏 + 哥/弟/郎等）
    "张三": "张三", "张兄": "张三", "三哥": "张三", "三弟": "张三", "三郎": "张三", "张公子": "张三",
    "李四": "李四", "四哥": "李四", "四弟": "李四", "四郎": "李四", "李公子": "李四",
    "王五": "王五", "五哥": "王五", "五弟": "王五", "五郎": "王五", "王公子": "王五",
    "赵六": "赵六", "六哥": "赵六", "六弟": "赵六", "六郎": "赵六", "赵公子": "赵六",
    "刘七": "刘七", "七哥": "刘七", "七弟": "刘七", "刘公子": "刘七",
    "陈八": "陈八", "八哥": "陈八", "八弟": "陈八", "陈公子": "陈八",
    # 网络小说特有称呼
    "前辈": "前辈", "前輩": "前辈", "师兄": "师兄",
    "道兄": "道兄", "道友好": "道兄", "道兄大人": "道兄",
    "宗主": "宗主", "宗主大人": "宗主",
    "掌门": "掌门", "掌门师兄": "掌门",
    "圣子": "圣子", "圣女": "圣女",
    "帝子": "帝子", "帝君": "帝君",
    "仙尊": "仙尊", "仙帝": "仙帝", "仙王": "仙王",
    "魔尊": "魔尊", "魔帝": "魔帝", "魔王": "魔王",
    "陛下": "陛下", "皇": "陛下", "皇帝": "陛下", "皇上": "陛下",
    "父皇": "父皇", "母后": "母后", "太子": "太子", "公主": "公主",
    "王妃": "王妃", "世子": "世子", "郡主": "郡主",
    "少爷": "少爷", "大小姐": "大小姐", "二小姐": "二小姐",
    "夫人": "夫人", "少奶奶": "少奶奶", "奶奶": "奶奶",
    "相公": "相公", "夫君": "夫君", "郎君": "郎君",
    "媳妇": "媳妇", "娘子": "娘子", "老婆": "老婆",
    "爸": "父亲", "爸": "父亲", "老爹": "父亲", "父亲大人": "父亲",
    "妈": "母亲", "老妈": "母亲", "母亲大人": "母亲",
    "哥": "哥哥", "大哥": "哥哥", "二哥": "哥哥", "三哥": "哥哥",
    "弟": "弟弟", "大弟": "弟弟", "二弟": "弟弟", "小弟": "弟弟",
}


# ===========================================
# 多音字消歧规则库（扩展版）
# ===========================================

# 常见多音字消歧
POLYPHONE_RULES = {
    # 行
    "银行": "háng", "行为": "xíng", "行吗": "xíng", "一行": "xíng", "步行": "xíng",
    "发行": "xíng", "行业": "háng", "行当": "háng", "行家": "háng",
    # 长
    "长短": "cháng", "长度": "cháng", "长短": "cháng", "很长": "cháng", "长短": "cháng",
    "成长": "cháng", "长短": "cháng", "修长": "cháng", "长处": "cháng",
    # 为
    "因为": "wèi", "为了": "wèi", "为何": "wèi", "因为": "wèi",
    "行为": "wéi", "作为": "wéi", "认为": "wéi", "为是": "wéi",
    # 还
    "还有": "hái", "还是": "hái", "还好": "hái", "还是": "hái",
    "归还": "huán", "还书": "huán", "还债": "huán",
    # 只
    "只要": "zhǐ", "只有": "zhǐ", "只是": "zhǐ", "只要": "zhǐ",
    "一只": "zhī", "船只": "zhī", "只身": "zhī",
    # 得
    "得到": "dé", "获得": "dé", "得意": "dé", "心得": "dé",
    "跑得快": "de", "很好": "de", "不得了": "de",
    # 重
    "重要": "zhòng", "重量": "zhòng", "重大": "zhòng", "重点": "zhòng",
    "重复": "chóng", "重新": "chóng", "重庆": "chóng",
    # 空
    "空间": "kōng", "天空": "kōng", "航空": "kōng",
    "空着": "kòng", "空隙": "kòng", "空地": "kòng",
    # 教
    "教育": "jiào", "教师": "jiào", "教学": "jiào",
    "教教": "jiāo", "请教": "qǐng",
    # 差
    "差异": "chā", "差别": "chā", "差距": "chā", "差错": "chā",
    "差不多": "chà", "很差": "hěn chà", "差点": "chà",
    # 数
    "数字": "shù", "数据": "shù", "数学": "shù",
    "数一数": "shǔ", "数不清": "shǔ", "数数": "shǔ",
}


# ===========================================
# 分析结果缓存
# ===========================================

class AnalysisCache:
    """
    分析结果缓存（线程安全）

    使用内存缓存 + MD5 哈希避免重复分析相同文本。
    支持 LRU 淘汰策略，防止内存无限增长。
    """

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = threading.Lock()
        self._access_order: List[str] = []  # 用于 LRU

    def _get_key(self, text: str) -> str:
        """计算文本的哈希键"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[Dict[str, Any]]:
        """获取缓存的分析结果"""
        key = self._get_key(text)
        
        with self._lock:
            entry = self._cache.get(key)

            if entry:
                # 检查是否过期
                if datetime.utcnow() - entry["cached_at"] < timedelta(seconds=self._ttl):
                    # 更新访问顺序（LRU）
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    
                    logger.debug(f"缓存命中: {key[:8]}...")
                    return entry["result"]
                else:
                    # 过期，删除
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)

        return None

    def set(self, text: str, result: Dict[str, Any]) -> None:
        """设置缓存（带 LRU 淘汰）"""
        key = self._get_key(text)
        
        with self._lock:
            # 检查容量，淘汰最久未使用的
            if len(self._cache) >= self._max_size and key not in self._cache:
                oldest_key = self._access_order.pop(0) if self._access_order else None
                if oldest_key:
                    self._cache.pop(oldest_key, None)
                    logger.debug(f"缓存淘汰: {oldest_key[:8]}...")

            self._cache[key] = {
                "result": result,
                "cached_at": datetime.utcnow(),
            }
            
            # 更新访问顺序
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
            }


# 全局缓存实例
_analysis_cache = AnalysisCache(ttl_seconds=3600, max_size=1000)


class DeepSeekAnalyzerService:
    """
    DeepSeek 分析服务 - 增强版

    提供文本智能分析功能，支持多阶段递进分析。
    """

    # ===========================================
    # 阶段一：文本标准化 Prompt（增强版）
    # ===========================================
    TEXT_NORMALIZATION_PROMPT = """你是有声书文本标准化专家。请对以下小说文本进行标准化处理。

【处理规则】

1. **数字转朗读格式**：
   - 年份："2024年" → "二零二四年"（不是"二零二四"年）
   - 日期："3月5日" → "三月五日"，"2024-03-05" → "二零二四年三月五日"
   - 时间："下午2点30分" → 保持自然格式，"14:30" → "下午两点半"
   - 百分比："50%" → "百分之五十"
   - 小数："3.14" → "三点一四"
   - 电话号码：逐位朗读
   - 序号："第1章" → "第一章"
   - 房间号："301室" → "三百零一室"
   - 温度："38.5度" → "三十八点五度"

2. **英文单词处理**：
   - 专有名词（iOS、AI、WiFi、HTML）→ 保持英文发音，用尖括号标注：<AI>
   - 普通英文词 → 判断是否为中文借词，酌情翻译或保留
   - 缩写词（CEO、GDP）→ 逐字母发音或音译

3. **特殊符号处理**：
   - 破折号（——）→ 转换为停顿标记：[停顿0.5秒]
   - 省略号（...）→ 转换为拖音标记：[拖音]
   - 感叹号（！）→ 保持原样
   - 省略号（......）→ [长拖音]

4. **多音字初步标注**（不确定的用括号标注）：
   - "行"在"银行"→"háng"，"行为"→"xíng"
   - "长"在"长短"→"cháng"，"成长"→"cháng"
   - "重"在"重要"→"zhòng"，"重复"→"chóng"

5. **乱码检测**：如有乱码，标记为[乱码片段]

6. **古文/诗词处理**：
   - 识别诗词、词牌、曲牌，添加[古文朗读]标记
   - 识别古文引用，添加[古文引用]标记

7. **网络小说特有表达**：
   - 识别感叹词："卧槽"、"呵呵" → 保持原样
   - 识别特殊格式："[系统提示]" → [系统提示]
   - 识别内心独白：（心想）（暗道）

【输出要求】
- 仅返回处理后的文本
- 不改变原文段落结构
- 保留所有标点符号
- 使用[停顿X秒]和[拖音]标记

待处理文本：
{text}"""

    # ===========================================
    # 阶段二：角色情感识别 Prompt（核心 - 增强版）
    # ===========================================
    ROLE_EMOTION_PROMPT = """你是有声书文本分析专家。请分析以下小说文本，完成角色识别和情感标注。

【已知角色列表】
{role_list}

【分析任务】
1. **段落拆分**：将文本按段落编号
2. **段落类型判断**：
   - `narration`：旁白/描写/心理活动
   - `dialogue`：对话/独白/喊叫
   - `mixed`：旁白+对话混合
3. **说话人识别**：
   - 旁白段落 → speaker: "旁白"
   - 对话段落 → 识别说话人（参考已知角色列表）
   - 同一角色的不同称呼需要合并（如"张兄"、"三哥"都是张三）
4. **情感标注**：根据上下文判断情感和强度
   - 平静_low / 平静_medium / 平静_high
   - 高兴_low / 高兴_medium / 高兴_high
   - 悲伤_low / 悲伤_medium / 悲伤_high
   - 愤怒_low / 愤怒_medium / 愤怒_high
   - 紧张_low / 紧张_medium / 紧张_high
   - 惊讶 / 温柔 / 严肃 / 冷漠 / 嘲讽
5. **多音字消歧**：识别并标注不确定读音的字
6. **混合段落拆分**：如果一段中同时有旁白和对话，拆分为多个子段落

【中文网络小说特色识别】
- 识别玄幻/都市/仙侠小说的特有格式
- 识别内心独白：（心想）、（暗道）
- 识别系统提示：[系统提示]、[任务发布]
- 识别旁白注释：*此处省略若干字*

【输出格式】（严格 JSON 数组）
```json
[
  {{
    "paragraph_index": 1,
    "text": "原文内容",
    "type": "narration|dialogue|mixed",
    "speaker": "旁白|角色名",
    "speaker_alias": "原始称呼（如有）",
    "emotion": "情感_强度",
    "polyphone_fixes": [["字", "拼音"]],
    "pause_hint": "normal|long|short|null",
    "special_markers": ["古文朗读", "内心独白", "系统提示"]  // 可选
  }}
]
```

待分析文本：
{text}"""

    # ===========================================
    # 阶段三：音频参数建议 Prompt
    # ===========================================
    AUDIO_PARAMS_PROMPT = """你是有声书音频工程师。根据以下分析结果，为每个角色推荐合适的音频参数。

【已识别的角色和对话】
{character_dialogues}

【角色类型参考】
- 旁白：沉稳叙述，语速适中
- 男主：年轻男性，语速正常
- 女主：年轻女性，语速稍快
- 老人：语速较慢，声音低沉
- 儿童：语速较快，声音清脆
- 反派：声音阴沉或尖锐
- 仙侠角色：略带空灵感
- 古风角色：语速略慢，庄重

【输出格式】（严格 JSON 数组）
```json
[
  {{
    "speaker": "角色名",
    "recommended_voice_id": "male-qn|female-shaon|male-yun|male-tian|female-xiang",
    "speed": 0.8-1.2,
    "pitch_adjust": -0.3至0.3,
    "emotion_params": {{
      "emotion": "happy|sad|angry|fearful|surprise|gentle|serious|neutral",
      "intensity": 0.5-1.5
    }}
  }}
]
```

角色对话信息：
{text}"""

    # ===========================================
    # 综合分析 Prompt（简化版，单次调用完成）
    # ===========================================
    FULL_ANALYSIS_PROMPT = """你是有声书文本分析专家。请对以下小说文本进行全面分析。

【已知角色】（如已知）
{role_list}

【分析任务】
1. 按段落编号
2. 判断段落类型（旁白/对话/混合）
3. 识别说话人，合并角色别名（如"张兄"、"三哥"→张三）
4. 判断情感及强度（平静/高兴/悲伤/愤怒/紧张/惊讶/温柔/严肃/冷漠/嘲讽）
5. 识别多音字并给出读音
6. 混合段落拆分
7. 识别特殊标记（古文/诗词/内心独白/系统提示）

【中文网络小说特色】
- 网络小说特有称呼：道兄、前辈、宗主、仙尊、魔帝等
- 特殊格式：[系统提示]、（心想）、*注释*
- 玄幻元素：灵根、筑基、金丹、元婴等修炼术语保持原样

【输出格式】（严格 JSON）
{{
  "paragraphs": [
    {{
      "paragraph_index": 1,
      "text": "原文",
      "type": "narration|dialogue|mixed",
      "speaker": "旁白|角色名",
      "emotion": "情感_强度",
      "polyphone_fixes": [["字","拼音"]],
      "special_markers": ["古文朗读"]  // 可选
    }}
  ],
  "characters": [
    {{
      "name": "角色名",
      "aliases": ["别名1", "别名2"],
      "dialogue_count": 5,
      "emotions": ["高兴", "悲伤"],
      "role_type": "男主|女主|反派|配角|旁白"  // 可选
    }}
  ],
  "statistics": {{
    "total_paragraphs": 10,
    "total_dialogues": 5,
    "total_characters": 3,
    "emotion_distribution": {{"高兴": 3, "悲伤": 2}}
  }}
}}

待分析文本：
{text}"""

    def __init__(self, use_cache: bool = True):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        self.max_tokens = settings.DEEPSEEK_MAX_TOKENS
        self.temperature = settings.DEEPSEEK_TEMPERATURE
        self.use_cache = use_cache
        self.max_chunk_chars = 8000  # 单次请求最大字符数
        
        # 成本计算（DeepSeek 价格：¥1/1M tokens 输入，¥2/1M tokens 输出）
        self.input_price = 0.001  # ¥/1K tokens
        self.output_price = 0.002  # ¥/1K tokens

    def _normalize_speaker(self, speaker: str) -> str:
        """
        规范化说话人名称（角色消歧）

        Args:
            speaker: 原始说话人称呼

        Returns:
            str: 规范化后的角色名
        """
        if not speaker or speaker in ("旁白", "未识别", "未知", "null"):
            return speaker

        # 检查别名映射表
        if speaker in ROLE_ALIAS_MAP:
            return ROLE_ALIAS_MAP[speaker]

        # 尝试模糊匹配（前两个字）
        if len(speaker) >= 2:
            prefix = speaker[:2]
            for alias, canonical in ROLE_ALIAS_MAP.items():
                if alias.startswith(prefix) and len(alias) >= 2:
                    return canonical

        # 尝试截取姓氏
        if len(speaker) == 1:
            return speaker
        
        # 检查是否包含常见姓氏
        common_surnames = ["张", "李", "王", "赵", "刘", "陈", "杨", "周", "吴", "郑", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗", "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧", "程", "曹", "袁", "邓", "许", "傅", "沈", "曾", "彭", "吕", "苏", "卢", "蒋", "蔡", "贾", "丁", "魏", "薛", "叶", "阎", "余", "潘", "杜", "戴", "夏", "钟", "汪", "田", "任", "姜", "范", "方", "石", "姚", "谭", "廖", "邹", "熊", "金", "陆", "郝", "孔", "白", "崔", "康", "毛", "邱", "秦", "江", "史", "顾", "侯", "邵", "孟", "龙", "万", "段", "雷", "钱", "汤", "尹", "黎", "易", "常", "武", "乔", "贺", "赖", "龚", "文"]
        if speaker[0] in common_surnames:
            # 返回姓氏作为角色名
            return speaker[0] + "某"

        return speaker

    def _split_long_text(self, text: str) -> List[str]:
        """
        智能拆分长文本（适配上下文限制）

        优先在段落边界拆分，保持语义完整性。

        Args:
            text: 原始文本

        Returns:
            list: 文本片段列表（至少返回一个片段）
        """
        # 边界检查
        if not text or not text.strip():
            return [""]

        text = text.strip()
        if len(text) <= self.max_chunk_chars:
            return [text]

        chunks = []
        paragraphs = text.split("\n")

        current_chunk = ""
        for para in paragraphs:
            # 跳过空段落
            if not para.strip():
                continue

            para_len = len(para)

            # 如果单个段落超过限制，尝试在句子边界拆分
            if para_len > self.max_chunk_chars:
                # 先保存当前chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # 按句子拆分（考虑中文标点）
                sentences = re.split(r'([。！？；\n]+)', para)
                temp_chunk = ""
                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    delimiter = sentences[i + 1] if i + 1 < len(sentences) else ""

                    if len(temp_chunk) + len(sentence) + len(delimiter) > self.max_chunk_chars:
                        if temp_chunk.strip():
                            chunks.append(temp_chunk.strip())
                        temp_chunk = sentence + delimiter
                    else:
                        temp_chunk += sentence + delimiter

                if temp_chunk.strip():
                    current_chunk = temp_chunk

            elif len(current_chunk) + para_len + 1 > self.max_chunk_chars:
                # 当前chunk已满，保存并开始新chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n" + para if current_chunk else para

        # 保存最后一个chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # 确保至少返回一个有效的 chunk
        if not chunks:
            return [text[:self.max_chunk_chars]]

        return chunks

    def _detect_polyphone(self, text: str) -> List[Tuple[str, str, str]]:
        """
        检测多音字

        Args:
            text: 文本内容

        Returns:
            list: [(字, 读音, 上下文), ...]
        """
        results = []
        
        for phrase, pronunciation in POLYPHONE_RULES.items():
            if phrase in text:
                # 找到短语在文本中的位置
                for match in re.finditer(re.escape(phrase), text):
                    start = match.start()
                    context_start = max(0, start - 10)
                    context_end = min(len(text), match.end() + 10)
                    context = text[context_start:context_end]
                    
                    results.append((phrase, pronunciation, context))
        
        return results

    async def analyze_text(
        self,
        text: str,
        role_list: List[str] = None,
        use_full_analysis: bool = True,
    ) -> Dict[str, Any]:
        """
        分析文本（支持缓存和多阶段分析）

        Args:
            text: 待分析文本
            role_list: 已知的角色列表
            use_full_analysis: 是否使用完整分析（默认True，单次调用完成）

        Returns:
            dict: 分析结果，包含：
                - paragraphs: 段落分析列表
                - characters: 角色列表
                - token_usage: Token 使用统计
        """
        global _cost_stats
        
        if not self.api_key:
            raise DeepSeekApiError("DeepSeek API Key 未配置")

        # 边界检查
        if not text or not text.strip():
            return {
                "paragraphs": [],
                "characters": [],
            }

        # 检查缓存
        if self.use_cache:
            cached_result = _analysis_cache.get(text)
            if cached_result:
                logger.info("使用缓存的分析结果")
                _cost_stats.add(0, 0, is_cache_hit=True)
                return cached_result

        try:
            if use_full_analysis:
                # 使用完整分析（单次调用）
                result = await self._full_analysis(text, role_list)
            else:
                # 使用三阶段递进分析
                result = await self._three_stage_analysis(text, role_list)

            # 确保 result 结构完整
            if result is None:
                result = {"paragraphs": [], "characters": []}
            if "paragraphs" not in result:
                result["paragraphs"] = []
            if "characters" not in result:
                result["characters"] = []

            # 合并角色别名
            result = self._merge_role_aliases(result)

            # 缓存结果
            if self.use_cache:
                _analysis_cache.set(text, result)

            return result

        except httpx.TimeoutException:
            _cost_stats.add_error()
            raise DeepSeekApiError("DeepSeek API 请求超时")
        except httpx.HTTPError as e:
            _cost_stats.add_error()
            raise DeepSeekApiError(f"DeepSeek API 请求失败: {e}")
        except json.JSONDecodeError as e:
            _cost_stats.add_error()
            raise DeepSeekApiError(f"DeepSeek 响应 JSON 解析失败: {e}")

    async def _full_analysis(self, text: str, role_list: List[str] = None) -> Dict[str, Any]:
        """
        完整分析（单次 API 调用）

        Args:
            text: 待分析文本
            role_list: 已知角色列表

        Returns:
            dict: 分析结果
        """
        global _cost_stats
        
        # 处理长文本
        chunks = self._split_long_text(text)

        if len(chunks) == 1:
            # 短文本，单次调用
            result = await self._call_deepseek(
                self.FULL_ANALYSIS_PROMPT.format(
                    text=text,
                    role_list=", ".join(role_list) if role_list else "未知",
                )
            )
            
            # 更新成本统计
            _cost_stats.add(
                tokens=len(text) // 4,  # 估算
                cost=len(text) // 4 * self.input_price / 1000
            )
            
            return result
        else:
            # 长文本，分段分析后合并
            all_paragraphs = []
            all_characters = {}
            base_index = 0

            for i, chunk in enumerate(chunks):
                logger.info(f"分析文本片段 {i + 1}/{len(chunks)}")

                # 传递已识别的角色
                known_roles = list(all_characters.keys()) if all_characters else role_list
                result = await self._call_deepseek(
                    self.FULL_ANALYSIS_PROMPT.format(
                        text=chunk,
                        role_list=", ".join(known_roles) if known_roles else "未知",
                    )
                )

                # 调整段落索引
                for para in result.get("paragraphs", []):
                    para["paragraph_index"] += base_index
                    all_paragraphs.append(para)

                # 合并角色
                for char in result.get("characters", []):
                    name = char.get("name")
                    if name in all_characters:
                        all_characters[name]["dialogue_count"] += char.get("dialogue_count", 0)
                    else:
                        all_characters[name] = char

                base_index = len(all_paragraphs)
                
                # 更新成本统计
                _cost_stats.add(
                    tokens=len(chunk) // 4,
                    cost=len(chunk) // 4 * self.input_price / 1000
                )

            return {
                "paragraphs": all_paragraphs,
                "characters": list(all_characters.values()),
            }

    async def _three_stage_analysis(
        self,
        text: str,
        role_list: List[str] = None,
    ) -> Dict[str, Any]:
        """
        三阶段递进分析

        阶段1：文本标准化
        阶段2：角色情感识别
        阶段3：音频参数建议

        Args:
            text: 待分析文本
            role_list: 已知角色列表

        Returns:
            dict: 分析结果
        """
        logger.info("开始三阶段递进分析")

        # 阶段1：文本标准化
        logger.debug("阶段1：文本标准化")
        normalized_text = await self._call_deepseek(
            self.TEXT_NORMALIZATION_PROMPT.format(text=text)
        )
        if isinstance(normalized_text, dict):
            normalized_text = normalized_text.get("text", text)

        # 阶段2：角色情感识别
        logger.debug("阶段2：角色情感识别")
        role_result = await self._call_deepseek(
            self.ROLE_EMOTION_PROMPT.format(
                text=normalized_text if isinstance(normalized_text, str) else text,
                role_list=", ".join(role_list) if role_list else "未知",
            )
        )

        paragraphs = role_result.get("paragraphs", [])

        # 提取对话信息供阶段3使用
        character_dialogues = self._extract_dialogue_info(paragraphs)

        # 阶段3：音频参数建议
        logger.debug("阶段3：音频参数建议")
        if character_dialogues:
            audio_params = await self._call_deepseek(
                self.AUDIO_PARAMS_PROMPT.format(
                    character_dialogues=json.dumps(character_dialogues, ensure_ascii=False),
                    text=json.dumps(paragraphs, ensure_ascii=False),
                )
            )

            # 将音频参数合并到段落结果中
            params_map = {
                p.get("speaker"): p for p in audio_params.get("params", [])
            }
            for para in paragraphs:
                speaker = para.get("speaker")
                if speaker in params_map:
                    para["audio_params"] = params_map[speaker]

        # 提取角色列表
        characters = self._extract_characters(paragraphs)

        return {
            "paragraphs": paragraphs,
            "characters": characters,
            "normalized_text": normalized_text if isinstance(normalized_text, str) else text,
        }

    async def _call_deepseek(self, prompt: str) -> Dict[str, Any]:
        """
        调用 DeepSeek API

        Args:
            prompt: 提示词

        Returns:
            dict: API 响应内容（已解析为 dict）
        """
        global _cost_stats
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                },
            )

            if response.status_code != 200:
                raise DeepSeekApiError(
                    f"DeepSeek API 调用失败: {response.status_code} - {response.text}"
                )

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 更新 Token 使用统计
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            cost = (prompt_tokens * self.input_price + completion_tokens * self.output_price) / 1000
            _cost_stats.add(total_tokens, cost)

            # 尝试解析 JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # 如果不是纯 JSON，可能是纯文本响应
                return {"text": content, "paragraphs": []}

    def _extract_dialogue_info(self, paragraphs: List[Dict]) -> List[Dict]:
        """提取对话信息供音频参数建议使用"""
        dialogues = []
        for para in paragraphs:
            if para.get("type") == "dialogue" and para.get("speaker") not in ("旁白", "未识别"):
                dialogues.append({
                    "speaker": para.get("speaker"),
                    "sample_text": para.get("text", "")[:50],
                    "emotion": para.get("emotion", "平静_medium"),
                })
        return dialogues

    def _merge_role_aliases(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并角色别名

        将同一角色的不同称呼合并为统一名称。

        Args:
            result: 分析结果

        Returns:
            dict: 合并后的结果
        """
        # 构建角色名映射
        name_mapping = {}
        canonical_names: Set[str] = set()

        # 第一遍：确定规范名称
        for char in result.get("characters", []):
            name = char.get("name", "")
            aliases = char.get("aliases", [])

            # 规范化主名称
            canonical = self._normalize_speaker(name)
            name_mapping[name] = canonical
            canonical_names.add(canonical)

            # 规范化别名
            for alias in aliases:
                normalized_alias = self._normalize_speaker(alias)
                name_mapping[alias] = normalized_alias

        # 第二遍：合并段落中的角色
        for para in result.get("paragraphs", []):
            speaker = para.get("speaker")
            if speaker and speaker not in ("旁白", "未识别"):
                para["original_speaker"] = speaker
                para["speaker"] = name_mapping.get(speaker, self._normalize_speaker(speaker))

        # 第三遍：合并角色列表
        merged_characters = {}
        for char in result.get("characters", []):
            name = char.get("name", "")
            canonical = name_mapping.get(name, self._normalize_speaker(name))

            if canonical not in merged_characters:
                merged_characters[canonical] = {
                    "name": canonical,
                    "aliases": [],
                    "dialogue_count": 0,
                    "emotions": set(),
                }

            # 合并统计
            merged_characters[canonical]["dialogue_count"] += char.get("dialogue_count", 0)
            merged_characters[canonical]["aliases"].extend(char.get("aliases", []))
            merged_characters[canonical]["aliases"].append(name)

            # 合并情感
            for emotion in char.get("emotions", []):
                merged_characters[canonical]["emotions"].add(emotion)

        # 转换为列表并清理
        final_characters = []
        for name, char_data in merged_characters.items():
            char_data["aliases"] = list(set(char_data["aliases"]))
            char_data["emotions"] = list(char_data["emotions"])
            final_characters.append(char_data)

        result["characters"] = final_characters
        return result

    def analyze_chapter(self, text: str, role_list: List[str] = None) -> Dict[str, Any]:
        """
        同步分析章节（用于 Celery 任务）

        Args:
            text: 章节文本
            role_list: 已知角色列表

        Returns:
            dict: 分析结果
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.analyze_text(text, role_list))

    def _extract_characters(self, paragraphs: List[Dict]) -> List[Dict[str, Any]]:
        """
        从分析结果中提取角色列表

        Args:
            paragraphs: 段落分析列表

        Returns:
            list: 角色列表
        """
        characters = {}
        speakers = set()

        for item in paragraphs:
            speaker = item.get("speaker")
            if speaker and speaker not in ("旁白", "未识别", "未知"):
                speakers.add(speaker)

        # 构建角色列表
        for speaker in speakers:
            canonical = self._normalize_speaker(speaker)
            if canonical not in characters:
                characters[canonical] = {
                    "name": canonical,
                    "dialogue_count": 0,
                    "emotions": set(),
                }

            characters[canonical]["dialogue_count"] += 1

            # 提取情感
            emotion = item.get("emotion", "")
            if emotion:
                base_emotion = emotion.split("_")[0] if "_" in emotion else emotion
                characters[canonical]["emotions"].add(base_emotion)

        # 转换为列表
        result = []
        for name, data in characters.items():
            data["emotions"] = list(data["emotions"])
            result.append(data)

        return result

    def normalize_text(self, text: str) -> str:
        """
        标准化文本（仅文本标准化，用于预处理阶段）

        Args:
            text: 原始文本

        Returns:
            str: 标准化后的文本
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def _normalize():
            result = await self._call_deepseek(
                self.TEXT_NORMALIZATION_PROMPT.format(text=text)
            )
            if isinstance(result, dict):
                return result.get("text", text)
            return text

        return loop.run_until_complete(_normalize())

    def clear_cache(self) -> None:
        """清空分析缓存"""
        _analysis_cache.clear()
        logger.info("分析缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计

        Returns:
            dict: 缓存统计信息
        """
        return _analysis_cache.get_stats()

    def get_cost_stats(self) -> Dict[str, Any]:
        """
        获取成本统计

        Returns:
            dict: 成本统计信息
        """
        return _cost_stats.to_dict()

    def reset_cost_stats(self) -> None:
        """重置成本统计"""
        global _cost_stats
        _cost_stats = CostStats()
        logger.info("成本统计已重置")
