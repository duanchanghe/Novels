# ===========================================
# Service Base Classes
# ===========================================

"""
Base classes and interfaces for service layer.

Provides abstract base classes for all services following
the Dependency Inversion Principle (DIP) from SOLID.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging


class ServiceType(Enum):
    """Service type enumeration."""
    EPUB_PARSER = "epub_parser"
    TEXT_PREPROCESSOR = "text_preprocessor"
    CHAPTER_CLEANER = "chapter_cleaner"
    DEEPSEEK_ANALYZER = "deepseek_analyzer"
    MINIMAX_TTS = "minimax_tts"
    AUDIO_POSTPROCESSOR = "audio_postprocessor"
    MINIO_STORAGE = "minio_storage"
    VOICE_MAPPER = "voice_mapper"
    FILE_WATCHER = "file_watcher"
    PUBLISHER = "publisher"
    MONITOR = "monitor"


@dataclass
class ServiceResult:
    """Standard service result wrapper."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def ok(cls, data: Any = None, metadata: Optional[Dict[str, Any]] = None) -> "ServiceResult":
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, metadata: Optional[Dict[str, Any]] = None) -> "ServiceResult":
        """Create a failed result."""
        return cls(success=False, error=error, metadata=metadata)


class BaseService(ABC):
    """
    Abstract base class for all services.

    Provides common functionality like logging and configuration access.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"audiobook.{self.__class__.__name__}")
        self._initialized = False

    @property
    @abstractmethod
    def service_type(self) -> ServiceType:
        """Return the service type."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the service."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is healthy."""
        pass

    def ensure_initialized(self) -> None:
        """Ensure service is initialized before use."""
        if not self._initialized:
            self.initialize()
            self._initialized = True


class IStorageService(ABC):
    """Interface for storage services."""

    @abstractmethod
    def upload_file(self, bucket: str, file_path: str, object_name: str) -> ServiceResult:
        pass

    @abstractmethod
    def download_file(self, bucket: str, object_name: str, file_path: str) -> ServiceResult:
        pass

    @abstractmethod
    def delete_file(self, bucket: str, object_name: str) -> ServiceResult:
        pass

    @abstractmethod
    def get_presigned_url(self, bucket: str, object_name: str, expiry: int = 3600) -> ServiceResult:
        pass


class IEpubParserService(ABC):
    """Interface for EPUB parsing services."""

    @abstractmethod
    def parse_file(self, file_path: str, book_id: Optional[int] = None) -> ServiceResult:
        pass

    @abstractmethod
    def parse_bytes(self, data: bytes, book_id: Optional[int] = None) -> ServiceResult:
        pass


class ITextProcessorService(ABC):
    """Interface for text processing services."""

    @abstractmethod
    def preprocess(self, text: str, options: Optional[Dict[str, Any]] = None) -> ServiceResult:
        pass

    @abstractmethod
    def clean(self, text: str) -> ServiceResult:
        pass


class IAnalyzerService(ABC):
    """Interface for AI analysis services."""

    @abstractmethod
    def analyze_chapter(self, chapter_id: int) -> ServiceResult:
        pass

    @abstractmethod
    def analyze_text(self, text: str, analysis_type: str) -> ServiceResult:
        pass


class ITTSService(ABC):
    """Interface for text-to-speech services."""

    @abstractmethod
    def synthesize(self, text: str, voice_id: str, options: Optional[Dict[str, Any]] = None) -> ServiceResult:
        pass

    @abstractmethod
    def synthesize_chapter(self, chapter_id: int) -> ServiceResult:
        pass


class IAudioPostprocessorService(ABC):
    """Interface for audio post-processing services."""

    @abstractmethod
    def concatenate(self, audio_paths: List[str], output_path: str) -> ServiceResult:
        pass

    @abstractmethod
    def normalize(self, audio_path: str, output_path: str, level_db: float = -20.0) -> ServiceResult:
        pass

    @abstractmethod
    def add_metadata(self, audio_path: str, metadata: Dict[str, Any]) -> ServiceResult:
        pass


class IVoiceMapperService(ABC):
    """Interface for voice mapping services."""

    @abstractmethod
    def map_character(self, character_name: str, book_id: int) -> ServiceResult:
        pass

    @abstractmethod
    def get_voice_profile(self, character_name: str, book_id: int) -> Optional[Dict[str, Any]]:
        pass


class IFileWatcherService(ABC):
    """Interface for file watching services."""

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def is_running(self) -> bool:
        pass


class IPublisherService(ABC):
    """Interface for publishing services."""

    @abstractmethod
    def publish(self, book_id: int, channels: List[str]) -> ServiceResult:
        pass

    @abstractmethod
    def get_supported_channels(self) -> List[str]:
        pass
