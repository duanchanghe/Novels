# ===========================================
# API App Configuration
# ===========================================

"""
API app configuration for AI 有声书工坊.
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    verbose_name = "API"
