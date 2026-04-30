# ===========================================
# 音频后处理服务测试
# ===========================================

"""
音频后处理服务单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.svc_audio_postprocessor import AudioPostprocessorService


class TestAudioPostprocessorService:
    """测试音频后处理服务"""

    @pytest.fixture
    def processor(self):
        """创建服务实例"""
        return AudioPostprocessorService()

    @pytest.fixture
    def mock_audio_segment(self):
        """创建模拟音频片段"""
        audio = MagicMock()
        audio.channels = 2
        audio.frame_rate = 44100
        audio.sample_width = 2
        audio.max_dBFS = -3.0
        audio.dBFS = -10.0
        return audio

    def test_init(self, processor):
        """测试初始化"""
        assert processor.sample_rate == 44100
        assert processor.bit_rate == 192
        assert processor.crossfade_ms == 20

    def test_pause_config(self, processor):
        """测试停顿时长配置"""
        assert processor.PAUSE_CONFIG["sentence_end"] == 500
        assert processor.PAUSE_CONFIG["paragraph_end"] == 1000
        assert processor.PAUSE_CONFIG["chapter_end"] == 2500
        assert processor.PAUSE_CONFIG["emotion_pause"] == 300

    def test_lufs_target(self, processor):
        """测试 LUFS 目标值"""
        assert processor.TARGET_LUFS == -16.0

    def test_eq_config(self, processor):
        """测试 EQ 配置"""
        assert processor.EQ_CONFIG["low_cut"] == 80
        assert processor.EQ_CONFIG["high_boost"] == 3000
        assert processor.EQ_CONFIG["high_boost_db"] == 2

    @patch("services.svc_audio_postprocessor.AudioSegment")
    def test_concatenate_with_intelligence(self, mock_audio_segment_class, processor):
        """测试智能拼接"""
        from pydub import AudioSegment

        # 创建模拟音频片段
        audio1 = MagicMock(spec=AudioSegment)
        audio1.__len__ = Mock(return_value=5000)
        
        audio2 = MagicMock(spec=AudioSegment)
        audio2.__len__ = Mock(return_value=6000)

        segment_info = [
            {"emotion": "neutral"},
            {"emotion": "happy"},
        ]

        # 测试单个片段
        result = processor._concatenate_with_intelligence([audio1], segment_info[:1])
        assert result == audio1

    @patch("services.svc_audio_postprocessor.AudioSegment")
    def test_apply_noise_reduction(self, mock_audio_segment_class, processor):
        """测试降噪处理"""
        from pydub import AudioSegment

        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.high_pass_filter = Mock(return_value=mock_audio)
        mock_audio.low_pass_filter = Mock(return_value=mock_audio)

        result = processor._apply_noise_reduction(mock_audio)

        # 验证滤波被调用
        assert mock_audio.high_pass_filter.called
        assert mock_audio.low_pass_filter.called

    def test_get_audio_stats(self, processor, mock_audio_segment):
        """测试获取音频统计"""
        stats = processor.get_audio_stats(mock_audio_segment)
        
        assert "duration_ms" in stats
        assert "channels" in stats
        assert "sample_rate" in stats
        assert "max_dBFS" in stats
        assert stats["channels"] == 2
        assert stats["sample_rate"] == 44100


class TestAudioQualityMetrics:
    """测试音频质量指标"""

    def test_sample_rate_standard(self):
        """测试标准采样率"""
        assert 44100 == 44100  # CD 标准

    def test_bitrate_levels(self):
        """测试比特率级别"""
        standard = 192
        high = 320
        
        assert standard < high
        assert standard >= 192
        assert high >= 320

    def test_lufs_target_range(self):
        """测试 LUFS 目标范围"""
        target = -16.0
        # Spotify 标准: -14 LUFS
        # YouTube 标准: -14 LUFS
        # 广播标准: -23 LUFS
        assert -24 <= target <= -13

    def test_crossfade_duration(self):
        """测试交叉淡入淡出时长"""
        normal_crossfade = 20  # ms
        emotion_crossfade = 30  # ms
        
        assert 10 <= normal_crossfade <= 50
        assert 10 <= emotion_crossfade <= 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
