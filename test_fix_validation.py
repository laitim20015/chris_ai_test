#!/usr/bin/env python3
"""
測試跨頁關聯修復效果
Test Cross-page Association Fix
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

import logging
from src.main import DocumentProcessor

# 設置日誌級別以捕獲我們添加的日誌
logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    print("🧪 測試跨頁關聯修復效果...")
    print("=" * 50)
    
    # 創建處理器
    processor = DocumentProcessor()
    
    # 處理文檔並捕獲日誌
    print("📄 開始處理文檔...")
    result = processor.process_document('tests/fixtures/documents/Workflows-sample.pdf')
    
    print(f"\n📊 處理結果:")
    print(f"   • 結果類型: {type(result)}")
    
    if isinstance(result, dict):
        print(f"   • 結果鍵: {list(result.keys())}")
        
        if 'associations' in result:
            associations = result['associations']
            print(f"   • 關聯總數: {len(associations)}")
            
            # 分析第7頁圖片的關聯情況
            p007_associations = []
            for assoc in associations:
                # 檢查是否關聯到第7頁的圖片
                image_id = assoc.get('image_id', '')
                if 'p007' in image_id or 'vector_007' in image_id:
                    p007_associations.append(assoc)
            
            print(f"\n🔍 第7頁圖片關聯分析:")
            print(f"   • 第7頁圖片的關聯數量: {len(p007_associations)}")
            
            if p007_associations:
                print(f"   • 關聯詳情:")
                for i, assoc in enumerate(p007_associations, 1):
                    text_id = assoc.get('text_id', 'Unknown')
                    final_score = assoc.get('final_score', 0)
                    print(f"     {i}. 文本ID: {text_id}, 關聯度: {final_score:.3f}")
            
            # 檢查具體的問題段落是否還在關聯列表中
            problem_text_ids = ['p46', 'p50', 'p88']  # 對應段落46, 50, 88
            
            print(f"\n🎯 問題段落關聯檢查:")
            for text_id in problem_text_ids:
                found = False
                for assoc in p007_associations:
                    if assoc.get('text_id') == text_id:
                        found = True
                        print(f"   ❌ {text_id} 仍然錯誤關聯到第7頁圖片 (分數: {assoc.get('final_score', 0):.3f})")
                        break
                
                if not found:
                    print(f"   ✅ {text_id} 不再關聯到第7頁圖片")
    
    print(f"\n" + "=" * 50)
    print(f"🧪 修復效果測試完成")

if __name__ == "__main__":
    main()
