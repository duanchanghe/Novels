# ===========================================
# API 模块
# ===========================================

"""
API module for AI 有声书工坊.

包含所有 API 接口定义：
- views: REST Framework 视图集
- serializers: 数据序列化器
- urls: URL 路由配置
"""

default_app_config = "api.apps.ApiConfig"

__all__ = [
    "views",
    "serializers",
]
