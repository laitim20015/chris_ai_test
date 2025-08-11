"""
關聯優化器
Association Optimizer

解決過度關聯問題，提供智能的關聯去重和過濾機制。
包含多種優化策略：
1. 基於閾值的過濾
2. 每張圖片的最大關聯數限制
3. 關聯質量評估
4. 重複關聯去重
5. 距離和語義相似度聚類
"""

from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import math
from collections import defaultdict

from src.config.logging_config import get_logger

logger = get_logger("association_optimizer")

class AssociationQuality(Enum):
    """關聯質量等級"""
    EXCELLENT = "excellent"    # 0.8+
    GOOD = "good"             # 0.6-0.8
    FAIR = "fair"             # 0.4-0.6
    POOR = "poor"             # 0.2-0.4
    INVALID = "invalid"       # <0.2

@dataclass
class OptimizationConfig:
    """優化配置"""
    # 基本閾值
    min_score_threshold: float = 0.4           # 最低關聯分數
    excellent_threshold: float = 0.8           # 優秀關聯分數
    good_threshold: float = 0.6                # 良好關聯分數
    fair_threshold: float = 0.4                # 一般關聯分數
    
    # 數量限制
    max_associations_per_image: int = 5        # 每張圖片最大關聯數
    max_total_associations: int = 100          # 總最大關聯數
    
    # Caption特殊處理
    caption_boost_factor: float = 1.2          # Caption檢測加成係數
    caption_min_confidence: float = 0.5       # Caption最低置信度
    
    # 去重配置
    enable_deduplication: bool = True          # 啟用去重
    similarity_threshold: float = 0.9          # 相似關聯合併閾值
    
    # 質量優先
    prioritize_quality: bool = True            # 優先保留高質量關聯
    quality_boost_factor: float = 1.1         # 質量加成係數

