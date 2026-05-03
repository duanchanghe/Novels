# ===========================================
# URL configuration
# ===========================================

"""
URL configuration for AI 有声书工坊 project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
