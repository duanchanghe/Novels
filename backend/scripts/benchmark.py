# ===========================================
# 性能基准测试脚本
# ===========================================

"""
性能基准测试脚本

测量各模块的性能指标：
- EPUB 解析速度
- DeepSeek 分析速度
- MiniMax TTS 合成速度
- 音频后处理速度
- 内存使用情况
"""

import asyncio
import sys
import time
import psutil
import tracemalloc
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from services.svc_epub_parser import EPUBParserService
from services.svc_text_preprocessor import TextPreprocessorService
from services.svc_deepseek_analyzer import DeepSeekAnalyzerService
from services.svc_minimax_tts import MiniMaxTTSService
from services.svc_audio_postprocessor import AudioPostprocessorService


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    memory_delta: int
    cpu_percent: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceBenchmark:
    """
    性能基准测试运行器
    """

    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.process = psutil.Process()

    def measure_memory(self, func, *args, **kwargs):
        """测量内存使用"""
        tracemalloc.start()
        start_memory = tracemalloc.get_traced_memory()[0]
        
        result = func(*args, **kwargs)
        
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return result, peak_memory - start_memory

    def measure_cpu(self, func, *args, **kwargs):
        """测量 CPU 使用"""
        self.process.cpu_percent()
        
        result = func(*args, **kwargs)
        
        cpu_percent = self.process.cpu_percent()
        
        return result, cpu_percent

    async def benchmark_epub_parsing(self, iterations: int = 10) -> BenchmarkResult:
        """测试 EPUB 解析性能"""
        test_epub_path = Path(__file__).parent.parent.parent / "test_sample.epub"
        
        if not test_epub_path.exists():
            return BenchmarkResult(
                name="EPUB 解析",
                iterations=0,
                total_time=0,
                avg_time=0,
                min_time=0,
                max_time=0,
                std_dev=0,
                memory_delta=0,
                cpu_percent=0,
                metadata={"status": "skipped", "reason": "测试文件不存在"}
            )

        times: List[float] = []
        memory_deltas: List[int] = []

        parser = EPUBParserService()

        for _ in range(iterations):
            start = time.perf_counter()
            _, memory_delta = self.measure_memory(parser.parse_file, str(test_epub_path))
            elapsed = time.perf_counter() - start
            
            times.append(elapsed)
            memory_deltas.append(memory_delta)

        return BenchmarkResult(
            name="EPUB 解析",
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            memory_delta=sum(memory_deltas) // len(memory_deltas),
            cpu_percent=0,
            metadata={
                "file_size": test_epub_path.stat().st_size,
            }
        )

    def benchmark_text_preprocessing(self, iterations: int = 100) -> BenchmarkResult:
        """测试文本预处理性能"""
        # 生成测试文本
        test_text = """
        这是一段测试文本，用于测试文本预处理的性能。
        包含一些数字：12345
        包含一些标点：，。、；
        包含一些特殊字符：@#$%
        
        第二段文本内容。
        """ * 100  # 放大文本量

        times: List[float] = []
        memory_deltas: List[int] = []

        preprocessor = TextPreprocessorService()

        for _ in range(iterations):
            start = time.perf_counter()
            _, memory_delta = self.measure_memory(preprocessor.normalize_text, test_text)
            elapsed = time.perf_counter() - start
            
            times.append(elapsed)
            memory_deltas.append(memory_delta)

        return BenchmarkResult(
            name="文本预处理",
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            memory_delta=sum(memory_deltas) // len(memory_deltas),
            cpu_percent=0,
            metadata={
                "text_length": len(test_text),
            }
        )

    async def benchmark_deepseek_analysis(self, iterations: int = 5) -> BenchmarkResult:
        """测试 DeepSeek 分析性能"""
        if not settings.DEEPSEEK_API_KEY:
            return BenchmarkResult(
                name="DeepSeek 分析",
                iterations=0,
                total_time=0,
                avg_time=0,
                min_time=0,
                max_time=0,
                std_dev=0,
                memory_delta=0,
                cpu_percent=0,
                metadata={"status": "skipped", "reason": "API Key 未配置"}
            )

        test_text = """
        李四走进房间，看见王五正在窗边站着。
        "你在这里做什么？"李四问道。
        王五转过身来，脸上带着微笑。
        "我在等你。"他回答。
        "太好了，我正需要你的帮助。"
        """ * 10  # 放大文本量

        times: List[float] = []
        memory_deltas: List[int] = []

        analyzer = DeepSeekAnalyzerService()

        for _ in range(iterations):
            start = time.perf_counter()
            _, memory_delta = self.measure_memory(
                lambda: asyncio.run(analyzer.analyze_text(test_text))
            )
            elapsed = time.perf_counter() - start
            
            times.append(elapsed)
            memory_deltas.append(memory_delta)

        return BenchmarkResult(
            name="DeepSeek 分析",
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            memory_delta=sum(memory_deltas) // len(memory_deltas),
            cpu_percent=0,
            metadata={
                "text_length": len(test_text),
            }
        )

    async def benchmark_tts_synthesis(self, iterations: int = 10) -> BenchmarkResult:
        """测试 TTS 合成性能"""
        if not settings.MINIMAX_API_KEY:
            return BenchmarkResult(
                name="MiniMax TTS 合成",
                iterations=0,
                total_time=0,
                avg_time=0,
                min_time=0,
                max_time=0,
                std_dev=0,
                memory_delta=0,
                cpu_percent=0,
                metadata={"status": "skipped", "reason": "API Key 未配置"}
            )

        test_text = "你好，这是测试语音合成。很高兴认识你。" * 5

        times: List[float] = []
        memory_deltas: List[int] = []
        audio_sizes: List[int] = []

        tts_service = MiniMaxTTSService()

        for _ in range(iterations):
            start = time.perf_counter()
            audio_data, memory_delta = self.measure_memory(
                lambda: asyncio.run(
                    tts_service.synthesize(test_text, voice_id="male-qn")
                )
            )
            elapsed = time.perf_counter() - start
            
            times.append(elapsed)
            memory_deltas.append(memory_delta)
            if audio_data:
                audio_sizes.append(len(audio_data))

        return BenchmarkResult(
            name="MiniMax TTS 合成",
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            memory_delta=sum(memory_deltas) // len(memory_deltas) if memory_deltas else 0,
            cpu_percent=0,
            metadata={
                "text_length": len(test_text),
                "avg_audio_size": statistics.mean(audio_sizes) if audio_sizes else 0,
            }
        )

    def benchmark_audio_postprocessor(self, iterations: int = 10) -> BenchmarkResult:
        """测试音频后处理性能"""
        processor = AudioPostprocessorService()
        
        # 验证配置加载
        start = time.perf_counter()
        for _ in range(iterations):
            _ = processor.sample_rate
            _ = processor.bit_rate
        elapsed = time.perf_counter() - start

        return BenchmarkResult(
            name="音频后处理",
            iterations=iterations,
            total_time=elapsed,
            avg_time=elapsed / iterations,
            min_time=elapsed / iterations,
            max_time=elapsed / iterations,
            std_dev=0,
            memory_delta=0,
            cpu_percent=0,
            metadata={
                "sample_rate": processor.sample_rate,
                "bit_rate": processor.bit_rate,
            }
        )

    def format_result(self, result: BenchmarkResult) -> str:
        """格式化测试结果"""
        lines = [
            f"\n{'='*60}",
            f"测试: {result.name}",
            f"{'='*60}",
            f"迭代次数: {result.iterations}",
            f"总耗时: {result.total_time:.3f}s",
            f"平均耗时: {result.avg_time:.3f}s",
            f"最小耗时: {result.min_time:.3f}s",
            f"最大耗时: {result.max_time:.3f}s",
            f"标准差: {result.std_dev:.3f}s",
            f"内存增量: {result.memory_delta / 1024:.2f} KB",
        ]
        
        if result.metadata:
            lines.append("\n元数据:")
            for key, value in result.metadata.items():
                lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)

    def print_summary(self):
        """打印结果汇总"""
        print("\n" + "=" * 60)
        print("性能基准测试汇总")
        print("=" * 60)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"系统信息:")
        print(f"  CPU: {psutil.cpu_count()} 核")
        print(f"  内存: {psutil.virtual_memory().total / (1024**3):.2f} GB")
        print(f"  Python: {sys.version.split()[0]}")
        
        for result in self.results:
            print(self.format_result(result))


async def main():
    """主函数"""
    benchmark = PerformanceBenchmark()

    print("开始性能基准测试...")
    print("=" * 60)

    # 运行各项测试
    benchmark.results.append(
        await benchmark.benchmark_epub_parsing(iterations=5)
    )
    benchmark.results.append(
        benchmark.benchmark_text_preprocessing(iterations=50)
    )
    benchmark.results.append(
        await benchmark.benchmark_deepseek_analysis(iterations=3)
    )
    benchmark.results.append(
        await benchmark.benchmark_tts_synthesis(iterations=5)
    )
    benchmark.results.append(
        benchmark.benchmark_audio_postprocessor(iterations=10)
    )

    # 打印结果
    benchmark.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
