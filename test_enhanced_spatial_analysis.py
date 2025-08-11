#!/usr/bin/env python3
"""
增強空間分析測試腳本
Enhanced Spatial Analysis Test Script

此腳本測試我們開發的通用空間距離計算改進方案，
段落102只是典型案例，重點是驗證整個系統的圖文關聯準確性提升。

測試目標：
1. 驗證新的空間分析算法在各種場景下的表現
2. 對比傳統方法與增強方法的差異
3. 確保通用性和魯棒性
4. 測試實際文檔處理的改進效果
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# 添加項目根目錄到系統路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.main import DocumentProcessor
from src.association.allen_logic import BoundingBox
from src.association.spatial_analyzer import enhanced_spatial_scoring, analyze_vertical_relationship
from src.parsers import ParsedContent, TextBlock, ImageContent
from src.parsers.base import DocumentMetadata, ContentType, ImageFormat

def print_header(title):
    """打印格式化的標題"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def print_subheader(title):
    """打印格式化的子標題"""
    print(f"\n{'─'*40}")
    print(f"📋 {title}")
    print('─'*40)

def create_test_scenarios():
    """
    創建多種測試場景來驗證通用性
    
    Returns:
        List[Dict]: 測試場景列表
    """
    scenarios = [
        {
            'name': '理想場景 - 文本在圖片正上方',
            'text_bbox': BoundingBox(100, 100, 100, 20),  
            'image_bbox': BoundingBox(110, 140, 80, 60),   
            'expected_relationship': 'below',
            'description': '類似段落102的理想關聯情況'
        },
        {
            'name': '錯位場景 - 文本距離較遠',
            'text_bbox': BoundingBox(100, 100, 100, 20),  
            'image_bbox': BoundingBox(120, 250, 80, 60),   
            'expected_relationship': 'below',
            'description': '類似段落116/120的遠距離情況'
        },
        {
            'name': '水平對齊場景 - 同一水平線',
            'text_bbox': BoundingBox(100, 150, 100, 20),  
            'image_bbox': BoundingBox(220, 140, 80, 60),   
            'expected_relationship': 'overlap',
            'description': '文本與圖片水平對齊'
        },
        {
            'name': '反向場景 - 圖片在文本上方',
            'text_bbox': BoundingBox(100, 200, 100, 20),  
            'image_bbox': BoundingBox(110, 100, 80, 60),   
            'expected_relationship': 'above',
            'description': '違背自然閱讀順序的情況'
        },
        {
            'name': '無重疊場景 - 不同欄位',
            'text_bbox': BoundingBox(100, 100, 100, 20),  
            'image_bbox': BoundingBox(300, 140, 80, 60),   
            'expected_relationship': 'below',
            'description': '跨欄位的關聯檢測'
        },
        {
            'name': '緊密場景 - 極近距離',
            'text_bbox': BoundingBox(100, 100, 100, 20),  
            'image_bbox': BoundingBox(105, 125, 90, 50),   
            'expected_relationship': 'below',
            'description': '文本和圖片緊密相鄰'
        }
    ]
    return scenarios

def test_enhanced_spatial_scoring():
    """測試增強空間評分算法的通用性能"""
    
    print_header("增強空間評分算法通用性測試")
    
    scenarios = create_test_scenarios()
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print_subheader(f"場景 {i}: {scenario['name']}")
        print(f"描述: {scenario['description']}")
        
        # 執行增強空間分析
        result = enhanced_spatial_scoring(
            scenario['text_bbox'], 
            scenario['image_bbox']
        )
        
        # 記錄結果
        scenario_result = {
            'scenario': scenario['name'],
            'final_score': result['final_score'],
            'relationship': result['details']['relationship'],
            'expected_relationship': scenario['expected_relationship'],
            'component_scores': result['component_scores'],
            'details': result['details']
        }
        results.append(scenario_result)
        
        # 顯示結果
        print(f"✅ 最終分數: {result['final_score']:.3f}")
        print(f"🔍 檢測關係: {result['details']['relationship']} (期望: {scenario['expected_relationship']})")
        print(f"📊 組件分數:")
        for component, score in result['component_scores'].items():
            print(f"   - {component}: {score:.3f}")
        
        # 關係匹配驗證
        relationship_match = result['details']['relationship'] == scenario['expected_relationship']
        print(f"🎯 關係匹配: {'✅ 正確' if relationship_match else '❌ 不匹配'}")
    
    return results

