"""
Caption檢測器 - 圖文關聯分析中最關鍵的組件
Caption Detector - The Most Critical Component in Image-Text Association Analysis

根據項目規則，Caption檢測擁有40%的權重，是所有關聯算法中最重要的。
Caption是指圖片的標題、說明文字或引用文本，通常包含：

1. 圖表編號標識：如"圖1"、"Figure 1"、"Table 2"等
2. 描述性文字：對圖片內容的說明
3. 引用語句：如"如圖所示"、"見圖"等

檢測策略：
1. 正則表達式模式匹配（主要方法）
2. 位置關係分析（Caption通常在圖片上方或下方）
3. 文本格式特徵（字體、樣式等）
4. 語義內容分析（描述性詞彙）

Caption檢測的準確率直接影響整個關聯分析的效果。
"""

import re
from typing import List, Dict, Tuple, Optional, NamedTuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
from src.association.allen_logic import BoundingBox, SpatialDirection
from src.config.logging_config import get_logger, log_performance

logger = get_logger("caption_detector")

class CaptionType(Enum):
    """Caption類型枚舉"""
    
    FIGURE_NUMBER = "figure_number"        # 圖片編號：圖1, Figure 1
    TABLE_NUMBER = "table_number"          # 表格編號：表1, Table 1  
    CHART_DIAGRAM = "chart_diagram"        # 圖表類型：Chart 1, Diagram 1
    REFERENCE = "reference"                # 引用：如圖所示, 見圖
    DESCRIPTION = "description"            # 描述性文字
    TITLE = "title"                       # 標題類Caption
    UNKNOWN = "unknown"                   # 未知類型

class CaptionPosition(Enum):
    """Caption位置枚舉"""
    
    ABOVE = "above"                       # 圖片上方
    BELOW = "below"                       # 圖片下方  
    LEFT = "left"                         # 圖片左側
    RIGHT = "right"                       # 圖片右側
    INSIDE = "inside"                     # 圖片內部
    DISTANT = "distant"                   # 遠距離
    UNKNOWN = "unknown"                   # 位置不明

@dataclass
class CaptionPattern:
    """Caption匹配模式"""
    pattern: str                          # 正則表達式模式
    caption_type: CaptionType            # Caption類型
    confidence_base: float               # 基礎置信度
    description: str                     # 模式描述
    language: str = "mixed"              # 適用語言

class CaptionMatch(NamedTuple):
    """Caption匹配結果"""
    text: str                            # 匹配的文本
    caption_type: CaptionType           # Caption類型
    position: CaptionPosition           # 相對位置
    confidence: float                   # 置信度
    pattern_used: str                   # 使用的模式
    start_pos: int                      # 文本中的開始位置
    end_pos: int                        # 文本中的結束位置

class CaptionDetector:
    """Caption檢測器 - 核心組件（40%權重）"""
    
    def __init__(self, custom_patterns: Optional[List[CaptionPattern]] = None):
        """
        初始化Caption檢測器
        
        Args:
            custom_patterns: 自定義匹配模式
        """
        self.patterns = self._load_default_patterns()
        
        if custom_patterns:
            self.patterns.extend(custom_patterns)
        
        # 編譯正則表達式以提高性能
        self.compiled_patterns = self._compile_patterns()
        
        # 位置分析閾值
        self.position_thresholds = {
            "close_distance": 50,        # 近距離閾值（像素）
            "medium_distance": 150,      # 中距離閾值
            "far_distance": 300,         # 遠距離閾值
        }
        
        logger.info(f"Caption檢測器初始化完成，載入模式數量: {len(self.patterns)}")
    
    def _load_default_patterns(self) -> List[CaptionPattern]:
        """
        載入默認的Caption匹配模式
        嚴格按照項目規則定義的模式
        
        Returns:
            List[CaptionPattern]: 默認模式列表
        """
        patterns = [
            # 1. 圖片編號模式（中英文）
            CaptionPattern(
                pattern=r'^(圖|圖片|Figure|Fig\.?)\s*[：:]*\s*(\d+)',
                caption_type=CaptionType.FIGURE_NUMBER,
                confidence_base=0.95,
                description="圖片編號標識",
                language="mixed"
            ),
            
            # 2. 表格編號模式
            CaptionPattern(
                pattern=r'^(表|表格|Table|Tab\.?)\s*[：:]*\s*(\d+)',
                caption_type=CaptionType.TABLE_NUMBER,
                confidence_base=0.95,
                description="表格編號標識",
                language="mixed"
            ),
            
            # 3. 圖表類型模式
            CaptionPattern(
                pattern=r'^(Chart|Diagram|Image|Graph|Plot)\s*[：:]*\s*(\d+)',
                caption_type=CaptionType.CHART_DIAGRAM,
                confidence_base=0.9,
                description="圖表類型標識",
                language="en"
            ),
            
            # 4. 中文引用模式（項目規則指定）
            CaptionPattern(
                pattern=r'(如圖\s*\d+|見圖\s*\d+|參見圖\s*\d+)',
                caption_type=CaptionType.REFERENCE,
                confidence_base=0.9,
                description="中文圖片引用",
                language="zh"
            ),
            
            # 5. 英文引用模式
            CaptionPattern(
                pattern=r'(see\s+figure\s*\d+|as\s+shown\s+in\s+figure\s*\d+|figure\s*\d+\s+shows)',
                caption_type=CaptionType.REFERENCE,
                confidence_base=0.85,
                description="英文圖片引用",
                language="en"
            ),
            
            # 6. 描述性文字模式
            CaptionPattern(
                pattern=r'(顯示了|表明|說明|展示|描述|示意圖|流程圖)',
                caption_type=CaptionType.DESCRIPTION,
                confidence_base=0.7,
                description="描述性詞彙",
                language="zh"
            ),
            
            # 7. 英文描述性模式
            CaptionPattern(
                pattern=r'(shows|displays|illustrates|demonstrates|depicts|represents)',
                caption_type=CaptionType.DESCRIPTION,
                confidence_base=0.7,
                description="英文描述性詞彙",
                language="en"
            ),
            
            # 8. 標題模式（通常較短且位於圖片附近）
            CaptionPattern(
                pattern=r'^.{5,50}$',  # 5-50字符的短文本
                caption_type=CaptionType.TITLE,
                confidence_base=0.6,
                description="標題型Caption",
                language="mixed"
            ),
            
            # 9. 數學公式引用
            CaptionPattern(
                pattern=r'(公式\s*\d+|equation\s*\d+|formula\s*\d+)',
                caption_type=CaptionType.REFERENCE,
                confidence_base=0.8,
                description="數學公式引用",
                language="mixed"
            ),
            
            # 10. 附錄圖表模式
            CaptionPattern(
                pattern=r'(附圖\s*\d+|appendix\s+figure\s*\d+|附表\s*\d+)',
                caption_type=CaptionType.FIGURE_NUMBER,
                confidence_base=0.85,
                description="附錄圖表標識",
                language="mixed"
            )
        ]
        
        return patterns
    
    def _compile_patterns(self) -> List[Tuple[re.Pattern, CaptionPattern]]:
        """
        編譯正則表達式模式以提高匹配性能
        
        Returns:
            List[Tuple[re.Pattern, CaptionPattern]]: 編譯後的模式列表
        """
        compiled = []
        
        for pattern_obj in self.patterns:
            try:
                compiled_re = re.compile(pattern_obj.pattern, re.IGNORECASE | re.MULTILINE)
                compiled.append((compiled_re, pattern_obj))
            except re.error as e:
                logger.warning(f"正則表達式編譯失敗: {pattern_obj.pattern}, 錯誤: {e}")
        
        logger.debug(f"成功編譯 {len(compiled)} 個Caption匹配模式")
        return compiled
    
    @log_performance("detect_captions")
    def detect_captions(self, text: str, text_bbox: BoundingBox, 
                       image_bbox: BoundingBox) -> List[CaptionMatch]:
        """
        檢測文本中的Caption
        
        Args:
            text: 文本內容
            text_bbox: 文本邊界框
            image_bbox: 圖片邊界框
            
        Returns:
            List[CaptionMatch]: Caption匹配結果列表
        """
        if not text or not text.strip():
            return []
        
        matches = []
        
        # 1. 模式匹配
        pattern_matches = self._match_patterns(text)
        
        # 2. 位置分析
        position = self._analyze_caption_position(text_bbox, image_bbox)
        
        # 3. 生成匹配結果
        for match_info in pattern_matches:
            pattern_obj = match_info['pattern']
            regex_match = match_info['match']
            
            # 計算置信度
            confidence = self._calculate_caption_confidence(
                pattern_obj, position, text, text_bbox, image_bbox
            )
            
            caption_match = CaptionMatch(
                text=regex_match.group(0),
                caption_type=pattern_obj.caption_type,
                position=position,
                confidence=confidence,
                pattern_used=pattern_obj.pattern,
                start_pos=regex_match.start(),
                end_pos=regex_match.end()
            )
            
            matches.append(caption_match)
        
        # 按置信度排序
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.debug(f"Caption檢測完成，找到 {len(matches)} 個匹配")
        return matches
    
    def detect_captions_with_priority(self, candidates: List[Dict], image_bbox: BoundingBox) -> List[CaptionMatch]:
        """
        增強的Caption檢測 - 實施最近上方優先規則
        
        Args:
            candidates: 候選文本塊列表，每個包含 {'text': str, 'bbox': BoundingBox, 'id': str}
            image_bbox: 圖片邊界框
            
        Returns:
            List[CaptionMatch]: 排序後的Caption匹配結果列表
        """
        all_matches = []
        
        # 1. 對每個候選進行Caption檢測
        for candidate in candidates:
            text = candidate.get('text', '')
            text_bbox = candidate.get('bbox')
            text_id = candidate.get('id', '')
            
            if not text or not text_bbox:
                continue
                
            matches = self.detect_captions(text, text_bbox, image_bbox)
            
            # 為每個匹配添加候選信息
            for match in matches:
                enhanced_match = CaptionMatch(
                    text=match.text,
                    caption_type=match.caption_type,
                    position=match.position,
                    confidence=match.confidence,
                    pattern_used=match.pattern_used,
                    start_pos=match.start_pos,
                    end_pos=match.end_pos
                )
                
                # 添加額外信息
                enhanced_match_dict = enhanced_match._asdict()
                enhanced_match_dict['text_id'] = text_id
                enhanced_match_dict['text_bbox'] = text_bbox
                enhanced_match_dict['full_text'] = text
                
                all_matches.append(enhanced_match_dict)
        
        if not all_matches:
            return []
        
        # 2. 應用最近上方優先規則
        prioritized_matches = self._apply_nearest_above_priority(all_matches, image_bbox)
        
        # 3. 轉換回CaptionMatch格式
        result_matches = []
        for match_dict in prioritized_matches:
            caption_match = CaptionMatch(
                text=match_dict['text'],
                caption_type=match_dict['caption_type'],
                position=match_dict['position'],
                confidence=match_dict['confidence'],
                pattern_used=match_dict['pattern_used'],
                start_pos=match_dict['start_pos'],
                end_pos=match_dict['end_pos']
            )
            result_matches.append(caption_match)
        
        logger.debug(f"優先級Caption檢測完成，處理 {len(candidates)} 個候選，找到 {len(result_matches)} 個匹配")
        return result_matches
    
    def _apply_nearest_above_priority(self, matches: List[Dict], image_bbox: BoundingBox) -> List[Dict]:
        """
        實施最近上方優先規則
        
        Args:
            matches: 匹配結果列表
            image_bbox: 圖片邊界框
            
        Returns:
            List[Dict]: 應用優先規則後的匹配列表
        """
        # 1. 分類匹配：上方、下方、其他
        above_matches = []
        below_matches = []
        other_matches = []
        
        for match in matches:
            text_bbox = match['text_bbox']
            
            if text_bbox.bottom <= image_bbox.top:
                # 文本在圖片上方
                vertical_distance = image_bbox.top - text_bbox.bottom
                match['vertical_distance'] = vertical_distance
                match['relative_position'] = 'above'
                above_matches.append(match)
            elif text_bbox.top >= image_bbox.bottom:
                # 文本在圖片下方
                vertical_distance = text_bbox.top - image_bbox.bottom
                match['vertical_distance'] = vertical_distance
                match['relative_position'] = 'below'
                below_matches.append(match)
            else:
                # 重疊或其他情況
                match['vertical_distance'] = 0
                match['relative_position'] = 'overlap'
                other_matches.append(match)
        
        # 2. 應用最近上方優先規則
        if above_matches:
            # 按垂直距離排序（最近的在前）
            above_matches.sort(key=lambda x: x['vertical_distance'])
            
            # 最近的上方匹配獲得顯著加分
            nearest_above = above_matches[0]
            reasonable_distance = image_bbox.height * 2  # 2倍圖片高度內算合理
            
            if nearest_above['vertical_distance'] <= reasonable_distance:
                # 距離合理，給予30%加分
                boost_factor = 1.3
                nearest_above['confidence'] *= boost_factor
                nearest_above['priority_boost'] = boost_factor
                
                # 檢查是否有明確的Caption指示詞
                if self._has_strong_caption_indicators(nearest_above['full_text']):
                    # 有強指示詞，再給予20%加分
                    additional_boost = 1.2
                    nearest_above['confidence'] *= additional_boost
                    nearest_above['caption_indicator_boost'] = additional_boost
                
                logger.debug(f"最近上方匹配獲得優先級提升: {nearest_above['text'][:20]}...")
        
        # 3. 距離懲罰機制
        max_reasonable_distance = image_bbox.height * 3  # 3倍圖片高度
        
        for match in above_matches + below_matches:
            if match['vertical_distance'] > max_reasonable_distance:
                # 距離過遠，應用懲罰
                distance_penalty = max(0.5, 1.0 - (match['vertical_distance'] - max_reasonable_distance) / max_reasonable_distance)
                match['confidence'] *= distance_penalty
                match['distance_penalty'] = distance_penalty
        
        # 4. 合併並按置信度重新排序
        all_processed_matches = above_matches + below_matches + other_matches
        all_processed_matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        return all_processed_matches
    
    def _has_strong_caption_indicators(self, text: str) -> bool:
        """
        檢查文本是否包含強Caption指示詞
        
        Args:
            text: 文本內容
            
        Returns:
            bool: 是否包含強指示詞
        """
        strong_indicators = [
            r'下列?圖\w*',
            r'如圖\s*\d*所示',
            r'見圖\s*\d+',
            r'圖\s*\d+[\.:：]',
            r'表\s*\d+[\.:：]',
            r'圖表\s*\d*[\.:：]',
            r'示意圖[\.:：]',
            r'流程圖[\.:：]',
            r'(下|以下)(圖|表|圖表)[\.:：]',
            r'Figure\s+\d+[\.:：]',
            r'Table\s+\d+[\.:：]',
            r'Chart\s+\d+[\.:：]',
            r'Diagram\s+\d+[\.:：]'
        ]
        
        for pattern in strong_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _match_patterns(self, text: str) -> List[Dict]:
        """
        對文本進行模式匹配
        
        Args:
            text: 文本內容
            
        Returns:
            List[Dict]: 匹配信息列表
        """
        matches = []
        
        for compiled_re, pattern_obj in self.compiled_patterns:
            for match in compiled_re.finditer(text):
                matches.append({
                    'pattern': pattern_obj,
                    'match': match
                })
        
        return matches
    
    def _analyze_caption_position(self, text_bbox: BoundingBox, 
                                image_bbox: BoundingBox) -> CaptionPosition:
        """
        分析Caption相對於圖片的位置
        
        Args:
            text_bbox: 文本邊界框
            image_bbox: 圖片邊界框
            
        Returns:
            CaptionPosition: Caption位置
        """
        # 計算相對位置
        text_center_x = text_bbox.center_x
        text_center_y = text_bbox.center_y
        image_center_x = image_bbox.center_x
        image_center_y = image_bbox.center_y
        
        # 計算距離
        dx = text_center_x - image_center_x
        dy = text_center_y - image_center_y
        distance = np.sqrt(dx * dx + dy * dy)
        
        # 判斷是否在圖片內部
        if (text_bbox.left >= image_bbox.left and text_bbox.right <= image_bbox.right and
            text_bbox.top >= image_bbox.top and text_bbox.bottom <= image_bbox.bottom):
            return CaptionPosition.INSIDE
        
        # 判斷距離
        if distance > self.position_thresholds["far_distance"]:
            return CaptionPosition.DISTANT
        
        # 判斷主要方向
        if abs(dy) > abs(dx):
            # 垂直方向佔主導
            if dy < 0:
                return CaptionPosition.ABOVE
            else:
                return CaptionPosition.BELOW
        else:
            # 水平方向佔主導
            if dx < 0:
                return CaptionPosition.LEFT
            else:
                return CaptionPosition.RIGHT
    
    def _calculate_caption_confidence(self, pattern: CaptionPattern, 
                                    position: CaptionPosition,
                                    text: str, text_bbox: BoundingBox, 
                                    image_bbox: BoundingBox) -> float:
        """
        計算Caption的置信度
        
        Args:
            pattern: 匹配的模式
            position: Caption位置
            text: 文本內容
            text_bbox: 文本邊界框
            image_bbox: 圖片邊界框
            
        Returns:
            float: 置信度 (0-1)
        """
        # 基礎置信度
        base_confidence = pattern.confidence_base
        
        # 位置調整因子
        position_multipliers = {
            CaptionPosition.ABOVE: 1.1,      # 圖片上方通常是標題
            CaptionPosition.BELOW: 1.2,      # 圖片下方最常見
            CaptionPosition.LEFT: 0.9,       # 左側較少見
            CaptionPosition.RIGHT: 0.9,      # 右側較少見
            CaptionPosition.INSIDE: 0.8,     # 內部通常不是Caption
            CaptionPosition.DISTANT: 0.6,    # 太遠的文本不太可能是Caption
            CaptionPosition.UNKNOWN: 0.8     # 未知位置
        }
        
        position_factor = position_multipliers.get(position, 0.8)
        
        # 距離調整因子
        distance = np.sqrt(
            (text_bbox.center_x - image_bbox.center_x) ** 2 + 
            (text_bbox.center_y - image_bbox.center_y) ** 2
        )
        
        avg_dimension = (image_bbox.width + image_bbox.height) / 2
        normalized_distance = distance / max(avg_dimension, 1)
        
        distance_factor = 1.0
        if normalized_distance > 2:
            distance_factor = max(0.5, 1.0 - (normalized_distance - 2) * 0.1)
        
        # 文本長度調整因子
        text_length = len(text.strip())
        length_factor = 1.0
        
        if pattern.caption_type == CaptionType.TITLE:
            # 標題應該適中長度
            if 10 <= text_length <= 100:
                length_factor = 1.1
            elif text_length < 5 or text_length > 200:
                length_factor = 0.7
        elif pattern.caption_type in [CaptionType.FIGURE_NUMBER, CaptionType.TABLE_NUMBER]:
            # 編號應該較短
            if text_length <= 50:
                length_factor = 1.1
            else:
                length_factor = 0.8
        
        # 計算最終置信度
        final_confidence = base_confidence * position_factor * distance_factor * length_factor
        
        return min(1.0, max(0.1, final_confidence))

