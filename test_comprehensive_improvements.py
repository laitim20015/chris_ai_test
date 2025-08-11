#!/usr/bin/env python3
"""
全面的空間分析改進測試
Comprehensive Spatial Analysis Improvements Test

這個腳本測試我們在Phase 1-3中實現的所有改進：
1. Phase 1: 基礎空間分析改進
2. Phase 2: 佈局分析和候選排序
3. Phase 3: 性能優化和緩存機制

運行這個腳本來驗證所有改進是否正常工作。
"""

import sys
import os
import time
import json
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent))

from src.main import DocumentProcessor
from src.association.spatial_analyzer import (
    enhanced_spatial_scoring, enhanced_spatial_scoring_optimized,
    get_performance_stats, clear_cache
)
from src.association.candidate_ranker import CandidateRanker
from src.association.allen_logic import BoundingBox
from src.config.settings import get_settings

def create_test_bboxes():
    """創建測試用的邊界框"""
    # 測試場景1：理想的圖文關聯（圖片在文字上方）
    text_bbox_ideal = BoundingBox(x=100, y=300, width=300, height=50)
    image_bbox_ideal = BoundingBox(x=120, y=200, width=260, height=80)
    
    # 測試場景2：距離較遠的關聯（應該得分較低）
    text_bbox_far = BoundingBox(x=100, y=500, width=300, height=50)
    image_bbox_far = BoundingBox(x=500, y=200, width=300, height=80)
    
    # 測試場景3：水平重疊度很好的關聯
    text_bbox_aligned = BoundingBox(x=100, y=350, width=300, height=50)
    image_bbox_aligned = BoundingBox(x=110, y=250, width=280, height=80)
    
    # 測試場景4：有介入元素的情況
    text_bbox_intervened = BoundingBox(x=100, y=400, width=300, height=50)
    image_bbox_intervened = BoundingBox(x=120, y=200, width=260, height=80)
    
    return [
        ("理想關聯", text_bbox_ideal, image_bbox_ideal),
        ("距離較遠", text_bbox_far, image_bbox_far),
        ("良好對齊", text_bbox_aligned, image_bbox_aligned),
        ("有介入元素", text_bbox_intervened, image_bbox_intervened)
    ]

def test_phase1_improvements():
    """測試Phase 1的基礎空間分析改進"""
    print("🔍 測試 Phase 1: 基礎空間分析改進")
    print("=" * 50)
    
    test_cases = create_test_bboxes()
    results = []
    
    for name, text_bbox, image_bbox in test_cases:
        print(f"\n測試案例: {name}")
        print(f"文本框: ({text_bbox.x}, {text_bbox.y}) + ({text_bbox.width}, {text_bbox.height})")
        print(f"圖片框: ({image_bbox.x}, {image_bbox.y}) + ({image_bbox.width}, {image_bbox.height})")
        
        # 創建上下文信息
        context_info = {
            'layout_type': 'single_column',
            'all_elements': [text_bbox, image_bbox],
            'page_width': 600,
            'page_height': 800
        }
        
        # 使用增強的空間評分
        result = enhanced_spatial_scoring(text_bbox, image_bbox, context_info)
        
        print(f"最終分數: {result['final_score']:.3f}")
        print(f"組件分數:")
        for component, score in result['component_scores'].items():
            print(f"  {component}: {score:.3f}")
        
        if 'details' in result:
            print(f"詳細信息:")
            print(f"  垂直關係: {result['details']['relationship']}")
            print(f"  垂直間隙: {result['details']['vertical_gap']:.1f}")
            print(f"  水平重疊: {result['details']['horizontal_overlap']:.3f}")
        
        results.append((name, result['final_score']))
        print("-" * 30)
    
    # 驗證結果是否符合預期
    scores = [score for _, score in results]
    ideal_score = scores[0]  # 理想關聯應該得分最高
    
    print(f"\n📊 Phase 1 測試結果總結:")
    for name, score in results:
        print(f"  {name}: {score:.3f}")
    
    print(f"\n✅ Phase 1 驗證:")
    print(f"  理想關聯得分: {ideal_score:.3f}")
    print(f"  是否為最高分: {'是' if ideal_score == max(scores) else '否'}")
    
    return results

