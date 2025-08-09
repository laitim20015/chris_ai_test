"""
核心功能測試腳本

用於測試智能文件轉換與RAG知識庫系統的完整功能流程。
使用Workflows-sample.pdf作為測試文件。
"""

import os
import sys
import time
from pathlib import Path

# 添加項目根目錄到Python路徑
sys.path.append(str(Path(__file__).parent))

from src.main import DocumentProcessor
from src.config.logging_config import get_logger
from src.utils.file_utils import ensure_directory_exists

logger = get_logger(__name__)


def test_core_functionality(test_file: str = "test-document.pdf"):
    """
    測試核心功能的完整流程
    
    Args:
        test_file: 測試文件名
    """
    
    print("🚀 智能文件轉換與RAG知識庫系統 - 核心功能測試")
    print("=" * 60)
    
    # 1. 檢查測試文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 測試文件不存在: {test_file}")
        print(f"請將 {test_file} 放置在項目根目錄中")
        return False
    
    print(f"✅ 測試文件已找到: {test_file}")
    
    # 2. 初始化處理器
    try:
        print("\n🔧 初始化文檔處理器...")
        processor = DocumentProcessor()
        print("✅ 文檔處理器初始化成功")
    except Exception as e:
        print(f"❌ 處理器初始化失敗: {e}")
        return False
    
    # 3. 執行文檔處理
    try:
        print(f"\n📄 開始處理文檔: {test_file}")
        print("⏳ 這可能需要幾十秒，請稍候...")
        
        start_time = time.time()
        
        result = processor.process_document(
            file_path=test_file,
            output_dir="./test_output",
            template_name="enhanced.md.j2",
            save_associations=True
        )
        
        processing_time = time.time() - start_time
        
        if result["success"]:
            print(f"✅ 文檔處理成功！耗時: {processing_time:.2f}秒")
            
            # 4. 顯示處理結果
            print("\n📊 處理統計信息:")
            stats = result["statistics"]
            print(f"  📝 文本塊數量: {stats['total_text_blocks']}")
            print(f"  🖼️ 圖片數量: {stats['total_images']}")
            print(f"  📋 表格數量: {stats['total_tables']}")
            print(f"  🔗 關聯關係數量: {stats['total_associations']}")
            print(f"  ⭐ 高質量關聯: {stats['high_quality_associations']}")
            print(f"  🎯 Caption關聯: {stats['caption_associations']}")
            print(f"  📊 平均關聯度: {stats['average_association_score']:.3f}")
            
            # 5. 顯示輸出文件
            print("\n📁 生成的文件:")
            for file_type, file_path in result["output_files"].items():
                print(f"  📄 {file_type}: {file_path}")
                
                # 檢查文件是否真的存在
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"      └─ 文件大小: {file_size} bytes")
                else:
                    print(f"      └─ ⚠️ 文件不存在")
            
            # 6. 顯示性能指標
            if "performance_metrics" in stats:
                print("\n⚡ 性能指標:")
                for metric, value in stats["performance_metrics"].items():
                    if isinstance(value, float):
                        print(f"  {metric}: {value:.3f}秒")
                    else:
                        print(f"  {metric}: {value}")
            
            return True
            
        else:
            print(f"❌ 文檔處理失敗: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ 處理過程出錯: {e}")
        logger.error(f"文檔處理異常: {e}", exc_info=True)
        return False


def test_individual_components():
    """測試各個組件的獨立功能"""
    
    print("\n🔍 組件獨立測試")
    print("-" * 40)
    
    # 測試解析器
    try:
        from src.parsers import ParserFactory
        factory = ParserFactory()
        print("✅ 解析器工廠初始化成功")
        
        pdf_parser = factory.get_parser(".pdf")
        if pdf_parser:
            print("✅ PDF解析器獲取成功")
        else:
            print("❌ PDF解析器獲取失敗")
    except Exception as e:
        print(f"❌ 解析器測試失敗: {e}")
    
    # 測試關聯分析器
    try:
        from src.association import AssociationScorer
        scorer = AssociationScorer()
        print("✅ 關聯分析器初始化成功")
        
        # 測試評分計算
        test_score, details = scorer.calculate_simple_score(
            caption_score=0.8,
            spatial_score=0.6,
            semantic_score=0.4,
            layout_score=0.3,
            proximity_score=0.2
        )
        print(f"✅ 測試評分計算: {test_score:.3f}")
        
    except Exception as e:
        print(f"❌ 關聯分析器測試失敗: {e}")
    
    # 測試Markdown生成器
    try:
        from src.markdown import MarkdownGenerator
        generator = MarkdownGenerator()
        print("✅ Markdown生成器初始化成功")
    except Exception as e:
        print(f"❌ Markdown生成器測試失敗: {e}")


