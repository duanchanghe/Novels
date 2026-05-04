# ===========================================
# Core Exceptions
# ===========================================

"""
Core exceptions module.

Re-exports domain exceptions for backward compatibility.
This module exists for historical reasons - new code should import
from core.domain.exceptions directly.
"""

# Re-export all domain exceptions for backward compatibility
from .domain.exceptions import (
    # Base
    DomainError,
    # Book
    BookNotFoundError,
    BookAlreadyExistsError,
    BookInInvalidStateError,
    InvalidStateTransitionError,
    # Chapter
    ChapterNotFoundError,
    ChapterAlreadyExistsError,
    # Segment
    SegmentNotFoundError,
    # Publish
    ChannelNotFoundError,
    PublishError,
    # Storage
    StorageError,
    FileNotFoundError,
    # Service
    ServiceError,
    EPUBParseError,
    APIError,
    DeepSeekAPIError,
    MiniMaxAPIError,
    # Validation
    ValidationError,
    FileFormatError,
    DRMProtectedError,
)

__all__ = [
    # Base
    "DomainError",
    # Book
    "BookNotFoundError",
    "BookAlreadyExistsError",
    "BookInInvalidStateError",
    "InvalidStateTransitionError",
    # Chapter
    "ChapterNotFoundError",
    "ChapterAlreadyExistsError",
    # Segment
    "SegmentNotFoundError",
    # Publish
    "ChannelNotFoundError",
    "PublishError",
    # Storage
    "StorageError",
    "FileNotFoundError",
    # Service
    "ServiceError",
    "EPUBParseError",
    "APIError",
    "DeepSeekAPIError",
    "MiniMaxAPIError",
    # Validation
    "ValidationError",
    "FileFormatError",
    "DRMProtectedError",
]
