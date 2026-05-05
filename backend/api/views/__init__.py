# ===========================================
# API Views - 模块导出
# ===========================================

"""
API 视图模块

包含：
- health.py: 健康检查
- books.py: 书籍管理
- chapters.py: 章节管理
- upload.py: 文件上传
- voices.py: 音色管理
- publish.py: 发布管理
- watch.py: 文件监听
"""

from .health import HealthCheckView
from .books import (
    BookListView,
    BookDetailView,
    BookChaptersView,
    BookStatusView,
    BookGenerateView,
    BookRetryView,
    BookAudioView,
    BookDownloadView,
    BookSubtitleView,
    BookDeleteView,
    BookStopAllView,
)
from .chapters import (
    ChapterDetailView,
    ChapterConfirmView,
    ChapterRetryView,
    ChapterSegmentsView,
)
from .upload import UploadView, PresignedUrlView
from .voices import (
    VoiceListView,
    EmotionListView,
    RoleMappingView,
    RateLimitView,
    CacheStatsView,
    VoiceRecommendView,
)
from .publish import (
    PublishChannelListView,
    PublishChannelCreateView,
    PublishChannelDetailView,
    PublishBookView,
    PublishStatusView,
    PublishRecordView,
    PublishRecordListView,
)
from .watch import (
    WatchStatusView,
    WatchRestartView,
    WatchHistoryView,
)

__all__ = [
    # Health
    "HealthCheckView",
    # Books
    "BookListView",
    "BookDetailView",
    "BookChaptersView",
    "BookStatusView",
    "BookGenerateView",
    "BookRetryView",
    "BookAudioView",
    "BookDownloadView",
    "BookDeleteView",
    "BookStopAllView",
    # Chapters
    "ChapterDetailView",
    "ChapterConfirmView",
    "ChapterRetryView",
    "ChapterSegmentsView",
    # Upload
    "UploadView",
    "PresignedUrlView",
    # Voices
    "VoiceListView",
    "EmotionListView",
    "RoleMappingView",
    "RateLimitView",
    "CacheStatsView",
    "VoiceRecommendView",
    # Publish
    "PublishChannelListView",
    "PublishChannelCreateView",
    "PublishChannelDetailView",
    "PublishBookView",
    "PublishStatusView",
    "PublishRecordView",
    "PublishRecordListView",
    # Watch
    "WatchStatusView",
    "WatchRestartView",
    "WatchHistoryView",
]
