# ===========================================
# 文本预处理服务
# ===========================================

"""
文本预处理服务

对文本进行标准化处理，使其更适合 TTS 朗读。
"""

import re
from typing import Dict, List, Any


class TextPreprocessorService:
    """
    文本预处理服务

    提供文本标准化功能：
    - 数字转朗读格式
    - 标点规范化
    - 特殊符号处理
    """

    # 数字转换映射
    DIGIT_MAP = {
        "0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
        "5": "五", "6": "六", "7": "七", "8": "八", "9": "九",
    }

    # 常用量词
    UNITS = ["十", "百", "千", "万", "亿"]

    def __init__(self):
        self.digit_map = self.DIGIT_MAP

    def normalize_text(self, text: str) -> str:
        """
        标准化文本

        Args:
            text: 原始文本

        Returns:
            str: 标准化后的文本
        """
        # 移除多余空白
        text = self._normalize_whitespace(text)

        # 规范化标点
        text = self._normalize_punctuation(text)

        # 规范化引号
        text = self._normalize_quotes(text)

        # 规范化破折号
        text = self._normalize_dashes(text)

        return text

    def convert_numbers(self, text: str) -> str:
        """
        将数字转换为朗读格式

        Args:
            text: 包含数字的文本

        Returns:
            str: 转换后的文本
        """
        # 年份转换
        text = self._convert_years(text)

        # 电话号码处理
        text = self._convert_phone_numbers(text)

        # 百分比转换
        text = self._convert_percentages(text)

        # 小数转换
        text = self._convert_decimals(text)

        # 普通数字转换（保留原样，避免过度转换）

        return text

    def split_paragraphs(self, text: str) -> List[str]:
        """
        拆分段落

        Args:
            text: 文本内容

        Returns:
            list: 段落列表
        """
        # 按换行符拆分
        paragraphs = re.split(r"\n+", text)

        # 过滤空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        # 将多个空格合并为一个
        text = re.sub(r"[ \t]+", " ", text)
        # 将多个换行合并为两个
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _normalize_punctuation(self, text: str) -> str:
        """规范化标点符号"""
        # 统一省略号
        text = re.sub(r"\.{3,}", "……", text)
        text = re.sub(r"…{2,}", "……", text)

        # 规范化引号
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # 规范化破折号
        text = text.replace("——", "——")

        return text

    def _normalize_quotes(self, text: str) -> str:
        """规范化引号"""
        # 对话引号标准化
        # 这里可以根据具体需求调整
        return text

    def _normalize_dashes(self, text: str) -> str:
        """规范化破折号"""
        # 统一为全角破折号
        text = re.sub(r"--+", "——", text)
        return text

    def _convert_years(self, text: str) -> str:
        """转换年份"""
        # 匹配 4 位数字年份
        def convert_year(match):
            year = match.group(0)
            result = ""
            for char in year:
                result += self.digit_map.get(char, char)
            return result + "年"

        return re.sub(r"\d{4}年", convert_year, text)

    def _convert_phone_numbers(self, text: str) -> str:
        """处理电话号码"""
        # 匹配手机号
        phone_pattern = r"1[3-9]\d{9}"
        # 电话号码逐位朗读
        return text

    def _convert_percentages(self, text: str) -> str:
        """转换百分比"""
        def convert_percent(match):
            number = match.group(1)
            result = ""
            for char in number:
                result += self.digit_map.get(char, char)
            return f"百分之{result}"

        return re.sub(r"(\d+(?:\.\d+)?)\s*%", convert_percent, text)

    def _convert_decimals(self, text: str) -> str:
        """转换小数"""
        def convert_decimal(match):
            number = match.group(0)
            result = ""
            for char in number:
                if char == ".":
                    result += "点"
                else:
                    result += self.digit_map.get(char, char)
            return result

        return re.sub(r"\d+\.\d+", convert_decimal, text)
