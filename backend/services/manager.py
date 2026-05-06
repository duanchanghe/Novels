"""
Service Manager - 服务生命周期管理
"""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger("audiobook.service_manager")


class ServiceManager:
    """服务注册中心（单例模式）"""

    _instance: Optional["ServiceManager"] = None
    _services: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
        return cls._instance

    def register(self, name: str, service: Any) -> None:
        """注册服务"""
        self._services[name] = service
        logger.debug(f"Registered service: {name}")

    def get(self, name: str) -> Optional[Any]:
        """获取服务"""
        return self._services.get(name)

    def get_or_init(self, name: str, factory_func):
        """获取或初始化服务"""
        if name not in self._services:
            self._services[name] = factory_func()
        return self._services[name]

    def initialize_all(self) -> Dict[str, bool]:
        """初始化所有服务"""
        results = {}
        for name, service in self._services.items():
            try:
                if hasattr(service, "initialize"):
                    service.initialize()
                results[name] = True
            except Exception as e:
                results[name] = False
                logger.error(f"Failed to initialize {name}: {e}")
        return results

    def health_check_all(self) -> Dict[str, bool]:
        """健康检查所有服务"""
        results = {}
        for name, service in self._services.items():
            try:
                results[name] = service.health_check() if hasattr(service, "health_check") else True
            except Exception:
                results[name] = False
        return results

    def clear(self) -> None:
        """清空所有服务"""
        self._services.clear()


_service_manager: Optional[ServiceManager] = None


def get_service_manager() -> ServiceManager:
    """获取全局服务管理器"""
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager
