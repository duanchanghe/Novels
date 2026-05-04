# ===========================================
# Task Unit Tests
# ===========================================

"""
Unit tests for Celery tasks.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tasks.base import (
    BasePipelineTask,
    AIAPITask,
    task_retry_config,
)


class TestTaskRetryConfig:
    """Test task retry configuration."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = task_retry_config()
        assert config["max_retries"] == 3
        assert config["retry_backoff"] is True
        assert config["retry_jitter"] is True

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = task_retry_config(
            max_retries=5,
            retry_delay=20,
            backoff_max=300
        )
        assert config["max_retries"] == 5
        assert config["default_retry_delay"] == 20
        assert config["retry_backoff_max"] == 300


class TestPipelineContext:
    """Test pipeline context dataclass."""

    def test_create_context(self):
        """Test creating pipeline context."""
        from tasks.task_pipeline import PipelineContext, PipelineStage

        ctx = PipelineContext(
            book_id=1,
            chapter_ids=[1, 2, 3]
        )
        assert ctx.book_id == 1
        assert len(ctx.chapter_ids) == 3
        assert ctx.current_stage == PipelineStage.PARSING

    def test_add_error(self):
        """Test adding errors to context."""
        from tasks.task_pipeline import PipelineContext, PipelineStage

        ctx = PipelineContext(book_id=1)
        ctx.add_error(PipelineStage.ANALYZING, ValueError("Test error"))

        assert len(ctx.errors) == 1
        assert ctx.errors[0]["stage"] == "analyzing"
        assert "Test error" in ctx.errors[0]["error"]

    def test_to_dict(self):
        """Test converting context to dictionary."""
        from tasks.task_pipeline import PipelineContext

        ctx = PipelineContext(book_id=1, chapter_ids=[1, 2])
        data = ctx.to_dict()

        assert data["book_id"] == 1
        assert data["chapter_ids"] == [1, 2]
        assert "errors" in data