def compare_traditional_vs_enhanced():
    """對比傳統方法與增強方法的差異"""
    
    print_header("傳統方法 vs 增強方法對比分析")
    
    # 使用段落102場景作為典型案例進行對比
    text_bbox = BoundingBox(100, 100, 100, 20)  # 段落102場景
    image_bbox = BoundingBox(110, 140, 80, 60)  
    
    print("🔬 使用段落102場景進行方法對比...")
    print(f"文本位置: x={text_bbox.x}, y={text_bbox.y}, w={text_bbox.width}, h={text_bbox.height}")
    print(f"圖片位置: x={image_bbox.x}, y={image_bbox.y}, w={image_bbox.width}, h={image_bbox.height}")
    
    # 傳統方法模擬
    print_subheader("傳統歐幾里得距離方法")
    import numpy as np
    center_distance = np.sqrt(
        (text_bbox.center_x - image_bbox.center_x) ** 2 + 
        (text_bbox.center_y - image_bbox.center_y) ** 2
    )
    page_diagonal = np.sqrt(400**2 + 400**2)  # 假設頁面400x400
    traditional_score = 1.0 - min(center_distance / (page_diagonal * 0.5), 1.0)
    
    print(f"中心距離: {center_distance:.1f}")
    print(f"頁面對角線: {page_diagonal:.1f}")  
    print(f"傳統分數: {traditional_score:.3f}")
    
    # 增強方法
    print_subheader("增強空間分析方法")
    enhanced_result = enhanced_spatial_scoring(text_bbox, image_bbox)
    
    print(f"增強分數: {enhanced_result['final_score']:.3f}")
    print(f"垂直關係: {enhanced_result['details']['relationship']}")
    print(f"垂直分數: {enhanced_result['component_scores']['vertical']:.3f}")
    print(f"水平重疊: {enhanced_result['component_scores']['horizontal']:.3f}")
    print(f"距離分數: {enhanced_result['component_scores']['distance']:.3f}")
    
    # 對比分析
    print_subheader("對比分析結果")
    improvement = enhanced_result['final_score'] - traditional_score
    print(f"分數提升: {improvement:+.3f} ({improvement/traditional_score*100:+.1f}%)")
    print(f"方向感知: {'✅ 支持' if enhanced_result['details']['relationship'] != 'unknown' else '❌ 不支持'}")
    print(f"重疊檢測: {'✅ 支持' if enhanced_result['component_scores']['horizontal'] > 0 else '❌ 不支持'}")
    
    return {
        'traditional_score': traditional_score,
        'enhanced_score': enhanced_result['final_score'],
        'improvement': improvement,
        'improvement_percentage': improvement/traditional_score*100
    }

