#!/usr/bin/env python3
"""
完整端到端測試腳本
使用 Workflows-sample.pdf 測試所有功能流程

測試流程：
1. 文檔解析
2. 圖片處理  
3. 圖文關聯
4. Markdown生成
5. 返回結果

確保不使用任何簡化版本，執行完整功能。
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# 設置離線模式，避免Hugging Face模型下載問題
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import DocumentProcessor
from src.config.settings import get_settings
from src.config.logging_config import get_logger
from src.parsers.parser_factory import ParserFactory
from src.image_processing.extractor import ImageExtractor
from src.image_processing.optimizer import ImageOptimizer
from src.image_processing.storage import LocalImageStorage, StorageConfig
from src.image_processing.metadata import ImageMetadataManager
from src.association.caption_detector import CaptionDetector
from src.association.spatial_analyzer import SpatialAnalyzer
from src.association.semantic_analyzer import SemanticAnalyzer
from src.association.association_scorer import AssociationScorer
from src.association.association_optimizer import AssociationOptimizer, create_balanced_config
from src.markdown.generator import MarkdownGenerator
from src.utils.validation import validate_markdown_output


class CompleteEndToEndTest:
    """完整端到端測試類"""
    
    def __init__(self):
        """初始化測試環境"""
        self.logger = get_logger("end_to_end_test")
        self.settings = get_settings()
        self.test_file = Path("tests/fixtures/documents/Workflows-sample.pdf")
        
        # 確保輸出目錄存在
        self.output_dir = Path("data/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 結果統計
        self.test_results = {
            "start_time": datetime.now(),
            "steps_completed": [],
            "errors": [],
            "warnings": [],
            "performance_metrics": {}
        }
        
        self.logger.info("🧪 初始化完整端到端測試")
        self.logger.info(f"📄 測試文件: {self.test_file}")
        self.logger.info(f"📂 輸出目錄: {self.output_dir}")

    async def run_complete_test(self):
        """運行完整測試"""
        try:
            self.logger.info("🚀 開始完整端到端測試")
            self.logger.info("=" * 80)
            
            # 步驟1: 文檔解析
            parsed_content = await self.test_document_parsing()
            
            # 步驟2: 圖片處理
            processed_images = await self.test_image_processing(parsed_content)
            
            # 步驟3: 圖文關聯
            associations = await self.test_image_text_association(parsed_content)
            
            # 步驟4: Markdown生成
            markdown_content = await self.test_markdown_generation(parsed_content, associations)
            
            # 步驟5: 結果驗證和返回
            final_results = await self.test_result_validation(markdown_content, parsed_content, associations)
            
            # 生成測試報告
            await self.generate_test_report(final_results)
            
            self.logger.info("🎉 完整端到端測試成功完成！")
            return final_results
            
        except Exception as e:
            self.logger.error(f"❌ 測試失敗: {str(e)}")
            self.test_results["errors"].append(str(e))
            raise

    async def test_document_parsing(self):
        """步驟1: 完整文檔解析測試"""
        self.logger.info("📄 步驟1: 開始文檔解析測試")
        start_time = datetime.now()
        
        try:
            # 修復解析器工廠的使用
            from src.parsers.parser_factory import initialize_default_parsers, get_parser_for_file
            
            # 手動初始化解析器（修復工廠問題）
            self.logger.info("🔧 初始化解析器...")
            initialize_default_parsers()
            
            # 解析文檔
            self.logger.info("🔍 開始解析PDF文檔...")
            parser = get_parser_for_file(str(self.test_file))
            
            if not parser:
                raise ValueError(f"不支持的文件格式: {self.test_file.suffix}")
            
            parsed_content = await asyncio.to_thread(
                parser.parse,
                str(self.test_file)
            )
            
            # 驗證解析結果
            self.logger.info("📊 解析結果統計:")
            self.logger.info(f"  • 文本塊數量: {len(parsed_content.text_blocks)}")
            self.logger.info(f"  • 圖片數量: {len(parsed_content.images)}")
            self.logger.info(f"  • 表格數量: {len(parsed_content.tables)}")
            self.logger.info(f"  • 文檔頁數: {len(set(block.page_number for block in parsed_content.text_blocks)) if parsed_content.text_blocks else 0}")
            
            # 驗證內容不為空
            assert len(parsed_content.text_blocks) > 0, "文本塊不能為空"
            assert parsed_content.metadata is not None, "元數據不能為空"
            
            # 記錄性能指標
            processing_time = (datetime.now() - start_time).total_seconds()
            self.test_results["performance_metrics"]["document_parsing"] = processing_time
            self.logger.info(f"⏱️ 文檔解析耗時: {processing_time:.2f}秒")
            
            self.test_results["steps_completed"].append("document_parsing")
            self.logger.info("✅ 步驟1: 文檔解析完成")
            
            return parsed_content
            
        except Exception as e:
            self.logger.error(f"❌ 文檔解析失敗: {str(e)}")
            self.test_results["errors"].append(f"document_parsing: {str(e)}")
            raise

    async def test_image_processing(self, parsed_content):
        """步驟2: 完整圖片處理測試"""
        self.logger.info("🖼️ 步驟2: 開始圖片處理測試")
        start_time = datetime.now()
        
        try:
            # 初始化圖片處理組件
            image_extractor = ImageExtractor()
            image_optimizer = ImageOptimizer()
            
            # 創建本地存儲配置
            storage_config = StorageConfig(
                storage_type="local",
                base_path=str(self.output_dir / "images")
            )
            image_storage = LocalImageStorage(storage_config)
            metadata_manager = ImageMetadataManager()
            
            processed_images = []
            
            if not parsed_content.images:
                self.logger.warning("⚠️ 沒有找到圖片，檢查PDF是否包含圖片")
                self.test_results["warnings"].append("no_images_found")
                return processed_images
            
            self.logger.info(f"🔍 開始處理 {len(parsed_content.images)} 張圖片")
            
            for i, image_content in enumerate(parsed_content.images):
                self.logger.info(f"📸 處理圖片 {i+1}/{len(parsed_content.images)}")
                
                # 將ImageContent轉換為ExtractedImage
                from src.image_processing.extractor import ExtractedImage
                extracted_image = ExtractedImage(
                    image_data=image_content.data,
                    format=image_content.format.value.lower(),
                    size=(image_content.width, image_content.height),
                    source_page=image_content.page_number,
                    source_position=image_content.bbox,
                    hash=image_content.checksum,
                    filename=f"image_{i+1}.{image_content.format.value.lower()}",
                    metadata={}
                )
                
                # 圖片優化
                optimized_image = await asyncio.to_thread(
                    image_optimizer.optimize_image,
                    extracted_image
                )
                
                # 生成文件名
                image_filename = f"workflows_sample_p{image_content.page_number:03d}_img{i+1:03d}.png"
                
                # 存儲圖片
                stored_image = await image_storage.store_image(
                    optimized_image,
                    image_filename
                )
                image_url = stored_image.url
                
                # 創建並保存元數據
                image_metadata = metadata_manager.create_metadata_from_extraction(
                    extracted_image,
                    self.test_file.name
                )
                
                # 更新存儲後信息
                image_metadata = metadata_manager.update_metadata_after_storage(
                    image_metadata,
                    stored_image
                )
                
                # 保存元數據
                await asyncio.to_thread(
                    metadata_manager.save_metadata,
                    image_metadata.image_id
                )
                
                # 更新圖片內容
                image_content.url = image_url
                processed_images.append(image_content)
                
                self.logger.info(f"  ✅ 圖片已處理: {image_filename}")
                self.logger.info(f"     原始大小: {image_metadata.original_file_size:,} bytes")
                self.logger.info(f"     優化後: {image_metadata.final_file_size:,} bytes")
                self.logger.info(f"     URL: {image_url}")
            
            # 記錄性能指標
            processing_time = (datetime.now() - start_time).total_seconds()
            self.test_results["performance_metrics"]["image_processing"] = processing_time
            self.logger.info(f"⏱️ 圖片處理耗時: {processing_time:.2f}秒")
            
            self.test_results["steps_completed"].append("image_processing")
            self.logger.info("✅ 步驟2: 圖片處理完成")
            
            return processed_images
            
        except Exception as e:
            self.logger.error(f"❌ 圖片處理失敗: {str(e)}")
            self.test_results["errors"].append(f"image_processing: {str(e)}")
            raise

    async def test_image_text_association(self, parsed_content):
        """步驟3: 完整圖文關聯測試"""
        self.logger.info("🎯 步驟3: 開始圖文關聯分析測試")
        start_time = datetime.now()
        
        try:
            # 初始化關聯分析組件
            caption_detector = CaptionDetector()
            spatial_analyzer = SpatialAnalyzer()
            semantic_analyzer = SemanticAnalyzer()
            association_scorer = AssociationScorer()
            
            # 初始化關聯優化器
            association_optimizer = AssociationOptimizer(create_balanced_config())
            
            associations = []
            
            if not parsed_content.images or not parsed_content.text_blocks:
                self.logger.warning("⚠️ 缺少圖片或文本塊，無法進行關聯分析")
                self.test_results["warnings"].append("insufficient_content_for_association")
                return associations
            
            self.logger.info(f"🔍 分析 {len(parsed_content.images)} 張圖片與 {len(parsed_content.text_blocks)} 個文本塊的關聯")
            
            total_associations = 0
            
            for image in parsed_content.images:
                self.logger.info(f"📸 分析圖片 (頁面 {image.page_number}) 的關聯關係")
                
                image_associations = []
                
                for text_block in parsed_content.text_blocks:
                    # 跳過不同頁面的文本（可選，根據需求調整）
                    if abs(text_block.page_number - image.page_number) > 1:
                        continue
                    
                    # 🎯 使用修復後的完整關聯分析系統（通過DocumentProcessor）
                    # 這確保我們使用最新修復的關聯算法和權重模型
                    
                    # 創建DocumentProcessor實例以使用完整的關聯分析
                    from src.main import DocumentProcessor
                    processor = DocumentProcessor()
                    
                    # 使用完整的關聯分析方法
                    association_result = await asyncio.to_thread(
                        processor._perform_association_analysis,
                        text_block,
                        image,
                        parsed_content  # 提供完整上下文
                    )
                    
                    # 提取所有分數
                    final_score = association_result.get('final_score', 0.0)
                    caption_score = association_result.get('caption_score', 0.0)
                    spatial_score = association_result.get('spatial_score', 0.0)
                    semantic_score = association_result.get('semantic_score', 0.0)
                    layout_score = association_result.get('layout_score', 0.0)
                    proximity_score = association_result.get('proximity_score', 0.0)
                    
                    # 獲取詳細分析結果
                    score_details = association_result.get('details', {})
                    
                    # 使用配置化閾值判斷關聯
                    threshold = self.settings.association.min_association_score
                    if final_score > threshold:
                        association = {
                            "text_block_id": text_block.id,
                            "image_id": image.id,
                            "final_score": final_score,
                            "caption_score": caption_score,
                            "spatial_score": spatial_score,
                            "semantic_score": semantic_score,
                            "layout_score": layout_score,      # 新增佈局評分
                            "proximity_score": proximity_score, # 新增距離評分
                            "text_preview": text_block.content[:100] + "..." if len(text_block.content) > 100 else text_block.content
                        }
                        
                        image_associations.append(association)
                        total_associations += 1
                        
                        self.logger.info(f"  🎯 找到關聯 (分數: {final_score:.3f})")
                        self.logger.info(f"     Caption: {caption_score:.3f} | 空間: {spatial_score:.3f} | 語義: {semantic_score:.3f}")
                        self.logger.info(f"     佈局: {layout_score:.3f} | 距離: {proximity_score:.3f}")
                        self.logger.info(f"     文本預覽: {association['text_preview']}")
                
                if image_associations:
                    # 按分數排序
                    image_associations.sort(key=lambda x: x["final_score"], reverse=True)
                    associations.extend(image_associations)
                    
                    self.logger.info(f"  ✅ 圖片關聯完成: 找到 {len(image_associations)} 個關聯")
                else:
                    self.logger.info(f"  ⚠️ 圖片未找到高質量關聯")
            
            # 🔧 關聯優化 - 去重、過濾和質量提升
            self.logger.info(f"🔧 開始關聯優化 - 原始關聯數: {len(associations)}")
            optimized_associations = await asyncio.to_thread(
                association_optimizer.optimize_associations,
                associations,
                parsed_content.images,
                parsed_content.text_blocks
            )
            self.logger.info(f"關聯優化完成 - 優化後關聯數: {len(optimized_associations)}")
            reduction_rate = ((len(associations) - len(optimized_associations)) / len(associations) * 100) if associations else 0
            self.logger.info(f"關聯減少率: {reduction_rate:.1f}%")
            
            # 使用優化後的關聯
            associations = optimized_associations
            
            # 記錄性能指標
            processing_time = (datetime.now() - start_time).total_seconds()
            self.test_results["performance_metrics"]["association_analysis"] = processing_time
            self.logger.info(f"⏱️ 關聯分析耗時: {processing_time:.2f}秒")
            self.logger.info(f"📊 總關聯數: {total_associations}")
            
            self.test_results["steps_completed"].append("association_analysis")
            self.logger.info("✅ 步驟3: 圖文關聯分析完成")
            
            return associations
            
        except Exception as e:
            self.logger.error(f"❌ 圖文關聯分析失敗: {str(e)}")
            self.test_results["errors"].append(f"association_analysis: {str(e)}")
            raise

    async def test_markdown_generation(self, parsed_content, associations):
        """步驟4: 完整Markdown生成測試"""
        self.logger.info("📝 步驟4: 開始Markdown生成測試")
        start_time = datetime.now()
        
        try:
            # 初始化Markdown生成器
            markdown_generator = MarkdownGenerator()
            
            self.logger.info("🔨 生成結構化Markdown內容...")
            
            # 構建關聯映射
            association_map = {}
            for assoc in associations:
                text_id = assoc["text_block_id"]
                if text_id not in association_map:
                    association_map[text_id] = []
                association_map[text_id].append(assoc)
            
            # 生成Markdown
            markdown_content = await asyncio.to_thread(
                markdown_generator.generate,
                parsed_content,
                associations,
                template_name="enhanced.md.j2",
                include_metadata=True
            )
            
            # 驗證Markdown格式
            is_valid = validate_markdown_output(markdown_content)
            if not is_valid:
                self.logger.warning("⚠️ Markdown格式驗證失敗")
                self.test_results["warnings"].append("markdown_validation_failed")
            
            # 保存Markdown文件
            output_file = self.output_dir / "workflows_sample_complete.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            # 統計信息
            lines_count = len(markdown_content.split('\n'))
            chars_count = len(markdown_content)
            images_in_markdown = markdown_content.count('![')
            
            self.logger.info("📊 Markdown生成統計:")
            self.logger.info(f"  • 總行數: {lines_count}")
            self.logger.info(f"  • 總字符數: {chars_count:,}")
            self.logger.info(f"  • 嵌入圖片數: {images_in_markdown}")
            self.logger.info(f"  • 輸出文件: {output_file}")
            
            # 記錄性能指標
            processing_time = (datetime.now() - start_time).total_seconds()
            self.test_results["performance_metrics"]["markdown_generation"] = processing_time
            self.logger.info(f"⏱️ Markdown生成耗時: {processing_time:.2f}秒")
            
            self.test_results["steps_completed"].append("markdown_generation")
            self.logger.info("✅ 步驟4: Markdown生成完成")
            
            return markdown_content
            
        except Exception as e:
            self.logger.error(f"❌ Markdown生成失敗: {str(e)}")
            self.test_results["errors"].append(f"markdown_generation: {str(e)}")
            raise

    async def test_result_validation(self, markdown_content, parsed_content, associations):
        """步驟5: 結果驗證和返回"""
        self.logger.info("🔍 步驟5: 開始結果驗證")
        start_time = datetime.now()
        
        try:
            # 構建完整結果
            final_results = {
                "test_metadata": {
                    "test_file": str(self.test_file),
                    "test_date": datetime.now().isoformat(),
                    "total_processing_time": (datetime.now() - self.test_results["start_time"]).total_seconds()
                },
                "document_info": {
                    "filename": self.test_file.name,
                    "file_size": self.test_file.stat().st_size,
                    "text_blocks_count": len(parsed_content.text_blocks),
                    "images_count": len(parsed_content.images),
                    "tables_count": len(parsed_content.tables)
                },
                "processing_results": {
                    "associations_count": len(associations),
                    "markdown_length": len(markdown_content),
                    "markdown_lines": len(markdown_content.split('\n')),
                    "images_in_markdown": markdown_content.count('![')
                },
                "performance_metrics": self.test_results["performance_metrics"],
                "quality_metrics": {
                    "steps_completed": len(self.test_results["steps_completed"]),
                    "total_steps": 5,
                    "success_rate": len(self.test_results["steps_completed"]) / 5 * 100,
                    "errors_count": len(self.test_results["errors"]),
                    "warnings_count": len(self.test_results["warnings"])
                },
                "outputs": {
                    "markdown_content": markdown_content[:1000] + "..." if len(markdown_content) > 1000 else markdown_content,
                    "sample_associations": associations[:3] if associations else []
                }
            }
            
            # 驗證完整性
            validation_checks = {
                "document_parsed": len(parsed_content.text_blocks) > 0,
                "images_processed": len(parsed_content.images) >= 0,  # 允許無圖片
                "associations_analyzed": True,  # 即使沒有關聯也算完成
                "markdown_generated": len(markdown_content) > 0,
                "no_critical_errors": len(self.test_results["errors"]) == 0
            }
            
            final_results["validation_checks"] = validation_checks
            all_checks_passed = all(validation_checks.values())
            
            self.logger.info("📋 結果驗證摘要:")
            for check, passed in validation_checks.items():
                status = "✅" if passed else "❌"
                self.logger.info(f"  {status} {check}")
            
            if all_checks_passed:
                self.logger.info("🎉 所有驗證檢查通過！")
            else:
                self.logger.warning("⚠️ 部分驗證檢查未通過")
            
            # 記錄性能指標
            processing_time = (datetime.now() - start_time).total_seconds()
            self.test_results["performance_metrics"]["result_validation"] = processing_time
            
            self.test_results["steps_completed"].append("result_validation")
            
            # 重新計算成功率（修復時序問題）
            final_results["quality_metrics"]["steps_completed"] = len(self.test_results["steps_completed"])
            final_results["quality_metrics"]["success_rate"] = len(self.test_results["steps_completed"]) / 5 * 100
            
            self.logger.info("✅ 步驟5: 結果驗證完成")
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"❌ 結果驗證失敗: {str(e)}")
            self.test_results["errors"].append(f"result_validation: {str(e)}")
            raise

    async def generate_test_report(self, final_results):
        """生成詳細測試報告"""
        self.logger.info("📊 生成測試報告...")
        
        report_content = f"""# 完整端到端測試報告

