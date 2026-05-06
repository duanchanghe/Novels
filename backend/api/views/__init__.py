"""
API 视图模块
"""

from .health import HealthCheckView
from .books import (
    BookListView, BookDetailView, BookChaptersView, BookStatusView,
    BookGenerateView, BookRetryView, BookAudioView, BookDownloadView,
    BookSubtitleView, BookDeleteView, BookStopAllView,
)
from .chapters import (
    ChapterDetailView, ChapterConfirmView, ChapterRetryView, ChapterSegmentsView,
)
from .upload import UploadView, PresignedUrlView
from .voices import (
    VoiceListView, EmotionListView, RoleMappingView,
    RateLimitView, CacheStatsView, VoiceRecommendView,
)
from .publish import (
    PublishChannelListView, PublishChannelCreateView, PublishChannelDetailView,
    PublishBookView, PublishStatusView, PublishRecordView, PublishRecordListView,
)
from .watch import WatchStatusView, WatchRestartView, WatchHistoryView
from .characters import (
    CharacterListView, CharacterDetailView, CharacterBatchAssignVoiceView,
    CharacterApproveView, CharacterApproveAllView, CharacterSummaryView,
    CharacterCanGenerateView, VoiceProfileOptionsView,
)
from .generate import ManualGenerateView, GenerateCheckView, CharacterSyncView
from .sound_effects import (
    SoundEffectListView, SoundEffectDetailView, SoundEffectSearchView,
    SoundEffectRecommendView, SoundEffectStatisticsView, BBBSyncView,
    BBCEffectDownloadView, SoundEffectUsageView, SoundEffectFavoriteView,
    SoundEffectVerifyView, SoundEffectCollectionListView, SoundEffectCollectionDetailView,
    SoundEffectCollectionItemView, SoundEffectExportView, SoundEffectImportView,
    SoundEffectTypeListView, SoundEffectSourceListView,
)

__all__ = [
    # Health
    "HealthCheckView",
    # Books
    "BookListView", "BookDetailView", "BookChaptersView", "BookStatusView",
    "BookGenerateView", "BookRetryView", "BookAudioView", "BookDownloadView",
    "BookSubtitleView", "BookDeleteView", "BookStopAllView",
    # Chapters
    "ChapterDetailView", "ChapterConfirmView", "ChapterRetryView", "ChapterSegmentsView",
    # Upload
    "UploadView", "PresignedUrlView",
    # Voices
    "VoiceListView", "EmotionListView", "RoleMappingView",
    "RateLimitView", "CacheStatsView", "VoiceRecommendView",
    # Publish
    "PublishChannelListView", "PublishChannelCreateView", "PublishChannelDetailView",
    "PublishBookView", "PublishStatusView", "PublishRecordView", "PublishRecordListView",
    # Watch
    "WatchStatusView", "WatchRestartView", "WatchHistoryView",
    # Characters
    "CharacterListView", "CharacterDetailView", "CharacterBatchAssignVoiceView",
    "CharacterApproveView", "CharacterApproveAllView", "CharacterSummaryView",
    "CharacterCanGenerateView", "VoiceProfileOptionsView",
    # Generate
    "ManualGenerateView", "GenerateCheckView", "CharacterSyncView",
    # Sound Effects
    "SoundEffectListView", "SoundEffectDetailView", "SoundEffectSearchView",
    "SoundEffectRecommendView", "SoundEffectStatisticsView", "BBBSyncView",
    "BBCEffectDownloadView", "SoundEffectUsageView", "SoundEffectFavoriteView",
    "SoundEffectVerifyView", "SoundEffectCollectionListView", "SoundEffectCollectionDetailView",
    "SoundEffectCollectionItemView", "SoundEffectExportView", "SoundEffectImportView",
    "SoundEffectTypeListView", "SoundEffectSourceListView",
]
