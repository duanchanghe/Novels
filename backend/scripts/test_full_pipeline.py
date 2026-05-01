# ===========================================
# 全链路集成测试脚本
# ===========================================

"""
全链路端到端测试脚本

测试从 EPUB 上传到有声书生成、发布的完整流程。
包含各模块的性能基准测试和稳定性测试。
"""

import asyncio
import sys
import time
import os
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from core.database import get_db_context, engine, Base
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("audiobook.e2e.test")


@dataclass
class StageResult:
    """阶段测试结果"""
    name: str
    success: bool
    duration: float
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    # 性能基准数据
    baseline_duration: float = 0.0  # 基准耗时
    acceptable_duration: float = 0.0  # 可接受耗时
    performance_rating: str = "unknown"  # 性能评级: excellent/good/acceptable/poor

    def evaluate_performance(self) -> str:
        """评估性能评级"""
        if self.duration == 0 or self.baseline_duration == 0:
            self.performance_rating = "unknown"
            return self.performance_rating

        ratio = self.duration / self.baseline_duration
        if ratio <= 1.0:
            self.performance_rating = "excellent"
        elif ratio <= 1.5:
            self.performance_rating = "good"
        elif ratio <= 2.0:
            self.performance_rating = "acceptable"
        else:
            self.performance_rating = "poor"
        return self.performance_rating


@dataclass
class TestReport:
    """测试报告"""
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    stages: List[StageResult] = field(default_factory=list)
    overall_success: bool = True
    total_duration: float = 0.0

    # 性能基准配置
    performance_baselines: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "Database Connection": {"baseline": 0.1, "acceptable": 0.5},
        "MinIO Connection": {"baseline": 0.2, "acceptable": 1.0},
        "Redis/Celery Connection": {"baseline": 0.1, "acceptable": 0.5},
        "EPUB Parsing": {"baseline": 1.0, "acceptable": 5.0},
        "Text Preprocessing": {"baseline": 0.5, "acceptable": 2.0},
        "DeepSeek Analysis": {"baseline": 2.0, "acceptable": 10.0},
        "MiniMax TTS": {"baseline": 3.0, "acceptable": 15.0},
        "Audio Postprocessing": {"baseline": 2.0, "acceptable": 10.0},
    })

    def add_stage(self, stage: StageResult):
        # 设置性能基准
        if stage.name in self.performance_baselines:
            baseline_config = self.performance_baselines[stage.name]
            stage.baseline_duration = baseline_config.get("baseline", 0)
            stage.acceptable_duration = baseline_config.get("acceptable", 0)
            stage.evaluate_performance()

        self.stages.append(stage)
        if not stage.success:
            self.overall_success = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration": self.total_duration,
            "overall_success": self.overall_success,
            "performance_summary": self._get_performance_summary(),
            "stages": [
                {
                    "name": s.name,
                    "success": s.success,
                    "duration": round(s.duration, 3),
                    "baseline": s.baseline_duration,
                    "acceptable": s.acceptable_duration,
                    "performance_rating": s.performance_rating,
                    "message": s.message,
                    "errors": s.errors,
                    "data": s.data,
                }
                for s in self.stages
            ],
        }

    def _get_performance_summary(self) -> Dict[str, Any]:
        """获取性能汇总"""
        if not self.stages:
            return {}

        ratings = {}
        for stage in self.stages:
            if stage.performance_rating != "unknown":
                ratings[stage.performance_rating] = ratings.get(stage.performance_rating, 0) + 1

        total_rated = sum(ratings.values())
        return {
            "total_stages": len(self.stages),
            "rated_stages": total_rated,
            "rating_distribution": ratings,
            "average_duration": round(sum(s.duration for s in self.stages) / len(self.stages), 3) if self.stages else 0,
            "slowest_stage": max(self.stages, key=lambda s: s.duration).name if self.stages else None,
            "slowest_duration": round(max(s.duration for s in self.stages), 3) if self.stages else 0,
        }


