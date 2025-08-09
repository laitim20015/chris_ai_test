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

from typing import List, Dict, Tuple, Optional, NamedTuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
from src.association.allen_logic import (
    AllenLogicAnalyzer, SpatialRelation, BoundingBox, 
    SpatialDirection, AllenRelation
)
from src.config.logging_config import get_logger, log_performance

logger = get_logger("spatial_analyzer")

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

class SpatialAnalyzer:
    """空間關係分析器"""
    
    def __init__(self, 
                 alignment_tolerance: float = 10.0,
                 distance_normalization: bool = True):
        """
        初始化空間分析器
        
        Args:
            alignment_tolerance: 對齊容差（像素）
            distance_normalization: 是否進行距離標準化
        """
        self.alignment_tolerance = alignment_tolerance
        self.distance_normalization = distance_normalization
        self.allen_analyzer = AllenLogicAnalyzer()
        
        # 佈局分析參數
        self.layout_params = {
            "column_gap_threshold": 50,      # 欄間距閾值
            "row_gap_threshold": 20,         # 行間距閾值
            "grid_regularity_threshold": 0.8 # 網格規律性閾值
        }
        
        logger.debug("空間關係分析器初始化完成")
    
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

# 導出便捷函數
def quick_spatial_analysis(text_box: BoundingBox, image_box: BoundingBox) -> Tuple[SpatialFeatures, SpatialRelation]:
    """快速空間分析"""
    analyzer = SpatialAnalyzer()
    features = analyzer.calculate_spatial_features(text_box, image_box)
    allen_analyzer = AllenLogicAnalyzer()
    relation = allen_analyzer.analyze_spatial_relation(text_box, image_box)
    return features, relation

