# ===========================================
# 中文网络小说文本处理器测试
# ===========================================

"""
中文网络小说文本处理器单元测试
"""

import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestNovelTextProcessor:
    """网络小说文本处理器测试"""

    @pytest.fixture
    def processor(self):
        """创建处理器实例"""
        from services.svc_novel_text_processor import NovelTextProcessor
        return NovelTextProcessor()

    def test_detect_narration(self, processor):
        """测试旁白检测"""
        text = "夜幕降临，天空笼罩着一层薄薄的云层。"
        text_type, speaker = processor.detect_text_type(text)
        
        from services.svc_novel_text_processor import TextType
        assert text_type == TextType.NARRATION
        assert speaker is None

    def test_detect_inner_thought_round_bracket(self, processor):
        """测试圆括号内心独白"""
        text = "（心想：这个人到底是谁？）"
        text_type, content = processor.detect_text_type(text)
        
        from services.svc_novel_text_processor import TextType
        assert text_type == TextType.INNER_THOUGHT
        assert "这个人到底是谁" in content

    def test_detect_inner_thought_square_bracket(self, processor):
        """测试方括号内心独白"""
        text = "（暗道：此人心思缜密，不可小觑。）"
        text_type, content = processor.detect_text_type(text)
        
        from services.svc_novel_text_processor import TextType
        assert text_type == TextType.INNER_THOUGHT

    def test_detect_system_prompt(self, processor):
        """测试系统提示"""
        text = "[系统提示：恭喜获得新手大礼包！]"
        text_type, content = processor.detect_text_type(text)
        
        from services.svc_novel_text_processor import TextType
        assert text_type == TextType.SYSTEM提示
        assert "新手大礼包" in content

    def test_detect_quest_prompt(self, processor):
        """测试任务提示"""
        text = "[任务发布：收集10颗灵石]"
        text_type, content = processor.detect_text_type(text)
        
        from services.svc_novel_text_processor import TextType
        assert text_type == TextType.SYSTEM提示

    def test_detect_breakthrough_prompt(self, processor):
        """测试突破提示"""
        text = "[突破成功：筑基初期]"
        text_type, content = processor.detect_text_type(text)
        
        from services.svc_novel_text_processor import TextType
        assert text_type == TextType.SYSTEM提示

    def test_detect_dialogue(self, processor):
        """测试对话检测"""
        text = '"张兄，你这是何意？"'
        text_type, speaker = processor.detect_text_type(text)
        
        from services.svc_novel_text_processor import TextType
        assert text_type == TextType.DIALOGUE

    def test_detect_dialogue_chinese_quote(self, processor):
        """测试中文引号对话"""
        text = "「我来了」，张三说道。"
        text_type, speaker = processor.detect_text_type(text)
        
        from services.svc_novel_text_processor import TextType
        assert text_type == TextType.DIALOGUE

    def test_detect_empty_text(self, processor):
        """测试空文本"""
        from services.svc_novel_text_processor import TextType
        
        text_type, speaker = processor.detect_text_type("")
        assert text_type == TextType.UNKNOWN

        text_type, speaker = processor.detect_text_type("   ")
        assert text_type == TextType.UNKNOWN


class TestCultivationTerms:
    """修炼术语测试"""

    @pytest.fixture
    def processor(self):
        from services.svc_novel_text_processor import NovelTextProcessor
        return NovelTextProcessor()

    def test_extract_realm_terms(self, processor):
        """测试境界术语提取"""
        text = "他修炼到了筑基境界，距离金丹只有一步之遥。"
        terms = processor.extract_cultivation_terms(text)
        
        term_texts = [t["term"] for t in terms]
        assert "筑基" in term_texts
        assert "金丹" in term_texts

    def test_extract_no_cultivation_terms(self, processor):
        """测试无修炼术语"""
        text = "今天天气很好。"
        terms = processor.extract_cultivation_terms(text)
        assert len(terms) == 0

    def test_extract_multiple_terms(self, processor):
        """测试多个术语提取"""
        text = "元婴期的他终于突破了化神境界。"
        terms = processor.extract_cultivation_terms(text)
        
        assert len(terms) >= 2


class TestSystemPrompts:
    """系统提示测试"""

    @pytest.fixture
    def processor(self):
        from services.svc_novel_text_processor import NovelTextProcessor
        return NovelTextProcessor()

    def test_extract_system_prompt(self, processor):
        """测试提取系统提示"""
        text = """
        [系统提示：检测到新任务]
        夜幕降临。
        [任务完成：获得100经验值]
        """
        prompts = processor.extract_system_prompts(text)
        
        assert len(prompts) == 2
        assert prompts[0]["prompt_type"] == "system"
        assert prompts[1]["prompt_type"] == "quest"

    def test_extract_no_system_prompts(self, processor):
        """测试无系统提示"""
        text = "这是一个普通的旁白叙述。"
        prompts = processor.extract_system_prompts(text)
        assert len(prompts) == 0


class TestInnerThoughts:
    """内心独白测试"""

    @pytest.fixture
    def processor(self):
        from services.svc_novel_text_processor import NovelTextProcessor
        return NovelTextProcessor()

    def test_extract_inner_thought(self, processor):
        """测试提取内心独白"""
        text = """
        张三走了进来。
        （心想：这个地方好熟悉。）
        他突然想起了什么。
        """
        thoughts = processor.extract_inner_thoughts(text)
        
        assert len(thoughts) >= 1

    def test_extract_no_inner_thoughts(self, processor):
        """测试无内心独白"""
        text = "这是一个普通的叙述段落。"
        thoughts = processor.extract_inner_thoughts(text)
        assert len(thoughts) == 0