class FullPipelineIntegrationTest:
    """
    全链路集成测试运行器

    测试完整的有声书生成流程，包括：
    1. 数据库连接
    2. MinIO 连接
    3. Redis/Celery 连接
    4. EPUB 解析
    5. 文本预处理
    6. DeepSeek 分析
    7. MiniMax TTS 合成
    8. 音频后处理
    9. 完整流水线串联
    """

    def __init__(self):
        self.report = TestReport(
            test_name="Full Pipeline Integration Test",
            start_time=datetime.now(),
        )
        self.test_epub_path: Optional[str] = None

    def _create_test_epub(self) -> str:
        """创建测试用 EPUB 文件"""
        try:
            import zipfile
            from io import BytesIO

            # 创建临时 EPUB 文件
            epub_content = self._generate_simple_epub()

            # 写入临时文件
            temp_dir = tempfile.gettempdir()
            epub_path = os.path.join(temp_dir, f"test_audiobook_{int(time.time())}.epub")

            with open(epub_path, "wb") as f:
                f.write(epub_content)

            logger.info(f"创建测试 EPUB 文件: {epub_path}")
            return epub_path

        except Exception as e:
            logger.error(f"创建测试 EPUB 失败: {e}")
            raise

    def _generate_simple_epub(self) -> bytes:
        """生成简单的测试用 EPUB 内容"""
        try:
            import zipfile
            from io import BytesIO

            buffer = BytesIO()

            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                # mimetype (不压缩)
                zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

                # META-INF/container.xml
                container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
                zf.writestr("META-INF/container.xml", container_xml)

                # OEBPS/content.opf
                content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>测试有声书</dc:title>
    <dc:creator>测试作者</dc:creator>
    <dc:language>zh-CN</dc:language>
    <dc:identifier id="uid">test-book-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
    <itemref idref="chapter2"/>
  </spine>
</package>'''
                zf.writestr("OEBPS/content.opf", content_opf)

                # OEBPS/nav.xhtml
                nav_xhtml = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>目录</title></head>
<body>
  <nav epub:type="toc">
    <h1>目录</h1>
    <ol>
      <li><a href="chapter1.xhtml">第一章 测试</a></li>
      <li><a href="chapter2.xhtml">第二章 对话</a></li>
    </ol>
  </nav>
</body>
</html>'''
                zf.writestr("OEBPS/nav.xhtml", nav_xhtml)

                # OEBPS/chapter1.xhtml
                chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>第一章 测试</title></head>
<body>
  <h1>第一章 测试</h1>
  <p>这是一个测试章节，用于验证有声书生成流程。</p>
  <p>2024年3月5日下午2点30分，天气晴朗。</p>
  <p>张三来到银行办理业务。</p>
  <p>"你好，我想要开户。"他说道。</p>
  <p>百分比是50%，小数是3.14。</p>