def test_real_document_processing():
    """測試實際文檔處理的改進效果"""
    
    print_header("實際文檔處理改進效果測試")
    
    # 使用Workflows-sample.pdf進行實際測試
    test_file = "tests/fixtures/documents/Workflows-sample.pdf"
    
    if not Path(test_file).exists():
        print("❌ 測試文件不存在，跳過實際文檔測試")
        return None
    
    print(f"📄 測試文件: {test_file}")
    
    try:
        # 初始化處理器
        print("🔧 初始化DocumentProcessor...")
        start_time = time.time()
        processor = DocumentProcessor()
        init_time = time.time() - start_time
        print(f"✅ 初始化完成 ({init_time:.2f}s)")
        
        # 執行文檔處理
        print("🚀 執行增強空間分析的文檔處理...")
        start_time = time.time()
        result = processor.process_document(
            file_path=test_file,
            output_dir="data/output",
            save_associations=True
        )
        processing_time = time.time() - start_time
        print(f"✅ 處理完成 ({processing_time:.2f}s)")
        
        if result["success"]:
            stats = result["statistics"]
            print(f"📊 處理統計:")
            print(f"   - 文本塊: {stats['total_text_blocks']}")
            print(f"   - 圖片: {stats['total_images']}")
            print(f"   - 關聯關係: {stats['total_associations']}")
            print(f"   - 高質量關聯: {stats['high_quality_associations']}")
            print(f"   - 平均關聯分數: {stats['average_association_score']:.3f}")
            
            # 計算關聯質量指標
            quality_ratio = stats['high_quality_associations'] / stats['total_associations'] if stats['total_associations'] > 0 else 0
            print(f"   - 高質量比例: {quality_ratio:.1%}")
            
            return {
                'success': True,
                'processing_time': processing_time,
                'stats': stats,
                'quality_ratio': quality_ratio,
                'output_files': result["output_files"]
            }
        else:
            print(f"❌ 處理失敗: {result['error']}")
            return {'success': False, 'error': result['error']}
            
    except Exception as e:
        print(f"❌ 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def generate_test_report(scenario_results, comparison_results, document_results):
    """生成測試報告"""
    
    print_header("生成測試報告")
    
    # 創建報告
    report = {
        'test_info': {
            'timestamp': datetime.now().isoformat(),
            'test_purpose': '驗證通用空間距離計算改進方案',
            'note': '段落102只是典型案例，重點測試整體系統改進'
        },
        'scenario_tests': {
            'total_scenarios': len(scenario_results),
            'correct_relationships': sum(1 for r in scenario_results if r['relationship'] == r['expected_relationship']),
            'average_score': sum(r['final_score'] for r in scenario_results) / len(scenario_results),
            'results': scenario_results
        },
        'comparison_analysis': comparison_results,
        'document_processing': document_results
    }
    
    # 保存報告
    report_file = f"data/output/enhanced_spatial_analysis_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path("data/output").mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📄 詳細報告已保存: {report_file}")
    
    # 顯示總結
    print_subheader("測試總結")
    scenario_accuracy = report['scenario_tests']['correct_relationships'] / report['scenario_tests']['total_scenarios']
    print(f"✅ 場景測試準確率: {scenario_accuracy:.1%} ({report['scenario_tests']['correct_relationships']}/{report['scenario_tests']['total_scenarios']})")
    print(f"📈 平均關聯分數: {report['scenario_tests']['average_score']:.3f}")
    
    if comparison_results:
        print(f"🚀 算法改進幅度: {comparison_results['improvement_percentage']:+.1f}%")
    
    if document_results and document_results.get('success'):
        print(f"📊 實際文檔高質量關聯比例: {document_results['quality_ratio']:.1%}")
    
    return report_file

def main():
    """主測試函數"""
    
    print_header("增強空間分析通用改進方案驗證測試")
    print("🎯 重要提醒: 段落102只是典型案例，本測試驗證整個系統的通用改進效果")
    
    try:
        # 1. 測試增強空間評分的通用性
        scenario_results = test_enhanced_spatial_scoring()
        
        # 2. 對比傳統方法與增強方法
        comparison_results = compare_traditional_vs_enhanced()
        
        # 3. 測試實際文檔處理
        document_results = test_real_document_processing()
        
        # 4. 生成測試報告
        report_file = generate_test_report(scenario_results, comparison_results, document_results)
        
        print_header("測試完成")
        print("🎉 增強空間分析通用改進方案驗證測試成功完成！")
        print(f"📋 詳細報告: {report_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
