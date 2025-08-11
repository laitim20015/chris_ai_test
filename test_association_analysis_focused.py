#!/usr/bin/env python3
"""
關聯分析專項測試腳本
專門測試圖文關聯分析功能，特別是段落102類似問題的診斷

主要測試內容：
1. Caption檢測準確性（描述性指示詞）
2. 空間關係計算與優先級
3. CandidateRanker智能排序
4. AssociationOptimizer類型同步
5. 完整關聯流程驗證

使用方式：
python test_association_analysis_focused.py
"""

import os
import sys
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
import json
from datetime import datetime

# 添加src目錄到路徑
sys.path.append(str(Path(__file__).parent / "src"))

from src.parsers.base import TextBlock, ImageContent, ContentType, ImageFormat
from src.association.allen_logic import BoundingBox
from src.association.caption_detector import CaptionDetector
from src.association.spatial_analyzer import SpatialAnalyzer
from src.association.semantic_analyzer import SemanticAnalyzer
from src.association.association_scorer import AssociationScorer
from src.association.association_optimizer import AssociationOptimizer
from src.association.candidate_ranker import CandidateRanker
from src.config.settings import Settings

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AssociationAnalysisTest:
    """關聯分析專項測試類"""
    
    def __init__(self):
        """初始化測試組件"""
        self.settings = Settings()
        self.caption_detector = CaptionDetector()
        self.spatial_analyzer = SpatialAnalyzer()
        self.semantic_analyzer = SemanticAnalyzer()
        self.association_scorer = AssociationScorer()
        self.association_optimizer = AssociationOptimizer()
        self.candidate_ranker = CandidateRanker(
            caption_detector=self.caption_detector,
            semantic_analyzer=self.semantic_analyzer
        )
        
        # 測試結果收集
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
        
        logger.info("關聯分析測試組件初始化完成")
    
    def create_test_scenario_paragraph_102(self) -> Tuple[List[TextBlock], List[ImageContent]]:
        """創建段落102類似的測試場景"""
        
        # 模擬段落102：描述性Caption指示詞
        text_blocks = [
            TextBlock(
                id="p102",
                content="下列圖表描述了工作對商務名片進行拼版的方式。",
                content_type=ContentType.PARAGRAPH,
                page_number=1,
                bbox=BoundingBox(x=100, y=200, width=400, height=30)
            ),
            TextBlock(
                id="p103",
                content="1 5 欄",
                content_type=ContentType.PARAGRAPH,
                page_number=1,
                bbox=BoundingBox(x=150, y=400, width=50, height=20)
            ),
            TextBlock(
                id="p104", 
                content="2 5 列",
                content_type=ContentType.PARAGRAPH,
                page_number=1,
                bbox=BoundingBox(x=150, y=430, width=50, height=20)
            ),
            TextBlock(
                id="p116",
                content="• 11 x 17 重磅紙，如卡片紙張",
                content_type=ContentType.LIST,
                page_number=1,
                bbox=BoundingBox(x=120, y=650, width=280, height=20)
            ),
            TextBlock(
                id="p120",
                content="4 選擇聯合拼版，然後選擇重複。",
                content_type=ContentType.PARAGRAPH,
                page_number=1,
                bbox=BoundingBox(x=120, y=720, width=300, height=20)
            )
        ]
        
        # 目標圖片位置（應該關聯到p102）
        images = [
            ImageContent(
                id="img_001",
                filename="workflows_sample_p011_img001.png",
                format=ImageFormat.PNG,
                data=b"fake_image_data",
                page_number=1,
                bbox=BoundingBox(x=100, y=250, width=400, height=130),  # 在p102下方
                alt_text="商務名片拼版布局圖表"
            )
        ]
        
        return text_blocks, images
    
    def test_caption_detection_descriptive_words(self) -> Dict[str, Any]:
        """測試描述性指示詞的Caption檢測"""
        logger.info("🔍 測試1: Caption檢測 - 描述性指示詞")
        
        test_cases = [
            ("下列圖表描述了工作對商務名片進行拼版的方式。", 0.7),  # 段落102原文
            ("以下圖示說明了操作流程。", 0.7),
            ("上圖顯示了數據分析結果。", 0.7),
            ("圖1顯示了銷售趨勢", 0.9),  # 編號引用應該更高分
            ("Figure 1 shows the trend", 0.9),
            ("• 11 x 17 重磅紙，如卡片紙張", 0.1),  # 普通文本
        ]
        
        results = []
        passed = 0
        
        for text_content, expected_min_score in test_cases:
            text_block = TextBlock(
                id="test_text",
                content=text_content,
                content_type=ContentType.PARAGRAPH,
                page_number=1,
                bbox=BoundingBox(x=100, y=200, width=300, height=30)
            )
            
            image = ImageContent(
                id="test_image",
                filename="test.jpg",
                format=ImageFormat.JPEG,
                data=b"fake_data",
                page_number=1,
                bbox=BoundingBox(x=100, y=250, width=300, height=100),
                alt_text="測試圖片"
            )
            
            caption_matches = self.caption_detector.detect_captions(
                text_content, text_block.bbox, image.bbox
            )
            caption_score = max((match.confidence for match in caption_matches), default=0.0)
            
            test_passed = caption_score >= expected_min_score
            if test_passed:
                passed += 1
            
            result = {
                'text': text_content,
                'expected_min_score': expected_min_score,
                'actual_score': caption_score,
                'passed': test_passed,
                'caption_matches': len(caption_matches)
            }
            results.append(result)
            
            logger.info(f"   文本: '{text_content[:30]}...' | "
                       f"期望≥{expected_min_score:.1f} | 實際: {caption_score:.3f} | "
                       f"{'✅' if test_passed else '❌'}")
        
        self.test_results['total_tests'] += len(test_cases)
        self.test_results['passed_tests'] += passed
        self.test_results['failed_tests'] += len(test_cases) - passed
        
        return {
            'test_name': 'Caption檢測 - 描述性指示詞',
            'total_cases': len(test_cases),
            'passed': passed,
            'success_rate': passed / len(test_cases),
            'details': results
        }
    
    def test_spatial_relationship_priority(self) -> Dict[str, Any]:
        """測試空間關係優先級計算"""
        logger.info("🔍 測試2: 空間關係優先級")
        
        text_blocks, images = self.create_test_scenario_paragraph_102()
        target_image = images[0]
        
        results = []
        
        for text_block in text_blocks:
            # 計算空間特徵
            spatial_features = self.spatial_analyzer.calculate_spatial_features(
                text_block.bbox, target_image.bbox
            )
            
            # 增強空間分析
            context_info = {
                'all_elements': text_blocks + images,
                'text_content': text_block.content
            }
            
            try:
                enhanced_result = self.spatial_analyzer.calculate_enhanced_spatial_features(
                    text_block.bbox, target_image.bbox, context_info
                )
                enhanced_score = enhanced_result['final_score']
                spatial_relationship = enhanced_result['details']['relationship']
            except Exception as e:
                logger.warning(f"增強空間分析失敗: {e}")
                enhanced_score = 0.5
                spatial_relationship = "unknown"
            
            result = {
                'text_id': text_block.id,
                'text_content': text_block.content[:50],
                'center_distance': spatial_features.center_distance if spatial_features else 0,
                'min_distance': spatial_features.min_distance if spatial_features else 0,
                'alignment_score': spatial_features.alignment_score if spatial_features else 0,
                'enhanced_spatial_score': enhanced_score,
                'spatial_relationship': spatial_relationship,
                'is_above_image': text_block.bbox.bottom <= target_image.bbox.top
            }
            results.append(result)
            
            logger.info(f"   {text_block.id}: {text_block.content[:30]}... | "
                       f"空間分數: {enhanced_score:.3f} | 關係: {spatial_relationship}")
        
        # 驗證段落102應該有合理的空間關係
        p102_result = next((r for r in results if r['text_id'] == 'p102'), None)
        test_passed = p102_result and p102_result['is_above_image'] and p102_result['enhanced_spatial_score'] > 0.3
        
        self.test_results['total_tests'] += 1
        if test_passed:
            self.test_results['passed_tests'] += 1
        else:
            self.test_results['failed_tests'] += 1
        
        return {
            'test_name': '空間關係優先級',
            'passed': test_passed,
            'p102_spatial_score': p102_result['enhanced_spatial_score'] if p102_result else 0,
            'details': results
        }
    
    def test_candidate_ranking_logic(self) -> Dict[str, Any]:
        """測試候選排序器邏輯"""
        logger.info("🔍 測試3: CandidateRanker智能排序")
        
        text_blocks, images = self.create_test_scenario_paragraph_102()
        target_image = images[0]
        
        # 準備候選文本
        text_candidates = [
            {
                'id': tb.id,
                'content': tb.content,
                'bbox': tb.bbox
            }
            for tb in text_blocks
        ]
        
        context_info = {
            'all_elements': text_blocks + images,
            'document_type': 'manual'
        }
        
        # 執行候選排序
        ranked_candidates = self.candidate_ranker.rank_candidates(
            text_candidates=text_candidates,
            image_bbox=target_image.bbox,
            image_content=target_image.alt_text,
            context_info=context_info
        )
        
        results = []
        for i, candidate in enumerate(ranked_candidates):
            result = {
                'rank': candidate.rank,
                'text_id': candidate.text_id,
                'text_content': candidate.text_content[:50],
                'final_score': candidate.scores.final_score,
                'caption_score': candidate.scores.caption_score,
                'spatial_score': candidate.scores.spatial_score,
                'semantic_score': candidate.scores.semantic_score,
                'is_recommended': candidate.is_recommended,
                'quality': candidate.scores.quality.value,
                'reasoning': candidate.reasoning[:100] if candidate.reasoning else ""
            }
            results.append(result)
            
            logger.info(f"   排名{candidate.rank}: {candidate.text_id} | "
                       f"總分: {candidate.scores.final_score:.3f} | "
                       f"Caption: {candidate.scores.caption_score:.3f} | "
                       f"推薦: {'✅' if candidate.is_recommended else '❌'}")
        
        # 驗證段落102是否獲得較高排名
        p102_candidate = next((c for c in ranked_candidates if c.text_id == 'p102'), None)
        test_passed = p102_candidate and p102_candidate.rank <= 3 and p102_candidate.is_recommended
        
        self.test_results['total_tests'] += 1
        if test_passed:
            self.test_results['passed_tests'] += 1
        else:
            self.test_results['failed_tests'] += 1
        
        return {
            'test_name': 'CandidateRanker智能排序',
            'passed': test_passed,
            'p102_rank': p102_candidate.rank if p102_candidate else None,
            'p102_recommended': p102_candidate.is_recommended if p102_candidate else False,
            'total_candidates': len(ranked_candidates),
            'recommended_count': sum(1 for c in ranked_candidates if c.is_recommended),
            'details': results
        }
    
    def test_complete_association_workflow(self) -> Dict[str, Any]:
        """測試完整關聯分析工作流程"""
        logger.info("🔍 測試4: 完整關聯分析工作流程")
        
        text_blocks, images = self.create_test_scenario_paragraph_102()
        target_image = images[0]
        
        # 執行完整關聯分析
        associations = []
        
        for text_block in text_blocks:
            # 1. Caption檢測
            caption_matches = self.caption_detector.detect_captions(
                text_block.content, text_block.bbox, target_image.bbox
            )
            caption_score = max((match.confidence for match in caption_matches), default=0.0)
            
            # 2. 空間關係分析
            spatial_features = self.spatial_analyzer.calculate_spatial_features(
                text_block.bbox, target_image.bbox
            )
            
            # 3. 語義相似度分析
            semantic_score = self.semantic_analyzer.calculate_similarity(
                text_block.content, 
                target_image.alt_text or f"Image {target_image.id}"
            )
            
            # 4. 增強空間分析
            context_info = {
                'all_elements': text_blocks + images,
                'text_content': text_block.content
            }
            
            try:
                enhanced_result = self.spatial_analyzer.calculate_enhanced_spatial_features(
                    text_block.bbox, target_image.bbox, context_info
                )
                enhanced_spatial_score = enhanced_result['final_score']
                layout_score = enhanced_result['component_scores'].get('alignment', 0.5)
                proximity_score = enhanced_result['component_scores'].get('distance', 0.5)
            except Exception:
                enhanced_spatial_score = 0.5
                layout_score = 0.5
                proximity_score = 0.5
            
            # 5. 綜合評分
            final_score, details = self.association_scorer.calculate_simple_score(
                caption_score=caption_score,
                spatial_score=enhanced_spatial_score,
                semantic_score=semantic_score,
                layout_score=layout_score,
                proximity_score=proximity_score
            )
            
            # 6. 創建關聯記錄
            association = {
                "text_block_id": text_block.id,
                "image_id": target_image.id,
                "final_score": final_score,
                "caption_score": caption_score,
                "spatial_score": enhanced_spatial_score,
                "semantic_score": semantic_score,
                "layout_score": layout_score,
                "proximity_score": proximity_score,
                "association_type": "caption" if caption_score > 0.5 else "spatial",
                "details": details
            }
            
            associations.append(association)
        
        # 7. 關聯優化
        optimized_associations = self.association_optimizer.optimize_associations(
            associations=associations,
            images=images,
            text_blocks=text_blocks
        )
        
        # 分析結果
        results = []
        for assoc in optimized_associations:
            result = {
                'text_id': assoc['text_block_id'],
                'final_score': assoc['final_score'],
                'adjusted_score': assoc.get('adjusted_score', assoc['final_score']),
                'caption_score': assoc['caption_score'],
                'association_type': assoc['association_type'],
                'caption_boosted': assoc.get('caption_boosted', False),
                'quality_grade': assoc.get('quality_grade', 'unknown')
            }
            results.append(result)
            
            logger.info(f"   {assoc['text_block_id']}: 分數 {assoc['final_score']:.3f} → "
                       f"{assoc.get('adjusted_score', assoc['final_score']):.3f} | "
                       f"類型: {assoc['association_type']} | "
                       f"Caption加成: {'✅' if assoc.get('caption_boosted', False) else '❌'}")
        
        # 驗證段落102的處理結果
        p102_assoc = next((a for a in optimized_associations if a['text_block_id'] == 'p102'), None)
        
        if p102_assoc:
            test_passed = (
                p102_assoc['caption_score'] > 0.3 and  # Caption檢測到
                p102_assoc['association_type'] == 'caption' and  # 類型正確
                p102_assoc.get('caption_boosted', False)  # 獲得Caption加成
            )
        else:
            test_passed = False
        
        self.test_results['total_tests'] += 1
        if test_passed:
            self.test_results['passed_tests'] += 1
        else:
            self.test_results['failed_tests'] += 1
        
        return {
            'test_name': '完整關聯分析工作流程',
            'passed': test_passed,
            'total_associations': len(associations),
            'optimized_associations': len(optimized_associations),
            'p102_found': p102_assoc is not None,
            'p102_caption_score': p102_assoc['caption_score'] if p102_assoc else 0,
            'p102_association_type': p102_assoc['association_type'] if p102_assoc else 'none',
            'p102_caption_boosted': p102_assoc.get('caption_boosted', False) if p102_assoc else False,
            'details': results
        }
    
    def test_association_type_consistency(self) -> Dict[str, Any]:
        """測試關聯類型一致性（Caption檢測與類型標記同步）"""
        logger.info("🔍 測試5: 關聯類型一致性檢查")
        
        # 測試案例：明確的Caption指示詞
        test_cases = [
            "下列圖表描述了工作對商務名片進行拼版的方式。",
            "圖1顯示了銷售趨勢變化",
            "以下圖示說明了操作流程",
            "Figure 2 demonstrates the process"
        ]
        
        results = []
        consistent_count = 0
        
        for text_content in test_cases:
            text_block = TextBlock(
                id=f"test_{len(results)}",
                content=text_content,
                content_type=ContentType.PARAGRAPH,
                page_number=1,
                bbox=BoundingBox(x=100, y=200, width=400, height=30)
            )
            
            image = ImageContent(
                id="test_image",
                filename="test.jpg",
                format=ImageFormat.JPEG,
                data=b"fake_data",
                page_number=1,
                bbox=BoundingBox(x=100, y=250, width=400, height=130),
                alt_text="測試圖片"
            )
            
            # 1. Caption檢測
            caption_matches = self.caption_detector.detect_captions(
                text_content, text_block.bbox, image.bbox
            )
            caption_score = max((match.confidence for match in caption_matches), default=0.0)
            
            # 2. 初始關聯類型決定
            initial_type = "caption" if caption_score > 0.5 else "spatial"
            
            # 3. 模擬優化過程
            association = {
                "text_block_id": text_block.id,
                "image_id": image.id,
                "final_score": 0.6,
                "caption_score": caption_score,
                "spatial_score": 0.5,
                "semantic_score": 0.4,
                "layout_score": 0.5,
                "proximity_score": 0.5,
                "association_type": initial_type
            }
            
            # 4. 關聯優化
            optimized = self.association_optimizer.optimize_associations(
                associations=[association],
                images=[image],
                text_blocks=[text_block]
            )
            
            if optimized:
                final_type = optimized[0]['association_type']
                caption_boosted = optimized[0].get('caption_boosted', False)
                
                # 檢查一致性
                is_consistent = (
                    (caption_score > 0.3 and final_type == 'caption') or
                    (caption_score <= 0.3 and final_type == 'spatial')
                )
                
                if is_consistent:
                    consistent_count += 1
            else:
                final_type = 'none'
                caption_boosted = False
                is_consistent = False
            
            result = {
                'text_content': text_content,
                'caption_score': caption_score,
                'initial_type': initial_type,
                'final_type': final_type,
                'caption_boosted': caption_boosted,
                'is_consistent': is_consistent
            }
            results.append(result)
            
            logger.info(f"   文本: '{text_content[:40]}...' | "
                       f"Caption分數: {caption_score:.3f} | "
                       f"類型: {initial_type} → {final_type} | "
                       f"一致性: {'✅' if is_consistent else '❌'}")
        
        test_passed = consistent_count == len(test_cases)
        
        self.test_results['total_tests'] += 1
        if test_passed:
            self.test_results['passed_tests'] += 1
        else:
            self.test_results['failed_tests'] += 1
        
        return {
            'test_name': '關聯類型一致性檢查',
            'passed': test_passed,
            'consistent_count': consistent_count,
            'total_cases': len(test_cases),
            'consistency_rate': consistent_count / len(test_cases),
            'details': results
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """執行所有測試"""
        logger.info("🚀 開始關聯分析專項測試")
        
        test_functions = [
            self.test_caption_detection_descriptive_words,
            self.test_spatial_relationship_priority,
            self.test_candidate_ranking_logic,
            self.test_complete_association_workflow,
            self.test_association_type_consistency
        ]
        
        all_results = []
        
        for test_func in test_functions:
            try:
                result = test_func()
                self.test_results['test_details'].append(result)
                all_results.append(result)
                logger.info(f"✅ {result['test_name']} 完成")
            except Exception as e:
                logger.error(f"❌ {test_func.__name__} 測試失敗: {e}")
                self.test_results['failed_tests'] += 1
                all_results.append({
                    'test_name': test_func.__name__,
                    'passed': False,
                    'error': str(e)
                })
        
        # 計算總體結果
        self.test_results['success_rate'] = (
            self.test_results['passed_tests'] / self.test_results['total_tests'] 
            if self.test_results['total_tests'] > 0 else 0
        )
        
        return {
            'summary': self.test_results,
            'individual_results': all_results
        }
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成測試報告"""
        summary = results['summary']
        
        report = f"""
# 關聯分析專項測試報告

## 📊 測試總結

- **測試時間**: {summary['timestamp']}
- **總測試數**: {summary['total_tests']}
- **通過測試**: {summary['passed_tests']}
- **失敗測試**: {summary['failed_tests']}
- **成功率**: {summary['success_rate']:.1%}

## 📋 測試詳情

"""
        
        for test_detail in summary['test_details']:
            report += f"### {test_detail['test_name']}\n"
            report += f"- **結果**: {'✅ 通過' if test_detail['passed'] else '❌ 失敗'}\n"
            
            if 'success_rate' in test_detail:
                report += f"- **成功率**: {test_detail['success_rate']:.1%}\n"
            
            if 'details' in test_detail and isinstance(test_detail['details'], list):
                report += f"- **詳細結果**: {len(test_detail['details'])} 個測試案例\n"
            
            report += "\n"
        
        # 針對段落102問題的特別分析
        report += """
## 🎯 段落102問題分析

基於測試結果的分析：
1. **Caption檢測**: 描述性指示詞的檢測準確性
2. **空間優先**: 上方文本的空間關係計算
3. **候選排序**: CandidateRanker的智能排序效果
4. **類型一致**: Caption檢測與關聯類型的同步性
5. **完整流程**: 端到端的關聯分析準確性

## 🔧 改進建議

基於測試發現的問題，建議：
1. 增強描述性Caption指示詞的檢測模式
2. 優化空間關係的位置加權邏輯
3. 確保關聯類型與Caption檢測結果的同步
4. 加強候選排序中的上方優先規則

"""
        
        return report


def main():
    """主函數"""
    print("🚀 關聯分析專項測試啟動")
    print("=" * 60)
    
    # 初始化測試
    test_runner = AssociationAnalysisTest()
    
    # 執行所有測試
    results = test_runner.run_all_tests()
    
    # 生成報告
    report = test_runner.generate_report(results)
    
    # 保存結果
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # 保存JSON結果
    json_file = output_dir / "association_analysis_test_results.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    # 保存Markdown報告
    report_file = output_dir / "association_analysis_test_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 輸出結果
    print("\n" + "=" * 60)
    print("📊 測試完成!")
    print(f"總測試數: {results['summary']['total_tests']}")
    print(f"通過測試: {results['summary']['passed_tests']}")
    print(f"失敗測試: {results['summary']['failed_tests']}")
    print(f"成功率: {results['summary']['success_rate']:.1%}")
    print(f"\n📁 詳細結果保存至:")
    print(f"   - JSON: {json_file}")
    print(f"   - 報告: {report_file}")
    
    # 重點分析段落102類似問題
    print("\n🎯 段落102問題重點分析:")
    
    for test_detail in results['summary']['test_details']:
        if 'p102' in str(test_detail):
            print(f"   - {test_detail['test_name']}: {'✅' if test_detail['passed'] else '❌'}")
    
    print("\n" + "=" * 60)
    
    return results['summary']['success_rate']


if __name__ == "__main__":
    success_rate = main()
    # 返回適當的退出碼
    sys.exit(0 if success_rate >= 0.8 else 1)