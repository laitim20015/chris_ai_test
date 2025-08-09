"""
Allen區間邏輯空間關係分析器
Allen Interval Logic Spatial Relation Analyzer

基於Allen時間間隔邏輯的13種關係，應用於2D空間中的圖文關聯分析。
Allen邏輯原本用於時間間隔關係，這裡擴展用於空間矩形區域的關係分析。

Allen的13種基本關係：
1. precedes (A < B): A完全在B之前
2. meets (A m B): A與B相鄰
3. overlaps (A o B): A與B重疊
4. starts (A s B): A從B開始
5. during (A d B): A在B期間
6. finishes (A f B): A在B結束
7. equals (A = B): A與B相等

以及它們的逆關係：
8. preceded-by (A > B)
9. met-by (A mi B)
10. overlapped-by (A oi B)
11. started-by (A si B)
12. contains (A di B)
13. finished-by (A fi B)

擴展到2D空間的方向關係：
- above/below: 垂直方向的空間關係
- left-of/right-of: 水平方向的空間關係
- adjacent: 鄰接關係
- distant: 遠距離關係
"""

from typing import List, Dict, Tuple, Optional, NamedTuple, Union
from enum import Enum
import numpy as np
from dataclasses import dataclass
from src.config.logging_config import get_logger, log_performance

logger = get_logger("allen_logic")

class AllenRelation(Enum):
    """Allen區間邏輯的13種基本關係"""
    
    # 基本關係
    PRECEDES = "precedes"           # A < B
    MEETS = "meets"                 # A m B  
    OVERLAPS = "overlaps"           # A o B
    STARTS = "starts"               # A s B
    DURING = "during"               # A d B
    FINISHES = "finishes"           # A f B
    EQUALS = "equals"               # A = B
    
    # 逆關係
    PRECEDED_BY = "preceded_by"     # A > B
    MET_BY = "met_by"              # A mi B
    OVERLAPPED_BY = "overlapped_by" # A oi B
    STARTED_BY = "started_by"       # A si B
    CONTAINS = "contains"           # A di B
    FINISHED_BY = "finished_by"     # A fi B

class SpatialDirection(Enum):
    """2D空間方向擴展"""
    
    ABOVE = "above"                 # 在...上方
    BELOW = "below"                 # 在...下方
    LEFT_OF = "left_of"            # 在...左側
    RIGHT_OF = "right_of"          # 在...右側
    ADJACENT = "adjacent"           # 鄰接
    DISTANT = "distant"            # 遠距離

@dataclass
class Interval:
    """一維區間"""
    start: float
    end: float
    
    def __post_init__(self):
        """確保start <= end"""
        if self.start > self.end:
            self.start, self.end = self.end, self.start
    
    @property
    def length(self) -> float:
        """區間長度"""
        return self.end - self.start
    
    @property
    def center(self) -> float:
        """區間中心"""
        return (self.start + self.end) / 2

@dataclass
class BoundingBox:
    """2D邊界框"""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def left(self) -> float:
        return self.x
    
    @property
    def right(self) -> float:
        return self.x + self.width
    
    @property
    def top(self) -> float:
        return self.y
    
    @property
    def bottom(self) -> float:
        return self.y + self.height
    
    @property
    def center_x(self) -> float:
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        return self.y + self.height / 2
    
    @property
    def x_interval(self) -> Interval:
        """水平區間"""
        return Interval(self.left, self.right)
    
    @property
    def y_interval(self) -> Interval:
        """垂直區間"""
        return Interval(self.top, self.bottom)
    
    @property
    def area(self) -> float:
        """面積"""
        return self.width * self.height

class SpatialRelation(NamedTuple):
    """空間關係結果"""
    horizontal: AllenRelation
    vertical: AllenRelation
    direction: Optional[SpatialDirection]
    confidence: float
    distance: float

class IntervalRelation(NamedTuple):
    """區間關係結果"""
    relation: AllenRelation
    confidence: float
    overlap_ratio: float

