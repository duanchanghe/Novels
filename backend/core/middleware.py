# ===========================================
# 中间件模块
# ===========================================

"""
中间件模块

包含应用的中间件配置：
- 日志中间件：记录请求日志
- 错误处理中间件：统一处理异常
- 请求耗时中间件：记录请求处理时间
"""

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.exceptions import AppError, NotFoundError, ValidationError


# 配置日志
logger = logging.getLogger("audiobook")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    记录每个 HTTP 请求的详细信息：
    - 请求方法、路径、参数
    - 响应状态码
    - 请求处理耗时
    - 客户端 IP
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.time()

        # 获取请求信息
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # 记录请求
        logger.info(f"请求开始: {method} {path} - 客户端: {client_ip}")

        try:
            # 处理请求
            response = await call_next(request)

            # 计算处理耗时
            process_time = time.time() - start_time

            # 记录响应
            logger.info(
                f"请求完成: {method} {path} - "
                f"状态: {response.status_code} - "
                f"耗时: {process_time:.3f}s"
            )

            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # 计算处理耗时
            process_time = time.time() - start_time

            # 记录错误
            logger.error(
                f"请求失败: {method} {path} - "
                f"错误: {str(e)} - "
                f"耗时: {process_time:.3f}s"
            )
            raise


def setup_middleware(app: FastAPI) -> None:
    """
    配置应用中间件

    注册所有中间件到 FastAPI 应用。

    Args:
        app: FastAPI 应用实例
    """
    # 添加请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)


def create_error_response(status_code: int, error: AppError) -> JSONResponse:
    """
    创建错误响应

    将异常转换为标准 JSON 响应格式。

    Args:
        status_code: HTTP 状态码
        error: 应用异常实例

    Returns:
        JSONResponse: 错误响应
    """
    return JSONResponse(
        status_code=status_code,
        content=error.to_dict(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册全局异常处理器

    将自定义异常映射到对应的 HTTP 状态码。

    Args:
        app: FastAPI 应用实例
    """

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """处理应用自定义异常"""
        status_map = {
            "VALIDATION_ERROR": 400,
            "NOT_FOUND_ERROR": 404,
            "AUTH_ERROR": 401,
            "PERMISSION_ERROR": 403,
        }
        status_code = status_map.get(exc.code, 500)
        return create_error_response(status_code, exc)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        """处理资源不存在异常"""
        return create_error_response(404, exc)

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """处理数据验证异常"""
        return create_error_response(400, exc)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """处理未捕获的异常"""
        logger.exception("未处理的异常")
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"exception": str(exc)} if app.debug else {},
            },
        )
