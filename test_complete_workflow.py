#!/usr/bin/env python3
"""
完整工作流測試
Complete Workflow Test

使用Workflows-sample.pdf進行完整的端到端測試，驗證修復後的系統功能
"""

import sys
import os
import time
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent))

from src.main import DocumentProcessor

def test_complete_workflow():
    """測試完整的文檔處理工作流"""
    
    # 測試文件路徑
    test_file = r"C:\AP_Project_RAG\tests\fixtures\documents\Workflows-sample.pdf"
    
    print("🚀 開始完整工作流測試")
    print("=" * 60)
    print(f"測試文件: {test_file}")
    
    # 檢查文件是否存在
    if not Path(test_file).exists():
        print(f"❌ 測試文件不存在: {test_file}")
        return False
    
    try:
        # 初始化文檔處理器
        print("\n📋 初始化文檔處理器...")
        processor = DocumentProcessor()
        
        # 處理文檔
        print("⚙️  開始處理文檔...")
        start_time = time.time()
        
        result = processor.process_document(test_file)
        
        processing_time = time.time() - start_time
        
        print(f"✅ 文檔處理完成！耗時: {processing_time:.2f}秒")
        
        # 顯示處理結果統計
        print("\n📊 處理結果統計:")
        print("-" * 40)
        
        text_blocks = result.get('text_blocks', [])
        images = result.get('images', [])
        associations = result.get('associations', [])
        
        print(f"  📝 提取文本塊: {len(text_blocks)} 個")
        print(f"  🖼️  提取圖片: {len(images)} 個")
        print(f"  🔗 圖文關聯: {len(associations)} 個")
        
        # 顯示關聯分析詳情
        if associations:
            print(f"\n🎯 圖文關聯分析詳情:")
            print("-" * 40)
            
            # 顯示前5個關聯的詳細信息
            for i, assoc in enumerate(associations[:5], 1):
                print(f"  關聯 {i}:")
                print(f"    文本ID: {assoc.get('text_block_id', 'N/A')}")
                print(f"    圖片ID: {assoc.get('image_id', 'N/A')}")
                print(f"    最終分數: {assoc.get('final_score', 0):.3f}")
                print(f"    Caption分數: {assoc.get('caption_score', 0):.3f}")
                print(f"    空間分數: {assoc.get('spatial_score', 0):.3f}")
                print(f"    語義分數: {assoc.get('semantic_score', 0):.3f}")
                print(f"    關聯類型: {assoc.get('association_type', 'N/A')}")
                print()
        
        # 檢查輸出質量
        print("🔍 輸出質量檢查:")
        print("-" * 40)
        
        quality_checks = []
        
        # 檢查是否有文本提取
        if len(text_blocks) > 0:
            quality_checks.append("✅ 文本提取正常")
        else:
            quality_checks.append("❌ 未提取到文本")
        
        # 檢查是否有圖片提取
        if len(images) > 0:
            quality_checks.append("✅ 圖片提取正常")
        else:
            quality_checks.append("❌ 未提取到圖片")
        
        # 檢查是否有關聯分析
        if len(associations) > 0:
            quality_checks.append("✅ 關聯分析正常")
            
            # 檢查Caption檢測是否工作
            caption_working = any(assoc.get('caption_score', 0) > 0.5 for assoc in associations)
            if caption_working:
                quality_checks.append("✅ Caption檢測正常")
            else:
                quality_checks.append("⚠️  未檢測到明確的Caption")
            
            # 檢查分數分布是否合理
            scores = [assoc.get('final_score', 0) for assoc in associations]
            avg_score = sum(scores) / len(scores) if scores else 0
            if avg_score > 0.3:
                quality_checks.append("✅ 關聯分數合理")
            else:
                quality_checks.append("⚠️  關聯分數偏低")
        else:
            quality_checks.append("❌ 未進行關聯分析")
        
        for check in quality_checks:
            print(f"  {check}")
        
        # 檢查是否生成了Markdown輸出
        markdown_output = result.get('markdown_content', '')
        if markdown_output:
            print(f"\n📄 Markdown輸出:")
            print("-" * 40)
            print(f"  生成的Markdown長度: {len(markdown_output)} 字符")
            
            # 顯示前500字符作為預覽
            if len(markdown_output) > 500:
                preview = markdown_output[:500] + "..."
            else:
                preview = markdown_output
            
            print(f"  預覽:")
            print("  " + "─" * 38)
            for line in preview.split('\n')[:10]:  # 只顯示前10行
                print(f"  {line}")
            if len(markdown_output.split('\n')) > 10:
                print("  ...")
        
        print(f"\n🎉 完整工作流測試完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_workflow()
    sys.exit(0 if success else 1)
