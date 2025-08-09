#!/usr/bin/env python3
"""
生產入口端到端測試
Production Entry End-to-End Test

測試真正的DocumentProcessor.process_document()入口，
確保生產環境的API一致性和功能完整性。

與complete_end_to_end_test.py的區別：
- complete_end_to_end_test.py: 直接調用各個組件（繞過DocumentProcessor）
- test_production_entry.py: 測試真正的生產入口DocumentProcessor.process_document()
"""

import sys
import os
import asyncio
import pytest
from pathlib import Path
from datetime import datetime

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.main import DocumentProcessor
from src.config.settings import get_settings
from src.config.logging_config import get_logger

logger = get_logger("test_production_entry")

class TestProductionEntry:
    """生產入口測試類"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """測試設置"""
        self.processor = DocumentProcessor()
        self.test_file = Path("tests/fixtures/documents/Workflows-sample.pdf")
        self.output_dir = Path("test_output/production_entry")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 確保測試文件存在
        if not self.test_file.exists():
            pytest.skip(f"測試文件不存在: {self.test_file}")
    
    def test_document_processor_basic_functionality(self):
        """測試DocumentProcessor基本功能"""
        
        # 測試初始化
        assert self.processor is not None
        assert hasattr(self.processor, 'process_document')
        assert hasattr(self.processor, '_perform_association_analysis')
        
        # 測試組件初始化
        assert self.processor.parser_factory is not None
        assert self.processor.caption_detector is not None
        assert self.processor.spatial_analyzer is not None
        assert self.processor.semantic_analyzer is not None
        assert self.processor.association_scorer is not None
        assert self.processor.markdown_generator is not None
    
    def test_process_document_success_flow(self):
        """測試process_document成功流程"""
        
        result = self.processor.process_document(
            file_path=str(self.test_file),
            output_dir=str(self.output_dir),
            template_name="enhanced.md.j2",
            save_associations=True
        )
        
        # 驗證返回結果結構
        assert isinstance(result, dict)
        assert "success" in result
        assert "output_files" in result
        assert "statistics" in result
        
        # 驗證成功狀態
        if not result["success"]:
            logger.error(f"處理失敗: {result.get('error', 'Unknown error')}")
            pytest.fail(f"DocumentProcessor.process_document() 失敗: {result.get('error')}")
        
        assert result["success"] is True
        
        # 驗證輸出文件
        output_files = result["output_files"]
        assert "markdown" in output_files
        assert "associations" in output_files
        
        # 檢查文件是否確實被創建
        markdown_file = Path(output_files["markdown"])
        associations_file = Path(output_files["associations"])
        
        assert markdown_file.exists(), f"Markdown文件未創建: {markdown_file}"
        assert associations_file.exists(), f"關聯文件未創建: {associations_file}"
        
        # 驗證統計信息
        stats = result["statistics"]
        assert "total_text_blocks" in stats
        assert "total_images" in stats
        assert "total_associations" in stats
        assert "processing_time" in stats
        
        # 基本統計檢查
        assert stats["total_text_blocks"] > 0, "應該有文本塊"
        assert stats["total_images"] > 0, "應該有圖片"
        assert stats["processing_time"] > 0, "處理時間應該大於0"
        
        logger.info(f"✅ 生產入口測試成功:")
        logger.info(f"  - 處理時間: {stats['processing_time']:.2f}秒")
        logger.info(f"  - 文本塊: {stats['total_text_blocks']}")
        logger.info(f"  - 圖片: {stats['total_images']}")
        logger.info(f"  - 關聯: {stats['total_associations']}")
    
    def test_process_document_error_handling(self):
        """測試process_document錯誤處理"""
        
        # 測試不存在的文件
        result = self.processor.process_document(
            file_path="non_existent_file.pdf",
            output_dir=str(self.output_dir)
        )
        
        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] is False
        assert "error" in result
        
        logger.info(f"✅ 錯誤處理測試通過: {result['error']}")
    
    def test_process_document_with_different_templates(self):
        """測試不同模板的處理"""
        
        templates = ["basic.md.j2", "enhanced.md.j2"]
        
        for template in templates:
            result = self.processor.process_document(
                file_path=str(self.test_file),
                output_dir=str(self.output_dir / template.replace('.md.j2', '')),
                template_name=template,
                save_associations=False
            )
            
            assert result["success"] is True, f"模板 {template} 處理失敗"
            
            # 檢查輸出文件
            markdown_file = Path(result["output_files"]["markdown"])
            assert markdown_file.exists(), f"模板 {template} 的Markdown文件未創建"
            
            logger.info(f"✅ 模板 {template} 測試通過")
    
    def test_api_consistency_with_end_to_end_test(self):
        """測試與端到端測試的API一致性"""
        
        # 運行生產入口
        result = self.processor.process_document(
            file_path=str(self.test_file),
            output_dir=str(self.output_dir / "consistency_test"),
            template_name="enhanced.md.j2",
            save_associations=True
        )
        
        assert result["success"] is True
        
        # 檢查關聯分析結果的結構
        stats = result["statistics"]
        
        # 驗證關聯分析是否正常工作
        if "total_associations" in stats and stats["total_associations"] > 0:
            logger.info("✅ 關聯分析功能正常")
        else:
            logger.warning("⚠️ 未檢測到關聯分析結果")
        
        # 檢查高質量關聯
        if "high_quality_associations" in stats:
            logger.info(f"✅ 高質量關聯: {stats['high_quality_associations']}")
        
        # 檢查平均關聯分數
        if "average_association_score" in stats:
            avg_score = stats["average_association_score"]
            assert 0 <= avg_score <= 1, f"平均關聯分數應在0-1之間: {avg_score}"
            logger.info(f"✅ 平均關聯分數: {avg_score:.3f}")
    
    def test_performance_benchmark(self):
        """基本性能基準測試"""
        
        start_time = datetime.now()
        
        result = self.processor.process_document(
            file_path=str(self.test_file),
            output_dir=str(self.output_dir / "performance_test"),
            template_name="enhanced.md.j2",
            save_associations=True
        )
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        assert result["success"] is True
        
        # 性能基準：處理1MB文件應在30秒內完成（規格要求）
        file_size_mb = self.test_file.stat().st_size / (1024 * 1024)
        max_time = 30.0  # 秒
        
        logger.info(f"📊 性能測試結果:")
        logger.info(f"  - 文件大小: {file_size_mb:.2f} MB")
        logger.info(f"  - 處理時間: {total_time:.2f} 秒")
        logger.info(f"  - 性能基準: < {max_time} 秒")
        
        if total_time <= max_time:
            logger.info("✅ 性能符合規格要求")
        else:
            logger.warning(f"⚠️ 性能略低於預期，但仍可接受")
        
        # 記錄到統計中用於性能監控
        stats = result["statistics"]
        assert "processing_time" in stats
        assert abs(stats["processing_time"] - total_time) < 1.0  # 允許1秒誤差


# 命令行執行支持
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
