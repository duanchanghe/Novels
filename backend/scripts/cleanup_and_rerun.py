#!/usr/bin/env python3
"""
清理并重新处理书籍前3章的脚本
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from core.models import Book, Chapter, AudioSegment
from core.models.book import BookStatus
from core.models.chapter import ChapterStatus
from core.models.segment import SegmentStatus
from tasks.task_pipeline import process_chapter


def cleanup_and_rerun(book_id: int = None, num_chapters: int = 3):
    """
    清理书籍章节数据并重新处理

    Args:
        book_id: 书籍ID，如果不提供则取最新的一本书
        num_chapters: 要处理的章节数（默认前3章）
    """
    # 获取书籍
    if book_id:
        book = Book.objects.filter(id=book_id).first()
        if not book:
            print(f"书籍不存在: {book_id}")
            return
    else:
        # 取最新的书籍
        book = Book.objects.order_by('-id').first()
        if not book:
            print("没有找到任何书籍")
            return

    print(f"=" * 60)
    print(f"书籍: {book.title} (ID: {book.id})")
    print(f"状态: {book.status}")
    print(f"=" * 60)

    # 获取前N章
    chapters = Chapter.objects.filter(
        book_id=book.id
    ).order_by('chapter_index')[:num_chapters]

    if not chapters:
        print(f"该书没有章节")
        return

    print(f"\n前 {len(chapters)} 章:")

    for ch in chapters:
        # 删除原有音频片段
        deleted_count = AudioSegment.objects.filter(chapter_id=ch.id).delete()[0]
        print(f"  - 第{ch.chapter_index}章: {ch.title}")
        print(f"    删除 {deleted_count} 个音频片段")

        # 重置章节状态
        ch.status = ChapterStatus.PENDING
        ch.error_message = None
        ch.failed_segments = 0
        ch.total_segments = 0
        ch.completed_segments = 0
        ch.audio_file_path = None
        ch.audio_url = None
        ch.audio_duration = None
        ch.audio_file_size = None
        ch.analysis_result = None
        ch.characters = None
        ch.save()

    # 重置书籍状态
    book.status = BookStatus.PENDING
    book.processed_chapters = 0
    book.error_message = None
    book.save()

    print(f"\n数据已清理，准备触发处理...")

    # 触发处理
    for ch in chapters:
        print(f"触发处理: 第{ch.chapter_index}章 - {ch.title}")
        process_chapter.delay(ch.id)

    print(f"\n完成! 已触发 {len(chapters)} 个章节处理任务")
    print("查看 Celery 日志获取处理进度")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清理并重新处理书籍章节")
    parser.add_argument("--book-id", type=int, help="书籍ID（不提供则取最新书籍）")
    parser.add_argument("--chapters", type=int, default=3, help="处理的章节数（默认3）")

    args = parser.parse_args()

    cleanup_and_rerun(book_id=args.book_id, num_chapters=args.chapters)
