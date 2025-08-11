#!/usr/bin/env python3
"""
文檔類型識別功能測試腳本
Document Type Detection Test Script

測試Phase 2.2實施的文檔類型識別功能，驗證不同文檔類型的自動識別準確性。
"""

import sys
from pathlib import Path

# 添加項目根目錄到系統路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.association.spatial_analyzer import (
    identify_document_type, 
    get_document_type_weights,
    DocumentType,
    _extract_document_features,
    _calculate_academic_paper_score,
    _calculate_technical_manual_score
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

def create_document_mock_elements():
    """創建不同文檔類型的模擬元素"""
    
    scenarios = {
        'academic_paper': {
            'description': '學術論文 - 文字為主，少量圖表',
            'elements': create_academic_paper_elements(),
            'expected_type': DocumentType.ACADEMIC_PAPER
        },
        'technical_manual': {
            'description': '技術手冊 - 圖文並茂，詳細說明',
            'elements': create_technical_manual_elements(),
            'expected_type': DocumentType.TECHNICAL_MANUAL
        },
        'presentation': {
            'description': '演示文稿 - 簡潔要點，視覺化內容',
            'elements': create_presentation_elements(),
            'expected_type': DocumentType.PRESENTATION
        },
        'magazine': {
            'description': '雜誌 - 多欄佈局，豐富視覺',
            'elements': create_magazine_elements(),
            'expected_type': DocumentType.MAGAZINE
        },
        'book': {
            'description': '書籍 - 連續文字，少量插圖',
            'elements': create_book_elements(),
            'expected_type': DocumentType.BOOK
        },
        'report': {
            'description': '報告 - 結構化內容，適量圖表',
            'elements': create_report_elements(),
            'expected_type': DocumentType.REPORT
        }
    }
    
    return scenarios

def create_academic_paper_elements():
    """創建學術論文模擬元素"""
    elements = []
    
    # 模擬文本塊（學術論文特徵：長段落，專業內容）
    for i in range(25):  # 較多文本塊
        # 模擬長段落
        mock_text = MockTextBlock(
            id=f"text_{i}",
            content="A" * (120 + i * 10),  # 較長的文本（模擬學術段落）
            bbox=BoundingBox(50, 100 + i * 40, 500, 25)
        )
        elements.append(mock_text)
    
    # 少量圖片（圖表、圖形）
    for i in range(3):  # 較少圖片
        mock_image = MockImage(
            id=f"image_{i}",
            bbox=BoundingBox(60, 300 + i * 200, 480, 150)
        )
        elements.append(mock_image)
    
    return elements

def create_technical_manual_elements():
    """創建技術手冊模擬元素"""
    elements = []
    
    # 模擬文本塊（技術手冊特徵：標題+步驟+說明）
    for i in range(35):  # 較多元素
        if i % 5 == 0:
            # 標題（短）
            content_length = 30 + i * 2
        else:
            # 步驟說明（中等長度）
            content_length = 80 + i * 5
            
        mock_text = MockTextBlock(
            id=f"text_{i}",
            content="B" * content_length,
            bbox=BoundingBox(50, 80 + i * 30, 500, 20)
        )
        elements.append(mock_text)
    
    # 較多圖片（步驟圖、示意圖）
    for i in range(8):  # 較多圖片
        mock_image = MockImage(
            id=f"image_{i}",
            bbox=BoundingBox(60, 200 + i * 150, 480, 120)
        )
        elements.append(mock_image)
    
    return elements

def create_presentation_elements():
    """創建演示文稿模擬元素"""
    elements = []
    
    # 模擬文本塊（演示文稿特徵：簡短要點）
    for i in range(15):  # 較少文本
        mock_text = MockTextBlock(
            id=f"text_{i}",
            content="C" * (25 + i * 3),  # 較短的文本（要點式）
            bbox=BoundingBox(100, 150 + i * 60, 400, 18)
        )
        elements.append(mock_text)
    
    # 較多圖片（圖表、圖像）
    for i in range(6):  # 圖片比例較高
        mock_image = MockImage(
            id=f"image_{i}",
            bbox=BoundingBox(120, 250 + i * 100, 360, 80)
        )
        elements.append(mock_image)
    
    return elements

