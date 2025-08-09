"""
關聯度評分器 - 圖文關聯分析的最終評分模組
Association Scorer - Final Scoring Module for Image-Text Association Analysis

這是關聯分析的核心評分模組，負責整合所有分析結果並生成最終的關聯度評分。
嚴格按照項目規則的權重配置進行加權融合：

權重配置（必須嚴格遵循）：
- Caption檢測：40% （最高權重）
- 空間關係：30%
- 語義相似度：15%
- 佈局模式：10%
- 距離計算：5%

總權重必須等於1.0，且Caption權重必須最高。
"""

from typing import List, Dict, Tuple, Optional, NamedTuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
from src.association.caption_detector import CaptionMatch, calculate_caption_score
from src.association.spatial_analyzer import SpatialFeatures, calculate_spatial_score
from src.association.semantic_analyzer import SemanticSimilarity, calculate_semantic_score
from src.association.allen_logic import SpatialRelation
from src.config.logging_config import get_logger, log_performance

logger = get_logger("association_scorer")

@dataclass
class WeightConfig:
    """權重配置類"""
    caption_weight: float = 0.4      # Caption檢測權重（最高）
    spatial_weight: float = 0.3      # 空間關係權重
    semantic_weight: float = 0.15    # 語義相似度權重
    layout_weight: float = 0.1       # 佈局模式權重
    proximity_weight: float = 0.05   # 距離權重
    
    def __post_init__(self):
        """驗證權重配置"""
        total = (self.caption_weight + self.spatial_weight + self.semantic_weight + 
                self.layout_weight + self.proximity_weight)
        
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"權重總和必須為1.0，當前為: {total}")
        
        # 檢查Caption權重是否最高
        max_weight = max(self.caption_weight, self.spatial_weight, self.semantic_weight,
                        self.layout_weight, self.proximity_weight)
        if self.caption_weight != max_weight:
            raise ValueError("Caption權重必須為最高（項目規則要求）")

class AssociationLevel(Enum):
    """關聯度等級"""
    VERY_HIGH = "very_high"          # 非常高 (0.8-1.0)
    HIGH = "high"                    # 高 (0.6-0.8)
    MEDIUM = "medium"                # 中等 (0.4-0.6)
    LOW = "low"                      # 低 (0.2-0.4)
    VERY_LOW = "very_low"           # 非常低 (0.0-0.2)

@dataclass
class AssociationResult:
    """關聯分析結果"""
    
    # 基本信息
    text_id: str                     # 文本ID
    image_id: str                    # 圖片ID
    
    # 各項評分
    caption_score: float             # Caption評分 (40%權重)
    spatial_score: float             # 空間關係評分 (30%權重)
    semantic_score: float            # 語義相似度評分 (15%權重)
    layout_score: float              # 佈局模式評分 (10%權重)
    proximity_score: float           # 距離評分 (5%權重)
    
    # 最終結果
    final_score: float               # 最終關聯度評分
    confidence: float                # 置信度
    association_level: AssociationLevel  # 關聯度等級
    
    # 詳細信息
    caption_matches: List[CaptionMatch]      # Caption匹配詳情
    spatial_features: SpatialFeatures       # 空間特徵
    semantic_similarity: SemanticSimilarity # 語義相似度詳情
    
    # 元數據
    processing_time: float           # 處理時間（秒）
    algorithm_version: str           # 算法版本

