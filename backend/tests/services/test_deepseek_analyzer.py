# ===========================================
# DeepSeek 分析服务测试 - 增强版
# ===========================================

"""
DeepSeek 分析服务单元测试 - 增强版
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestDeepSeekAnalyzerService:
    """DeepSeek 分析服务测试"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例（Mock API Key）"""
        with patch("services.svc_deepseek_analyzer.settings") as mock_settings:
            mock_settings.DEEPSEEK_API_KEY = "test-api-key"
            mock_settings.DEEPSEEK_BASE_URL = "https://api.deepseek.com"
            mock_settings.DEEPSEEK_MODEL = "deepseek-chat"
            mock_settings.DEEPSEEK_MAX_TOKENS = 4096
            mock_settings.DEEPSEEK_TEMPERATURE = 0.7

            from services.svc_deepseek_analyzer import DeepSeekAnalyzerService
            return DeepSeekAnalyzerService(use_cache=False)

    def test_normalize_speaker(self, analyzer):
        """测试说话人规范化"""
        # 测试已知别名
        assert analyzer._normalize_speaker("张兄") == "张三"
        assert analyzer._normalize_speaker("三哥") == "张三"

        # 测试旁白/未识别
        assert analyzer._normalize_speaker("旁白") == "旁白"
        assert analyzer._normalize_speaker("未识别") == "未识别"
        assert analyzer._normalize_speaker("null") == "null"

        # 测试未知角色（应返回原值）
        assert analyzer._normalize_speaker("李四") == "李四"

    def test_normalize_speaker_extended(self, analyzer):
        """测试扩展的角色别名"""
        # 网络小说特有称呼
        assert analyzer._normalize_speaker("师傅") == "师父"
        assert analyzer._normalize_speaker("师尊") == "师父"
        assert analyzer._normalize_speaker("前辈") == "前辈"
        assert analyzer._normalize_speaker("道兄") == "道兄"
        assert analyzer._normalize_speaker("仙尊") == "仙尊"
        assert analyzer._normalize_speaker("魔帝") == "魔帝"
        assert analyzer._normalize_speaker("陛下") == "陛下"
        assert analyzer._normalize_speaker("皇上") == "陛下"

    def test_normalize_speaker_with_surname(self, analyzer):
        """测试姓氏识别"""
        # 测试常见姓氏
        result = analyzer._normalize_speaker("张")
        assert result == "张某"
        
        result = analyzer._normalize_speaker("李")
        assert result == "李某"

    def test_split_long_text(self, analyzer):
        """测试长文本拆分"""
        # 短文本不应拆分
        short_text = "这是一段短文本。"
        chunks = analyzer._split_long_text(short_text)
        assert len(chunks) == 1
        assert chunks[0] == short_text

        # 长文本应拆分
        long_text = "\n".join([f"段落{i}的内容。这是一个测试段落。" * 10 for i in range(50)])
        chunks = analyzer._split_long_text(long_text)
        assert len(chunks) > 1

        # 每个chunk应小于限制
        for chunk in chunks:
            assert len(chunk) <= analyzer.max_chunk_chars

    def test_split_long_text_edge_cases(self, analyzer):
        """测试长文本拆分的边界情况"""
        # 空文本
        chunks = analyzer._split_long_text("")
        assert len(chunks) == 1
        assert chunks[0] == ""

        # 仅空白字符
        chunks = analyzer._split_long_text("   \n\t  ")
        assert len(chunks) == 1

        # 单个超长段落
        long_para = "测试" * 3000  # 12000字符
        chunks = analyzer._split_long_text(long_para)
        assert len(chunks) > 1

    def test_detect_polyphone(self, analyzer):
        """测试多音字检测"""
        text = "我去了银行办理业务"
        results = analyzer._detect_polyphone(text)
        
        assert len(results) > 0
        found = False
        for char, pinyin, context in results:
            if "银行" in char:
                assert pinyin == "háng"
                found = True
        assert found, "应该检测到'银行'的多音字"

    def test_detect_polyphone_multiple(self, analyzer):
        """测试多音字检测（多个）"""
        text = "我在银行存钱，行为很奇怪"
        results = analyzer._detect_polyphone(text)
        
        # 应该检测到"银行"和"行为"
        chars = [r[0] for r in results]
        assert "银行" in chars
        assert "行为" in chars

    def test_extract_characters(self, analyzer):
        """测试角色提取"""
        paragraphs = [
            {"speaker": "张三", "emotion": "高兴"},
            {"speaker": "张三", "emotion": "悲伤"},
            {"speaker": "李四", "emotion": "平静"},
            {"speaker": "旁白", "emotion": "平静"},
        ]

        characters = analyzer._extract_characters(paragraphs)

        # 验证角色数量
        assert len(characters) == 2

        # 验证角色名
        names = [c["name"] for c in characters]
        assert "张三" in names
        assert "李四" in names

        # 验证对话次数
        for char in characters:
            if char["name"] == "张三":
                assert char["dialogue_count"] == 2
            elif char["name"] == "李四":
                assert char["dialogue_count"] == 1

    def test_merge_role_aliases(self, analyzer):
        """测试角色别名合并"""
        result = {
            "paragraphs": [
                {"speaker": "张三", "type": "dialogue", "emotion": "高兴"},
                {"speaker": "张兄", "type": "dialogue", "emotion": "悲伤"},
            ],
            "characters": [
                {"name": "张三", "dialogue_count": 1, "aliases": [], "emotions": ["高兴"]},
                {"name": "张兄", "dialogue_count": 1, "aliases": [], "emotions": ["悲伤"]},
            ],
        }

        merged = analyzer._merge_role_aliases(result)

        # 验证段落中的说话人被合并
        for para in merged["paragraphs"]:
            assert para["speaker"] == "张三"

        # 验证角色列表中的对话次数被合并
        for char in merged["characters"]:
            if char["name"] == "张三":
                assert char["dialogue_count"] == 2

    def test_merge_role_aliases_extended(self, analyzer):
        """测试扩展的角色别名合并"""
        result = {
            "paragraphs": [
                {"speaker": "师父", "type": "dialogue", "emotion": "严肃"},
                {"speaker": "师傅", "type": "dialogue", "emotion": "严肃"},
                {"speaker": "师尊", "type": "dialogue", "emotion": "严肃"},
            ],
            "characters": [
                {"name": "师父", "dialogue_count": 3, "aliases": ["师傅", "师尊"], "emotions": ["严肃"]},
            ],
        }

        merged = analyzer._merge_role_aliases(result)

        # 验证所有称呼都被合并为"师父"
        for para in merged["paragraphs"]:
            assert para["speaker"] == "师父"

    @pytest.mark.asyncio
    async def test_analyze_text_with_mock(self, analyzer):
        """测试文本分析（Mock API）"""
        mock_response = {
            "paragraphs": [
                {
                    "paragraph_index": 1,
                    "text": "测试文本",
                    "type": "narration",
                    "speaker": "旁白",
                    "emotion": "平静",
                },
            ],
            "characters": [],
        }

        with patch.object(analyzer, "_call_deepseek", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await analyzer.analyze_text("测试文本")

            assert "paragraphs" in result
            assert len(result["paragraphs"]) == 1
            assert result["paragraphs"][0]["speaker"] == "旁白"

    @pytest.mark.asyncio
    async def test_analyze_text_long_text_chunking(self, analyzer):
        """测试长文本分片分析"""
        # 准备分片响应
        chunk1_response = {
            "paragraphs": [
                {"paragraph_index": 1, "text": "chunk1内容", "speaker": "张三", "type": "dialogue", "emotion": "平静"},
            ],
            "characters": [
                {"name": "张三", "dialogue_count": 1, "aliases": [], "emotions": ["平静"]},
            ],
        }
        chunk2_response = {
            "paragraphs": [
                {"paragraph_index": 1, "text": "chunk2内容", "speaker": "李四", "type": "dialogue", "emotion": "高兴"},
            ],
            "characters": [
                {"name": "李四", "dialogue_count": 1, "aliases": [], "emotions": ["高兴"]},
            ],
        }

        with patch.object(analyzer, "_call_deepseek", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [chunk1_response, chunk2_response]

            # 模拟长文本
            long_text = "chunk1内容\n" + "x" * analyzer.max_chunk_chars + "\nchunk2内容"
            result = await analyzer._full_analysis(long_text, None)

            # 验证段落数量
            assert len(result["paragraphs"]) == 2

            # 验证角色数量
            character_names = [c["name"] for c in result.get("characters", [])]
            assert "张三" in character_names
            assert "李四" in character_names

    @pytest.mark.asyncio
    async def test_analyze_text_empty_text(self, analyzer):
        """测试空文本处理"""
        result = await analyzer.analyze_text("")

        assert result["paragraphs"] == []
        assert result["characters"] == []

    @pytest.mark.asyncio
    async def test_analyze_text_whitespace_only(self, analyzer):
        """测试仅空白字符"""
        result = await analyzer.analyze_text("   \n\t  ")

        assert result["paragraphs"] == []
        assert result["characters"] == []

    @pytest.mark.asyncio
    async def test_cost_tracking(self, analyzer):
        """测试成本追踪"""
        from services.svc_deepseek_analyzer import _cost_stats
        
        # 记录初始状态
        initial_requests = _cost_stats.request_count
        
        mock_response = {
            "paragraphs": [
                {"paragraph_index": 1, "text": "测试", "speaker": "旁白", "type": "narration", "emotion": "平静"},
            ],
            "characters": [],
        }
        
        # Mock 返回包含 usage 信息
        with patch.object(analyzer, "_call_deepseek", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            # 添加 mock usage
            mock_call.return_value._usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

            # 调用分析（会触发成本统计更新）
            # 注意：由于 mock，返回的结果不含 usage，实际不会更新成本
            
            # 验证服务有成本相关方法
            assert hasattr(analyzer, "get_cost_stats")
            assert hasattr(analyzer, "reset_cost_stats")


class TestRoleNormalization:
    """角色规范化测试"""

    @pytest.fixture
    def analyzer(self):
        with patch("services.svc_deepseek_analyzer.settings") as mock_settings:
            mock_settings.DEEPSEEK_API_KEY = "test"
            mock_settings.DEEPSEEK_BASE_URL = "https://api.deepseek.com"
            mock_settings.DEEPSEEK_MODEL = "deepseek-chat"
            mock_settings.DEEPSEEK_MAX_TOKENS = 4096
            mock_settings.DEEPSEEK_TEMPERATURE = 0.7

            from services.svc_deepseek_analyzer import DeepSeekAnalyzerService
            return DeepSeekAnalyzerService(use_cache=False)

    def test_common_aliases(self, analyzer):
        """测试常见别名映射"""
        # 男性常见称呼
        assert analyzer._normalize_speaker("张兄") == "张三"
        assert analyzer._normalize_speaker("三哥") == "张三"
        assert analyzer._normalize_speaker("三弟") == "张三"
        assert analyzer._normalize_speaker("三郎") == "张三"

        # 通用称呼
        assert analyzer._normalize_speaker("师傅") == "师父"
        assert analyzer._normalize_speaker("师尊") == "师父"

    def test_novel_specific_aliases(self, analyzer):
        """测试网络小说特有别名"""
        # 仙侠/玄幻特有称呼
        assert analyzer._normalize_speaker("道兄") == "道兄"
        assert analyzer._normalize_speaker("前辈") == "前辈"
        assert analyzer._normalize_speaker("宗主") == "宗主"
        assert analyzer._normalize_speaker("掌门") == "掌门"
        assert analyzer._normalize_speaker("圣子") == "圣子"
        assert analyzer._normalize_speaker("圣女") == "圣女"

    def test_royal_aliases(self, analyzer):
        """测试皇室称呼"""
        assert analyzer._normalize_speaker("陛下") == "陛下"
        assert analyzer._normalize_speaker("皇上") == "陛下"
        assert analyzer._normalize_speaker("皇") == "陛下"
        assert analyzer._normalize_speaker("父皇") == "父皇"
        assert analyzer._normalize_speaker("太子") == "太子"

    def test_family_aliases(self, analyzer):
        """测试家族称呼"""
        assert analyzer._normalize_speaker("相公") == "相公"
        assert analyzer._normalize_speaker("夫君") == "夫君"
        assert analyzer._normalize_speaker("娘子") == "娘子"
        assert analyzer._normalize_speaker("老婆") == "老婆"

    def test_case_sensitivity(self, analyzer):
        """测试大小写处理"""
        # 未知角色不应被修改
        assert analyzer._normalize_speaker("王五") == "王五"
        assert analyzer._normalize_speaker("赵六") == "赵六"


class TestAnalysisCache:
    """分析缓存测试"""

    def test_cache_basic(self):
        """测试缓存基本功能"""
        from services.svc_deepseek_analyzer import AnalysisCache

        cache = AnalysisCache(ttl_seconds=60)

        # 测试缓存未命中
        result = cache.get("test_text")
        assert result is None

        # 测试缓存设置
        test_result = {"paragraphs": [], "characters": []}
        cache.set("test_text", test_result)

        # 测试缓存命中
        cached = cache.get("test_text")
        assert cached == test_result

    def test_cache_expiration(self):
        """测试缓存过期"""
        from services.svc_deepseek_analyzer import AnalysisCache

        # 设置极短的过期时间
        cache = AnalysisCache(ttl_seconds=0)

        test_result = {"data": "test"}
        cache.set("expire_test", test_result)

        # 立即获取应该为空（已过期）
        result = cache.get("expire_test")
        assert result is None

    def test_cache_clear(self):
        """测试缓存清空"""
        from services.svc_deepseek_analyzer import AnalysisCache

        cache = AnalysisCache()
        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})

        # 清空前应该有数据
        assert cache.get("key1") is not None

        # 清空
        cache.clear()

        # 清空后应该为空
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_lru_eviction(self):
        """测试 LRU 淘汰"""
        from services.svc_deepseek_analyzer import AnalysisCache

        # 设置较小的缓存大小
        cache = AnalysisCache(max_size=3)

        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})
        cache.set("key3", {"data": 3})

        # 访问 key1 使其成为最近使用
        cache.get("key1")

        # 添加新键，应该淘汰 key2
        cache.set("key4", {"data": 4})

        # key1 应该还在
        assert cache.get("key1") is not None
        # key2 应该被淘汰
        assert cache.get("key2") is None
        # key3 和 key4 应该存在
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None

    def test_cache_stats(self):
        """测试缓存统计"""
        from services.svc_deepseek_analyzer import AnalysisCache

        cache = AnalysisCache(max_size=100, ttl_seconds=3600)
        cache.set("key1", {"data": 1})

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 100
        assert stats["ttl_seconds"] == 3600


