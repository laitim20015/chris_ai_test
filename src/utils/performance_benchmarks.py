"""
性能基準測試模組
Performance Benchmarks Module

提供全面的性能測試、基準比較和性能監控功能。
測試處理速度、內存使用、準確性等關鍵指標。
"""

import time
import psutil
import gc
import asyncio
import json
import platform
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
from statistics import mean, stdev
import tracemalloc
from contextlib import contextmanager

from src.config.logging_config import get_logger

logger = get_logger("performance_benchmarks")

@dataclass
class PerformanceMetrics:
    """性能指標數據結構"""
    operation_name: str                           # 操作名稱
    execution_time: float                         # 執行時間（秒）
    memory_peak: float = 0.0                     # 峰值內存使用（MB）
    memory_current: float = 0.0                  # 當前內存使用（MB）
    cpu_percent: float = 0.0                     # CPU使用率
    success: bool = True                          # 是否成功
    error_message: str = ""                       # 錯誤信息
    input_size: int = 0                          # 輸入大小
    output_size: int = 0                         # 輸出大小
    throughput: float = 0.0                      # 吞吐量（操作/秒）
    additional_metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class BenchmarkSuite:
    """基準測試套件"""
    name: str                                     # 套件名稱
    description: str                              # 描述
    metrics: List[PerformanceMetrics] = field(default_factory=list)
    baseline_metrics: Optional[PerformanceMetrics] = None
    created_at: datetime = field(default_factory=datetime.now)

