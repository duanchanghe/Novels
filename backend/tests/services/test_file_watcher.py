# ===========================================
# 文件夹监听服务测试
# ===========================================

"""
文件夹监听服务单元测试
"""

import pytest
import tempfile
import os
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from threading import Event

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.svc_file_watcher import (
    FileLock,
    ProcessingQueue,
    EPUBFileHandler,
    MultiDirectoryWatcher,
)


class TestFileLock:
    """测试文件锁"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_init(self, temp_dir):
        """测试初始化"""
        lock = FileLock(lock_dir=temp_dir)
        assert os.path.exists(temp_dir)

    def test_acquire_release(self, temp_dir):
        """测试获取和释放锁"""
        lock = FileLock(lock_dir=temp_dir)
        file_path = "/test/file.txt"
        
        # 获取锁
        result = lock.acquire(file_path, timeout=1.0)
        assert result == True
        
        # 释放锁
        lock.release(file_path)
        
        # 再次获取应该成功
        result = lock.acquire(file_path, timeout=1.0)
        assert result == True

    def test_concurrent_access(self, temp_dir):
        """测试并发访问"""
        lock = FileLock(lock_dir=temp_dir)
        file_path = "/test/concurrent.txt"
        
        acquired = [False]
        
        def try_acquire():
            result = lock.acquire(file_path, timeout=0.5)
            acquired[0] = result
            if result:
                time.sleep(0.2)
                lock.release(file_path)
        
        # 第一次获取
        result1 = lock.acquire(file_path, timeout=1.0)
        assert result1 == True
        
        # 第二次获取应该超时
        start = time.time()
        result2 = lock.acquire(file_path, timeout=0.3)
        elapsed = time.time() - start
        
        assert result2 == False
        assert elapsed >= 0.3


class TestProcessingQueue:
    """测试处理队列"""

    def test_init(self):
        """测试初始化"""
        queue = ProcessingQueue(max_concurrent=3)
        assert queue.max_concurrent == 3
        assert queue.current == 0
        assert queue.available == 3

    def test_acquire_release(self):
        """测试获取和释放"""
        queue = ProcessingQueue(max_concurrent=2)
        
        # 获取名额
        result1 = queue.acquire()
        assert result1 == True
        assert queue.current == 1
        assert queue.available == 1
        
        # 再次获取
        result2 = queue.acquire()
        assert result2 == True
        assert queue.current == 2
        assert queue.available == 0
        
        # 第三次获取应该失败
        result3 = queue.acquire()
        assert result3 == False
        
        # 释放
        queue.release()
        assert queue.current == 1
        assert queue.available == 1


class TestEPUBFileHandler:
    """测试 EPUB 文件处理器"""

    @pytest.fixture
    def handler(self):
        """创建处理器实例"""
        callback = Mock()
        return EPUBFileHandler(
            on_new_file=callback,
            watch_dirs=["/test/watch"],
        )

    def test_init(self, handler):
        """测试初始化"""
        assert handler.on_new_file is not None
        assert "/test/watch" in handler.watch_dirs
        assert len(handler.processed_files) == 0

    def test_wait_for_file_ready_success(self, handler, tmp_path):
        """测试文件就绪检测成功"""
        test_file = tmp_path / "test.epub"
        test_file.write_bytes(b"test content")
        
        result = handler._wait_for_file_ready(str(test_file), timeout=5)
        assert result == True

    def test_wait_for_file_ready_timeout(self, handler):
        """测试文件就绪检测超时"""
        result = handler._wait_for_file_ready("/nonexistent/file.epub", timeout=1)
        assert result == False

    def test_process_epub_file(self, handler, tmp_path):
        """测试处理 EPUB 文件"""
        test_file = tmp_path / "test.epub"
        test_file.write_bytes(b"test epub content")
        
        # 模拟等待就绪
        with patch.object(handler, "_wait_for_file_ready", return_value=True):
            with patch.object(handler, "_processing_queue") as mock_queue:
                mock_queue.acquire = Mock(return_value=True)
                handler._process_epub_file(str(test_file))

    def test_mark_processed(self, handler):
        """测试标记文件已处理"""
        handler.mark_processed("/test/file.epub", success=True)
        assert "/test/file.epub" in handler.processed_files
        
        stats = handler.get_stats()
        assert stats["total_processed"] == 1

    def test_get_stats(self, handler):
        """测试获取统计信息"""
        handler.mark_processed("/test/file1.epub", success=True)
        handler.mark_processed("/test/file2.epub", success=True)
        handler.mark_processed("/test/file3.epub", success=False)
        
        stats = handler.get_stats()
        assert stats["total_processed"] == 2
        assert stats["total_failed"] == 1


class TestMultiDirectoryWatcher:
    """测试多目录监听器"""

    @pytest.fixture
    def watcher(self):
        """创建监听器实例"""
        return MultiDirectoryWatcher()

    def test_init(self, watcher):
        """测试初始化"""
        assert isinstance(watcher.watch_dirs, list)
        assert watcher.observers == []

    @patch("services.svc_file_watcher.settings")
    def test_start_stop(self, mock_settings, watcher):
        """测试启动和停止"""
        mock_settings.WATCH_ENABLED = False
        
        # 启动
        result = watcher.start()
        assert result == True
        
        # 停止
        watcher.stop()
        assert watcher.observers == []

    def test_is_running(self, watcher):
        """测试运行状态检查"""
        assert watcher.is_running() == False

    def test_get_status(self, watcher):
        """测试获取状态"""
        status = watcher.get_status()
        
        assert "enabled" in status
        assert "running" in status
        assert "watch_dirs" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
