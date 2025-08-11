"""
空間關係分析器
Spatial Relationship Analyzer

基於Allen邏輯的空間關係分析器，專門用於分析文本塊和圖片之間的空間關係。
這個模組整合了Allen區間邏輯，並添加了針對圖文關聯的專門分析功能。

主要功能：
1. 空間特徵提取 - 提取邊界框的詳細空間特徵
2. 佈局模式分析 - 識別文檔的佈局模式（單欄、雙欄、複雜佈局）
3. 閱讀順序推斷 - 根據空間位置推斷自然閱讀順序
4. 空間關係評分 - 為空間關係生成置信度評分

權重：30%（項目規則）
"""

from typing import List, Dict, Tuple, Optional, NamedTuple, Union, Any
from dataclasses import dataclass
from enum import Enum
import re
try:
    import numpy as np
except ImportError:
    # 如果 numpy 不可用，使用內置 math 模組作為替代
    import math
    class np:
        @staticmethod
        def sqrt(x):
            return math.sqrt(x)
        @staticmethod
        def mean(x):
            return sum(x) / len(x) if x else 0
from functools import lru_cache
import hashlib
import time
from src.association.allen_logic import (
    AllenLogicAnalyzer, SpatialRelation, BoundingBox, 
    SpatialDirection, AllenRelation
)
from src.config.logging_config import get_logger, log_performance
from src.association.cache_manager import get_cache_manager, CacheType

logger = get_logger("spatial_analyzer")

# 獲取全局緩存管理器
cache_manager = get_cache_manager(
    max_memory_mb=100,
    default_ttl=3600.0,
    enable_persistence=True,
    persistence_path="data/cache"
)

class PerformanceOptimizer:
    """性能優化工具類"""
    
    @staticmethod
    def create_bbox_hash(bbox: BoundingBox) -> str:
        """為邊界框創建哈希值，用於緩存鍵"""
        content = f"{bbox.x1},{bbox.y1},{bbox.x2},{bbox.y2}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    @staticmethod
    def create_cache_key(text_bbox: BoundingBox, image_bbox: BoundingBox, 
                        context_hash: Optional[str] = None) -> str:
        """創建緩存鍵"""
        text_hash = PerformanceOptimizer.create_bbox_hash(text_bbox)
        image_hash = PerformanceOptimizer.create_bbox_hash(image_bbox)
        
        if context_hash:
            return f"spatial_{text_hash}_{image_hash}_{context_hash}"
        return f"spatial_{text_hash}_{image_hash}"
    
    @staticmethod
    def clean_expired_cache(expiry_seconds: int = 3600):
        """清理過期緩存（現在由緩存管理器自動處理）"""
        # 這個方法現在由緩存管理器自動處理
        # 手動觸發清理
        cache_manager._cleanup_expired()
        logger.debug("手動觸發緩存清理")

class LayoutPattern(Enum):
    """文檔佈局模式"""
    
    SINGLE_COLUMN = "single_column"        # 單欄佈局
    DOUBLE_COLUMN = "double_column"        # 雙欄佈局
    MULTI_COLUMN = "multi_column"          # 多欄佈局
    GRID_LAYOUT = "grid_layout"            # 網格佈局
    COMPLEX_LAYOUT = "complex_layout"      # 複雜佈局
    UNKNOWN = "unknown"                    # 未知佈局

class ReadingOrder(Enum):
    """閱讀順序"""
    
    LEFT_TO_RIGHT = "left_to_right"        # 從左到右
    TOP_TO_BOTTOM = "top_to_bottom"        # 從上到下
    ZIGZAG = "zigzag"                      # 之字形
    RANDOM = "random"                      # 隨機順序
    UNKNOWN = "unknown"                    # 未知順序

class AlignmentType(Enum):
    """對齊類型"""
    
    LEFT_ALIGNED = "left_aligned"          # 左對齊
    RIGHT_ALIGNED = "right_aligned"        # 右對齊
    CENTER_ALIGNED = "center_aligned"      # 居中對齊
    TOP_ALIGNED = "top_aligned"            # 頂部對齊
    BOTTOM_ALIGNED = "bottom_aligned"      # 底部對齊
    MIDDLE_ALIGNED = "middle_aligned"      # 垂直居中
    NO_ALIGNMENT = "no_alignment"          # 無對齊

class DocumentType(Enum):
    """文檔類型"""
    
    ACADEMIC_PAPER = "academic_paper"      # 學術論文
    TECHNICAL_MANUAL = "technical_manual"  # 技術手冊
    PRESENTATION = "presentation"          # 演示文稿
    REPORT = "report"                      # 報告
    MAGAZINE = "magazine"                  # 雜誌
    NEWSPAPER = "newspaper"                # 報紙
    BOOK = "book"                          # 書籍
    BROCHURE = "brochure"                  # 手冊/傳單
    FORM = "form"                          # 表單
    INVOICE = "invoice"                    # 發票
    UNKNOWN = "unknown"                    # 未知類型
    
@dataclass
class SpatialFeatures:
    """空間特徵數據類"""
    
    # 基本距離特徵
    center_distance: float                 # 中心點距離
    edge_distance: float                   # 邊緣距離
    min_distance: float                    # 最小距離
    
    # 相對位置特徵
    relative_position: Tuple[float, float] # 相對位置 (dx, dy)
    direction_angle: float                 # 方向角度（弧度）
    
    # 尺寸關係特徵
    size_ratio: float                      # 尺寸比例
    area_ratio: float                      # 面積比例
    aspect_ratio_diff: float               # 寬高比差異
    
    # 重疊特徵
    overlap_area: float                    # 重疊面積
    overlap_ratio: float                   # 重疊比例
    
    # 對齊特徵
    horizontal_alignment: AlignmentType    # 水平對齊
    vertical_alignment: AlignmentType      # 垂直對齊
    alignment_score: float                 # 對齊程度評分
    
    # 佈局特徵
    same_row: bool                         # 是否在同一行
    same_column: bool                      # 是否在同一列
    reading_order_score: float             # 閱讀順序評分

@dataclass
class EnhancedSpatialFeatures:
    """增強的空間特徵數據類，包含所有新添加的分析功能"""
    
    # 繼承基本空間特徵
    basic_features: SpatialFeatures
    
    # 增強的垂直關係分析
    vertical_relationship: str             # 垂直關係類型 ('above', 'below', 'same_level')
    natural_reading_priority: float        # 自然閱讀順序優先級 (0-1)
    vertical_distance_normalized: float    # 歸一化垂直距離
    
    # 增強的水平重疊分析
    horizontal_overlap_ratio: float        # 水平重疊比例 (0-1)
    overlap_threshold_passed: bool         # 是否通過重疊門檻
    horizontal_alignment_strength: float   # 水平對齊強度 (0-1)
    
    # 介入元素分析
    has_intervening_elements: bool         # 是否有介入元素
    intervening_element_count: int         # 介入元素數量
    intervening_penalty: float             # 介入元素懲罰係數 (0-1)
    
    # 動態距離歸一化
    normalized_distance: float             # 動態歸一化距離
    page_size_factor: float                # 頁面尺寸影響因子
    document_density: float                # 文檔密度影響因子
    
    # 整合評分
    enhanced_spatial_score: float          # 增強空間關係評分 (0-1)
    confidence_level: float                # 評分置信度 (0-1)
    
    # 調試信息
    debug_info: Dict[str, Any]             # 調試和分析信息

