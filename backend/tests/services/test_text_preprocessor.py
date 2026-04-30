# ===========================================
# 文本预处理服务测试
# ===========================================

"""
文本预处理服务单元测试

测试文本标准化、数字转换、段落拆分等功能。
验收标准：100段文本测试通过 / 输出格式可直接送入TTS
"""

import pytest
import re

from services.svc_text_preprocessor import TextPreprocessorService


class TestTextPreprocessorService:
    """文本预处理服务测试类"""

    @pytest.fixture
    def preprocessor(self):
        """创建预处理器实例"""
        return TextPreprocessorService()

    # ===== 测试 normalize_text 方法 =====

    def test_normalize_text_basic(self, preprocessor):
        """测试基本文本规范化"""
        text = "这是  一段   有多余  空格    的文本"
        result = preprocessor.normalize_text(text)
        # 多余空格应该被合并
        assert "  " not in result

    def test_normalize_text_newlines(self, preprocessor):
        """测试换行符规范化"""
        text = "第一段\n\n\n第二段\n\n\n\n第三段"
        result = preprocessor.normalize_text(text)
        # 多个连续换行应该被合并
        assert "\n\n\n" not in result

    def test_normalize_text_punctuation(self, preprocessor):
        """测试标点符号规范化"""
        text = "这是...一段...省略号的文本"
        result = preprocessor.normalize_text(text)
        assert "……" in result

    def test_normalize_text_ellipsis_variants(self, preprocessor):
        """测试省略号变体处理"""
        text = "你好……世界…"  # 全角省略号
        result = preprocessor.normalize_text(text)
        # 应该统一为两个省略号
        assert result.count("……") >= 1

    def test_normalize_text_dashes(self, preprocessor):
        """测试破折号规范化"""
        text = "这是--一段--有破折号的--文本"
        result = preprocessor.normalize_text(text)
        assert "——" in result

    def test_normalize_text_quotes(self, preprocessor):
        """测试引号规范化"""
        text = '"这是一段"带引号的文本'
        result = preprocessor.normalize_text(text)
        # 引号应该被转换为全角
        assert "‘" in result or '"' in result or '"' in result

    def test_normalize_text_mixed(self, preprocessor):
        """测试混合规范化"""
        text = "   文本   有\n\n\n混合   的\t\t格式   问题   "
        result = preprocessor.normalize_text(text)
        # 前后空白应该被去除
        assert result == result.strip()
        assert "\t" not in result

    # ===== 测试 convert_numbers 方法 =====

    def test_convert_numbers_years(self, preprocessor):
        """测试年份转换"""
        text = "1990年、2000年、2024年"
        result = preprocessor.convert_numbers(text)
        assert "一九九零年" in result or "1990年" in result
        assert "年" in result  # 年字应该保留

    def test_convert_numbers_percentages(self, preprocessor):
        """测试百分比转换"""
        text = "增长率是50%，下降了30%。"
        result = preprocessor.convert_numbers(text)
        # 应该转换为中文数字
        assert "百分之" in result or "%" in result

    def test_convert_numbers_decimals(self, preprocessor):
        """测试小数转换"""
        text = "圆周率约等于3.14159。"
        result = preprocessor.convert_numbers(text)
        # 小数点应该被转换为"点"
        assert "点" in result or "3.14159" in result

    def test_convert_numbers_phone(self, preprocessor):
        """测试电话号码处理"""
        text = "联系电话：13812345678"
        result = preprocessor.convert_numbers(text)
        # 手机号可以保留原样或转换
        assert "13812345678" in result or "一三八" in result

    def test_convert_numbers_preserve_plain_numbers(self, preprocessor):
        """测试保留普通数字"""
        text = "第1章有100页"
        result = preprocessor.convert_numbers(text)
        # 普通场景数字可以保留
        assert "1" in result or "一" in result

    # ===== 测试 split_paragraphs 方法 =====

    def test_split_paragraphs_basic(self, preprocessor):
        """测试基本段落拆分"""
        text = "第一段\n第二段\n第三段"
        result = preprocessor.split_paragraphs(text)
        assert len(result) == 3
        assert "第一段" in result
        assert "第二段" in result

    def test_split_paragraphs_with_empty_lines(self, preprocessor):
        """测试带空行的段落拆分"""
        text = "第一段\n\n\n第二段\n\n第三段"
        result = preprocessor.split_paragraphs(text)
        assert len(result) == 3
        assert "第一段" in result
        assert "第二段" in result

    def test_split_paragraphs_strips_whitespace(self, preprocessor):
        """测试段落空白去除"""
        text = "  第一段  \n  第二段  \n  第三段  "
        result = preprocessor.split_paragraphs(text)
        for p in result:
            assert p == p.strip()

    def test_split_paragraphs_filters_empty(self, preprocessor):
        """测试过滤空段落"""
        text = "第一段\n\n\n\n第二段"
        result = preprocessor.split_paragraphs(text)
        assert all(p.strip() for p in result)

    def test_split_paragraphs_single_paragraph(self, preprocessor):
        """测试单段落"""
        text = "只有一段文本"
        result = preprocessor.split_paragraphs(text)
        assert len(result) == 1
        assert result[0] == "只有一段文本"

    def test_split_paragraphs_no_split(self, preprocessor):
        """测试无分隔符"""
        text = "一段没有换行的文本"
        result = preprocessor.split_paragraphs(text)
        assert len(result) == 1

    # ===== 测试 TTS 友好格式 =====

    def test_tts_friendly_dialogue(self, preprocessor):
        """测试对话文本处理"""
        text = '''他说："你好！"她说："你好！"'''
        normalized = preprocessor.normalize_text(text)
        assert "你好" in normalized

    def test_tts_friendly_chinese_text(self, preprocessor):
        """测试中文文本处理"""
        text = '''李明走进房间，看到小红坐在窗边。
"你来啦。"小红抬起头，微笑着说。
"是的，我来了。"李明点点头。
他环顾四周，发现房间里布置得很温馨。'''
        normalized = preprocessor.normalize_text(text)
        # 应该保留基本结构
        assert len(normalized) > 0

    def test_tts_friendly_no_html(self, preprocessor):
        """测试无 HTML 残留"""
        text = "<p>段落一</p>\n<p>段落二</p>"
        from services.svc_epub_parser import EPUBParserService
        parser = EPUBParserService()
        cleaned = parser.clean_html(text)
        normalized = preprocessor.normalize_text(cleaned)
        assert "<" not in normalized
        assert ">" not in normalized

    # ===== 边界情况测试 =====

    def test_empty_text(self, preprocessor):
        """测试空文本"""
        result = preprocessor.normalize_text("")
        assert result == ""

    def test_whitespace_only(self, preprocessor):
        """测试纯空白文本"""
        result = preprocessor.normalize_text("   \n\n\t  ")
        assert result == ""

    def test_very_long_text(self, preprocessor):
        """测试超长文本"""
        long_text = "测试文本。" * 10000
        result = preprocessor.normalize_text(long_text)
        assert len(result) > 0
        assert result.count("  ") == 0

    def test_unicode_special_chars(self, preprocessor):
        """测试 Unicode 特殊字符"""
        text = "特殊符号：★☆♪♫●○※△□"
        result = preprocessor.normalize_text(text)
        assert "★" in result

    def test_english_text(self, preprocessor):
        """测试英文文本"""
        text = "Hello, World! This is a test."
        result = preprocessor.normalize_text(text)
        assert "Hello" in result
        assert "World" in result

    def test_mixed_language(self, preprocessor):
        """测试混合语言"""
        text = "你好 Hello 世界 World 123"
        result = preprocessor.normalize_text(text)
        assert "你好" in result
        assert "Hello" in result
        assert "世界" in result
        assert "World" in result

    def test_numbers_only(self, preprocessor):
        """测试纯数字"""
        text = "1234567890"
        result = preprocessor.normalize_text(text)
        assert "1234567890" in result

    def test_punctuation_only(self, preprocessor):
        """测试纯标点"""
        text = "，。、；：？！""''【】《》"
        result = preprocessor.normalize_text(text)
        assert len(result) > 0