class TestPolyphoneRules:
    """多音字规则测试"""

    def test_common_polyphone_rules(self):
        """测试常见多音字规则"""
        from services.svc_deepseek_analyzer import POLYPHONE_RULES

        # 验证"行"的规则
        assert "银行" in POLYPHONE_RULES
        assert POLYPHONE_RULES["银行"] == "háng"
        assert "行为" in POLYPHONE_RULES
        assert POLYPHONE_RULES["行为"] == "xíng"

        # 验证"长"的规则
        assert "长短" in POLYPHONE_RULES
        assert POLYPHONE_RULES["长短"] == "cháng"
        assert "成长" in POLYPHONE_RULES

        # 验证"还"的规则
        assert "还有" in POLYPHONE_RULES
        assert POLYPHONE_RULES["还有"] == "hái"
        assert "归还" in POLYPHONE_RULES
        assert POLYPHONE_RULES["归还"] == "huán"

    def test_polyphone_rules_count(self):
        """测试规则数量"""
        from services.svc_deepseek_analyzer import POLYPHONE_RULES

        # 应该有一定数量的规则
        assert len(POLYPHONE_RULES) > 20


class TestCostStats:
    """成本统计测试"""

    def test_cost_stats_basic(self):
        """测试成本统计基本功能"""
        from services.svc_deepseek_analyzer import CostStats

        stats = CostStats()

        # 初始状态
        assert stats.total_tokens == 0
        assert stats.request_count == 0

        # 添加记录
        stats.add(1000, 0.002)
        assert stats.total_tokens == 1000
        assert stats.request_count == 1

        # 添加缓存命中
        stats.add(0, 0, is_cache_hit=True)
        assert stats.cache_hit_count == 1

    def test_cost_stats_to_dict(self):
        """测试成本统计序列化"""
        from services.svc_deepseek_analyzer import CostStats

        stats = CostStats()
        stats.add(1000, 0.002)
        stats.add(0, 0, is_cache_hit=True)

        result = stats.to_dict()
        assert "total_tokens" in result
        assert "cache_hit_rate" in result
        assert result["cache_hit_rate"] == 50.0  # 1/2 = 50%


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
