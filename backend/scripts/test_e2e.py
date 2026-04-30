# ===========================================
# 端到端测试脚本
# ===========================================

"""
端到端集成测试脚本

测试从 EPUB 上传到有声书生成的完整流程。
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from core.database import get_db_context, engine, Base
from core.config import settings
from models import Book, Chapter, AudioSegment
from models.model_book import SourceType, BookStatus
from models.model_chapter import ChapterStatus
from services.svc_epub_parser import EPUBParserService
from services.svc_text_preprocessor import TextPreprocessorService
from services.svc_deepseek_analyzer import DeepSeekAnalyzerService
from services.svc_minimax_tts import MiniMaxTTSService
from services.svc_audio_postprocessor import AudioPostprocessorService
from services.svc_minio_storage import get_storage_service


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audiobook.e2e")


class E2ETestRunner:
    """
    端到端测试运行器

    执行完整的有声书生成流程测试。
    """

    def __init__(self):
        self.results: Dict[str, Any] = {
            "passed": [],
            "failed": [],
            "skipped": [],
            "errors": [],
        }
        self.storage = None

    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        result = {
            "name": test_name,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if passed:
            self.results["passed"].append(result)
            logger.info(f"✅ PASS: {test_name} {message}")
        else:
            self.results["failed"].append(result)
            logger.error(f"❌ FAIL: {test_name} {message}")

    def log_error(self, test_name: str, error: Exception):
        """记录错误"""
        self.results["errors"].append({
            "name": test_name,
            "error": str(error),
            "type": type(error).__name__,
        })
        logger.exception(f"💥 ERROR: {test_name}: {error}")

    async def test_database_connection(self) -> bool:
        """测试数据库连接"""
        test_name = "数据库连接测试"
        try:
            with get_db_context() as db:
                db.execute("SELECT 1")
            self.log_result(test_name, True, "数据库连接成功")
            return True
        except Exception as e:
            self.log_result(test_name, False, f"连接失败: {e}")
            return False

    async def test_minio_connection(self) -> bool:
        """测试 MinIO 连接"""
        test_name = "MinIO 连接测试"
        try:
            self.storage = get_storage_service()
            self.storage.initialize()
            self.log_result(test_name, True, "MinIO 连接成功")
            return True
        except Exception as e:
            self.log_result(test_name, False, f"连接失败: {e}")
            return False

    async def test_epub_parser(self) -> bool:
        """测试 EPUB 解析"""
        test_name = "EPUB 解析测试"
        
        # 创建测试 EPUB 文件
        test_epub_path = Path(__file__).parent.parent.parent / "test_sample.epub"
        
        if not test_epub_path.exists():
            logger.warning(f"测试 EPUB 文件不存在，跳过测试: {test_epub_path}")
            self.results["skipped"].append({"name": test_name, "reason": "测试文件不存在"})
            return True

        try:
            parser = EPUBParserService()
            result = parser.parse_file(str(test_epub_path))
            
            assert result.get("title"), "缺少书名"
            assert result.get("chapters"), "缺少章节"
            assert len(result["chapters"]) > 0, "章节列表为空"
            
            self.log_result(
                test_name, True,
                f"解析成功: {result['title']}, {len(result['chapters'])} 章节"
            )
            return True
        except Exception as e:
            self.log_result(test_name, False, f"解析失败: {e}")
            return False

    async def test_text_preprocessor(self) -> bool:
        """测试文本预处理"""
        test_name = "文本预处理测试"
        
        test_text = """
        2024年3月5日下午2点30分，张三来到银行。
        "你好，我想要开户。"他说。
        百分比是50%，小数是3.14。
        """
        
        try:
            preprocessor = TextPreprocessorService()
            
            # 测试规范化
            normalized = preprocessor.normalize_text(test_text)
            assert normalized, "规范化结果为空"
            
            # 测试段落拆分
            paragraphs = preprocessor.split_paragraphs(normalized)
            assert len(paragraphs) > 0, "段落拆分失败"
            
            # 测试 TTS 准备
            prepared = preprocessor.prepare_for_tts(test_text)
            assert "processed_text" in prepared, "TTS 准备结果缺少字段"
            
            self.log_result(
                test_name, True,
                f"预处理成功: {len(paragraphs)} 段落"
            )
            return True
        except Exception as e:
            self.log_result(test_name, False, f"预处理失败: {e}")
            return False

    async def test_deepseek_analyzer(self) -> bool:
        """测试 DeepSeek 分析"""
        test_name = "DeepSeek 分析测试"
        
        if not settings.DEEPSEEK_API_KEY:
            logger.warning("DeepSeek API Key 未配置，跳过测试")
            self.results["skipped"].append({"name": test_name, "reason": "API Key 未配置"})
            return True
        
        test_text = """
        李四走进房间，看见王五正在窗边站着。
        "你在这里做什么？"李四问道。
        王五转过身来，脸上带着微笑。
        "我在等你。"他回答。
        """
        
        try:
            analyzer = DeepSeekAnalyzerService()
            result = await analyzer.analyze_text(test_text)
            
            assert "paragraphs" in result, "分析结果缺少 paragraphs"
            assert isinstance(result["paragraphs"], list), "paragraphs 不是列表"
            
            characters = result.get("characters", [])
            self.log_result(
                test_name, True,
                f"分析成功: {len(result['paragraphs'])} 段落, {len(characters)} 角色"
            )
            return True
        except Exception as e:
            self.log_result(test_name, False, f"分析失败: {e}")
            return False

    async def test_minimax_tts(self) -> bool:
        """测试 MiniMax TTS"""
        test_name = "MiniMax TTS 测试"
        
        if not settings.MINIMAX_API_KEY:
            logger.warning("MiniMax API Key 未配置，跳过测试")
            self.results["skipped"].append({"name": test_name, "reason": "API Key 未配置"})
            return True
        
        try:
            tts_service = MiniMaxTTSService()
            
            # 获取可用音色
            voices = tts_service.get_available_voices()
            assert len(voices) > 0, "没有可用音色"
            
            # 测试合成
            audio_data = await tts_service.synthesize(
                text="你好，这是测试音频。",
                voice_id="male-qn",
                speed=1.0,
            )
            
            assert audio_data, "合成结果为空"
            assert len(audio_data) > 0, "合成数据长度为 0"
            
            self.log_result(
                test_name, True,
                f"合成成功: {len(audio_data)} bytes"
            )
            return True
        except Exception as e:
            self.log_result(test_name, False, f"合成失败: {e}")
            return False

    async def test_audio_postprocessor(self) -> bool:
        """测试音频后处理"""
        test_name = "音频后处理测试"
        
        try:
            processor = AudioPostprocessorService()
            
            # 验证配置
            assert processor.sample_rate == settings.AUDIO_SAMPLE_RATE
            assert processor.bit_rate == settings.AUDIO_BITRATE
            
            self.log_result(
                test_name, True,
                f"后处理服务就绪: 采样率={processor.sample_rate}Hz, 比特率={processor.bit_rate}kbps"
            )
            return True
        except Exception as e:
            self.log_result(test_name, False, f"后处理测试失败: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("开始端到端集成测试")
        logger.info("=" * 60)

        # 基础设施测试
        await self.test_database_connection()
        await self.test_minio_connection()
        
        # 核心服务测试
        await self.test_epub_parser()
        await self.test_text_preprocessor()
        await self.test_deepseek_analyzer()
        await self.test_minimax_tts()
        await self.test_audio_postprocessor()

        # 汇总结果
        total = len(self.results["passed"]) + len(self.results["failed"])
        passed = len(self.results["passed"])
        failed = len(self.results["failed"])
        skipped = len(self.results["skipped"])
        errors = len(self.results["errors"])

        logger.info("=" * 60)
        logger.info("测试结果汇总")
        logger.info("=" * 60)
        logger.info(f"总测试数: {total}")
        logger.info(f"通过: {passed}")
        logger.info(f"失败: {failed}")
        logger.info(f"跳过: {skipped}")
        logger.info(f"错误: {errors}")

        if self.results["failed"]:
            logger.error("失败测试详情:")
            for r in self.results["failed"]:
                logger.error(f"  - {r['name']}: {r['message']}")

        if self.results["errors"]:
            logger.error("错误详情:")
            for r in self.results["errors"]:
                logger.error(f"  - {r['name']}: {r['type']}: {r['error']}")

        self.results["summary"] = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "success_rate": passed / total if total > 0 else 0,
        }

        return self.results


async def main():
    """主函数"""
    runner = E2ETestRunner()
    results = await runner.run_all_tests()
    
    # 返回退出码
    if results["failed"] or results["errors"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
