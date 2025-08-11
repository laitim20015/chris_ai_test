#!/usr/bin/env python3
"""
快速測試腳本 - 跳過網絡依賴的模型下載
Quick Test Script - Skip network-dependent model downloading
"""

import sys
import os
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent))

# 設置離線模式，避免模型下載
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'

def test_basic_workflow():
    """測試基本工作流程，跳過可能的網絡依賴"""
    
    test_file = r"tests\fixtures\documents\Workflows-sample.pdf"
    
    print("🚀 快速工作流測試（離線模式）")
    print("=" * 60)
    print(f"測試文件: {test_file}")
    
    try:
        # 1. 測試解析器初始化
        print("\n📋 1. 測試解析器...")
        from src.parsers.parser_factory import initialize_default_parsers, get_parser_for_file
        
        initialize_default_parsers()
        parser = get_parser_for_file(test_file)
        print(f"   ✅ 解析器創建成功: {type(parser).__name__}")
        
        # 2. 測試文檔解析
        print("\n📄 2. 測試文檔解析...")
        parsed_content = parser.parse(test_file)
        print(f"   ✅ 解析成功:")
        print(f"      - 文本塊: {len(parsed_content.text_blocks)}")
        print(f"      - 圖片: {len(parsed_content.images)}")
        print(f"      - 表格: {len(parsed_content.tables)}")
        
        # 3. 測試關聯分析（使用備用方法）
        print("\n🎯 3. 測試關聯分析（備用方法）...")
        if parsed_content.text_blocks and parsed_content.images:
            from src.main import DocumentProcessor
            processor = DocumentProcessor()
            
            # 測試單個關聯
            text_block = parsed_content.text_blocks[0]
            image = parsed_content.images[0]
            
            association = processor._perform_association_analysis(text_block, image, parsed_content)
            
            print(f"   ✅ 關聯分析成功:")
            print(f"      - 最終分數: {association['final_score']:.3f}")
            print(f"      - Caption分數: {association['caption_score']:.3f}")
            print(f"      - 空間分數: {association['spatial_score']:.3f}")
            print(f"      - 語義分數: {association['semantic_score']:.3f}")
            print(f"      - 佈局分數: {association['layout_score']:.3f}")
            print(f"      - 距離分數: {association['proximity_score']:.3f}")
        else:
            print("   ⚠️ 沒有內容可供關聯分析")
        
        # 4. 測試Markdown生成
        print("\n📝 4. 測試Markdown生成...")
        from src.markdown.generator import MarkdownGenerator
        
        generator = MarkdownGenerator()
        markdown_content = generator.generate(
            parsed_content,
            [],  # 暫時不包含關聯
            template_name="basic.md.j2"
        )
        
        print(f"   ✅ Markdown生成成功:")
        print(f"      - 長度: {len(markdown_content)} 字符")
        lines_count = len(markdown_content.split('\n'))
        print(f"      - 行數: {lines_count}")
        
        # 保存結果
        output_file = Path("data/output/quick_test_result.md")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        print(f"      - 保存到: {output_file}")
        
        print("\n🎉 快速測試完成！所有基本功能正常工作。")
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_workflow()
    sys.exit(0 if success else 1)
