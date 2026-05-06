"""
Service 层 - 核心服务模块
"""

from .base import ServiceResult
from .factory import ServiceFactory
from .manager import ServiceManager, get_service_manager

# 服务初始化
def initialize_services() -> dict:
    """初始化所有服务"""
    manager = get_service_manager()
    manager.register("minio_storage", ServiceFactory.get_minio_storage())
    manager.register("epub_parser", ServiceFactory.get_epub_parser())
    manager.register("text_preprocessor", ServiceFactory.get_text_preprocessor())
    manager.register("deepseek_analyzer", ServiceFactory.get_deepseek_analyzer())
    manager.register("minimax_tts", ServiceFactory.get_minimax_tts())
    manager.register("voice_mapper", ServiceFactory.get_voice_mapper())
    manager.register("file_watcher", ServiceFactory.get_file_watcher())
    manager.register("publisher", ServiceFactory.get_publisher())
    return manager.initialize_all()


def health_check_services() -> dict:
    """健康检查所有服务"""
    return get_service_manager().health_check_all()


__all__ = [
    "ServiceResult",
    "ServiceFactory",
    "ServiceManager",
    "get_service_manager",
    "initialize_services",
    "health_check_services",
]
