# ===========================================
# 音效合成服务
# ===========================================

"""
音效合成服务模块

将音效与主音频轨道混合，生成完整的有声书音频。

功能特性：
- 音效自动定位（基于 DeepSeek 分析结果）
- 音量平衡控制
- 淡入淡出效果
- 循环播放支持
- 前景/背景音效分层
- 与 panns-inference 集成进行语义匹配

参考 audiobookshelf 的音效处理方式。
"""

import logging
import os
from io import BytesIO
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from pydub import AudioSegment

from core.config import settings
from core.database import get_db_context
from core.models import SoundEffect, Chapter
from core.exceptions import ServiceError as AppError


logger = logging.getLogger("audiobook")


# ===========================================
# 数据结构
# ===========================================

@dataclass
class SoundEffectMixItem:
    """音效混合项目"""
    sound_effect: SoundEffect
    trigger_at_ms: int  # 触发时间（毫秒）
    duration_ms: int    # 持续时间（毫秒）
    volume: float       # 音量 (0.0 - 1.0)
    fade_in_ms: int     # 淡入时间
    fade_out_ms: int    # 淡出时间
    loop: bool          # 是否循环
    layer: str          # 层级 (foreground/background)


@dataclass
class MixResult:
    """混合结果"""
    success: bool
    output_path: str
    duration_ms: int
    warnings: List[str]


# ===========================================
# 音效合成服务
# ===========================================

