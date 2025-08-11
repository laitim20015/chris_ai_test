"""
候選排序器 - 圖文關聯的最終排序和優先級調整模組
Candidate Ranker - Final Ranking and Priority Adjustment Module for Image-Text Association

此模組整合了所有前面開發的改進功能：
1. Phase 1: 增強空間分析（方向敏感、動態歸一化）
2. Phase 2.1: 佈局分析（欄位檢測、跨欄位懲罰）
3. Phase 2.2: 文檔類型識別（權重動態調整）
4. Phase 2.3: Caption檢測增強（最近上方優先）

提供統一的候選排序接口，實現智能的優先級調整機制。
"""

from typing import List, Dict, Tuple, Optional, Any, NamedTuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

from src.association.spatial_analyzer import (
    enhanced_spatial_scoring, 
    identify_document_type, 
    get_document_type_weights,
    DocumentType
)
from src.association.caption_detector import CaptionDetector
from src.association.semantic_analyzer import SemanticAnalyzer
from src.association.allen_logic import BoundingBox
from src.config.logging_config import get_logger

logger = get_logger("candidate_ranker")

class AssociationQuality(Enum):
    """關聯質量等級"""
    
    EXCELLENT = "excellent"        # 優秀 (>= 0.8)
    GOOD = "good"                 # 良好 (>= 0.6)
    FAIR = "fair"                 # 一般 (>= 0.4)
    POOR = "poor"                 # 較差 (>= 0.2)
    VERY_POOR = "very_poor"       # 很差 (< 0.2)

@dataclass
class CandidateScore:
    """候選關聯分數詳情"""
    
    # 基礎分數
    spatial_score: float = 0.0          # 空間分析分數
    caption_score: float = 0.0          # Caption檢測分數
    semantic_score: float = 0.0         # 語義相似度分數
    
    # 增強分數組件
    vertical_score: float = 0.0         # 垂直關係分數
    horizontal_score: float = 0.0       # 水平重疊分數
    distance_score: float = 0.0         # 歸一化距離分數
    alignment_score: float = 0.0        # 對齊分數
    
    # 懲罰和加分因子
    layout_penalty: float = 1.0         # 佈局懲罰（跨欄位等）
    intervening_penalty: float = 1.0    # 介入元素懲罰
    priority_boost: float = 1.0         # 優先級提升（最近上方等）
    
    # 最終結果
    final_score: float = 0.0            # 最終關聯分數
    quality: AssociationQuality = AssociationQuality.VERY_POOR
    confidence: float = 0.0             # 置信度

@dataclass
class RankedCandidate:
    """排序後的候選結果"""
    
    # 候選信息
    text_id: str                        # 文本塊ID
    text_content: str                   # 文本內容
    text_bbox: BoundingBox             # 文本邊界框
    
    # 評分詳情
    scores: CandidateScore             # 詳細分數
    
    # 排序信息
    rank: int = 0                      # 排名（從1開始）
    is_recommended: bool = False       # 是否推薦關聯
    reasoning: str = ""                # 排序推理說明

class CandidateRanker:
    """候選排序器 - 統一的關聯排序和優先級調整"""
    
    def __init__(self, 
                 caption_detector: Optional[CaptionDetector] = None,
                 semantic_analyzer: Optional[SemanticAnalyzer] = None):
        """
        初始化候選排序器
        
        Args:
            caption_detector: Caption檢測器實例
            semantic_analyzer: 語義分析器實例
        """
        self.caption_detector = caption_detector or CaptionDetector()
        self.semantic_analyzer = semantic_analyzer or SemanticAnalyzer()
        
        # 預設權重配置
        self.default_weights = {
            'spatial': 0.35,      # 空間分析權重
            'caption': 0.40,      # Caption檢測權重（最重要）
            'semantic': 0.25      # 語義分析權重
        }
        
        # 質量閾值
        self.quality_thresholds = {
            AssociationQuality.EXCELLENT: 0.8,
            AssociationQuality.GOOD: 0.6,
            AssociationQuality.FAIR: 0.4,
            AssociationQuality.POOR: 0.2,
            AssociationQuality.VERY_POOR: 0.0
        }
        
        logger.info("候選排序器初始化完成")
    
    def rank_candidates(self, 
                       text_candidates: List[Dict[str, Any]], 
                       image_bbox: BoundingBox,
                       image_content: Optional[str] = None,
                       context_info: Optional[Dict[str, Any]] = None) -> List[RankedCandidate]:
        """
        對候選文本進行關聯排序
        
        Args:
            text_candidates: 候選文本列表，格式：[{'id': str, 'content': str, 'bbox': BoundingBox}, ...]
            image_bbox: 圖片邊界框
            image_content: 圖片內容描述（可選，用於語義分析）
            context_info: 上下文信息（文檔類型、佈局信息等）
            
        Returns:
            List[RankedCandidate]: 排序後的候選列表
        """
        if not text_candidates:
            return []
        
        logger.debug(f"開始對 {len(text_candidates)} 個候選文本進行排序")
        
        # 1. 文檔類型識別和權重調整
        doc_weights = self._get_document_weights(text_candidates, context_info)
        
        # 2. 對每個候選進行全面評分
        scored_candidates = []
        for candidate in text_candidates:
            candidate_score = self._score_candidate(
                candidate, image_bbox, image_content, context_info, doc_weights
            )
            
            ranked_candidate = RankedCandidate(
                text_id=candidate.get('id', ''),
                text_content=candidate.get('content', ''),
                text_bbox=candidate.get('bbox'),
                scores=candidate_score
            )
            
            scored_candidates.append(ranked_candidate)
        
        # 3. 排序和優先級調整
        final_ranked = self._apply_ranking_and_priority(scored_candidates, image_bbox, context_info)
        
        # 4. 生成推理說明
        self._generate_reasoning_explanations(final_ranked)
        
        logger.debug(f"候選排序完成，推薦關聯數量: {sum(1 for c in final_ranked if c.is_recommended)}")
        
        return final_ranked
    
    def _get_document_weights(self, 
                            text_candidates: List[Dict[str, Any]], 
                            context_info: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """獲取基於文檔類型的權重配置"""
        
        if context_info and 'document_type' in context_info:
            doc_type = context_info['document_type']
            if isinstance(doc_type, str):
                try:
                    doc_type = DocumentType(doc_type)
                except ValueError:
                    doc_type = DocumentType.UNKNOWN
        else:
            # 自動識別文檔類型
            all_elements = text_candidates.copy()
            if context_info and 'all_elements' in context_info:
                all_elements = context_info['all_elements']
            
            doc_type_result = identify_document_type(all_elements)
            doc_type = doc_type_result['document_type']
        
        # 獲取文檔類型特定的權重
        type_weights = get_document_type_weights(doc_type)
        
        # 轉換為我們的權重格式
        spatial_weight = (type_weights.get('vertical', 0.4) + 
                         type_weights.get('horizontal', 0.25) + 
                         type_weights.get('distance', 0.2) + 
                         type_weights.get('alignment', 0.1))
        
        weights = {
            'spatial': min(0.6, max(0.2, spatial_weight)),  # 限制範圍
            'caption': 0.4 * type_weights.get('caption_boost_factor', 1.0),
            'semantic': self.default_weights['semantic']
        }
        
        # 重新歸一化權重
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        else:
            weights = self.default_weights
        
        logger.debug(f"文檔類型: {doc_type.value}, 調整後權重: {weights}")
        return weights
    
    def _score_candidate(self, 
                        candidate: Dict[str, Any], 
                        image_bbox: BoundingBox,
                        image_content: Optional[str],
                        context_info: Optional[Dict[str, Any]],
                        weights: Dict[str, float]) -> CandidateScore:
        """對單個候選進行全面評分"""
        
        text_content = candidate.get('content', '')
        text_bbox = candidate.get('bbox')
        text_id = candidate.get('id', '')
        
        if not text_bbox:
            return CandidateScore()
        
        # 1. 空間分析評分（使用增強算法）
        spatial_result = enhanced_spatial_scoring(text_bbox, image_bbox, context_info)
        
        # 2. Caption檢測評分
        caption_matches = self.caption_detector.detect_captions(text_content, text_bbox, image_bbox)
        caption_score = max([match.confidence for match in caption_matches], default=0.0)
        
        # 3. 語義相似度評分
        semantic_score = 0.0
        if image_content and self.semantic_analyzer:
            try:
                semantic_score = self.semantic_analyzer.calculate_similarity(text_content, image_content)
            except Exception as e:
                logger.warning(f"語義分析失敗: {e}")
        
        # 4. 計算最終分數
        spatial_weighted = spatial_result.get('final_score', 0.0) * weights['spatial']
        caption_weighted = caption_score * weights['caption']
        semantic_weighted = semantic_score * weights['semantic']
        
        final_score = spatial_weighted + caption_weighted + semantic_weighted
        
        # 5. 確定質量等級
        quality = self._determine_quality(final_score)
        
        # 6. 計算置信度
        confidence = self._calculate_confidence(spatial_result, caption_score, semantic_score)
        
        return CandidateScore(
            spatial_score=spatial_result.get('final_score', 0.0),
            caption_score=caption_score,
            semantic_score=semantic_score,
            vertical_score=spatial_result.get('component_scores', {}).get('vertical', 0.0),
            horizontal_score=spatial_result.get('component_scores', {}).get('horizontal', 0.0),
            distance_score=spatial_result.get('component_scores', {}).get('distance', 0.0),
            alignment_score=spatial_result.get('component_scores', {}).get('alignment', 0.0),
            layout_penalty=spatial_result.get('component_scores', {}).get('layout_penalty', 1.0),
            intervening_penalty=spatial_result.get('component_scores', {}).get('intervening_penalty', 1.0),
            priority_boost=1.0,  # 在後續優先級調整中設置
            final_score=final_score,
            quality=quality,
            confidence=confidence
        )
    
    def _apply_ranking_and_priority(self, 
                                  candidates: List[RankedCandidate], 
                                  image_bbox: BoundingBox,
                                  context_info: Optional[Dict[str, Any]]) -> List[RankedCandidate]:
        """應用排序和優先級調整"""
        
        # 1. 基礎排序（按最終分數）
        candidates.sort(key=lambda x: x.scores.final_score, reverse=True)
        
        # 2. 應用Caption優先規則
        candidates = self._apply_caption_priority_boost(candidates, image_bbox)
        
        # 3. 應用距離優先規則
        candidates = self._apply_distance_priority_rules(candidates, image_bbox)
        
        # 4. 重新排序
        candidates.sort(key=lambda x: x.scores.final_score, reverse=True)
        
        # 5. 設置排名和推薦標記
        for i, candidate in enumerate(candidates, 1):
            candidate.rank = i
            # 推薦標準：排名前3且質量不低於FAIR
            candidate.is_recommended = (
                i <= 3 and 
                candidate.scores.quality in [AssociationQuality.EXCELLENT, AssociationQuality.GOOD, AssociationQuality.FAIR]
            )
        
        return candidates
    
    def _apply_caption_priority_boost(self, 
                                    candidates: List[RankedCandidate], 
                                    image_bbox: BoundingBox) -> List[RankedCandidate]:
        """應用Caption優先級提升"""
        
        # 找出有Caption的候選
        caption_candidates = [c for c in candidates if c.scores.caption_score > 0.3]
        
        if not caption_candidates:
            return candidates
        
        # 按Caption分數和位置關係排序
        for candidate in caption_candidates:
            text_bbox = candidate.text_bbox
            
            # 檢查是否在圖片上方且距離合理
            if (text_bbox.bottom <= image_bbox.top and 
                (image_bbox.top - text_bbox.bottom) <= image_bbox.height * 2):
                
                # 上方Caption獲得額外加分
                boost_factor = 1.2
                candidate.scores.priority_boost *= boost_factor
                candidate.scores.final_score *= boost_factor
                
                logger.debug(f"Caption優先級提升: {candidate.text_content[:20]}... (+{(boost_factor-1)*100:.0f}%)")
        
        return candidates
    
    def _apply_distance_priority_rules(self, 
                                     candidates: List[RankedCandidate], 
                                     image_bbox: BoundingBox) -> List[RankedCandidate]:
        """應用距離優先規則"""
        
        # 計算每個候選的距離
        for candidate in candidates:
            text_bbox = candidate.text_bbox
            center_distance = np.sqrt(
                (text_bbox.center_x - image_bbox.center_x) ** 2 + 
                (text_bbox.center_y - image_bbox.center_y) ** 2
            )
            
            # 對於非常近的候選（1倍圖片高度內），給予小幅加分
            if center_distance <= image_bbox.height:
                proximity_boost = 1.1
                candidate.scores.priority_boost *= proximity_boost
                candidate.scores.final_score *= proximity_boost
                
                logger.debug(f"距離優先級提升: {candidate.text_content[:20]}... (+{(proximity_boost-1)*100:.0f}%)")
        
        return candidates
    
    def _determine_quality(self, final_score: float) -> AssociationQuality:
        """確定關聯質量等級"""
        
        if final_score >= self.quality_thresholds[AssociationQuality.EXCELLENT]:
            return AssociationQuality.EXCELLENT
        elif final_score >= self.quality_thresholds[AssociationQuality.GOOD]:
            return AssociationQuality.GOOD
        elif final_score >= self.quality_thresholds[AssociationQuality.FAIR]:
            return AssociationQuality.FAIR
        elif final_score >= self.quality_thresholds[AssociationQuality.POOR]:
            return AssociationQuality.POOR
        else:
            return AssociationQuality.VERY_POOR
    
    def _calculate_confidence(self, 
                            spatial_result: Dict[str, Any], 
                            caption_score: float, 
                            semantic_score: float) -> float:
        """計算關聯置信度"""
        
        # 基於多個指標的置信度計算
        spatial_confidence = min(1.0, spatial_result.get('final_score', 0.0) * 1.2)
        caption_confidence = min(1.0, caption_score * 1.5)
        semantic_confidence = min(1.0, semantic_score * 1.0)
        
        # 加權平均
        confidence = (spatial_confidence * 0.4 + 
                     caption_confidence * 0.4 + 
                     semantic_confidence * 0.2)
        
        return min(1.0, confidence)
    
    def _generate_reasoning_explanations(self, candidates: List[RankedCandidate]) -> None:
        """生成排序推理說明"""
        
        for candidate in candidates:
            reasoning_parts = []
            scores = candidate.scores
            
            # 主要評分來源
            if scores.caption_score > 0.3:
                reasoning_parts.append(f"Caption檢測 ({scores.caption_score:.2f})")
            
            if scores.spatial_score > 0.3:
                reasoning_parts.append(f"空間關係 ({scores.spatial_score:.2f})")
            
            if scores.semantic_score > 0.2:
                reasoning_parts.append(f"語義相似 ({scores.semantic_score:.2f})")
            
            # 特殊加分或懲罰
            if scores.priority_boost > 1.0:
                reasoning_parts.append(f"優先級提升 (+{(scores.priority_boost-1)*100:.0f}%)")
            
            if scores.layout_penalty < 1.0:
                reasoning_parts.append(f"佈局懲罰 (-{(1-scores.layout_penalty)*100:.0f}%)")
            
            # 質量評估
            quality_desc = {
                AssociationQuality.EXCELLENT: "優秀關聯",
                AssociationQuality.GOOD: "良好關聯",
                AssociationQuality.FAIR: "一般關聯",
                AssociationQuality.POOR: "較差關聯",
                AssociationQuality.VERY_POOR: "很差關聯"
            }
            
            reasoning = f"{quality_desc[scores.quality]} - " + "; ".join(reasoning_parts)
            candidate.reasoning = reasoning

def rank_image_text_associations(text_candidates: List[Dict[str, Any]], 
                                image_bbox: BoundingBox,
                                image_content: Optional[str] = None,
                                context_info: Optional[Dict[str, Any]] = None) -> List[RankedCandidate]:
    """
    便捷函數：對圖文關聯候選進行排序
    
    Args:
        text_candidates: 候選文本列表
        image_bbox: 圖片邊界框
        image_content: 圖片內容描述（可選）
        context_info: 上下文信息（可選）
        
    Returns:
        List[RankedCandidate]: 排序後的候選列表
    """
    ranker = CandidateRanker()
    return ranker.rank_candidates(text_candidates, image_bbox, image_content, context_info)