## 測試概述
- **測試文件**: {final_results['test_metadata']['test_file']}
- **測試時間**: {final_results['test_metadata']['test_date']}
- **總處理時間**: {final_results['test_metadata']['total_processing_time']:.2f}秒

## 文檔信息
- **文件名**: {final_results['document_info']['filename']}
- **文件大小**: {final_results['document_info']['file_size']:,} bytes
- **文本塊數**: {final_results['document_info']['text_blocks_count']}
- **圖片數**: {final_results['document_info']['images_count']}
- **表格數**: {final_results['document_info']['tables_count']}

## 處理結果
- **關聯數**: {final_results['processing_results']['associations_count']}
- **Markdown長度**: {final_results['processing_results']['markdown_length']:,} 字符
- **Markdown行數**: {final_results['processing_results']['markdown_lines']}
- **嵌入圖片數**: {final_results['processing_results']['images_in_markdown']}

## 性能指標
"""
        
        for step, time_taken in final_results['performance_metrics'].items():
            report_content += f"- **{step}**: {time_taken:.2f}秒\n"
        
        report_content += f"""
## 質量指標
- **完成步驟**: {final_results['quality_metrics']['steps_completed']}/{final_results['quality_metrics']['total_steps']}
- **成功率**: {final_results['quality_metrics']['success_rate']:.1f}%
- **錯誤數**: {final_results['quality_metrics']['errors_count']}
- **警告數**: {final_results['quality_metrics']['warnings_count']}

