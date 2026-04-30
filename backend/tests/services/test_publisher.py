# ===========================================
# 发布引擎服务测试
# ===========================================

"""
发布引擎服务单元测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import asyncio

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.svc_publisher import (
    BasePublisher,
    SelfHostedPublisher,
    XimalayaPublisher,
    QingtingPublisher,
    PublisherService,
    PublishStatus,
)


class TestPublishStatus:
    """测试发布状态枚举"""

    def test_status_values(self):
        """测试状态值"""
        assert PublishStatus.PENDING.value == "pending"
        assert PublishStatus.PREPARING.value == "preparing"
        assert PublishStatus.PUBLISHING.value == "publishing"
        assert PublishStatus.PARTIAL_DONE.value == "partial_done"
        assert PublishStatus.DONE.value == "done"
        assert PublishStatus.FAILED.value == "failed"
        assert PublishStatus.CANCELLED.value == "cancelled"


class TestSelfHostedPublisher:
    """测试自建平台发布器"""

    @pytest.fixture
    def publisher(self):
        """创建发布器实例"""
        return SelfHostedPublisher()

    def test_channel_name(self, publisher):
        """测试渠道名称"""
        assert publisher.channel_name == "自建平台"

    def test_channel_code(self, publisher):
        """测试渠道代码"""
        assert publisher.channel_code == "self_hosted"

    @pytest.mark.asyncio
    async def test_create_album(self, publisher):
        """测试创建专辑"""
        book_data = {
            "id": 1,
            "title": "测试书籍",
            "author": "测试作者",
        }
        
        result = await publisher.create_album(book_data)
        
        assert result["album_id"] == "self_1"
        assert result["album_url"] == "/books/1/player"
        assert result["internal"] == True

    @pytest.mark.asyncio
    async def test_upload_chapter(self, publisher):
        """测试上传章节"""
        with patch("services.svc_publisher.get_storage_service") as mock_storage:
            mock_storage_instance = Mock()
            mock_storage_instance.get_presigned_url.return_value = "https://example.com/audio.mp3"
            mock_storage.return_value = mock_storage_instance
            
            chapter_data = {
                "id": 1,
                "audio_file_path": "chapters/1/test.mp3",
            }
            
            result = await publisher.upload_chapter(
                "self_1",
                chapter_data,
                b"audio_data",
            )
            
            assert "audio_id" in result
            assert "audio_url" in result

    @pytest.mark.asyncio
    async def test_publish_album(self, publisher):
        """测试发布专辑"""
        result = await publisher.publish_album("self_1")
        assert result == True


class TestPublisherService:
    """测试发布服务"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return PublisherService()

    def test_init(self, service):
        """测试初始化"""
        assert "self_hosted" in service.PUBLISHERS
        assert "ximalaya" in service.PUBLISHERS
        assert "qingting" in service.PUBLISHERS

    def test_get_publisher_self_hosted(self, service):
        """测试获取自建平台发布器"""
        publisher = service.get_publisher("self_hosted")
        assert isinstance(publisher, SelfHostedPublisher)

    def test_get_publisher_ximalaya(self, service):
        """测试获取喜马拉雅发布器"""
        publisher = service.get_publisher("ximalaya")
        assert isinstance(publisher, XimalayaPublisher)

    def test_get_publisher_invalid(self, service):
        """测试获取无效发布器"""
        publisher = service.get_publisher("invalid")
        assert publisher is None

    def test_list_available_channels(self, service):
        """测试列出可用渠道"""
        channels = service.list_available_channels()
        
        assert len(channels) == 3
        assert any(c["code"] == "self_hosted" for c in channels)
        assert any(c["code"] == "ximalaya" for c in channels)

    def test_calculate_progress(self, service):
        """测试计算进度"""
        # 创建模拟记录
        record = Mock()
        record.total_chapters = 10
        record.published_chapters = 5
        
        progress = service._calculate_progress(record)
        assert progress == 50.0

    def test_calculate_progress_zero(self, service):
        """测试零章节进度"""
        record = Mock()
        record.total_chapters = 0
        record.published_chapters = 0
        
        progress = service._calculate_progress(record)
        assert progress == 0.0


class TestPublisherIntegration:
    """测试发布集成"""

    @pytest.mark.asyncio
    async def test_full_publish_flow(self):
        """测试完整发布流程"""
        service = PublisherService()
        publisher = service.get_publisher("self_hosted")
        
        # 准备数据
        book_data = {
            "id": 1,
            "title": "测试书籍",
            "author": "测试作者",
        }
        
        # 创建专辑
        album_result = await publisher.create_album(book_data)
        assert album_result["album_id"] == "self_1"
        
        # 上传章节
        chapter_data = {
            "id": 1,
            "audio_file_path": "chapters/1/test.mp3",
        }
        
        with patch("services.svc_publisher.get_storage_service") as mock_storage:
            mock_storage_instance = Mock()
            mock_storage_instance.get_presigned_url.return_value = "https://example.com/audio.mp3"
            mock_storage.return_value = mock_storage_instance
            
            chapter_result = await publisher.upload_chapter(
                album_result["album_id"],
                chapter_data,
                b"audio_data",
            )
            
            assert "audio_id" in chapter_result
        
        # 发布
        publish_result = await publisher.publish_album(album_result["album_id"])
        assert publish_result == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