class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        """初始化性能分析器"""
        self.logger = logger
        self.current_metrics: Optional[PerformanceMetrics] = None
        self.suites: Dict[str, BenchmarkSuite] = {}
        
        # 系統信息
        self.system_info = {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total / (1024**3),  # GB
            "platform": platform.platform()
        }
        
        self.logger.info(f"性能分析器初始化完成 - CPU: {self.system_info['cpu_count']}核, 內存: {self.system_info['memory_total']:.1f}GB")
    
    @contextmanager
    def profile_operation(self, operation_name: str, input_size: int = 0):
        """
        性能分析上下文管理器
        
        Args:
            operation_name: 操作名稱
            input_size: 輸入大小
            
        Yields:
            PerformanceMetrics: 性能指標對象
        """
        # 開始內存跟踪
        tracemalloc.start()
        
        # 記錄開始狀態
        start_time = time.perf_counter()
        start_memory = psutil.virtual_memory().used / (1024**2)  # MB
        process = psutil.Process()
        start_cpu = process.cpu_percent()
        
        # 初始化指標對象
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            execution_time=0.0,
            input_size=input_size
        )
        
        try:
            # 執行操作
            yield metrics
            
            # 記錄成功
            metrics.success = True
            
        except Exception as e:
            # 記錄錯誤
            metrics.success = False
            metrics.error_message = str(e)
            self.logger.error(f"性能測試中發生錯誤 {operation_name}: {e}")
            
        finally:
            # 計算性能指標
            end_time = time.perf_counter()
            end_memory = psutil.virtual_memory().used / (1024**2)  # MB
            end_cpu = process.cpu_percent()
            
            # 獲取內存峰值
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # 更新指標
            metrics.execution_time = end_time - start_time
            metrics.memory_current = end_memory - start_memory
            metrics.memory_peak = peak / (1024**2)  # 轉換為MB
            metrics.cpu_percent = (start_cpu + end_cpu) / 2
            
            # 計算吞吐量
            if metrics.execution_time > 0:
                metrics.throughput = 1.0 / metrics.execution_time
            
            self.current_metrics = metrics
            self.logger.debug(f"性能分析完成: {operation_name} - {metrics.execution_time:.3f}s")
    
    def benchmark_function(self, 
                          func: Callable,
                          args: tuple = (),
                          kwargs: dict = None,
                          iterations: int = 1,
                          warmup: int = 0) -> List[PerformanceMetrics]:
        """
        對函數進行基準測試
        
        Args:
            func: 要測試的函數
            args: 函數參數
            kwargs: 函數關鍵字參數
            iterations: 測試迭代次數
            warmup: 預熱次數
            
        Returns:
            List[PerformanceMetrics]: 性能指標列表
        """
        kwargs = kwargs or {}
        function_name = getattr(func, '__name__', str(func))
        
        self.logger.info(f"開始基準測試: {function_name} ({iterations}次迭代，{warmup}次預熱)")
        
        # 預熱
        for i in range(warmup):
            try:
                func(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"預熱 {i+1} 失敗: {e}")
        
        # 實際測試
        results = []
        for i in range(iterations):
            with self.profile_operation(f"{function_name}_iter_{i+1}") as metrics:
                try:
                    result = func(*args, **kwargs)
                    
                    # 嘗試獲取輸出大小
                    if hasattr(result, '__len__'):
                        metrics.output_size = len(result)
                    elif isinstance(result, str):
                        metrics.output_size = len(result.encode('utf-8'))
                    
                except Exception:
                    raise  # 重新拋出異常以便上下文管理器處理
                
            results.append(metrics)
        
        # 計算統計信息
        self._log_benchmark_summary(function_name, results)
        
        return results
    
    async def benchmark_async_function(self,
                                     func: Callable,
                                     args: tuple = (),
                                     kwargs: dict = None,
                                     iterations: int = 1,
                                     warmup: int = 0) -> List[PerformanceMetrics]:
        """
        對異步函數進行基準測試
        
        Args:
            func: 要測試的異步函數
            args: 函數參數
            kwargs: 函數關鍵字參數
            iterations: 測試迭代次數
            warmup: 預熱次數
            
        Returns:
            List[PerformanceMetrics]: 性能指標列表
        """
        kwargs = kwargs or {}
        function_name = getattr(func, '__name__', str(func))
        
        self.logger.info(f"開始異步基準測試: {function_name} ({iterations}次迭代，{warmup}次預熱)")
        
        # 預熱
        for i in range(warmup):
            try:
                await func(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"預熱 {i+1} 失敗: {e}")
        
        # 實際測試
        results = []
        for i in range(iterations):
            with self.profile_operation(f"{function_name}_async_iter_{i+1}") as metrics:
                try:
                    result = await func(*args, **kwargs)
                    
                    # 嘗試獲取輸出大小
                    if hasattr(result, '__len__'):
                        metrics.output_size = len(result)
                    elif isinstance(result, str):
                        metrics.output_size = len(result.encode('utf-8'))
                    
                except Exception:
                    raise  # 重新拋出異常以便上下文管理器處理
                
            results.append(metrics)
        
        # 計算統計信息
        self._log_benchmark_summary(function_name + "_async", results)
        
        return results
    
    def _log_benchmark_summary(self, function_name: str, results: List[PerformanceMetrics]):
        """記錄基準測試摘要"""
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            self.logger.error(f"基準測試全部失敗: {function_name}")
            return
        
        times = [r.execution_time for r in successful_results]
        memories = [r.memory_peak for r in successful_results]
        
        avg_time = mean(times)
        std_time = stdev(times) if len(times) > 1 else 0
        avg_memory = mean(memories)
        success_rate = len(successful_results) / len(results) * 100
        
        self.logger.info(f"📊 基準測試摘要: {function_name}")
        self.logger.info(f"  ⏱️  平均時間: {avg_time:.3f}s (±{std_time:.3f}s)")
        self.logger.info(f"  🧠 平均內存: {avg_memory:.2f}MB")
        self.logger.info(f"  ✅ 成功率: {success_rate:.1f}%")
        self.logger.info(f"  🔄 吞吐量: {1/avg_time:.2f} ops/sec")
    
    def create_benchmark_suite(self, name: str, description: str) -> BenchmarkSuite:
        """
        創建基準測試套件
        
        Args:
            name: 套件名稱
            description: 描述
            
        Returns:
            BenchmarkSuite: 基準測試套件
        """
        suite = BenchmarkSuite(name=name, description=description)
        self.suites[name] = suite
        
        self.logger.info(f"創建基準測試套件: {name}")
        
        return suite
    
    def add_to_suite(self, suite_name: str, metrics: Union[PerformanceMetrics, List[PerformanceMetrics]]):
        """
        添加指標到測試套件
        
        Args:
            suite_name: 套件名稱
            metrics: 性能指標
        """
        if suite_name not in self.suites:
            raise ValueError(f"測試套件不存在: {suite_name}")
        
        suite = self.suites[suite_name]
        
        if isinstance(metrics, list):
            suite.metrics.extend(metrics)
        else:
            suite.metrics.append(metrics)
    
    def compare_with_baseline(self, suite_name: str, baseline_metrics: PerformanceMetrics) -> Dict[str, float]:
        """
        與基準線比較
        
        Args:
            suite_name: 套件名稱
            baseline_metrics: 基準線指標
            
        Returns:
            Dict[str, float]: 比較結果（比率）
        """
        if suite_name not in self.suites:
            raise ValueError(f"測試套件不存在: {suite_name}")
        
        suite = self.suites[suite_name]
        suite.baseline_metrics = baseline_metrics
        
        successful_metrics = [m for m in suite.metrics if m.success]
        if not successful_metrics:
            return {}
        
        # 計算平均值
        avg_time = mean([m.execution_time for m in successful_metrics])
        avg_memory = mean([m.memory_peak for m in successful_metrics])
        
        # 計算比率（當前/基準線）
        comparison = {
            "time_ratio": avg_time / baseline_metrics.execution_time,
            "memory_ratio": avg_memory / baseline_metrics.memory_peak,
            "throughput_ratio": (1/avg_time) / baseline_metrics.throughput
        }
        
        self.logger.info(f"📈 基準線比較 ({suite_name}):")
        self.logger.info(f"  ⏱️  時間比率: {comparison['time_ratio']:.2f}x")
        self.logger.info(f"  🧠 內存比率: {comparison['memory_ratio']:.2f}x")
        self.logger.info(f"  🔄 吞吐量比率: {comparison['throughput_ratio']:.2f}x")
        
        return comparison
    
    def export_results(self, file_path: Union[str, Path]) -> bool:
        """
        導出測試結果
        
        Args:
            file_path: 輸出文件路徑
            
        Returns:
            bool: 是否成功
        """
        try:
            # 準備導出數據
            export_data = {
                "system_info": self.system_info,
                "export_time": datetime.now().isoformat(),
                "suites": {}
            }
            
            for name, suite in self.suites.items():
                export_data["suites"][name] = {
                    "name": suite.name,
                    "description": suite.description,
                    "created_at": suite.created_at.isoformat(),
                    "metrics": [asdict(m) for m in suite.metrics],
                    "baseline_metrics": asdict(suite.baseline_metrics) if suite.baseline_metrics else None
                }
            
            # 寫入文件
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"性能測試結果已導出: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"導出結果失敗: {e}")
            return False
    
    def generate_report(self, suite_name: str) -> Dict[str, Any]:
        """
        生成性能報告
        
        Args:
            suite_name: 套件名稱
            
        Returns:
            Dict[str, Any]: 性能報告
        """
        if suite_name not in self.suites:
            raise ValueError(f"測試套件不存在: {suite_name}")
        
        suite = self.suites[suite_name]
        successful_metrics = [m for m in suite.metrics if m.success]
        failed_metrics = [m for m in suite.metrics if not m.success]
        
        if not successful_metrics:
            return {"error": "沒有成功的測試結果"}
        
        # 統計數據
        times = [m.execution_time for m in successful_metrics]
        memories = [m.memory_peak for m in successful_metrics]
        
        report = {
            "suite_name": suite.name,
            "description": suite.description,
            "total_tests": len(suite.metrics),
            "successful_tests": len(successful_metrics),
            "failed_tests": len(failed_metrics),
            "success_rate": len(successful_metrics) / len(suite.metrics) * 100,
            "performance_stats": {
                "execution_time": {
                    "min": min(times),
                    "max": max(times),
                    "avg": mean(times),
                    "std": stdev(times) if len(times) > 1 else 0
                },
                "memory_usage": {
                    "min": min(memories),
                    "max": max(memories),
                    "avg": mean(memories),
                    "std": stdev(memories) if len(memories) > 1 else 0
                },
                "throughput": {
                    "avg": 1 / mean(times),
                    "peak": 1 / min(times)
                }
            },
            "system_info": self.system_info,
            "generated_at": datetime.now().isoformat()
        }
        
        # 如果有基準線，添加比較
        if suite.baseline_metrics:
            comparison = self.compare_with_baseline(suite_name, suite.baseline_metrics)
            report["baseline_comparison"] = comparison
        
        return report

# 全局性能分析器實例
_global_profiler = PerformanceProfiler()

def get_profiler() -> PerformanceProfiler:
    """獲取全局性能分析器"""
    return _global_profiler

def profile(operation_name: str = None, input_size: int = 0):
    """
    性能分析裝飾器
    
    Args:
        operation_name: 操作名稱
        input_size: 輸入大小
        
    Returns:
        裝飾後的函數
    """
    def decorator(func: Callable) -> Callable:
        actual_name = operation_name or getattr(func, '__name__', str(func))
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with get_profiler().profile_operation(actual_name, input_size) as metrics:
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with get_profiler().profile_operation(actual_name, input_size) as metrics:
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator
