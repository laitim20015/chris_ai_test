#!/usr/bin/env python3
"""
段落102診斷腳本
專門分析真實PDF解析中段落102的具體位置、關聯候選和計算過程
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from src.parsers.pdf_parser import PDFParser
from src.association.caption_detector import CaptionDetector
from src.association.spatial_analyzer import SpatialAnalyzer
from src.association.semantic_analyzer import SemanticAnalyzer
from src.association.association_scorer import AssociationScorer

def main():
    print("=== 段落102診斷開始 ===")
    
    # 1. 解析PDF
    print("1. 解析PDF文件...")
    pdf_path = "tests/fixtures/documents/Workflows-sample.pdf"
    parser = PDFParser()
    parsed_content = parser.parse(pdf_path)
    
    print(f"   總文本塊: {len(parsed_content.text_blocks)}")
    print(f"   總圖片: {len(parsed_content.images)}")
    
    # 2. 查找段落102
    print("\n2. 查找段落102...")
    target_paragraph = None
    target_index = -1
    
    for i, block in enumerate(parsed_content.text_blocks):
        if '下列圖表描述了工作對商務名片進行拼版的方式' in block.content:
            target_paragraph = block
            target_index = i
            print(f"   ✅ 找到段落102！")
            print(f"   索引: {i}")
            print(f"   ID: {block.id}")
            print(f"   內容: {block.content}")
            print(f"   頁面: {block.page_number}")
            print(f"   坐標: x={block.bbox.x}, y={block.bbox.y}, w={block.bbox.width}, h={block.bbox.height}")
            break
    
    if not target_paragraph:
        print("   ❌ 未找到段落102！")
        return
    
    # 3. 分析第9頁的詳細內容
    print(f"\n3. 分析第{target_paragraph.page_number}頁的詳細內容...")
    
    # 列出同頁所有文本塊（按Y坐標排序）
    same_page_texts = []
    for i, block in enumerate(parsed_content.text_blocks):
        if block.page_number == target_paragraph.page_number:
            same_page_texts.append((i, block))
    
    same_page_texts.sort(key=lambda x: x[1].bbox.y)  # 按Y坐標排序
    
    print(f"   同頁文本塊 (按垂直位置排序):")
    for i, block in same_page_texts:
        is_target = ">>> " if block.id == target_paragraph.id else "    "
        content_preview = block.content[:50] + "..." if len(block.content) > 50 else block.content
        print(f"{is_target}索引{i}: y={block.bbox.y:.1f} - \"{content_preview}\"")
    
    # 分析同頁圖片
    print(f"\n   同頁圖片:")
    same_page_images = []
    for i, img in enumerate(parsed_content.images):
        if img.page_number == target_paragraph.page_number:
            same_page_images.append((i, img))
            print(f"   圖片{i+1}: {img.filename}")
            print(f"     坐標: x={img.bbox.x:.1f}, y={img.bbox.y:.1f}, w={img.bbox.width:.1f}, h={img.bbox.height:.1f}")
            
            # 計算距離
            text_center_x = target_paragraph.bbox.x + target_paragraph.bbox.width / 2
            text_center_y = target_paragraph.bbox.y + target_paragraph.bbox.height / 2
            img_center_x = img.bbox.x + img.bbox.width / 2
            img_center_y = img.bbox.y + img.bbox.height / 2
            center_distance = ((text_center_x - img_center_x)**2 + (text_center_y - img_center_y)**2)**0.5
            print(f"     與段落102中心距離: {center_distance:.1f}像素")
            
            # 垂直關係
            if img.bbox.y > target_paragraph.bbox.y + target_paragraph.bbox.height:
                distance = img.bbox.y - (target_paragraph.bbox.y + target_paragraph.bbox.height)
                print(f"     位置關係: 圖片在段落102下方 (距離{distance:.1f}像素)")
            elif img.bbox.y + img.bbox.height < target_paragraph.bbox.y:
                distance = target_paragraph.bbox.y - (img.bbox.y + img.bbox.height)
                print(f"     位置關係: 圖片在段落102上方 (距離{distance:.1f}像素)")
            else:
                print(f"     位置關係: 圖片與段落102垂直重疊")
    
    # 檢查是否真的沒有圖片
    if not same_page_images:
        print(f"   ❌ 第{target_paragraph.page_number}頁確實沒有圖片！")
        
        # 檢查附近頁面
        print(f"\n   檢查附近頁面的圖片:")
        for page_offset in [-1, 1, 2]:
            check_page = target_paragraph.page_number + page_offset
            if check_page > 0:
                nearby_images = [img for img in parsed_content.images if img.page_number == check_page]
                if nearby_images:
                    print(f"     第{check_page}頁: {len(nearby_images)}張圖片")
                    for i, img in enumerate(nearby_images):
                        print(f"       - {img.filename}")
    else:
        print(f"   ✅ 第{target_paragraph.page_number}頁有 {len(same_page_images)} 張圖片")
    
    if not same_page_images:
        print("   ❌ 同頁面無圖片！")
        # 不要return，繼續分析其他信息
    
    # 4. 跳過關聯分析（因為同頁無圖片）
    if same_page_images:
        print("\n4. 進行關聯分析...")
        # 這部分在同頁無圖片時不會執行
    else:
        print("\n4. 跳過關聯分析（同頁無圖片）")
    
    # 6. 分析所有圖片分佈
    print("\n6. 分析所有圖片分佈...")
    print("=== 所有圖片分佈情況 ===")
    page_counts = {}
    
    for i, img in enumerate(parsed_content.images):
        print(f"   圖片{i+1}: {img.filename}")
        print(f"     頁面: {img.page_number}")
        print(f"     坐標: x={img.bbox.x:.1f}, y={img.bbox.y:.1f}, w={img.bbox.width:.1f}, h={img.bbox.height:.1f}")
        page_counts[img.page_number] = page_counts.get(img.page_number, 0) + 1
    
    print("\n=== 每頁圖片數量統計 ===")
    for page in sorted(page_counts.keys()):
        print(f"   第{page}頁: {page_counts[page]}張圖片")
    
    # 7. 檢查跨頁關聯
    print("\n7. 檢查跨頁關聯可能性...")
    if target_paragraph:
        nearest_images = []
        for i, img in enumerate(parsed_content.images):
            # 計算頁面距離
            page_distance = abs(img.page_number - target_paragraph.page_number)
            if page_distance <= 2:  # 只考慮前後2頁內的圖片
                nearest_images.append((i, img, page_distance))
        
        if nearest_images:
            print(f"   段落102附近頁面的圖片:")
            for i, img, page_dist in nearest_images:
                print(f"     圖片{i+1}: 頁面{img.page_number} (距離{page_dist}頁) - {img.filename}")
        else:
            print("   ❌ 附近2頁內無圖片")

    print("\n=== 段落102診斷完成 ===")

if __name__ == "__main__":
    main()
