# ===========================================
# 音频处理工具
# ===========================================

"""
音频处理工具模块

提供音频相关的辅助函数。
"""

import os
from io import BytesIO
from typing import Optional

from pydub import AudioSegment


def calculate_audio_duration(audio_data: bytes) -> float:
    """
    计算音频时长

    Args:
        audio_data: 音频数据

    Returns:
        float: 时长（秒）
    """
    try:
        audio = AudioSegment.from_mp3(BytesIO(audio_data))
        return len(audio) / 1000.0  # 转换为秒
    except Exception:
        return 0.0


def normalize_audio_path(path: str) -> str:
    """
    规范化音频文件路径

    Args:
        path: 原始路径

    Returns:
        str: 规范化后的路径
    """
    # 移除多余的斜杠
    path = os.path.normpath(path)

    # 替换反斜杠
    path = path.replace("\\", "/")

    return path


def get_audio_format(file_path: str) -> str:
    """
    获取音频文件格式

    Args:
        file_path: 文件路径

    Returns:
        str: 音频格式（小写）
    """
    _, ext = os.path.splitext(file_path)
    return ext.lstrip(".").lower()


def format_duration(seconds: float) -> str:
    """
    格式化时长为人类可读格式

    Args:
        seconds: 秒数

    Returns:
        str: 格式化后的时长 (HH:MM:SS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"
