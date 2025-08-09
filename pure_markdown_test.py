"""
純Markdown測試 - 避免解析器導入問題
"""

import sys
sys.path.append('.')

def test_markdown_generation():
    """測試Markdown生成器的基本功能"""
    print("🧪 測試Markdown生成器")
    
    try:
        # 直接導入Markdown相關模組
        from src.markdown.generator import MarkdownGenerator
        from src.parsers.base import ParsedContent, TextBlock, ImageContent, DocumentMetadata
        
        # 創建測試數據
        metadata = DocumentMetadata(
            filename="test.pdf",
            file_path="./test.pdf",
            file_size=1024,
            file_format="pdf",
            page_count=1
        )
        
        from src.association.allen_logic import BoundingBox
        from src.parsers.base import ContentType
        
        text_blocks = [
            TextBlock(
                id="text_1",
                content="這是第一段文字。如圖1所示，系統架構包含多個模組。",
                content_type=ContentType.PARAGRAPH,
                page_number=1,
                bbox=BoundingBox(100, 100, 500, 150),
                font_size=12,
                font_name="Arial"
            ),
            TextBlock(
                id="text_2", 
                content="第二段描述了技術實現細節。下圖展示了處理流程。",
                content_type=ContentType.PARAGRAPH,
                page_number=1,
                bbox=BoundingBox(100, 200, 500, 250),
                font_size=12,
                font_name="Arial"
            )
        ]
        
        from src.parsers.base import ImageFormat
        
        images = [
            ImageContent(
                id="img_1",
                filename="architecture.png",
                format=ImageFormat.PNG,
                data=b'',  # 空的測試數據
                page_number=1,
                bbox=BoundingBox(100, 160, 400, 300),
                width=300,
                height=140,
                alt_text="系統架構圖"
            )
        ]
        
        parsed_content = ParsedContent(
            text_blocks=text_blocks,
            images=images,
            tables=[],
            metadata=metadata
        )
        
        # 創建測試關聯數據
        associations = [
            {
                "text_block_id": "text_1",
                "image_id": "img_1", 
                "final_score": 0.85,
                "caption_score": 0.9,
                "spatial_score": 0.8,
                "semantic_score": 0.7,
                "layout_score": 0.6,
                "proximity_score": 0.5,
                "spatial_relation": "below",
                "association_type": "caption"
            }
        ]
        
        # 測試Markdown生成
        generator = MarkdownGenerator()
        print("✅ Markdown生成器初始化成功")
        
        # 生成簡化版本
        simple_markdown = generator.generate_simple_markdown(parsed_content, associations)
        print("✅ 簡化Markdown生成成功")
        
        # 保存結果
        with open("test_output_simple.md", "w", encoding="utf-8") as f:
            f.write(simple_markdown)
        print("✅ Markdown文件已保存: test_output_simple.md")
        
        # 顯示部分內容
        print("\n📄 生成的Markdown內容（前500字符）:")
        print("-" * 50)
        print(simple_markdown[:500])
        print("-" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_association_scorer():
    """測試關聯評分器"""
    print("\n🧪 測試關聯評分器")
    
    try:
        from src.association.association_scorer import AssociationScorer
        scorer = AssociationScorer()
        print("✅ 關聯評分器初始化成功")
        
        # 測試評分計算
        score, details = scorer.calculate_simple_score(
            caption_score=0.8,
            spatial_score=0.6,
            semantic_score=0.4,
            layout_score=0.3,
            proximity_score=0.2
        )
        
        print(f"✅ 評分計算成功: {score:.3f}")
        print(f"權重驗證: Caption={details['weights']['caption']} (應為最高)")
        
        return True
        
    except Exception as e:
        print(f"❌ 關聯評分器測試失敗: {e}")
        return False

def test_markdown_formatter():
    """測試Markdown格式化器"""
    print("\n🧪 測試Markdown格式化器")
    
    try:
        from src.markdown.formatter import MarkdownFormatter
        formatter = MarkdownFormatter()
        print("✅ Markdown格式化器初始化成功")
        
        # 測試基本格式化
        test_content = """# 測試標題

這是一段測試文字。

![圖片](./test.jpg)

## 子標題

更多內容...
"""
        
        formatted = formatter.format_content(test_content)
        print("✅ 內容格式化成功")
        
        # 測試URL驗證
        urls = formatter.url_embedder.validate_urls(formatted)
        print(f"✅ URL驗證完成，發現 {len(urls)} 個無效URL")
        
        return True
        
    except Exception as e:
        print(f"❌ 格式化器測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 Phase 5 純Markdown功能測試")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # 測試1: Markdown生成器
    if test_markdown_generation():
        success_count += 1
    
    # 測試2: 關聯評分器
    if test_association_scorer():
        success_count += 1
    
    # 測試3: Markdown格式化器
    if test_markdown_formatter():
        success_count += 1
    
    # 總結
    print("\n" + "=" * 50)
    print(f"測試結果: {success_count}/{total_tests} 通過")
    
    if success_count == total_tests:
        print("🎉 Phase 5 核心功能全部測試通過！")
        print("✅ Markdown生成器工作正常")
        print("✅ 關聯評分器工作正常")
        print("✅ Markdown格式化器工作正常")
        print("\n📋 Phase 5 完成狀態:")
        print("  ✅ 5.1 實現Markdown生成器和模板系統")
        print("  ✅ 5.2 實現格式化工具和URL嵌入")
        print("  ✅ 5.3 Phase 5 完成後的檢查和分析")
        print("\n🎯 下一步建議:")
        print("  1. ✅ Phase 5 已完成")
        print("  2. 開始 Phase 3 (圖片處理) 或 Phase 6 (API)")
        print("  3. 解決解析器註冊問題（獨立任務）")
        print("  4. 最終進行完整的端到端測試")
    else:
        print("❌ 部分測試失敗，需要進一步調試")
    
    return success_count == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
