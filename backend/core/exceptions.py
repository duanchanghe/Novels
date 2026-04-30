# ===========================================
# 自定义异常模块
# ===========================================

"""
自定义异常模块

定义项目使用的所有自定义异常类型。
采用层次化设计，便于异常捕获和处理。
"""


class AppError(Exception):
    """
    应用基础异常类

    所有自定义异常的基类。
    提供统一的异常处理接口。
    """

    def __init__(self, message: str, code: str = "APP_ERROR", details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """将异常转换为字典格式"""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class FileError(AppError):
    """
    文件相关异常基类
    """
    pass


class EPUBParseError(FileError):
    """
    EPUB 文件解析异常

    当 EPUB 文件格式不正确、无法解析或包含 DRM 保护时抛出。
    """
    pass


class StorageError(AppError):
    """
    存储服务异常

    当 MinIO 或其他存储服务操作失败时抛出。
    """
    pass


class APIError(AppError):
    """
    外部 API 调用异常基类
    """
    pass


class DeepSeekApiError(APIError):
    """
    DeepSeek API 调用异常

    当调用 DeepSeek LLM API 失败时抛出。
    包括认证失败、请求超时、限流等情况。
    """
    pass


class MiniMaxApiError(APIError):
    """
    MiniMax API 调用异常

    当调用 MiniMax TTS API 失败时抛出。
    包括认证失败、请求超时、限流等情况。
    """
    pass


class TTSApiError(APIError):
    """
    TTS API 调用异常

    通用的语音合成 API 异常。
    """
    pass


class PublishError(AppError):
    """
    发布相关异常

    当有声书发布到平台失败时抛出。
    """
    pass


class ValidationError(AppError):
    """
    数据验证异常

    当输入数据校验失败时抛出。
    """
    pass


class NotFoundError(AppError):
    """
    资源不存在异常

    当查询的资源不存在时抛出。
    """
    pass


class TaskError(AppError):
    """
    任务执行异常

    当异步任务执行失败时抛出。
    """
    pass
