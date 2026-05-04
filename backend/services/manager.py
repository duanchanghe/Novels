# ===========================================
# Service Manager
# ===========================================

"""
Unified service manager for dependency injection and lifecycle management.

Provides a central registry for all services with lazy initialization
and dependency injection support.
"""

import logging
from typing import Dict, Type, Optional, Any
from functools import lru_cache

from .base import (
    BaseService,
    ServiceType,
    ServiceResult,
    IStorageService,
    IEpubParserService,
    ITextProcessorService,
    IAnalyzerService,
    ITTSService,
    IAudioPostprocessorService,
    IVoiceMapperService,
    IFileWatcherService,
    IPublisherService,
)


logger = logging.getLogger("audiobook.service_manager")


class ServiceManager:
    """
    Central service registry and lifecycle manager.

    Implements lazy initialization and singleton pattern for services.
    """

    _instance: Optional["ServiceManager"] = None
    _services: Dict[ServiceType, BaseService] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._services = {}
            self._initialized = True

    def register(self, service_type: ServiceType, service: BaseService) -> None:
        """Register a service instance."""
        self._services[service_type] = service
        logger.debug(f"Registered service: {service_type.value}")

    def get(self, service_type: ServiceType) -> Optional[BaseService]:
        """Get a registered service instance."""
        return self._services.get(service_type)

    def get_storage(self) -> Optional[IStorageService]:
        """Get storage service."""
        return self.get(ServiceType.MINIO_STORAGE)

    def get_epub_parser(self) -> Optional[IEpubParserService]:
        """Get EPUB parser service."""
        return self.get(ServiceType.EPUB_PARSER)

    def get_text_processor(self) -> Optional[ITextProcessorService]:
        """Get text processor service."""
        return self.get(ServiceType.TEXT_PREPROCESSOR)

    def get_analyzer(self) -> Optional[IAnalyzerService]:
        """Get analyzer service."""
        return self.get(ServiceType.DEEPSEEK_ANALYZER)

    def get_tts(self) -> Optional[ITTSService]:
        """Get TTS service."""
        return self.get(ServiceType.MINIMAX_TTS)

    def get_audio_postprocessor(self) -> Optional[IAudioPostprocessorService]:
        """Get audio postprocessor service."""
        return self.get(ServiceType.AUDIO_POSTPROCESSOR)

    def get_voice_mapper(self) -> Optional[IVoiceMapperService]:
        """Get voice mapper service."""
        return self.get(ServiceType.VOICE_MAPPER)

    def get_file_watcher(self) -> Optional[IFileWatcherService]:
        """Get file watcher service."""
        return self.get(ServiceType.FILE_WATCHER)

    def get_publisher(self) -> Optional[IPublisherService]:
        """Get publisher service."""
        return self.get(ServiceType.PUBLISHER)

    def initialize_all(self) -> Dict[str, bool]:
        """Initialize all registered services."""
        results = {}
        for service_type, service in self._services.items():
            try:
                service.initialize()
                results[service_type.value] = True
                logger.info(f"Initialized service: {service_type.value}")
            except Exception as e:
                results[service_type.value] = False
                logger.error(f"Failed to initialize {service_type.value}: {e}")
        return results

    def health_check_all(self) -> Dict[str, bool]:
        """Run health check on all services."""
        results = {}
        for service_type, service in self._services.items():
            try:
                results[service_type.value] = service.health_check()
            except Exception as e:
                results[service_type.value] = False
                logger.error(f"Health check failed for {service_type.value}: {e}")
        return results

    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        logger.info("Cleared all services")


# Global instance
_service_manager: Optional[ServiceManager] = None


def get_service_manager() -> ServiceManager:
    """Get the global service manager instance."""
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager


def get_services() -> Dict[ServiceType, BaseService]:
    """Get all registered services."""
    return get_service_manager()._services.copy()
