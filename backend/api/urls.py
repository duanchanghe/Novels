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
    BookSubtitleView,
    BookDeleteView,
    BookStopAllView,
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
from .views.characters import (
    CharacterListView,
    CharacterDetailView,
    CharacterBatchAssignVoiceView,
    CharacterApproveView,
    CharacterApproveAllView,
    CharacterSummaryView,
    CharacterCanGenerateView,
    VoiceProfileOptionsView,
)
from .views.generate import (
    ManualGenerateView,
    GenerateCheckView,
    CharacterSyncView,
)
from .views.sound_effects import (
    SoundEffectListView,
    SoundEffectDetailView,
    SoundEffectSearchView,
    SoundEffectRecommendView,
    SoundEffectStatisticsView,
    BBSSyncView,
    BBCEffectDownloadView,
    SoundEffectUsageView,
    SoundEffectFavoriteView,
    SoundEffectVerifyView,
    SoundEffectCollectionListView,
    SoundEffectCollectionDetailView,
    SoundEffectCollectionItemView,
    SoundEffectExportView,
    SoundEffectImportView,
    SoundEffectTypeListView,
    SoundEffectSourceListView,
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
    path('books/<int:pk>/subtitles/', BookSubtitleView.as_view(), name='book-subtitles'),
    path('books/<int:pk>/delete/', BookDeleteView.as_view(), name='book-delete'),
    path('books/stop-all/', BookStopAllView.as_view(), name='book-stop-all'),
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
    # Characters API (角色库)
    # ===========================================
    path('books/<int:book_id>/characters/', CharacterListView.as_view(), name='character-list'),
    path('books/<int:book_id>/characters/<int:character_id>/', CharacterDetailView.as_view(), name='character-detail'),
    path('books/<int:book_id>/characters/batch-assign-voice/', CharacterBatchAssignVoiceView.as_view(), name='character-batch-assign'),
    path('books/<int:book_id>/characters/<int:character_id>/approve/', CharacterApproveView.as_view(), name='character-approve'),
    path('books/<int:book_id>/characters/approve-all/', CharacterApproveAllView.as_view(), name='character-approve-all'),
    path('books/<int:book_id>/characters/summary/', CharacterSummaryView.as_view(), name='character-summary'),
    path('books/<int:book_id>/characters/can-generate/', CharacterCanGenerateView.as_view(), name='character-can-generate'),
    path('books/<int:book_id>/voice-profiles/', VoiceProfileOptionsView.as_view(), name='voice-profile-options'),
    path('books/<int:book_id>/manual-generate/', ManualGenerateView.as_view(), name='manual-generate'),
    path('books/<int:book_id>/generate-check/', GenerateCheckView.as_view(), name='generate-check'),
    path('books/<int:book_id>/sync-characters/', CharacterSyncView.as_view(), name='sync-characters'),
    path('voice-profiles/', VoiceProfileOptionsView.as_view(), name='voice-profiles-all'),

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

    # ===========================================
    # Sound Effects API (音效库)
    # ===========================================
    path('sound-effects/', SoundEffectListView.as_view(), name='sound-effect-list'),
    path('sound-effects/<int:effect_id>/', SoundEffectDetailView.as_view(), name='sound-effect-detail'),
    path('sound-effects/search/', SoundEffectSearchView.as_view(), name='sound-effect-search'),
    path('sound-effects/recommend/', SoundEffectRecommendView.as_view(), name='sound-effect-recommend'),
    path('sound-effects/statistics/', SoundEffectStatisticsView.as_view(), name='sound-effect-statistics'),
    path('sound-effects/bbc-sync/', BBSSyncView.as_view(), name='sound-effect-bbc-sync'),
    path('sound-effects/bbc-download/', BBCEffectDownloadView.as_view(), name='sound-effect-bbc-download'),
    path('sound-effects/<int:effect_id>/usage/', SoundEffectUsageView.as_view(), name='sound-effect-usage'),
    path('sound-effects/<int:effect_id>/favorite/', SoundEffectFavoriteView.as_view(), name='sound-effect-favorite'),
    path('sound-effects/<int:effect_id>/verify/', SoundEffectVerifyView.as_view(), name='sound-effect-verify'),

    # Sound Effect Collections (音效收藏集)
    path('sound-effects/collections/', SoundEffectCollectionListView.as_view(), name='sound-effect-collection-list'),
    path('sound-effects/collections/<int:collection_id>/', SoundEffectCollectionDetailView.as_view(), name='sound-effect-collection-detail'),
    path('sound-effects/collections/<int:collection_id>/items/', SoundEffectCollectionItemView.as_view(), name='sound-effect-collection-item'),

    # Import/Export (导入导出)
    path('books/<int:book_id>/sound-effects/export/', SoundEffectExportView.as_view(), name='sound-effect-export'),
    path('books/<int:book_id>/sound-effects/import/', SoundEffectImportView.as_view(), name='sound-effect-import'),

    # Types and Sources (类型和来源)
    path('sound-effects/types/', SoundEffectTypeListView.as_view(), name='sound-effect-types'),
    path('sound-effects/sources/', SoundEffectSourceListView.as_view(), name='sound-effect-sources'),
]