def detect_image_captions(text_blocks: List[Tuple[str, BoundingBox]], 
                         image_boxes: List[BoundingBox],
                         detector: Optional[CaptionDetector] = None) -> List[List[List[CaptionMatch]]]:
    """
    批量檢測圖片的Caption
    
    Args:
        text_blocks: 文本塊列表 [(text, bbox), ...]
        image_boxes: 圖片邊界框列表
        detector: Caption檢測器實例
        
    Returns:
        List[List[List[CaptionMatch]]]: 三維匹配結果 [text_idx][image_idx][match_idx]
    """
    if detector is None:
        detector = CaptionDetector()
    
    results = []
    
    for i, (text, text_bbox) in enumerate(text_blocks):
        text_results = []
        for j, image_bbox in enumerate(image_boxes):
            matches = detector.detect_captions(text, text_bbox, image_bbox)
            text_results.append(matches)
        results.append(text_results)
    
    logger.info(f"批量Caption檢測完成: {len(text_blocks)}個文本塊 x {len(image_boxes)}個圖片")
    return results

def extract_caption_references(text: str) -> List[Tuple[str, int, int]]:
    """
    提取文本中的圖片引用
    
    Args:
        text: 文本內容
        
    Returns:
        List[Tuple[str, int, int]]: (引用文本, 開始位置, 結束位置)
    """
    detector = CaptionDetector()
    references = []
    
    for compiled_re, pattern_obj in detector.compiled_patterns:
        if pattern_obj.caption_type == CaptionType.REFERENCE:
            for match in compiled_re.finditer(text):
                references.append((
                    match.group(0),
                    match.start(),
                    match.end()
                ))
    
    return references

