"""
Service Factory - 服务工厂
"""

import logging

logger = logging.getLogger("audiobook.service_factory")


class ServiceFactory:
    """服务工厂类（懒加载单例模式）"""

    _instances = {}

    @classmethod
    def get_epub_parser(cls):
        if "epub_parser" not in cls._instances:
            from .svc_epub_parser import EPUBParserService
            cls._instances["epub_parser"] = EPUBParserService()
        return cls._instances["epub_parser"]

    @classmethod
    def get_text_preprocessor(cls):
        if "text_preprocessor" not in cls._instances:
            from .svc_text_preprocessor import TextPreprocessorService
            cls._instances["text_preprocessor"] = TextPreprocessorService()
        return cls._instances["text_preprocessor"]

    @classmethod
    def get_chapter_cleaner(cls):
        if "chapter_cleaner" not in cls._instances:
            from .svc_chapter_cleaner import ChapterTextCleaner
            cls._instances["chapter_cleaner"] = ChapterTextCleaner()
        return cls._instances["chapter_cleaner"]

    @classmethod
    def get_deepseek_analyzer(cls):
        if "deepseek_analyzer" not in cls._instances:
            from .svc_deepseek_analyzer import DeepSeekAnalyzerService
            cls._instances["deepseek_analyzer"] = DeepSeekAnalyzerService()
        return cls._instances["deepseek_analyzer"]

    @classmethod
    def get_minimax_tts(cls):
        if "minimax_tts" not in cls._instances:
            from .svc_minimax_tts import MiniMaxTTSService
            cls._instances["minimax_tts"] = MiniMaxTTSService()
        return cls._instances["minimax_tts"]

    @classmethod
    def get_audio_postprocessor(cls):
        if "audio_postprocessor" not in cls._instances:
            try:
                from .svc_audio_postprocessor import AudioPostprocessorService
                cls._instances["audio_postprocessor"] = AudioPostprocessorService()
            except ImportError:
                logger.warning("AudioPostprocessorService not available (pydub issue)")
                return None
        return cls._instances["audio_postprocessor"]

    @classmethod
    def get_minio_storage(cls):
        if "minio_storage" not in cls._instances:
            from .svc_minio_storage import MinioStorageService
            cls._instances["minio_storage"] = MinioStorageService()
        return cls._instances["minio_storage"]

    @classmethod
    def get_voice_mapper(cls):
        if "voice_mapper" not in cls._instances:
            from .svc_voice_mapper import VoiceMapperService
            cls._instances["voice_mapper"] = VoiceMapperService()
        return cls._instances["voice_mapper"]

    @classmethod
    def get_file_watcher(cls):
        if "file_watcher" not in cls._instances:
            from .svc_file_watcher import get_watcher_service
            cls._instances["file_watcher"] = get_watcher_service()
        return cls._instances["file_watcher"]

    @classmethod
    def get_publisher(cls):
        if "publisher" not in cls._instances:
            from .svc_publisher import PublisherService
            cls._instances["publisher"] = PublisherService()
        return cls._instances["publisher"]

    @classmethod
    def clear_cache(cls):
        cls._instances.clear()