class AllenLogicAnalyzer:
    """Allen區間邏輯分析器"""
    
    def __init__(self, tolerance: float = 1e-6):
        """
        初始化分析器
        
        Args:
            tolerance: 數值比較容差
        """
        self.tolerance = tolerance
        
        # Allen關係的符號表示
        self.relation_symbols = {
            AllenRelation.PRECEDES: "<",
            AllenRelation.MEETS: "m",
            AllenRelation.OVERLAPS: "o", 
            AllenRelation.STARTS: "s",
            AllenRelation.DURING: "d",
            AllenRelation.FINISHES: "f",
            AllenRelation.EQUALS: "=",
            AllenRelation.PRECEDED_BY: ">",
            AllenRelation.MET_BY: "mi",
            AllenRelation.OVERLAPPED_BY: "oi",
            AllenRelation.STARTED_BY: "si",
            AllenRelation.CONTAINS: "di",
            AllenRelation.FINISHED_BY: "fi"
        }
        
        logger.debug("Allen邏輯分析器初始化完成")
    
    def analyze_interval_relation(self, interval_a: Interval, interval_b: Interval) -> IntervalRelation:
        """
        分析兩個一維區間的Allen關係
        
        Args:
            interval_a: 區間A
            interval_b: 區間B
            
        Returns:
            IntervalRelation: 區間關係結果
        """
        a_start, a_end = interval_a.start, interval_a.end
        b_start, b_end = interval_b.start, interval_b.end
        
        # 計算重疊部分
        overlap_start = max(a_start, b_start)
        overlap_end = min(a_end, b_end)
        overlap_length = max(0, overlap_end - overlap_start)
        
        # 計算重疊比例
        total_length = max(interval_a.length, interval_b.length)
        overlap_ratio = overlap_length / total_length if total_length > 0 else 0
        
        # 確定Allen關係
        relation, confidence = self._determine_allen_relation(
            a_start, a_end, b_start, b_end, overlap_ratio
        )
        
        logger.debug(f"區間關係分析: {interval_a} vs {interval_b} -> {relation.value}")
        
        return IntervalRelation(
            relation=relation,
            confidence=confidence,
            overlap_ratio=overlap_ratio
        )
    
    def _determine_allen_relation(self, a_start: float, a_end: float, 
                                b_start: float, b_end: float, 
                                overlap_ratio: float) -> Tuple[AllenRelation, float]:
        """
        確定Allen關係
        
        Args:
            a_start, a_end: 區間A的開始和結束
            b_start, b_end: 區間B的開始和結束
            overlap_ratio: 重疊比例
            
        Returns:
            Tuple[AllenRelation, float]: (關係, 置信度)
        """
        # 使用容差進行比較
        def equal(x, y): return abs(x - y) <= self.tolerance
        def less_than(x, y): return x < y - self.tolerance
        def greater_than(x, y): return x > y + self.tolerance
        
        # 基本情況檢查
        if equal(a_start, b_start) and equal(a_end, b_end):
            return AllenRelation.EQUALS, 1.0
        
        if less_than(a_end, b_start):
            if equal(a_end, b_start):
                return AllenRelation.MEETS, 0.95
            else:
                return AllenRelation.PRECEDES, 0.9
        
        if greater_than(a_start, b_end):
            if equal(a_start, b_end):
                return AllenRelation.MET_BY, 0.95
            else:
                return AllenRelation.PRECEDED_BY, 0.9
        
        # 重疊情況
        if overlap_ratio > 0:
            # 檢查starts關係
            if equal(a_start, b_start):
                if less_than(a_end, b_end):
                    return AllenRelation.STARTS, 0.9
                else:
                    return AllenRelation.STARTED_BY, 0.9
            
            # 檢查finishes關係
            if equal(a_end, b_end):
                if greater_than(a_start, b_start):
                    return AllenRelation.FINISHES, 0.9
                else:
                    return AllenRelation.FINISHED_BY, 0.9
            
            # 檢查during/contains關係
            if greater_than(a_start, b_start) and less_than(a_end, b_end):
                return AllenRelation.DURING, min(0.9, overlap_ratio + 0.1)
            
            if less_than(a_start, b_start) and greater_than(a_end, b_end):
                return AllenRelation.CONTAINS, min(0.9, overlap_ratio + 0.1)
            
            # 一般重疊情況
            if less_than(a_start, b_start) and less_than(a_end, b_end):
                return AllenRelation.OVERLAPS, max(0.5, overlap_ratio)
            else:
                return AllenRelation.OVERLAPPED_BY, max(0.5, overlap_ratio)
        
        # 默認情況（理論上不應該到達這裡）
        return AllenRelation.OVERLAPS, 0.1
    
    @log_performance("analyze_spatial_relation")
    def analyze_spatial_relation(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> SpatialRelation:
        """
        分析兩個2D邊界框的空間關係
        
        Args:
            bbox_a: 邊界框A（通常是文本塊）
            bbox_b: 邊界框B（通常是圖片）
            
        Returns:
            SpatialRelation: 空間關係結果
        """
        # 分析水平和垂直關係
        h_relation = self.analyze_interval_relation(bbox_a.x_interval, bbox_b.x_interval)
        v_relation = self.analyze_interval_relation(bbox_a.y_interval, bbox_b.y_interval)
        
        # 計算中心距離
        distance = self._calculate_center_distance(bbox_a, bbox_b)
        
        # 確定主要方向
        direction = self._determine_primary_direction(bbox_a, bbox_b, h_relation, v_relation)
        
        # 計算綜合置信度
        confidence = self._calculate_spatial_confidence(h_relation, v_relation, distance, bbox_a, bbox_b)
        
        result = SpatialRelation(
            horizontal=h_relation.relation,
            vertical=v_relation.relation,
            direction=direction,
            confidence=confidence,
            distance=distance
        )
        
        logger.debug(f"空間關係分析完成: {result}")
        return result
    
    def _calculate_center_distance(self, bbox_a: BoundingBox, bbox_b: BoundingBox) -> float:
        """計算兩個邊界框中心點的歐幾里得距離"""
        dx = bbox_a.center_x - bbox_b.center_x
        dy = bbox_a.center_y - bbox_b.center_y
        return np.sqrt(dx * dx + dy * dy)
    
    def _determine_primary_direction(self, bbox_a: BoundingBox, bbox_b: BoundingBox,
                                   h_relation: IntervalRelation, 
                                   v_relation: IntervalRelation) -> Optional[SpatialDirection]:
        """
        確定主要的空間方向
        
        Args:
            bbox_a, bbox_b: 邊界框
            h_relation, v_relation: 水平和垂直關係
            
        Returns:
            Optional[SpatialDirection]: 主要方向
        """
        # 計算中心點偏移
        dx = bbox_a.center_x - bbox_b.center_x
        dy = bbox_a.center_y - bbox_b.center_y
        
        # 計算距離閾值（基於框的大小）
        avg_width = (bbox_a.width + bbox_b.width) / 2
        avg_height = (bbox_a.height + bbox_b.height) / 2
        
        # 判斷是否鄰接
        h_adjacent = h_relation.relation in [AllenRelation.MEETS, AllenRelation.MET_BY]
        v_adjacent = v_relation.relation in [AllenRelation.MEETS, AllenRelation.MET_BY]
        
        if h_adjacent or v_adjacent:
            return SpatialDirection.ADJACENT
        
        # 判斷主要方向
        if abs(dx) > abs(dy):
            # 水平方向佔主導
            if dx > avg_width * 0.5:
                return SpatialDirection.RIGHT_OF
            elif dx < -avg_width * 0.5:
                return SpatialDirection.LEFT_OF
        else:
            # 垂直方向佔主導
            if dy > avg_height * 0.5:
                return SpatialDirection.BELOW
            elif dy < -avg_height * 0.5:
                return SpatialDirection.ABOVE
        
        # 如果距離很遠
        distance = np.sqrt(dx * dx + dy * dy)
        max_dimension = max(avg_width, avg_height)
        if distance > max_dimension * 3:
            return SpatialDirection.DISTANT
        
        return None
    
    def _calculate_spatial_confidence(self, h_relation: IntervalRelation, 
                                    v_relation: IntervalRelation,
                                    distance: float, bbox_a: BoundingBox, 
                                    bbox_b: BoundingBox) -> float:
        """
        計算空間關係的綜合置信度
        
        Args:
            h_relation, v_relation: 水平和垂直關係
            distance: 中心距離
            bbox_a, bbox_b: 邊界框
            
        Returns:
            float: 置信度 (0-1)
        """
        # 基礎置信度（水平和垂直關係的平均值）
        base_confidence = (h_relation.confidence + v_relation.confidence) / 2
        
        # 距離調整因子
        avg_dimension = ((bbox_a.width + bbox_a.height) + (bbox_b.width + bbox_b.height)) / 4
        normalized_distance = distance / max(avg_dimension, 1)
        
        # 距離太遠會降低置信度
        distance_factor = 1.0
        if normalized_distance > 5:
            distance_factor = max(0.3, 1.0 - (normalized_distance - 5) * 0.1)
        
        # 重疊調整因子
        overlap_factor = 1.0
        if h_relation.overlap_ratio > 0 or v_relation.overlap_ratio > 0:
            avg_overlap = (h_relation.overlap_ratio + v_relation.overlap_ratio) / 2
            overlap_factor = 1.0 + avg_overlap * 0.2  # 重疊會提高置信度
        
        final_confidence = base_confidence * distance_factor * overlap_factor
        return min(1.0, max(0.1, final_confidence))

def analyze_spatial_relations(text_boxes: List[BoundingBox], 
                            image_boxes: List[BoundingBox],
                            analyzer: Optional[AllenLogicAnalyzer] = None) -> List[List[SpatialRelation]]:
    """
    批量分析文本框和圖片框之間的空間關係
    
    Args:
        text_boxes: 文本邊界框列表
        image_boxes: 圖片邊界框列表  
        analyzer: Allen邏輯分析器實例
        
    Returns:
        List[List[SpatialRelation]]: 關係矩陣 [text_idx][image_idx]
    """
    if analyzer is None:
        analyzer = AllenLogicAnalyzer()
    
    relations = []
    
    for i, text_box in enumerate(text_boxes):
        text_relations = []
        for j, image_box in enumerate(image_boxes):
            relation = analyzer.analyze_spatial_relation(text_box, image_box)
            text_relations.append(relation)
        relations.append(text_relations)
    
    logger.info(f"批量空間關係分析完成: {len(text_boxes)}個文本框 x {len(image_boxes)}個圖片框")
    return relations

def get_allen_relations_matrix() -> Dict[Tuple[AllenRelation, AllenRelation], List[AllenRelation]]:
    """
    獲取Allen關係的組合轉換矩陣
    用於複合關係推理
    
    Returns:
        Dict: 關係組合矩陣
    """
    # 這是一個簡化版本，完整的Allen代數包含更復雜的關係組合規則
    basic_combinations = {
        (AllenRelation.PRECEDES, AllenRelation.PRECEDES): [AllenRelation.PRECEDES],
        (AllenRelation.MEETS, AllenRelation.PRECEDES): [AllenRelation.PRECEDES],
        (AllenRelation.OVERLAPS, AllenRelation.OVERLAPS): [AllenRelation.OVERLAPS],
        (AllenRelation.DURING, AllenRelation.CONTAINS): [AllenRelation.DURING],
        (AllenRelation.EQUALS, AllenRelation.EQUALS): [AllenRelation.EQUALS],
    }
    
    return basic_combinations

def calculate_spatial_score(relation: SpatialRelation, weight_spatial: float = 0.3) -> float:
    """
    計算空間關係的評分（用於最終的關聯度計算）
    
    Args:
        relation: 空間關係
        weight_spatial: 空間權重（項目規則規定為0.3）
        
    Returns:
        float: 空間評分
    """
    base_score = relation.confidence
    
    # 根據關係類型調整分數
    direction_boost = {
        SpatialDirection.ADJACENT: 0.3,    # 鄰接關係加分
        SpatialDirection.ABOVE: 0.2,       # 上下關係加分
        SpatialDirection.BELOW: 0.2,
        SpatialDirection.LEFT_OF: 0.1,     # 左右關係較少加分
        SpatialDirection.RIGHT_OF: 0.1,
        SpatialDirection.DISTANT: -0.2,    # 遠距離關係扣分
    }
    
    boost = direction_boost.get(relation.direction, 0)
    adjusted_score = min(1.0, base_score + boost)
    
    return adjusted_score * weight_spatial

# 導出便捷函數
def quick_spatial_analysis(text_box: BoundingBox, image_box: BoundingBox) -> SpatialRelation:
    """快速空間關係分析"""
    analyzer = AllenLogicAnalyzer()
    return analyzer.analyze_spatial_relation(text_box, image_box)
