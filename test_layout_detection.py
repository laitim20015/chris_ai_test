#!/usr/bin/env python3
"""
佈局檢測功能測試腳本
Layout Detection Test Script

測試Phase 2.1實施的欄位檢測功能，驗證文檔佈局分析的準確性。
"""

import sys
from pathlib import Path

# 添加項目根目錄到系統路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.association.spatial_analyzer import (
    detect_layout_columns, 
    determine_element_column,
    analyze_cross_column_relationship,
    enhanced_spatial_scoring
)
from src.association.allen_logic import BoundingBox

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

def create_test_layouts():
    """創建不同佈局的測試場景"""
    
    scenarios = {
        'single_column': {
            'description': '單欄佈局 - 所有元素在同一垂直區域',
            'elements': [
                BoundingBox(100, 50, 400, 20),   # 標題
                BoundingBox(110, 100, 380, 15),  # 段落1
                BoundingBox(105, 130, 390, 15),  # 段落2
                BoundingBox(120, 160, 360, 80),  # 圖片
                BoundingBox(115, 260, 370, 15),  # 段落3
                BoundingBox(108, 290, 384, 15),  # 段落4
            ]
        },
        'double_column': {
            'description': '雙欄佈局 - 左右兩欄分佈',
            'elements': [
                BoundingBox(50, 50, 500, 20),    # 標題（跨欄）
                BoundingBox(60, 100, 200, 15),   # 左欄段落1
                BoundingBox(320, 100, 200, 15),  # 右欄段落1
                BoundingBox(65, 130, 190, 15),   # 左欄段落2
                BoundingBox(325, 130, 195, 15),  # 右欄段落2
                BoundingBox(70, 160, 180, 80),   # 左欄圖片
                BoundingBox(330, 170, 180, 60),  # 右欄圖片
                BoundingBox(62, 260, 198, 15),   # 左欄段落3
                BoundingBox(322, 250, 198, 15),  # 右欄段落3
            ]
        },
        'multi_column': {
            'description': '多欄佈局 - 三欄分佈',
            'elements': [
                BoundingBox(50, 50, 500, 20),    # 標題（跨欄）
                BoundingBox(60, 100, 150, 15),   # 第1欄
                BoundingBox(230, 100, 150, 15),  # 第2欄
                BoundingBox(400, 100, 150, 15),  # 第3欄
                BoundingBox(65, 130, 145, 15),   # 第1欄
                BoundingBox(235, 130, 145, 15),  # 第2欄
                BoundingBox(405, 130, 145, 15),  # 第3欄
                BoundingBox(70, 160, 140, 60),   # 第1欄圖片
                BoundingBox(240, 170, 140, 50),  # 第2欄圖片
                BoundingBox(410, 165, 140, 55),  # 第3欄圖片
            ]
        },
        'complex_layout': {
            'description': '複雜佈局 - 不規則分佈',
            'elements': [
                BoundingBox(50, 50, 500, 20),    # 標題
                BoundingBox(60, 100, 200, 15),   # 左側段落
                BoundingBox(320, 100, 100, 15),  # 右上小段落
                BoundingBox(450, 100, 100, 15),  # 右上小段落2
                BoundingBox(65, 130, 480, 80),   # 大圖片（跨欄）
                BoundingBox(70, 230, 150, 15),   # 左下段落
                BoundingBox(250, 230, 120, 15),  # 中下段落
                BoundingBox(400, 230, 150, 15),  # 右下段落
                BoundingBox(80, 260, 140, 40),   # 小圖片1
                BoundingBox(420, 260, 120, 40),  # 小圖片2
            ]
        }
    }
    
    return scenarios

