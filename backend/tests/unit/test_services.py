# ===========================================
# Service Layer Unit Tests
# ===========================================

"""
Unit tests for service layer components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from services.base import (
    ServiceType,
    ServiceResult,
    BaseService,
)


class TestServiceResult:
    """Test ServiceResult dataclass."""

    def test_ok_creates_successful_result(self):
        """Test creating successful result."""
        result = ServiceResult.ok(data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_fail_creates_failed_result(self):
        """Test creating failed result."""
        result = ServiceResult.fail(error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_ok_with_metadata(self):
        """Test successful result with metadata."""
        result = ServiceResult.ok(
            data="test",
            metadata={"count": 1, "type": "example"}
        )
        assert result.success is True
        assert result.metadata == {"count": 1, "type": "example"}


class TestEPUBParserService:
    """Test EPUB parser service."""

    @pytest.fixture
    def mock_epub_parser(self):
        """Mock EPUB parser service."""
        with patch('services.svc_epub_parser.epub') as mock_epub:
            mock_book = Mock()
            mock_book.get_metadata.return_value = [
                ("Test Book", {})
            ]
            mock_book.toc = []
            mock_book.get_items.return_value = []
            mock_epub.read_epub.return_value = mock_book
            yield mock_epub

    def test_validate_epub_format_valid(self, tmp_path, mock_epub_parser):
        """Test validating a valid EPUB file."""
        from services.svc_epub_parser import EPUBParserService

        # Create a valid EPUB structure
        epub_file = tmp_path / "test.epub"
        import zipfile
        with zipfile.ZipFile(epub_file, 'w') as zf:
            zf.writestr("mimetype", "application/epub+zip")

        parser = EPUBParserService()
        assert parser._validate_epub_format(str(epub_file)) is True

    def test_validate_epub_format_invalid(self, tmp_path):
        """Test validating an invalid file."""
        from services.svc_epub_parser import EPUBParserService

        # Create an invalid file (not a zip)
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("This is not an EPUB file")

        parser = EPUBParserService()
        assert parser._validate_epub_format(str(invalid_file)) is False


class TestServiceManager:
    """Test service manager."""

    def test_service_manager_singleton(self):
        """Test that service manager is a singleton."""
        from services.manager import ServiceManager

        manager1 = ServiceManager()
        manager2 = ServiceManager()
        assert manager1 is manager2

    def test_register_service(self):
        """Test registering a service."""
        from services.manager import ServiceManager

        manager = ServiceManager()
        mock_service = Mock()
        mock_service.service_type = ServiceType.MINIO_STORAGE

        manager.register(ServiceType.MINIO_STORAGE, mock_service)
        assert manager.get(ServiceType.MINIO_STORAGE) is mock_service

    def test_get_nonexistent_service(self):
        """Test getting a service that doesn't exist."""
        from services.manager import ServiceManager

        manager = ServiceManager()
        assert manager.get(ServiceType.MINIO_STORAGE) is None