class AssociationScorer:
    """關聯度評分器"""
    
    def __init__(self, weights: Optional[WeightConfig] = None):
        """
        初始化評分器
        
        Args:
            weights: 權重配置，如果為None則使用默認配置
        """
        self.weights = weights if weights is not None else WeightConfig()
        self.algorithm_version = "1.0.0"
        
        logger.info(f"關聯度評分器初始化完成")
        logger.info(f"權重配置: Caption={self.weights.caption_weight}, "
                   f"Spatial={self.weights.spatial_weight}, "
                   f"Semantic={self.weights.semantic_weight}, "
                   f"Layout={self.weights.layout_weight}, "
                   f"Proximity={self.weights.proximity_weight}")
    
    @log_performance("calculate_association_score")
    def calculate_association_score(self,
                                  text_id: str,
                                  image_id: str,
                                  caption_matches: List[CaptionMatch],
                                  spatial_features: SpatialFeatures,
                                  spatial_relation: SpatialRelation,
                                  semantic_similarity: SemanticSimilarity,
                                  text_content: str = "",
                                  processing_time: float = 0.0) -> AssociationResult:
        """
        計算最終的關聯度評分
        
        Args:
            text_id: 文本ID
            image_id: 圖片ID
            caption_matches: Caption匹配結果
            spatial_features: 空間特徵
            spatial_relation: Allen邏輯空間關係
            semantic_similarity: 語義相似度
            text_content: 文本內容
            processing_time: 處理時間
            
        Returns:
            AssociationResult: 關聯分析結果
        """
        # 1. 計算各項評分
        caption_score = self._calculate_caption_score(caption_matches)
        spatial_score = self._calculate_spatial_score(spatial_features, spatial_relation)
        semantic_score = self._calculate_semantic_score(semantic_similarity)
        layout_score = self._calculate_layout_score(spatial_features)
        proximity_score = self._calculate_proximity_score(spatial_features)
        
        # 2. 計算加權最終評分
        final_score = (
            caption_score * self.weights.caption_weight +
            spatial_score * self.weights.spatial_weight +
            semantic_score * self.weights.semantic_weight +
            layout_score * self.weights.layout_weight +
            proximity_score * self.weights.proximity_weight
        )
        
        # 3. 計算置信度
        confidence = self._calculate_confidence(
            caption_matches, spatial_features, spatial_relation, semantic_similarity
        )
        
        # 4. 確定關聯度等級
        association_level = self._determine_association_level(final_score)
        
        # 5. 構建結果
        result = AssociationResult(
            text_id=text_id,
            image_id=image_id,
            caption_score=caption_score,
            spatial_score=spatial_score,
            semantic_score=semantic_score,
            layout_score=layout_score,
            proximity_score=proximity_score,
            final_score=final_score,
            confidence=confidence,
            association_level=association_level,
            caption_matches=caption_matches,
            spatial_features=spatial_features,
            semantic_similarity=semantic_similarity,
            processing_time=processing_time,
            algorithm_version=self.algorithm_version
        )
        
        logger.debug(f"關聯度評分完成: {text_id} <-> {image_id}, 最終評分: {final_score:.3f}")
        
        return result
    
    def calculate_simple_score(self, 
                             caption_score: float = 0.0,
                             spatial_score: float = 0.0, 
                             semantic_score: float = 0.0,
                             layout_score: float = 0.0,
                             proximity_score: float = 0.0) -> Tuple[float, Dict]:
        """
        簡化的評分計算方法（用於測試和快速評分）
        
        Args:
            caption_score: Caption檢測評分
            spatial_score: 空間關係評分
            semantic_score: 語義相似度評分
            layout_score: 佈局模式評分
            proximity_score: 距離評分
            
        Returns:
            Tuple[float, Dict]: (最終評分, 詳細信息)
        """
        weights = self.weights
        
        final_score = (
            weights.caption_weight * caption_score +
            weights.spatial_weight * spatial_score +
            weights.semantic_weight * semantic_score +
            weights.layout_weight * layout_score +
            weights.proximity_weight * proximity_score
        )
        
        details = {
            "caption_score": caption_score,
            "spatial_score": spatial_score,
            "semantic_score": semantic_score,
            "layout_score": layout_score,
            "proximity_score": proximity_score,
            "weights": {
                "caption": weights.caption_weight,
                "spatial": weights.spatial_weight,
                "semantic": weights.semantic_weight,
                "layout": weights.layout_weight,
                "proximity": weights.proximity_weight
            },
            "final_score": final_score
        }
        
        return final_score, details
    
    def _calculate_caption_score(self, caption_matches: List[CaptionMatch]) -> float:
        """計算Caption評分（40%權重）"""
        if not caption_matches:
            return 0.0
        
        # 使用最高置信度的匹配
        best_match = max(caption_matches, key=lambda x: x.confidence)
        
        # 根據Caption類型調整分數
        from src.association.caption_detector import CaptionType
        
        type_weights = {
            CaptionType.FIGURE_NUMBER: 1.0,    # 圖片編號最重要
            CaptionType.TABLE_NUMBER: 1.0,     # 表格編號同等重要
            CaptionType.REFERENCE: 0.9,        # 引用略低
            CaptionType.CHART_DIAGRAM: 0.95,   # 圖表類型較重要
            CaptionType.DESCRIPTION: 0.8,      # 描述性文字
            CaptionType.TITLE: 0.85,          # 標題
            CaptionType.UNKNOWN: 0.7          # 未知類型
        }
        
        type_weight = type_weights.get(best_match.caption_type, 0.7)
        
        # 位置調整
        from src.association.caption_detector import CaptionPosition
        
        position_weights = {
            CaptionPosition.ABOVE: 1.1,        # 上方位置加分
            CaptionPosition.BELOW: 1.2,        # 下方位置最佳
            CaptionPosition.LEFT: 0.9,         # 左側略低
            CaptionPosition.RIGHT: 0.9,        # 右側略低
            CaptionPosition.INSIDE: 0.8,       # 內部較低
            CaptionPosition.DISTANT: 0.6,      # 遠距離扣分
            CaptionPosition.UNKNOWN: 0.8       # 未知位置
        }
        
        position_weight = position_weights.get(best_match.position, 0.8)
        
        caption_score = best_match.confidence * type_weight * position_weight
        return min(1.0, caption_score)
    
    def _calculate_spatial_score(self, spatial_features: SpatialFeatures, 
                               spatial_relation: SpatialRelation) -> float:
        """計算空間關係評分（30%權重）"""
        base_score = spatial_relation.confidence
        
        # 對齊加分
        alignment_bonus = spatial_features.alignment_score * 0.2
        
        # 距離調整
        distance_factor = 1.0
        if spatial_features.center_distance > 0:
            # 標準化距離，距離越遠評分越低
            distance_factor = max(0.3, 1.0 - spatial_features.center_distance * 0.1)
        
        # 重疊調整
        overlap_factor = 1.0
        if spatial_features.overlap_ratio > 0:
            # 適度重疊是好的
            if spatial_features.overlap_ratio <= 0.3:
                overlap_factor = 1.0 + spatial_features.overlap_ratio * 0.2
            else:
                overlap_factor = 1.0  # 過度重疊不加分
        
        spatial_score = (base_score + alignment_bonus) * distance_factor * overlap_factor
        return min(1.0, spatial_score)
    
    def _calculate_semantic_score(self, semantic_similarity: SemanticSimilarity) -> float:
        """計算語義相似度評分（15%權重）"""
        return semantic_similarity.similarity_score * semantic_similarity.confidence
    
    def _calculate_layout_score(self, spatial_features: SpatialFeatures) -> float:
        """計算佈局模式評分（10%權重）"""
        layout_score = 0.5  # 基礎分數
        
        # 同行/同列加分
        if spatial_features.same_row:
            layout_score += 0.2
        if spatial_features.same_column:
            layout_score += 0.15
        
        # 閱讀順序加分
        layout_score += spatial_features.reading_order_score * 0.3
        
        return min(1.0, layout_score)
    
    def _calculate_proximity_score(self, spatial_features: SpatialFeatures) -> float:
        """計算距離評分（5%權重）"""
        # 距離越近評分越高
        if spatial_features.center_distance == 0:
            return 1.0
        
        # 使用標準化距離計算評分
        proximity_score = max(0.1, 1.0 - spatial_features.center_distance * 0.1)
        
        return proximity_score
    
    def _calculate_confidence(self, caption_matches: List[CaptionMatch],
                            spatial_features: SpatialFeatures,
                            spatial_relation: SpatialRelation,
                            semantic_similarity: SemanticSimilarity) -> float:
        """計算整體置信度"""
        confidences = []
        
        # Caption置信度
        if caption_matches:
            max_caption_conf = max(match.confidence for match in caption_matches)
            confidences.append(max_caption_conf)
        else:
            confidences.append(0.5)  # 無Caption時的基礎置信度
        
        # 空間關係置信度
        confidences.append(spatial_relation.confidence)
        
        # 語義相似度置信度
        confidences.append(semantic_similarity.confidence)
        
        # 使用加權平均
        weights = [0.5, 0.3, 0.2]  # Caption權重最高
        weighted_confidence = sum(c * w for c, w in zip(confidences, weights))
        
        return min(1.0, weighted_confidence)
    
    def _determine_association_level(self, score: float) -> AssociationLevel:
        """根據評分確定關聯度等級"""
        if score >= 0.8:
            return AssociationLevel.VERY_HIGH
        elif score >= 0.6:
            return AssociationLevel.HIGH
        elif score >= 0.4:
            return AssociationLevel.MEDIUM
        elif score >= 0.2:
            return AssociationLevel.LOW
        else:
            return AssociationLevel.VERY_LOW

