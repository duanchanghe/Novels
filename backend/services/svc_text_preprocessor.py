# ===========================================
# 文本预处理服务
# ===========================================

"""
文本预处理服务

对文本进行标准化处理，使其更适合 TTS 朗读。
支持：
- 文本规范化（空白、标点、引号、破折号）
- 数字转换（年份、百分比、小数、电话号码）
- 段落拆分（智能拆分，保留对话结构）
- TTS 友好格式输出
"""

import re
import logging
from typing import Dict, List, Any, Tuple, Optional


class TextPreprocessorService:
    """
    文本预处理服务

    提供文本标准化功能：
    - 数字转朗读格式
    - 标点规范化
    - 特殊符号处理
    - 对话识别与保留
    """

    # 数字转换映射
    DIGIT_MAP = {
        "0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
        "5": "五", "6": "六", "7": "七", "8": "八", "9": "九",
    }

    # 常用量词
    UNITS = ["十", "百", "千", "万", "亿"]

    # TTS 友好标点映射
    TTS_PUNCTUATION_PAUSE = {
        "。": "。",
        "，": "，",
        "；": "；",
        "：": "：",
        "？": "？",
        "！": "！",
        "……": "……",
        "——": "——",
        ".": "。",
        ",": "，",
        ";": "；",
        ":": "：",
        "?": "？",
        "!": "！",
    }

    def __init__(self):
        self.digit_map = self.DIGIT_MAP
        self.logger = logging.getLogger("audiobook.text_preprocessor")

    def normalize_text(self, text: str) -> str:
        """
        标准化文本

        Args:
            text: 原始文本

        Returns:
            str: 标准化后的文本
        """
        if not text:
            return ""

        # 移除多余空白
        text = self._normalize_whitespace(text)

        # 规范化标点
        text = self._normalize_punctuation(text)

        # 规范化引号
        text = self._normalize_quotes(text)

        # 规范化破折号
        text = self._normalize_dashes(text)

        # 移除控制字符
        text = self._remove_control_chars(text)

        return text.strip()

    def convert_numbers(self, text: str, aggressive: bool = False) -> str:
        """
        将数字转换为朗读格式

        Args:
            text: 包含数字的文本
            aggressive: 是否激进转换（将所有数字转为中文）

        Returns:
            str: 转换后的文本
        """
        if not text:
            return text

        # 年份转换
        text = self._convert_years(text)

        # 电话号码处理
        text = self._convert_phone_numbers(text)

        # 百分比转换
        text = self._convert_percentages(text)

        # 小数转换
        text = self._convert_decimals(text)

        # 房间号、门牌号等转换
        text = self._convert_room_numbers(text)

        # 激进模式：转换其他数字
        if aggressive:
            text = self._convert_remaining_numbers(text)

        return text

    def split_paragraphs(self, text: str, preserve_dialogue: bool = True) -> List[str]:
        """
        拆分段落

        Args:
            text: 文本内容
            preserve_dialogue: 是否保留对话在同一段落

        Returns:
            list: 段落列表
        """
        if not text:
            return []

        # 按换行符拆分
        paragraphs = re.split(r"\n+", text)

        # 过滤空段落
        result = []
        for p in paragraphs:
            stripped = p.strip()
            if stripped:
                if preserve_dialogue:
                    # 合并短对话段落
                    if self._is_short_dialogue(stripped) and result:
                        last = result[-1]
                        if self._is_short_dialogue(last) or self._ends_with_dialogue_quote(last):
                            result[-1] = last + " " + stripped
                            continue
                result.append(stripped)

        return result

    def prepare_for_tts(self, text: str) -> Dict[str, Any]:
        """
        准备 TTS 友好格式的文本

        完整的文本处理流程，返回处理后的文本和元数据

        Args:
            text: 原始文本

        Returns:
            dict: 包含 processed_text 和 metadata 的字典
        """
        if not text:
            return {
                "processed_text": "",
                "metadata": {
                    "original_length": 0,
                    "processed_length": 0,
                    "paragraph_count": 0,
                    "dialogue_count": 0,
                }
            }

        original_length = len(text)

        # 1. 规范化
        normalized = self.normalize_text(text)

        # 2. 数字转换
        converted = self.convert_numbers(normalized)

        # 3. 拆分段落
        paragraphs = self.split_paragraphs(converted, preserve_dialogue=True)

        # 4. 统计信息
        dialogue_count = self._count_dialogues("\n".join(paragraphs))

        return {
            "processed_text": "\n\n".join(paragraphs),
            "metadata": {
                "original_length": original_length,
                "processed_length": len(converted),
                "paragraph_count": len(paragraphs),
                "dialogue_count": dialogue_count,
            }
        }

    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        # 将 Tab 转换为空格
        text = text.replace("\t", " ")
        # 将多个空格合并为一个
        text = re.sub(r"[ \u3000]+", " ", text)
        # 将多个换行合并为两个（段落的分隔）
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 移除行首行尾空格
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(lines)

    def _normalize_punctuation(self, text: str) -> str:
        """规范化标点符号"""
        # 统一省略号
        text = re.sub(r"\.{3,}", "……", text)
        text = re.sub(r"…", "……", text)

        # 统一破折号
        text = re.sub(r"-{2,}", "——", text)
        text = re.sub(r"–{2,}", "——", text)
        text = re.sub(r"—{2,}", "——", text)

        # 半角转全角标点
        punctuation_map = {
            ".": "。",
            ",": "，",
            ";": "；",
            ":": "：",
            "?": "？",
            "!": "！",
            "(": "（",
            ")": "）",
            "[": "【",
            "]": "】",
        }
        for half, full in punctuation_map.items():
            # 避免重复转换
            if half in text:
                text = text.replace(half, full)

        return text

    def _normalize_quotes(self, text: str) -> str:
        """规范化引号"""
        # 英文引号转中文引号
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace("'", "'").replace("'", "'")

        return text

    def _normalize_dashes(self, text: str) -> str:
        """规范化破折号"""
        # 统一为全角破折号
        text = re.sub(r"--+", "——", text)
        text = re.sub(r"–+", "——", text)
        return text

    def _remove_control_chars(self, text: str) -> str:
        """移除控制字符"""
        # 移除常见的控制字符，保留换行
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    def _convert_years(self, text: str) -> str:
        """转换年份"""
        def convert_year(match):
            year = match.group(0)
            # 保留原始年份格式，因为 TTS 通常能正确读出数字年份
            # 只在激进模式下转换
            return year

        return re.sub(r"\d{4}年", convert_year, text)

    def _convert_phone_numbers(self, text: str) -> str:
        """处理电话号码"""
        # 手机号保留原样，因为分段朗读即可
        # 不做转换，避免破坏语义
        return text

    def _convert_percentages(self, text: str) -> str:
        """转换百分比"""
        def convert_percent(match):
            number = match.group(1)
            # 将数字转为中文
            chinese_num = self._number_to_chinese(number)
            return f"百分之{chinese_num}"

        return re.sub(r"(\d+(?:\.\d+)?)\s*%", convert_percent, text)

    def _convert_decimals(self, text: str) -> str:
        """转换小数"""
        def convert_decimal(match):
            number = match.group(0)
            # 将小数转为中文读法
            chinese = self._number_to_chinese_decimal(number)
            return chinese

        return re.sub(r"\d+\.\d+", convert_decimal, text)

    def _convert_room_numbers(self, text: str) -> str:
        """转换房间号、门牌号"""
        # 匹配 3-4 位数字（可能是房间号）
        def convert_room(match):
            number = match.group(0)
            if len(number) == 3 or len(number) == 4:
                chinese = self._number_to_chinese(number)
                return f"{chinese}"
            return number

        return re.sub(r"\d{3,4}室?", convert_room, text)

    def _convert_remaining_numbers(self, text: str) -> str:
        """转换剩余的数字"""
        def convert_number(match):
            number = match.group(0)
            return self._number_to_chinese(number)

        # 转换独立的数字（避免转换年份等）
        return re.sub(r"(?<!\d)\d{1,4}(?!\d)", convert_number, text)

    def _number_to_chinese(self, number: str) -> str:
        """将数字转换为中文"""
        result = ""
        for char in str(number):
            result += self.digit_map.get(char, char)
        return result

    def _number_to_chinese_decimal(self, number: str) -> str:
        """将小数转换为中文读法"""
        result = ""
        for char in number:
            if char == ".":
                result += "点"
            else:
                result += self.digit_map.get(char, char)
        return result

    def _is_short_dialogue(self, text: str) -> bool:
        """判断是否为短对话"""
        # 短对话：引号开头或结尾，长度较短
        if len(text) < 50:
            if text.startswith('"') or text.startswith('"') or text.startswith('"'):
                return True
            if text.endswith('"') or text.endswith('"') or text.endswith('"'):
                return True
            if text.startswith("「") or text.endswith("」"):
                return True
        return False

    def _ends_with_dialogue_quote(self, text: str) -> bool:
        """判断文本是否以对话引号结尾"""
        return text.endswith('"') or text.endswith('"') or text.endswith('"') or text.endswith("」")

    def _count_dialogues(self, text: str) -> int:
        """统计对话数量"""
        # 统计中文引号对
        count = 0
        # 简单计数，实际应更精确
        for quote in ['"', '"', '"', '"', "「", "」"]:
            count += text.count(quote) // 2
        return count

    def extract_chapters_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取章节

        Args:
            text: 文本内容

        Returns:
            list: 章节列表
        """
        chapters = []
        lines = text.split("\n")
        current_chapter = None
        current_content = []

        for line in lines:
            # 检测章节标题
            chapter_match = re.match(r"^(第[一二三四五六七八九十百千万\d]+[章节部篇卷]|第\d+章|第\d+节)", line.strip())
            if chapter_match:
                # 保存上一个章节
                if current_chapter is not None:
                    chapters.append({
                        "title": current_chapter,
                        "content": "\n".join(current_content),
                        "line_count": len(current_content),
                    })

                current_chapter = line.strip()
                current_content = []
            else:
                if current_chapter is not None:
                    current_content.append(line)

        # 保存最后一个章节
        if current_chapter is not None:
            chapters.append({
                "title": current_chapter,
                "content": "\n".join(current_content),
                "line_count": len(current_content),
            })

        return chapters
