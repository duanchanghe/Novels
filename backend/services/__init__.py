# ===========================================
# 服务层模块
# ===========================================

"""
业务逻辑服务模块

包含所有核心业务逻辑：
- svc_epub_parser: EPUB 解析引擎
- svc_text_preprocessor: 文本预处理
- svc_deepseek_analyzer: DeepSeek 分析引擎
- svc_minimax_tts: MiniMax TTS 合成引擎
- svc_audio_postprocessor: 音频后处理
- svc_minio_storage: MinIO 存储服务
- svc_voice_mapper: 角色-音色映射
- svc_file_watcher: 文件夹监听服务
- svc_publisher: 自动发布引擎
"""

from .svc_minio_storage import MinioStorageService
from .svc_epub_parser import EPUBParserService
from .svc_text_preprocessor import TextPreprocessorService
from .svc_deepseek_analyzer import DeepSeekAnalyzerService
from .svc_minimax_tts import MiniMaxTTSService
from .svc_audio_postprocessor import AudioPostprocessorService
from .svc_voice_mapper import VoiceMapperService
from .svc_file_watcher import get_watcher_service, start_watcher, stop_watcher, MultiDirectoryWatcher
from .svc_publisher import PublisherService

__all__ = [
    "MinioStorageService",
    "EPUBParserService",
    "TextPreprocessorService",
    "DeepSeekAnalyzerService",
    "MiniMaxTTSService",
    "AudioPostprocessorService",
    "VoiceMapperService",
    "get_watcher_service",
    "start_watcher",
    "stop_watcher",
    "MultiDirectoryWatcher",
    "PublisherService",
]
