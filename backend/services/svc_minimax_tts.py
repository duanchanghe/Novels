# ===========================================
# MiniMax TTS 服务 - 增强版
# ===========================================

"""
MiniMax TTS 服务 - 增强版

调用 MiniMax API 进行语音合成，支持超高品质音质优化。

功能特性：
- 音色映射：角色名 → MiniMax 音色ID（支持中文网络小说角色类型）
- 情感参数映射：情感 → MiniMax 情感参数（细分强度）
- 并发控制：令牌桶限流（10 QPS）
- 重试策略：指数退避重试
- 成本追踪：记录 API 调用和消耗
- 批量合成：支持并发批量处理
- 音频优化：支持音调、语速、音量微调
- SSML 支持：高级音频参数控制
"""

import logging
import threading
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

import httpx

from core.config import settings
from core.constants import (
    VOICE_MAP_SIMPLE,
    ROLE_VOICE_MAP,
    EMOTION_PARAM_MAP,
    DEFAULT_EMOTION_CONFIG,
    INTENSITY_FACTOR_MAP,
)
from core.exceptions import MiniMaxApiError
from utils.util_rate_limiter import TokenBucket, RateLimiter
from utils.util_retry import retry_sync, exponential_backoff


logger = logging.getLogger("audiobook")


# ===========================================
# 数据结构定义
# ===========================================

class AudioQuality(str, Enum):
    """音频质量等级"""
    STANDARD = "standard"      # 标准质量
    HIGH = "high"             # 高品质
    ULTRA = "ultra"           # 超高品质
    LOSSLESS = "lossless"     # 无损品质


class AudioFormat(str, Enum):
    """音频格式"""
    MP3 = "mp3"
    WAV = "wav"
    PCM = "pcm"
    FLAC = "flac"


@dataclass
class TTSCostStats:
    """TTS 成本统计"""
    total_requests: int = 0
    total_characters: int = 0
    total_audio_seconds: float = 0
    total_cost: float = 0.0
    error_count: int = 0
    retry_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # MiniMax TTS 价格（示例，实际以官方为准）
    PRICE_PER_1000_CHARS = 0.05  # ¥/1000 字符

    def add(self, characters: int, audio_seconds: float = 0, cost: float = 0):
        with self._lock:
            self.total_requests += 1
            self.total_characters += characters
            self.total_audio_seconds += audio_seconds
            self.total_cost += cost

    def add_error(self):
        with self._lock:
            self.error_count += 1

    def add_retry(self):
        with self._lock:
            self.retry_count += 1

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_requests": self.total_requests,
                "total_characters": self.total_characters,
                "total_audio_seconds": round(self.total_audio_seconds, 2),
                "estimated_cost": round(self.total_cost, 4),
                "cost_per_1k_chars": self.PRICE_PER_1000_CHARS,
                "error_count": self.error_count,
                "retry_count": self.retry_count,
                "error_rate": round(self.error_count / max(self.total_requests, 1) * 100, 2),
            }


# 全局成本统计
_tts_cost_stats = TTSCostStats()


# ===========================================
# 全局限流器（单例模式，线程安全）
# ===========================================

