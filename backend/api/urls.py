# ===========================================
# API URLs - 向后兼容版
# ===========================================

"""
API URL Configuration - 向后兼容版

保留旧的路由格式以确保向后兼容。
新代码应使用清晰的 RESTful 路由。
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# 导入新的视图
from .views import (
    HealthCheckView,
    BookListView,
    BookDetailView,
    BookChaptersView,
    BookStatusView,
    BookGenerateView,
    BookRetryView,
    BookAudioView,
    BookDownloadView,
    BookDeleteView,
    ChapterDetailView,
    ChapterConfirmView,
    ChapterRetryView,
    ChapterSegmentsView,
    UploadView,
    PresignedUrlView,
    VoiceListView,
    EmotionListView,
    RoleMappingView,
    RateLimitView,
    CacheStatsView,
    VoiceRecommendView,
    PublishChannelListView,
    PublishChannelCreateView,
    PublishChannelDetailView,
    PublishBookView,
    PublishStatusView,
    PublishRecordView,
    PublishRecordListView,
    WatchStatusView,
    WatchRestartView,
    WatchHistoryView,
)

# 使用简单的 URL 配置
urlpatterns = [
    # ===========================================
    # Health Check
    # ===========================================
    path('health/', HealthCheckView.as_view(), name='health'),

    # ===========================================
    # Books API
    # ===========================================
    path('books/', BookListView.as_view(), name='book-list'),
    path('books/<int:pk>/', BookDetailView.as_view(), name='book-detail'),
    path('books/<int:pk>/chapters/', BookChaptersView.as_view(), name='book-chapters'),
    path('books/<int:pk>/status/', BookStatusView.as_view(), name='book-status'),
    path('books/<int:pk>/generate/', BookGenerateView.as_view(), name='book-generate'),
    path('books/<int:pk>/retry/', BookRetryView.as_view(), name='book-retry'),
    path('books/<int:pk>/audio/', BookAudioView.as_view(), name='book-audio'),
    path('books/<int:pk>/download/', BookDownloadView.as_view(), name='book-download'),
    path('books/<int:pk>/delete/', BookDeleteView.as_view(), name='book-delete'),
    path('books/<int:pk>/voice-recommend/', VoiceRecommendView.as_view(), name='book-voice-recommend'),
    path('books/<int:pk>/publish/', PublishBookView.as_view(), name='book-publish'),
    path('books/<int:pk>/publish-status/', PublishStatusView.as_view(), name='book-publish-status'),

    # ===========================================
    # Chapters API
    # ===========================================
    path('chapters/<int:pk>/', ChapterDetailView.as_view(), name='chapter-detail'),
    path('chapters/<int:pk>/confirm/', ChapterConfirmView.as_view(), name='chapter-confirm'),
    path('chapters/<int:pk>/retry/', ChapterRetryView.as_view(), name='chapter-retry'),
    path('chapters/<int:pk>/segments/', ChapterSegmentsView.as_view(), name='chapter-segments'),

    # ===========================================
    # Upload API
    # ===========================================
    path('upload/epub/', UploadView.as_view(), name='upload-epub'),
    path('upload/presigned-url/', PresignedUrlView.as_view(), name='upload-presigned-url'),

    # ===========================================
    # Voices API
    # ===========================================
    path('voices/', VoiceListView.as_view(), name='voice-list'),
    path('voices/emotions/', EmotionListView.as_view(), name='voice-emotions'),
    path('voices/roles/', RoleMappingView.as_view(), name='voice-roles'),
    path('voices/rate-limit/', RateLimitView.as_view(), name='voice-rate-limit'),
    path('voices/cache-stats/', CacheStatsView.as_view(), name='voice-cache-stats'),

    # ===========================================
    # Publish API
    # ===========================================
    path('publish/channels/', PublishChannelListView.as_view(), name='publish-channel-list'),
    path('publish/channels/create/', PublishChannelCreateView.as_view(), name='publish-channel-create'),
    path('publish/channels/<int:pk>/', PublishChannelDetailView.as_view(), name='publish-channel-detail'),
    path('publish/records/', PublishRecordListView.as_view(), name='publish-record-list'),
    path('publish/records/<int:pk>/', PublishRecordView.as_view(), name='publish-record-detail'),

    # ===========================================
    # Watch API
    # ===========================================
    path('watch/status/', WatchStatusView.as_view(), name='watch-status'),
    path('watch/restart/', WatchRestartView.as_view(), name='watch-restart'),
    path('watch/history/', WatchHistoryView.as_view(), name='watch-history'),
]
