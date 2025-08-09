"""
簡化的測試腳本 - 測試Phase 5的基本功能
"""

import sys
sys.path.append('.')

from src.markdown import MarkdownGenerator
from src.parsers.base import ParsedContent, TextBlock, ImageContent, DocumentMetadata

def test_markdown_generation():
    """測試Markdown生成器的基本功能"""
    print("🧪 測試Markdown生成器")
    
    # 創建測試數據
    metadata = DocumentMetadata(
        filename="test.pdf",
        file_path="./test.pdf",
        file_size=1024,
        file_format="pdf",
        page_count=1
    )
    
    text_blocks = [
        TextBlock(
            id="text_1",
            content="這是第一段文字。如圖1所示，系統架構包含多個模組。",
            page_number=1,
            bounding_box=(100, 100, 500, 150),
            font_size=12,
            font_family="Arial"
        ),
        TextBlock(
            id="text_2", 
            content="第二段描述了技術實現細節。下圖展示了處理流程。",
            page_number=1,
            bounding_box=(100, 200, 500, 250),
            font_size=12,
            font_family="Arial"
        )
    ]
    
    images = [
        ImageContent(
            id="img_1",
            filename="architecture.png",
            page_number=1,
            bounding_box=(100, 160, 400, 300),
            format="PNG",
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
    try:
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
        from src.association import AssociationScorer
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
        print(f"詳細信息: {details}")
        
        return True
        
    except Exception as e:
        print(f"❌ 關聯評分器測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 Phase 5 簡化功能測試")
    print("=" * 50)
    
    success_count = 0
    
    # 測試1: Markdown生成器
    if test_markdown_generation():
        success_count += 1
    
    # 測試2: 關聯評分器
    if test_association_scorer():
        success_count += 1
    
    # 總結
    print("\n" + "=" * 50)
    print(f"測試結果: {success_count}/2 通過")
    
    if success_count == 2:
        print("🎉 Phase 5 核心功能測試通過！")
        print("✅ Markdown生成器工作正常")
        print("✅ 關聯評分器工作正常")
        print("\n📋 下一步:")
        print("  1. Phase 5 已完成")
        print("  2. 可以開始Phase 3 (圖片處理) 或 Phase 6 (API)")
        print("  3. 最終會有完整的端到端測試")
    else:
        print("❌ 部分測試失敗，需要進一步調試")
    
    return success_count == 2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
