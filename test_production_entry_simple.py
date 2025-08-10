#!/usr/bin/env python
"""
生產入口端到端測試 - 純調用模式

這個測試腳本直接調用 DocumentProcessor 的生產代碼，
不包含任何業務邏輯實現，只負責驗證主入口的功能。
"""

import sys
import os
import time
import asyncio
from pathlib import Path

# 添加src目錄到路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.main import DocumentProcessor
from src.config.logging_config import get_logger

logger = get_logger(__name__)


def test_production_entry():
    """測試生產入口的完整處理流程"""
    
    # 測試配置
    test_file = "tests/fixtures/documents/Workflows-sample.pdf"
    output_dir = "data/output"
    
    print("🧪 **生產入口端到端測試開始**")
    print(f"📄 測試文件: {test_file}")
    print(f"📁 輸出目錄: {output_dir}")
    print("-" * 60)
    
    start_time = time.time()
    steps = []
    
    try:
        # Step 1: 初始化DocumentProcessor
        print("🔧 Step 1: 初始化DocumentProcessor...")
        step_start = time.time()
        processor = DocumentProcessor()
        step_time = time.time() - step_start
        steps.append(("processor_initialization", True, step_time))
        print(f"✅ DocumentProcessor初始化完成 ({step_time:.2f}s)")
        
        # Step 2: 檢查測試文件是否存在
        print("📋 Step 2: 檢查測試文件...")
        step_start = time.time()
        if not os.path.exists(test_file):
            raise FileNotFoundError(f"測試文件不存在: {test_file}")
        file_size = os.path.getsize(test_file) / (1024 * 1024)  # MB
        step_time = time.time() - step_start
        steps.append(("file_validation", True, step_time))
        print(f"✅ 測試文件驗證通過 - 大小: {file_size:.1f}MB ({step_time:.2f}s)")
        
        # Step 3: 執行完整文檔處理
        print("🚀 Step 3: 執行文檔處理...")
        step_start = time.time()
        result = processor.process_document(
            file_path=test_file,
            output_dir=output_dir,
            template_name="enhanced.md.j2",
            save_associations=True
        )
        step_time = time.time() - step_start
        
        if not result["success"]:
            raise Exception(f"文檔處理失敗: {result.get('error', 'Unknown error')}")
        
        steps.append(("document_processing", True, step_time))
        print(f"✅ 文檔處理完成 ({step_time:.2f}s)")
        
        # Step 4: 驗證輸出文件
        print("📊 Step 4: 驗證輸出文件...")
        step_start = time.time()
        output_files = result["output_files"]
        
        # 檢查Markdown文件
        if "markdown" not in output_files:
            raise Exception("缺少Markdown輸出文件")
        
        markdown_path = output_files["markdown"]
        if not os.path.exists(markdown_path):
            raise Exception(f"Markdown文件不存在: {markdown_path}")
        
        markdown_size = os.path.getsize(markdown_path) / 1024  # KB
        
        # 檢查關聯文件
        if "associations" not in output_files:
            raise Exception("缺少關聯分析輸出文件")
        
        associations_path = output_files["associations"]
        if not os.path.exists(associations_path):
            raise Exception(f"關聯文件不存在: {associations_path}")
        
        step_time = time.time() - step_start
        steps.append(("output_validation", True, step_time))
        print(f"✅ 輸出文件驗證通過 - Markdown: {markdown_size:.1f}KB ({step_time:.2f}s)")
        
        # Step 5: 驗證統計信息
        print("📈 Step 5: 驗證統計信息...")
        step_start = time.time()
        stats = result["statistics"]
        
        required_stats = [
            "processing_time", "total_text_blocks", "total_images", 
            "total_associations", "high_quality_associations"
        ]
        
        for stat in required_stats:
            if stat not in stats:
                raise Exception(f"缺少統計信息: {stat}")
        
        step_time = time.time() - step_start
        steps.append(("statistics_validation", True, step_time))
        print(f"✅ 統計信息驗證通過 ({step_time:.2f}s)")
        
        # 測試成功總結
        total_time = time.time() - start_time
        success_count = len([s for s in steps if s[1]])
        
        print("-" * 60)
        print("🎉 **測試成功完成！**")
        print(f"📊 **測試統計**:")
        print(f"  - 總耗時: {total_time:.2f}秒")
        print(f"  - 步驟數: {len(steps)}")
        print(f"  - 成功率: {success_count}/{len(steps)} (100%)")
        
        print(f"\n📋 **處理統計**:")
        print(f"  - 處理時間: {stats['processing_time']:.2f}秒")
        print(f"  - 文本塊數: {stats['total_text_blocks']}")
        print(f"  - 圖片數: {stats['total_images']}")
        print(f"  - 關聯關係: {stats['total_associations']}")
        print(f"  - 高質量關聯: {stats['high_quality_associations']}")
        
        print(f"\n📁 **輸出文件**:")
        for file_type, file_path in output_files.items():
            file_size = os.path.getsize(file_path) / 1024 if os.path.exists(file_path) else 0
            print(f"  - {file_type}: {file_path} ({file_size:.1f}KB)")
        
        return True
        
    except Exception as e:
        error_time = time.time() - start_time
        failed_steps = len([s for s in steps if not s[1]])
        total_steps = len(steps) + 1  # +1 for the failed step
        
        print("-" * 60)
        print("❌ **測試失敗！**")
        print(f"💥 錯誤: {e}")
        print(f"📊 **測試統計**:")
        print(f"  - 失敗時間: {error_time:.2f}秒")
        print(f"  - 完成步驟: {len(steps)}/{total_steps}")
        print(f"  - 成功率: {len(steps)}/{total_steps} ({len(steps)/total_steps*100:.0f}%)")
        
        # 顯示詳細步驟信息
        print(f"\n📋 **步驟詳情**:")
        for i, (step_name, success, step_time) in enumerate(steps, 1):
            status = "✅" if success else "❌"
            print(f"  {i}. {step_name}: {status} ({step_time:.2f}s)")
        
        return False


def generate_test_report(success: bool):
    """生成測試報告"""
    
    report_path = "data/output/production_entry_test_report.md"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    report_content = f"""# 生產入口端到端測試報告

**測試時間**: {timestamp}  
**測試結果**: {"✅ 成功" if success else "❌ 失敗"}  
**測試模式**: 純調用模式（不包含業務邏輯）

## 測試目的

驗證 `DocumentProcessor` 主入口的完整處理流程，確保：
1. 系統能正確初始化
2. 文檔處理流程完整無誤
3. 輸出文件生成正確
4. 統計信息完整可靠

## 測試結果

{'測試通過，系統運行正常。' if success else '測試失敗，需要檢查系統配置和依賴。'}

## 建議

- {"系統已就緒，可以進行生產部署。" if success else "修復上述問題後重新測試。"}
- 定期運行此測試以確保系統穩定性
- 可考慮將此測試集成到CI/CD流程中

---
*此報告由生產入口測試自動生成*
"""
    
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n📄 測試報告已保存: {report_path}")


if __name__ == "__main__":
    print("🚀 **智能文檔轉換系統 - 生產入口測試**")
    print("=" * 60)
    
    success = test_production_entry()
    generate_test_report(success)
    
    if success:
        print("\n🎯 **測試結論**: 系統生產入口工作正常！")
        sys.exit(0)
    else:
        print("\n⚠️ **測試結論**: 系統需要修復後再次測試。")
        sys.exit(1)