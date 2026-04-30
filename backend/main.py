# ===========================================
# AI 有声书工坊 - FastAPI 主应用入口
# ===========================================

"""
AI 有声书工坊 - FastAPI 主应用入口

提供 EPUB 电子书到 AI 有声书的自动化转换服务。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import engine, Base
from core.middleware import setup_middleware, register_exception_handlers
from api import (
    books_router,
    upload_router,
    voices_router,
    watch_router,
    publish_router,
)


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用实例

    Returns:
        FastAPI: 配置好的应用实例
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI 有声书工坊 - 将 EPUB 电子书自动转换为 AI 有声书",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 配置自定义中间件（请求日志、错误处理等）
    setup_middleware(app)
    register_exception_handlers(app)

    # 注册路由
    app.include_router(books_router, prefix="/api", tags=["书籍管理"])
    app.include_router(upload_router, prefix="/api", tags=["文件上传"])
    app.include_router(voices_router, prefix="/api", tags=["音色管理"])
    app.include_router(watch_router, prefix="/api", tags=["文件夹监听"])
    app.include_router(publish_router, prefix="/api", tags=["自动发布"])

    @app.get("/api/health")
    async def health_check():
        """
        健康检查接口

        Returns:
            dict: 服务健康状态
        """
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": "0.1.0",
        }

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