def analyze_test_output():
    """分析測試輸出結果"""
    
    print("\n🔍 分析測試輸出")
    print("-" * 40)
    
    output_dir = Path("./test_output")
    
    if not output_dir.exists():
        print("❌ 輸出目錄不存在")
        return
    
    # 查找生成的文件
    markdown_files = list(output_dir.glob("*.md"))
    json_files = list(output_dir.glob("*_associations.json"))
    
    print(f"📄 找到 {len(markdown_files)} 個Markdown文件")
    print(f"📊 找到 {len(json_files)} 個關聯分析文件")
    
    # 分析Markdown文件
    if markdown_files:
        md_file = markdown_files[0]
        print(f"\n📝 分析Markdown文件: {md_file.name}")
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            print(f"  📏 總行數: {len(lines)}")
            
            # 計算各種Markdown元素
            headings = [line for line in lines if line.strip().startswith('#')]
            images = [line for line in lines if '![' in line and '](' in line]
            tables = [line for line in lines if '|' in line]
            
            print(f"  📋 標題數量: {len(headings)}")
            print(f"  🖼️ 圖片引用: {len(images)}")
            print(f"  📊 表格行數: {len(tables)}")
            
            # 顯示前幾個標題
            if headings:
                print("\n  📋 文檔結構:")
                for heading in headings[:5]:
                    level = len([c for c in heading if c == '#'])
                    indent = "  " * level
                    title = heading.strip('#').strip()
                    print(f"    {indent}└─ {title}")
                
                if len(headings) > 5:
                    print(f"    ... 還有 {len(headings) - 5} 個標題")
            
        except Exception as e:
            print(f"❌ 分析Markdown文件失敗: {e}")
    
    # 分析關聯分析文件
    if json_files:
        json_file = json_files[0]
        print(f"\n📊 分析關聯文件: {json_file.name}")
        
        try:
            import json
            with open(json_file, 'r', encoding='utf-8') as f:
                associations = json.load(f)
            
            print(f"  🔗 關聯關係總數: {len(associations)}")
            
            if associations:
                # 分析關聯質量
                high_quality = [a for a in associations if a.get('final_score', 0) >= 0.7]
                medium_quality = [a for a in associations if 0.4 <= a.get('final_score', 0) < 0.7]
                low_quality = [a for a in associations if a.get('final_score', 0) < 0.4]
                
                print(f"  ⭐ 高質量關聯 (≥0.7): {len(high_quality)}")
                print(f"  🟡 中等質量關聯 (0.4-0.7): {len(medium_quality)}")
                print(f"  🔴 低質量關聯 (<0.4): {len(low_quality)}")
                
                # 顯示最高分的關聯
                if associations:
                    best_association = max(associations, key=lambda x: x.get('final_score', 0))
                    print(f"\n  🏆 最佳關聯:")
                    print(f"    文本塊: {best_association.get('text_block_id', 'N/A')}")
                    print(f"    圖片: {best_association.get('image_id', 'N/A')}")
                    print(f"    關聯度: {best_association.get('final_score', 0):.3f}")
                    print(f"    類型: {best_association.get('association_type', 'unknown')}")
                
        except Exception as e:
            print(f"❌ 分析關聯文件失敗: {e}")


def main():
    """主測試函數"""
    
    print("🧪 開始核心功能測試")
    print("時間:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # 1. 測試各個組件
    test_individual_components()
    
    # 2. 測試完整流程
    success = test_core_functionality()
    
    # 3. 分析結果
    if success:
        analyze_test_output()
    
    # 4. 總結
    print("\n" + "=" * 60)
    if success:
        print("🎉 測試完成！所有核心功能正常工作")
        print("\n📋 下一步建議:")
        print("  1. 檢查生成的Markdown文件質量")
        print("  2. 驗證圖文關聯的準確性")
        print("  3. 調整關聯算法參數（如需要）")
        print("  4. 準備更多測試文件")
    else:
        print("❌ 測試失敗，請檢查上述錯誤信息")
        print("\n🔧 故障排除建議:")
        print("  1. 確認所有依賴包已安裝")
        print("  2. 檢查測試文件是否存在")
        print("  3. 查看詳細錯誤日誌")
        print("  4. 驗證配置文件設置")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
