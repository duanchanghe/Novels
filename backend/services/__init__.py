# ===========================================
# Services Package
# ===========================================

"""
Business logic services for AI 有声书工坊.

Service architecture:
- base.py: Abstract interfaces and base classes
- factory.py: Service factory for dependency injection
- manager.py: Service lifecycle management

Core services:
- svc_epub_parser: EPUB parsing engine
- svc_chapter_cleaner: Chapter text cleaning
- svc_text_preprocessor: Text preprocessing
- svc_deepseek_analyzer: DeepSeek AI analysis
- svc_minimax_tts: MiniMax TTS synthesis
- svc_audio_postprocessor: Audio post-processing
- svc_minio_storage: MinIO object storage
- svc_voice_mapper: Character-voice mapping
- svc_file_watcher: Directory watching
- svc_publisher: Auto-publishing
"""

# Base classes and interfaces
from .base import (
    ServiceType,
    ServiceResult,
    BaseService,
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

# Service factory
from .factory import ServiceFactory

# Service manager
from .manager import ServiceManager, get_service_manager, get_services

# Core services - lazy imports via factory
from .svc_minio_storage import MinioStorageService
from .svc_epub_parser import EPUBParserService
from .svc_chapter_cleaner import ChapterTextCleaner, clean_chapter_text, clean_chapter_with_report
from .svc_text_preprocessor import TextPreprocessorService
from .svc_deepseek_analyzer import DeepSeekAnalyzerService
from .svc_minimax_tts import MiniMaxTTSService
from .svc_voice_mapper import VoiceMapperService
from .svc_file_watcher import get_watcher_service, start_watcher, stop_watcher, MultiDirectoryWatcher
from .svc_publisher import PublisherService

# Audio postprocessor with fallback
try:
    from .svc_audio_postprocessor import AudioPostprocessorService
    _AudioPostprocessorService = AudioPostprocessorService
except ImportError:
    _AudioPostprocessorService = None
    AudioPostprocessorService = None


def get_audio_postprocessor():
    """Get audio postprocessor service with fallback."""
    if _AudioPostprocessorService is None:
        raise ImportError("AudioPostprocessorService requires pydub with audioop support")
    return _AudioPostprocessorService()


def initialize_services() -> dict:
    """
    Initialize all services.

    Returns:
        dict: Initialization results for each service type
    """
    manager = get_service_manager()

    # Register services
    manager.register(ServiceType.MINIO_STORAGE, ServiceFactory.get_minio_storage())
    manager.register(ServiceType.EPUB_PARSER, ServiceFactory.get_epub_parser())
    manager.register(ServiceType.TEXT_PREPROCESSOR, ServiceFactory.get_text_preprocessor())
    manager.register(ServiceType.DEEPSEEK_ANALYZER, ServiceFactory.get_deepseek_analyzer())
    manager.register(ServiceType.MINIMAX_TTS, ServiceFactory.get_minimax_tts())

    audio_pp = ServiceFactory.get_audio_postprocessor()
    if audio_pp:
        manager.register(ServiceType.AUDIO_POSTPROCESSOR, audio_pp)

    manager.register(ServiceType.VOICE_MAPPER, ServiceFactory.get_voice_mapper())
    manager.register(ServiceType.FILE_WATCHER, ServiceFactory.get_file_watcher())
    manager.register(ServiceType.PUBLISHER, ServiceFactory.get_publisher())

    return manager.initialize_all()


def health_check_services() -> dict:
    """
    Run health check on all services.

    Returns:
        dict: Health status for each service type
    """
    return get_service_manager().health_check_all()


__all__ = [
    # Base classes
    "ServiceType",
    "ServiceResult",
    "BaseService",
    "IStorageService",
    "IEpubParserService",
    "ITextProcessorService",
    "IAnalyzerService",
    "ITTSService",
    "IAudioPostprocessorService",
    "IVoiceMapperService",
    "IFileWatcherService",
    "IPublisherService",
    # Factory and manager
    "ServiceFactory",
    "ServiceManager",
    "get_service_manager",
    "get_services",
    # Services
    "MinioStorageService",
    "EPUBParserService",
    "TextPreprocessorService",
    "DeepSeekAnalyzerService",
    "MiniMaxTTSService",
    "AudioPostprocessorService",
    "VoiceMapperService",
    "PublisherService",
    "get_audio_postprocessor",
    # File watcher
    "get_watcher_service",
    "start_watcher",
    "stop_watcher",
    "MultiDirectoryWatcher",
    # Chapter cleaner
    "ChapterTextCleaner",
    "clean_chapter_text",
    "clean_chapter_with_report",
    # Utilities
    "initialize_services",
    "health_check_services",
]
