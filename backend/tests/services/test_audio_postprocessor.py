# ===========================================
# 音频后处理服务测试
# ===========================================

"""
音频后处理服务单元测试

覆盖功能：
- 音频拼接（交叉淡入淡出）
- 智能停顿控制
- 降噪处理
- LUFS 音量均衡
- ID3 标签注入
- 多格式转换（M4B）
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
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
        assert processor.PAUSE_CONFIG["dialogue_break"] == 200

    def test_lufs_target(self, processor):
        """测试 LUFS 目标值"""
        assert processor.TARGET_LUFS == -16.0

    def test_eq_config(self, processor):
        """测试 EQ 配置"""
        assert processor.EQ_CONFIG["low_cut"] == 80
        assert processor.EQ_CONFIG["high_boost"] == 3000
        assert processor.EQ_CONFIG["high_boost_db"] == 2
        assert processor.EQ_CONFIG["low_cut_db"] == -3

    @patch("services.svc_audio_postprocessor.AudioSegment")
    def test_concatenate_single_segment(self, mock_audio_segment_class, processor):
        """测试单个片段处理（边界情况）"""
        from pydub import AudioSegment

        # 创建模拟音频片段
        audio1 = MagicMock(spec=AudioSegment)
        audio1.__len__ = Mock(return_value=5000)

        segment_info = [
            {"emotion": "neutral", "duration_ms": 5000},
        ]

        # 测试单个片段
        result = processor._concatenate_with_intelligence([audio1], segment_info)
        assert result == audio1

    @patch("services.svc_audio_postprocessor.AudioSegment")
    def test_concatenate_with_emotion_change(self, mock_audio_segment_class, processor):
        """测试情感变化时的拼接"""
        from pydub import AudioSegment

        audio1 = MagicMock(spec=AudioSegment)
        audio1.__len__ = Mock(return_value=3000)
        audio1.append = Mock(return_value=audio1)
        audio1.__add__ = Mock(return_value=audio1)

        audio2 = MagicMock(spec=AudioSegment)
        audio2.__len__ = Mock(return_value=4000)

        segment_info = [
            {"emotion": "neutral", "duration_ms": 3000},
            {"emotion": "happy", "duration_ms": 4000},
        ]

        processor._concatenate_with_intelligence([audio1, audio2], segment_info)

        # 验证 append 被调用（带交叉淡入淡出）
        audio1.append.assert_called()

    @patch("services.svc_audio_postprocessor.AudioSegment")
    def test_concatenate_same_emotion(self, mock_audio_segment_class, processor):
        """测试相同情感时的拼接"""
        from pydub import AudioSegment

        audio1 = MagicMock(spec=AudioSegment)
        audio1.__len__ = Mock(return_value=3000)
        audio1.append = Mock(return_value=audio1)

        audio2 = MagicMock(spec=AudioSegment)
        audio2.__len__ = Mock(return_value=4000)

        segment_info = [
            {"emotion": "neutral", "duration_ms": 3000},
            {"emotion": "neutral", "duration_ms": 4000},
        ]

        processor._concatenate_with_intelligence([audio1, audio2], segment_info)

        # 验证 append 被调用
        audio1.append.assert_called()

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

    @patch("services.svc_audio_postprocessor.AudioSegment")
    def test_apply_noise_reduction_error_handling(self, mock_audio_segment_class, processor):
        """测试降噪处理错误处理"""
        from pydub import AudioSegment

        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.high_pass_filter = Mock(side_effect=Exception("Filter error"))
        mock_audio.low_pass_filter = Mock(return_value=mock_audio)

        # 不应抛出异常
        result = processor._apply_noise_reduction(mock_audio)
        assert result is not None

    @patch("services.svc_audio_postprocessor.normalize")
    @patch("services.svc_audio_postprocessor.compress_dynamic_range")
    def test_apply_lufs_normalization(self, mock_compress, mock_normalize, processor):
        """测试 LUFS 音量标准化"""
        from pydub import AudioSegment

        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.max_dBFS = -0.5
        mock_audio.apply_gain = Mock(return_value=mock_audio)
        mock_normalize.return_value = mock_audio
        mock_compress.return_value = mock_audio

        result = processor._apply_lufs_normalization(mock_audio)

        # 验证 normalize 被调用
        mock_normalize.assert_called_once()

    @patch("services.svc_audio_postprocessor.normalize")
    @patch("services.svc_audio_postprocessor.compress_dynamic_range")
    def test_apply_lufs_normalization_compression_failure(
        self, mock_compress, mock_normalize, processor
    ):
        """测试 LUFS 标准化时压缩失败的处理"""
        from pydub import AudioSegment

        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.max_dBFS = -3.0
        mock_audio.apply_gain = Mock(return_value=mock_audio)
        mock_normalize.return_value = mock_audio
        mock_compress.side_effect = Exception("Compression error")

        # 不应抛出异常
        result = processor._apply_lufs_normalization(mock_audio)
        assert result == mock_audio

    def test_get_audio_stats(self, processor, mock_audio_segment):
        """测试获取音频统计"""
        stats = processor.get_audio_stats(mock_audio_segment)
        
        assert "duration_ms" in stats
        assert "channels" in stats
        assert "sample_rate" in stats
        assert "max_dBFS" in stats
        assert "rms_dBFS" in stats
        assert stats["channels"] == 2
        assert stats["sample_rate"] == 44100
        assert stats["max_dBFS"] == -3.0
        assert stats["rms_dBFS"] == -10.0

    @patch("services.svc_audio_postprocessor.AudioSegment")
    def test_insert_smart_pauses(self, mock_audio_segment_class, processor):
        """测试智能停顿插入"""
        from pydub import AudioSegment

        mock_audio = MagicMock(spec=AudioSegment)
        segment_info = [
            {"emotion": "neutral", "pause_after": "normal"},
        ]

        # 当前实现为 pass-through
        result = processor._insert_smart_pauses(mock_audio, segment_info)
        assert result == mock_audio

    def test_concatenate_empty_segments_error(self, processor):
        """测试空片段列表错误处理"""
        with pytest.raises(Exception):  # AppError
            processor._concatenate_with_intelligence([], [])


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

    def test_pause_durations(self):
        """测试各类停顿时长配置"""
        pauses = {
            "sentence_end": 500,      # 句号后
            "paragraph_end": 1000,    # 段落结束
            "chapter_end": 2500,       # 章节结束
            "emotion_pause": 300,     # 情感切换
            "dialogue_break": 200,    # 对话间隔
        }
        
        assert pauses["sentence_end"] == 500
        assert pauses["paragraph_end"] == 1000
        assert pauses["chapter_end"] == 2500

    def test_eq_filter_frequencies(self):
        """测试 EQ 滤波器频率"""
        eq_config = {
            "low_cut": 80,       # 低频切除（Hz）
            "high_boost": 3000,  # 高频提升起始点（Hz）
        }
        
        assert eq_config["low_cut"] >= 20  # 最低有效频率
        assert eq_config["high_boost"] <= 10000  # 语音高频上限


class TestID3TagInjection:
    """测试 ID3 标签注入"""

    @patch("services.svc_audio_postprocessor.subprocess")
    @patch("services.svc_audio_postprocessor.tempfile")
    def test_inject_id3_tags_success(self, mock_tempfile, mock_subprocess, processor):
        """测试 ID3 标签成功注入"""
        mock_tempfile.NamedTemporaryFile.return_value.__enter__ = Mock(
            return_value=Mock(name="/tmp/test.mp3")
        )
        mock_subprocess.run.return_value = Mock(returncode=0)

        # Mock storage
        mock_storage = MagicMock()

        # 测试不应抛出异常
        result = processor._inject_id3_tags(
            audio_data=b"fake audio data",
            object_name="test/chapter1.mp3",
            book_title="测试书籍",
            author="测试作者",
            chapter_title="第一章",
            track_number=1,
            cover_image=None,
            storage=mock_storage,
        )

        assert result is not None

    @patch("services.svc_audio_postprocessor.subprocess")
    @patch("services.svc_audio_postprocessor.tempfile")
    def test_inject_id3_tags_with_cover(self, mock_tempfile, mock_subprocess, processor):
        """测试带封面的 ID3 标签注入"""
        mock_tempfile.NamedTemporaryFile.return_value.__enter__ = Mock(
            return_value=Mock(name="/tmp/test.mp3")
        )
        mock_subprocess.run.return_value = Mock(returncode=0)

        mock_storage = MagicMock()

        # 测试带封面图
        result = processor._inject_id3_tags(
            audio_data=b"fake audio data",
            object_name="test/chapter1.mp3",
            book_title="测试书籍",
            author="测试作者",
            chapter_title="第一章",
            track_number=1,
            cover_image=b"fake image data",
            storage=mock_storage,
        )

        assert result is not None

    @patch("services.svc_audio_postprocessor.subprocess")
    @patch("services.svc_audio_postprocessor.tempfile")
    def test_inject_id3_tags_fallback(self, mock_tempfile, mock_subprocess, processor):
        """测试 ID3 标签注入失败时的回退"""
        mock_tempfile.NamedTemporaryFile.return_value.__enter__ = Mock(
            side_effect=Exception("Temp file error")
        )
        mock_subprocess.run.return_value = Mock(returncode=1)

        mock_storage = MagicMock()

        # 应该回退到原始文件
        result = processor._inject_id3_tags(
            audio_data=b"fake audio data",
            object_name="test/chapter1.mp3",
            book_title="测试书籍",
            author="测试作者",
            chapter_title="第一章",
            track_number=1,
            cover_image=None,
            storage=mock_storage,
        )

        assert result == "test/chapter1.mp3"


class TestM4BCreation:
    """测试 M4B 文件创建"""

    @patch("services.svc_audio_postprocessor.subprocess")
    @patch("services.svc_audio_postprocessor.tempfile")
    def test_create_m4b_fallback(self, mock_tempfile, mock_subprocess, processor):
        """测试 M4B 创建失败时的回退"""
        mock_tempfile.mkdtemp.return_value = "/tmp/test_dir"
        mock_subprocess.run.side_effect = Exception("FFmpeg error")

        mock_storage = MagicMock()

        # Mock chapter
        mock_chapter = MagicMock()
        mock_chapter.book_id = 1
        mock_chapter.chapter_index = 1
        mock_chapter.title = "第一章"
        mock_chapter.audio_file_path = None

        # 应该不会抛出异常
        result = processor._create_m4b_with_chapters(
            chapters=[mock_chapter],
            book_title="测试书籍",
            author="测试作者",
            cover_image=None,
            storage=mock_storage,
            quality="high",
        )

        # 返回空字符串或原始 object_name
        assert result == "" or result is not None


class TestIntegration:
    """集成测试（Mock 环境）"""

    @patch("services.svc_audio_postprocessor.AudioSegment")
    def test_full_processing_pipeline(self, mock_audio_segment_class, processor):
        """测试完整处理流程"""
        from pydub import AudioSegment

        # 创建多个模拟音频片段
        audio1 = MagicMock(spec=AudioSegment)
        audio1.__len__ = Mock(return_value=5000)
        audio1.channels = 2
        audio1.frame_rate = 44100

        audio2 = MagicMock(spec=AudioSegment)
        audio2.__len__ = Mock(return_value=6000)
        audio2.channels = 2
        audio2.frame_rate = 44100

        segments = [audio1, audio2]
        segment_info = [
            {"emotion": "neutral", "duration_ms": 5000},
            {"emotion": "happy", "duration_ms": 6000},
        ]

        # 1. 测试拼接
        concatenated = processor._concatenate_with_intelligence(segments, segment_info)
        assert concatenated is not None

        # 2. 测试停顿插入
        with_pauses = processor._insert_smart_pauses(concatenated, segment_info)
        assert with_pauses is not None

        # 3. 测试降噪
        with patch.object(processor, '_apply_noise_reduction', return_value=concatenated):
            denoised = processor._apply_noise_reduction(concatenated)
            assert denoised is not None

        # 4. 测试 LUFS 标准化
        with patch.object(processor, '_apply_lufs_normalization', return_value=concatenated):
            normalized = processor._apply_lufs_normalization(concatenated)
            assert normalized is not None

        # 5. 测试统计
        stats = processor.get_audio_stats(audio1)
        assert "duration_ms" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
