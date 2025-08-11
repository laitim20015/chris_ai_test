"""
主應用程序入口點

智能文件轉換與RAG知識庫系統的核心處理引擎，
協調文件解析、圖文關聯分析和Markdown生成的完整流程。
"""

import os
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from .config.settings import get_settings
from .config.logging_config import get_logger, PerformanceLogger
from .parsers import ParserFactory, ParsedContent
from .association import AssociationScorer
from .association.allen_logic import AllenLogicAnalyzer
from .association.caption_detector import CaptionDetector
from .association.spatial_analyzer import SpatialAnalyzer
from .association.semantic_analyzer import SemanticAnalyzer
from .association.association_optimizer import AssociationOptimizer, create_balanced_config
from .association.candidate_ranker import CandidateRanker
from .markdown import MarkdownGenerator
from .utils.file_utils import ensure_directory_exists, get_file_hash
from .utils.validation import validate_file_path, check_file_safety

logger = get_logger(__name__)


class DocumentProcessor:
    """
    文件處理核心引擎
    
    協調整個文件轉換流程，從原始文件到Markdown輸出。
    支持多種文件格式和智能圖文關聯分析。
    """
    
    def __init__(self):
        """初始化文件處理器"""
        self.settings = get_settings()
        self.parser_factory = ParserFactory()
        self.markdown_generator = MarkdownGenerator()
        
        # 初始化關聯分析組件
        self.allen_analyzer = AllenLogicAnalyzer()
        self.caption_detector = CaptionDetector()
        self.spatial_analyzer = SpatialAnalyzer()
        self.semantic_analyzer = SemanticAnalyzer()
        self.association_scorer = AssociationScorer()
        
        # 初始化關聯優化器
        self.association_optimizer = AssociationOptimizer(create_balanced_config())
        
        # 初始化候選排序器（智能關聯選擇）
        self.candidate_ranker = CandidateRanker(
            caption_detector=self.caption_detector,
            semantic_analyzer=self.semantic_analyzer
        )
        
        # 性能監控
        self.performance_logger = PerformanceLogger()
        
        logger.info("文件處理器初始化完成")
    
    def process_document(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
        template_name: str = "enhanced.md.j2",
        save_associations: bool = True
    ) -> Dict[str, Any]:
        """
        處理單個文檔
        
        Args:
            file_path: 輸入文件路徑
            output_dir: 輸出目錄（可選）
            template_name: 使用的模板名稱
            save_associations: 是否保存關聯分析結果
            
        Returns:
            Dict: 處理結果，包含生成的文件路徑和統計信息
        """
        
        start_time = time.time()
        
        try:
            # 1. 文件驗證
            logger.info(f"開始處理文檔: {file_path}")
            
            if not validate_file_path(file_path):
                raise ValueError(f"文件路徑無效: {file_path}")
            
            is_safe, warnings = check_file_safety(file_path)
            if not is_safe:
                logger.warning(f"文件安全檢查警告: {warnings}")
            
            # 2. 文件解析
            with self.performance_logger.measure("file_parsing"):
                parsed_content = self._parse_file(file_path)
            
            logger.info(
                f"文件解析完成 - 文本塊: {len(parsed_content.text_blocks)}, "
                f"圖片: {len(parsed_content.images)}, "
                f"表格: {len(parsed_content.tables)}"
            )
            
            # 3. 圖文關聯分析
            with self.performance_logger.measure("association_analysis"):
                associations = self._analyze_associations(parsed_content)
            
            logger.info(f"關聯分析完成 - 發現 {len(associations)} 個關聯關係")
            
            # 4. 生成Markdown
            with self.performance_logger.measure("markdown_generation"):
                markdown_content = self._generate_markdown(
                    parsed_content, associations, template_name
                )
            
            # 5. 保存結果
            output_files = self._save_results(
                parsed_content, associations, markdown_content,
                output_dir, save_associations
            )
            
            # 6. 統計信息
            processing_time = time.time() - start_time
            stats = self._collect_statistics(
                parsed_content, associations, processing_time
            )
            
            logger.info(f"文檔處理完成，耗時: {processing_time:.2f}秒")
            
            return {
                "success": True,
                "output_files": output_files,
                "statistics": stats,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"文檔處理失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    def _parse_file(self, file_path: str) -> ParsedContent:
        """解析文件內容"""
        
        file_extension = Path(file_path).suffix.lower()
        parser = self.parser_factory.get_parser(file_extension)
        
        if not parser:
            raise ValueError(f"不支持的文件格式: {file_extension}")
        
        return parser.parse(file_path)
    
    def _analyze_associations(self, parsed_content: ParsedContent) -> List[Dict[str, Any]]:
        """分析圖文關聯關係 - 使用智能候選排序策略"""
        
        associations = []
        
        # 收集所有元素供增強空間分析使用
        self._current_all_elements = parsed_content.text_blocks + parsed_content.images
        
        # 準備上下文信息
        context_info = {
            'all_elements': self._current_all_elements,
            # 已移除硬編碼layout_type，讓增強空間分析自動檢測佈局
        }
        
        logger.info(f"開始智能圖文關聯分析 - 圖片數: {len(parsed_content.images)}, 文本塊數: {len(parsed_content.text_blocks)}")
        
        # 🎯 核心改進：圖片優先的智能候選排序策略
        for image in parsed_content.images:
            try:
                # 準備候選文本列表（所有文本塊都是潛在候選）
                text_candidates = [
                    {
                        'id': text_block.id,
                        'content': text_block.content,
                        'bbox': text_block.bbox
                    }
                    for text_block in parsed_content.text_blocks
                ]
                
                # 使用CandidateRanker進行智能排序
                ranked_candidates = self.candidate_ranker.rank_candidates(
                    text_candidates=text_candidates,
                    image_bbox=image.bbox,
                    image_content=getattr(image, 'description', None),
                    context_info=context_info
                )
                
                # 選擇推薦的候選進行詳細關聯分析
                threshold = self.settings.association.min_association_score
                
                for ranked_candidate in ranked_candidates:
                    # 只處理推薦的候選或高分候選
                    if (ranked_candidate.is_recommended or 
                        ranked_candidate.scores.final_score >= threshold):
                        
                        # 從ranked_candidate轉換回text_block格式
                        text_block = next(
                            (tb for tb in parsed_content.text_blocks 
                             if tb.id == ranked_candidate.text_id), 
                            None
                        )
                        
                        if text_block:
                            # 執行完整的關聯分析
                            association_result = self._perform_association_analysis(
                                text_block, image, parsed_content
                            )
                            
                            # 融合CandidateRanker的排序信息
                            association_result.update({
                                'candidate_rank': ranked_candidate.rank,
                                'candidate_quality': ranked_candidate.scores.quality.value,
                                'candidate_reasoning': ranked_candidate.reasoning,
                                'is_candidate_recommended': ranked_candidate.is_recommended
                            })
                            
                            associations.append(association_result)
                
                logger.debug(f"圖片 {image.id} 完成候選排序，找到 {len([c for c in ranked_candidates if c.is_recommended])} 個推薦關聯")
                
            except Exception as e:
                logger.warning(f"圖片 {image.id} 的智能關聯分析失敗: {e}")
        
        # 🔧 關聯優化 - 去重、過濾和質量提升
        logger.info(f"開始關聯優化 - 原始關聯數: {len(associations)}")
        
        optimized_associations = self.association_optimizer.optimize_associations(
            associations=associations,
            images=parsed_content.images,
            text_blocks=parsed_content.text_blocks
        )
        
        logger.info(f"智能關聯分析完成 - 優化後關聯數: {len(optimized_associations)}")
        logger.info(f"關聯減少率: {((len(associations) - len(optimized_associations)) / len(associations) * 100):.1f}%" if associations else "0%")
        
        return optimized_associations
    
    def _perform_association_analysis(self, text_block, image, parsed_content: ParsedContent = None) -> Dict[str, Any]:
        """執行單個文本塊和圖片的關聯分析"""
        
        # 1. Caption檢測
        caption_matches = self.caption_detector.detect_captions(
            text_block.content, text_block.bbox, image.bbox
        )
        caption_score = max((match.confidence for match in caption_matches), default=0.0)
        
        # 2. 空間關係分析
        spatial_features = self.spatial_analyzer.calculate_spatial_features(
            text_block.bbox, image.bbox
        )
        
        # 3. 語義相似度分析
        semantic_score = self.semantic_analyzer.calculate_similarity(
            text_block.content, 
            image.alt_text or f"Image {image.id}"
        )
        
        # 4. 增強的空間關係分析（使用改進的算法）
        try:
            # 創建上下文信息（用於增強空間分析）
            all_elements = getattr(self, '_current_all_elements', [])
            if parsed_content:
                all_elements = parsed_content.text_blocks + parsed_content.images
            
            context_info = {
                'all_elements': all_elements,
                # 移除硬編碼的layout_type，讓增強空間分析自動檢測佈局
                'text_content': text_block.content  # 傳遞文本內容以供分析
            }
            
            # 使用增強的空間分析（僅用於空間關係部分）
            enhanced_result = self.spatial_analyzer.calculate_enhanced_spatial_features(
                text_block.bbox, image.bbox, context_info
            )
            
            # 提取空間分析結果
            enhanced_spatial_score = enhanced_result['final_score']  # 這是改進後的空間分數
            
            # 可選：記錄詳細分析信息供調試
            logger.debug(f"增強空間分析詳情 - 關係: {enhanced_result['details']['relationship']}, "
                        f"空間分數: {enhanced_spatial_score:.3f}")
            
        except Exception as e:
            # 備選方案：使用傳統空間分析方法
            logger.warning(f"增強空間分析失敗，使用傳統方法: {e}")
            
            if spatial_features:
                # 估算頁面尺寸（使用所有元素的最大座標）
                page_width = max(text_block.bbox.right, image.bbox.right)
                page_height = max(text_block.bbox.bottom, image.bbox.bottom)
                page_diagonal = (page_width ** 2 + page_height ** 2) ** 0.5
                
                # 使用傳統的空間分數計算
                enhanced_spatial_score = 1.0 - min(spatial_features.center_distance / (page_diagonal * 0.5), 1.0)
            else:
                enhanced_spatial_score = 0.0
        
        # 5. 綜合評分 - 按照項目規則的權重模型
        # Caption 40% + Spatial 30% + Semantic 15% + Layout 10% + Proximity 5%
        
        # 佈局和距離分數（從增強空間分析中獲取）
        if 'enhanced_result' in locals() and enhanced_result:
            layout_score = enhanced_result['component_scores'].get('alignment', 0.5)
            proximity_score = enhanced_result['component_scores'].get('distance', 0.5)
        else:
            layout_score = spatial_features.alignment_score if spatial_features else 0.5
            proximity_score = 0.5  # 預設值
        
        final_score, details = self.association_scorer.calculate_simple_score(
            caption_score=caption_score,
            spatial_score=enhanced_spatial_score,  # 使用增強的空間分數
            semantic_score=semantic_score,
            layout_score=layout_score,
            proximity_score=proximity_score
        )
        
        return {
            "text_block_id": text_block.id,
            "image_id": image.id,
            "final_score": final_score,
            "caption_score": caption_score,
            "spatial_score": enhanced_spatial_score,  # 使用增強的空間分數
            "semantic_score": semantic_score,
            "layout_score": layout_score,
            "proximity_score": proximity_score,
            "spatial_relation": "enhanced",  # 使用增強的空間分析
            "association_type": "caption" if caption_score > 0.5 else "spatial",
            "details": details,
            "enhanced_spatial_details": enhanced_result.get('details', {}) if 'enhanced_result' in locals() else {},
            "spatial_features": {
                "center_distance": spatial_features.center_distance if spatial_features else 0,
                "alignment_score": spatial_features.alignment_score if spatial_features else 0,
                "min_distance": spatial_features.min_distance if spatial_features else 0
            }
        }
    
    def _generate_markdown(
        self, 
        parsed_content: ParsedContent, 
        associations: List[Dict[str, Any]],
        template_name: str
    ) -> str:
        """生成Markdown內容"""
        
        return self.markdown_generator.generate(
            parsed_content=parsed_content,
            associations=associations,
            template_name=template_name,
            include_metadata=True
        )
    
    def _save_results(
        self,
        parsed_content: ParsedContent,
        associations: List[Dict[str, Any]],
        markdown_content: str,
        output_dir: Optional[str],
        save_associations: bool
    ) -> Dict[str, str]:
        """保存處理結果"""
        
        if not output_dir:
            output_dir = "./output"
        
        ensure_directory_exists(output_dir)
        
        # 生成文件名
        base_name = Path(parsed_content.metadata.filename).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_files = {}
        
        # 保存Markdown文件
        markdown_path = Path(output_dir) / f"{base_name}_{timestamp}.md"
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        output_files["markdown"] = str(markdown_path)
        
        # 保存關聯分析結果
        if save_associations:
            import json
            from enum import Enum
            
            # 序列化助手函數
            def serialize_for_json(obj):
                if isinstance(obj, Enum):
                    return obj.value
                elif hasattr(obj, '__dict__'):
                    return {k: serialize_for_json(v) for k, v in obj.__dict__.items()}
                elif isinstance(obj, (list, tuple)):
                    return [serialize_for_json(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: serialize_for_json(v) for k, v in obj.items()}
                else:
                    return obj
            
            serializable_associations = serialize_for_json(associations)
            
            associations_path = Path(output_dir) / f"{base_name}_{timestamp}_associations.json"
            with open(associations_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_associations, f, ensure_ascii=False, indent=2)
            output_files["associations"] = str(associations_path)
        
        return output_files
    
    def _collect_statistics(
        self,
        parsed_content: ParsedContent,
        associations: List[Dict[str, Any]],
        processing_time: float
    ) -> Dict[str, Any]:
        """收集處理統計信息"""
        
        # 計算關聯統計
        high_quality_associations = [
            a for a in associations if a["final_score"] >= 0.7
        ]
        
        caption_associations = [
            a for a in associations if a["association_type"] == "caption"
        ]
        
        return {
            "processing_time": processing_time,
            "total_text_blocks": len(parsed_content.text_blocks),
            "total_images": len(parsed_content.images),
            "total_tables": len(parsed_content.tables),
            "total_associations": len(associations),
            "high_quality_associations": len(high_quality_associations),
            "caption_associations": len(caption_associations),
            "average_association_score": (
                sum(a["final_score"] for a in associations) / len(associations)
                if associations else 0.0
            ),
            "performance_metrics": self.performance_logger.get_summary()
        }


def main():
    """主函數 - 命令行界面"""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="智能文件轉換與RAG知識庫系統"
    )
    
    parser.add_argument(
        "input_file",
        help="輸入文件路徑"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="輸出目錄",
        default="./output"
    )
    
    parser.add_argument(
        "-t", "--template",
        help="使用的模板",
        choices=["basic.md.j2", "enhanced.md.j2"],
        default="enhanced.md.j2"
    )
    
    parser.add_argument(
        "--no-associations",
        action="store_true",
        help="不保存關聯分析結果"
    )
    
    args = parser.parse_args()
    
    try:
        processor = DocumentProcessor()
        
        result = processor.process_document(
            file_path=args.input_file,
            output_dir=args.output,
            template_name=args.template,
            save_associations=not args.no_associations
        )
        
        if result["success"]:
            print("✅ 處理成功！")
            print(f"📊 統計信息:")
            stats = result["statistics"]
            print(f"  - 處理時間: {stats['processing_time']:.2f}秒")
            print(f"  - 文本塊: {stats['total_text_blocks']}")
            print(f"  - 圖片: {stats['total_images']}")
            print(f"  - 關聯關係: {stats['total_associations']}")
            print(f"  - 高質量關聯: {stats['high_quality_associations']}")
            
            print(f"📁 輸出文件:")
            for file_type, file_path in result["output_files"].items():
                print(f"  - {file_type}: {file_path}")
        else:
            print(f"❌ 處理失敗: {result['error']}")
            return 1
    
    except Exception as e:
        logger.error(f"主程序執行失敗: {e}")
        print(f"❌ 執行失敗: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