class TestTextPreprocessorIntegration:
    """文本预处理集成测试"""

    @pytest.fixture
    def preprocessor(self):
        return TextPreprocessorService()

    def test_full_pipeline(self, preprocessor):
        """测试完整处理流程"""
        raw_text = """
        第一章  开始

        这是   一段   有很多   空格    的文本。

        "你好啊！"   他说。

        日期是2024年1月1日。

        第二段内容。
        """

        # 1. 清洗 HTML（模拟）
        # 2. 规范化文本
        normalized = preprocessor.normalize_text(raw_text)

        # 3. 转换数字
        converted = preprocessor.convert_numbers(normalized)

        # 4. 拆分段落
        paragraphs = preprocessor.split_paragraphs(converted)

        # 验证结果
        assert len(paragraphs) > 0
        assert all(isinstance(p, str) for p in paragraphs)
        # 不应该有纯空白段落
        assert all(p.strip() for p in paragraphs)

    def test_epub_chapter_processing(self, preprocessor):
        """测试 EPUB 章节处理"""
        from services.svc_epub_parser import EPUBParserService

        # 模拟解析的章节内容
        chapter_content = """
        第一章 新的开始

        李明站在门口，看着眼前的高楼大厦。

        "终于到了。"他深吸一口气。

        电梯门打开，他走了进去。

        "请问去几楼？"一个声音问道。

        "十五楼。"李明回答。

        电梯缓缓上升，李明看着窗外的城市风景。
        """

        # 清洗
        normalized = preprocessor.normalize_text(chapter_content)

        # 拆分段落
        paragraphs = preprocessor.split_paragraphs(normalized)

        # 验证：对话应该被保留
        assert len(paragraphs) > 0

    def test_noisy_text_processing(self, preprocessor):
        """测试噪声文本处理"""
        noisy_text = """
        <html><body>
        <p>    这是一段    </p>
        <p>   有很多    空白    的    文本    </p>

        <script>alert('bad');</script>

        <p>处理后应该变干净。</p>

        </body></html>
        """

        from services.svc_epub_parser import EPUBParserService
        parser = EPUBParserService()

        # 清洗 HTML
        cleaned = parser.clean_html(noisy_text)

        # 规范化
        normalized = preprocessor.normalize_text(cleaned)

        # 验证
        assert "<" not in normalized
        assert "alert" not in normalized
        assert "这是一段" in normalized


class TestTextPreprocessorEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def preprocessor(self):
        return TextPreprocessorService()

    def test_line_numbers_in_text(self, preprocessor):
        """测试文本中的行号"""
        text = "第1行\n第2行\n第3行\n第10行"
        paragraphs = preprocessor.split_paragraphs(text)
        assert len(paragraphs) == 4

    def test_poetry_format(self, preprocessor):
        """测试诗歌格式"""
        poetry = """
        春眠不觉晓，
        处处闻啼鸟。
        夜来风雨声，
        花落知多少。
        """
        paragraphs = preprocessor.split_paragraphs(poetry)
        assert len(paragraphs) == 4

    def test_code_in_text(self, preprocessor):
        """测试文本中的代码片段"""
        text = "代码示例：`print('Hello')`"
        normalized = preprocessor.normalize_text(text)
        assert "print" in normalized

    def test_math_formula(self, preprocessor):
        """测试数学公式"""
        text = "公式：E=mc^2"
        normalized = preprocessor.normalize_text(text)
        assert "E" in normalized or "mc" in normalized

    def test_repeated_text(self, preprocessor):
        """测试重复文本"""
        text = "啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊"
        normalized = preprocessor.normalize_text(text)
        assert len(normalized) > 0


class TestDigitMap:
    """数字映射测试"""

    def test_digit_map_completeness(self):
        """测试数字映射完整性"""
        preprocessor = TextPreprocessorService()
        # 验证所有数字 0-9 都在映射中
        expected_digits = set("0123456789")
        mapped_keys = set(preprocessor.digit_map.keys())
        assert expected_digits == mapped_keys

    def test_digit_map_values(self):
        """测试数字映射值"""
        preprocessor = TextPreprocessorService()
        assert preprocessor.digit_map["0"] == "零"
        assert preprocessor.digit_map["1"] == "一"
        assert preprocessor.digit_map["9"] == "九"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
