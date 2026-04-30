# ===========================================
# 文件夹监听服务
# ===========================================

"""
文件夹监听服务

使用 watchdog 监听文件系统变化。
"""

import logging
import os
import time
import hashlib
from typing import Optional, Callable
from threading import Thread, Event

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from core.config import settings
from core.database import get_db_context


logger = logging.getLogger("audiobook")


class EPUBFileHandler(FileSystemEventHandler):
    """
    EPUB 文件事件处理器

    处理文件系统事件，检测新放入的 EPUB 文件。
    """

    def __init__(self, on_new_file: Callable[[str], None]):
        """
        初始化处理器

        Args:
            on_new_file: 新文件发现时的回调函数
        """
        self.on_new_file = on_new_file
        self.processed_files = set()

    def on_created(self, event: FileCreatedEvent):
        """
        文件创建事件处理

        Args:
            event: 文件创建事件
        """
        if event.is_directory:
            return

        file_path = event.src_path

        # 只处理 EPUB 文件
        if not file_path.lower().endswith(".epub"):
            return

        # 跳过临时文件
        if file_path.endswith(".part") or file_path.endswith(".tmp"):
            return

        logger.info(f"检测到新 EPUB 文件: {file_path}")

        # 等待文件写入完成
        if self._wait_for_file_ready(file_path):
            self.on_new_file(file_path)
        else:
            logger.warning(f"文件就绪检测超时，跳过: {file_path}")

    def _wait_for_file_ready(self, file_path: str, timeout: int = 60) -> bool:
        """
        等待文件写入完成

        Args:
            file_path: 文件路径
            timeout: 超时时间（秒）

        Returns:
            bool: 文件是否就绪
        """
        if not os.path.exists(file_path):
            return False

        last_size = -1
        stable_count = 0
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)

                if current_size == last_size:
                    stable_count += 1
                    if stable_count >= 3:  # 连续3次大小不变
                        return True
                else:
                    stable_count = 0

                last_size = current_size
                time.sleep(1)

            except OSError:
                return False

        return False


class FileWatcherService:
    """
    文件夹监听服务

    使用 watchdog 库监听文件夹变化。
    """

    def __init__(self):
        self.watch_dir = settings.WATCH_DIR
        self.enabled = settings.WATCH_ENABLED
        self.observer: Optional[Observer] = None
        self.handler: Optional[EPUBFileHandler] = None
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    def start(self) -> bool:
        """
        启动监听服务

        Returns:
            bool: 是否启动成功
        """
        if not self.enabled:
            logger.info("文件夹监听已禁用")
            return True

        if not os.path.exists(self.watch_dir):
            logger.warning(f"监听目录不存在: {self.watch_dir}")
            # 创建目录
            os.makedirs(self.watch_dir, exist_ok=True)
            logger.info(f"已创建监听目录: {self.watch_dir}")

        if self.observer and self.observer.is_alive():
            logger.warning("监听服务已在运行")
            return True

        try:
            self.handler = EPUBFileHandler(on_new_file=self._on_new_file)
            self.observer = Observer()
            self.observer.schedule(self.handler, self.watch_dir, recursive=False)
            self.observer.start()

            logger.info(f"文件夹监听服务已启动: {self.watch_dir}")
            return True

        except Exception as e:
            logger.error(f"启动监听服务失败: {e}")
            return False

    def stop(self) -> None:
        """停止监听服务"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("文件夹监听服务已停止")

    def _on_new_file(self, file_path: str) -> None:
        """
        新文件发现时的处理

        Args:
            file_path: 文件路径
        """
        logger.info(f"处理新 EPUB 文件: {file_path}")

        try:
            # 计算文件哈希
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

            # 检查是否已处理
            with get_db_context() as db:
                from models import Book, BookStatus

                existing = (
                    db.query(Book)
                    .filter(Book.file_hash == file_hash)
                    .filter(Book.status != BookStatus.FAILED)
                    .first()
                )

                if existing:
                    logger.info(f"文件已处理过，跳过: {file_path}")
                    return

            # 触发处理任务
            from tasks.task_watch import process_new_epub
            process_new_epub.delay(file_path, file_hash)

            logger.info(f"已提交处理任务: {file_path}")

        except Exception as e:
            logger.error(f"处理新文件失败: {file_path} - {e}")

    def is_running(self) -> bool:
        """
        检查监听服务是否运行中

        Returns:
            bool: 是否运行中
        """
        return self.observer is not None and self.observer.is_alive()

    def get_status(self) -> dict:
        """
        获取监听服务状态

        Returns:
            dict: 状态信息
        """
        return {
            "enabled": self.enabled,
            "running": self.is_running(),
            "watch_dir": self.watch_dir,
        }


# 全局单例
_watcher_service: Optional[FileWatcherService] = None


def get_watcher_service() -> FileWatcherService:
    """
    获取监听服务实例

    Returns:
        FileWatcherService: 监听服务实例
    """
    global _watcher_service
    if _watcher_service is None:
        _watcher_service = FileWatcherService()
    return _watcher_service