def calculate_association_score(text_id: str, image_id: str,
                              caption_matches: List[CaptionMatch],
                              spatial_features: SpatialFeatures,
                              spatial_relation: SpatialRelation,
                              semantic_similarity: SemanticSimilarity,
                              weights: Optional[WeightConfig] = None) -> AssociationResult:
    """
    便捷的關聯度評分函數
    
    Args:
        text_id: 文本ID
        image_id: 圖片ID
        caption_matches: Caption匹配結果
        spatial_features: 空間特徵
        spatial_relation: 空間關係
        semantic_similarity: 語義相似度
        weights: 權重配置
        
    Returns:
        AssociationResult: 關聯分析結果
    """
    scorer = AssociationScorer(weights)
    return scorer.calculate_association_score(
        text_id, image_id, caption_matches, spatial_features,
        spatial_relation, semantic_similarity
    )

def rank_associations(results: List[AssociationResult], 
                     top_k: Optional[int] = None) -> List[AssociationResult]:
    """
    對關聯結果進行排序
    
    Args:
        results: 關聯結果列表
        top_k: 返回前K個結果，如果為None則返回全部
        
    Returns:
        List[AssociationResult]: 排序後的結果列表
    """
    # 按最終評分排序（降序）
    sorted_results = sorted(results, key=lambda x: x.final_score, reverse=True)
    
    if top_k is not None:
        sorted_results = sorted_results[:top_k]
    
    logger.info(f"關聯結果排序完成，共 {len(sorted_results)} 個結果")
    
    return sorted_results