class SoundEffectMixerService:
    """
    音效合成服务

    将音效与主音频轨道混合，支持：
    - 前景音效（Action sounds）
    - 背景音效（Ambient sounds）
    - 环境音（Environment sounds）
    - 转场音效（Transition sounds）
    """

    # 音量层级配置
    VOLUME_LAYER_CONFIG = {
        "foreground": 0.8,   # 前景音效：80%
        "background": 0.5,   # 背景音效：50%
        "ambient": 0.3,      # 环境音：30%
    }

    # 基础音量配置
    BASE_VOLUME = {
        "dialogue": 1.0,    # 对话/旁白：100%
        "foreground": 0.8,   # 前景音效
        "background": 0.5,   # 背景音效
        "music": 0.3,       # 背景音乐
    }

    def __init__(self):
        self.sample_rate = settings.AUDIO_SAMPLE_RATE

    def mix_chapter_audio(
        self,
        chapter_id: int,
        main_audio_path: str,
        sound_effects: List[Dict[str, Any]] = None,
        output_format: str = "mp3",
        quality: str = "high",
    ) -> Dict[str, Any]:
        """
        混合章节音频

        将主音频与音效混合，生成完整的有声书音频。

        Args:
            chapter_id: 章节 ID
            main_audio_path: 主音频路径（MinIO 路径）
            sound_effects: 音效列表（来自 DeepSeek 分析）
            output_format: 输出格式
            quality: 质量级别

        Returns:
            Dict: 混合结果
        """
        from services.svc_minio_storage import get_storage_service
        storage = get_storage_service()

        # 1. 加载主音频
        main_audio = self._load_audio_from_minio(storage, main_audio_path)
        if not main_audio:
            raise AppError(f"无法加载主音频: {main_audio_path}")

        total_duration_ms = len(main_audio)
        logger.info(f"主音频加载完成: {total_duration_ms}ms")

        # 2. 如果有音效配置，进行混合
        if sound_effects:
            main_audio = self._apply_sound_effects(
                main_audio,
                sound_effects,
                total_duration_ms,
            )

        # 3. 导出混合后的音频
        output_path = main_audio_path.replace(".mp3", "_mixed.mp3")
        output_data = self._export_audio(
            main_audio,
            output_format,
            quality,
        )

        # 4. 上传到 MinIO
        mixed_path = storage.upload_file(
            settings.MINIO_BUCKET_AUDIO,
            output_path,
            output_data,
            content_type=f"audio/{output_format}",
        )

        logger.info(f"音效混合完成: {mixed_path}")

        return {
            "success": True,
            "output_path": mixed_path,
            "duration_ms": len(main_audio),
            "file_size": len(output_data),
        }

    def mix_audio_with_timeline(
        self,
        main_audio: AudioSegment,
        sound_effect_items: List[SoundEffectMixItem],
    ) -> AudioSegment:
        """
        将音效按照时间线混合到主音频

        Args:
            main_audio: 主音频
            sound_effect_items: 音效混合项目列表

        Returns:
            AudioSegment: 混合后的音频
        """
        # 创建叠加层
        overlay = AudioSegment.silent(duration=len(main_audio))

        # 按层级排序（先处理背景，再处理前景）
        sound_effect_items.sort(key=lambda x: (
            0 if x.layer == "background" else
            1 if x.layer == "ambient" else
            2
        ))

        for item in sound_effect_items:
            # 加载音效
            effect_audio = self._load_sound_effect(item.sound_effect)
            if not effect_audio:
                logger.warning(f"无法加载音效: {item.sound_effect.name}")
                continue

            # 调整音量
            layer_volume = self.VOLUME_LAYER_CONFIG.get(item.layer, 0.5)
            final_volume = item.volume * layer_volume
            effect_audio = effect_audio + (20 * (final_volume - 1))  # 音量调整

            # 循环播放（如果需要）
            if item.loop:
                effect_audio = self._loop_audio(
                    effect_audio,
                    item.duration_ms,
                    item.fade_in_ms,
                    item.fade_out_ms,
                )
            else:
                # 裁剪到指定时长
                if len(effect_audio) > item.duration_ms:
                    effect_audio = effect_audio[:item.duration_ms]
                elif len(effect_audio) < item.duration_ms:
                    # 补静音
                    effect_audio = effect_audio + AudioSegment.silent(
                        duration=item.duration_ms - len(effect_audio)
                    )

                # 应用淡入淡出
                if item.fade_in_ms > 0:
                    effect_audio = effect_audio.fade_in(item.fade_in_ms)
                if item.fade_out_ms > 0:
                    effect_audio = effect_audio.fade_out(item.fade_out_ms)

            # 放置到指定位置
            if item.trigger_at_ms < len(main_audio):
                # 裁剪以确保不超出主音频范围
                available_duration = len(main_audio) - item.trigger_at_ms
                if len(effect_audio) > available_duration:
                    effect_audio = effect_audio[:available_duration]

                # 叠加
                overlay = overlay.overlay(effect_audio, position=item.trigger_at_ms)

        # 混合主音频和叠加层
        mixed = main_audio
        if overlay.dBFS > -60:  # 只有叠加层有内容时才混合
            mixed = main_audio.overlay(overlay)

        return mixed

    def _load_audio_from_minio(
        self,
        storage,
        audio_path: str,
    ) -> Optional[AudioSegment]:
        """从 MinIO 加载音频"""
        try:
            data = storage.download_file(
                settings.MINIO_BUCKET_AUDIO,
                audio_path,
            )
            return AudioSegment.from_mp3(BytesIO(data))
        except Exception as e:
            logger.error(f"加载音频失败: {audio_path} - {e}")
            return None

    def _load_sound_effect(
        self,
        sound_effect: SoundEffect,
    ) -> Optional[AudioSegment]:
        """加载音效文件"""
        from services.svc_minio_storage import get_storage_service
        storage = get_storage_service()

        try:
            # 优先使用本地路径
            if sound_effect.local_path and os.path.exists(sound_effect.local_path):
                if sound_effect.file_format == "mp3":
                    return AudioSegment.from_mp3(sound_effect.local_path)
                elif sound_effect.file_format == "wav":
                    return AudioSegment.from_wav(sound_effect.local_path)
                elif sound_effect.file_format == "ogg":
                    return AudioSegment.from_ogg(sound_effect.local_path)

            # 其次使用 MinIO 路径
            if sound_effect.minio_path:
                data = storage.download_file(
                    settings.MINIO_BUCKET_AUDIO,
                    sound_effect.minio_path,
                )
                return AudioSegment.from_mp3(BytesIO(data))

            logger.warning(f"音效没有可用路径: {sound_effect.name}")
            return None

        except Exception as e:
            logger.error(f"加载音效失败: {sound_effect.name} - {e}")
            return None

    def _loop_audio(
        self,
        audio: AudioSegment,
        target_duration_ms: int,
        fade_in_ms: int = 0,
        fade_out_ms: int = 0,
    ) -> AudioSegment:
        """循环音频以达到目标时长"""
        if len(audio) == 0:
            return audio

        result = AudioSegment.empty()
        current_duration = 0

        while current_duration < target_duration_ms:
            remaining = target_duration_ms - current_duration

            if len(audio) <= remaining:
                # 完整添加（最后一段不做淡出）
                if remaining - len(audio) < 500:  # 剩余空间小时，直接填充
                    result += audio[:remaining]
                    current_duration = target_duration_ms
                else:
                    result += audio
                    current_duration += len(audio)
            else:
                # 添加部分
                result += audio[:remaining]
                current_duration = target_duration_ms

        # 应用整体淡入淡出
        if fade_in_ms > 0:
            result = result.fade_in(min(fade_in_ms, len(result) // 2))
        if fade_out_ms > 0:
            result = result.fade_out(min(fade_out_ms, len(result) // 2))

        return result

    def _apply_sound_effects(
        self,
        main_audio: AudioSegment,
        sound_effects: List[Dict[str, Any]],
        total_duration_ms: int,
    ) -> AudioSegment:
        """
        应用音效到主音频

        Args:
            main_audio: 主音频
            sound_effects: 音效列表
            total_duration_ms: 总时长

        Returns:
            AudioSegment: 混合后的音频
        """
        # 创建音效项目列表
        mix_items = []

        for se in sound_effects:
            # 解析时间点
            trigger_at = self._parse_timestamp(se.get("trigger_at", "00:00:00"))
            duration_ms = se.get("duration_ms", 3000)
            volume = se.get("volume", 0.5)
            fade_in_ms = se.get("fade_in_ms", 500)
            fade_out_ms = se.get("fade_out_ms", 500)
            loop = se.get("loop", False)
            layer = se.get("layer", "foreground")

            # 查找匹配的音效
            matched_effect = self._find_matching_sound_effect(
                description=se.get("description", ""),
                effect_type=se.get("type"),
                layer=layer,
            )

            if matched_effect:
                mix_item = SoundEffectMixItem(
                    sound_effect=matched_effect,
                    trigger_at_ms=trigger_at,
                    duration_ms=duration_ms,
                    volume=volume,
                    fade_in_ms=fade_in_ms,
                    fade_out_ms=fade_out_ms,
                    loop=loop,
                    layer=layer,
                )
                mix_items.append(mix_item)

        if not mix_items:
            logger.info("没有找到匹配的音效，跳过混合")
            return main_audio

        return self.mix_audio_with_timeline(main_audio, mix_items)

    def _find_matching_sound_effect(
        self,
        description: str,
        effect_type: str = None,
        layer: str = "foreground",
    ) -> Optional[SoundEffect]:
        """
        查找匹配的音效

        Args:
            description: 音效描述
            effect_type: 音效类型
            layer: 音效层级

        Returns:
            SoundEffect 或 None
        """
        from services.svc_sound_effect_library import get_sound_effect_library_service

        service = get_sound_effect_library_service()
        results = service.search_sound_effects(
            query=description,
            effect_type=effect_type,
            layer=layer,
            limit=3,
            include_bbc=True,
        )

        if results and results[0].match_score >= 0.3:
            return results[0].sound_effect

        return None

    def _parse_timestamp(self, timestamp: str) -> int:
        """
        解析时间戳为毫秒

        Args:
            timestamp: 时间戳格式 "HH:MM:SS"

        Returns:
            int: 毫秒
        """
        try:
            parts = timestamp.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = parts
                return (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000
            elif len(parts) == 2:
                minutes, seconds = parts
                return (int(minutes) * 60 + int(seconds)) * 1000
            else:
                return int(timestamp)
        except Exception:
            logger.warning(f"无法解析时间戳: {timestamp}")
            return 0

    def _export_audio(
        self,
        audio: AudioSegment,
        output_format: str,
        quality: str,
    ) -> bytes:
        """导出音频"""
        bitrate = "320k" if quality == "high" else "192k"

        export_format = output_format
        if output_format == "m4b":
            export_format = "ipod"

        return audio.export(
            format=export_format,
            bitrate=bitrate,
        ).read()

    def create_sound_effect_manifest(
        self,
        chapter_id: int,
        sound_effects: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        创建音效清单

        用于前端显示和用户编辑。

        Args:
            chapter_id: 章节 ID
            sound_effects: 音效列表

        Returns:
            Dict: 音效清单
        """
        manifest = {
            "chapter_id": chapter_id,
            "sound_effects": [],
            "total_duration_ms": 0,
            "warnings": [],
        }

        for idx, se in enumerate(sound_effects):
            # 查找匹配的音效
            matched_effect = self._find_matching_sound_effect(
                description=se.get("description", ""),
                effect_type=se.get("type"),
                layer=se.get("layer"),
            )

            manifest_item = {
                "index": idx,
                "design": se,
                "matched": matched_effect is not None,
                "matched_sound_effect": matched_effect.to_dict() if matched_effect else None,
            }

            # 检查时间点是否有效
            trigger_at = self._parse_timestamp(se.get("trigger_at", "00:00:00"))
            if trigger_at < 0:
                manifest["warnings"].append(f"音效 {idx} 时间点无效: {se.get('trigger_at')}")

            manifest["sound_effects"].append(manifest_item)

        return manifest


# ===========================================
# 背景音乐混合
# ===========================================

class BackgroundMusicMixerService:
    """
    背景音乐混合服务

    专门处理背景音乐的混合。
    """

    def __init__(self):
        self.sample_rate = settings.AUDIO_SAMPLE_RATE

    def mix_background_music(
        self,
        main_audio: AudioSegment,
        background_music_configs: List[Dict[str, Any]],
        base_dialogue_volume: float = 1.0,
    ) -> AudioSegment:
        """
        混合背景音乐

        Args:
            main_audio: 主音频（对话/旁白）
            background_music_configs: 背景音乐配置列表
            base_dialogue_volume: 对话基础音量

        Returns:
            AudioSegment: 混合后的音频
        """
        if not background_music_configs:
            return main_audio

        # 创建背景音乐轨道
        music_track = AudioSegment.silent(duration=len(main_audio))

        for config in background_music_configs:
            trigger_at = self._parse_timestamp(config.get("trigger_at", "00:00:00"))
            end_at = self._parse_timestamp(config.get("end_at", ""))
            duration_ms = config.get("duration_ms")
            volume = config.get("volume", 0.3)
            fade_in_ms = config.get("fade_in_ms", 2000)
            fade_out_ms = config.get("fade_out_ms", 3000)
            crossfade = config.get("crossfade_with_next", True)
            intensity = config.get("intensity", 3)

            # 加载背景音乐
            music = self._load_background_music(config)
            if not music:
                continue

            # 根据强度调整音量
            adjusted_volume = volume * (intensity / 5.0) * 0.5
            music = music + (20 * (adjusted_volume - 1))

            # 计算播放范围
            if not end_at:
                end_at = len(main_audio)
            if not duration_ms:
                duration_ms = end_at - trigger_at

            # 裁剪音乐
            if len(music) > duration_ms:
                music = music[:duration_ms]

            # 应用淡入淡出
            if fade_in_ms > 0 and trigger_at == 0:
                music = music.fade_in(fade_in_ms)

            # 放置到指定位置
            if trigger_at < len(main_audio):
                available = len(main_audio) - trigger_at
                music_to_place = music[:available]

                if crossfade and len(music_track) > trigger_at:
                    # 交叉淡入淡出
                    crossfade_duration = min(fade_out_ms, 2000)
                    music_track = music_track.overlay(
                        music_to_place,
                        position=trigger_at,
                    )
                else:
                    music_track = music_track.overlay(music_to_place, position=trigger_at)

        # 降低背景音乐音量以确保对话清晰
        # 背景音乐不应超过对话音量的 30%
        max_music_volume = base_dialogue_volume * 0.3
        if music_track.dBFS > -60:  # 音乐有内容
            current_music_db = music_track.dBFS
            target_music_db = -20 - (20 * (1 - max_music_volume))  # 转换为 dB

            if current_music_db > target_music_db:
                adjustment = target_music_db - current_music_db
                music_track = music_track + adjustment

            # 混合主音频和背景音乐
            return main_audio.overlay(music_track)
        else:
            return main_audio

    def _load_background_music(self, config: Dict[str, Any]) -> Optional[AudioSegment]:
        """
        加载背景音乐

        实际实现中应该：
        1. 从本地音乐库查找
        2. 从在线音乐服务获取
        3. 使用 AI 生成音乐
        """
        # 这里是一个占位实现
        # 实际项目中应该接入音乐库
        logger.info(f"加载背景音乐: {config.get('type', 'unknown')}")
        return None

    def _parse_timestamp(self, timestamp: str) -> int:
        """解析时间戳为毫秒"""
        try:
            parts = timestamp.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = parts
                return (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000
            elif len(parts) == 2:
                minutes, seconds = parts
                return (int(minutes) * 60 + int(seconds)) * 1000
            else:
                return int(timestamp)
        except Exception:
            return 0


# ===========================================
# 全局服务实例
# ===========================================

_sound_effect_mixer_service = None
_background_music_mixer_service = None


def get_sound_effect_mixer_service() -> SoundEffectMixerService:
    """获取音效合成服务实例"""
    global _sound_effect_mixer_service
    if _sound_effect_mixer_service is None:
        _sound_effect_mixer_service = SoundEffectMixerService()
    return _sound_effect_mixer_service


def get_background_music_mixer_service() -> BackgroundMusicMixerService:
    """获取背景音乐混合服务实例"""
    global _background_music_mixer_service
    if _background_music_mixer_service is None:
        _background_music_mixer_service = BackgroundMusicMixerService()
    return _background_music_mixer_service