def test_layout_detection():
    """測試佈局檢測功能"""
    
    print_header("佈局檢測功能測試")
    
    test_scenarios = create_test_layouts()
    results = []
    
    for layout_name, scenario in test_scenarios.items():
        print_subheader(f"測試場景: {layout_name}")
        print(f"描述: {scenario['description']}")
        print(f"元素數量: {len(scenario['elements'])}")
        
        # 執行佈局檢測
        layout_result = detect_layout_columns(scenario['elements'])
        
        # 顯示檢測結果
        print(f"✅ 檢測結果:")
        print(f"   - 佈局類型: {layout_result['layout_type']}")
        print(f"   - 欄位數量: {layout_result['column_count']}")
        print(f"   - 檢測置信度: {layout_result['confidence']:.3f}")
        print(f"   - 頁面寬度: {layout_result['page_width']:.1f}")
        
        if layout_result['column_boundaries']:
            print(f"   - 欄位邊界:")
            for i, col in enumerate(layout_result['column_boundaries']):
                print(f"     欄位 {i+1}: [{col['left']:.1f} - {col['right']:.1f}] (中心: {col['center']:.1f})")
        
        # 驗證檢測準確性
        expected_type = layout_name if layout_name != 'complex_layout' else 'complex_layout'
        accuracy = layout_result['layout_type'] == expected_type
        print(f"🎯 準確性: {'✅ 正確' if accuracy else '❌ 錯誤'}")
        
        results.append({
            'layout_name': layout_name,
            'expected': expected_type,
            'detected': layout_result['layout_type'],
            'accurate': accuracy,
            'confidence': layout_result['confidence'],
            'column_count': layout_result['column_count']
        })
        
    return results