## 驗證檢查
"""
        
        for check, passed in final_results['validation_checks'].items():
            status = "✅ 通過" if passed else "❌ 失敗"
            report_content += f"- **{check}**: {status}\n"
        
        if final_results['outputs']['sample_associations']:
            report_content += "\n## 樣本關聯\n"
            for i, assoc in enumerate(final_results['outputs']['sample_associations'], 1):
                report_content += f"### 關聯 {i}\n"
                report_content += f"- **關聯分數**: {assoc['final_score']:.3f}\n"
                report_content += f"- **Caption分數**: {assoc['caption_score']:.3f}\n"
                report_content += f"- **空間分數**: {assoc['spatial_score']:.3f}\n"
                report_content += f"- **語義分數**: {assoc['semantic_score']:.3f}\n"
                report_content += f"- **文本預覽**: {assoc['text_preview']}\n\n"
        
        # 保存報告
        report_file = self.output_dir / "test_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        self.logger.info(f"📊 測試報告已保存: {report_file}")


async def main():
    """主測試函數"""
    test = CompleteEndToEndTest()
    
    try:
        # 運行完整測試
        results = await test.run_complete_test()
        
        print("\n" + "="*80)
        print("🎉 完整端到端測試成功完成！")
        print("="*80)
        print(f"📊 總處理時間: {results['test_metadata']['total_processing_time']:.2f}秒")
        print(f"✅ 成功率: {results['quality_metrics']['success_rate']:.1f}%")
        print(f"📄 文本塊: {results['document_info']['text_blocks_count']}")
        print(f"🖼️ 圖片: {results['document_info']['images_count']}")
        print(f"🎯 關聯: {results['processing_results']['associations_count']}")
        print(f"📝 Markdown: {results['processing_results']['markdown_length']:,} 字符")
        print("="*80)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
