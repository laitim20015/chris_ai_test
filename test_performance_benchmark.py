#!/usr/bin/env python3
"""
性能基準測試
Performance Benchmark Test

測試空間分析改進的性能基準，包括：
1. 不同規模數據的性能測試
2. 緩存效果測試
3. 記憶體使用測試
4. 併發性能測試
"""

import sys
import os
import time
import random
import threading
from pathlib import Path
from typing import List, Dict, Any
import json
import gc
import psutil

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent))

from src.association.spatial_analyzer import (
    enhanced_spatial_scoring, enhanced_spatial_scoring_optimized,
    get_performance_stats, clear_cache, SpatialAnalyzer
)
from src.association.allen_logic import BoundingBox
from src.association.candidate_ranker import CandidateRanker

def generate_random_bbox(page_width: int = 600, page_height: int = 800) -> BoundingBox:
    """生成隨機邊界框"""
    x = random.randint(0, page_width - 100)
    y = random.randint(0, page_height - 100)
    width = random.randint(50, min(200, page_width - x))
    height = random.randint(20, min(100, page_height - y))
    return BoundingBox(x=x, y=y, width=width, height=height)

def generate_test_data(num_pairs: int = 100) -> List[tuple]:
    """生成測試數據集"""
    test_data = []
    
    for i in range(num_pairs):
        text_bbox = generate_random_bbox()
        image_bbox = generate_random_bbox()
        
        context_info = {
            'layout_type': random.choice(['single_column', 'double_column', 'multi_column']),
            'all_elements': [text_bbox, image_bbox],
            'page_width': 600,
            'page_height': 800
        }
        
        test_data.append((f"pair_{i}", text_bbox, image_bbox, context_info))
    
    return test_data

