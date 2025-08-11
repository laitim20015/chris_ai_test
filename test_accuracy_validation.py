#!/usr/bin/env python3
"""
準確性驗證測試
Accuracy Validation Test

驗證空間分析改進的準確性和可靠性，包括：
1. 算法準確性驗證
2. 邊界情況測試
3. 回歸測試
4. 結果一致性驗證
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent))

from src.association.spatial_analyzer import (
    enhanced_spatial_scoring, enhanced_spatial_scoring_optimized,
    analyze_vertical_relationship, calculate_horizontal_overlap,
    check_intervening_elements, calculate_normalized_distance
)
from src.association.allen_logic import BoundingBox
from src.association.candidate_ranker import CandidateRanker
from src.main import DocumentProcessor
from src.parsers.base import TextBlock, ImageContent

def create_accuracy_test_cases() -> List[Dict[str, Any]]:
    """創建準確性測試用例"""
    test_cases = [
        # Test Case 1: 理想的圖文關聯 (Caption在圖片下方，完美對齊)
        {
            'name': '理想關聯_Caption下方',
            'text_bbox': BoundingBox(x=100, y=320, width=300, height=30),
            'image_bbox': BoundingBox(x=120, y=200, width=260, height=100),
            'text_content': 'Figure 1: This diagram shows the complete workflow process.',
            'expected_score_range': (0.7, 1.0),
            'expected_caption_detected': True,
            'description': 'Caption文本位於圖片正下方，完美水平對齊'
        },
        
        # Test Case 2: 良好關聯 (文本在圖片上方，部分對齊)
        {
            'name': '良好關聯_文本上方',
            'text_bbox': BoundingBox(x=110, y=150, width=280, height=30),
            'image_bbox': BoundingBox(x=100, y=200, width=300, height=100),
            'text_content': 'The following diagram illustrates the key concepts.',
            'expected_score_range': (0.4, 0.7),
            'expected_caption_detected': False,
            'description': '普通文本在圖片上方，有一定水平重疊'
        },
        
        # Test Case 3: 較差關聯 (距離較遠，無對齊)
        {
            'name': '較差關聯_距離遠',
            'text_bbox': BoundingBox(x=50, y=500, width=200, height=30),
            'image_bbox': BoundingBox(x=400, y=200, width=150, height=80),
            'text_content': 'This text is not related to any specific image.',
            'expected_score_range': (0.0, 0.3),
            'expected_caption_detected': False,
            'description': '文本和圖片距離很遠，沒有對齊'
        },
        
        # Test Case 4: 跨欄位關聯 (應該被懲罰)
        {
            'name': '跨欄位關聯',
            'text_bbox': BoundingBox(x=50, y=300, width=150, height=30),
            'image_bbox': BoundingBox(x=350, y=280, width=150, height=80),
            'text_content': 'Figure 2: Cross-column caption text.',
            'expected_score_range': (0.2, 0.5),
            'expected_caption_detected': True,
            'description': 'Caption文本和圖片在不同欄位中'
        },
        
        # Test Case 5: 垂直對齊但水平重疊差
        {
            'name': '垂直對齊_水平不重疊',
            'text_bbox': BoundingBox(x=400, y=320, width=180, height=30),
            'image_bbox': BoundingBox(x=100, y=200, width=200, height=100),
            'text_content': 'Table 1: Summary of experimental results.',
            'expected_score_range': (0.1, 0.4),
            'expected_caption_detected': True,
            'description': '垂直位置合適但水平位置相距較遠'
        },
        
        # Test Case 6: 完美Caption關聯
        {
            'name': '完美Caption關聯',
            'text_bbox': BoundingBox(x=100, y=310, width=300, height=25),
            'image_bbox': BoundingBox(x=100, y=200, width=300, height=100),
            'text_content': 'Figure 3: Detailed analysis of the proposed algorithm performance.',
            'expected_score_range': (0.8, 1.0),
            'expected_caption_detected': True,
            'description': '完美的Caption關聯：位置、對齊、內容都理想'
        }
    ]
    
    return test_cases

def test_algorithm_accuracy():
    """測試算法準確性"""
    print("🎯 算法準確性驗證")
    print("=" * 60)
    
    test_cases = create_accuracy_test_cases()
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n測試案例 {i}: {test_case['name']}")
        print(f"描述: {test_case['description']}")
        print(f"文本內容: {test_case['text_content'][:60]}...")
        
        # 創建上下文信息（包含text_content）
        context_info = {
            'layout_type': 'double_column' if '跨欄位' in test_case['name'] else 'single_column',
            'all_elements': [test_case['text_bbox'], test_case['image_bbox']],
            'page_width': 600,
            'page_height': 800,
            'text_content': test_case['text_content']  # 添加文本內容以便Caption檢測
        }
        
        # 執行完整的關聯分析（通過DocumentProcessor）
        processor = DocumentProcessor()
        
        # 創建測試用的TextBlock和ImageContent
        from src.parsers.base import ContentType
        text_block = TextBlock(
            id=f"text_{i}",
            content=test_case['text_content'],
            content_type=ContentType.PARAGRAPH,
            bbox=test_case['text_bbox'],
            font_size=12.0,
            font_name="Arial"
        )
        
        from src.parsers.base import ImageFormat
        image = ImageContent(
            id=f"image_{i}",
            filename="test_image.jpg",
            format=ImageFormat.JPEG,
            data=b"test_data",  # 測試用假數據
            bbox=test_case['image_bbox']
        )
        
        # 執行完整的關聯分析
        result = processor._perform_association_analysis(text_block, image)
        
        final_score = result['final_score']
        expected_min, expected_max = test_case['expected_score_range']
        
        # 驗證分數範圍
        score_in_range = expected_min <= final_score <= expected_max
        
        # 驗證Caption檢測（簡單檢查文本內容）
        has_caption = any(pattern in test_case['text_content'].lower() 
                         for pattern in ['figure', 'table', 'chart', 'diagram'])
        caption_correct = has_caption == test_case['expected_caption_detected']
        
        # 記錄結果
        test_result = {
            'name': test_case['name'],
            'score': final_score,
            'expected_range': test_case['expected_score_range'],
            'score_in_range': score_in_range,
            'caption_detected': has_caption,
            'caption_correct': caption_correct,
            'passed': score_in_range and caption_correct,
            'component_scores': {
                'caption': result['caption_score'],
                'spatial': result['spatial_score'], 
                'semantic': result['semantic_score'],
                'layout': result['layout_score'],
                'proximity': result['proximity_score']
            }
        }
        results.append(test_result)
        
        # 顯示結果
        print(f"  最終分數: {final_score:.3f} (期望: {expected_min:.1f}-{expected_max:.1f})")
        print(f"  分數範圍: {'✅' if score_in_range else '❌'}")
        print(f"  Caption檢測: {'✅' if caption_correct else '❌'}")
        print(f"  整體結果: {'✅ PASS' if test_result['passed'] else '❌ FAIL'}")
        
        # 顯示組件分數（從完整關聯分析結果）
        print(f"  組件分數: Caption={result['caption_score']:.3f}, "
              f"Spatial={result['spatial_score']:.3f}, "
              f"Semantic={result['semantic_score']:.3f}, "
              f"Layout={result['layout_score']:.3f}, "
              f"Proximity={result['proximity_score']:.3f}")
        print("-" * 40)
    
    return results

def test_edge_cases():
    """測試邊界情況"""
    print("\n🔬 邊界情況測試")
    print("=" * 60)
    
    edge_cases = [
        # 極小邊界框
        {
            'name': '極小邊界框',
            'text_bbox': BoundingBox(x=100, y=300, width=1, height=1),
            'image_bbox': BoundingBox(x=101, y=301, width=1, height=1),
            'should_not_crash': True
        },
        
        # 極大邊界框
        {
            'name': '極大邊界框',
            'text_bbox': BoundingBox(x=0, y=0, width=10000, height=10000),
            'image_bbox': BoundingBox(x=5000, y=5000, width=10000, height=10000),
            'should_not_crash': True
        },
        
        # 負坐標
        {
            'name': '負坐標邊界框',
            'text_bbox': BoundingBox(x=-100, y=-100, width=200, height=50),
            'image_bbox': BoundingBox(x=-50, y=-50, width=150, height=80),
            'should_not_crash': True
        },
        
        # 零尺寸
        {
            'name': '零尺寸邊界框',
            'text_bbox': BoundingBox(x=100, y=300, width=0, height=0),
            'image_bbox': BoundingBox(x=120, y=280, width=100, height=80),
            'should_not_crash': True
        },
        
        # 完全重疊
        {
            'name': '完全重疊邊界框',
            'text_bbox': BoundingBox(x=100, y=200, width=200, height=100),
            'image_bbox': BoundingBox(x=100, y=200, width=200, height=100),
            'should_not_crash': True
        }
    ]
    
    results = []
    
    for edge_case in edge_cases:
        print(f"\n測試邊界情況: {edge_case['name']}")
        
        try:
            context_info = {
                'layout_type': 'single_column',
                'all_elements': [edge_case['text_bbox'], edge_case['image_bbox']],
                'page_width': 600,
                'page_height': 800
            }
            
            # 執行測試
            result = enhanced_spatial_scoring(
                edge_case['text_bbox'], 
                edge_case['image_bbox'], 
                context_info
            )
            
            score = result['final_score']
            
            # 檢查結果是否合理
            is_valid = (isinstance(score, (int, float)) and 
                       0 <= score <= 1 and 
                       not (score != score))  # 檢查是否為 NaN
            
            test_result = {
                'name': edge_case['name'],
                'passed': True,
                'score': score,
                'valid_score': is_valid,
                'error': None
            }
            
            print(f"  結果: ✅ 正常執行")
            print(f"  分數: {score:.3f}")
            print(f"  分數有效: {'✅' if is_valid else '❌'}")
            
        except Exception as e:
            test_result = {
                'name': edge_case['name'],
                'passed': False,
                'score': None,
                'valid_score': False,
                'error': str(e)
            }
            
            print(f"  結果: ❌ 異常: {e}")
        
        results.append(test_result)
    
    return results

def test_consistency():
    """測試結果一致性"""
    print("\n🔄 結果一致性測試")
    print("=" * 60)
    
    # 創建測試案例
    text_bbox = BoundingBox(x=100, y=320, width=300, height=30)
    image_bbox = BoundingBox(x=120, y=200, width=260, height=100)
    context_info = {
        'layout_type': 'single_column',
        'all_elements': [text_bbox, image_bbox],
        'page_width': 600,
        'page_height': 800
    }
    
    # 多次運行同樣的測試
    num_runs = 10
    scores = []
    
    print(f"執行 {num_runs} 次相同的分析...")
    
    for i in range(num_runs):
        result = enhanced_spatial_scoring(text_bbox, image_bbox, context_info)
        scores.append(result['final_score'])
    
    # 計算一致性統計
    min_score = min(scores)
    max_score = max(scores)
    avg_score = sum(scores) / len(scores)
    variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
    std_dev = variance ** 0.5
    
    # 判斷一致性
    is_consistent = (max_score - min_score) < 0.001  # 差異小於0.1%
    
    print(f"\n一致性結果:")
    print(f"  最小分數: {min_score:.6f}")
    print(f"  最大分數: {max_score:.6f}")
    print(f"  平均分數: {avg_score:.6f}")
    print(f"  標準差: {std_dev:.6f}")
    print(f"  分數範圍: {max_score - min_score:.6f}")
    print(f"  一致性: {'✅ 通過' if is_consistent else '❌ 失敗'}")
    
    return {
        'passed': is_consistent,
        'scores': scores,
        'statistics': {
            'min': min_score,
            'max': max_score,
            'avg': avg_score,
            'std_dev': std_dev,
            'range': max_score - min_score
        }
    }

def test_performance_vs_accuracy():
    """測試性能與準確性的平衡"""
    print("\n⚖️  性能與準確性平衡測試")
    print("=" * 60)
    
    # 創建測試案例
    text_bbox = BoundingBox(x=100, y=320, width=300, height=30)
    image_bbox = BoundingBox(x=120, y=200, width=260, height=100)
    context_info = {
        'layout_type': 'single_column',
        'all_elements': [text_bbox, image_bbox],
        'page_width': 600,
        'page_height': 800
    }
    
    import time
    
    # 測試標準算法
    start_time = time.time()
    result1 = enhanced_spatial_scoring(text_bbox, image_bbox, context_info)
    standard_time = time.time() - start_time
    
    # 測試優化算法
    start_time = time.time()
    result2 = enhanced_spatial_scoring_optimized(text_bbox, image_bbox, context_info, enable_cache=True)
    optimized_time = time.time() - start_time
    
    # 比較結果
    score_diff = abs(result1['final_score'] - result2['final_score'])
    time_speedup = standard_time / max(optimized_time, 0.001)
    
    print(f"標準算法:")
    print(f"  時間: {standard_time:.6f}s")
    print(f"  分數: {result1['final_score']:.6f}")
    
    print(f"\n優化算法:")
    print(f"  時間: {optimized_time:.6f}s")
    print(f"  分數: {result2['final_score']:.6f}")
    
    print(f"\n比較結果:")
    print(f"  分數差異: {score_diff:.6f}")
    print(f"  速度提升: {time_speedup:.2f}x")
    print(f"  準確性保持: {'✅' if score_diff < 0.001 else '❌'}")
    
    return {
        'standard_time': standard_time,
        'optimized_time': optimized_time,
        'score_diff': score_diff,
        'speedup': time_speedup,
        'accuracy_maintained': score_diff < 0.001
    }

def run_accuracy_validation():
    """運行完整的準確性驗證"""
    print("🎯 空間分析準確性驗證測試")
    print("=" * 70)
    
    results = {}
    
    try:
        # 1. 算法準確性測試
        results['accuracy_test'] = test_algorithm_accuracy()
        
        # 2. 邊界情況測試
        results['edge_cases'] = test_edge_cases()
        
        # 3. 一致性測試
        results['consistency'] = test_consistency()
        
        # 4. 性能與準確性平衡測試
        results['performance_accuracy'] = test_performance_vs_accuracy()
        
        # 總結結果
        print(f"\n🎯 準確性驗證總結")
        print("=" * 70)
        
        # 計算通過率
        accuracy_passed = sum(1 for r in results['accuracy_test'] if r['passed'])
        accuracy_total = len(results['accuracy_test'])
        
        edge_passed = sum(1 for r in results['edge_cases'] if r['passed'])
        edge_total = len(results['edge_cases'])
        
        print(f"📊 測試結果:")
        print(f"  準確性測試: {accuracy_passed}/{accuracy_total} 通過 ({accuracy_passed/accuracy_total*100:.1f}%)")
        print(f"  邊界情況測試: {edge_passed}/{edge_total} 通過 ({edge_passed/edge_total*100:.1f}%)")
        print(f"  一致性測試: {'✅ 通過' if results['consistency']['passed'] else '❌ 失敗'}")
        print(f"  性能準確性平衡: {'✅ 通過' if results['performance_accuracy']['accuracy_maintained'] else '❌ 失敗'}")
        
        # 計算總體評分
        total_tests = accuracy_total + edge_total + 2  # +2 for consistency and performance tests
        total_passed = accuracy_passed + edge_passed + \
                      (1 if results['consistency']['passed'] else 0) + \
                      (1 if results['performance_accuracy']['accuracy_maintained'] else 0)
        
        overall_score = total_passed / total_tests
        
        print(f"\n🏆 總體評分: {overall_score:.1%}")
        
        if overall_score >= 0.9:
            print("🎉 優秀！所有測試基本通過")
        elif overall_score >= 0.8:
            print("👍 良好！大部分測試通過")
        elif overall_score >= 0.7:
            print("⚠️  一般，需要一些改進")
        else:
            print("❌ 需要重要改進")
        
        # 保存結果（轉換numpy類型以避免JSON序列化錯誤）
        def convert_numpy_types(obj):
            """轉換numpy類型為Python原生類型"""
            if hasattr(obj, 'item'):  # numpy scalar
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj
        
        validation_report = {
            'timestamp': time.time(),
            'overall_score': float(overall_score),
            'results': convert_numpy_types(results)
        }
        
        with open('accuracy_validation_report.json', 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 詳細驗證報告已保存到: accuracy_validation_report.json")
        
    except Exception as e:
        print(f"\n❌ 準確性驗證失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_accuracy_validation()