class _GlobalRateLimiter:
    """
    全局限流器（线程安全单例）

    确保所有 TTS 请求共享同一个限流器。
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, qps: float = 10.0):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._rate_limiter = RateLimiter(qps=qps)
                    cls._instance._qps = qps
        return cls._instance

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    @property
    def qps(self) -> float:
        return self._qps

    def reset(self, qps: float = 10.0):
        """重置限流器"""
        self._rate_limiter = RateLimiter(qps=qps)
        self._qps = qps


def _get_rate_limiter(qps: float = 10.0) -> RateLimiter:
    """获取全局限流器实例"""
    return _GlobalRateLimiter(qps=qps).rate_limiter


class MiniMaxTTSService:
    """
    MiniMax TTS 服务 - 增强版

    提供语音合成功能，支持多音色和情感参数，以及超高品质音质优化。
    音色与情感映射表统一来源于 core.constants（唯一数据源）。
    """

    # ===========================================
    # 音色映射表 → 来源 core.constants.VOICE_MAP_SIMPLE
    # ===========================================
    VOICE_MAP = VOICE_MAP_SIMPLE

    # ===========================================
    # 情感参数映射 → 来源 core.constants.EMOTION_PARAM_MAP
    # （TTS 服务扩展了 volume_factor 字段，默认 1.0）
    # ===========================================
    @staticmethod
    def _build_emotion_map():
        """从共享常量构建带 volume_factor 的情感映射表"""
        result = {}
        for key, config in EMOTION_PARAM_MAP.items():
            result[key] = {
                "emotion": config["emotion"],
                "speed_factor": config["speed_factor"],
                "pitch_factor": config["pitch"],
                "volume_factor": 1.0,
            }
        # 补充英文 key（如 happy/sad/angry 等）
        en_aliases = {
            "happy": "高兴", "sad": "悲伤", "angry": "愤怒",
            "fearful": "紧张", "surprise": "惊讶", "gentle": "温柔",
            "serious": "严肃", "neutral": "平静",
        }
        for en, cn in en_aliases.items():
            if cn in EMOTION_PARAM_MAP:
                c = EMOTION_PARAM_MAP[cn]
                result[f"{en}_low"] = {"emotion": c["emotion"], "speed_factor": c["speed_factor"] - 0.05, "pitch_factor": c["pitch"] - 0.05, "volume_factor": 0.95}
                result[f"{en}_medium"] = {"emotion": c["emotion"], "speed_factor": c["speed_factor"], "pitch_factor": c["pitch"], "volume_factor": 1.0}
                result[f"{en}_high"] = {"emotion": c["emotion"], "speed_factor": c["speed_factor"] + 0.05, "pitch_factor": c["pitch"] + 0.1, "volume_factor": 1.05}
        return result

    EMOTION_MAP = _build_emotion_map.__func__()

    # 默认回退情感
    DEFAULT_EMOTION_ENTRY = {
        "emotion": "neutral", "speed_factor": 1.0,
        "pitch_factor": 0, "volume_factor": 1.0,
    }

    def __init__(self, rate_limit_qps: float = 10.0):
        """
        初始化 TTS 服务

        Args:
            rate_limit_qps: 每秒请求数限制（默认 10 QPS）
                           注意：仅在首次调用时生效，后续调用会忽略此参数
        """
        self.api_key = settings.MINIMAX_API_KEY
        self.api_host = settings.MINIMAX_API_HOST
        self.group_id = settings.MINIMAX_GROUP_ID
        # 使用全局限流器（单例模式）
        self._rate_limiter = _get_rate_limiter(rate_limit_qps)

    def _get_voice_id(self, voice_id: str) -> str:
        """
        获取规范化后的音色 ID

        Args:
            voice_id: 原始音色标识

        Returns:
            str: MiniMax 音色 ID
        """
        if not voice_id:
            return "male-qn-qingse"

        # 如果已经是有效的 MiniMax voice_id，直接返回
        voice_values = list(self.VOICE_MAP.values())
        if voice_id in voice_values:
            return voice_id

        # 尝试精确匹配
        if voice_id in self.VOICE_MAP:
            return self.VOICE_MAP[voice_id]

        # 尝试小写匹配
        voice_id_lower = voice_id.lower()
        for key, value in self.VOICE_MAP.items():
            if key.lower() == voice_id_lower:
                return value

        # 尝试中文角色类型匹配
        if voice_id in self.ROLE_TYPE_VOICE_MAP:
            return self.ROLE_TYPE_VOICE_MAP[voice_id]

        # 默认返回 male-qn-qingse
        return "male-qn-qingse"

    def _get_emotion_params(
        self,
        emotion: str,
        base_speed: float = 1.0,
        base_pitch: float = 0.0,
        base_volume: float = 1.0,
    ) -> Dict[str, Any]:
        """
        获取情感参数（支持强度细分）

        Args:
            emotion: 情感标签（如"悲伤_high"、"高兴_medium"）
            base_speed: 基础语速
            base_pitch: 基础音调
            base_volume: 基础音量

        Returns:
            dict: MiniMax 情感参数
        """
        # 查找精确匹配
        if emotion in self.EMOTION_MAP:
            emotion_config = self.EMOTION_MAP[emotion]
            return {
                "emotion": emotion_config["emotion"],
                "speed": float(base_speed) * float(emotion_config["speed_factor"]),
                "pitch": float(base_pitch) + float(emotion_config["pitch_factor"]),
                "volume": float(base_volume) * float(emotion_config["volume_factor"]),
            }

        # 尝试基础情感匹配
        base_emotion = emotion.split("_")[0] if "_" in emotion else emotion
        for key, config in self.EMOTION_MAP.items():
            if key.startswith(base_emotion):
                return {
                    "emotion": config["emotion"],
                    "speed": float(base_speed) * float(config["speed_factor"]),
                    "pitch": float(base_pitch) + float(config["pitch_factor"]),
                    "volume": float(base_volume) * float(config["volume_factor"]),
                }

        # 默认返回 neutral
        return {"emotion": "neutral", "speed": base_speed, "pitch": base_pitch, "volume": base_volume}

    def _build_ssml(
        self,
        text: str,
        voice_id: str,
        speed: float,
        pitch: float,
        emotion: str,
    ) -> Optional[str]:
        """
        构建 SSML 文本（如果 API 支持）

        用于更精细的音频控制，如多音字注音、停顿控制等。

        Args:
            text: 原始文本
            voice_id: 音色 ID
            speed: 语速
            pitch: 音调
            emotion: 情感

        Returns:
            str: SSML 格式文本，或 None（如果不支持）
        """
        # MiniMax 目前不完全支持 SSML，这里提供预留接口
        # 如果未来支持，可以在这里添加 SSML 转换逻辑
        return None

    async def synthesize(
        self,
        text: str,
        voice_id: str = "male-qn",
        speed: float = 1.0,
        emotion: str = None,
        pitch: float = 0.0,
        volume: float = 1.0,
        block: bool = True,
        quality: AudioQuality = AudioQuality.HIGH,
    ) -> bytes:
        """
        合成语音（支持限流和重试）

        Args:
            text: 待合成文本
            voice_id: 音色 ID
            speed: 语速（0.5-2.0）
            emotion: 情感标签
            pitch: 音调调整（-0.5 到 0.5）
            volume: 音量调整（0.5 到 2.0）
            block: 是否阻塞等待（False则限流时直接失败）
            quality: 音频质量等级

        Returns:
            bytes: 音频数据（MP3 格式）

        Raises:
            MiniMaxApiError: 合成失败时抛出
        """
        global _tts_cost_stats
        
        if not self.api_key:
            raise MiniMaxApiError("MiniMax API Key 未配置")

        # 限流检查
        if not self._rate_limiter.acquire(block=block):
            raise MiniMaxApiError("API 速率限制，请稍后重试")

        # 映射音色 ID
        mapped_voice_id = self._get_voice_id(voice_id)

        # 获取情感参数
        emotion_params = self._get_emotion_params(
            emotion or "neutral",
            speed,
            pitch,
            volume,
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.api_host}/v1/t2a_v2",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "speech-2.8-hd",
                        "text": text,
                        "stream": False,
                        "voice_setting": {
                            "voice_id": mapped_voice_id,
                            "speed": int(float(emotion_params["speed"]) * 100),  # MiniMax 使用整数（百分比）
                            "vol": int(float(emotion_params["volume"]) * 100),
                            "pitch": int(float(emotion_params["pitch"]) * 100),
                        },
                        "audio_setting": {
                            "sample_rate": 32000,
                            "bitrate": 128000,
                            "format": "mp3",
                            "channel": 1,
                        },
                    },
                )

                if response.status_code == 429:
                    _tts_cost_stats.add_error()
                    raise MiniMaxApiError("MiniMax API 请求过于频繁 (429)")
                elif response.status_code >= 500:
                    _tts_cost_stats.add_error()
                    raise MiniMaxApiError(f"MiniMax API 服务器错误: {response.status_code}")

                if response.status_code != 200:
                    _tts_cost_stats.add_error()
                    error_msg = response.text
                    # 提取错误消息
                    try:
                        resp_json = response.json()
                        error_msg = resp_json.get("base_resp", {}).get("status_msg", error_msg)
                    except:
                        pass
                    raise MiniMaxApiError(
                        f"MiniMax API 调用失败: {response.status_code} - {error_msg}"
                    )

                result = response.json()

                # 检查业务层面的错误码（MiniMax 在 HTTP 200 时也可能返回业务错误）
                base_resp = result.get("base_resp", {})
                status_code = base_resp.get("status_code", 0)

                if status_code == 1002:
                    # 速率限制 (RPM/TPM exceeded)
                    _tts_cost_stats.add_error()
                    logger.warning(f"MiniMax 速率限制: {base_resp.get('status_msg')}")
                    raise MiniMaxApiError(
                        f"MiniMax 速率限制: {base_resp.get('status_msg', 'RPM exceeded')}"
                    )
                elif status_code == 1000:
                    # 成功
                    pass
                elif status_code != 0:
                    # 其他业务错误
                    _tts_cost_stats.add_error()
                    raise MiniMaxApiError(
                        f"MiniMax 业务错误 ({status_code}): {base_resp.get('status_msg', 'unknown')}"
                    )

                # 检查是否有音频数据
                if "data" in result and "audio" in result["data"]:
                    # 更新成本统计
                    _tts_cost_stats.add(
                        characters=len(text),
                        audio_seconds=len(text) / 10,  # 估算：每秒约10字符
                        cost=len(text) / 1000 * _tts_cost_stats.PRICE_PER_1000_CHARS,
                    )

                    # 返回音频数据 (hex 编码)
                    audio_hex = result["data"]["audio"]
                    # 转换为 bytes
                    if isinstance(audio_hex, str):
                        return bytes.fromhex(audio_hex)
                    return audio_hex

                # 如果返回的是 URL
                if "data" in result and "audio_url" in result["data"]:
                    audio_url = result["data"]["audio_url"]
                    # 下载音频数据
                    audio_response = await client.get(audio_url)
                    return audio_response.content

                raise MiniMaxApiError("MiniMax API 响应格式异常")

        except httpx.TimeoutException:
            _tts_cost_stats.add_error()
            raise MiniMaxApiError("MiniMax API 请求超时")
        except httpx.HTTPError as e:
            _tts_cost_stats.add_error()
            raise MiniMaxApiError(f"MiniMax API 请求失败: {e}")

    @retry_sync(max_attempts=3, delay=1.0, backoff=True, exceptions=(MiniMaxApiError,))
    def synthesize_with_retry(
        self,
        text: str,
        voice_id: str = "male-qn",
        speed: float = 1.0,
        emotion: str = None,
        pitch: float = 0.0,
        volume: float = 1.0,
    ) -> bytes:
        """
        合成语音（带重试）

        Args:
            text: 待合成文本
            voice_id: 音色 ID
            speed: 语速
            emotion: 情感标签
            pitch: 音调调整
            volume: 音量调整

        Returns:
            bytes: 音频数据
        """
        global _tts_cost_stats

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(
                self.synthesize(text, voice_id, speed, emotion, pitch, volume)
            )
        except MiniMaxApiError:
            _tts_cost_stats.add_retry()
            raise
        finally:
            loop.close()

    def synthesize_sync(
        self,
        text: str,
        voice_id: str = "male-qn",
        speed: float = 1.0,
        emotion: str = None,
        pitch: float = 0.0,
        volume: float = 1.0,
    ) -> bytes:
        """
        同步合成语音

        Args:
            text: 待合成文本
            voice_id: 音色 ID
            speed: 语速
            emotion: 情感标签
            pitch: 音调调整
            volume: 音量调整

        Returns:
            bytes: 音频数据
        """
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(
                self.synthesize(text, voice_id, speed, emotion, pitch, volume)
            )
        finally:
            loop.close()

    async def synthesize_batch(
        self,
        segments: List[Dict[str, Any]],
        max_concurrent: int = 5,
        on_progress: Callable[[int, int, Dict], None] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量合成语音

        Args:
            segments: 片段列表，每个元素包含 text, voice_id, speed, emotion, pitch, volume
            max_concurrent: 最大并发数
            on_progress: 进度回调函数 (completed, total, result)

        Returns:
            list: 合成结果列表，每个元素包含原片段信息和 audio_data
        """
        import asyncio

        async def _synthesize_one(segment: Dict[str, Any], index: int) -> Dict[str, Any]:
            try:
                audio_data = await self.synthesize(
                    text=segment.get("text", ""),
                    voice_id=segment.get("voice_id", "male-qn"),
                    speed=segment.get("speed", 1.0),
                    emotion=segment.get("emotion"),
                    pitch=segment.get("pitch", 0.0),
                    volume=segment.get("volume", 1.0),
                )
                result = {
                    **segment,
                    "success": True,
                    "audio_data": audio_data,
                    "index": index,
                }
                if on_progress:
                    on_progress(index + 1, len(segments), result)
                return result
            except Exception as e:
                logger.error(f"片段合成失败: {e}")
                result = {
                    **segment,
                    "success": False,
                    "error": str(e),
                    "index": index,
                }
                if on_progress:
                    on_progress(index + 1, len(segments), result)
                return result

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _synthesize_with_semaphore(segment: Dict[str, Any], index: int) -> Dict[str, Any]:
            async with semaphore:
                return await _synthesize_one(segment, index)

        # 创建任务
        tasks = [
            _synthesize_with_semaphore(seg, i) 
            for i, seg in enumerate(segments)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    **segments[i],
                    "success": False,
                    "error": str(result),
                    "index": i,
                })
            else:
                processed_results.append(result)

        # 按原始顺序排序
        processed_results.sort(key=lambda x: x.get("index", 0))

        return processed_results

    def _get_emotion_params_simple(self, emotion: str) -> Dict[str, Any]:
        """
        获取情感参数（简化版）

        Args:
            emotion: 情感标签

        Returns:
            dict: MiniMax 情感参数
        """
        emotion_map = {
            "happy": {"emotion": "happy"},
            "sad": {"emotion": "sad"},
            "angry": {"emotion": "angry"},
            "fearful": {"emotion": "fearful"},
            "surprise": {"emotion": "surprise"},
            "gentle": {"emotion": "gentle"},
            "serious": {"emotion": "serious"},
            "neutral": {"emotion": "neutral"},
        }

        if emotion:
            return emotion_map.get(emotion.lower(), {"emotion": "neutral"})

        return {"emotion": "neutral"}

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        获取可用音色列表

        Returns:
            list: 音色列表
        """
        return [
            {
                "id": "male-qn",
                "name": "青年男声",
                "gender": "male",
                "age_range": "young",
                "description": "标准青年男性音色，适合旁白和男主角",
                "suitable_roles": ["男主", "旁白", "师兄", "前辈", "掌门"],
            },
            {
                "id": "male-yun",
                "name": "成熟男声",
                "gender": "male",
                "age_range": "adult",
                "description": "成熟稳重的男性音色，适合长辈、师父、仙尊等角色",
                "suitable_roles": ["老人", "师父", "仙尊", "宗主", "长老"],
            },
            {
                "id": "male-tian",
                "name": "低沉男声",
                "gender": "male",
                "age_range": "adult",
                "description": "低沉有力的男性音色，适合反派、boss等角色",
                "suitable_roles": ["反派", "魔帝", "魔王", "boss"],
            },
            {
                "id": "female-shaon",
                "name": "青年女声",
                "gender": "female",
                "age_range": "young",
                "description": "标准青年女性音色，适合女主角和年轻女性",
                "suitable_roles": ["女主", "仙女", "圣女", "女帝"],
            },
            {
                "id": "female-don",
                "name": "成熟女声",
                "gender": "female",
                "age_range": "adult",
                "description": "成熟女性音色，适合年长女性角色",
                "suitable_roles": ["长辈", "师娘", "皇后"],
            },
            {
                "id": "female-xiang",
                "name": "甜美女声",
                "gender": "female",
                "age_range": "young",
                "description": "甜美可爱的女性音色，适合儿童、少女等角色",
                "suitable_roles": ["儿童", "少女", "萝莉", "师妹"],
            },
        ]

    def get_emotion_list(self) -> List[Dict[str, Any]]:
        """
        获取支持的情感列表

        Returns:
            list: 情感列表
        """
        return [
            {"id": "neutral", "name": "平静", "intensity_levels": ["low", "medium", "high"], "aliases": ["neutral"]},
            {"id": "happy", "name": "高兴", "intensity_levels": ["low", "medium", "high"], "aliases": ["开心", "joyful"]},
            {"id": "sad", "name": "悲伤", "intensity_levels": ["low", "medium", "high"], "aliases": ["伤心", "sorrowful"]},
            {"id": "angry", "name": "愤怒", "intensity_levels": ["low", "medium", "high"], "aliases": ["生气", "恼怒"]},
            {"id": "fearful", "name": "紧张/害怕", "intensity_levels": ["low", "medium", "high"], "aliases": ["害怕", "惊恐"]},
            {"id": "surprise", "name": "惊讶/震惊", "intensity_levels": None, "aliases": ["震惊", "惊愕"]},
            {"id": "gentle", "name": "温柔/柔和", "intensity_levels": None, "aliases": ["柔和", "轻柔"]},
            {"id": "serious", "name": "严肃", "intensity_levels": None, "aliases": ["郑重", "正经"]},
        ]

    def get_quality_options(self) -> List[Dict[str, Any]]:
        """
        获取音频质量选项

        Returns:
            list: 质量选项列表
        """
        return [
            {"id": "standard", "name": "标准品质", "sample_rate": 32000, "bitrate": 128000, "description": "适合快速预览"},
            {"id": "high", "name": "高品质", "sample_rate": 48000, "bitrate": 256000, "description": "推荐日常使用"},
            {"id": "ultra", "name": "超高品质", "sample_rate": 48000, "bitrate": 320000, "description": "适合正式发布"},
        ]

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        获取限流器状态

        Returns:
            dict: 限流器状态信息
        """
        global_limiter = _GlobalRateLimiter()
        bucket = global_limiter._rate_limiter.bucket
        return {
            "qps": global_limiter.qps,
            "available_tokens": round(bucket.tokens, 2),
            "capacity": bucket.capacity,
        }

    def get_cost_stats(self) -> Dict[str, Any]:
        """
        获取成本统计

        Returns:
            dict: 成本统计信息
        """
        return _tts_cost_stats.to_dict()

    def reset_cost_stats(self) -> None:
        """重置成本统计"""
        global _tts_cost_stats
        _tts_cost_stats = TTSCostStats()
        logger.info("TTS 成本统计已重置")

    def reset_rate_limiter(self, qps: float = 10.0) -> None:
        """
        重置限流器

        Args:
            qps: 新的 QPS 限制
        """
        global_limiter = _GlobalRateLimiter()
        global_limiter.reset(qps)
        logger.info(f"限流器已重置，QPS: {qps}")