def validate_caption_patterns(patterns: List[CaptionPattern]) -> List[str]:
    """
    驗證Caption模式的有效性
    
    Args:
        patterns: Caption模式列表
        
    Returns:
        List[str]: 錯誤信息列表
    """
    errors = []
    
    for i, pattern in enumerate(patterns):
        try:
            re.compile(pattern.pattern)
        except re.error as e:
            errors.append(f"模式 {i} 正則表達式錯誤: {e}")
        
        if not (0 <= pattern.confidence_base <= 1):
            errors.append(f"模式 {i} 置信度範圍錯誤: {pattern.confidence_base}")
    
    return errors

def calculate_caption_score(matches: List[CaptionMatch], weight_caption: float = 0.4) -> float:
    """
    計算Caption的最終評分（用於關聯度計算）
    
    Args:
        matches: Caption匹配結果列表
        weight_caption: Caption權重（項目規則規定為0.4）
        
    Returns:
        float: Caption評分
    """
    if not matches:
        return 0.0
    
    # 使用最高置信度的匹配
    best_match = max(matches, key=lambda x: x.confidence)
    
    # 根據Caption類型調整分數
    type_multipliers = {
        CaptionType.FIGURE_NUMBER: 1.0,    # 圖片編號最重要
        CaptionType.TABLE_NUMBER: 1.0,     # 表格編號同等重要
        CaptionType.REFERENCE: 0.9,        # 引用略低
        CaptionType.CHART_DIAGRAM: 0.95,   # 圖表類型較重要
        CaptionType.DESCRIPTION: 0.8,      # 描述性文字
        CaptionType.TITLE: 0.85,          # 標題
        CaptionType.UNKNOWN: 0.7          # 未知類型
    }
    
    type_factor = type_multipliers.get(best_match.caption_type, 0.7)
    base_score = best_match.confidence * type_factor
    
    return base_score * weight_caption

# 導出便捷函數
def quick_caption_detection(text: str, text_bbox: BoundingBox, image_bbox: BoundingBox) -> List[CaptionMatch]:
    """快速Caption檢測"""
    detector = CaptionDetector()
    return detector.detect_captions(text, text_bbox, image_bbox)
