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
from core.constants import POLYPHONE_DICT, POLYPHONE_RULES
from core.exceptions import DeepSeekAPIError as DeepSeekApiError


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
# JSON 修复辅助函数
# ===========================================

def _parse_deepseek_response(content: str) -> dict:
    """
    解析 DeepSeek API 响应

    处理多种可能的响应格式：
    1. 纯 JSON
    2. markdown 代码块包裹的 JSON
    3. 嵌套 JSON（API 在 JSON 中返回了文本形式的 JSON）
    4. 格式错误的 JSON

    Args:
        content: API 返回的原始内容

    Returns:
        dict: 解析后的结果
    """
    import re

    # 策略1：尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 策略2：提取 markdown 代码块中的 JSON
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # 策略3：处理嵌套 JSON（API 在 text 字段中返回了 JSON 文本）
    # 查找 "text": "```json\n{..." 模式
    nested_match = re.search(r'"text"\s*:\s*"```json\s*([\s\S]*?)\s*```\s*"', content)
    if nested_match:
        nested_json = nested_match.group(1).strip()
        try:
            return json.loads(nested_json)
        except json.JSONDecodeError:
            pass

    # 策略4：尝试修复格式错误的 JSON
    fixed_result = _fix_malformed_json(json_match.group(1) if json_match else content)
    if fixed_result and (fixed_result.get("sentences") or fixed_result.get("paragraphs")):
        return fixed_result

    # 策略5：最后的尝试 - 查找任何看起来像 JSON 对象的内容
    # 这是一个兜底策略
    all_json_matches = re.findall(r'\{[\s\S]*\}', content)
    for potential_json in all_json_matches:
        try:
            result = json.loads(potential_json)
            if isinstance(result, dict) and ("sentences" in result or "paragraphs" in result or "characters" in result):
                return result
        except json.JSONDecodeError:
            continue

    # 所有策略都失败，返回包含原始内容的响应
    return {"text": content, "sentences": [], "paragraphs": []}


def _fix_malformed_json(json_str: str) -> dict:
    """
    修复格式错误的 JSON（DeepSeek 有时返回未转义引号的 JSON）

    Args:
        json_str: JSON 字符串

    Returns:
        dict: 修复后的结果
    """
    lines = json_str.split('\n')
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            fixed_lines.append(line)
            continue
        text_keys = ['"text"', '"speaker"', '"name"', '"aliases"']
        has_text_key = any(key in line for key in text_keys)
        if has_text_key and ':' in line:
            colon_pos = line.rfind(':')
            if colon_pos != -1:
                value_part = line[colon_pos + 1:].strip()
                if value_part.startswith('"'):
                    remaining = value_part[1:]
                    last_quote_pos = remaining.rfind('"')
                    if last_quote_pos != -1:
                        value_content = remaining[:last_quote_pos]
                        trailing = remaining[last_quote_pos + 1:]
                        if '"' in value_content and '\\"' not in value_content:
                            value_content = value_content.replace('"', '\\"')
                            line = line[:colon_pos + 1] + ' "' + value_content + '"' + trailing
        fixed_lines.append(line)
    fixed_json = '\n'.join(fixed_lines)
    try:
        return json.loads(fixed_json)
    except json.JSONDecodeError:
        return {"paragraphs": []}


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
# 分析结果缓存
# ===========================================