def validate_weight_config(weights: Dict[str, float]) -> bool:
    """
    驗證權重配置是否符合項目規則
    
    Args:
        weights: 權重字典
        
    Returns:
        bool: 是否有效
    """
    try:
        # 檢查必需的權重字段
        required_fields = [
            'caption_score', 'spatial_score', 'semantic_score',
            'layout_score', 'proximity_score'
        ]
        
        for field in required_fields:
            if field not in weights:
                logger.error(f"缺少權重字段: {field}")
                return False
            
            if not isinstance(weights[field], (int, float)):
                logger.error(f"權重必須為數值: {field}")
                return False
            
            if weights[field] < 0 or weights[field] > 1:
                logger.error(f"權重必須在0-1範圍內: {field}")
                return False
        
        # 檢查權重總和
        total_weight = sum(weights[field] for field in required_fields)
        if abs(total_weight - 1.0) > 1e-6:
            logger.error(f"權重總和必須為1.0，當前為: {total_weight}")
            return False
        
        # 檢查Caption權重是否最高（項目規則）
        caption_weight = weights['caption_score']
        max_weight = max(weights[field] for field in required_fields)
        
        if caption_weight != max_weight:
            logger.error("Caption權重必須為最高（項目規則要求）")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"權重驗證失敗: {e}")
        return False

# 導出便捷函數
def quick_association_score(caption_score: float, spatial_score: float, 
                          semantic_score: float) -> float:
    """快速關聯度評分（使用默認權重）"""
    weights = WeightConfig()
    
    # 簡化計算（忽略layout和proximity）
    layout_score = 0.5
    proximity_score = 0.5
    
    final_score = (
        caption_score * weights.caption_weight +
        spatial_score * weights.spatial_weight +
        semantic_score * weights.semantic_weight +
        layout_score * weights.layout_weight +
        proximity_score * weights.proximity_weight
    )
    
    return min(1.0, final_score)

