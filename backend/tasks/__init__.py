# ===========================================
# Celery 异步任务模块
# ===========================================

"""
Celery 异步任务模块

包含所有后台异步任务：
- task_analyze: DeepSeek 文本分析任务
- task_synthesize: MiniMax TTS 合成任务
- task_postprocess: 音频后处理任务
- task_publish: 自动发布任务
- task_watch: 文件夹监听兜底任务
"""

from .celery_app import celery_app
from .task_analyze import *
from .task_synthesize import *
from .task_postprocess import *
from .task_publish import *
from .task_watch import *

__all__ = ["celery_app"]
