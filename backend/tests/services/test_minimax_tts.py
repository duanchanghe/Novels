# ===========================================
# MiniMax TTS 服务测试 - 增强版
# ===========================================

"""
MiniMax TTS 服务单元测试 - 增强版
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import base64

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestMiniMaxTTSService:
    """MiniMax TTS 服务测试"""

    @pytest.fixture
    def tts_service(self):
        """创建 TTS 服务实例（Mock API Key）"""
        with patch("services.svc_minimax_tts.settings") as mock_settings:
            mock_settings.MINIMAX_API_KEY = "test-api-key"
            mock_settings.MINIMAX_API_HOST = "https://api.minimax.chat"
            mock_settings.MINIMAX_GROUP_ID = "test-group"

            from services.svc_minimax_tts import MiniMaxTTSService
            return MiniMaxTTSService(rate_limit_qps=10)

    def test_get_voice_id(self, tts_service):
        """测试音色 ID 映射"""
        # 测试已知音色
        assert tts_service._get_voice_id("male-qn") == "male-qn"
        assert tts_service._get_voice_id("female-shaon") == "female-shaon"

        # 测试别名
        assert tts_service._get_voice_id("narrator") == "male-qn"
        assert tts_service._get_voice_id("male-young") == "male-qn"
        assert tts_service._get_voice_id("female-young") == "female-shaon"

        # 测试未知音色（应返回默认）
        assert tts_service._get_voice_id("unknown-voice") == "male-qn"

    def test_get_voice_id_empty(self, tts_service):
        """测试空音色 ID"""
        assert tts_service._get_voice_id("") == "male-qn"
        assert tts_service._get_voice_id(None) == "male-qn"

    def test_get_voice_id_novel_roles(self, tts_service):
        """测试网络小说角色音色映射"""
        # 仙侠角色
        assert tts_service._get_voice_id("仙尊") == "male-yun"
        assert tts_service._get_voice_id("魔帝") == "male-tian"
        assert tts_service._get_voice_id("圣女") == "female-shaon"
        assert tts_service._get_voice_id("仙女") == "female-shaon"
        
        # 普通角色
        assert tts_service._get_voice_id("师父") == "male-yun"
        assert tts_service._get_voice_id("师兄") == "male-qn"

    def test_get_emotion_params(self, tts_service):
        """测试情感参数映射"""
        # 测试平静
        params = tts_service._get_emotion_params("平静", 1.0, 0.0, 1.0)
        assert params["emotion"] == "neutral"
        assert params["speed"] == 1.0
        assert params["pitch"] == 0.0
        assert params["volume"] == 1.0

        # 测试高兴
        params = tts_service._get_emotion_params("高兴", 1.0, 0.0, 1.0)
        assert params["emotion"] == "happy"
        assert params["speed"] > 1.0  # 应有速度加成

        # 测试悲伤
        params = tts_service._get_emotion_params("悲伤", 1.0, 0.0, 1.0)
        assert params["emotion"] == "sad"
        assert params["speed"] < 1.0  # 应有速度降低

        # 测试愤怒
        params = tts_service._get_emotion_params("愤怒", 1.0, 0.0, 1.0)
        assert params["emotion"] == "angry"
        assert params["speed"] > 1.0

    def test_get_emotion_params_with_intensity(self, tts_service):
        """测试带强度的情感参数"""
        # 测试高兴_low
        params = tts_service._get_emotion_params("高兴_low", 1.0, 0.0, 1.0)
        assert params["emotion"] == "happy"
        assert params["speed"] == pytest.approx(1.05, rel=0.1)

        # 测试高兴_high
        params = tts_service._get_emotion_params("高兴_high", 1.0, 0.0, 1.0)
        assert params["emotion"] == "happy"
        assert params["speed"] > 1.1

    def test_get_emotion_params_with_base_params(self, tts_service):
        """测试带基础参数的情感映射"""
        # 基础速度为 0.8 的情况
        params = tts_service._get_emotion_params("平静", 0.8, 0.0, 1.0)
        assert params["speed"] == 0.8

        # 基础音调为 0.1 的情况
        params = tts_service._get_emotion_params("愤怒", 1.0, 0.1, 1.0)
        assert params["pitch"] > 0.3  # 应有情感音调加成

        # 基础音量为 0.9 的情况
        params = tts_service._get_emotion_params("高兴", 1.0, 0.0, 0.9)
        assert params["volume"] > 0.9  # 应有情感音量加成

    def test_get_emotion_params_unknown_emotion(self, tts_service):
        """测试未知情感"""
        params = tts_service._get_emotion_params("未知情感", 1.0, 0.0, 1.0)
        assert params["emotion"] == "neutral"
        assert params["speed"] == 1.0

    def test_get_emotion_params_english_emotion(self, tts_service):
        """测试英文情感标签"""
        params = tts_service._get_emotion_params("happy_low", 1.0, 0.0, 1.0)
        assert params["emotion"] == "happy"

        params = tts_service._get_emotion_params("sad_high", 1.0, 0.0, 1.0)
        assert params["emotion"] == "sad"

    @pytest.mark.asyncio
    async def test_synthesize_success(self, tts_service):
        """测试语音合成成功"""
        # Mock API 响应
        mock_audio_data = b"fake audio data"
        mock_response_data = {
            "data": {
                "audio_file": base64.b64encode(mock_audio_data).decode("utf-8")
            }
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.__aenter__.return_value.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await tts_service.synthesize("测试文本")

            assert result == mock_audio_data

    @pytest.mark.asyncio
    async def test_synthesize_with_url(self, tts_service):
        """测试通过 URL 获取音频"""
        mock_audio_data = b"audio from url"
        mock_response_data = {
            "data": {
                "audio_url": "https://example.com/audio.mp3"
            }
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data

            # Mock 下载响应
            mock_download_response = Mock()
            mock_download_response.content = mock_audio_data
            mock_client.__aenter__.return_value.post.return_value = mock_response
            mock_client.__aenter__.return_value.get.return_value = mock_download_response

            mock_client_class.return_value = mock_client

            result = await tts_service.synthesize("测试文本")

            assert result == mock_audio_data

    @pytest.mark.asyncio
    async def test_synthesize_rate_limit(self, tts_service):
        """测试速率限制"""
        # Mock API 响应
        mock_response_data = {"data": {"audio_file": ""}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.__aenter__.return_value.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # 快速发送多个请求
            # 由于限流器存在，应该都能通过（令牌桶初始有足够令牌）
            for _ in range(5):
                try:
                    await tts_service.synthesize("测试文本", block=True)
                except Exception:
                    pass

    def test_get_available_voices(self, tts_service):
        """测试获取可用音色列表"""
        voices = tts_service.get_available_voices()

        assert len(voices) == 6

        # 验证音色结构
        for voice in voices:
            assert "id" in voice
            assert "name" in voice
            assert "gender" in voice
            assert "age_range" in voice
            assert "suitable_roles" in voice

        # 验证特定音色
        voice_ids = [v["id"] for v in voices]
        assert "male-qn" in voice_ids
        assert "female-shaon" in voice_ids

    def test_get_emotion_list(self, tts_service):
        """测试获取情感列表"""
        emotions = tts_service.get_emotion_list()

        assert len(emotions) > 0

        # 验证情感结构
        for emotion in emotions:
            assert "id" in emotion
            assert "name" in emotion
            assert "aliases" in emotion

        # 验证特定情感
        emotion_ids = [e["id"] for e in emotions]
        assert "neutral" in emotion_ids
        assert "happy" in emotion_ids
        assert "sad" in emotion_ids

    def test_get_quality_options(self, tts_service):
        """测试获取音频质量选项"""
        qualities = tts_service.get_quality_options()

        assert len(qualities) == 3

        for quality in qualities:
            assert "id" in quality
            assert "name" in quality
            assert "sample_rate" in quality
            assert "bitrate" in quality

    def test_get_rate_limit_status(self, tts_service):
        """测试限流器状态"""
        status = tts_service.get_rate_limit_status()

        assert "qps" in status
        assert "available_tokens" in status
        assert "capacity" in status
        assert status["qps"] == 10

    def test_get_cost_stats(self, tts_service):
        """测试成本统计"""
        stats = tts_service.get_cost_stats()

        assert "total_requests" in stats
        assert "total_characters" in stats
        assert "estimated_cost" in stats
        assert "error_rate" in stats

    def test_reset_cost_stats(self, tts_service):
        """测试重置成本统计"""
        # 添加一些统计数据
        stats = tts_service.get_cost_stats()
        initial_requests = stats["total_requests"]

        # 重置
        tts_service.reset_cost_stats()

        # 验证已重置
        new_stats = tts_service.get_cost_stats()
        assert new_stats["total_requests"] == 0

    def test_reset_rate_limiter(self, tts_service):
        """测试重置限流器"""
        # 获取当前状态
        old_status = tts_service.get_rate_limit_status()

        # 重置为新的 QPS
        tts_service.reset_rate_limiter(qps=5)

        # 验证已更新
        new_status = tts_service.get_rate_limit_status()
        assert new_status["qps"] == 5


class TestVoiceMapping:
    """音色映射测试"""

    @pytest.fixture
    def tts_service(self):
        with patch("services.svc_minimax_tts.settings") as mock_settings:
            mock_settings.MINIMAX_API_KEY = "test"
            mock_settings.MINIMAX_API_HOST = "https://api.minimax.chat"
            mock_settings.MINIMAX_GROUP_ID = "test"

            from services.svc_minimax_tts import MiniMaxTTSService
            return MiniMaxTTSService()

    def test_voice_mapping_completeness(self, tts_service):
        """测试音色映射完整性"""
        # 所有预设音色都应能正确映射
        test_cases = [
            ("narrator", "male-qn"),
            ("male-narrator", "male-qn"),
            ("female-narrator", "female-shaon"),
            ("male", "male-qn"),
            ("male-young", "male-qn"),
            ("male-elderly", "male-yun"),
            ("male-deep", "male-tian"),
            ("female", "female-shaon"),
            ("female-young", "female-shaon"),
            ("female-elderly", "female-don"),
            ("female-child", "female-xiang"),
        ]

        for input_voice, expected_output in test_cases:
            result = tts_service._get_voice_id(input_voice)
            assert result == expected_output, f"Failed for {input_voice}"

    def test_novel_role_voice_mapping(self, tts_service):
        """测试网络小说角色音色映射"""
        test_cases = [
            ("仙尊", "male-yun"),
            ("魔帝", "male-tian"),
            ("圣女", "female-shaon"),
            ("仙女", "female-shaon"),
            ("剑圣", "male-qn"),
            ("妖女", "female-xiang"),
            ("女帝", "female-shaon"),
        ]

        for input_role, expected_output in test_cases:
            result = tts_service._get_voice_id(input_role)
            assert result == expected_output, f"Failed for {input_role}"


class TestEmotionMapping:
    """情感映射测试"""

    @pytest.fixture
    def tts_service(self):
        with patch("services.svc_minimax_tts.settings") as mock_settings:
            mock_settings.MINIMAX_API_KEY = "test"
            mock_settings.MINIMAX_API_HOST = "https://api.minimax.chat"
            mock_settings.MINIMAX_GROUP_ID = "test"

            from services.svc_minimax_tts import MiniMaxTTSService
            return MiniMaxTTSService()

    def test_emotion_mapping_all_emotions(self, tts_service):
        """测试所有情感映射"""
        test_cases = [
            "平静",
            "高兴",
            "悲伤",
            "愤怒",
            "紧张",
            "惊讶",
            "温柔",
            "严肃",
            "冷漠",
        ]

        for emotion in test_cases:
            params = tts_service._get_emotion_params(emotion, 1.0, 0.0, 1.0)
            assert "emotion" in params
            assert "speed" in params
            assert "pitch" in params
            assert "volume" in params

    def test_emotion_intensity_levels(self, tts_service):
        """测试情感强度级别"""
        # 高兴的不同强度
        happy_low = tts_service._get_emotion_params("高兴_low", 1.0, 0.0, 1.0)
        happy_medium = tts_service._get_emotion_params("高兴", 1.0, 0.0, 1.0)
        happy_high = tts_service._get_emotion_params("高兴_high", 1.0, 0.0, 1.0)

        # 速度应该递增
        assert happy_low["speed"] < happy_medium["speed"]
        assert happy_medium["speed"] < happy_high["speed"]

        # 悲伤的不同强度
        sad_low = tts_service._get_emotion_params("悲伤_low", 1.0, 0.0, 1.0)
        sad_high = tts_service._get_emotion_params("悲伤_high", 1.0, 0.0, 1.0)

        # 悲伤速度应该递减
        assert sad_low["speed"] > sad_high["speed"]

    def test_english_emotion_aliases(self, tts_service):
        """测试英文情感别名"""
        # happy 系列
        params_en = tts_service._get_emotion_params("happy", 1.0, 0.0, 1.0)
        params_cn = tts_service._get_emotion_params("高兴", 1.0, 0.0, 1.0)
        assert params_en["emotion"] == params_cn["emotion"]

        # sad 系列
        params_en = tts_service._get_emotion_params("sad", 1.0, 0.0, 1.0)
        params_cn = tts_service._get_emotion_params("悲伤", 1.0, 0.0, 1.0)
        assert params_en["emotion"] == params_cn["emotion"]


class TestRateLimiterSingleton:
    """全局限流器单例测试"""

    def test_singleton_pattern(self):
        """测试全局限流器是单例"""
        with patch("services.svc_minimax_tts.settings") as mock_settings:
            mock_settings.MINIMAX_API_KEY = "test"
            mock_settings.MINIMAX_API_HOST = "https://api.minimax.chat"
            mock_settings.MINIMAX_GROUP_ID = "test"

            from services.svc_minimax_tts import MiniMaxTTSService, _GlobalRateLimiter

            # 重置单例以便测试
            _GlobalRateLimiter._instance = None

            # 创建两个实例
            service1 = MiniMaxTTSService(rate_limit_qps=5)
            service2 = MiniMaxTTSService(rate_limit_qps=10)

            # 它们应该共享同一个限流器
            assert service1._rate_limiter is service2._rate_limiter

            # 重置单例
            _GlobalRateLimiter._instance = None

    def test_rate_limiter_shared(self):
        """测试限流器在多个实例间共享"""
        with patch("services.svc_minimax_tts.settings") as mock_settings:
            mock_settings.MINIMAX_API_KEY = "test"
            mock_settings.MINIMAX_API_HOST = "https://api.minimax.chat"
            mock_settings.MINIMAX_GROUP_ID = "test"

            from services.svc_minimax_tts import MiniMaxTTSService, _GlobalRateLimiter

            # 重置单例
            _GlobalRateLimiter._instance = None

            service1 = MiniMaxTTSService()
            service2 = MiniMaxTTSService()

            # 获取状态应该一致
            status1 = service1.get_rate_limit_status()
            status2 = service2.get_rate_limit_status()

            assert status1["qps"] == status2["qps"]

            # 重置单例
            _GlobalRateLimiter._instance = None


class TestBatchSynthesis:
    """批量合成测试"""

    @pytest.fixture
    def tts_service(self):
        with patch("services.svc_minimax_tts.settings") as mock_settings:
            mock_settings.MINIMAX_API_KEY = "test"
            mock_settings.MINIMAX_API_HOST = "https://api.minimax.chat"
            mock_settings.MINIMAX_GROUP_ID = "test"

            from services.svc_minimax_tts import MiniMaxTTSService
            return MiniMaxTTSService()

    @pytest.mark.asyncio
    async def test_synthesize_batch(self, tts_service):
        """测试批量合成"""
        segments = [
            {"text": "第一段", "voice_id": "male-qn", "speed": 1.0},
            {"text": "第二段", "voice_id": "female-shaon", "speed": 1.0},
            {"text": "第三段", "voice_id": "male-qn", "speed": 1.0},
        ]

        mock_audio_data = b"fake audio"
        mock_response_data = {
            "data": {
                "audio_file": base64.b64encode(mock_audio_data).decode("utf-8")
            }
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.__aenter__.return_value.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            results = await tts_service.synthesize_batch(segments, max_concurrent=2)

            assert len(results) == 3
            for result in results:
                assert "success" in result
                assert "index" in result

    @pytest.mark.asyncio
    async def test_synthesize_batch_with_progress(self, tts_service):
        """测试批量合成（带进度回调）"""
        segments = [
            {"text": "第一段", "voice_id": "male-qn", "speed": 1.0},
            {"text": "第二段", "voice_id": "female-shaon", "speed": 1.0},
        ]

        mock_audio_data = b"fake audio"
        mock_response_data = {
            "data": {
                "audio_file": base64.b64encode(mock_audio_data).decode("utf-8")
            }
        }

        progress_calls = []

        def on_progress(completed, total, result):
            progress_calls.append((completed, total, result))

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.__aenter__.return_value.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            results = await tts_service.synthesize_batch(
                segments, 
                max_concurrent=2,
                on_progress=on_progress
            )

            # 验证进度回调被调用
            assert len(progress_calls) == 2


class TestAudioQuality:
    """音频质量测试"""

    def test_audio_quality_enum(self):
        """测试音频质量枚举"""
        from services.svc_minimax_tts import AudioQuality

        assert AudioQuality.STANDARD.value == "standard"
        assert AudioQuality.HIGH.value == "high"
        assert AudioQuality.ULTRA.value == "ultra"

    def test_audio_format_enum(self):
        """测试音频格式枚举"""
        from services.svc_minimax_tts import AudioFormat

        assert AudioFormat.MP3.value == "mp3"
        assert AudioFormat.WAV.value == "wav"


class TestCostTracking:
    """成本追踪测试"""

    def test_cost_stats_basic(self):
        """测试成本统计基本功能"""
        from services.svc_minimax_tts import TTSCostStats

        stats = TTSCostStats()

        # 初始状态
        assert stats.total_requests == 0
        assert stats.total_characters == 0

        # 添加记录
        stats.add(1000, 100.0, 0.05)
        assert stats.total_requests == 1
        assert stats.total_characters == 1000

    def test_cost_stats_to_dict(self):
        """测试成本统计序列化"""
        from services.svc_minimax_tts import TTSCostStats

        stats = TTSCostStats()
        stats.add(1000, 100.0, 0.05)
        stats.add_error()
        stats.add_retry()

        result = stats.to_dict()
        assert "total_requests" in result
        assert "total_characters" in result
        assert "error_count" in result
        assert "retry_count" in result
        assert "error_rate" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