class AnalysisCache:
    """
    分析结果缓存（线程安全 + Redis 二级缓存）

    使用内存缓存 + MD5 哈希避免重复分析相同文本。
    支持 LRU 淘汰策略 + Redis 持久化二级缓存。
    """

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000, redis_url: str = None):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = threading.Lock()
        self._access_order: List[str] = []
        self._redis_url = redis_url
        self._redis_client = None  # 延迟初始化

    def _get_redis(self):
        """延迟初始化 Redis 客户端"""
        if self._redis_client is None and self._redis_url:
            try:
                import redis as _redis
                self._redis_client = _redis.from_url(self._redis_url, decode_responses=True,
                    socket_connect_timeout=2, socket_timeout=2)
            except Exception:
                self._redis_client = False  # 标记为不可用
        return self._redis_client if self._redis_client is not False else None

    def _get_redis_key(self, key: str) -> str:
        return f"deepseek_cache:{key}"

    def _get_key(self, text: str) -> str:
        """计算文本的哈希键"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[Dict[str, Any]]:
        """获取缓存的分析结果（L1: 内存 → L2: Redis）"""
        key = self._get_key(text)

        with self._lock:
            entry = self._cache.get(key)
            if entry:
                if datetime.utcnow() - entry["cached_at"] < timedelta(seconds=self._ttl):
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    logger.debug(f"L1 缓存命中: {key[:8]}...")
                    return entry["result"]
                else:
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)

        # L2: Redis 二级缓存
        redis_client = self._get_redis()
        if redis_client:
            try:
                redis_key = self._get_redis_key(key)
                data = redis_client.get(redis_key)
                if data:
                    result = json.loads(data)
                    # 回填 L1 缓存
                    with self._lock:
                        self._cache[key] = {
                            "result": result,
                            "cached_at": datetime.utcnow(),
                        }
                    logger.debug(f"L2 缓存命中: {key[:8]}...")
                    return result
            except Exception as e:
                logger.debug(f"Redis 缓存读取失败: {e}")

        return None

    def set(self, text: str, result: Dict[str, Any]) -> None:
        """设置缓存（L1 + L2，带 LRU 淘汰）"""
        key = self._get_key(text)

        with self._lock:
            if len(self._cache) >= self._max_size and key not in self._cache:
                oldest_key = self._access_order.pop(0) if self._access_order else None
                if oldest_key:
                    self._cache.pop(oldest_key, None)
                    logger.debug(f"L1 缓存淘汰: {oldest_key[:8]}...")

            self._cache[key] = {
                "result": result,
                "cached_at": datetime.utcnow(),
            }

            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

        # L2: 写入 Redis（异步友好，失败不影响主流程）
        redis_client = self._get_redis()
        if redis_client:
            try:
                redis_key = self._get_redis_key(key)
                redis_client.setex(redis_key, self._ttl, json.dumps(result, ensure_ascii=False))
            except Exception as e:
                logger.debug(f"Redis 缓存写入失败: {e}")

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


# 全局缓存实例（TTL: 24小时, 最大: 5000条, 支持 Redis 二级缓存）
# DeepSeek 分析结果是确定性的（相同输入→相同输出），缓存越久成本越低
_analysis_cache = AnalysisCache(
    ttl_seconds=86400,
    max_size=5000,
    redis_url=settings.REDIS_URL or settings._redis_url if hasattr(settings, '_redis_url') else None,
)


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
    # 综合分析 Prompt（句子级拆分版 - 严格区分对话与旁白）
    # ===========================================
    FULL_ANALYSIS_PROMPT = """你是有声书文本分析专家。请对以下小说文本进行全面分析，**严格区分对话与旁白**。

【核心原则】
1. **句子级拆分**：每个句子独立输出，不要将对话和旁白混在同一段落
2. **说话人必须明确**：
   - 对话内容 → 标注具体角色名（如"张三"、"李四"）
   - 旁白/叙述/描写 → 标注"旁白"
3. **绝对禁止**：将角色对话标注为旁白音色

【已知角色】（如已知）
{role_list}

【分析任务】
1. **按句子拆分**：每个句子独立一个条目
2. **判断句子类型**：
   - `dialogue`：直接引用的对话，必须有说话人
   - `narration`：旁白叙述、心理描写、动作描写
3. **识别说话人**：
   - 对话句子 → 识别说话者（参考已知角色）
   - 旁白句子 → speaker 固定为 "旁白"
4. **情感标注**：仅对话句子需要情感，旁白句子 emotion 为 null
5. **多音字消歧**
6. **识别特殊标记**（古文/诗词/内心独白/系统提示）

【混合段落处理（关键）】

❌ 错误示例（错误地混合在一起）：
```json
{"type": "mixed", "text": "她叹了口气说："算了，不说了。", "speaker": "旁白"}
```

✅ 正确示例（严格拆分）：
```json
[
  {"type": "narration", "text": "她叹了口气说：", "speaker": "旁白"},
  {"type": "dialogue", "text": "算了，不说了。", "speaker": "她", "emotion": "悲伤_中"}
]
```

✅ 更复杂示例（旁白→对话→旁白）：
原文："张三静静地坐在窗边，轻声说道："这里的夜色真美。"他望着远方，眼中满是回忆。"
拆分：
```json
[
  {"type": "narration", "text": "张三静静地坐在窗边，轻声说道：", "speaker": "旁白"},
  {"type": "dialogue", "text": "这里的夜色真美。", "speaker": "张三", "emotion": "平静_medium"},
  {"type": "narration", "text": "他望着远方，眼中满是回忆。", "speaker": "旁白"}
]
```

