# ===========================================
# 文件处理工具
# ===========================================

"""
文件处理工具模块

提供文件校验和哈希计算工具。
"""

import hashlib
import os
import re
from typing import Optional, Tuple


def calculate_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """
    计算文件哈希值

    Args:
        file_path: 文件路径
        algorithm: 哈希算法 (md5, sha1, sha256)

    Returns:
        str: 哈希值（小写十六进制）
    """
    hash_func = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def calculate_bytes_hash(data: bytes, algorithm: str = "md5") -> str:
    """
    计算字节数据的哈希值

    Args:
        data: 字节数据
        algorithm: 哈希算法

    Returns:
        str: 哈希值
    """
    hash_func = hashlib.new(algorithm)
    hash_func.update(data)
    return hash_func.hexdigest()


def validate_file_type(filename: str, allowed_extensions: list = None) -> Tuple[bool, Optional[str]]:
    """
    验证文件类型

    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表

    Returns:
        tuple: (是否有效, 错误信息)
    """
    if allowed_extensions is None:
        allowed_extensions = [".epub"]

    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext not in allowed_extensions:
        return False, f"不支持的文件类型: {ext}"

    return True, None


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符

    Args:
        filename: 原始文件名

    Returns:
        str: 清理后的文件名
    """
    # 移除非法字符
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)

    # 移除控制字符
    filename = re.sub(r"[\x00-\x1f]", "", filename)

    # 限制长度
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext

    return filename


def get_file_size_mb(file_path: str) -> float:
    """
    获取文件大小（MB）

    Args:
        file_path: 文件路径

    Returns:
        float: 文件大小（MB）
    """
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)
