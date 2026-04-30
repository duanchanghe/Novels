# ===========================================
# DeepSeek 分析服务
# ===========================================

"""
DeepSeek 分析服务

调用 DeepSeek API 进行文本分析，包括：
- 角色识别
- 情感标注
- 多音字消歧
- 段落拆分
"""

import json
import logging
from typing import Dict, List, Any, Optional

import httpx

from core.config import settings
from core.exceptions import DeepSeekApiError


logger = logging.getLogger("audiobook")


class DeepSeekAnalyzerService:
    """
    DeepSeek 分析服务

    提供文本智能分析功能。
    """

    # 角色识别 Prompt 模板
    ROLE_RECOGNITION_PROMPT = """你是有声书文本分析专家。请分析以下小说文本，完成：

1. 将文本按段落编号
2. 标记每段是"旁白/描写"还是"对话/独白/心理活动"
3. 如果是对话，判断说话人身份（角色名或"未识别"）
   - 注意：同一角色在不同段落可能使用不同称呼（如"张三"/"张兄"/"三哥"），请合并为同一角色名
4. 判断每段的情感基调（平静/高兴/悲伤/愤怒/紧张/惊讶/温柔/严肃）
   - 情感强度：low/medium/high
5. 识别段中可能的多音字并给出正确读音

角色清单（如果已知）：{role_list}

输出格式：严格 JSON 数组
[{{"paragraph_index": 1, "text": "...", "type": "narration|dialogue", "speaker": "旁白|角色名", "emotion": "emotion_intensity", "polyphone_fixes": [["字", "拼音"]]}}]

文本内容：
{text}
"""

    # 文本标准化 Prompt
    TEXT_NORMALIZATION_PROMPT = """你是有声书文本标准化专家。请对以下小说文本进行处理：

1. 数字转朗读格式："2024年"→"二零二四年"，"3月5日"→"三月五日"
2. 英文单词判断是否需要朗读或保留原文
3. 特殊符号处理：破折号→停顿、省略号→拖音
4. 人名/地名/Jargon 保持原样并标注

输出格式：仅返回处理后的文本，不改变原文结构和标点

文本内容：
{text}
"""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        self.max_tokens = settings.DEEPSEEK_MAX_TOKENS
        self.temperature = settings.DEEPSEEK_TEMPERATURE

    async def analyze_text(self, text: str, role_list: List[str] = None) -> Dict[str, Any]:
        """
        分析文本

        Args:
            text: 待分析文本
            role_list: 已知的角色列表

        Returns:
            dict: 分析结果
        """
        if not self.api_key:
            raise DeepSeekApiError("DeepSeek API Key 未配置")

        prompt = self.ROLE_RECOGNITION_PROMPT.format(
            text=text,
            role_list=", ".join(role_list) if role_list else "未知",
        )

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                    },
                )

                if response.status_code != 200:
                    raise DeepSeekApiError(
                        f"DeepSeek API 调用失败: {response.status_code} - {response.text}"
                    )

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # 解析 JSON 响应
                analysis = json.loads(content)

                # 提取角色列表
                characters = self._extract_characters(analysis)

                return {
                    "paragraphs": analysis,
                    "characters": characters,
                    "token_usage": result.get("usage", {}),
                }

        except httpx.TimeoutException:
            raise DeepSeekApiError("DeepSeek API 请求超时")
        except httpx.HTTPError as e:
            raise DeepSeekApiError(f"DeepSeek API 请求失败: {e}")
        except json.JSONDecodeError as e:
            raise DeepSeekApiError(f"DeepSeek 响应 JSON 解析失败: {e}")

    def analyze_chapter(self, text: str, role_list: List[str] = None) -> Dict[str, Any]:
        """
        同步分析章节（用于 Celery 任务）

        Args:
            text: 章节文本
            role_list: 已知角色列表

        Returns:
            dict: 分析结果
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.analyze_text(text, role_list))

    def _extract_characters(self, analysis: List[Dict]) -> List[Dict[str, Any]]:
        """
        从分析结果中提取角色列表

        Args:
            analysis: 分析结果

        Returns:
            list: 角色列表
        """
        characters = {}
        speakers = set()

        for item in analysis:
            speaker = item.get("speaker")
            if speaker and speaker != "旁白" and speaker != "未识别":
                speakers.add(speaker)

        # 构建角色列表
        for speaker in speakers:
            characters[speaker] = {
                "name": speaker,
                "dialogue_count": sum(
                    1 for item in analysis if item.get("speaker") == speaker
                ),
            }

        return list(characters.values())

    def normalize_text(self, text: str) -> str:
        """
        标准化文本

        Args:
            text: 原始文本

        Returns:
            str: 标准化后的文本
        """
        prompt = self.TEXT_NORMALIZATION_PROMPT.format(text=text)

        try:
            import requests

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": self.max_tokens,
                },
                timeout=60,
            )

            if response.status_code != 200:
                raise DeepSeekApiError(f"DeepSeek API 调用失败: {response.status_code}")

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"文本标准化失败: {e}")
            return text
