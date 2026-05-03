# ===========================================
# API URLs
# ===========================================

"""
API URL Configuration

All API endpoints are defined here.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views import (
    BookViewSet, ChapterViewSet, UploadViewSet,
    VoiceViewSet, WatchViewSet, PublishViewSet,
    HealthCheckView
)

router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')
router.register(r'chapters', ChapterViewSet, basename='chapter')
router.register(r'voices', VoiceViewSet, basename='voice')
router.register(r'watch', WatchViewSet, basename='watch')
router.register(r'publish', PublishViewSet, basename='publish')

urlpatterns = [
    # Health check
    path('health', HealthCheckView.as_view(), name='health'),
    
    # Upload endpoint
    path('upload/epub', UploadViewSet.as_view(), name='upload-epub'),
    path('upload/presigned-url', UploadViewSet.as_view(), name='upload-presigned-url'),
    
    # Router URLs
    path('', include(router.urls)),
]
