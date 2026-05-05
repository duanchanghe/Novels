# ===========================================
# 领域异常
# ===========================================

"""
领域异常 - 领域层专用的异常类型

这些异常表示业务逻辑层面的错误，
与基础设施层的异常（如 API 调用失败）区分开来。
"""


class DomainError(Exception):
    """
    领域基础异常

    所有领域层异常的基类。
    """

    def __init__(self, message: str, code: str = "DOMAIN_ERROR", details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


# ===========================================
# 书籍异常
# ===========================================

class BookNotFoundError(DomainError):
    """书籍不存在"""

    def __init__(self, book_id: int):
        super().__init__(
            message=f"书籍不存在: {book_id}",
            code="BOOK_NOT_FOUND",
            details={"book_id": book_id},
        )


class BookAlreadyExistsError(DomainError):
    """书籍已存在"""

    def __init__(self, file_hash: str = None):
        details = {"file_hash": file_hash} if file_hash else {}
        super().__init__(
            message="该书籍已存在",
            code="BOOK_ALREADY_EXISTS",
            details=details,
        )


class BookInInvalidStateError(DomainError):
    """书籍处于无效状态"""

    def __init__(self, book_id: int, current_status: str, expected_status: str):
        super().__init__(
            message=f"书籍 {book_id} 当前状态为 {current_status}，无法执行操作",
            code="BOOK_INVALID_STATE",
            details={
                "book_id": book_id,
                "current_status": current_status,
                "expected_status": expected_status,
            },
        )


class InvalidStateTransitionError(DomainError):
    """无效的状态转换"""

    def __init__(self, entity_type: str, entity_id: int, current_status: str, target_status: str):
        super().__init__(
            message=f"{entity_type} {entity_id} 无法从 {current_status} 转换到 {target_status}",
            code="INVALID_STATE_TRANSITION",
            details={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "current_status": current_status,
                "target_status": target_status,
            },
        )


# ===========================================
# 章节异常
# ===========================================

class ChapterNotFoundError(DomainError):
    """章节不存在"""

    def __init__(self, chapter_id: int = None, book_id: int = None, chapter_index: int = None):
        details = {}
        if chapter_id:
            details["chapter_id"] = chapter_id
        if book_id:
            details["book_id"] = book_id
        if chapter_index is not None:
            details["chapter_index"] = chapter_index

        message = "章节不存在"
        if chapter_id:
            message = f"章节不存在: {chapter_id}"

        super().__init__(
            message=message,
            code="CHAPTER_NOT_FOUND",
            details=details,
        )


class ChapterAlreadyExistsError(DomainError):
    """章节已存在"""

    def __init__(self, book_id: int, chapter_index: int):
        super().__init__(
            message=f"书籍 {book_id} 的第 {chapter_index} 章已存在",
            code="CHAPTER_ALREADY_EXISTS",
            details={"book_id": book_id, "chapter_index": chapter_index},
        )


# ===========================================
# 片段异常
# ===========================================

class SegmentNotFoundError(DomainError):
    """片段不存在"""

    def __init__(self, segment_id: int = None, chapter_id: int = None, segment_index: int = None):
        details = {}
        if segment_id:
            details["segment_id"] = segment_id
        if chapter_id:
            details["chapter_id"] = chapter_id
        if segment_index is not None:
            details["segment_index"] = segment_index

        message = "片段不存在"
        if segment_id:
            message = f"片段不存在: {segment_id}"

        super().__init__(
            message=message,
            code="SEGMENT_NOT_FOUND",
            details=details,
        )


# ===========================================
# 发布异常
# ===========================================

class ChannelNotFoundError(DomainError):
    """发布渠道不存在"""

    def __init__(self, channel_id: int):
        super().__init__(
            message=f"发布渠道不存在: {channel_id}",
            code="CHANNEL_NOT_FOUND",
            details={"channel_id": channel_id},
        )


class PublishError(DomainError):
    """发布失败"""

    def __init__(self, book_id: int, channel_id: int, message: str):
        super().__init__(
            message=f"发布失败: {message}",
            code="PUBLISH_ERROR",
            details={"book_id": book_id, "channel_id": channel_id},
        )


# ===========================================
# 存储异常
# ===========================================

class StorageError(DomainError):
    """存储操作失败"""

    def __init__(self, operation: str, message: str, bucket: str = None, object_name: str = None):
        details = {"operation": operation, "message": message}
        if bucket:
            details["bucket"] = bucket
        if object_name:
            details["object_name"] = object_name

        super().__init__(
            message=f"存储操作失败: {message}",
            code="STORAGE_ERROR",
            details=details,
        )


class FileNotFoundError(StorageError):
    """文件不存在"""

    def __init__(self, bucket: str, object_name: str):
        super().__init__(
            operation="get",
            message=f"文件不存在: {object_name}",
            bucket=bucket,
            object_name=object_name,
        )
        self.code = "FILE_NOT_FOUND"


# ===========================================
# 服务异常
# ===========================================

class ServiceError(DomainError):
    """服务层基础异常"""

    def __init__(self, service_name: str = "Unknown", message: str = "", original_error: Exception = None):
        if not message:
            message = service_name
            service_name = "Service"
        details = {"service": service_name}
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(
            message=f"{service_name} 服务错误: {message}",
            code="SERVICE_ERROR",
            details=details,
        )


class EPUBParseError(ServiceError):
    """EPUB 解析失败"""

    def __init__(self, message: str, file_path: str = None, original_error: Exception = None):
        details = {"file_path": file_path} if file_path else {}
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(
            service_name="EPUB Parser",
            message=message,
            original_error=original_error,
        )
        self.code = "EPUB_PARSE_ERROR"
        self.details.update(details)


class APIError(ServiceError):
    """外部 API 调用失败"""

    def __init__(self, api_name: str, message: str, status_code: int = None, original_error: Exception = None):
        details = {"api": api_name}
        if status_code:
            details["status_code"] = status_code
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(
            service_name=api_name,
            message=message,
            original_error=original_error,
        )
        self.code = "API_ERROR"
        self.details.update(details)


class DeepSeekAPIError(APIError):
    """DeepSeek API 调用失败"""

    def __init__(self, message: str, status_code: int = None, original_error: Exception = None):
        super().__init__(
            api_name="DeepSeek",
            message=message,
            status_code=status_code,
            original_error=original_error,
        )
        self.code = "DEEPSEEK_API_ERROR"


class MiniMaxAPIError(APIError):
    """MiniMax API 调用失败"""

    def __init__(self, message: str, status_code: int = None, original_error: Exception = None):
        super().__init__(
            api_name="MiniMax",
            message=message,
            status_code=status_code,
            original_error=original_error,
        )
        self.code = "MINIMAX_API_ERROR"


# ===========================================
# 验证异常
# ===========================================

class ValidationError(DomainError):
    """数据验证失败"""

    def __init__(self, message: str, field: str = None, value: any = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details,
        )


class FileFormatError(ValidationError):
    """文件格式错误"""

    def __init__(self, expected_format: str, actual_format: str = None):
        message = f"不支持的文件格式: {expected_format}"
        if actual_format:
            message = f"文件格式错误，期望 {expected_format}，实际 {actual_format}"

        super().__init__(
            message=message,
            field="file",
        )
        self.code = "FILE_FORMAT_ERROR"


class DRMProtectedError(FileFormatError):
    """文件受 DRM 保护"""

    def __init__(self):
        super().__init__(
            message="文件受 DRM 保护，无法处理",
            actual_format="DRM",
        )
        self.code = "DRM_PROTECTED"
