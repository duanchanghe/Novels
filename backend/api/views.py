# ===========================================
# API Views - 向后兼容层
# ===========================================

"""
向后兼容层

保留旧的 ViewSet 接口以便现有代码继续工作。
新代码应使用 api.views 子模块中的视图类。
"""

# 为了向后兼容，从子模块导入所有视图
from .views import (
    # Health
    HealthCheckView,
    # Books
    BookListView,
    BookDetailView,
    BookChaptersView,
    BookStatusView,
    BookGenerateView,
    BookRetryView,
    BookAudioView,
    BookDownloadView,
    BookDeleteView,
    # Chapters
    ChapterDetailView,
    ChapterConfirmView,
    ChapterRetryView,
    ChapterSegmentsView,
    # Upload
    UploadView,
    PresignedUrlView,
    # Voices
    VoiceListView,
    EmotionListView,
    RoleMappingView,
    RateLimitView,
    CacheStatsView,
    VoiceRecommendView,
    # Publish
    PublishChannelListView,
    PublishChannelCreateView,
    PublishChannelDetailView,
    PublishBookView,
    PublishStatusView,
    PublishRecordView,
    PublishRecordListView,
    # Watch
    WatchStatusView,
    WatchRestartView,
    WatchHistoryView,
)

# 重新导出以便旧代码可以导入
__all__ = [
    "HealthCheckView",
    # Books - 兼容旧命名
    "BookListView",
    "BookDetailView",
    "BookChaptersView",
    "BookStatusView",
    "BookGenerateView",
    "BookRetryView",
    "BookAudioView",
    "BookDownloadView",
    "BookDeleteView",
    # Chapters - 兼容旧命名
    "ChapterDetailView",
    "ChapterConfirmView",
    "ChapterRetryView",
    "ChapterSegmentsView",
    # Upload - 兼容旧命名
    "UploadView",
    "PresignedUrlView",
    # Voices - 兼容旧命名
    "VoiceListView",
    "EmotionListView",
    "RoleMappingView",
    "RateLimitView",
    "CacheStatsView",
    "VoiceRecommendView",
    # Publish - 兼容旧命名
    "PublishChannelListView",
    "PublishChannelCreateView",
    "PublishChannelDetailView",
    "PublishBookView",
    "PublishStatusView",
    "PublishRecordView",
    "PublishRecordListView",
    # Watch - 兼容旧命名
    "WatchStatusView",
    "WatchRestartView",
    "WatchHistoryView",
]

# 为了向后兼容，定义 ViewSet 别名（这些在旧的 urls.py 中使用）
# 注意：这些实际上是 APIView，不是 ViewSet

# 兼容旧的路由注册方式（使用 router.register）
# 如果旧代码使用 BookViewSet.as_view()，我们需要提供
class CompatibleMixin:
    """兼容混入类"""
    pass