class AssociationOptimizer:
    """關聯優化器"""
    
    def __init__(self, config: OptimizationConfig = None):
        """
        初始化優化器
        
        Args:
            config: 優化配置
        """
        self.config = config or OptimizationConfig()
        self.logger = logger
        
        self.logger.info("關聯優化器初始化完成")
    
    def optimize_associations(self, 
                            associations: List[Dict[str, Any]],
                            images: List[Any] = None,
                            text_blocks: List[Any] = None) -> List[Dict[str, Any]]:
        """
        優化關聯列表
        
        Args:
            associations: 原始關聯列表
            images: 圖片列表（可選，用於額外驗證）
            text_blocks: 文本塊列表（可選，用於額外驗證）
            
        Returns:
            優化後的關聯列表
        """
        self.logger.info(f"🔧 開始關聯優化，原始關聯數: {len(associations)}")
        
        if not associations:
            return []
        
        # 步驟1: 基本過濾
        filtered_associations = self._filter_by_threshold(associations)
        self.logger.info(f"📊 閾值過濾後: {len(filtered_associations)} 個關聯")
        
        # 步驟2: 質量評估和分級
        graded_associations = self._grade_associations(filtered_associations)
        self.logger.info(f"📈 質量評估完成")
        
        # 步驟3: Caption檢測加成
        boosted_associations = self._apply_caption_boost(graded_associations)
        self.logger.info(f"🎯 Caption加成處理完成")
        
        # 步驟4: 去重處理
        if self.config.enable_deduplication:
            deduplicated_associations = self._deduplicate_associations(boosted_associations)
            self.logger.info(f"🔄 去重處理後: {len(deduplicated_associations)} 個關聯")
        else:
            deduplicated_associations = boosted_associations
        
        # 步驟5: 按圖片限制關聯數
        limited_associations = self._limit_associations_per_image(deduplicated_associations)
        self.logger.info(f"🎚️ 數量限制後: {len(limited_associations)} 個關聯")
        
        # 步驟6: 總數控制
        final_associations = self._limit_total_associations(limited_associations)
        self.logger.info(f"✅ 最終優化結果: {len(final_associations)} 個關聯")
        
        # 統計報告
        self._generate_optimization_report(associations, final_associations)
        
        return final_associations
    
    def _filter_by_threshold(self, associations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基本閾值過濾"""
        filtered = []
        
        for assoc in associations:
            final_score = assoc.get("final_score", 0.0)
            
            if final_score >= self.config.min_score_threshold:
                filtered.append(assoc)
            else:
                self.logger.debug(f"過濾低分關聯: {final_score:.3f}")
        
        return filtered
    
    def _grade_associations(self, associations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """關聯質量評估和分級"""
        graded = []
        
        for assoc in associations.copy():
            final_score = assoc.get("final_score", 0.0)
            
            # 確定質量等級
            if final_score >= self.config.excellent_threshold:
                quality = AssociationQuality.EXCELLENT
            elif final_score >= self.config.good_threshold:
                quality = AssociationQuality.GOOD
            elif final_score >= self.config.fair_threshold:
                quality = AssociationQuality.FAIR
            else:
                quality = AssociationQuality.POOR
            
            # 添加質量信息
            assoc["quality"] = quality.value
            assoc["quality_enum"] = quality
            
            # 質量加成
            if self.config.prioritize_quality and quality in [AssociationQuality.EXCELLENT, AssociationQuality.GOOD]:
                assoc["adjusted_score"] = final_score * self.config.quality_boost_factor
            else:
                assoc["adjusted_score"] = final_score
            
            graded.append(assoc)
        
        return graded
    
    def _apply_caption_boost(self, associations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Caption檢測加成處理"""
        boosted = []
        
        for assoc in associations.copy():
            caption_score = assoc.get("caption_score", 0.0)
            
            # Caption檢測加成
            if caption_score >= self.config.caption_min_confidence:
                boost_factor = self.config.caption_boost_factor
                assoc["adjusted_score"] = assoc.get("adjusted_score", assoc["final_score"]) * boost_factor
                assoc["caption_boosted"] = True
                # 同步更新關聯類型為caption，確保輸出一致性
                assoc["association_type"] = "caption"
                
                self.logger.debug(f"Caption加成: {assoc['final_score']:.3f} -> {assoc['adjusted_score']:.3f}")
            else:
                assoc["caption_boosted"] = False
            
            boosted.append(assoc)
        
        return boosted
    
    def _deduplicate_associations(self, associations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """關聯去重處理"""
        if len(associations) <= 1:
            return associations
        
        # 按調整後分數排序
        sorted_associations = sorted(associations, key=lambda x: x.get("adjusted_score", x["final_score"]), reverse=True)
        
        deduplicated = []
        used_combinations: Set[Tuple[str, str]] = set()
        
        for assoc in sorted_associations:
            text_id = assoc.get("text_block_id", "")
            image_id = assoc.get("image_id", "")
            
            combination = (text_id, image_id)
            
            # 檢查是否已存在相同組合
            if combination not in used_combinations:
                deduplicated.append(assoc)
                used_combinations.add(combination)
            else:
                self.logger.debug(f"去重: 重複組合 {text_id} <-> {image_id}")
        
        return deduplicated
    
    def _limit_associations_per_image(self, associations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """限制每張圖片的關聯數"""
        # 按圖片分組
        image_groups = defaultdict(list)
        
        for assoc in associations:
            image_id = assoc.get("image_id", "")
            image_groups[image_id].append(assoc)
        
        limited = []
        
        for image_id, image_associations in image_groups.items():
            # 按調整後分數排序
            sorted_assocs = sorted(
                image_associations, 
                key=lambda x: x.get("adjusted_score", x["final_score"]), 
                reverse=True
            )
            
            # 限制數量
            kept_count = min(len(sorted_assocs), self.config.max_associations_per_image)
            kept_associations = sorted_assocs[:kept_count]
            
            limited.extend(kept_associations)
            
            if len(sorted_assocs) > kept_count:
                self.logger.debug(f"圖片 {image_id} 關聯限制: {len(sorted_assocs)} -> {kept_count}")
        
        return limited
    
    def _limit_total_associations(self, associations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """總關聯數控制"""
        if len(associations) <= self.config.max_total_associations:
            return associations
        
        # 按調整後分數排序
        sorted_associations = sorted(
            associations, 
            key=lambda x: x.get("adjusted_score", x["final_score"]), 
            reverse=True
        )
        
        limited = sorted_associations[:self.config.max_total_associations]
        
        self.logger.info(f"總數限制: {len(associations)} -> {len(limited)}")
        
        return limited
    
    def _generate_optimization_report(self, 
                                    original: List[Dict[str, Any]], 
                                    optimized: List[Dict[str, Any]]):
        """生成優化報告"""
        original_count = len(original)
        optimized_count = len(optimized)
        reduction_rate = (original_count - optimized_count) / max(original_count, 1) * 100
        
        # 質量分布統計
        quality_stats = defaultdict(int)
        for assoc in optimized:
            quality = assoc.get("quality", "unknown")
            quality_stats[quality] += 1
        
        # Caption檢測統計
        caption_boosted = sum(1 for assoc in optimized if assoc.get("caption_boosted", False))
        
        self.logger.info("📊 關聯優化報告:")
        self.logger.info(f"  📉 關聯數變化: {original_count} -> {optimized_count}")
        self.logger.info(f"  📈 優化率: {reduction_rate:.1f}%")
        self.logger.info(f"  🎯 Caption加成: {caption_boosted}/{optimized_count}")
        self.logger.info(f"  📈 質量分布:")
        
        for quality, count in quality_stats.items():
            percentage = count / max(optimized_count, 1) * 100
            self.logger.info(f"    {quality}: {count} ({percentage:.1f}%)")
    
    def get_optimization_metrics(self, 
                                original: List[Dict[str, Any]], 
                                optimized: List[Dict[str, Any]]) -> Dict[str, Any]:
        """獲取優化指標"""
        if not original:
            return {"error": "沒有原始關聯數據"}
        
        original_count = len(original)
        optimized_count = len(optimized)
        
        # 分數統計
        original_scores = [assoc.get("final_score", 0.0) for assoc in original]
        optimized_scores = [assoc.get("final_score", 0.0) for assoc in optimized]
        
        original_avg = sum(original_scores) / max(len(original_scores), 1)
        optimized_avg = sum(optimized_scores) / max(len(optimized_scores), 1)
        
        # 質量分布
        quality_distribution = defaultdict(int)
        for assoc in optimized:
            quality = assoc.get("quality", "unknown")
            quality_distribution[quality] += 1
        
        return {
            "original_count": original_count,
            "optimized_count": optimized_count,
            "reduction_count": original_count - optimized_count,
            "reduction_rate": (original_count - optimized_count) / max(original_count, 1) * 100,
            "original_avg_score": original_avg,
            "optimized_avg_score": optimized_avg,
            "quality_improvement": optimized_avg - original_avg,
            "quality_distribution": dict(quality_distribution),
            "caption_boosted_count": sum(1 for assoc in optimized if assoc.get("caption_boosted", False))
        }

# 便捷函數
def optimize_associations(associations: List[Dict[str, Any]], 
                         config: OptimizationConfig = None) -> List[Dict[str, Any]]:
    """
    優化關聯列表（便捷函數）
    
    Args:
        associations: 原始關聯列表
        config: 優化配置
        
    Returns:
        優化後的關聯列表
    """
    optimizer = AssociationOptimizer(config)
    return optimizer.optimize_associations(associations)

def create_strict_config() -> OptimizationConfig:
    """創建嚴格的優化配置"""
    return OptimizationConfig(
        min_score_threshold=0.5,
        max_associations_per_image=3,
        max_total_associations=50,
        caption_min_confidence=0.6,
        prioritize_quality=True
    )

def create_balanced_config() -> OptimizationConfig:
    """創建平衡的優化配置"""
    return OptimizationConfig(
        min_score_threshold=0.4,
        max_associations_per_image=5,
        max_total_associations=100,
        caption_min_confidence=0.5,
        prioritize_quality=True
    )

def create_lenient_config() -> OptimizationConfig:
    """創建寬鬆的優化配置"""
    return OptimizationConfig(
        min_score_threshold=0.3,
        max_associations_per_image=8,
        max_total_associations=200,
        caption_min_confidence=0.4,
        prioritize_quality=False
    )