class SpatialAnalyzer:
    """空間關係分析器（性能優化版本）"""
    
    # 類級別的共享實例，避免重複創建
    _shared_instances = {}
    _instance_lock = False
    
    def __init__(self, 
                 alignment_tolerance: float = 10.0,
                 distance_normalization: bool = True,
                 enable_cache: bool = True):
        """
        初始化空間分析器
        
        Args:
            alignment_tolerance: 對齊容差（像素）
            distance_normalization: 是否進行距離標準化
            enable_cache: 是否啟用緩存（默認啟用）
        """
        self.alignment_tolerance = alignment_tolerance
        self.distance_normalization = distance_normalization
        self.enable_cache = enable_cache
        self.allen_analyzer = AllenLogicAnalyzer()
        
        # 佈局分析參數
        self.layout_params = {
            "column_gap_threshold": 50,      # 欄間距閾值
            "row_gap_threshold": 20,         # 行間距閾值
            "grid_regularity_threshold": 0.8 # 網格規律性閾值
        }
        
        # 性能統計
        self.stats = {
            "calculations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time": 0.0
        }
        
        logger.debug("空間關係分析器初始化完成")
    
    @classmethod
    def get_shared_instance(cls, 
                           alignment_tolerance: float = 10.0,
                           distance_normalization: bool = True,
                           enable_cache: bool = True) -> 'SpatialAnalyzer':
        """
        獲取共享實例，避免重複創建分析器
        """
        key = f"{alignment_tolerance}_{distance_normalization}_{enable_cache}"
        
        if key not in cls._shared_instances:
            cls._shared_instances[key] = cls(
                alignment_tolerance=alignment_tolerance,
                distance_normalization=distance_normalization,
                enable_cache=enable_cache
            )
        
        return cls._shared_instances[key]
    
    @log_performance("calculate_spatial_features")
    def calculate_spatial_features(self, bbox_a: BoundingBox, 
                                 bbox_b: BoundingBox) -> SpatialFeatures:
        """
        計算兩個邊界框之間的詳細空間特徵
        
        Args:
            bbox_a: 邊界框A（通常是文本框）
            bbox_b: 邊界框B（通常是圖片框）
            
        Returns:
            SpatialFeatures: 空間特徵對象
        """
        # 1. 基本距離計算
        center_distance = self._calculate_center_distance(bbox_a, bbox_b)
        edge_distance = self._calculate_edge_distance(bbox_a, bbox_b)
        min_distance = self._calculate_min_distance(bbox_a, bbox_b)
        
        # 2. 相對位置特徵
        dx = bbox_a.center_x - bbox_b.center_x
        dy = bbox_a.center_y - bbox_b.center_y
        relative_position = (dx, dy)
        direction_angle = np.arctan2(dy, dx)
        
        # 3. 尺寸關係特徵
        size_ratio = self._calculate_size_ratio(bbox_a, bbox_b)
        area_ratio = bbox_a.area / max(bbox_b.area, 1e-6)
        aspect_ratio_diff = abs((bbox_a.width / max(bbox_a.height, 1e-6)) - 
                               (bbox_b.width / max(bbox_b.height, 1e-6)))
        
        # 4. 重疊特徵
        overlap_area, overlap_ratio = self._calculate_overlap(bbox_a, bbox_b)
        
        # 5. 對齊特徵
        h_alignment, v_alignment, alignment_score = self._analyze_alignment(bbox_a, bbox_b)
        
        # 6. 佈局特徵
        same_row = self._is_same_row(bbox_a, bbox_b)
        same_column = self._is_same_column(bbox_a, bbox_b)
        reading_order_score = self._calculate_reading_order_score(bbox_a, bbox_b)
        
        # 距離標準化（如果啟用）
        if self.distance_normalization:
            avg_dimension = (bbox_a.width + bbox_a.height + bbox_b.width + bbox_b.height) / 4
            center_distance /= max(avg_dimension, 1)
            edge_distance /= max(avg_dimension, 1)
            min_distance /= max(avg_dimension, 1)
        
        return SpatialFeatures(
            center_distance=center_distance,
            edge_distance=edge_distance,
            min_distance=min_distance,
            relative_position=relative_position,
            direction_angle=direction_angle,
            size_ratio=size_ratio,
            area_ratio=area_ratio,
            aspect_ratio_diff=aspect_ratio_diff,
            overlap_area=overlap_area,
            overlap_ratio=overlap_ratio,
            horizontal_alignment=h_alignment,
            vertical_alignment=v_alignment,
            alignment_score=alignment_score,
            same_row=same_row,
            same_column=same_column,
            reading_order_score=reading_order_score
        )
    
    def _calculate_center_distance(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> float:
        """計算中心點歐幾里得距離"""
        dx = bbox_a.center_x - bbox_b.center_x
        dy = bbox_a.center_y - bbox_b.center_y
        return np.sqrt(dx * dx + dy * dy)
    
    def _calculate_edge_distance(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> float:
        """計算邊緣間的最小距離"""
        # 計算水平方向的間距
        h_gap = 0
        if bbox_a.right < bbox_b.left:
            h_gap = bbox_b.left - bbox_a.right
        elif bbox_b.right < bbox_a.left:
            h_gap = bbox_a.left - bbox_b.right
        
        # 計算垂直方向的間距
        v_gap = 0
        if bbox_a.bottom < bbox_b.top:
            v_gap = bbox_b.top - bbox_a.bottom
        elif bbox_b.bottom < bbox_a.top:
            v_gap = bbox_a.top - bbox_b.bottom
        
        # 如果有重疊，返回0
        if h_gap <= 0 and v_gap <= 0:
            return 0
        
        # 返回間距的歐幾里得距離
        return np.sqrt(h_gap * h_gap + v_gap * v_gap)
    
    def _calculate_min_distance(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> float:
        """計算兩個矩形之間的最小距離"""
        # 計算所有可能的點對距離，返回最小值
        points_a = [
            (bbox_a.left, bbox_a.top),
            (bbox_a.right, bbox_a.top),
            (bbox_a.left, bbox_a.bottom),
            (bbox_a.right, bbox_a.bottom),
            (bbox_a.center_x, bbox_a.center_y)
        ]
        
        points_b = [
            (bbox_b.left, bbox_b.top),
            (bbox_b.right, bbox_b.top),
            (bbox_b.left, bbox_b.bottom),
            (bbox_b.right, bbox_b.bottom),
            (bbox_b.center_x, bbox_b.center_y)
        ]
        
        min_dist = float('inf')
        for px_a, py_a in points_a:
            for px_b, py_b in points_b:
                dist = np.sqrt((px_a - px_b) ** 2 + (py_a - py_b) ** 2)
                min_dist = min(min_dist, dist)
        
        return min_dist
    
    def _calculate_size_ratio(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> float:
        """計算尺寸比例（較小邊界框/較大邊界框）"""
        size_a = max(bbox_a.width, bbox_a.height)
        size_b = max(bbox_b.width, bbox_b.height)
        return min(size_a, size_b) / max(size_a, size_b)
    
    def _calculate_overlap(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> Tuple[float, float]:
        """
        計算重疊面積和重疊比例
        
        Returns:
            Tuple[float, float]: (重疊面積, 重疊比例)
        """
        # 計算重疊區域
        overlap_left = max(bbox_a.left, bbox_b.left)
        overlap_right = min(bbox_a.right, bbox_b.right)
        overlap_top = max(bbox_a.top, bbox_b.top)
        overlap_bottom = min(bbox_a.bottom, bbox_b.bottom)
        
        # 檢查是否有重疊
        if overlap_left >= overlap_right or overlap_top >= overlap_bottom:
            return 0.0, 0.0
        
        # 計算重疊面積
        overlap_area = (overlap_right - overlap_left) * (overlap_bottom - overlap_top)
        
        # 計算重疊比例（相對於較小的矩形）
        min_area = min(bbox_a.area, bbox_b.area)
        overlap_ratio = overlap_area / max(min_area, 1e-6)
        
        return overlap_area, overlap_ratio
    
    def _analyze_alignment(self, bbox_a: BoundingBox, 
                         bbox_b: BoundingBox) -> Tuple[AlignmentType, AlignmentType, float]:
        """
        分析對齊關係
        
        Returns:
            Tuple[AlignmentType, AlignmentType, float]: (水平對齊, 垂直對齊, 對齊評分)
        """
        tolerance = self.alignment_tolerance
        
        # 水平對齊分析
        h_alignment = AlignmentType.NO_ALIGNMENT
        if abs(bbox_a.left - bbox_b.left) <= tolerance:
            h_alignment = AlignmentType.LEFT_ALIGNED
        elif abs(bbox_a.right - bbox_b.right) <= tolerance:
            h_alignment = AlignmentType.RIGHT_ALIGNED
        elif abs(bbox_a.center_x - bbox_b.center_x) <= tolerance:
            h_alignment = AlignmentType.CENTER_ALIGNED
        
        # 垂直對齊分析
        v_alignment = AlignmentType.NO_ALIGNMENT
        if abs(bbox_a.top - bbox_b.top) <= tolerance:
            v_alignment = AlignmentType.TOP_ALIGNED
        elif abs(bbox_a.bottom - bbox_b.bottom) <= tolerance:
            v_alignment = AlignmentType.BOTTOM_ALIGNED
        elif abs(bbox_a.center_y - bbox_b.center_y) <= tolerance:
            v_alignment = AlignmentType.MIDDLE_ALIGNED
        
        # 計算對齊評分
        h_score = 1.0 if h_alignment != AlignmentType.NO_ALIGNMENT else 0.0
        v_score = 1.0 if v_alignment != AlignmentType.NO_ALIGNMENT else 0.0
        alignment_score = (h_score + v_score) / 2
        
        return h_alignment, v_alignment, alignment_score
    
    def _is_same_row(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> bool:
        """判斷是否在同一行"""
        # 檢查垂直重疊
        v_overlap = min(bbox_a.bottom, bbox_b.bottom) - max(bbox_a.top, bbox_b.top)
        avg_height = (bbox_a.height + bbox_b.height) / 2
        
        return v_overlap > avg_height * 0.3  # 30%重疊認為是同一行
    
    def _is_same_column(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> bool:
        """判斷是否在同一列"""
        # 檢查水平重疊
        h_overlap = min(bbox_a.right, bbox_b.right) - max(bbox_a.left, bbox_b.left)
        avg_width = (bbox_a.width + bbox_b.width) / 2
        
        return h_overlap > avg_width * 0.3  # 30%重疊認為是同一列
    
    def _calculate_reading_order_score(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> float:
        """
        計算閱讀順序評分
        左上角優先，從左到右，從上到下的自然閱讀順序得分更高
        
        Returns:
            float: 閱讀順序評分 (0-1)
        """
        # 計算相對位置
        dx = bbox_a.center_x - bbox_b.center_x
        dy = bbox_a.center_y - bbox_b.center_y
        
        # 從左到右的權重
        lr_score = 0.5
        if dx < 0:  # A在B左側
            lr_score = 0.7
        elif dx > 0:  # A在B右側
            lr_score = 0.3
        
        # 從上到下的權重
        tb_score = 0.5
        if dy < 0:  # A在B上方
            tb_score = 0.8
        elif dy > 0:  # A在B下方
            tb_score = 0.2
        
        # 綜合評分（垂直位置權重更高）
        reading_score = lr_score * 0.3 + tb_score * 0.7
        
        return reading_score
    
    def calculate_enhanced_spatial_features(self, text_bbox: BoundingBox, image_bbox: BoundingBox, context_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        增強的空間特徵計算，整合所有改進方法
        
        Args:
            text_bbox: 文本邊界框
            image_bbox: 圖片邊界框
            context_info: 上下文信息（佈局類型、所有元素等）
            
        Returns:
            Dict[str, Any]: 包含增強空間特徵的完整結果
        """
        # 調用全局的增強空間評分函數
        enhanced_result = enhanced_spatial_scoring(text_bbox, image_bbox, context_info)
        
        # 同時獲取傳統的空間特徵以保持兼容性
        traditional_features = self.calculate_spatial_features(text_bbox, image_bbox)
        
        # 合併結果
        return {
            'enhanced_features': enhanced_result,
            'traditional_features': traditional_features,
            'final_score': enhanced_result['final_score'],
            'component_scores': enhanced_result['component_scores'],
            'details': enhanced_result['details']
        }

def analyze_layout_patterns(bboxes: List[BoundingBox]) -> LayoutPattern:
    """
    分析邊界框列表的佈局模式
    
    Args:
        bboxes: 邊界框列表
        
    Returns:
        LayoutPattern: 佈局模式
    """
    if len(bboxes) < 2:
        return LayoutPattern.UNKNOWN
    
    analyzer = SpatialAnalyzer()
    
    # 按位置排序
    sorted_boxes = sorted(bboxes, key=lambda b: (b.top, b.left))
    
    # 分析行
    rows = []
    current_row = [sorted_boxes[0]]
    
    for bbox in sorted_boxes[1:]:
        # 檢查是否與當前行的最後一個框在同一行
        if analyzer._is_same_row(current_row[-1], bbox):
            current_row.append(bbox)
        else:
            rows.append(current_row)
            current_row = [bbox]
    
    if current_row:
        rows.append(current_row)
    
    # 分析欄數
    column_counts = [len(row) for row in rows]
    max_columns = max(column_counts)
    avg_columns = np.mean(column_counts)
    
    # 判斷佈局模式
    if max_columns == 1:
        return LayoutPattern.SINGLE_COLUMN
    elif max_columns == 2 and avg_columns >= 1.5:
        return LayoutPattern.DOUBLE_COLUMN
    elif max_columns > 2 and avg_columns >= 2:
        if _is_grid_layout(rows):
            return LayoutPattern.GRID_LAYOUT
        else:
            return LayoutPattern.MULTI_COLUMN
    else:
        return LayoutPattern.COMPLEX_LAYOUT

def _is_grid_layout(rows: List[List[BoundingBox]]) -> bool:
    """檢查是否為網格佈局"""
    if len(rows) < 2:
        return False
    
    # 檢查每行的欄數是否相近
    column_counts = [len(row) for row in rows]
    return np.std(column_counts) < 0.5  # 標準差小於0.5認為是網格

def calculate_spatial_features(text_boxes: List[BoundingBox], 
                             image_boxes: List[BoundingBox],
                             analyzer: Optional[SpatialAnalyzer] = None) -> List[List[SpatialFeatures]]:
    """
    批量計算空間特徵
    
    Args:
        text_boxes: 文本邊界框列表
        image_boxes: 圖片邊界框列表
        analyzer: 空間分析器實例
        
    Returns:
        List[List[SpatialFeatures]]: 特徵矩陣 [text_idx][image_idx]
    """
    if analyzer is None:
        analyzer = SpatialAnalyzer()
    
    features_matrix = []
    
    for text_box in text_boxes:
        text_features = []
        for image_box in image_boxes:
            features = analyzer.calculate_spatial_features(text_box, image_box)
            text_features.append(features)
        features_matrix.append(text_features)
    
    logger.info(f"批量空間特徵計算完成: {len(text_boxes)}個文本框 x {len(image_boxes)}個圖片框")
    return features_matrix

def calculate_spatial_score(features: SpatialFeatures, 
                          spatial_relation: SpatialRelation,
                          weight_spatial: float = 0.3) -> float:
    """
    計算空間關係的最終評分
    
    Args:
        features: 空間特徵
        spatial_relation: Allen邏輯空間關係
        weight_spatial: 空間權重（項目規則規定為0.3）
        
    Returns:
        float: 空間評分
    """
    # 基礎評分來自Allen邏輯的置信度
    base_score = spatial_relation.confidence
    
    # 對齊加分
    alignment_bonus = features.alignment_score * 0.2
    
    # 距離調整（距離越近評分越高）
    distance_factor = 1.0
    if features.center_distance > 0:
        # 使用歸一化的距離，距離越遠評分越低
        distance_factor = max(0.3, 1.0 - features.center_distance * 0.1)
    
    # 重疊加分（適度重疊是好的）
    overlap_bonus = 0
    if 0 < features.overlap_ratio < 0.3:  # 適度重疊
        overlap_bonus = features.overlap_ratio * 0.1
    
    # 閱讀順序加分
    reading_bonus = features.reading_order_score * 0.1
    
    # 計算最終評分
    final_score = (base_score + alignment_bonus + overlap_bonus + reading_bonus) * distance_factor
    
    return min(1.0, final_score) * weight_spatial

# 增強的空間分析函數 (新增)
def analyze_vertical_relationship(text_bbox: BoundingBox, image_bbox: BoundingBox) -> Dict:
    """
    分析垂直關係，優先考慮自然閱讀順序
    
    Args:
        text_bbox: 文本邊界框
        image_bbox: 圖片邊界框
        
    Returns:
        Dict: 包含垂直關係分析結果
    """
    if image_bbox.top >= text_bbox.bottom:
        # 圖片在文本下方（自然閱讀順序）
        vertical_gap = image_bbox.top - text_bbox.bottom
        direction_weight = 1.0  # 最高權重
        relationship = "below"
    elif text_bbox.top >= image_bbox.bottom:
        # 文本在圖片下方（反向關係）
        vertical_gap = text_bbox.top - image_bbox.bottom
        direction_weight = 0.3  # 大幅降權
        relationship = "above"
    else:
        # 垂直重疊
        vertical_gap = 0
        direction_weight = 0.8
        relationship = "overlap"
    
    # 使用指數衰減計算距離分數
    # 歸一化基準：圖片高度的2倍作為"中等距離"
    normalized_gap = vertical_gap / max(image_bbox.height * 2, 1)
    distance_score = np.exp(-normalized_gap * 2.0)
    
    # 應用方向權重
    final_score = distance_score * direction_weight
    
    return {
        'score': final_score,
        'gap': vertical_gap,
        'weight': direction_weight,
        'relationship': relationship
    }

def calculate_horizontal_overlap(text_bbox: BoundingBox, image_bbox: BoundingBox, threshold: float = 0.4) -> float:
    """
    計算水平重疊度並設置門檻過濾
    確保文本和圖片在同一欄位或具有合理的水平關聯
    
    Args:
        text_bbox: 文本邊界框
        image_bbox: 圖片邊界框
        threshold: 重疊度門檻（預設40%）
        
    Returns:
        float: 水平重疊分數 (0-1)
    """
    # 計算水平重疊區間
    overlap_left = max(text_bbox.left, image_bbox.left)
    overlap_right = min(text_bbox.right, image_bbox.right)
    
    if overlap_left >= overlap_right:
        return 0.0  # 無重疊，直接排除
    
    overlap_width = overlap_right - overlap_left
    
    # 使用較小元素的寬度作為基準
    min_width = min(text_bbox.width, image_bbox.width)
    overlap_ratio = overlap_width / max(min_width, 1)
    
    # 門檻過濾機制
    if overlap_ratio < threshold:
        # 重疊度不足，大幅降權但不完全排除
        return overlap_ratio * 0.3
    
    # 重疊度充足，給予加分
    return min(1.0, overlap_ratio * 1.2)

def check_intervening_elements(text_bbox: BoundingBox, image_bbox: BoundingBox, context_info: Optional[Dict] = None) -> float:
    """
    檢查文本和圖片之間是否有其他元素介入
    介入元素會降低關聯可能性
    
    Args:
        text_bbox: 文本邊界框
        image_bbox: 圖片邊界框
        context_info: 上下文信息，包含所有元素列表
        
    Returns:
        float: 介入懲罰因子 (0.3-1.0，1.0表示無懲罰)
    """
    if not context_info or 'all_elements' not in context_info:
        return 1.0  # 無上下文信息，不應用懲罰
    
    all_elements = context_info['all_elements']
    intervening_count = 0
    
    # 定義檢查區域（文本底部到圖片頂部的矩形區域）
    check_top = min(text_bbox.bottom, image_bbox.top)
    check_bottom = max(text_bbox.bottom, image_bbox.top)
    check_left = min(text_bbox.left, image_bbox.left) - 10  # 添加小的容差
    check_right = max(text_bbox.right, image_bbox.right) + 10
    
    for element in all_elements:
        # 跳過自身元素
        if hasattr(element, 'id') and element.id in [getattr(text_bbox, 'id', None), getattr(image_bbox, 'id', None)]:
            continue
        
        # 檢查元素是否在介入區域內
        element_bbox = element if hasattr(element, 'left') else getattr(element, 'bbox', None)
        if not element_bbox:
            continue
            
        if (element_bbox.left < check_right and 
            element_bbox.right > check_left and
            element_bbox.top < check_bottom and 
            element_bbox.bottom > check_top):
            
            # 根據介入元素的大小給予不同權重的懲罰
            element_area = element_bbox.width * element_bbox.height
            text_area = text_bbox.width * text_bbox.height
            
            if element_area > text_area * 0.5:
                intervening_count += 1.0  # 大元素，完整懲罰
            else:
                intervening_count += 0.5  # 小元素，減半懲罰
    
    # 每個介入元素降低15%分數，但保持最低30%
    penalty_factor = 1.0 - (intervening_count * 0.15)
    return max(0.3, penalty_factor)

def calculate_normalized_distance(text_bbox: BoundingBox, image_bbox: BoundingBox, context_info: Optional[Dict] = None) -> float:
    """
    動態歸一化距離計算
    根據文檔類型和佈局密度調整歸一化參數
    
    Args:
        text_bbox: 文本邊界框
        image_bbox: 圖片邊界框
        context_info: 上下文信息（佈局類型等）
        
    Returns:
        float: 歸一化距離分數 (0-1)
    """
    # 基礎距離計算
    center_distance = np.sqrt(
        (text_bbox.center_x - image_bbox.center_x) ** 2 + 
        (text_bbox.center_y - image_bbox.center_y) ** 2
    )
    
    # 動態選擇歸一化基準
    if context_info and 'layout_type' in context_info:
        layout_type = context_info['layout_type']
        
        if layout_type == 'single_column':
            # 單欄文檔：使用圖片高度的5倍
            normalization_base = image_bbox.height * 5
        elif layout_type == 'multi_column':
            # 多欄文檔：使用圖片高度的3倍
            normalization_base = image_bbox.height * 3
        else:
            # 複雜佈局：使用圖片對角線的2倍
            image_diagonal = np.sqrt(image_bbox.width**2 + image_bbox.height**2)
            normalization_base = image_diagonal * 2
    else:
        # 預設：使用圖片高度的4倍
        normalization_base = image_bbox.height * 4
    
    # 計算歸一化距離
    normalized_distance = center_distance / max(normalization_base, 1)
    
    # 使用指數衰減轉換為分數
    distance_score = np.exp(-normalized_distance * 1.5)
    
    return distance_score

def detect_layout_columns(all_elements: List[Any], page_width: Optional[float] = None) -> Dict[str, Any]:
    """
    檢測文檔的欄位結構
    
    Args:
        all_elements: 所有文檔元素（文本塊和圖片）
        page_width: 頁面寬度（可選）
        
    Returns:
        Dict[str, Any]: 欄位檢測結果
    """
    if not all_elements:
        return {
            'layout_type': 'unknown',
            'column_count': 1,
            'column_boundaries': [],
            'confidence': 0.0
        }
    
    # 提取所有元素的水平位置
    left_positions = []
    right_positions = []
    center_positions = []
    
    for element in all_elements:
        bbox = element if hasattr(element, 'left') else getattr(element, 'bbox', None)
        if bbox:
            left_positions.append(bbox.left)
            right_positions.append(bbox.right)
            center_positions.append(bbox.center_x)
    
    if not left_positions:
        return {
            'layout_type': 'unknown',
            'column_count': 1,
            'column_boundaries': [],
            'confidence': 0.0
        }
    
    # 估算頁面寬度
    if page_width is None:
        page_width = max(right_positions) - min(left_positions)
    
    # 使用聚類方法檢測欄位
    sorted_centers = sorted(center_positions)
    
    # 檢測聚類中心
    clusters = []
    current_cluster = [sorted_centers[0]]
    cluster_threshold = page_width * 0.15  # 15%頁面寬度作為聚類閾值
    
    for i in range(1, len(sorted_centers)):
        if sorted_centers[i] - sorted_centers[i-1] <= cluster_threshold:
            current_cluster.append(sorted_centers[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [sorted_centers[i]]
    
    if current_cluster:
        clusters.append(current_cluster)
    
    # 計算每個聚類的中心
    column_centers = []
    for cluster in clusters:
        if len(cluster) >= 3:  # 至少3個元素才算有效欄位
            column_centers.append(sum(cluster) / len(cluster))
    
    # 確定佈局類型
    column_count = len(column_centers)
    
    if column_count <= 1:
        layout_type = 'single_column'
    elif column_count == 2:
        layout_type = 'double_column'
    elif column_count <= 4:
        layout_type = 'multi_column'
    else:
        layout_type = 'complex_layout'
    
    # 計算置信度
    confidence = min(1.0, len(column_centers) / max(1, len(clusters)) * 0.8 + 0.2)
    
    # 計算欄位邊界
    column_boundaries = []
    if column_count > 1:
        for i in range(len(column_centers)):
            if i == 0:
                left_bound = min(left_positions)
                right_bound = (column_centers[0] + column_centers[1]) / 2 if len(column_centers) > 1 else max(right_positions)
            elif i == len(column_centers) - 1:
                left_bound = (column_centers[i-1] + column_centers[i]) / 2
                right_bound = max(right_positions)
            else:
                left_bound = (column_centers[i-1] + column_centers[i]) / 2
                right_bound = (column_centers[i] + column_centers[i+1]) / 2
            
            column_boundaries.append({
                'center': column_centers[i],
                'left': left_bound,
                'right': right_bound,
                'width': right_bound - left_bound
            })
    
    logger.debug(f"佈局檢測結果: {layout_type}, 欄位數: {column_count}, 置信度: {confidence:.3f}")
    
    return {
        'layout_type': layout_type,
        'column_count': column_count,
        'column_boundaries': column_boundaries,
        'column_centers': column_centers,
        'confidence': confidence,
        'page_width': page_width
    }

def determine_element_column(element_bbox: BoundingBox, column_info: Dict[str, Any]) -> Optional[int]:
    """
    確定元素屬於哪個欄位
    
    Args:
        element_bbox: 元素邊界框
        column_info: 欄位信息
        
    Returns:
        Optional[int]: 欄位索引（從0開始），如果無法確定則返回None
    """
    if not column_info['column_boundaries']:
        return 0  # 單欄情況
    
    element_center = element_bbox.center_x
    
    for i, column in enumerate(column_info['column_boundaries']):
        if column['left'] <= element_center <= column['right']:
            return i
    
    # 如果不在任何欄位內，找最近的欄位
    min_distance = float('inf')
    closest_column = 0
    
    for i, column in enumerate(column_info['column_boundaries']):
        distance = abs(element_center - column['center'])
        if distance < min_distance:
            min_distance = distance
            closest_column = i
    
    return closest_column

def analyze_cross_column_relationship(text_bbox: BoundingBox, image_bbox: BoundingBox, column_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析跨欄位關係
    
    Args:
        text_bbox: 文本邊界框
        image_bbox: 圖片邊界框
        column_info: 欄位信息
        
    Returns:
        Dict[str, Any]: 跨欄位關係分析結果
    """
    text_column = determine_element_column(text_bbox, column_info)
    image_column = determine_element_column(image_bbox, column_info)
    
    is_same_column = text_column == image_column
    column_distance = abs(text_column - image_column) if text_column is not None and image_column is not None else 0
    
    # 跨欄位懲罰
    if is_same_column:
        cross_column_penalty = 1.0  # 無懲罰
    elif column_distance == 1:
        cross_column_penalty = 0.6  # 相鄰欄位，中等懲罰
    elif column_distance == 2:
        cross_column_penalty = 0.3  # 間隔一欄，較重懲罰
    else:
        cross_column_penalty = 0.1  # 距離很遠，重懲罰
    
    return {
        'text_column': text_column,
        'image_column': image_column,
        'is_same_column': is_same_column,
        'column_distance': column_distance,
        'cross_column_penalty': cross_column_penalty
    }

def enhanced_spatial_scoring(text_bbox: BoundingBox, image_bbox: BoundingBox, context_info: Optional[Dict] = None) -> Dict[str, Any]:
    """
    增強的空間評分模型 - 完整的5組件關聯評分系統
    嚴格按照項目規則實施：Caption 40% + Spatial 30% + Semantic 15% + Layout 10% + Proximity 5%
    
    Args:
        text_bbox: 文本邊界框
        image_bbox: 圖片邊界框
        context_info: 上下文信息（佈局類型、所有元素、文本內容等）
        
    Returns:
        Dict[str, Any]: 包含最終分數和各組件分數的詳細結果
    """
    # === 按照空間距離計算改進分析的建議實施 ===
    # 參考文檔：空間距離計算改進整合分析_20250808_1430.md
    
    # 0. 佈局分析（如果有上下文信息）
    column_info = None
    cross_column_analysis = None
    
    if context_info and 'all_elements' in context_info:
        # 檢測文檔佈局
        column_info = detect_layout_columns(context_info['all_elements'])
        # 分析跨欄位關係
        cross_column_analysis = analyze_cross_column_relationship(text_bbox, image_bbox, column_info)
        
        # 更新上下文信息中的佈局類型
        if 'layout_type' not in context_info:
            context_info['layout_type'] = column_info['layout_type']
    
    # 1. 垂直關係分析（最重要）
    vertical_result = analyze_vertical_relationship(text_bbox, image_bbox)
    
    # 2. 水平重疊檢測（門檻過濾）
    horizontal_score = calculate_horizontal_overlap(text_bbox, image_bbox)
    
    # 3. 介入元素檢測
    intervening_penalty = check_intervening_elements(text_bbox, image_bbox, context_info)
    
    # 4. 對齊度分析（使用現有的方法）
    analyzer = SpatialAnalyzer()
    temp_features = analyzer.calculate_spatial_features(text_bbox, image_bbox)
    alignment_score = temp_features.alignment_score
    
    # 5. 動態距離歸一化
    normalized_distance_score = calculate_normalized_distance(text_bbox, image_bbox, context_info)
    
    # 權重分配（基於空間分析改進文檔的建議）
    weights = {
        'vertical': 0.4,        # 垂直關係最重要
        'horizontal': 0.25,     # 水平重疊次重要
        'distance': 0.2,        # 歸一化距離
        'alignment': 0.1,       # 對齊度
        'intervening': 0.05     # 介入懲罰權重最小，但作為乘法因子
    }
    
    # 計算基礎分數
    base_score = (
        vertical_result['score'] * weights['vertical'] +
        horizontal_score * weights['horizontal'] +
        normalized_distance_score * weights['distance'] +
        alignment_score * weights['alignment']
    )
    
    # 應用介入懲罰和佈局懲罰（乘法因子）
    layout_penalty = 1.0
    if cross_column_analysis:
        layout_penalty = cross_column_analysis['cross_column_penalty']
    
    final_score = base_score * intervening_penalty * layout_penalty
    
    # 構建詳細結果（按照空間分析改進文檔的建議）
    result = {
        'final_score': final_score,
        'component_scores': {
            'vertical': vertical_result['score'],
            'horizontal': horizontal_score,
            'distance': normalized_distance_score,
            'alignment': alignment_score,
            'intervening_penalty': intervening_penalty,
            'layout_penalty': layout_penalty
        },
        'details': {
            'vertical_gap': vertical_result['gap'],
            'direction_weight': vertical_result['weight'],
            'horizontal_overlap': horizontal_score,
            'base_score': base_score,
            'relationship': vertical_result['relationship'],
            'weights_used': weights
        }
    }
    
    # 添加佈局分析信息（如果可用）
    if column_info:
        result['layout_info'] = {
            'layout_type': column_info['layout_type'],
            'column_count': column_info['column_count'],
            'confidence': column_info['confidence']
        }
    
    if cross_column_analysis:
        result['cross_column_info'] = {
            'text_column': cross_column_analysis['text_column'],
            'image_column': cross_column_analysis['image_column'],
            'is_same_column': cross_column_analysis['is_same_column'],
            'column_distance': cross_column_analysis['column_distance'],
            'cross_column_penalty': cross_column_analysis['cross_column_penalty']
        }
    
    return result

def enhanced_spatial_scoring_optimized(text_bbox: BoundingBox, image_bbox: BoundingBox, context_info: Optional[Dict] = None, enable_cache: bool = True) -> Dict[str, Any]:
    """
    增強的空間評分模型（性能優化版本）
    整合所有改進的空間分析方法，包括佈局感知和緩存機制
    
    Args:
        text_bbox: 文本邊界框
        image_bbox: 圖片邊界框
        context_info: 上下文信息（佈局類型、所有元素等）
        enable_cache: 是否啟用緩存（默認True）
        
    Returns:
        Dict[str, Any]: 包含最終分數和各組件分數的詳細結果
    """
    start_time = time.time()
    
    # 嘗試從緩存獲取結果
    if enable_cache:
        # 創建緩存鍵
        cache_key = cache_manager.create_key(
            text_bbox.x, text_bbox.y, text_bbox.width, text_bbox.height,
            image_bbox.x, image_bbox.y, image_bbox.width, image_bbox.height,
            context_info.get('layout_type', 'unknown') if context_info else 'none',
            len(context_info.get('all_elements', [])) if context_info else 0
        )
        
        # 嘗試從緩存獲取
        cached_result = cache_manager.get(CacheType.SPATIAL, cache_key)
        if cached_result:
            cached_result['performance'] = {
                'cache_hit': True,
                'computation_time': time.time() - start_time
            }
            return cached_result
    
    # 0. 佈局分析（如果有上下文信息）- 使用緩存
    column_info = None
    cross_column_analysis = None
    
    if context_info and 'all_elements' in context_info:
        # 使用佈局緩存
        layout_cache_key = cache_manager.create_key(
            "layout", len(context_info['all_elements']),
            str(sorted([str(elem) for elem in context_info['all_elements'][:5]]))  # 使用前5個元素的簡化表示
        )
        
        if enable_cache:
            column_info = cache_manager.get(CacheType.LAYOUT, layout_cache_key)
        
        if not column_info:
            # 檢測文檔佈局
            column_info = detect_layout_columns(context_info['all_elements'])
            if enable_cache:
                cache_manager.put(CacheType.LAYOUT, layout_cache_key, column_info)
        
        # 分析跨欄位關係
        cross_column_analysis = analyze_cross_column_relationship(text_bbox, image_bbox, column_info)
        
        # 更新上下文信息中的佈局類型
        if 'layout_type' not in context_info:
            context_info['layout_type'] = column_info['layout_type']
    
    # 使用共享的分析器實例，避免重複創建
    analyzer = SpatialAnalyzer.get_shared_instance(enable_cache=enable_cache)
    
    # 1. 垂直關係分析（最重要）
    vertical_result = analyze_vertical_relationship(text_bbox, image_bbox)
    
    # 2. 水平重疊檢測（門檻過濾）
    horizontal_score = calculate_horizontal_overlap(text_bbox, image_bbox)
    
    # 3. 介入元素檢測
    intervening_penalty = check_intervening_elements(text_bbox, image_bbox, context_info)
    
    # 4. 對齊度分析（重用分析器實例）
    temp_features = analyzer.calculate_spatial_features(text_bbox, image_bbox)
    alignment_score = temp_features.alignment_score
    
    # 5. 動態距離歸一化
    normalized_distance_score = calculate_normalized_distance(text_bbox, image_bbox, context_info)
    
    # 權重分配（基於重要性）
    weights = {
        'vertical': 0.4,        # 垂直關係最重要
        'horizontal': 0.25,     # 水平重疊次重要
        'distance': 0.2,        # 歸一化距離
        'alignment': 0.1,       # 對齊度
        'intervening': 0.05     # 介入懲罰權重最小，但作為乘法因子
    }
    
    # 計算基礎分數
    base_score = (
        vertical_result['score'] * weights['vertical'] +
        horizontal_score * weights['horizontal'] +
        normalized_distance_score * weights['distance'] +
        alignment_score * weights['alignment']
    )
    
    # 應用介入懲罰和佈局懲罰（乘法因子）
    layout_penalty = 1.0
    if cross_column_analysis:
        layout_penalty = cross_column_analysis['cross_column_penalty']
    
    final_score = base_score * intervening_penalty * layout_penalty
    
    computation_time = time.time() - start_time
    
    # 構建詳細結果
    result = {
        'final_score': final_score,
        'component_scores': {
            'vertical': vertical_result['score'],
            'horizontal': horizontal_score,
            'distance': normalized_distance_score,
            'alignment': alignment_score,
            'intervening_penalty': intervening_penalty,
            'layout_penalty': layout_penalty
        },
        'details': {
            'vertical_gap': vertical_result['gap'],
            'direction_weight': vertical_result['weight'],
            'horizontal_overlap': horizontal_score,
            'base_score': base_score,
            'relationship': vertical_result['relationship']
        },
        'performance': {
            'cache_hit': False,
            'computation_time': computation_time,
            'cache_enabled': enable_cache
        }
    }
    
    # 添加佈局分析信息（如果可用）
    if column_info:
        result['layout_info'] = {
            'layout_type': column_info['layout_type'],
            'column_count': column_info['column_count'],
            'confidence': column_info['confidence']
        }
    
    if cross_column_analysis:
        result['cross_column_info'] = {
            'text_column': cross_column_analysis['text_column'],
            'image_column': cross_column_analysis['image_column'],
            'is_same_column': cross_column_analysis['is_same_column'],
            'column_distance': cross_column_analysis['column_distance'],
            'cross_column_penalty': cross_column_analysis['cross_column_penalty']
        }
    
    # 存入緩存
    if enable_cache:
        cache_manager.put(CacheType.SPATIAL, cache_key, result)
    
    return result

def get_performance_stats() -> Dict[str, Any]:
    """獲取性能統計信息"""
    stats = cache_manager.get_stats()
    
    # 計算總體統計
    total_hits = sum(s.hits for s in stats.values())
    total_misses = sum(s.misses for s in stats.values())
    total_requests = total_hits + total_misses
    overall_hit_rate = total_hits / total_requests if total_requests > 0 else 0
    
    return {
        'cache_stats_by_type': {
            cache_type: {
                'hits': stat.hits,
                'misses': stat.misses,
                'hit_rate': stat.hit_rate(),
                'size': stat.size,
                'memory_usage_mb': stat.memory_usage_bytes / (1024 * 1024),
                'evictions': stat.evictions
            }
            for cache_type, stat in stats.items()
        },
        'overall_stats': {
            'total_hits': total_hits,
            'total_misses': total_misses,
            'total_requests': total_requests,
            'overall_hit_rate': overall_hit_rate,
            'total_memory_usage_mb': sum(s.memory_usage_bytes for s in stats.values()) / (1024 * 1024)
        }
    }

def clear_cache():
    """清空所有緩存"""
    cache_manager.clear()
    logger.info("已清空所有緩存")

def identify_document_type(
    all_elements: List[Any], 
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    識別文檔類型
    
    Args:
        all_elements: 所有文檔元素（文本塊和圖片）
        metadata: 文檔元數據（文件名、頁數等）
        
    Returns:
        Dict[str, Any]: 文檔類型識別結果
    """
    if not all_elements:
        return {
            'document_type': DocumentType.UNKNOWN,
            'confidence': 0.0,
            'features': {},
            'reasoning': '無足夠元素進行分析'
        }
    
    # 提取文檔特徵
    features = _extract_document_features(all_elements, metadata)
    
    # 基於規則的文檔類型識別
    type_scores = {}
    
    # 1. 學術論文特徵
    academic_score = _calculate_academic_paper_score(features)
    type_scores[DocumentType.ACADEMIC_PAPER] = academic_score
    
    # 2. 技術手冊特徵
    manual_score = _calculate_technical_manual_score(features)
    type_scores[DocumentType.TECHNICAL_MANUAL] = manual_score
    
    # 3. 演示文稿特徵
    presentation_score = _calculate_presentation_score(features)
    type_scores[DocumentType.PRESENTATION] = presentation_score
    
    # 4. 報告特徵
    report_score = _calculate_report_score(features)
    type_scores[DocumentType.REPORT] = report_score
    
    # 5. 雜誌特徵
    magazine_score = _calculate_magazine_score(features)
    type_scores[DocumentType.MAGAZINE] = magazine_score
    
    # 6. 書籍特徵
    book_score = _calculate_book_score(features)
    type_scores[DocumentType.BOOK] = book_score
    
    # 找出最高分的類型
    best_type = max(type_scores.keys(), key=lambda x: type_scores[x])
    best_score = type_scores[best_type]
    
    # 如果最高分太低，歸類為未知
    if best_score < 0.3:
        best_type = DocumentType.UNKNOWN
        best_score = 0.0
    
    logger.debug(f"文檔類型識別: {best_type.value}, 置信度: {best_score:.3f}")
    
    return {
        'document_type': best_type,
        'confidence': best_score,
        'type_scores': {k.value: v for k, v in type_scores.items()},
        'features': features,
        'reasoning': _generate_reasoning(best_type, features)
    }

def _extract_document_features(all_elements: List[Any], metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """提取文檔特徵"""
    
    # 統計基本信息
    text_blocks = []
    images = []
    
    for element in all_elements:
        if hasattr(element, 'content') or hasattr(element, 'text'):
            text_blocks.append(element)
        elif hasattr(element, 'filename') or hasattr(element, 'data'):
            images.append(element)
    
    total_elements = len(all_elements)
    text_count = len(text_blocks)
    image_count = len(images)
    
    # 計算佈局特徵
    layout_info = detect_layout_columns(all_elements)
    
    # 計算密度特徵
    if all_elements:
        bboxes = []
        for element in all_elements:
            bbox = element if hasattr(element, 'left') else getattr(element, 'bbox', None)
            if bbox:
                bboxes.append(bbox)
        
        if bboxes:
            total_area = sum(bbox.width * bbox.height for bbox in bboxes)
            page_area = layout_info.get('page_width', 600) * 800  # 假設高度800
            density = total_area / page_area if page_area > 0 else 0
        else:
            density = 0
    else:
        density = 0
    
    # 分析文本特徵
    text_features = _analyze_text_features(text_blocks)
    
    # 分析圖片特徵
    image_features = _analyze_image_features(images)
    
    return {
        'total_elements': total_elements,
        'text_count': text_count,
        'image_count': image_count,
        'text_image_ratio': text_count / max(image_count, 1),
        'layout_type': layout_info['layout_type'],
        'column_count': layout_info['column_count'],
        'content_density': density,
        'text_features': text_features,
        'image_features': image_features,
        'metadata': metadata or {}
    }

def _analyze_text_features(text_blocks: List[Any]) -> Dict[str, Any]:
    """分析文本特徵"""
    
    if not text_blocks:
        return {'avg_length': 0, 'total_length': 0, 'variation': 0}
    
    lengths = []
    total_length = 0
    
    for block in text_blocks:
        content = getattr(block, 'content', '') or getattr(block, 'text', '')
        length = len(content) if content else 0
        lengths.append(length)
        total_length += length
    
    avg_length = total_length / len(text_blocks) if text_blocks else 0
    length_variation = np.std(lengths) if lengths else 0
    
    return {
        'avg_length': avg_length,
        'total_length': total_length,
        'variation': length_variation,
        'block_count': len(text_blocks)
    }

def _analyze_image_features(images: List[Any]) -> Dict[str, Any]:
    """分析圖片特徵"""
    
    if not images:
        return {'count': 0, 'avg_size': 0, 'size_variation': 0}
    
    sizes = []
    for image in images:
        bbox = image if hasattr(image, 'width') else getattr(image, 'bbox', None)
        if bbox:
            size = bbox.width * bbox.height
            sizes.append(size)
    
    avg_size = np.mean(sizes) if sizes else 0
    size_variation = np.std(sizes) if sizes else 0
    
    return {
        'count': len(images),
        'avg_size': avg_size,
        'size_variation': size_variation
    }

def _calculate_academic_paper_score(features: Dict[str, Any]) -> float:
    """計算學術論文分數"""
    score = 0.0
    
    # 學術論文通常是單欄或雙欄
    if features['layout_type'] in ['single_column', 'double_column']:
        score += 0.3
    
    # 文字密度較高，圖片較少
    if features['text_image_ratio'] > 5:
        score += 0.2
    
    # 文本塊較長（包含段落）
    if features['text_features']['avg_length'] > 100:
        score += 0.2
    
    # 內容密度適中
    if 0.1 < features['content_density'] < 0.4:
        score += 0.2
    
    # 圖片數量適中
    if 1 <= features['image_count'] <= 10:
        score += 0.1
    
    return min(score, 1.0)

def _calculate_technical_manual_score(features: Dict[str, Any]) -> float:
    """計算技術手冊分數"""
    score = 0.0
    
    # 技術手冊通常有較多圖片
    if features['text_image_ratio'] < 8 and features['image_count'] > 2:
        score += 0.3
    
    # 佈局相對規整
    if features['layout_type'] in ['single_column', 'double_column']:
        score += 0.2
    
    # 文本塊長度變化較大（標題、段落、步驟）
    if features['text_features']['variation'] > 50:
        score += 0.2
    
    # 內容密度較高
    if features['content_density'] > 0.2:
        score += 0.2
    
    # 元素總數較多
    if features['total_elements'] > 20:
        score += 0.1
    
    return min(score, 1.0)

def _calculate_presentation_score(features: Dict[str, Any]) -> float:
    """計算演示文稿分數"""
    score = 0.0
    
    # 演示文稿文字較少，圖片較多
    if features['text_image_ratio'] < 5 and features['image_count'] > 1:
        score += 0.4
    
    # 內容密度較低（簡潔）
    if features['content_density'] < 0.3:
        score += 0.2
    
    # 文本塊較短（要點式）
    if features['text_features']['avg_length'] < 80:
        score += 0.2
    
    # 可能是單欄或複雜佈局
    if features['layout_type'] in ['single_column', 'complex_layout']:
        score += 0.2
    
    return min(score, 1.0)

def _calculate_report_score(features: Dict[str, Any]) -> float:
    """計算報告分數"""
    score = 0.0
    
    # 報告文字和圖片比例適中
    if 3 <= features['text_image_ratio'] <= 15:
        score += 0.3
    
    # 通常是單欄佈局
    if features['layout_type'] == 'single_column':
        score += 0.2
    
    # 文本長度適中
    if 50 < features['text_features']['avg_length'] < 200:
        score += 0.2
    
    # 內容密度適中
    if 0.15 < features['content_density'] < 0.5:
        score += 0.2
    
    # 有一定數量的圖片
    if features['image_count'] >= 1:
        score += 0.1
    
    return min(score, 1.0)

def _calculate_magazine_score(features: Dict[str, Any]) -> float:
    """計算雜誌分數"""
    score = 0.0
    
    # 雜誌通常多欄佈局
    if features['column_count'] >= 2:
        score += 0.3
    
    # 圖片較多
    if features['image_count'] > 3 and features['text_image_ratio'] < 10:
        score += 0.3
    
    # 內容密度較高
    if features['content_density'] > 0.3:
        score += 0.2
    
    # 文本塊長度變化大
    if features['text_features']['variation'] > 30:
        score += 0.2
    
    return min(score, 1.0)

def _calculate_book_score(features: Dict[str, Any]) -> float:
    """計算書籍分數"""
    score = 0.0
    
    # 書籍通常單欄或雙欄
    if features['layout_type'] in ['single_column', 'double_column']:
        score += 0.3
    
    # 文字為主，圖片較少
    if features['text_image_ratio'] > 10:
        score += 0.3
    
    # 文本塊較長
    if features['text_features']['avg_length'] > 80:
        score += 0.2
    
    # 內容密度適中
    if 0.2 < features['content_density'] < 0.6:
        score += 0.2
    
    return min(score, 1.0)

def _generate_reasoning(doc_type: DocumentType, features: Dict[str, Any]) -> str:
    """生成識別推理"""
    
    reasoning_parts = []
    
    # 佈局特徵
    layout = features['layout_type']
    columns = features['column_count']
    reasoning_parts.append(f"佈局類型: {layout} ({columns}欄)")
    
    # 內容比例
    ratio = features['text_image_ratio']
    reasoning_parts.append(f"文字圖片比例: {ratio:.1f}")
    
    # 密度特徵
    density = features['content_density']
    reasoning_parts.append(f"內容密度: {density:.2f}")
    
    # 特定類型的推理
    if doc_type == DocumentType.ACADEMIC_PAPER:
        reasoning_parts.append("具有學術論文特徵：規整佈局、文字為主")
    elif doc_type == DocumentType.TECHNICAL_MANUAL:
        reasoning_parts.append("具有技術手冊特徵：圖文並茂、結構化內容")
    elif doc_type == DocumentType.PRESENTATION:
        reasoning_parts.append("具有演示文稿特徵：簡潔佈局、視覺化內容")
    elif doc_type == DocumentType.MAGAZINE:
        reasoning_parts.append("具有雜誌特徵：多欄佈局、豐富視覺元素")
    elif doc_type == DocumentType.BOOK:
        reasoning_parts.append("具有書籍特徵：文字為主、規整排版")
    
    return "; ".join(reasoning_parts)

def get_document_type_weights(doc_type: DocumentType) -> Dict[str, float]:
    """
    根據文檔類型獲取空間分析權重
    
    Args:
        doc_type: 文檔類型
        
    Returns:
        Dict[str, float]: 空間分析權重配置
    """
    
    # 默認權重
    default_weights = {
        'vertical': 0.4,
        'horizontal': 0.25,
        'distance': 0.2,
        'alignment': 0.1,
        'layout_penalty_factor': 1.0,
        'caption_boost_factor': 1.0
    }
    
    # 基於文檔類型的權重調整
    if doc_type == DocumentType.ACADEMIC_PAPER:
        # 學術論文：更重視垂直關係和Caption
        return {
            **default_weights,
            'vertical': 0.45,
            'horizontal': 0.3,
            'caption_boost_factor': 1.2
        }
    
    elif doc_type == DocumentType.TECHNICAL_MANUAL:
        # 技術手冊：平衡各因素，重視佈局
        return {
            **default_weights,
            'vertical': 0.35,
            'horizontal': 0.25,
            'distance': 0.25,
            'layout_penalty_factor': 1.3
        }
    
    elif doc_type == DocumentType.PRESENTATION:
        # 演示文稿：更靈活的關聯規則
        return {
            **default_weights,
            'vertical': 0.3,
            'horizontal': 0.2,
            'distance': 0.3,
            'alignment': 0.2,
            'layout_penalty_factor': 0.8
        }
    
    elif doc_type == DocumentType.MAGAZINE:
        # 雜誌：重視佈局和對齊
        return {
            **default_weights,
            'vertical': 0.3,
            'horizontal': 0.2,
            'alignment': 0.2,
            'layout_penalty_factor': 1.4
        }
    
    elif doc_type == DocumentType.BOOK:
        # 書籍：重視閱讀順序
        return {
            **default_weights,
            'vertical': 0.5,
            'horizontal': 0.3,
            'caption_boost_factor': 1.1
        }
    
    else:
        return default_weights

# 導出便捷函數
def quick_spatial_analysis(text_box: BoundingBox, image_box: BoundingBox) -> Tuple[SpatialFeatures, SpatialRelation]:
    """快速空間分析"""
    analyzer = SpatialAnalyzer()
    features = analyzer.calculate_spatial_features(text_box, image_box)
    allen_analyzer = AllenLogicAnalyzer()
    relation = allen_analyzer.analyze_spatial_relation(text_box, image_box)
    return features, relation

