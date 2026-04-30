# ===========================================
# MiniMax TTS 服务
# ===========================================

"""
MiniMax TTS 服务

调用 MiniMax API 进行语音合成。
"""

import logging
from typing import Optional, Dict, Any

import httpx

from core.config import settings
from core.exceptions import MiniMaxApiError


logger = logging.getLogger("audiobook")


class MiniMaxTTSService:
    """
    MiniMax TTS 服务

    提供语音合成功能。
    """

    # 可用音色映射
    VOICE_MAP = {
        # 旁白
        "narrator": "male-qn",
        "male-narrator": "male-qn",
        "female-narrator": "female-shaon",
        # 男性
        "male": "male-qn",
        "male-young": "male-qn",
        "male-elderly": "male-yun",
        "male-deep": "male-tian",
        # 女性
        "female": "female-shaon",
        "female-young": "female-shaon",
        "female-elderly": "female-don",
        "female-child": "female-xiang",
        # 默认
        "default": "male-qn",
    }

    def __init__(self):
        self.api_key = settings.MINIMAX_API_KEY
        self.api_host = settings.MINIMAX_API_HOST
        self.group_id = settings.MINIMAX_GROUP_ID

    async def synthesize(
        self,
        text: str,
        voice_id: str = "male-qn",
        speed: float = 1.0,
        emotion: str = None,
    ) -> bytes:
        """
        合成语音

        Args:
            text: 待合成文本
            voice_id: 音色 ID
            speed: 语速（0.5-2.0）
            emotion: 情感标签

        Returns:
            bytes: 音频数据（MP3 格式）

        Raises:
            MiniMaxApiError: 合成失败时抛出
        """
        if not self.api_key:
            raise MiniMaxApiError("MiniMax API Key 未配置")

        # 映射音色 ID
        mapped_voice_id = self.VOICE_MAP.get(voice_id, voice_id)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.api_host}/v1/t2a_v2",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "speech-01-turbo",
                        "text": text,
                        "voice_setting": {
                            "voice_id": mapped_voice_id,
                            "speed": speed,
                        },
                        "emotion_setting": self._get_emotion_params(emotion),
                    },
                )

                if response.status_code != 200:
                    raise MiniMaxApiError(
                        f"MiniMax API 调用失败: {response.status_code} - {response.text}"
                    )

                result = response.json()

                # 检查是否有音频数据
                if "data" in result and "audio_file" in result["data"]:
                    # 返回音频 URL 或直接数据
                    return result["data"]["audio_file"]

                # 如果返回的是 URL
                if "data" in result and "audio_url" in result["data"]:
                    audio_url = result["data"]["audio_url"]
                    # 下载音频数据
                    audio_response = await client.get(audio_url)
                    return audio_response.content

                raise MiniMaxApiError("MiniMax API 响应格式异常")

        except httpx.TimeoutException:
            raise MiniMaxApiError("MiniMax API 请求超时")
        except httpx.HTTPError as e:
            raise MiniMaxApiError(f"MiniMax API 请求失败: {e}")

    def synthesize_sync(
        self,
        text: str,
        voice_id: str = "male-qn",
        speed: float = 1.0,
        emotion: str = None,
    ) -> bytes:
        """
        同步合成语音

        Args:
            text: 待合成文本
            voice_id: 音色 ID
            speed: 语速
            emotion: 情感标签

        Returns:
            bytes: 音频数据
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.synthesize(text, voice_id, speed, emotion))

    def _get_emotion_params(self, emotion: str) -> Dict[str, Any]:
        """
        获取情感参数

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
            "neutral": {"emotion": "neutral"},
        }

        if emotion:
            return emotion_map.get(emotion.lower(), {"emotion": "neutral"})

        return {"emotion": "neutral"}

    def get_available_voices(self) -> list:
        """
        获取可用音色列表

        Returns:
            list: 音色列表
        """
        return [
            {"id": "male-qn", "name": "青年男声", "gender": "male"},
            {"id": "male-yun", "name": "成熟男声", "gender": "male"},
            {"id": "male-tian", "name": "低沉男声", "gender": "male"},
            {"id": "female-shaon", "name": "青年女声", "gender": "female"},
            {"id": "female-don", "name": "成熟女声", "gender": "female"},
            {"id": "female-xiang", "name": "甜美女声", "gender": "female"},
        ]