class TestProcessSegment:
    """片段处理测试"""

    @pytest.fixture
    def processor(self):
        from services.svc_novel_text_processor import NovelTextProcessor
        return NovelTextProcessor()

    def test_process_narration_segment(self, processor):
        """测试旁白片段处理"""
        text = "夜幕降临，天空笼罩着一层薄薄的云层。"
        segment = processor.process_segment(text)
        
        from services.svc_novel_text_processor import TextType
        assert segment.text_type == TextType.NARRATION

    def test_process_dialogue_segment(self, processor):
        """测试对话片段处理"""
        text = '"仙尊，这该如何是好？"'
        segment = processor.process_segment(text)
        
        from services.svc_novel_text_processor import TextType
        assert segment.text_type == TextType.DIALOGUE

    def test_process_system_segment(self, processor):
        """测试系统提示片段处理"""
        text = "[系统提示：恭喜获得灵草×10]"
        segment = processor.process_segment(text)
        
        from services.svc_novel_text_processor import TextType
        assert segment.text_type == TextType.SYSTEM提示
        assert "系统提示" in segment.special_markers

    def test_process_with_role_list(self, processor):
        """测试带角色列表处理"""
        text = "张三微微一笑。"
        role_list = ["张三", "李四", "王五"]
        segment = processor.process_segment(text, role_list)
        
        assert segment.speaker == "张三"


class TestBatchProcess:
    """批量处理测试"""

    @pytest.fixture
    def processor(self):
        from services.svc_novel_text_processor import NovelTextProcessor
        return NovelTextProcessor()

    def test_batch_process(self, processor):
        """测试批量处理"""
        texts = [
            "夜幕降临。",
            '"张三，你来了。"',
            "[系统提示：任务开始]",
            "（心想：这一切都结束了。）",
        ]
        
        segments = processor.batch_process(texts)
        
        assert len(segments) == 4


class TestCharacterTitles:
    """角色称呼测试"""

    @pytest.fixture
    def processor(self):
        from services.svc_novel_text_processor import NovelTextProcessor
        return NovelTextProcessor()

    def test_detect_xianxia_titles(self, processor):
        """测试仙侠角色称呼"""
        text = "前辈，此事该如何处理？"
        title = processor.detect_character_title(text)
        
        assert title == "前辈"

    def test_detect_royal_titles(self, processor):
        """测试皇室称呼"""
        text = "陛下万岁万岁万万岁。"
        title = processor.detect_character_title(text)
        
        assert title == "陛下"

    def test_no_title(self, processor):
        """测试无角色称呼"""
        text = "今天天气真好。"
        title = processor.detect_character_title(text)
        
        assert title is None


class TestEmotionDetection:
    """情感检测测试"""

    @pytest.fixture
    def processor(self):
        from services.svc_novel_text_processor import NovelTextProcessor
        return NovelTextProcessor()

    def test_detect_happy_emotion(self, processor):
        """测试高兴情感"""
        text = "他非常开心地笑了起来。"
        emotion = processor._detect_emotion(text)
        
        assert emotion == "高兴"

    def test_detect_sad_emotion(self, processor):
        """测试悲伤情感"""
        text = "她伤心地哭了起来。"
        emotion = processor._detect_emotion(text)
        
        assert emotion == "悲伤"

    def test_detect_angry_emotion(self, processor):
        """测试愤怒情感"""
        text = "他愤怒地吼道。"
        emotion = processor._detect_emotion(text)
        
        assert emotion == "愤怒"

    def test_no_emotion(self, processor):
        """测试无明显情感"""
        text = "这是一个普通的叙述。"
        emotion = processor._detect_emotion(text)
        
        assert emotion is None


class TestGenreTags:
    """类型标签测试"""

    @pytest.fixture
    def processor(self):
        from services.svc_novel_text_processor import NovelTextProcessor
        return NovelTextProcessor()

    def test_detect_xuanhuan_tag(self, processor):
        """测试玄幻标签"""
        text = "他修炼了一门强大的功法。"
        tags = processor._detect_genre_tags(text)
        
        assert "xuanhuan" in tags

    def test_detect_urban_tag(self, processor):
        """测试都市标签"""
        text = "他是一家上市公司的总裁。"
        tags = processor._detect_genre_tags(text)
        
        assert "urban" in tags

    def test_no_tag(self, processor):
        """测试无标签"""
        text = "今天天气很好。"
        tags = processor._detect_genre_tags(text)
        
        assert len(tags) == 0


class TestQuickFunctions:
    """便捷函数测试"""

    def test_quick_detect_type(self):
        """测试快速类型检测"""
        from services.svc_novel_text_processor import quick_detect_type, TextType
        
        text = "[系统提示：任务开始]"
        text_type = quick_detect_type(text)
        
        assert text_type == TextType.SYSTEM提示

    def test_quick_extract_system_prompts(self):
        """测试快速提取系统提示"""
        from services.svc_novel_text_processor import quick_extract_system_prompts
        
        text = "[系统提示：测试]\n[任务发布：123]"
        prompts = quick_extract_system_prompts(text)
        
        assert len(prompts) == 2

    def test_quick_extract_inner_thoughts(self):
        """测试快速提取内心独白"""
        from services.svc_novel_text_processor import quick_extract_inner_thoughts
        
        text = "（心想：这是测试）\n正常的旁白。"
        thoughts = quick_extract_inner_thoughts(text)
        
        assert len(thoughts) == 1

    def test_quick_extract_cultivation_terms(self):
        """测试快速提取修炼术语"""
        from services.svc_novel_text_processor import quick_extract_cultivation_terms
        
        text = "他达到了筑基境界。"
        terms = quick_extract_cultivation_terms(text)
        
        assert len(terms) >= 1
        assert terms[0]["term"] == "筑基"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
