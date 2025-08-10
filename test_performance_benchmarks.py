#!/usr/bin/env python3
"""
性能基準測試演示
Performance Benchmarks Demo

演示性能測試系統的功能，包括基準測試、性能分析和報告生成。
"""

import sys
import time
import asyncio
from pathlib import Path

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_performance_benchmarks():
    """測試性能基準測試系統"""
    
    print("🧪 性能基準測試系統演示")
    print("=" * 50)
    
    try:
        from utils.performance_benchmarks import (
            PerformanceProfiler,
            PerformanceMetrics,
            get_profiler,
            profile
        )
        
        # 初始化性能分析器
        profiler = PerformanceProfiler()
        
        # 創建測試套件
        print("📊 創建性能測試套件...")
        suite = profiler.create_benchmark_suite(
            "document_processing_benchmark",
            "文檔處理性能基準測試"
        )
        
        # 測試同步函數性能
        print("\n⏱️ 測試同步函數性能...")
        
        def slow_text_processing(text_length: int = 1000):
            """模擬慢速文本處理"""
            text = "測試文本 " * text_length
            
            # 模擬一些處理時間
            processed_words = []
            for word in text.split():
                processed_words.append(word.upper())
                if len(processed_words) % 100 == 0:
                    time.sleep(0.001)  # 模擬處理延遲
            
            return " ".join(processed_words)
        
        # 基準測試
        sync_results = profiler.benchmark_function(
            slow_text_processing,
            kwargs={"text_length": 500},
            iterations=3,
            warmup=1
        )
        
        profiler.add_to_suite("document_processing_benchmark", sync_results)
        
        # 測試異步函數性能
        print("\n⚡ 測試異步函數性能...")
        
        async def async_network_simulation(requests: int = 10):
            """模擬異步網絡請求"""
            results = []
            
            for i in range(requests):
                # 模擬異步I/O延遲
                await asyncio.sleep(0.01)
                results.append(f"響應_{i+1}")
            
            return results
        
        # 異步基準測試
        async_results = asyncio.run(
            profiler.benchmark_async_function(
                async_network_simulation,
                kwargs={"requests": 5},
                iterations=3,
                warmup=1
            )
        )
        
        profiler.add_to_suite("document_processing_benchmark", async_results)
        
        # 使用裝飾器進行性能分析
        print("\n🎯 使用裝飾器進行性能分析...")
        
        @profile("image_processing_simulation")
        def image_processing_simulation():
            """模擬圖片處理"""
            # 模擬圖片數據
            image_data = list(range(100000))
            
            # 模擬處理操作
            processed = []
            for pixel in image_data:
                processed.append(pixel * 1.1)
            
            return processed
        
        # 執行被裝飾的函數
        result = image_processing_simulation()
        print(f"  ✅ 圖片處理完成，處理了 {len(result)} 個像素")
        
        # 測試異步裝飾器
        @profile("async_file_processing")
        async def async_file_processing():
            """模擬異步文件處理"""
            files = ["file1.txt", "file2.txt", "file3.txt"]
            processed_files = []
            
            for file_name in files:
                await asyncio.sleep(0.02)  # 模擬文件I/O
                processed_files.append(f"processed_{file_name}")
            
            return processed_files
        
        async_result = asyncio.run(async_file_processing())
        print(f"  ✅ 異步文件處理完成，處理了 {len(async_result)} 個文件")
        
        # 生成性能報告
        print("\n📈 生成性能報告...")
        
        report = profiler.generate_report("document_processing_benchmark")
        
        print(f"📊 性能報告摘要:")
        print(f"  測試套件: {report['suite_name']}")
        print(f"  總測試數: {report['total_tests']}")
        print(f"  成功率: {report['success_rate']:.1f}%")
        print(f"  平均執行時間: {report['performance_stats']['execution_time']['avg']:.3f}s")
        print(f"  平均內存使用: {report['performance_stats']['memory_usage']['avg']:.2f}MB")
        print(f"  平均吞吐量: {report['performance_stats']['throughput']['avg']:.2f} ops/sec")
        
        # 測試基準線比較
        print("\n📊 測試基準線比較...")
        
        baseline = PerformanceMetrics(
            operation_name="baseline_reference",
            execution_time=0.1,
            memory_peak=10.0,
            throughput=10.0
        )
        
        comparison = profiler.compare_with_baseline("document_processing_benchmark", baseline)
        
        # 導出結果
        print("\n💾 導出測試結果...")
        
        export_path = Path("data/temp/performance_benchmark_results.json")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        success = profiler.export_results(export_path)
        if success:
            print(f"  ✅ 結果已導出到: {export_path}")
        
        # 測試全局分析器
        print("\n🌍 測試全局分析器...")
        
        global_profiler = get_profiler()
        
        with global_profiler.profile_operation("global_test_operation") as metrics:
            # 模擬一些操作
            data = list(range(10000))
            result = sum(data)
            metrics.additional_metrics = {"sum_result": result}
        
        print(f"  ✅ 全局操作完成: {metrics.execution_time:.3f}s")
        print(f"  📊 附加指標: {metrics.additional_metrics}")
        
        # 性能測試總結
        print("\n🎉 性能基準測試系統演示完成！")
        print("✅ 功能驗證:")
        print("  🔍 同步函數基準測試 ✓")
        print("  ⚡ 異步函數基準測試 ✓")
        print("  🎯 裝飾器性能分析 ✓")
        print("  📊 性能報告生成 ✓")
        print("  📈 基準線比較 ✓")
        print("  💾 結果導出 ✓")
        print("  🌍 全局分析器 ✓")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_performance_benchmarks()
    exit(0 if success else 1)
