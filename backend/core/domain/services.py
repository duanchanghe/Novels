# ===========================================
# 领域服务
# ===========================================

"""
领域服务 - 封装核心业务逻辑

领域服务用于：
1. 协调多个领域对象
2. 实现不属于单一实体的业务逻辑
3. 封装领域级别的操作
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import (
    BookModel,
    ChapterModel,
    SegmentModel,
    BookStatus,
    ChapterStatus,
    SegmentStatus,
)
from .events import (
    BookCreatedEvent,
    BookCompletedEvent,
    ChapterAnalyzedEvent,
    ChapterCompletedEvent,
    SegmentSynthesizedEvent,
)


class BookDomainService:
    """
    书籍领域服务

    处理书籍相关的领域逻辑：
    - 状态流转验证
    - 进度计算
    - 事件发布
    """

    @staticmethod
    def can_transition(book: BookModel, new_status: BookStatus) -> bool:
        """
        检查状态是否可转换

        Args:
            book: 书籍模型
            new_status: 目标状态

        Returns:
            bool: 是否可转换
        """
        valid_transitions = {
            BookStatus.PENDING: [BookStatus.ANALYZING, BookStatus.FAILED],
            BookStatus.ANALYZING: [BookStatus.SYNTHESIZING, BookStatus.FAILED],
            BookStatus.SYNTHESIZING: [BookStatus.POST_PROCESSING, BookStatus.FAILED],
            BookStatus.POST_PROCESSING: [BookStatus.PUBLISHING, BookStatus.FAILED],
            BookStatus.PUBLISHING: [BookStatus.DONE, BookStatus.FAILED],
            BookStatus.DONE: [BookStatus.PENDING],  # 允许重新生成
            BookStatus.FAILED: [BookStatus.PENDING],  # 允许重试
        }

        return new_status in valid_transitions.get(book.status, [])

    @staticmethod
    def calculate_progress(book: BookModel) -> float:
        """
        计算处理进度

        Args:
            book: 书籍模型

        Returns:
            float: 进度百分比 (0-100)
        """
        if book.total_chapters == 0:
            return 0.0
        return round((book.processed_chapters / book.total_chapters) * 100, 2)

    @staticmethod
    def is_completed(book: BookModel) -> bool:
        """检查书籍是否完成"""
        return book.status == BookStatus.DONE

    @staticmethod
    def is_failed(book: BookModel) -> bool:
        """检查书籍是否失败"""
        return book.status == BookStatus.FAILED

    @staticmethod
    def is_processing(book: BookModel) -> bool:
        """检查书籍是否正在处理"""
        return book.status in [
            BookStatus.ANALYZING,
            BookStatus.SYNTHESIZING,
            BookStatus.POST_PROCESSING,
            BookStatus.PUBLISHING,
        ]

    @staticmethod
    def create_created_event(book: BookModel) -> BookCreatedEvent:
        """创建书籍创建事件"""
        return BookCreatedEvent(
            aggregate_id=book.id,
            title=book.title,
            author=book.author,
            source_type=book.source_type,
        )

    @staticmethod
    def create_completed_event(book: BookModel) -> BookCompletedEvent:
        """创建书籍完成事件"""
        return BookCompletedEvent(
            aggregate_id=book.id,
            title=book.title,
            total_chapters=book.total_chapters,
            total_duration=book.total_duration,
        )


class ChapterDomainService:
    """
    章节领域服务

    处理章节相关的领域逻辑：
    - 状态流转验证
    - 进度计算
    - 事件发布
    """

    @staticmethod
    def can_transition(chapter: ChapterModel, new_status: ChapterStatus) -> bool:
        """
        检查状态是否可转换

        Args:
            chapter: 章节模型
            new_status: 目标状态

        Returns:
            bool: 是否可转换
        """
        valid_transitions = {
            ChapterStatus.PENDING: [
                ChapterStatus.ANALYZING,
                ChapterStatus.AWAITING_CONFIRM,
                ChapterStatus.FAILED,
            ],
            ChapterStatus.ANALYZING: [
                ChapterStatus.ANALYZED,
                ChapterStatus.FAILED,
            ],
            ChapterStatus.ANALYZED: [
                ChapterStatus.SYNTHESIZING,
                ChapterStatus.FAILED,
            ],
            ChapterStatus.SYNTHESIZING: [
                ChapterStatus.DONE,
                ChapterStatus.FAILED,
            ],
            ChapterStatus.AWAITING_CONFIRM: [
                ChapterStatus.PENDING,
                ChapterStatus.FAILED,
            ],
            ChapterStatus.DONE: [],  # 终态
            ChapterStatus.FAILED: [
                ChapterStatus.PENDING,
            ],  # 允许重试
        }

        return new_status in valid_transitions.get(chapter.status, [])

    @staticmethod
    def calculate_progress(chapter: ChapterModel) -> float:
        """
        计算处理进度

        Args:
            chapter: 章节模型

        Returns:
            float: 进度百分比 (0-100)
        """
        if chapter.total_segments == 0:
            return 0.0
        return round(
            (chapter.completed_segments / chapter.total_segments) * 100, 2
        )

    @staticmethod
    def is_completed(chapter: ChapterModel) -> bool:
        """检查章节是否完成"""
        return chapter.status == ChapterStatus.DONE

    @staticmethod
    def is_failed(chapter: ChapterModel) -> bool:
        """检查章节是否失败"""
        return chapter.status == ChapterStatus.FAILED

    @staticmethod
    def create_analyzed_event(chapter: ChapterModel) -> ChapterAnalyzedEvent:
        """创建章节分析完成事件"""
        # 统计本章角色数
        char_count = len(chapter.characters) if chapter.characters else 0
        if char_count == 0:
            char_count = len(chapter.characters) if chapter.characters else 0
        return ChapterAnalyzedEvent(
            aggregate_id=chapter.id,
            book_id=chapter.book_id,
            chapter_index=chapter.chapter_index,
            character_count=char_count,
        )

    @staticmethod
    def create_completed_event(chapter: ChapterModel) -> ChapterCompletedEvent:
        """创建章节完成事件"""
        return ChapterCompletedEvent(
            aggregate_id=chapter.id,
            book_id=chapter.book_id,
            chapter_index=chapter.chapter_index,
            audio_duration=chapter.audio_duration or 0,
            segment_count=chapter.total_segments,
        )


class SegmentDomainService:
    """
    音频片段领域服务

    处理音频片段相关的领域逻辑：
    - 状态流转验证
    - 成本计算
    - 事件发布
    """

    @staticmethod
    def can_transition(segment: SegmentModel, new_status: SegmentStatus) -> bool:
        """
        检查状态是否可转换

        Args:
            segment: 片段模型
            new_status: 目标状态

        Returns:
            bool: 是否可转换
        """
        valid_transitions = {
            SegmentStatus.PENDING: [
                SegmentStatus.SYNTHESIZING,
                SegmentStatus.FAILED,
            ],
            SegmentStatus.SYNTHESIZING: [
                SegmentStatus.SUCCESS,
                SegmentStatus.FAILED,
            ],
            SegmentStatus.SUCCESS: [],  # 终态
            SegmentStatus.FAILED: [
                SegmentStatus.PENDING,
            ],  # 允许重试
        }

        return new_status in valid_transitions.get(segment.status, [])

    @staticmethod
    def calculate_cost(segment: SegmentModel) -> Dict[str, int]:
        """
        计算片段成本

        Args:
            segment: 片段模型

        Returns:
            dict: 成本统计
        """
        return {
            "minimax_cost": segment.minimax_cost,
            "deepseek_cost": segment.deepseek_cost,
            "total_cost": segment.minimax_cost + segment.deepseek_cost,
        }

    @staticmethod
    def is_completed(segment: SegmentModel) -> bool:
        """检查片段是否完成"""
        return segment.status == SegmentStatus.SUCCESS

    @staticmethod
    def is_failed(segment: SegmentModel) -> bool:
        """检查片段是否失败"""
        return segment.status == SegmentStatus.FAILED

    @staticmethod
    def can_retry(segment: SegmentModel, max_retries: int = 5) -> bool:
        """
        检查是否可重试

        Args:
            segment: 片段模型
            max_retries: 最大重试次数

        Returns:
            bool: 是否可重试
        """
        return (
            segment.status == SegmentStatus.FAILED
            and segment.retry_count < max_retries
        )

    @staticmethod
    def create_synthesized_event(
        segment: SegmentModel,
    ) -> SegmentSynthesizedEvent:
        """创建片段合成完成事件"""
        return SegmentSynthesizedEvent(
            aggregate_id=segment.id,
            chapter_id=segment.chapter_id,
            segment_index=segment.segment_index,
            audio_duration_ms=segment.audio_duration_ms or 0,
            voice_id=segment.voice_id,
        )


class PipelineDomainService:
    """
    流水线领域服务

    处理流水线级别的领域逻辑：
    - 阶段协调
    - 依赖管理
    - 错误处理策略
    """

    # 流水线阶段定义
    STAGES = [
        "parsing",
        "preprocessing",
        "analyzing",
        "creating_segments",
        "synthesizing",
        "postprocessing",
        "publishing",
    ]

    @staticmethod
    def get_next_stage(current_stage: str) -> Optional[str]:
        """
        获取下一阶段

        Args:
            current_stage: 当前阶段

        Returns:
            Optional[str]: 下一阶段，如果没有则返回 None
        """
        try:
            current_idx = PipelineDomainService.STAGES.index(current_stage)
            if current_idx + 1 < len(PipelineDomainService.STAGES):
                return PipelineDomainService.STAGES[current_idx + 1]
        except ValueError:
            pass
        return None

    @staticmethod
    def get_stage_order(stage: str) -> int:
        """
        获取阶段顺序

        Args:
            stage: 阶段名称

        Returns:
            int: 阶段顺序（从 0 开始）
        """
        try:
            return PipelineDomainService.STAGES.index(stage)
        except ValueError:
            return -1

    @staticmethod
    def should_retry(error: Exception) -> bool:
        """
        判断错误是否应重试

        Args:
            error: 异常对象

        Returns:
            bool: 是否应重试
        """
        # 网络错误应重试
        retryable_errors = [
            "ConnectionError",
            "TimeoutError",
            "HTTPError",
        ]

        error_type = type(error).__name__
        return error_type in retryable_errors

    @staticmethod
    def calculate_retry_delay(retry_count: int, base_delay: float = 1.0) -> float:
        """
        计算重试延迟（指数退避）

        Args:
            retry_count: 当前重试次数
            base_delay: 基础延迟（秒）

        Returns:
            float: 延迟时间（秒）
        """
        # 指数退避，最大 120 秒
        delay = min(base_delay * (2**retry_count), 120)
        # 添加随机抖动 (±25%)
        import random
        jitter = delay * 0.25 * (random.random() * 2 - 1)
        return delay + jitter
