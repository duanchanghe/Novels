# ===========================================
# 文件夹监听服务 - 增强版
# ===========================================

"""
文件夹监听服务 - 增强版

提供企业级的文件夹自动监听功能：
- 多目录监听支持（可配置多个监听目录）
- 文件就绪检测（等待写入完成）
- MD5 去重检测
- 文件锁机制（防止并发处理同一文件）
- 文件大小限制和告警
- 并发处理控制
- 监听状态可视化
- 容错和自动重启

配合 Celery Beat 定时扫描作为兜底方案。
"""

import logging
import os
import time
import hashlib
import threading
import fcntl
from typing import Optional, Callable, List, Dict, Any, Set
from threading import Thread, Event, Lock
from collections import deque
from datetime import datetime, timedelta

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from core.config import settings
from core.database import get_db_context


logger = logging.getLogger("audiobook")


class FileLock:
    """
    文件锁管理器

    使用 fcntl 实现跨进程文件锁，防止同一文件被并发处理。
    """

    def __init__(self, lock_dir: str = "/tmp/audiobook_locks"):
        self.lock_dir = lock_dir
        os.makedirs(lock_dir, exist_ok=True)

    def acquire(self, file_path: str, timeout: float = 30.0) -> bool:
        """
        获取文件锁

        Args:
            file_path: 文件路径
            timeout: 超时时间（秒）

        Returns:
            bool: 是否获取成功
        """
        lock_file = os.path.join(
            self.lock_dir,
            hashlib.md5(file_path.encode()).hexdigest() + ".lock"
        )

        lock_handle = open(lock_file, "w")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except IOError:
                time.sleep(0.1)

        lock_handle.close()
        return False

    def release(self, file_path: str) -> None:
        """
        释放文件锁

        Args:
            file_path: 文件路径
        """
        lock_file = os.path.join(
            self.lock_dir,
            hashlib.md5(file_path.encode()).hexdigest() + ".lock"
        )

        try:
            if os.path.exists(lock_file):
                os.unlink(lock_file)
        except Exception as e:
            logger.warning(f"释放文件锁失败: {e}")


class ProcessingQueue:
    """
    处理队列管理器

    控制并发处理数量，防止资源竞争。
    """

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._current = 0
        self._lock = Lock()
        self._condition = threading.Condition(self._lock)

    def acquire(self) -> bool:
        """
        获取处理名额

        Returns:
            bool: 是否获取成功
        """
        with self._lock:
            while self._current >= self.max_concurrent:
                self._condition.wait()

            if self._current < self.max_concurrent:
                self._current += 1
                return True
            return False

    def release(self) -> None:
        """
        释放处理名额
        """
        with self._lock:
            self._current -= 1
            self._condition.notify()

    @property
    def current(self) -> int:
        """当前处理数量"""
        return self._current

    @property
    def available(self) -> int:
        """可用名额"""
        return max(0, self.max_concurrent - self._current)


# 全局限流器和队列
_file_lock = FileLock()
_processing_queue = ProcessingQueue(max_concurrent=3)


