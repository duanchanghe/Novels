# ===========================================
# Domain Model Unit Tests
# ===========================================

"""
Unit tests for domain models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError

from core.domain.models import (
    BookModel,
    ChapterModel,
    SegmentModel,
    BookStatus,
    ChapterStatus,
    SegmentStatus,
    ProcessingMode,
)


class TestBookModel:
    """Test BookModel."""

    def test_create_book_with_defaults(self):
        """Test creating a book with default values."""
        book = BookModel(
            title="Test Book",
            author="Test Author"
        )
        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert book.status == BookStatus.PENDING
        assert book.total_chapters == 0

    def test_create_book_with_all_fields(self):
        """Test creating a book with all fields."""
        book = BookModel(
            title="Complete Book",
            author="Full Name",
            description="A complete test book",
            status=BookStatus.PROCESSING,
            total_chapters=10,
            language="zh-CN"
        )
        assert book.title == "Complete Book"
        assert book.status == BookStatus.PROCESSING
        assert book.total_chapters == 10

    def test_book_model_validation(self):
        """Test book model validation."""
        with pytest.raises(PydanticValidationError):
            BookModel()  # Missing required fields


class TestChapterModel:
    """Test ChapterModel."""

    def test_create_chapter(self):
        """Test creating a chapter."""
        chapter = ChapterModel(
            book_id=1,
            chapter_index=1,
            title="Chapter 1"
        )
        assert chapter.book_id == 1
        assert chapter.chapter_index == 1
        assert chapter.title == "Chapter 1"
        assert chapter.status == ChapterStatus.PENDING

    def test_chapter_ordering(self):
        """Test chapter ordering field."""
        chapter = ChapterModel(
            book_id=1,
            chapter_index=1,
            title="First Chapter",
            play_order=1
        )
        assert chapter.play_order == 1


class TestSegmentModel:
    """Test SegmentModel."""

    def test_create_segment(self):
        """Test creating a segment."""
        segment = SegmentModel(
            chapter_id=1,
            segment_index=0,
            text_content="Test segment content",
            role="narrator"
        )
        assert segment.chapter_id == 1
        assert segment.text_content == "Test segment content"
        assert segment.role == "narrator"
        assert segment.status == SegmentStatus.PENDING


class TestDomainEnums:
    """Test domain enumerations."""

    def test_book_status_values(self):
        """Test BookStatus enum values."""
        assert BookStatus.PENDING.value == "pending"
        assert BookStatus.PROCESSING.value == "processing"
        assert BookStatus.DONE.value == "done"
        assert BookStatus.FAILED.value == "failed"

    def test_chapter_status_values(self):
        """Test ChapterStatus enum values."""
        assert ChapterStatus.PENDING.value == "pending"
        assert ChapterStatus.ANALYZED.value == "analyzed"
        assert ChapterStatus.SYNTHESIZING.value == "synthesizing"
        assert ChapterStatus.DONE.value == "done"

    def test_processing_mode_values(self):
        """Test ProcessingMode enum values."""
        assert ProcessingMode.AUTO.value == "auto"
        assert ProcessingMode.MANUAL.value == "manual"
