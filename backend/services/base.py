"""
Service 层基础模块

提供通用的服务结果封装。
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ServiceResult:
    """统一的服务结果封装"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def ok(cls, data: Any = None, metadata: Optional[Dict[str, Any]] = None) -> "ServiceResult":
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, metadata: Optional[Dict[str, Any]] = None) -> "ServiceResult":
        return cls(success=False, error=error, metadata=metadata)
