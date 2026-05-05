# ===========================================
# Tasks Package
# ===========================================

"""
Celery tasks for AI 有声书工坊.

Background processing tasks for:
- task_pipeline: Main pipeline orchestration
- task_analyze: DeepSeek analysis
- task_synthesize: TTS synthesis
- task_postprocess: Audio post-processing
- task_publish: Publishing to channels
- task_watch: File watching
"""

from celery import shared_task

# Base classes
from .base import BasePipelineTask, AIAPITask, ParseTask, StorageTask

# Import tasks for registration
from .task_pipeline import (
    parse_epub,
    preprocess_chapter,
    preprocess_book,
    analyze_chapter,
    create_segments,
    synthesize_segment,
    postprocess_chapter,
    process_chapter,
    publish_book,
    generate_audiobook,
    generate_audiobook_simple,
    analyze_all_chapters,
    unify_and_map_characters,
    generate_chapter_audio,
    check_pipeline_status,
    retry_failed_chapters,
    get_pipeline_history,
    cancel_pipeline,
)

# Task-specific imports
from .task_analyze import *
from .task_synthesize import *
from .task_postprocess import *
from .task_publish import *
from .task_watch import *

__all__ = [
    # Base classes
    "BasePipelineTask",
    "AIAPITask",
    "ParseTask",
    "StorageTask",
    "shared_task",
    # Pipeline tasks
    "parse_epub",
    "preprocess_chapter",
    "preprocess_book",
    "analyze_chapter",
    "create_segments",
    "synthesize_segment",
    "postprocess_chapter",
    "process_chapter",
    "publish_book",
    "generate_audiobook",
    "generate_audiobook_simple",
    "analyze_all_chapters",
    "unify_and_map_characters",
    "generate_chapter_audio",
    "check_pipeline_status",
    "retry_failed_chapters",
    "get_pipeline_history",
    "cancel_pipeline",
]