def test_phase2_improvements():
    """測試Phase 2的佈局分析和候選排序改進"""
    print("\n🏗️  測試 Phase 2: 佈局分析和候選排序")
    print("=" * 50)
    
    # 創建候選排序器
    ranker = CandidateRanker()
    
    # 創建測試候選
    image_bbox = BoundingBox(x=200, y=200, width=200, height=100)
    
    candidates = [
        {
            'id': 'text1',
            'content': 'Figure 1: This is a test image showing the workflow process.',
            'bbox': BoundingBox(x=180, y=320, width=240, height=30),
            'type': 'text'
        },
        {
            'id': 'text2', 
            'content': 'This paragraph discusses the methodology used in our research.',
            'bbox': BoundingBox(x=50, y=350, width=250, height=50),
            'type': 'text'
        },
        {
            'id': 'text3',
            'content': 'The results shown in the diagram indicate significant improvements.',
            'bbox': BoundingBox(x=180, y=150, width=240, height=30),
            'type': 'text'
        }
    ]
    
    context_info = {
        'layout_type': 'single_column',
        'all_elements': candidates + [{'bbox': image_bbox, 'type': 'image'}],
        'page_width': 500,
        'page_height': 600
    }
    
    print("測試候選文本:")
    for i, candidate in enumerate(candidates, 1):
        print(f"  {i}. {candidate['content'][:50]}...")
    
    # 執行候選排序
    start_time = time.time()
    ranked_results = ranker.rank_candidates(
        text_candidates=candidates,
        image_bbox=image_bbox,
        image_content="workflow diagram",
        context_info=context_info
    )
    ranking_time = time.time() - start_time
    
    print(f"\n📈 候選排序結果 (耗時: {ranking_time:.3f}s):")
    for i, result in enumerate(ranked_results[:3], 1):
        print(f"  {i}. 分數: {result.scores.final_score:.3f} - {result.text_id}")
        print(f"     Caption: {result.scores.caption_score:.3f}, 空間: {result.scores.spatial_score:.3f}")
        print(f"     質量: {result.scores.quality.value}, 置信度: {result.scores.confidence:.3f}")
    
    # 檢查是否Caption被正確識別並排在前面
    best_candidate = ranked_results[0]
    has_caption = 'Figure' in candidates[0]['content']
    
    print(f"\n✅ Phase 2 驗證:")
    print(f"  最佳候選ID: {best_candidate.text_id}")
    print(f"  包含Caption: {'是' if has_caption else '否'}")
    print(f"  Caption優先級: {'正確' if best_candidate.text_id == 'text1' else '需要調整'}")
    print(f"  總候選數: {len(ranked_results)}")
    
    return ranked_results

def test_phase3_performance():
    """測試Phase 3的性能優化和緩存機制"""
    print("\n⚡ 測試 Phase 3: 性能優化和緩存機制")
    print("=" * 50)
    
    test_cases = create_test_bboxes()
    
    # 清空緩存，開始測試
    clear_cache()
    
    print("1. 測試緩存性能")
    
    # 第一次運行（應該是緩存未命中）
    print("\n第一次運行（冷緩存）:")
    first_run_times = []
    
    for name, text_bbox, image_bbox in test_cases:
        context_info = {
            'layout_type': 'single_column',
            'all_elements': [text_bbox, image_bbox],
            'page_width': 600,
            'page_height': 800
        }
        
        start_time = time.time()
        result = enhanced_spatial_scoring_optimized(text_bbox, image_bbox, context_info, enable_cache=True)
        end_time = time.time()
        
        computation_time = end_time - start_time
        first_run_times.append(computation_time)
        
        print(f"  {name}: {computation_time:.4f}s, 分數: {result['final_score']:.3f}, 緩存命中: {result['performance']['cache_hit']}")
    
    # 第二次運行（應該是緩存命中）
    print("\n第二次運行（熱緩存）:")
    second_run_times = []
    
    for name, text_bbox, image_bbox in test_cases:
        context_info = {
            'layout_type': 'single_column',
            'all_elements': [text_bbox, image_bbox],
            'page_width': 600,
            'page_height': 800
        }
        
        start_time = time.time()
        result = enhanced_spatial_scoring_optimized(text_bbox, image_bbox, context_info, enable_cache=True)
        end_time = time.time()
        
        computation_time = end_time - start_time
        second_run_times.append(computation_time)
        
        print(f"  {name}: {computation_time:.4f}s, 分數: {result['final_score']:.3f}, 緩存命中: {result['performance']['cache_hit']}")
    
    # 性能統計
    stats = get_performance_stats()
    
    print(f"\n📊 緩存性能統計:")
    if 'overall_stats' in stats:
        overall = stats['overall_stats']
        print(f"  總請求數: {overall['total_requests']}")
        print(f"  總命中率: {overall['overall_hit_rate']:.3f}")
        print(f"  內存使用: {overall['total_memory_usage_mb']:.2f} MB")
    
    # 計算性能提升
    avg_first_run = sum(first_run_times) / len(first_run_times)
    avg_second_run = sum(second_run_times) / len(second_run_times)
    speedup = avg_first_run / avg_second_run if avg_second_run > 0 else 1
    
    print(f"\n⚡ 性能分析:")
    print(f"  第一次平均時間: {avg_first_run:.4f}s")
    print(f"  第二次平均時間: {avg_second_run:.4f}s")
    print(f"  加速倍數: {speedup:.1f}x")
    
    print(f"\n✅ Phase 3 驗證:")
    print(f"  緩存機制: {'正常工作' if speedup > 2 else '需要優化'}")
    print(f"  性能提升: {'顯著' if speedup > 5 else '一般' if speedup > 2 else '微小'}")
    
    return stats

