#!/usr/bin/env python3
"""
文檔處理調試腳本
Document Processing Debug Script

調試Workflows-sample.pdf的處理過程，找出問題所在
"""

import sys
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent))

def debug_document_processing():
    """調試文檔處理過程"""
    
    test_file = r"C:\AP_Project_RAG\tests\fixtures\documents\Workflows-sample.pdf"
    
    print("🔍 文檔處理調試")
    print("=" * 50)
    print(f"文件: {test_file}")
    print(f"文件大小: {Path(test_file).stat().st_size} bytes")
    
    try:
        # 1. 測試解析器工廠
        print("\n📋 測試解析器工廠...")
        
        # 手動初始化解析器
        from src.parsers.parser_factory import initialize_default_parsers, get_parser_for_file
        
        print("  初始化默認解析器...")
        initialize_default_parsers()
        
        parser = get_parser_for_file(test_file)
        print(f"  選擇的解析器: {type(parser).__name__}")
        
        # 2. 測試解析過程
        print("\n⚙️  測試文檔解析...")
        try:
            parsed_content = parser.parse(test_file)
            print(f"  解析成功！")
            print(f"  文本塊數量: {len(parsed_content.text_blocks)}")
            print(f"  圖片數量: {len(parsed_content.images)}")
            
            # 顯示前3個文本塊
            if parsed_content.text_blocks:
                print("\n📝 文本塊樣本:")
                for i, block in enumerate(parsed_content.text_blocks[:3]):
                    print(f"    文本塊 {i+1}: {block.content[:100]}...")
            
            # 顯示圖片信息
            if parsed_content.images:
                print("\n🖼️  圖片樣本:")
                for i, img in enumerate(parsed_content.images[:3]):
                    print(f"    圖片 {i+1}: {img.id}, 尺寸: {img.width}x{img.height}")
            
        except Exception as e:
            print(f"  ❌ 解析失敗: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 3. 測試關聯分析（如果有內容）
        if parsed_content.text_blocks and parsed_content.images:
            print("\n🔗 測試關聯分析...")
            from src.main import DocumentProcessor
            processor = DocumentProcessor()
            
            # 測試單個關聯
            text_block = parsed_content.text_blocks[0]
            image = parsed_content.images[0]
            
            try:
                association = processor._perform_association_analysis(text_block, image, parsed_content)
                print(f"  關聯分析成功！")
                print(f"    最終分數: {association['final_score']:.3f}")
                print(f"    Caption分數: {association['caption_score']:.3f}")
                print(f"    空間分數: {association['spatial_score']:.3f}")
                print(f"    語義分數: {association['semantic_score']:.3f}")
            except Exception as e:
                print(f"  ❌ 關聯分析失敗: {e}")
                import traceback
                traceback.print_exc()
        
        # 4. 測試主處理流程
        print("\n🚀 測試主處理流程...")
        from src.main import DocumentProcessor
        processor = DocumentProcessor()
        
        try:
            result = processor.process_document(test_file)
            print(f"  主流程成功！")
            print(f"    返回結果類型: {type(result)}")
            print(f"    結果鍵: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            
            # 檢查結果內容
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, list):
                        print(f"    {key}: {len(value)} 項")
                    elif isinstance(value, str):
                        print(f"    {key}: {len(value)} 字符")
                    else:
                        print(f"    {key}: {type(value)}")
            
        except Exception as e:
            print(f"  ❌ 主流程失敗: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ 調試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_document_processing()
