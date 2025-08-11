#!/usr/bin/env python3
"""
增強PDF解析器 - 支持向量圖形檢測
Enhanced PDF Parser - Vector Graphics Detection Support

專門處理由繪圖對象組成的圖表，解決段落102類似問題
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple
import math
from collections import defaultdict

from src.parsers.base import ImageContent, ImageFormat
from src.association.allen_logic import BoundingBox

class VectorGraphicsDetector:
    """向量圖形檢測器"""
    
    def __init__(self, min_drawing_density: int = 10, min_area: float = 10000):
        """
        初始化向量圖形檢測器
        
        Args:
            min_drawing_density: 最小繪圖對象密度（每單位面積）
            min_area: 最小圖表面積（像素²）
        """
        self.min_drawing_density = min_drawing_density
        self.min_area = min_area
    
    def detect_vector_graphics(self, page) -> List[Dict]:
        """
        檢測頁面中的向量圖形區域
        
        Args:
            page: PyMuPDF頁面對象
            
        Returns:
            List[Dict]: 檢測到的圖形區域列表
        """
        # 獲取所有繪圖對象
        drawings = page.get_drawings()
        
        if not drawings:
            return []
        
        print(f"   檢測到 {len(drawings)} 個繪圖對象")
        
        # 分析繪圖對象的空間分佈
        drawing_groups = self._group_drawings_by_proximity(drawings)
        
        # 識別圖表區域
        vector_graphics = []
        for group_id, group_drawings in drawing_groups.items():
            if len(group_drawings) >= self.min_drawing_density:
                bbox = self._calculate_group_bbox(group_drawings)
                area = bbox.width * bbox.height
                
                if area >= self.min_area:
                    vector_graphics.append({
                        'bbox': bbox,
                        'drawing_count': len(group_drawings),
                        'area': area,
                        'density': len(group_drawings) / area * 10000,  # 每10k像素的繪圖對象數
                        'drawings': group_drawings
                    })
                    print(f"   識別圖表區域: {len(group_drawings)}個對象, 面積{area:.0f}, 密度{len(group_drawings) / area * 10000:.2f}")
        
        return vector_graphics
    
    def _group_drawings_by_proximity(self, drawings: List, proximity_threshold: float = 100) -> Dict[int, List]:
        """
        按空間接近度分組繪圖對象
        
        Args:
            drawings: 繪圖對象列表
            proximity_threshold: 接近度閾值（像素）
            
        Returns:
            Dict[int, List]: 分組後的繪圖對象
        """
        if not drawings:
            return {}
        
        # 為每個繪圖對象計算中心點
        drawing_centers = []
        for drawing in drawings:
            rect = drawing.get('rect')
            if rect:
                center_x = rect.x0 + (rect.x1 - rect.x0) / 2
                center_y = rect.y0 + (rect.y1 - rect.y0) / 2
                drawing_centers.append((center_x, center_y, drawing))
        
        # 使用簡單的連通分量算法分組
        groups = defaultdict(list)
        visited = set()
        group_id = 0
        
        for i, (x1, y1, drawing1) in enumerate(drawing_centers):
            if i in visited:
                continue
                
            # 開始新組
            current_group = [drawing1]
            visited.add(i)
            stack = [(x1, y1, i)]
            
            while stack:
                cx, cy, idx = stack.pop()
                
                # 查找附近的未訪問對象
                for j, (x2, y2, drawing2) in enumerate(drawing_centers):
                    if j in visited:
                        continue
                    
                    distance = math.sqrt((x2 - cx) ** 2 + (y2 - cy) ** 2)
                    if distance <= proximity_threshold:
                        current_group.append(drawing2)
                        visited.add(j)
                        stack.append((x2, y2, j))
            
            if len(current_group) > 1:  # 只保留多對象組
                groups[group_id] = current_group
                group_id += 1
        
        return groups
    
    def _calculate_group_bbox(self, drawings: List) -> BoundingBox:
        """計算繪圖組的邊界框"""
        if not drawings:
            return BoundingBox(0, 0, 0, 0)
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for drawing in drawings:
            rect = drawing.get('rect')
            if rect:
                min_x = min(min_x, rect.x0)
                min_y = min(min_y, rect.y0)
                max_x = max(max_x, rect.x1)
                max_y = max(max_y, rect.y1)
        
        return BoundingBox(
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y
        )

def create_vector_image_content(vector_graphic: Dict, page_num: int, index: int) -> ImageContent:
    """
    從向量圖形創建ImageContent對象
    
    Args:
        vector_graphic: 向量圖形信息
        page_num: 頁面號
        index: 圖片索引
        
    Returns:
        ImageContent: 圖片內容對象
    """
    bbox = vector_graphic['bbox']
    
    # 生成檔案名
    filename = f"page_{page_num:03d}_vector_{index:03d}.svg"
    
    # 創建ImageContent（使用虛擬數據，實際實現中可以生成SVG）
    return ImageContent(
        id=f"vector_{page_num}_{index}",
        filename=filename,
        format=ImageFormat.PNG,  # 使用PNG格式（向量圖形轉換後）
        data=b"<svg><!-- Vector graphics placeholder --></svg>",  # 占位數據
        page_number=page_num,
        bbox=bbox,
        alt_text=f"向量圖表 ({vector_graphic['drawing_count']}個繪圖對象)"
    )

def test_enhanced_pdf_parsing():
    """測試增強PDF解析"""
    print("=== 增強PDF解析測試 ===")
    
    # 打開PDF
    pdf_path = "tests/fixtures/documents/Workflows-sample.pdf"
    doc = fitz.open(pdf_path)
    page = doc[8]  # 第9頁
    
    print(f"測試文件: {pdf_path}")
    print(f"頁面: 第9頁")
    print(f"頁面尺寸: {page.rect}")
    
    # 創建向量圖形檢測器
    detector = VectorGraphicsDetector(min_drawing_density=10, min_area=5000)
    
    # 檢測向量圖形
    vector_graphics = detector.detect_vector_graphics(page)
    
    print(f"\n檢測結果:")
    print(f"   向量圖形數量: {len(vector_graphics)}")
    
    for i, vg in enumerate(vector_graphics):
        print(f"\n   圖表{i+1}:")
        print(f"     位置: x={vg['bbox'].x:.1f}, y={vg['bbox'].y:.1f}")
        print(f"     尺寸: w={vg['bbox'].width:.1f}, h={vg['bbox'].height:.1f}")
        print(f"     繪圖對象數: {vg['drawing_count']}")
        print(f"     面積: {vg['area']:.0f} 像素²")
        print(f"     密度: {vg['density']:.2f} 對象/萬像素")
        
        # 創建ImageContent對象
        img_content = create_vector_image_content(vg, 9, i)
        print(f"     生成ImageContent: {img_content.filename}")
        print(f"     替代文本: {img_content.alt_text}")
    
    # 檢查與段落102的關係
    print(f"\n與段落102的關係分析:")
    paragraph_102_y = 350.8  # 從之前的分析得到
    
    for i, vg in enumerate(vector_graphics):
        bbox = vg['bbox']
        
        # 檢查垂直位置關係
        if bbox.y > paragraph_102_y:
            distance = bbox.y - paragraph_102_y
            print(f"   圖表{i+1}: 在段落102下方 {distance:.1f}像素 ✅")
            
            # 檢查是否在合理範圍內
            if distance < 200:  # 小於200像素認為是緊密關聯
                print(f"     → 距離合理，應該關聯 ✅")
            else:
                print(f"     → 距離較遠，可能不直接關聯")
        else:
            print(f"   圖表{i+1}: 在段落102上方，不太可能關聯")
    
    doc.close()

if __name__ == "__main__":
    test_enhanced_pdf_parsing()
