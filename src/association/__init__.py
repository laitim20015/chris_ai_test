"""
圖文關聯分析模組
Image-Text Association Analysis Module

本模組是系統的核心，負責建立精準的圖文關聯關係，包括：

核心算法（按項目規則優先級）：
1. Caption檢測器 (40%權重) - 最關鍵的關聯指標
2. Allen區間邏輯空間關係分析 (30%權重) - 13種空間關係
3. 語義相似度分析 (15%權重) - 基於sentence-transformers
4. 佈局模式分析 (10%權重) - 版面結構識別
5. 距離計算 (5%權重) - 空間距離測量

嚴格遵循項目規則：
- Caption檢測權重必須最高（0.4）
- 使用Allen時間間隔邏輯的13種空間關係
- 總權重必須等於1.0
- 基於PyMuPDF解析的文檔結構進行分析

核心類和函數：
- AllenLogicAnalyzer: Allen區間邏輯實現
- CaptionDetector: Caption檢測器（最關鍵）
- SpatialAnalyzer: 空間關係分析器
- SemanticAnalyzer: 語義分析器
- AssociationScorer: 加權融合評分模型
"""

from src.association.allen_logic import (
    AllenLogicAnalyzer,
    SpatialRelation,
    IntervalRelation,
    analyze_spatial_relations,
    get_allen_relations_matrix
)

from src.association.caption_detector import (
    CaptionDetector,
    CaptionMatch,
    detect_image_captions,
    extract_caption_references,
    validate_caption_patterns
)

from src.association.spatial_analyzer import (
    SpatialAnalyzer,
    SpatialFeatures,
    BoundingBox,
    calculate_spatial_features,
    analyze_layout_patterns
)

from src.association.semantic_analyzer import (
    SemanticAnalyzer,
    SemanticSimilarity,
    extract_text_embeddings,
    compare_semantic_content
)

from src.association.association_scorer import (
    AssociationScorer,
    AssociationResult,
    WeightConfig,
    calculate_association_score,
    rank_associations,
    validate_weight_config
)

__all__ = [
    # Allen邏輯分析
    "AllenLogicAnalyzer",
    "SpatialRelation", 
    "IntervalRelation",
    "analyze_spatial_relations",
    "get_allen_relations_matrix",
    
    # Caption檢測（最高優先級）
    "CaptionDetector",
    "CaptionMatch",
    "detect_image_captions",
    "extract_caption_references",
    "validate_caption_patterns",
    
    # 空間分析
    "SpatialAnalyzer",
    "SpatialFeatures",
    "BoundingBox",
    "calculate_spatial_features", 
    "analyze_layout_patterns",
    
    # 語義分析
    "SemanticAnalyzer",
    "SemanticSimilarity",
    "extract_text_embeddings",
    "compare_semantic_content",
    
    # 關聯評分
    "AssociationScorer",
    "AssociationResult",
    "WeightConfig",
    "calculate_association_score",
    "rank_associations",
    "validate_weight_config",
]

# 模組版本和元數據
__version__ = "1.0.0"
__description__ = "智能圖文關聯分析核心模組"

# 算法優先級（嚴格按照項目規則）
ALGORITHM_PRIORITIES = {
    "caption_detection": 1,     # 最高優先級
    "allen_logic": 2,          # 高優先級  
    "spatial_analysis": 3,     # 高優先級
    "semantic_analysis": 4,    # 中等優先級
    "proximity_calculation": 5 # 低優先級
}

# 權重配置（必須嚴格遵循項目規則）
DEFAULT_WEIGHTS = {
    "caption_score": 0.4,      # Caption檢測權重（最高）
    "spatial_score": 0.3,      # 空間關係權重
    "semantic_score": 0.15,    # 語義相似度權重
    "layout_score": 0.1,       # 佈局模式權重
    "proximity_score": 0.05,   # 距離權重
}

# 驗證權重總和
assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-6, "權重總和必須為1.0"
assert DEFAULT_WEIGHTS["caption_score"] == max(DEFAULT_WEIGHTS.values()), "Caption權重必須最高"

def get_association_info() -> dict:
    """
    獲取關聯分析模組信息
    
    Returns:
        dict: 模組信息字典
    """
    return {
        "version": __version__,
        "description": __description__,
        "algorithm_priorities": ALGORITHM_PRIORITIES,
        "default_weights": DEFAULT_WEIGHTS,
        "allen_relations_count": 13,
        "supported_features": [
            "caption_detection",
            "spatial_analysis", 
            "semantic_similarity",
            "layout_patterns",
            "proximity_calculation"
        ]
    }

def validate_association_environment() -> bool:
    """
    驗證關聯分析模組環境
    
    Returns:
        bool: 環境是否有效
    """
    try:
        # 驗證必要的依賴
        import numpy as np
        import re
        from typing import List, Dict, Tuple, Optional
        
        # 驗證權重配置
        if not validate_weight_config(DEFAULT_WEIGHTS):
            return False
        
        return True
        
    except ImportError as e:
        print(f"關聯分析模組環境驗證失敗: {e}")
        return False

def get_optimized_weights(document_type: str = "general") -> dict:
    """
    根據文檔類型獲取優化的權重配置
    
    Args:
        document_type: 文檔類型 ("academic", "technical", "general")
        
    Returns:
        dict: 優化的權重配置
    """
    weight_profiles = {
        "academic": {
            "caption_score": 0.5,    # 學術文檔圖表標題更重要
            "spatial_score": 0.25,
            "semantic_score": 0.15,
            "layout_score": 0.08,
            "proximity_score": 0.02,
        },
        "technical": {
            "caption_score": 0.45,   # 技術文檔重視圖表說明
            "spatial_score": 0.3,
            "semantic_score": 0.15,
            "layout_score": 0.08,
            "proximity_score": 0.02,
        },
        "general": DEFAULT_WEIGHTS  # 使用默認權重
    }
    
    return weight_profiles.get(document_type, DEFAULT_WEIGHTS)

# 性能配置
PERFORMANCE_CONFIG = {
    "max_associations_per_image": 5,    # 每張圖片最大關聯數
    "min_confidence_threshold": 0.3,    # 最小置信度閾值
    "enable_parallel_processing": True,  # 啟用並行處理
    "cache_embeddings": True,           # 緩存語義嵌入
    "batch_size": 32,                   # 批處理大小
}

def get_performance_config() -> dict:
    """獲取性能配置"""
    return PERFORMANCE_CONFIG.copy()

# 初始化時驗證環境
if not validate_association_environment():
    raise RuntimeError("關聯分析模組環境驗證失敗，請檢查依賴包安裝")

# 模組初始化完成日誌
from src.config.logging_config import get_logger
logger = get_logger("association")
logger.info(f"🎯 關聯分析模組初始化完成 v{__version__}")
logger.info(f"算法優先級: {ALGORITHM_PRIORITIES}")
logger.info(f"默認權重: {DEFAULT_WEIGHTS}")