</body>
</html>'''
                zf.writestr("OEBPS/chapter1.xhtml", chapter1)

                # OEBPS/chapter2.xhtml
                chapter2 = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>第二章 对话</title></head>
<body>
  <h1>第二章 对话</h1>
  <p>李四走进房间，看见王五正在窗边站着。</p>
  <p>"你在这里做什么？"李四问道。</p>
  <p>王五转过身来，脸上带着微笑。</p>
  <p>"我在等你。"他回答。</p>
  <p>"太好了，我正需要你的帮助。"李四说道。</p>
</body>
</html>'''
                zf.writestr("OEBPS/chapter2.xhtml", chapter2)

            return buffer.getvalue()

        except Exception as e:
            logger.error(f"生成 EPUB 内容失败: {e}")
            raise

    # ===========================================
    # 测试阶段
    # ===========================================

    async def test_database_connection(self) -> StageResult:
        """测试数据库连接"""
        name = "Database Connection"
        start = time.perf_counter()

        try:
            with get_db_context() as db:
                result = db.execute("SELECT 1")
                assert result is not None

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message="数据库连接成功",
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"数据库连接失败: {e}",
                errors=[str(e)],
            )

    async def test_minio_connection(self) -> StageResult:
        """测试 MinIO 连接"""
        name = "MinIO Connection"
        start = time.perf_counter()

        try:
            from services.svc_minio_storage import get_storage_service

            storage = get_storage_service()
            storage.initialize()

            # 尝试列出 buckets
            buckets = storage.list_buckets()
            logger.info(f"MinIO 连接成功，当前 buckets: {buckets}")

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"MinIO 连接成功",
                data={"buckets": buckets},
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"MinIO 连接失败: {e}",
                errors=[str(e)],
            )

    async def test_redis_celery(self) -> StageResult:
        """测试 Redis 和 Celery 连接"""
        name = "Redis/Celery Connection"
        start = time.perf_counter()

        try:
            import redis
            from tasks.celery_app import celery_app

            # 测试 Redis 连接
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            r = redis.from_url(redis_url)
            r.ping()

            # 测试 Celery
            inspect = celery_app.control.inspect()
            stats = inspect.stats()

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"Redis 和 Celery 连接成功",
                data={"celery_stats": stats},
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"Redis/Celery 连接失败: {e}",
                errors=[str(e)],
            )

    async def test_epub_parsing(self) -> StageResult:
        """测试 EPUB 解析"""
        name = "EPUB Parsing"
        start = time.perf_counter()

        try:
            # 创建测试 EPUB
            epub_path = self._create_test_epub()
            self.test_epub_path = epub_path

            from services.svc_epub_parser import EPUBParserService

            parser = EPUBParserService()
            result = parser.parse_file(epub_path)

            assert result.get("title"), "缺少书名"
            assert result.get("chapters"), "缺少章节"
            assert len(result["chapters"]) > 0, "章节列表为空"

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"EPUB 解析成功: {result['title']}, {len(result['chapters'])} 章节",
                data={
                    "title": result.get("title"),
                    "chapter_count": len(result["chapters"]),
                    "author": result.get("author"),
                },
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"EPUB 解析失败: {e}",
                errors=[str(e)],
            )

    async def test_text_preprocessing(self) -> StageResult:
        """测试文本预处理"""
        name = "Text Preprocessing"
        start = time.perf_counter()

        try:
            from services.svc_text_preprocessor import TextPreprocessorService

            test_text = """
            2024年3月5日下午2点30分，张三来到银行。
            "你好，我想要开户。"他说。
            百分比是50%，小数是3.14。
            """

            preprocessor = TextPreprocessorService()

            # 规范化
            normalized = preprocessor.normalize_text(test_text)
            assert normalized, "规范化结果为空"

            # 段落拆分
            paragraphs = preprocessor.split_paragraphs(normalized)
            assert len(paragraphs) > 0, "段落拆分失败"

            # TTS 准备
            prepared = preprocessor.prepare_for_tts(test_text)
            assert "processed_text" in prepared, "TTS 准备结果缺少字段"

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"文本预处理成功: {len(paragraphs)} 段落",
                data={"paragraph_count": len(paragraphs)},
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"文本预处理失败: {e}",
                errors=[str(e)],
            )

    async def test_deepseek_analysis(self) -> StageResult:
        """测试 DeepSeek 分析"""
        name = "DeepSeek Analysis"
        start = time.perf_counter()

        if not settings.DEEPSEEK_API_KEY:
            return StageResult(
                name=name,
                success=True,
                duration=0,
                message="DeepSeek API Key 未配置，跳过测试",
            )

        try:
            from services.svc_deepseek_analyzer import DeepSeekAnalyzerService

            test_text = """
            李四走进房间，看见王五正在窗边站着。
            "你在这里做什么？"李四问道。
            王五转过身来，脸上带着微笑。
            "我在等你。"他回答。
            """

            analyzer = DeepSeekAnalyzerService()
            result = analyzer.analyze_chapter(test_text)

            assert "paragraphs" in result or "characters" in result, "分析结果缺少必要字段"

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"DeepSeek 分析成功",
                data={"characters": result.get("characters", [])},
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"DeepSeek 分析失败: {e}",
                errors=[str(e)],
            )

    async def test_minimax_tts(self) -> StageResult:
        """测试 MiniMax TTS"""
        name = "MiniMax TTS"
        start = time.perf_counter()

        if not settings.MINIMAX_API_KEY:
            return StageResult(
                name=name,
                success=True,
                duration=0,
                message="MiniMax API Key 未配置，跳过测试",
            )

        try:
            from services.svc_minimax_tts import MiniMaxTTSService

            tts_service = MiniMaxTTSService()

            # 获取可用音色
            voices = tts_service.get_available_voices()
            if voices:
                logger.info(f"可用音色数: {len(voices)}")

            # 测试合成
            audio_data = await asyncio.to_thread(
                tts_service.synthesize,
                text="你好，这是测试音频。",
                voice_id="male-qn",
                speed=1.0,
            )

            assert audio_data, "合成结果为空"
            assert len(audio_data) > 0, "合成数据长度为 0"

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"MiniMax TTS 合成成功: {len(audio_data)} bytes",
                data={"audio_size": len(audio_data)},
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"MiniMax TTS 合成失败: {e}",
                errors=[str(e)],
            )

    async def test_audio_postprocessor(self) -> StageResult:
        """测试音频后处理"""
        name = "Audio Postprocessing"
        start = time.perf_counter()

        try:
            from services.svc_audio_postprocessor import AudioPostprocessorService

            processor = AudioPostprocessorService()

            assert processor.sample_rate == settings.AUDIO_SAMPLE_RATE
            assert processor.bit_rate == settings.AUDIO_BITRATE

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"音频后处理服务就绪: {processor.sample_rate}Hz/{processor.bit_rate}kbps",
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"音频后处理测试失败: {e}",
                errors=[str(e)],
            )

    async def test_file_watcher(self) -> StageResult:
        """测试文件监听服务"""
        name = "File Watcher Service"
        start = time.perf_counter()

        try:
            from services.svc_file_watcher import get_watcher_service

            watcher = get_watcher_service()
            status = watcher.get_status()

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"文件监听服务状态: {status.get('running', False)}",
                data=status,
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"文件监听服务测试失败: {e}",
                errors=[str(e)],
            )

    async def test_publisher_service(self) -> StageResult:
        """测试发布服务"""
        name = "Publisher Service"
        start = time.perf_counter()

        try:
            from services.svc_publisher import PublisherService

            publisher = PublisherService()

            # 获取可用渠道
            with get_db_context() as db:
                from models import PublishChannel
                channels = db.query(PublishChannel).filter(
                    PublishChannel.is_enabled == True
                ).all()

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"发布服务就绪，可用渠道数: {len(channels)}",
                data={"channel_count": len(channels)},
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"发布服务测试失败: {e}",
                errors=[str(e)],
            )

    # ===========================================
    # 完整流水线测试
    # ===========================================

    async def test_full_pipeline_with_celery(self) -> StageResult:
        """使用 Celery 执行完整流水线测试"""
        name = "Full Pipeline (Celery)"
        start = time.perf_counter()

        if not self.test_epub_path:
            return StageResult(
                name=name,
                success=False,
                duration=time.perf_counter() - start,
                message="缺少测试 EPUB 文件",
            )

        try:
            from tasks.task_pipeline import generate_audiobook_simple

            # 计算文件哈希
            with open(self.test_epub_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

            # 创建书籍记录
            with get_db_context() as db:
                from models import Book
                from models.model_book import SourceType, BookStatus

                # 检查是否已存在
                existing = db.query(Book).filter(Book.file_hash == file_hash).first()
                if existing:
                    book = existing
                    logger.info(f"使用已存在的书籍: {book.id}")
                else:
                    book = Book(
                        title="测试书籍",
                        file_name=os.path.basename(self.test_epub_path),
                        file_size=os.path.getsize(self.test_epub_path),
                        file_hash=file_hash,
                        source_type=SourceType.MANUAL,
                        status=BookStatus.PENDING,
                    )
                    db.add(book)
                    db.commit()
                    db.refresh(book)
                    logger.info(f"创建新书籍: {book.id}")

            # 触发流水线
            result = generate_audiobook_simple.delay(book.id)

            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=True,
                duration=duration,
                message=f"流水线任务已提交: {result.id}",
                data={
                    "book_id": book.id,
                    "task_id": result.id,
                },
            )

        except Exception as e:
            duration = time.perf_counter() - start
            return StageResult(
                name=name,
                success=False,
                duration=duration,
                message=f"流水线测试失败: {e}",
                errors=[str(e)],
            )

    # ===========================================
    # 执行入口
    # ===========================================

    async def run_all_tests(self) -> TestReport:
        """运行所有测试"""
        logger.info("=" * 70)
        logger.info("开始全链路集成测试")
        logger.info("=" * 70)

        # 基础设施测试
        stages_infrastructure = [
            ("数据库连接", self.test_database_connection),
            ("MinIO 连接", self.test_minio_connection),
            ("Redis/Celery 连接", self.test_redis_celery),
        ]

        logger.info("\n--- 基础设施测试 ---")
        for stage_name, test_func in stages_infrastructure:
            result = await test_func()
            self.report.add_stage(result)
            status = "✅" if result.success else "❌"
            logger.info(f"{status} {result.name}: {result.message}")

        # 核心服务测试
        stages_services = [
            ("EPUB 解析", self.test_epub_parsing),
            ("文本预处理", self.test_text_preprocessing),
            ("DeepSeek 分析", self.test_deepseek_analysis),
            ("MiniMax TTS", self.test_minimax_tts),
            ("音频后处理", self.test_audio_postprocessor),
            ("文件监听服务", self.test_file_watcher),
            ("发布服务", self.test_publisher_service),
        ]

        logger.info("\n--- 核心服务测试 ---")
        for stage_name, test_func in stages_services:
            result = await test_func()
            self.report.add_stage(result)
            status = "✅" if result.success else "❌"
            logger.info(f"{status} {result.name}: {result.message}")

        # 完整流水线测试
        logger.info("\n--- 完整流水线测试 ---")
        pipeline_result = await self.test_full_pipeline_with_celery()
        self.report.add_stage(pipeline_result)
        status = "✅" if pipeline_result.success else "❌"
        logger.info(f"{status} {pipeline_result.name}: {pipeline_result.message}")

        # 汇总结果
        self.report.end_time = datetime.now()
        self.report.total_duration = (
            self.report.end_time - self.report.start_time
        ).total_seconds()

        self._print_summary()

        # 清理
        if self.test_epub_path and os.path.exists(self.test_epub_path):
            try:
                os.remove(self.test_epub_path)
                logger.info(f"清理测试文件: {self.test_epub_path}")
            except Exception as e:
                logger.warning(f"清理测试文件失败: {e}")

        return self.report

    def _print_summary(self):
        """打印测试汇总"""
        passed = sum(1 for s in self.report.stages if s.success)
        failed = sum(1 for s in self.report.stages if not s.success)
        total = len(self.report.stages)

        logger.info("\n" + "=" * 70)
        logger.info("测试结果汇总")
        logger.info("=" * 70)
        logger.info(f"测试名称: {self.report.test_name}")
        logger.info(f"开始时间: {self.report.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"结束时间: {self.report.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"总耗时: {self.report.total_duration:.2f}s")
        logger.info(f"总测试数: {total}")
        logger.info(f"通过: {passed} ({passed/total*100:.1f}%)")
        logger.info(f"失败: {failed} ({failed/total*100:.1f}%)")

        # 性能汇总
        perf_summary = self.report._get_performance_summary()
        if perf_summary:
            logger.info("\n--- 性能汇总 ---")
            logger.info(f"评级分布: {perf_summary.get('rating_distribution', {})}")
            logger.info(f"平均耗时: {perf_summary.get('average_duration', 0):.3f}s")
            if perf_summary.get('slowest_stage'):
                logger.info(f"最慢阶段: {perf_summary['slowest_stage']} ({perf_summary['slowest_duration']:.3f}s)")

        if failed > 0:
            logger.error("\n失败测试详情:")
            for stage in self.report.stages:
                if not stage.success:
                    logger.error(f"  - {stage.name}: {stage.message}")
                    for error in stage.errors:
                        logger.error(f"    Error: {error}")

        # 性能评级详情
        logger.info("\n--- 各阶段性能详情 ---")
        for stage in self.report.stages:
            if stage.performance_rating != "unknown":
                rating_emoji = {
                    "excellent": "🟢",
                    "good": "🟡",
                    "acceptable": "🟠",
                    "poor": "🔴",
                }.get(stage.performance_rating, "⚪")
                status = "✅" if stage.success else "❌"
                logger.info(f"{status} {stage.name}: {stage.duration:.3f}s [{stage.performance_rating.upper()}] {rating_emoji}")
            else:
                status = "✅" if stage.success else "❌"
                logger.info(f"{status} {stage.name}: {stage.duration:.3f}s")

        logger.info("\n" + "=" * 70)


async def main():
    """主函数"""
    test_runner = FullPipelineIntegrationTest()
    report = await test_runner.run_all_tests()

    # 返回退出码
    if not report.overall_success:
        logger.error("部分测试失败")
        sys.exit(1)
    else:
        logger.info("所有测试通过!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