class EPUBFileHandler(FileSystemEventHandler):
    """
    EPUB 文件事件处理器

    处理文件系统事件，检测新放入的 EPUB 文件。
    """

    def __init__(
        self,
        on_new_file: Callable[[str], None],
        watch_dirs: List[str],
    ):
        """
        初始化处理器

        Args:
            on_new_file: 新文件发现时的回调函数
            watch_dirs: 监听目录列表
        """
        self.on_new_file = on_new_file
        self.watch_dirs = set(watch_dirs)
        self.processed_files: Set[str] = set()
        self.processing_files: Set[str] = set()
        self._lock = Lock()

        # 统计信息
        self.stats = {
            "total_detected": 0,
            "total_processed": 0,
            "total_skipped": 0,
            "total_failed": 0,
            "last_processed": None,
        }

    def on_created(self, event: FileCreatedEvent):
        """文件创建事件处理"""
        self._handle_file_event(event.src_path)

    def on_modified(self, event: FileModifiedEvent):
        """文件修改事件处理（处理正在写入的文件）"""
        # 仅处理 EPUB 文件
        if not event.is_directory and event.src_path.lower().endswith(".epub"):
            self._handle_file_event(event.src_path)

    def _handle_file_event(self, file_path: str) -> None:
        """
        处理文件事件

        Args:
            file_path: 文件路径
        """
        # 目录检查
        if any(file_path.startswith(d) for d in self.watch_dirs):
            self._process_epub_file(file_path)

    def _process_epub_file(self, file_path: str) -> None:
        """
        处理 EPUB 文件事件

        Args:
            file_path: 文件路径
        """
        # 只处理 EPUB 文件
        if not file_path.lower().endswith(".epub"):
            return

        # 跳过临时文件
        if file_path.endswith(".part") or file_path.endswith(".tmp"):
            return

        with self._lock:
            # 检查是否已处理或正在处理
            if file_path in self.processed_files or file_path in self.processing_files:
                return

        logger.info(f"检测到 EPUB 文件: {file_path}")

        # 等待文件写入完成
        if not self._wait_for_file_ready(file_path):
            logger.warning(f"文件就绪检测超时，跳过: {file_path}")
            return

        # 等待处理名额
        if not _processing_queue.acquire():
            logger.warning(f"处理队列已满，等待处理名额: {file_path}")
            time.sleep(5)
            if not _processing_queue.acquire():
                logger.error(f"无法获取处理名额，跳过: {file_path}")
                return

        try:
            with self._lock:
                self.processing_files.add(file_path)

            self.stats["total_detected"] += 1
            self.on_new_file(file_path)

        finally:
            _processing_queue.release()

    def _wait_for_file_ready(
        self,
        file_path: str,
        timeout: int = 60,
        stable_checks: int = 3,
    ) -> bool:
        """
        等待文件写入完成

        Args:
            file_path: 文件路径
            timeout: 超时时间（秒）
            stable_checks: 连续稳定检查次数

        Returns:
            bool: 文件是否就绪
        """
        if not os.path.exists(file_path):
            return False

        # 检查文件大小限制
        try:
            file_size = os.path.getsize(file_path)
            max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # 默认 500MB
            if file_size > max_size:
                logger.error(f"文件超过大小限制 ({settings.MAX_FILE_SIZE_MB}MB): {file_path}")
                return False
        except OSError:
            return False

        last_size = -1
        stable_count = 0
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)

                if current_size == last_size:
                    stable_count += 1
                    if stable_count >= stable_checks:
                        logger.debug(f"文件就绪: {file_path} ({current_size} bytes)")
                        return True
                else:
                    stable_count = 0

                last_size = current_size
                time.sleep(1)

            except OSError:
                return False

        return False

    def mark_processed(self, file_path: str, success: bool = True) -> None:
        """
        标记文件已处理

        Args:
            file_path: 文件路径
            success: 是否成功处理
        """
        with self._lock:
            self.processing_files.discard(file_path)
            if success:
                self.processed_files.add(file_path)
                self.stats["total_processed"] += 1
                self.stats["last_processed"] = datetime.utcnow().isoformat()
            else:
                self.stats["total_failed"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            dict: 统计信息
        """
        with self._lock:
            return {
                **self.stats,
                "processing_count": len(self.processing_files),
                "processed_count": len(self.processed_files),
                "queue_available": _processing_queue.available,
                "queue_current": _processing_queue.current,
            }


class MultiDirectoryWatcher:
    """
    多目录监听管理器

    管理多个目录的监听服务。
    """

    def __init__(self):
        self.watch_dirs = self._parse_watch_dirs()
        self.observers: List[Observer] = []
        self.handler: Optional[EPUBFileHandler] = None
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._on_new_file_callback: Optional[Callable[[str], None]] = None

    def _parse_watch_dirs(self) -> List[str]:
        """
        解析监听目录配置

        支持从环境变量读取多个目录，逗号分隔。

        Returns:
            list: 目录列表
        """
        dirs_str = getattr(settings, "WATCH_DIRS", settings.WATCH_DIR)
        dirs = [d.strip() for d in dirs_str.split(",") if d.strip()]

        # 确保目录存在
        for d in dirs:
            if not os.path.exists(d):
                logger.warning(f"监听目录不存在: {d}，将自动创建")
                os.makedirs(d, exist_ok=True)

        return dirs

    def start(self) -> bool:
        """
        启动监听服务

        Returns:
            bool: 是否启动成功
        """
        if not getattr(settings, "WATCH_ENABLED", True):
            logger.info("文件夹监听已禁用")
            return True

        if self._thread and self._thread.is_alive():
            logger.warning("监听服务已在运行")
            return True

        try:
            self._on_new_file_callback = self._on_new_file
            self.handler = EPUBFileHandler(
                on_new_file=self._on_new_file_callback,
                watch_dirs=self.watch_dirs,
            )

            # 为每个目录创建观察者
            for watch_dir in self.watch_dirs:
                observer = Observer()
                observer.schedule(self.handler, watch_dir, recursive=False)
                observer.start()
                self.observers.append(observer)
                logger.info(f"监听目录: {watch_dir}")

            # 启动状态报告线程
            self._thread = Thread(target=self._status_reporter, daemon=True)
            self._thread.start()

            logger.info(f"文件夹监听服务已启动，共监听 {len(self.watch_dirs)} 个目录")
            return True

        except Exception as e:
            logger.error(f"启动监听服务失败: {e}")
            return False

    def stop(self) -> None:
        """停止监听服务"""
        self._stop_event.set()

        for observer in self.observers:
            observer.stop()

        for observer in self.observers:
            observer.join(timeout=5)

        self.observers.clear()
        logger.info("文件夹监听服务已停止")

    def _on_new_file(self, file_path: str) -> None:
        """
        新文件发现时的处理

        Args:
            file_path: 文件路径
        """
        logger.info(f"处理新 EPUB 文件: {file_path}")

        # 获取文件锁
        if not _file_lock.acquire(file_path, timeout=30):
            logger.warning(f"无法获取文件锁，跳过: {file_path}")
            return

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
                    if self.handler:
                        self.handler.mark_processed(file_path, success=True)
                    return

            # 触发处理任务
            from tasks.task_watch import process_new_epub
            process_new_epub.delay(file_path, file_hash)

            if self.handler:
                self.handler.mark_processed(file_path, success=True)

            logger.info(f"已提交处理任务: {file_path}")

        except Exception as e:
            logger.error(f"处理新文件失败: {file_path} - {e}")
            if self.handler:
                self.handler.mark_processed(file_path, success=False)

        finally:
            _file_lock.release(file_path)

    def _status_reporter(self) -> None:
        """定期报告监听状态"""
        interval = getattr(settings, "WATCH_STATUS_INTERVAL", 300)  # 默认5分钟

        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=interval)

            if self.handler:
                stats = self.handler.get_stats()
                logger.info(
                    f"监听状态: 检测={stats['total_detected']}, "
                    f"成功={stats['total_processed']}, "
                    f"失败={stats['total_failed']}, "
                    f"队列空闲={stats['queue_available']}"
                )

    def is_running(self) -> bool:
        """
        检查监听服务是否运行中

        Returns:
            bool: 是否运行中
        """
        return all(obs.is_alive() for obs in self.observers) if self.observers else False

    def get_status(self) -> Dict[str, Any]:
        """
        获取监听服务状态

        Returns:
            dict: 状态信息
        """
        handler_stats = self.handler.get_stats() if self.handler else {}

        return {
            "enabled": getattr(settings, "WATCH_ENABLED", True),
            "running": self.is_running(),
            "watch_dirs": self.watch_dirs,
            "observer_count": len(self.observers),
            **handler_stats,
        }


class WatcherHealthChecker:
    """
    监听服务健康检查器

    定期检查监听服务状态，异常时自动重启。
    """

    def __init__(self, watcher: MultiDirectoryWatcher):
        self.watcher = watcher
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._failure_count = 0
        self._max_failures = 3

    def start(self) -> None:
        """启动健康检查"""
        self._thread = Thread(target=self._health_check_loop, daemon=True)
        self._thread.start()
        logger.info("监听服务健康检查已启动")

    def stop(self) -> None:
        """停止健康检查"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("监听服务健康检查已停止")

    def _health_check_loop(self) -> None:
        """健康检查循环"""
        check_interval = 300  # 5分钟检查一次

        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=check_interval)

            if self._stop_event.is_set():
                break

            try:
                if not self.watcher.is_running():
                    self._handle_failure("监听服务已停止")
                elif self.watcher.handler:
                    stats = self.watcher.handler.get_stats()
                    if stats["total_failed"] > 10:
                        self._handle_failure(f"失败任务过多: {stats['total_failed']}")
                    else:
                        self._failure_count = 0
            except Exception as e:
                self._handle_failure(f"健康检查异常: {e}")

    def _handle_failure(self, reason: str) -> None:
        """
        处理故障

        Args:
            reason: 故障原因
        """
        self._failure_count += 1
        logger.warning(f"监听服务故障 ({self._failure_count}/{self._max_failures}): {reason}")

        if self._failure_count >= self._max_failures:
            logger.error("监听服务连续故障，尝试重启")
            try:
                self.watcher.stop()
                time.sleep(5)
                self.watcher.start()
                self._failure_count = 0
                logger.info("监听服务已重启")
            except Exception as e:
                logger.error(f"监听服务重启失败: {e}")


# 全局单例
_watcher_service: Optional[MultiDirectoryWatcher] = None
_health_checker: Optional[WatcherHealthChecker] = None


def get_watcher_service() -> MultiDirectoryWatcher:
    """
    获取监听服务实例

    Returns:
        MultiDirectoryWatcher: 监听服务实例
    """
    global _watcher_service, _health_checker

    if _watcher_service is None:
        _watcher_service = MultiDirectoryWatcher()
        _health_checker = WatcherHealthChecker(_watcher_service)

    return _watcher_service


def start_watcher() -> bool:
    """
    启动监听服务

    Returns:
        bool: 是否启动成功
    """
    watcher = get_watcher_service()
    success = watcher.start()

    if success and _health_checker:
        _health_checker.start()

    return success


def stop_watcher() -> None:
    """停止监听服务"""
    global _watcher_service, _health_checker

    if _health_checker:
        _health_checker.stop()

    if _watcher_service:
        _watcher_service.stop()