def measure_memory_usage():
    """測量當前記憶體使用"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return {
        'rss_mb': memory_info.rss / 1024 / 1024,  # 實際記憶體使用
        'vms_mb': memory_info.vms / 1024 / 1024,  # 虛擬記憶體使用
    }

def test_scale_performance():
    """測試不同規模數據的性能"""
    print("🔬 規模性能測試")
    print("=" * 50)
    
    scales = [10, 50, 100, 200, 500]
    results = {}
    
    for scale in scales:
        print(f"\n📊 測試規模: {scale} 對")
        
        # 生成測試數據
        test_data = generate_test_data(scale)
        
        # 清空緩存
        clear_cache()
        gc.collect()
        
        # 測量初始記憶體
        initial_memory = measure_memory_usage()
        
        # 執行測試
        start_time = time.time()
        scores = []
        
        for name, text_bbox, image_bbox, context_info in test_data:
            result = enhanced_spatial_scoring(text_bbox, image_bbox, context_info)
            scores.append(result['final_score'])
        
        end_time = time.time()
        
        # 測量最終記憶體
        final_memory = measure_memory_usage()
        
        # 計算統計
        total_time = max(end_time - start_time, 0.001)  # 避免除零錯誤
        avg_time_per_pair = total_time / scale
        memory_increase = final_memory['rss_mb'] - initial_memory['rss_mb']
        
        results[scale] = {
            'total_time': total_time,
            'avg_time_per_pair': avg_time_per_pair,
            'memory_increase_mb': memory_increase,
            'avg_score': sum(scores) / len(scores),
            'throughput_pairs_per_sec': scale / total_time
        }
        
        print(f"  總時間: {total_time:.3f}s")
        print(f"  平均每對: {avg_time_per_pair:.4f}s")
        print(f"  記憶體增長: {memory_increase:.2f} MB")
        print(f"  吞吐量: {results[scale]['throughput_pairs_per_sec']:.1f} pairs/s")
        print(f"  平均分數: {results[scale]['avg_score']:.3f}")
    
    return results

def test_cache_effectiveness():
    """測試緩存效果"""
    print("\n🚀 緩存效果測試")
    print("=" * 50)
    
    # 生成測試數據（較小規模，便於重複使用）
    test_data = generate_test_data(20)
    
    results = {}
    
    # 測試場景1：無緩存
    print("\n1. 無緩存性能測試")
    clear_cache()
    
    start_time = time.time()
    for name, text_bbox, image_bbox, context_info in test_data * 3:  # 重複3次
        result = enhanced_spatial_scoring(text_bbox, image_bbox, context_info)
    no_cache_time = time.time() - start_time
    
    results['no_cache'] = {
        'time': no_cache_time,
        'requests': len(test_data) * 3
    }
    
    print(f"  總時間: {no_cache_time:.3f}s")
    print(f"  請求數: {results['no_cache']['requests']}")
    print(f"  平均每請求: {no_cache_time / results['no_cache']['requests']:.4f}s")
    
    # 測試場景2：有緩存
    print("\n2. 有緩存性能測試")
    clear_cache()
    
    start_time = time.time()
    for name, text_bbox, image_bbox, context_info in test_data * 3:  # 重複3次
        result = enhanced_spatial_scoring_optimized(text_bbox, image_bbox, context_info, enable_cache=True)
    cache_time = time.time() - start_time
    
    # 獲取緩存統計
    cache_stats = get_performance_stats()
    
    results['with_cache'] = {
        'time': cache_time,
        'requests': len(test_data) * 3,
        'cache_stats': cache_stats
    }
    
    print(f"  總時間: {cache_time:.3f}s")
    print(f"  請求數: {results['with_cache']['requests']}")
    print(f"  平均每請求: {cache_time / results['with_cache']['requests']:.4f}s")
    
    if 'overall_stats' in cache_stats:
        overall = cache_stats['overall_stats']
        print(f"  緩存命中率: {overall['overall_hit_rate']:.3f}")
        print(f"  緩存記憶體: {overall['total_memory_usage_mb']:.3f} MB")
    
    # 計算改進
    speedup = no_cache_time / max(cache_time, 0.001)
    print(f"\n💡 緩存改進:")
    print(f"  加速比: {speedup:.2f}x")
    print(f"  時間節省: {((no_cache_time - cache_time) / no_cache_time * 100):.1f}%")
    
    return results

def test_concurrent_performance():
    """測試併發性能"""
    print("\n⚡ 併發性能測試")
    print("=" * 50)
    
    test_data = generate_test_data(10)
    thread_counts = [1, 2, 4, 8]
    results = {}
    
    def worker_function(thread_id: int, data_subset: List, results_list: List):
        """工作線程函數"""
        thread_results = []
        for name, text_bbox, image_bbox, context_info in data_subset:
            start = time.time()
            result = enhanced_spatial_scoring_optimized(
                text_bbox, image_bbox, context_info, enable_cache=True
            )
            end = time.time()
            thread_results.append({
                'thread_id': thread_id,
                'time': end - start,
                'score': result['final_score']
            })
        results_list.extend(thread_results)
    
    for thread_count in thread_counts:
        print(f"\n📈 {thread_count} 線程測試:")
        
        # 清空緩存
        clear_cache()
        
        # 分配數據給線程
        data_per_thread = len(test_data) // thread_count
        threads = []
        all_results = []
        
        start_time = time.time()
        
        for i in range(thread_count):
            start_idx = i * data_per_thread
            end_idx = start_idx + data_per_thread if i < thread_count - 1 else len(test_data)
            data_subset = test_data[start_idx:end_idx]
            
            thread = threading.Thread(
                target=worker_function,
                args=(i, data_subset, all_results)
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有線程完成
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        results[thread_count] = {
            'total_time': total_time,
            'thread_count': thread_count,
            'total_operations': len(all_results),
            'avg_time_per_op': sum(r['time'] for r in all_results) / max(len(all_results), 1),
            'throughput': len(all_results) / max(total_time, 0.001)
        }
        
        print(f"  總時間: {total_time:.3f}s")
        print(f"  總操作數: {len(all_results)}")
        print(f"  吞吐量: {results[thread_count]['throughput']:.1f} ops/s")
        print(f"  平均延遲: {results[thread_count]['avg_time_per_op']:.4f}s")
    
    return results

def test_algorithm_comparison():
    """測試新舊算法性能對比"""
    print("\n🆚 算法對比測試")
    print("=" * 50)
    
    test_data = generate_test_data(50)
    
    # 創建分析器實例
    analyzer = SpatialAnalyzer()
    
    results = {}
    
    # 測試舊算法（基礎空間分析）
    print("\n1. 基礎空間分析:")
    start_time = time.time()
    old_scores = []
    
    for name, text_bbox, image_bbox, context_info in test_data:
        # 使用基礎的空間特徵計算
        features = analyzer.calculate_spatial_features(text_bbox, image_bbox)
        score = features.alignment_score  # 簡化評分
        old_scores.append(score)
    
    old_time = time.time() - start_time
    
    results['basic_algorithm'] = {
        'time': old_time,
        'avg_score': sum(old_scores) / len(old_scores),
        'operations': len(test_data)
    }
    
    print(f"  時間: {old_time:.3f}s")
    print(f"  平均分數: {results['basic_algorithm']['avg_score']:.3f}")
    print(f"  吞吐量: {len(test_data) / max(old_time, 0.001):.1f} ops/s")
    
    # 測試新算法（增強空間分析）
    print("\n2. 增強空間分析:")
    clear_cache()
    start_time = time.time()
    new_scores = []
    
    for name, text_bbox, image_bbox, context_info in test_data:
        result = enhanced_spatial_scoring(text_bbox, image_bbox, context_info)
        new_scores.append(result['final_score'])
    
    new_time = time.time() - start_time
    
    results['enhanced_algorithm'] = {
        'time': new_time,
        'avg_score': sum(new_scores) / len(new_scores),
        'operations': len(test_data)
    }
    
    print(f"  時間: {new_time:.3f}s")
    print(f"  平均分數: {results['enhanced_algorithm']['avg_score']:.3f}")
    print(f"  吞吐量: {len(test_data) / max(new_time, 0.001):.1f} ops/s")
    
    # 測試優化算法（增強+緩存）
    print("\n3. 增強空間分析 + 緩存:")
    clear_cache()
    start_time = time.time()
    optimized_scores = []
    
    # 運行兩次來測試緩存效果
    for name, text_bbox, image_bbox, context_info in test_data * 2:
        result = enhanced_spatial_scoring_optimized(text_bbox, image_bbox, context_info, enable_cache=True)
        optimized_scores.append(result['final_score'])
    
    optimized_time = time.time() - start_time
    
    results['optimized_algorithm'] = {
        'time': optimized_time,
        'avg_score': sum(optimized_scores) / len(optimized_scores),
        'operations': len(optimized_scores),
        'cache_stats': get_performance_stats()
    }
    
    print(f"  時間: {optimized_time:.3f}s")
    print(f"  平均分數: {results['optimized_algorithm']['avg_score']:.3f}")
    print(f"  吞吐量: {len(optimized_scores) / max(optimized_time, 0.001):.1f} ops/s")
    
    # 對比分析
    print(f"\n📊 性能對比:")
    basic_throughput = results['basic_algorithm']['operations'] / max(results['basic_algorithm']['time'], 0.001)
    enhanced_throughput = results['enhanced_algorithm']['operations'] / max(results['enhanced_algorithm']['time'], 0.001)
    optimized_throughput = results['optimized_algorithm']['operations'] / max(results['optimized_algorithm']['time'], 0.001)
    
    print(f"  基礎算法 vs 增強算法: {enhanced_throughput / max(basic_throughput, 0.001):.2f}x")
    print(f"  基礎算法 vs 優化算法: {optimized_throughput / max(basic_throughput, 0.001):.2f}x")
    print(f"  增強算法 vs 優化算法: {optimized_throughput / max(enhanced_throughput, 0.001):.2f}x")
    
    return results

def run_performance_benchmark():
    """運行完整的性能基準測試"""
    print("🚀 空間分析性能基準測試")
    print("=" * 70)
    
    start_time = time.time()
    
    # 記錄系統信息
    print("🖥️  系統信息:")
    print(f"  CPU 核心數: {psutil.cpu_count()}")
    print(f"  總記憶體: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
    print(f"  Python 版本: {sys.version}")
    
    results = {}
    
    try:
        # 1. 規模性能測試
        results['scale_test'] = test_scale_performance()
        
        # 2. 緩存效果測試
        results['cache_test'] = test_cache_effectiveness()
        
        # 3. 併發性能測試
        results['concurrent_test'] = test_concurrent_performance()
        
        # 4. 算法對比測試
        results['algorithm_comparison'] = test_algorithm_comparison()
        
        total_time = time.time() - start_time
        
        print(f"\n🎯 基準測試總結")
        print("=" * 70)
        print(f"總測試時間: {total_time:.2f}s")
        
        # 保存詳細結果
        benchmark_report = {
            'timestamp': time.time(),
            'total_time': total_time,
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'total_memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'python_version': sys.version
            },
            'results': results
        }
        
        with open('benchmark_report.json', 'w', encoding='utf-8') as f:
            json.dump(benchmark_report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 詳細基準報告已保存到: benchmark_report.json")
        
        # 顯示關鍵指標
        print(f"\n📈 關鍵性能指標:")
        
        if 'scale_test' in results and 100 in results['scale_test']:
            scale_100 = results['scale_test'][100]
            print(f"  100對數據處理: {scale_100['total_time']:.3f}s")
            print(f"  平均每對處理時間: {scale_100['avg_time_per_pair']:.4f}s")
            print(f"  吞吐量: {scale_100['throughput_pairs_per_sec']:.1f} pairs/s")
        
        if 'cache_test' in results:
            cache_result = results['cache_test']
            if 'with_cache' in cache_result and 'no_cache' in cache_result:
                speedup = cache_result['no_cache']['time'] / max(cache_result['with_cache']['time'], 0.001)
                print(f"  緩存加速比: {speedup:.2f}x")
        
        if 'algorithm_comparison' in results:
            algo_results = results['algorithm_comparison']
            if 'basic_algorithm' in algo_results and 'optimized_algorithm' in algo_results:
                basic_throughput = algo_results['basic_algorithm']['operations'] / max(algo_results['basic_algorithm']['time'], 0.001)
                opt_throughput = algo_results['optimized_algorithm']['operations'] / max(algo_results['optimized_algorithm']['time'], 0.001)
                improvement = opt_throughput / max(basic_throughput, 0.001)
                print(f"  整體性能提升: {improvement:.2f}x")
        
        print(f"\n🎉 性能基準測試完成！")
        
    except Exception as e:
        print(f"\n❌ 基準測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_performance_benchmark()
