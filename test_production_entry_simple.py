#!/usr/bin/env python3
"""
簡化的生產入口測試
Simplified Production Entry Test

直接測試DocumentProcessor.process_document()功能
"""

import sys
import os
from pathlib import Path

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.main import DocumentProcessor
    from src.config.logging_config import get_logger
    
    logger = get_logger("test_production_entry")
    
    def test_document_processor():
        """測試DocumentProcessor基本功能"""
        
        print("🚀 開始測試DocumentProcessor生產入口...")
        
        # 1. 初始化DocumentProcessor
        try:
            processor = DocumentProcessor()
            print("✅ DocumentProcessor初始化成功")
        except Exception as e:
            print(f"❌ DocumentProcessor初始化失敗: {e}")
            return False
        
        # 2. 檢查測試文件
        test_file = Path("tests/fixtures/documents/Workflows-sample.pdf")
        if not test_file.exists():
            print(f"❌ 測試文件不存在: {test_file}")
            return False
        print(f"✅ 測試文件確認: {test_file}")
        
        # 3. 設置輸出目錄
        output_dir = Path("test_output/production_entry_test")
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 輸出目錄: {output_dir}")
        
        # 4. 執行文檔處理
        try:
            print("🔄 開始處理文檔...")
            result = processor.process_document(
                file_path=str(test_file),
                output_dir=str(output_dir),
                template_name="enhanced.md.j2",
                save_associations=True
            )
            
            # 5. 檢查結果
            if not isinstance(result, dict):
                print(f"❌ 返回結果格式錯誤: {type(result)}")
                return False
            
            if not result.get("success", False):
                error_msg = result.get("error", "Unknown error")
                print(f"❌ 處理失敗: {error_msg}")
                return False
            
            print("✅ 文檔處理成功!")
            
            # 6. 驗證輸出
            output_files = result.get("output_files", {})
            stats = result.get("statistics", {})
            
            print(f"📊 處理統計:")
            print(f"  - 處理時間: {stats.get('processing_time', 'N/A')}秒")
            print(f"  - 文本塊: {stats.get('total_text_blocks', 'N/A')}")
            print(f"  - 圖片: {stats.get('total_images', 'N/A')}")
            print(f"  - 關聯: {stats.get('total_associations', 'N/A')}")
            
            # 7. 檢查輸出文件
            if "markdown" in output_files:
                markdown_file = Path(output_files["markdown"])
                if markdown_file.exists():
                    print(f"✅ Markdown文件創建成功: {markdown_file}")
                else:
                    print(f"❌ Markdown文件未創建: {markdown_file}")
                    return False
            
            if "associations" in output_files:
                associations_file = Path(output_files["associations"])
                if associations_file.exists():
                    print(f"✅ 關聯文件創建成功: {associations_file}")
                else:
                    print(f"❌ 關聯文件未創建: {associations_file}")
                    return False
            
            print("🎉 所有測試通過！生產入口正常工作！")
            return True
            
        except Exception as e:
            print(f"❌ 處理過程中發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    if __name__ == "__main__":
        success = test_document_processor()
        exit(0 if success else 1)
        
except ImportError as e:
    print(f"❌ 導入錯誤: {e}")
    print("請確保在項目根目錄運行此腳本")
    exit(1)
