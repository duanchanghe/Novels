# ===========================================
# API 路由模块
# ===========================================

"""
API 路由模块

包含所有 API 接口定义：
- api_books: 书籍管理接口
- api_upload: 文件上传接口
- api_voices: 音色相关接口
- api_watch: 文件夹监听管理接口
- api_publish: 自动发布管理接口
"""

from .api_books import router as books_router
from .api_upload import router as upload_router
from .api_voices import router as voices_router
from .api_watch import router as watch_router
from .api_publish import router as publish_router

__all__ = [
    "books_router",
    "upload_router",
    "voices_router",
    "watch_router",
    "publish_router",
]
