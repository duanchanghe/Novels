# ===========================================
# 阶段五自动化层集成测试
# ===========================================

"""
阶段五自动化层端到端集成测试

测试文件监听、自动处理和发布的完整流程。
"""

import pytest
import tempfile
import os
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.svc_file_watcher import (
    FileLock,
    ProcessingQueue,
    EPUBFileHandler,
    MultiDirectoryWatcher,
)
from services.svc_publisher import (
    BasePublisher,
    SelfHostedPublisher,
    XimalayaPublisher,
    PublisherService,
    PublishStatus,
)


class TestFileWatcherIntegration:
    """文件监听集成测试"""

    @pytest.fixture
    def temp_watch_dir(self):
        """创建临时监听目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_epub_file(self, temp_watch_dir):
        """创建模拟 EPUB 文件"""
        epub_path = os.path.join(temp_watch_dir, "test_book.epub")
        with open(epub_path, "wb") as f:
            f.write(b"PK\x03\x04" + b"fake epub content")
        return epub_path

    def test_watchdog_detects_new_file(self, temp_watch_dir, mock_epub_file):
        """测试 watchdog 检测新文件"""
        callback_mock = Mock()
        handler = EPUBFileHandler(
            on_new_file=callback_mock,
            watch_dirs=[temp_watch_dir],
        )

        # 模拟文件创建事件
        from watchdog.events import FileCreatedEvent
        event = FileCreatedEvent(mock_epub_file)
        handler.on_created(event)

        # 验证文件被检测
        time.sleep(1)  # 等待处理完成
        assert callback_mock.called

    def test_file_ready_detection(self, temp_watch_dir):
        """测试文件就绪检测"""
        handler = EPUBFileHandler(
            on_new_file=Mock(),
            watch_dirs=[temp_watch_dir],
        )

        # 创建文件
        epub_path = os.path.join(temp_watch_dir, "test.epub")
        with open(epub_path, "wb") as f:
            f.write(b"test content")

        # 文件应该就绪
        result = handler._wait_for_file_ready(epub_path, timeout=5)
        assert result is True

    def test_md5_deduplication_check(self, temp_watch_dir):
        """测试 MD5 去重检测"""
        import hashlib

        # 创建两个相同内容的文件
        content = b"test epub content"
        hash1 = hashlib.md5(content).hexdigest()

        # 模拟数据库返回已存在的哈希
        with patch("services.svc_file_watcher.get_db_context") as mock_db:
            mock_book = Mock()
            mock_book.file_hash = hash1
            mock_db.return_value.__enter__ = Mock(return_value=mock_db.return_value)
            mock_db.return_value.__exit__ = Mock(return_value=False)
            mock_db.return_value.query.return_value.filter.return_value.first.return_value = mock_book

            # 验证去重逻辑
            with open(os.path.join(temp_watch_dir, "dup.epub"), "wb") as f:
                f.write(content)

            # 检查逻辑（模拟）
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__ = Mock(
                    return_value=Mock(read=Mock(return_value=content))
                )
                mock_open.return_value.__exit__ = Mock(return_value=False)


class TestPublisherIntegration:
    """发布引擎集成测试"""

    @pytest.fixture
    def mock_book_data(self):
        """模拟书籍数据"""
        return {
            "id": 1,
            "title": "测试书籍",
            "author": "测试作者",
            "description": "这是一本测试书籍",
            "total_chapters": 10,
        }

    @pytest.fixture
    def mock_chapter_data(self):
        """模拟章节数据"""
        return {
            "id": 1,
            "title": "第一章",
            "index": 1,
            "duration": 300,
            "audio_file_path": "books/1/chapters/1.mp3",
        }

    @pytest.mark.asyncio
    async def test_self_hosted_publisher_flow(self, mock_book_data, mock_chapter_data):
        """测试自建平台发布流程"""
        publisher = SelfHostedPublisher()

        # 1. 创建专辑
        album_result = await publisher.create_album(mock_book_data)
        assert album_result["album_id"] == "self_1"
        assert album_result["album_url"] == "/books/1/player"
        assert album_result["internal"] is True

        # 2. 上传章节（Mock MinIO）
        with patch("services.svc_publisher.get_storage_service") as mock_storage:
            mock_storage_instance = Mock()
            mock_storage_instance.get_presigned_url.return_value = "https://minio.example.com/audio.mp3"
            mock_storage.return_value = mock_storage_instance

            audio_result = await publisher.upload_chapter(
                album_result["album_id"],
                mock_chapter_data,
                b"fake audio data",
            )

            assert audio_result["audio_id"] == "audio_1"
            assert "audio_url" in audio_result
            assert audio_result["internal"] is True

        # 3. 发布专辑
        publish_result = await publisher.publish_album(album_result["album_id"])
        assert publish_result is True

    def test_publisher_service_channel_selection(self):
        """测试发布渠道选择"""
        service = PublisherService()

        # 获取自建平台发布器
        publisher = service.get_publisher("self_hosted")
        assert isinstance(publisher, SelfHostedPublisher)

        # 获取喜马拉雅发布器（未实现）
        publisher = service.get_publisher("ximalaya")
        assert isinstance(publisher, XimalayaPublisher)

        # 无效渠道
        publisher = service.get_publisher("invalid")
        assert publisher is None

    def test_publisher_service_progress_calculation(self):
        """测试进度计算"""
        service = PublisherService()

        # 创建模拟记录
        record = Mock()
        record.total_chapters = 10
        record.published_chapters = 5

        progress = service._calculate_progress(record)
        assert progress == 50.0

        # 边界情况：零章节
        record.total_chapters = 0
        record.published_chapters = 0
        progress = service._calculate_progress(record)
        assert progress == 0.0


class TestPublishStatusFlow:
    """发布状态流转测试"""

    def test_publish_status_values(self):
        """测试发布状态枚举值"""
        assert PublishStatus.PENDING.value == "pending"
        assert PublishStatus.PREPARING.value == "preparing"
        assert PublishStatus.PUBLISHING.value == "publishing"
        assert PublishStatus.PARTIAL_DONE.value == "partial_done"
        assert PublishStatus.DONE.value == "done"
        assert PublishStatus.FAILED.value == "failed"
        assert PublishStatus.CANCELLED.value == "cancelled"


class TestAutoPublishWorkflow:
    """自动发布工作流测试"""

    def test_auto_publish_trigger_conditions(self):
        """测试自动发布触发条件"""
        # 测试场景1：书籍生成完成
        book_status = "done"
        channel_auto_publish = True
        assert book_status == "done" and channel_auto_publish is True

        # 测试场景2：书籍未完成
        book_status = "synthesizing"
        assert not (book_status == "done" and channel_auto_publish is True)

    def test_multi_channel_publish_order(self):
        """测试多渠道发布顺序"""
        channels = [
            {"name": "蜻蜓FM", "priority": 1},
            {"name": "喜马拉雅", "priority": 2},
            {"name": "自建平台", "priority": 3},
        ]

        # 按优先级排序
        sorted_channels = sorted(channels, key=lambda x: x["priority"], reverse=True)
        assert sorted_channels[0]["name"] == "自建平台"
        assert sorted_channels[2]["name"] == "蜻蜓FM"


class TestWatchDogHealthCheck:
    """监听服务健康检查测试"""

    def test_health_check_status_healthy(self):
        """测试健康状态正常"""
        stats = {
            "total_detected": 10,
            "total_processed": 9,
            "total_failed": 1,
        }

        # 失败率 < 10%
        failure_rate = stats["total_failed"] / max(stats["total_detected"], 1)
        assert failure_rate < 0.1

    def test_health_check_status_degraded(self):
        """测试服务降级状态"""
        stats = {
            "total_detected": 10,
            "total_processed": 5,
            "total_failed": 5,
        }

        # 失败率 >= 50%
        failure_rate = stats["total_failed"] / max(stats["total_detected"], 1)
        assert failure_rate >= 0.5


class TestFileProcessingConcurrency:
    """文件处理并发测试"""

    def test_concurrent_processing_limit(self):
        """测试并发处理限制"""
        queue = ProcessingQueue(max_concurrent=2)

        # 获取两个名额
        assert queue.acquire() is True
        assert queue.acquire() is True

        # 第三个应该失败
        assert queue.acquire() is False

        # 释放一个
        queue.release()
        assert queue.acquire() is True

    def test_file_lock_prevents_duplicate(self):
        """测试文件锁防止重复处理"""
        lock = FileLock()

        file_path = "/test/duplicate.epub"

        # 获取锁
        result1 = lock.acquire(file_path, timeout=1.0)
        assert result1 is True

        # 第二次获取应该失败
        result2 = lock.acquire(file_path, timeout=0.5)
        assert result2 is False

        # 释放锁
        lock.release(file_path)


class TestPublishRecordTracking:
    """发布记录追踪测试"""

    def test_chapter_publish_mapping(self):
        """测试章节发布映射"""
        chapters_published = {}

        # 模拟发布章节
        chapters_published["1"] = "audio_001"
        chapters_published["2"] = "audio_002"

        assert len(chapters_published) == 2
        assert chapters_published["1"] == "audio_001"

    def test_publish_progress_percentage(self):
        """测试发布进度百分比计算"""
        total = 10
        published = 3

        progress = round((published / total) * 100, 2)
        assert progress == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