【角色性格分析方法】
对每个角色，通过以下线索综合推断性格和说话风格：

1. **对白内容特征**：用词习惯、句式特点、口头禅
2. **情感表现**：情绪波动范围、表达方式
3. **人际关系**：对不同对象说话方式是否不同

【重要】
- **每个对话必须标注说话人角色名**，不允许出现无说话人的对话
- **旁白段落 speaker 只能是"旁白"**
- **情感只标注在对话上**

【中文网络小说特色】
- 识别玄幻/都市/仙侠特有格式
- 识别内心独白：（心想）、（暗道）
- 识别系统提示：[系统提示]、[任务发布]

【输出格式】（严格 JSON）
{{
  "sentences": [
    {{
      "sentence_index": 1,
      "text": "完整句子内容",
      "type": "dialogue|narration",
      "speaker": "旁白|角色名",  // dialogue 必须有具体角色名，narration 固定为"旁白"
      "emotion": "情感_强度|null",  // dialogue 需标注，narration 为 null
      "voice_context": "嘶哑|低沉|null",  // 从旁白提取的语音特征（如有）
      "polyphone_fixes": [["字","拼音"]],
      "special_markers": ["古文朗读"]  // 可选
    }}
  ],
  "characters": [
    {{
      "name": "角色名",
      "aliases": ["别名1", "别名2"],
      "gender": "male|female|unknown",
      "role_type": "主角|配角|反派|旁白",
      "dialogue_count": 5,
      "description": "角色外貌、身份、背景介绍",
      "personality": "性格特征（急躁易怒、温婉贤淑、老谋深算等）",
      "speech_style": "说话风格（语速快/慢、用词文雅/粗俗、语气强势/温和）",
      "voice_description": "适合该角色的声音描述（如'低沉磁性男声'、'清脆活泼女声'）",
      "age_group": "child|youth|adult|elderly"
    }}
  ],
  "statistics": {{
    "total_sentences": 10,
    "total_dialogues": 5,
    "total_narrations": 5,
    "total_characters": 3
  }}
}}