def test_document_processing_integration():
    """測試與主要文檔處理流程的集成"""
    print("\n🔗 測試集成: 文檔處理流程")
    print("=" * 50)
    
    # 檢查是否有測試文檔
    test_file = "Workflows-sample.pdf"
    if not Path(test_file).exists():
        print(f"⚠️  測試文檔 {test_file} 不存在，跳過集成測試")
        return None
    
    print(f"正在處理測試文檔: {test_file}")
    
    try:
        # 初始化文檔處理器
        processor = DocumentProcessor()
        
        # 處理文檔
        start_time = time.time()
        result = processor.process_document(test_file)
        processing_time = time.time() - start_time
        
        print(f"✅ 文檔處理完成 (耗時: {processing_time:.2f}s)")
        print(f"   提取的圖片數量: {len(result.get('images', []))}")
        print(f"   提取的文本塊數量: {len(result.get('text_blocks', []))}")
        
        # 檢查是否有關聯分析結果
        if 'associations' in result:
            associations = result['associations']
            print(f"   圖文關聯數量: {len(associations)}")
            
            # 顯示前幾個關聯的分數分布
            if associations:
                scores = [assoc.get('final_score', 0) for assoc in associations[:5]]
                print(f"   前5個關聯分數: {[f'{s:.3f}' for s in scores]}")
        
        return result
        
    except Exception as e:
        print(f"❌ 集成測試失敗: {e}")
        return None

def run_comprehensive_test():
    """運行全面測試"""
    print("🚀 開始全面的空間分析改進測試")
    print("=" * 70)
    
    # 記錄開始時間
    total_start_time = time.time()
    
    try:
        # Phase 1 測試
        phase1_results = test_phase1_improvements()
        
        # Phase 2 測試
        phase2_results = test_phase2_improvements()
        
        # Phase 3 測試
        phase3_results = test_phase3_performance()
        
        # 集成測試
        integration_result = test_document_processing_integration()
        
        # 總結
        total_time = time.time() - total_start_time
        
        print(f"\n🎯 測試總結")
        print("=" * 70)
        print(f"總測試時間: {total_time:.2f}s")
        
        print(f"\n📋 各階段測試結果:")
        print(f"  ✅ Phase 1 (基礎改進): 完成")
        print(f"  ✅ Phase 2 (佈局分析): 完成") 
        print(f"  ✅ Phase 3 (性能優化): 完成")
        print(f"  {'✅' if integration_result else '⚠️ '} 集成測試: {'完成' if integration_result else '跳過'}")
        
        print(f"\n🎉 所有測試執行完畢！")
        
        # 保存測試結果
        test_report = {
            'timestamp': time.time(),
            'total_time': total_time,
            'phase1_results': [{'name': name, 'score': score} for name, score in phase1_results],
            'phase2_completed': phase2_results is not None,
            'phase3_stats': phase3_results,
            'integration_success': integration_result is not None
        }
        
        with open('test_report.json', 'w', encoding='utf-8') as f:
            json.dump(test_report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 測試報告已保存到: test_report.json")
        
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_comprehensive_test()