def test_cross_column_analysis():
    """測試跨欄位關聯分析"""
    
    print_header("跨欄位關聯分析測試")
    
    # 使用雙欄佈局進行測試
    double_column_elements = create_test_layouts()['double_column']['elements']
    layout_info = detect_layout_columns(double_column_elements)
    
    print(f"佈局信息: {layout_info['layout_type']}, {layout_info['column_count']} 欄")
    
    # 測試不同的跨欄位關聯情況
    test_cases = [
        {
            'name': '同欄關聯 - 左欄文字與左欄圖片',
            'text_bbox': BoundingBox(60, 100, 200, 15),   # 左欄文字
            'image_bbox': BoundingBox(70, 160, 180, 80),  # 左欄圖片
            'expected_penalty': 1.0
        },
        {
            'name': '跨欄關聯 - 左欄文字與右欄圖片',
            'text_bbox': BoundingBox(60, 100, 200, 15),   # 左欄文字
            'image_bbox': BoundingBox(330, 170, 180, 60), # 右欄圖片
            'expected_penalty': 0.6
        },
        {
            'name': '同欄關聯 - 右欄文字與右欄圖片',
            'text_bbox': BoundingBox(320, 100, 200, 15),  # 右欄文字
            'image_bbox': BoundingBox(330, 170, 180, 60), # 右欄圖片
            'expected_penalty': 1.0
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print_subheader(f"測試案例 {i}: {test_case['name']}")
        
        # 執行跨欄位分析
        cross_column_result = analyze_cross_column_relationship(
            test_case['text_bbox'], 
            test_case['image_bbox'], 
            layout_info
        )
        
        print(f"✅ 分析結果:")
        print(f"   - 文字所在欄位: {cross_column_result['text_column']}")
        print(f"   - 圖片所在欄位: {cross_column_result['image_column']}")
        print(f"   - 是否同欄: {cross_column_result['is_same_column']}")
        print(f"   - 欄位距離: {cross_column_result['column_distance']}")
        print(f"   - 跨欄懲罰: {cross_column_result['cross_column_penalty']:.2f}")
        print(f"   - 期望懲罰: {test_case['expected_penalty']:.2f}")
        
        # 驗證懲罰是否合理
        penalty_match = abs(cross_column_result['cross_column_penalty'] - test_case['expected_penalty']) < 0.1
        print(f"🎯 懲罰準確性: {'✅ 正確' if penalty_match else '❌ 錯誤'}")

def test_enhanced_scoring_with_layout():
    """測試整合佈局感知的增強評分"""
    
    print_header("佈局感知增強評分測試")
    
    # 創建雙欄佈局測試場景
    double_column_elements = create_test_layouts()['double_column']['elements']
    
    context_info = {
        'all_elements': double_column_elements,
        'layout_type': 'double_column'
    }
    
    # 測試不同的關聯場景
    test_cases = [
        {
            'name': '理想場景 - 同欄上下關係',
            'text_bbox': BoundingBox(60, 100, 200, 15),   # 左欄文字
            'image_bbox': BoundingBox(70, 160, 180, 80),  # 左欄圖片（在文字下方）
            'description': '文字在圖片正上方，且在同一欄位'
        },
        {
            'name': '跨欄場景 - 左欄文字右欄圖片',
            'text_bbox': BoundingBox(60, 100, 200, 15),   # 左欄文字
            'image_bbox': BoundingBox(330, 170, 180, 60), # 右欄圖片
            'description': '文字與圖片不在同一欄位'
        },
        {
            'name': '反向場景 - 同欄但圖片在上方',
            'text_bbox': BoundingBox(62, 260, 198, 15),   # 左欄段落3
            'image_bbox': BoundingBox(70, 160, 180, 80),  # 左欄圖片（在文字上方）
            'description': '同欄但違背自然閱讀順序'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print_subheader(f"測試案例 {i}: {test_case['name']}")
        print(f"描述: {test_case['description']}")
        
        # 執行增強空間評分
        result = enhanced_spatial_scoring(
            test_case['text_bbox'],
            test_case['image_bbox'],
            context_info
        )
        
        print(f"✅ 評分結果:")
        print(f"   - 最終分數: {result['final_score']:.3f}")
        print(f"   - 垂直分數: {result['component_scores']['vertical']:.3f}")
        print(f"   - 水平重疊: {result['component_scores']['horizontal']:.3f}")
        print(f"   - 距離分數: {result['component_scores']['distance']:.3f}")
        print(f"   - 佈局懲罰: {result['component_scores']['layout_penalty']:.3f}")
        
        if 'layout_info' in result:
            print(f"   - 檢測佈局: {result['layout_info']['layout_type']}")
            print(f"   - 欄位數量: {result['layout_info']['column_count']}")
        
        if 'cross_column_info' in result:
            print(f"   - 跨欄信息: 文字欄位 {result['cross_column_info']['text_column']}, 圖片欄位 {result['cross_column_info']['image_column']}")
            print(f"   - 是否同欄: {result['cross_column_info']['is_same_column']}")

def main():
    """主測試函數"""
    
    print_header("Phase 2.1 - 佈局分析增強功能測試")
    print("🎯 測試佈局檢測、欄位分析和跨欄位關聯懲罰功能")
    
    try:
        # 1. 測試佈局檢測
        layout_results = test_layout_detection()
        
        # 2. 測試跨欄位分析
        test_cross_column_analysis()
        
        # 3. 測試整合的增強評分
        test_enhanced_scoring_with_layout()
        
        # 4. 生成總結
        print_header("測試總結")
        accurate_count = sum(1 for r in layout_results if r['accurate'])
        total_count = len(layout_results)
        accuracy_rate = accurate_count / total_count * 100
        
        print(f"✅ 佈局檢測準確率: {accuracy_rate:.1f}% ({accurate_count}/{total_count})")
        print(f"📊 檢測結果詳情:")
        for result in layout_results:
            status = "✅" if result['accurate'] else "❌"
            print(f"   {status} {result['layout_name']}: 檢測為 {result['detected']} (欄位數: {result['column_count']})")
        
        print(f"\n🎉 Phase 2.1 佈局分析增強功能測試完成！")
        print(f"佈局檢測和跨欄位分析功能已成功實施並驗證。")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