待分析文本：
{text}"""

    @staticmethod
    def build_enhanced_role_list(characters_data: list) -> str:
        """
        构建增强角色列表字符串（含别名和其他角色特征），供提示词使用。

        从已分析的章节角色数据中构建，格式如：
        张三（别名：张兄、三哥，性别：男，年龄：adult，性格：急躁易怒，说话风格：语速快、语气强硬）
        李四（别名：四哥，性别：女，年龄：youth，性格：温婉贤淑，说话风格：语速慢、语气温和）

        Args:
            characters_data: 角色 dict 列表，每项含 name、aliases、gender、
                            age_group、description、personality、speech_style 等

        Returns:
            str: 格式化后的角色列表
        """
        if not characters_data:
            return "未知"

        parts = []
        for char in characters_data:
            name = char.get("name", "")
            if not name or name in ("旁白", "narrator", "未识别", "未知"):
                continue

            info_parts = []

            # 别名
            aliases = char.get("aliases") or []
            alias_set = set()
            for a in aliases:
                a = a.strip()
                if a and a != name:
                    alias_set.add(a)
            if alias_set:
                alias_str = "、".join(sorted(alias_set, key=len, reverse=True))
                info_parts.append(f"别名：{alias_str}")

            # 性别
            gender = char.get("gender", "")
            if gender and gender not in ("", "unknown"):
                gender_cn = {"male": "男", "female": "女"}.get(gender, gender)
                info_parts.append(f"性别：{gender_cn}")

            # 年龄段
            age = char.get("age_group", "")
            if age:
                age_cn = {"child": "儿童", "youth": "青年", "adult": "成年", "elderly": "老年"}.get(age, age)
                info_parts.append(f"年龄：{age_cn}")

            # 性格
            personality = char.get("personality", "")
            if personality:
                info_parts.append(f"性格：{personality}")

            # 说话风格
            speech_style = char.get("speech_style", "")
            if speech_style:
                info_parts.append(f"说话：{speech_style}")

            # 声音描述
            voice_desc = char.get("voice_description", "")
            if voice_desc:
                info_parts.append(f"声线：{voice_desc}")

            # 描述
            description = char.get("description", "")
            if description:
                info_parts.append(f"简介：{description}")

            if info_parts:
                parts.append(f"{name}（{'，'.join(info_parts)}）")
            else:
                parts.append(name)

        return "，".join(parts) if parts else "未知"

    @staticmethod
    def _escape_format_braces(text: str) -> str:
        """转义文本中的花括号，避免 str.format() 报 KeyError"""
        if not text:
            return ""
        return text.replace("{", "{{").replace("}", "}}")

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
        role_list=None,
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
                - sentences: 句子分析列表（主要）
                - paragraphs: 段落分析列表（向后兼容）
                - characters: 角色列表
        """
        global _cost_stats

        if not self.api_key:
            raise DeepSeekApiError("DeepSeek API Key 未配置")

        # 边界检查
        if not text or not text.strip():
            return {
                "sentences": [],
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
                result = {"sentences": [], "paragraphs": [], "characters": []}
            if "sentences" not in result:
                # 兼容旧结构：paragraphs → sentences
                result["sentences"] = result.get("paragraphs", [])
            if "paragraphs" not in result:
                result["paragraphs"] = result.get("sentences", [])
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

    async def _full_analysis(self, text: str, role_list=None) -> Dict[str, Any]:
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
            role_str = role_list if isinstance(role_list, str) else (", ".join(role_list) if role_list else "未知")
            safe_text = self._escape_format_braces(text)
            safe_role = self._escape_format_braces(role_str)
            result = await self._call_deepseek(
                self.FULL_ANALYSIS_PROMPT.format(
                    text=safe_text,
                    role_list=safe_role,
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
                known_roles = list(all_characters.keys()) if all_characters else role_list
                role_str = known_roles if isinstance(known_roles, str) else (", ".join(known_roles) if known_roles else "未知")
                safe_chunk = self._escape_format_braces(chunk)
                safe_role = self._escape_format_braces(role_str)
                result = await self._call_deepseek(
                    self.FULL_ANALYSIS_PROMPT.format(
                        text=safe_chunk,
                        role_list=safe_role,
                    )
                )

                for para in result.get("paragraphs", []):
                    para["paragraph_index"] += base_index
                    all_paragraphs.append(para)

                for char in result.get("characters", []):
                    name = char.get("name")
                    if name in all_characters:
                        all_characters[name]["dialogue_count"] += char.get("dialogue_count", 0)
                    else:
                        all_characters[name] = char

                base_index = len(all_paragraphs)
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
            return _parse_deepseek_response(content)

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

    @staticmethod
    def _infer_gender_from_name(name: str) -> str:
        """
        根据中文称呼推断性别（作为 DeepSeek 未返回 gender 时的兜底）

        优先级：男称复合词 > 女称复合词 > 男称单字 > 女称单字
        复合词优先避免"伯爵夫人"含"伯"误判男、"二姐夫"含"姐"误判女。
        """
        if not name:
            return "unknown"

        male_word = ["先生", "少爷", "公子", "老爷", "大爷", "大叔",
                     "大哥", "老弟", "兄弟", "姐夫", "妹夫", "姑爷",
                     "师父", "道长", "师叔", "师伯", "师哥", "师弟", "师祖",
                     "爷爷", "外公", "侄儿", "儿子", "孙子"]
        female_word = ["夫人", "太太", "小姐", "公主", "仙女", "巫女", "女士",
                       "大妈", "大娘", "师太", "师娘", "姥姥", "外婆",
                       "妻子", "娘子", "闺女", "侄女", "甥女", "外甥女", "女儿",
                       "大姐", "二姐", "三姐", "小妹", "妹妹", "姐姐",
                       "奶奶", "婆婆"]
        male_char = ["爷", "哥", "弟", "爹", "爸", "叔", "伯", "兄", "郎", "君", "汉", "甥"]
        female_char = ["妹", "女", "娘", "妈", "嫂", "婶", "姑", "婆", "奶"]

        for w in sorted(male_word, key=len, reverse=True):
            if w in name:
                return "male"
        for w in sorted(female_word, key=len, reverse=True):
            if w in name:
                return "female"
        for c in male_char:
            if c in name:
                return "male"
        for c in female_char:
            if c in name:
                return "female"
        return "unknown"

    @staticmethod
    def _infer_age_group_from_name(name: str) -> str:
        """
        根据中文称呼推断年龄段，辅助匹配声线。

        年龄段: child(儿童) / youth(青少年/青年) / adult(成年/中年) / elderly(老年)
        """
        if not name:
            return ""

        # 老年
        elderly = ["老爷爷", "老太太", "老婆婆", "老大爷", "老大娘",
                   "老伯", "老奶奶", "老人家", "老夫人"]
        # 儿童/少年
        child = ["小朋友", "小宝宝", "小孩子", "小女孩", "小男孩",
                 "小丫头", "小弟弟", "小妹妹", "小屁孩"]
        # 青年
        youth = ["小哥", "小姐姐", "小伙子", "年轻人", "姑娘",
                 "少女", "少年", "少爷", "王子",
                 "丫头", "小弟", "小妹", "小妮", "小生"]
        # 成年/中年
        adult = ["先生", "太太", "夫人", "女士", "大叔", "大姐",
                 "大哥", "大嫂", "嫂子", "老弟",
                 "师父", "师太", "道长", "和尚",
                 "老爷", "君", "小姐", "公主"]

        for w in sorted(elderly, key=len, reverse=True):
            if w in name:
                return "elderly"
        for w in sorted(child, key=len, reverse=True):
            if w in name:
                return "child"
        for w in sorted(youth, key=len, reverse=True):
            if w in name:
                return "youth"
        for w in sorted(adult, key=len, reverse=True):
            if w in name:
                return "adult"

        # 单字推断
        if "老" in name and "小" not in name:
            return "elderly"
        if "小" in name:
            return "youth"
        if "少" in name:
            return "youth"
        if "老" in name:
            return "elderly"
        return ""

    def _merge_role_aliases(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并角色别名

        将同一角色的不同称呼合并为统一名称。
        支持新旧两种结构：
        - 新结构：sentences（句子级）
        - 旧结构：paragraphs（段落级）

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

        # 判断使用哪种结构
        sentences = result.get("sentences", [])
        paragraphs = result.get("paragraphs", [])
        items = sentences if sentences else paragraphs

        # 第二遍：合并句子/段落中的角色
        for item in items:
            speaker = item.get("speaker")
            if speaker and speaker not in ("旁白", "未识别"):
                item["original_speaker"] = speaker
                item["speaker"] = name_mapping.get(speaker, self._normalize_speaker(speaker))

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
                    "gender": "unknown",
                    "age_group": "",
                    "description": "",
                    "personality": "",
                    "speech_style": "",
                    "voice_description": "",
                }

            # 合并统计
            merged_characters[canonical]["dialogue_count"] += char.get("dialogue_count", 0)
            merged_characters[canonical]["aliases"].extend(char.get("aliases", []))
            merged_characters[canonical]["aliases"].append(name)

            # 合并情感
            for emotion in char.get("emotions", []):
                merged_characters[canonical]["emotions"].add(emotion)

            # 合并描述信息（优先非空）
            cc = merged_characters[canonical]
            if char.get("gender") and char["gender"] != "unknown" and cc["gender"] == "unknown":
                cc["gender"] = char["gender"]
            # 从称呼推断性别（兜底）
            if cc["gender"] in ("", "unknown"):
                inferred = self._infer_gender_from_name(canonical)
                if inferred != "unknown":
                    cc["gender"] = inferred
            if char.get("description") and not cc["description"]:
                cc["description"] = char["description"]
            if char.get("personality") and not cc["personality"]:
                cc["personality"] = char["personality"]
            if char.get("speech_style") and not cc["speech_style"]:
                cc["speech_style"] = char["speech_style"]
            if char.get("voice_description") and not cc["voice_description"]:
                cc["voice_description"] = char["voice_description"]
            if char.get("age_group") and not cc["age_group"]:
                cc["age_group"] = char["age_group"]
            if cc["age_group"] in ("", None):
                inferred_age = self._infer_age_group_from_name(canonical)
                if inferred_age:
                    cc["age_group"] = inferred_age

        # 转换为列表并清理
        final_characters = []
        for name, char_data in merged_characters.items():
            char_data["aliases"] = list(set(char_data["aliases"]))
            char_data["emotions"] = list(char_data["emotions"])
            final_characters.append(char_data)

        result["characters"] = final_characters

        # 确保结果中有 sentences 字段（兼容旧代码）
        if sentences and "paragraphs" not in result:
            result["paragraphs"] = sentences

        return result

    @staticmethod
    def _split_mixed_paragraphs(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        后处理：将 mixed 类型段落拆分为 narration + dialogue。

        核心能力：
        1. 识别旁白中的情感/语音特征（如"变得嘶哑而凶狠"）
        2. 将旁白和对话拆分为独立段落
        3. 对话继承旁白的情感强度

        支持新旧两种结构：
        - 新结构：sentences（句子级，已由 AI 严格拆分）
        - 旧结构：paragraphs（段落级，需要后处理拆分）

        例：
          她说："你疯了！"  →  她说： | 你疯了！
          她听了，直直地立在他面前，连嗓音都变了，变得嘶哑而凶狠，她说："见鬼了..."
            → 旁白(嗓音嘶哑而凶狠) + 对话(继承凶狠)
        """
        # 判断使用哪种结构（新结构 sentences 优先级更高）
        sentences = result.get("sentences", [])
        paragraphs = result.get("paragraphs", [])
        items = sentences if sentences else paragraphs

        # 新结构已经是句子级拆分，只需验证并整理
        if sentences:
            new_items = []
            for item in items:
                item_type = item.get("type", "narration")
                text = item.get("text", "")
                speaker = item.get("speaker", "旁白")

                # 验证说话人
                if item_type == "dialogue" and speaker == "旁白":
                    # 对话类型不能是旁白说话人，可能是 AI 漏识别
                    logger.warning(f"对话段落 speaker 为旁白，跳过: {text[:50]}...")
                    continue

                new_items.append(item)

            # 重新编号
            for i, item in enumerate(new_items):
                item["sentence_index"] = i + 1

            result["sentences"] = new_items
            result["paragraphs"] = new_items  # 保持兼容
            return result

        # 旧结构：继续原有逻辑
        new_paragraphs = []

        # 语音特征模式（从旁白中提取）
        voice_pattern = re.compile(
            r'(?:连)?嗓音都变了?[,，]?变得?([^，,。]+)'
        )
        # 情感词（用于推断情感和强度）
        emotion_pattern = re.compile(
            r'(?:嘶哑|凶狠|低沉|颤抖|平静|冷淡|激动|愤怒|温柔|冷酷|悲伤|严肃)'
        )

        for para in paragraphs:
            para_type = para.get("type", "narration")
            text = para.get("text", "")

            if para_type != "mixed" or not text:
                new_paragraphs.append(para)
                continue

            # 检查是否有对话引号
            has_quotes = re.search(r'[""\u201c\u201d]', text)
            if not has_quotes:
                # 无引号 → 降级为旁白
                new_paragraphs.append({**para, "type": "narration", "speaker": "旁白", "emotion": None})
                continue

            # 分析文本结构：找出所有引号内的对话和引号外的旁白
            segments = []
            i = 0
            in_quote = False
            quote_char = None
            current_text = ""

            quote_chars = ['"', '"', '"', '\u201c', '\u201d', '"', '"']
            while i < len(text):
                char = text[i]
                if char in quote_chars:
                    if not in_quote:
                        # 进入引号，保存之前的旁白
                        if current_text.strip():
                            segments.append(("narration", current_text.strip()))
                        in_quote = True
                        quote_char = char
                        current_text = ""
                    elif char == quote_char or char in ['\u201c', '\u201d']:
                        # 退出引号，保存对话
                        if current_text.strip():
                            segments.append(("dialogue", current_text.strip()))
                        in_quote = False
                        quote_char = None
                        current_text = ""
                    else:
                        current_text += char
                else:
                    current_text += char
                i += 1

            # 保存剩余文本
            if current_text.strip():
                segments.append(("narration" if not in_quote else "dialogue", current_text.strip()))

            # 合并连续的同类型段落
            merged_segments = []
            for seg_type, seg_text in segments:
                if merged_segments and merged_segments[-1][0] == seg_type:
                    merged_segments[-1] = (seg_type, merged_segments[-1][1] + " " + seg_text)
                else:
                    merged_segments.append((seg_type, seg_text))

            # 提取语音/情感特征（从所有旁白中）
            voice_context = ""
            detected_emotion = para.get("emotion")

            for seg_type, seg_text in merged_segments:
                if seg_type == "narration":
                    voice_match = voice_pattern.search(seg_text)
                    if voice_match:
                        voice_context = voice_match.group(0)
                        # 从语音描述推断情感
                        emotion_match = emotion_pattern.search(voice_context)
                        if emotion_match and not detected_emotion:
                            emotion_word = emotion_match.group(0)
                            if emotion_word in ("凶狠", "愤怒"):
                                detected_emotion = "愤怒_强"
                            elif emotion_word in ("嘶哑",):
                                detected_emotion = "愤怒_中"
                            elif emotion_word in ("温柔",):
                                detected_emotion = "温柔_弱"
                            elif emotion_word in ("冷淡", "冷漠"):
                                detected_emotion = "冷漠_中"
                            elif emotion_word in ("激动",):
                                detected_emotion = "激动_强"
                            elif emotion_word in ("悲伤",):
                                detected_emotion = "悲伤_中"

            # 为每个段落分配情感
            prev_para = None
            for seg_type, seg_text in merged_segments:
                seg_para = {**para, "paragraph_index": len(new_paragraphs) + 1}

                if seg_type == "narration":
                    seg_para.update({
                        "text": seg_text,
                        "type": "narration",
                        "speaker": "旁白",
                        "emotion": None,
                        "voice_context": voice_context if voice_context else para.get("voice_context"),
                    })
                else:  # dialogue
                    # 推断说话人
                    speaker = para.get("speaker", "")
                    if not speaker or speaker in ("旁白", "未识别", ""):
                        # 从前一个旁白中提取说话人
                        if prev_para and prev_para.get("type") == "narration":
                            speaker_text = prev_para.get("text", "")[-30:]
                            speaker_match = re.search(
                                r'([\u4e00-\u9fff]{1,4})(?:(?:(?:温和|严厉|低声|轻声|大声|感慨|激动|颤抖|嘶哑|慢慢|缓缓)?(?:地)?)'
                                r'(?:说|道|问|喊|叫|吼|听了|看着)',
                                speaker_text
                            )
                            if speaker_match:
                                speaker = speaker_match.group(1)

                    seg_para.update({
                        "text": seg_text,
                        "type": "dialogue",
                        "speaker": speaker if speaker else "旁白",
                        "emotion": detected_emotion if detected_emotion else para.get("emotion", "平静_中"),
                        "voice_context": voice_context,
                    })

                new_paragraphs.append(seg_para)
                prev_para = seg_para

        # 重新编号
        for i, p in enumerate(new_paragraphs):
            p["paragraph_index"] = i + 1
            p["sentence_index"] = i + 1  # 保持兼容

        result["paragraphs"] = new_paragraphs
        return result

    def analyze_chapter(self, text: str, role_list=None) -> Dict[str, Any]:
        """
        同步分析章节（用于 Celery 任务）

        Args:
            text: 章节文本
            role_list: 已知角色列表

        Returns:
            dict: 分析结果
        """
        if not self.api_key:
            raise DeepSeekApiError("DeepSeek API Key 未配置")

        if not text or not text.strip():
            return {"sentences": [], "paragraphs": [], "characters": []}

        # 检查缓存
        if self.use_cache:
            cached_result = _analysis_cache.get(text)
            if cached_result:
                logger.info("使用缓存的分析结果")
                _cost_stats.add(0, 0, is_cache_hit=True)
                return cached_result

        try:
            # 使用同步 API 调用（避免 ForkPoolWorker 中 asyncio 问题）
            result = self._full_analysis_sync(text, role_list)

            if result is None:
                result = {"sentences": [], "paragraphs": [], "characters": []}
            # 兼容新旧结构
            if "sentences" not in result:
                result["sentences"] = result.get("paragraphs", [])
            if "paragraphs" not in result:
                result["paragraphs"] = result.get("sentences", [])
            if "characters" not in result:
                result["characters"] = []

            result = self._merge_role_aliases(result)

            # 后处理：将 mixed 类型的句子拆分为 narration + dialogue
            result = self._split_mixed_paragraphs(result)

            if self.use_cache:
                _analysis_cache.set(text, result)

            return result
        except DeepSeekApiError:
            raise
        except Exception as e:
            logger.error(f"同步分析失败: {e}")
            # 回退到异步方式
            import asyncio
            try:
                return asyncio.run(self.analyze_text(text, role_list))
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self.analyze_text(text, role_list))
                finally:
                    loop.close()

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
                    "gender": "unknown",
                    "age_group": "",
                    "description": "",
                    "personality": "",
                    "speech_style": "",
                    "voice_description": "",
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
            # 从称呼推断性别（兜底）
            if data["gender"] in ("", "unknown"):
                inferred = self._infer_gender_from_name(name)
                if inferred != "unknown":
                    data["gender"] = inferred
            # 从称呼推断年龄（兜底）
            if not data.get("age_group"):
                inferred_age = self._infer_age_group_from_name(name)
                if inferred_age:
                    data["age_group"] = inferred_age
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

        async def _normalize():
            result = await self._call_deepseek(
                self.TEXT_NORMALIZATION_PROMPT.format(text=text)
            )
            if isinstance(result, dict):
                return result.get("text", text)
            return text

        try:
            return asyncio.run(_normalize())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_normalize())
            finally:
                loop.close()

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

    def _call_deepseek_sync(self, prompt: str) -> Dict[str, Any]:
        """
        同步调用 DeepSeek API（用于 ForkPoolWorker 环境）
        
        在 Celery ForkPoolWorker 中，asyncio 事件循环可能无法正常工作，
        使用同步 HTTP 调用作为替代。
        
        Args:
            prompt: 提示词
        
        Returns:
            dict: API 响应内容
        """
        import httpx as httpx_sync
        
        global _cost_stats
        
        try:
            import time as _time
            _t0 = _time.time()
            logger.debug(f"同步 DeepSeek API 调用开始, prompt 长度: {len(prompt)}")
            
            response = httpx_sync.post(
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
                timeout=300.0,
            )
            
            _t1 = _time.time()
            logger.debug(f"同步 DeepSeek API 响应: status={response.status_code}, 耗时={_t1-_t0:.1f}秒")
            
            if response.status_code != 200:
                raise DeepSeekApiError(
                    f"DeepSeek API 调用失败: {response.status_code} - {response.text[:200]}"
                )
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            logger.debug(f"DeepSeek API token 使用: prompt={prompt_tokens}, completion={completion_tokens}, 内容长度={len(content)}")
            
            cost = (prompt_tokens * self.input_price + completion_tokens * self.output_price) / 1000
            _cost_stats.add(total_tokens, cost)
            
            parsed = _parse_deepseek_response(content)
            paras = parsed.get("paragraphs", [])
            logger.debug(f"DeepSeek API 解析结果: {len(paras)} 段落")
            return parsed
            
        except Exception as e:
            _cost_stats.add_error()
            logger.error(f"同步 DeepSeek API 调用异常: {type(e).__name__}: {e}")
            raise DeepSeekApiError(f"DeepSeek API 调用失败: {e}")

    def _full_analysis_sync(self, text: str, role_list=None) -> Dict[str, Any]:
        """
        同步完整分析（用于 Celery ForkPoolWorker 环境）

        Args:
            text: 待分析文本
            role_list: 已知角色列表

        Returns:
            dict: 分析结果
        """
        # 处理长文本
        chunks = self._split_long_text(text)

        if len(chunks) == 1:
            # 短文本，单次调用
            role_str = role_list if isinstance(role_list, str) else (", ".join(role_list) if role_list else "未知")
            safe_text = self._escape_format_braces(text)
            safe_role = self._escape_format_braces(role_str)
            result = self._call_deepseek_sync(
                self.FULL_ANALYSIS_PROMPT.format(
                    text=safe_text,
                    role_list=safe_role,
                )
            )
            _cost_stats.add(tokens=len(text) // 4, cost=len(text) // 4 * self.input_price / 1000)
            return result
        else:
            # 长文本，分段分析后合并
            all_paragraphs = []
            all_characters = {}
            base_index = 0

            for i, chunk in enumerate(chunks):
                logger.info(f"分析文本片段 {i + 1}/{len(chunks)}")
                known_roles = list(all_characters.keys()) if all_characters else role_list
                role_str = known_roles if isinstance(known_roles, str) else (", ".join(known_roles) if known_roles else "未知")
                safe_chunk = self._escape_format_braces(chunk)
                safe_role = self._escape_format_braces(role_str)
                result = self._call_deepseek_sync(
                    self.FULL_ANALYSIS_PROMPT.format(
                        text=safe_chunk,
                        role_list=safe_role,
                    )
                )

                for para in result.get("paragraphs", []):
                    para["paragraph_index"] += base_index
                    all_paragraphs.append(para)

                for char in result.get("characters", []):
                    name = char.get("name")
                    if name in all_characters:
                        all_characters[name]["dialogue_count"] += char.get("dialogue_count", 0)
                    else:
                        all_characters[name] = char

                base_index = len(all_paragraphs)
                _cost_stats.add(tokens=len(chunk) // 4, cost=len(chunk) // 4 * self.input_price / 1000)

            return {
                "paragraphs": all_paragraphs,
                "characters": list(all_characters.values()),
            }