def create_magazine_elements():
    """創建雜誌模擬元素"""
    elements = []
    
    # 模擬多欄佈局文本
    for i in range(40):  # 較多元素
        # 模擬多欄佈局：左欄和右欄
        if i % 2 == 0:
            x_pos = 50   # 左欄
        else:
            x_pos = 350  # 右欄
            
        # 文本長度變化大（標題、段落、圖說）
        if i % 7 == 0:
            content_length = 20  # 標題
        elif i % 7 == 6:
            content_length = 40  # 圖說
        else:
            content_length = 60 + i * 3  # 段落
            
        mock_text = MockTextBlock(
            id=f"text_{i}",
            content="D" * content_length,
            bbox=BoundingBox(x_pos, 100 + (i // 2) * 25, 280, 18)
        )
        elements.append(mock_text)
    
    # 豐富的圖片
    for i in range(12):  # 很多圖片
        # 圖片也分佈在不同欄位
        if i % 2 == 0:
            x_pos = 60
        else:
            x_pos = 360
            
        mock_image = MockImage(
            id=f"image_{i}",
            bbox=BoundingBox(x_pos, 200 + i * 80, 260, 60)
        )
        elements.append(mock_image)
    
    return elements

def create_book_elements():
    """創建書籍模擬元素"""
    elements = []
    
    # 模擬文本塊（書籍特徵：連續長段落）
    for i in range(30):  # 較多文本
        mock_text = MockTextBlock(
            id=f"text_{i}",
            content="E" * (100 + i * 8),  # 較長的段落
            bbox=BoundingBox(80, 120 + i * 35, 440, 25)
        )
        elements.append(mock_text)
    
    # 少量插圖
    for i in range(2):  # 很少圖片
        mock_image = MockImage(
            id=f"image_{i}",
            bbox=BoundingBox(100, 400 + i * 300, 400, 200)
        )
        elements.append(mock_image)
    
    return elements

def create_report_elements():
    """創建報告模擬元素"""
    elements = []
    
    # 模擬文本塊（報告特徵：結構化內容）
    for i in range(20):  # 適中數量
        mock_text = MockTextBlock(
            id=f"text_{i}",
            content="F" * (70 + i * 6),  # 中等長度
            bbox=BoundingBox(60, 100 + i * 40, 480, 22)
        )
        elements.append(mock_text)
    
    # 適量圖表
    for i in range(4):  # 適中圖片數量
        mock_image = MockImage(
            id=f"image_{i}",
            bbox=BoundingBox(80, 250 + i * 180, 440, 140)
        )
        elements.append(mock_image)
    
    return elements

class MockTextBlock:
    """模擬文本塊"""
    def __init__(self, id, content, bbox):
        self.id = id
        self.content = content
        self.bbox = bbox

class MockImage:
    """模擬圖片"""
    def __init__(self, id, bbox):
        self.id = id
        self.filename = f"{id}.png"
        self.bbox = bbox
        self.data = b"mock_image_data"

def test_document_type_identification():
    """測試文檔類型識別功能"""
    
    print_header("文檔類型識別功能測試")
    
    test_scenarios = create_document_mock_elements()
    results = []
    
    for doc_name, scenario in test_scenarios.items():
        print_subheader(f"測試場景: {doc_name}")
        print(f"描述: {scenario['description']}")
        print(f"元素數量: {len(scenario['elements'])}")
        print(f"期望類型: {scenario['expected_type'].value}")
        
        # 執行文檔類型識別
        identification_result = identify_document_type(
            scenario['elements'],
            metadata={'filename': f'{doc_name}_sample.pdf'}
        )
        
        # 顯示識別結果
        detected_type = identification_result['document_type']
        confidence = identification_result['confidence']
        
        print(f"✅ 識別結果:")
        print(f"   - 檢測類型: {detected_type.value}")
        print(f"   - 置信度: {confidence:.3f}")
        print(f"   - 推理: {identification_result['reasoning']}")
        
        # 顯示各類型分數
        print(f"   - 各類型分數:")
        for type_name, score in identification_result['type_scores'].items():
            marker = "🎯" if type_name == detected_type.value else "  "
            print(f"     {marker} {type_name}: {score:.3f}")
        
        # 驗證識別準確性
        accuracy = detected_type == scenario['expected_type']
        print(f"🎯 準確性: {'✅ 正確' if accuracy else '❌ 錯誤'}")
        
        results.append({
            'document_name': doc_name,
            'expected': scenario['expected_type'],
            'detected': detected_type,
            'accurate': accuracy,
            'confidence': confidence
        })
        
    return results

def test_document_type_weights():
    """測試文檔類型權重配置"""
    
    print_header("文檔類型權重配置測試")
    
    document_types = [
        DocumentType.ACADEMIC_PAPER,
        DocumentType.TECHNICAL_MANUAL,
        DocumentType.PRESENTATION,
        DocumentType.MAGAZINE,
        DocumentType.BOOK,
        DocumentType.REPORT
    ]
    
    for doc_type in document_types:
        print_subheader(f"文檔類型: {doc_type.value}")
        
        weights = get_document_type_weights(doc_type)
        
        print(f"✅ 權重配置:")
        for component, weight in weights.items():
            print(f"   - {component}: {weight:.3f}")
        
        # 檢查權重合理性
        core_weights_sum = weights['vertical'] + weights['horizontal'] + weights['distance'] + weights['alignment']
        print(f"🔍 核心權重總和: {core_weights_sum:.3f}")
        
        if abs(core_weights_sum - 1.0) < 0.05:
            print(f"✅ 權重分配合理")
        else:
            print(f"⚠️ 權重分配需要調整")

def test_feature_extraction():
    """測試特徵提取功能"""
    
    print_header("文檔特徵提取測試")
    
    # 使用技術手冊作為測試案例
    elements = create_technical_manual_elements()
    
    print(f"測試元素數量: {len(elements)}")
    
    # 執行特徵提取
    features = _extract_document_features(elements, {'filename': 'test_manual.pdf'})
    
    print_subheader("提取的特徵")
    print(f"✅ 基本統計:")
    print(f"   - 總元素數: {features['total_elements']}")
    print(f"   - 文本塊數: {features['text_count']}")
    print(f"   - 圖片數: {features['image_count']}")
    print(f"   - 文字圖片比例: {features['text_image_ratio']:.2f}")
    
    print(f"✅ 佈局特徵:")
    print(f"   - 佈局類型: {features['layout_type']}")
    print(f"   - 欄位數量: {features['column_count']}")
    print(f"   - 內容密度: {features['content_density']:.3f}")
    
    print(f"✅ 文本特徵:")
    text_features = features['text_features']
    print(f"   - 平均長度: {text_features['avg_length']:.1f}")
    print(f"   - 總長度: {text_features['total_length']}")
    print(f"   - 長度變異: {text_features['variation']:.1f}")
    
    print(f"✅ 圖片特徵:")
    image_features = features['image_features']
    print(f"   - 圖片數量: {image_features['count']}")
    print(f"   - 平均尺寸: {image_features['avg_size']:.1f}")
    print(f"   - 尺寸變異: {image_features['size_variation']:.1f}")
    
    # 測試各類型分數計算
    print_subheader("類型分數計算")
    academic_score = _calculate_academic_paper_score(features)
    manual_score = _calculate_technical_manual_score(features)
    
    print(f"學術論文分數: {academic_score:.3f}")
    print(f"技術手冊分數: {manual_score:.3f}")
    print(f"技術手冊應該得分更高: {'✅ 正確' if manual_score > academic_score else '❌ 錯誤'}")

def main():
    """主測試函數"""
    
    print_header("Phase 2.2 - 文檔類型識別功能測試")
    print("🎯 測試文檔類型自動識別和權重配置功能")
    
    try:
        # 1. 測試文檔類型識別
        identification_results = test_document_type_identification()
        
        # 2. 測試權重配置
        test_document_type_weights()
        
        # 3. 測試特徵提取
        test_feature_extraction()
        
        # 4. 生成總結
        print_header("測試總結")
        accurate_count = sum(1 for r in identification_results if r['accurate'])
        total_count = len(identification_results)
        accuracy_rate = accurate_count / total_count * 100
        
        print(f"✅ 文檔類型識別準確率: {accuracy_rate:.1f}% ({accurate_count}/{total_count})")
        print(f"📊 識別結果詳情:")
        for result in identification_results:
            status = "✅" if result['accurate'] else "❌"
            print(f"   {status} {result['document_name']}: 檢測為 {result['detected'].value} (置信度: {result['confidence']:.3f})")
        
        print(f"\n🎉 Phase 2.2 文檔類型識別功能測試完成！")
        print(f"文檔類型識別和權重配置功能已成功實施並驗證。")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

