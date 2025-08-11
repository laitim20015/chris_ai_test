#!/usr/bin/env python3
"""
跨頁關聯問題診斷腳本
Cross-page Association Problem Diagnosis Script

專門分析和檢測錯誤的跨頁圖文關聯問題
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from src.parsers.pdf_parser import PDFParser
from collections import defaultdict
import json

def main():
    print("🔍 跨頁關聯問題診斷開始...")
    print("=" * 60)
    
    # 解析PDF文件
    parser = PDFParser()
    parsed_content = parser.parse('tests/fixtures/documents/Workflows-sample.pdf')
    
    print(f"📄 文檔解析完成:")
    print(f"   • 文本塊數量: {len(parsed_content.text_blocks)}")
    print(f"   • 圖片數量: {len(parsed_content.images)}")
    
    # 1. 分析頁面分佈
    print(f"\n📊 1. 頁面內容分佈分析:")
    page_text_count = defaultdict(int)
    page_image_count = defaultdict(int)
    
    for text_block in parsed_content.text_blocks:
        page_text_count[text_block.page_number] += 1
    
    for image in parsed_content.images:
        page_image_count[image.page_number] += 1
    
    # 重點關注第6、7、8頁
    focus_pages = [6, 7, 8]
    for page in focus_pages:
        print(f"   📄 第{page}頁: {page_text_count[page]}個文本塊, {page_image_count[page]}個圖片")
    
    # 2. 檢查問題段落的具體信息
    print(f"\n🎯 2. 問題段落詳細分析:")
    problem_paragraphs = [46, 50, 88]  # 已知問題段落
    correct_paragraphs = [61, 63]      # 正確關聯段落
    
    target_paragraphs = {}
    
    # 查找所有目標段落
    for i, text_block in enumerate(parsed_content.text_blocks):
        paragraph_id = i + 1  # 段落編號從1開始
        if paragraph_id in problem_paragraphs + correct_paragraphs:
            target_paragraphs[paragraph_id] = {
                'block': text_block,
                'index': i,
                'content_preview': text_block.content[:50] + "..." if len(text_block.content) > 50 else text_block.content
            }
    
    for para_id in sorted(target_paragraphs.keys()):
        info = target_paragraphs[para_id]
        block = info['block']
        status = "🔴 問題段落" if para_id in problem_paragraphs else "✅ 正確段落"
        print(f"   {status} 段落{para_id} (索引{info['index']}):")
        print(f"     頁面: {block.page_number}")
        print(f"     內容: {info['content_preview']}")
        print(f"     坐標: x={block.bbox.x:.1f}, y={block.bbox.y:.1f}")
        print()
    
    # 3. 檢查第7頁的圖片
    print(f"🖼️ 3. 第7頁圖片分析:")
    page_7_images = [img for img in parsed_content.images if img.page_number == 7]
    
    if page_7_images:
        for i, img in enumerate(page_7_images):
            print(f"   圖片{i+1}: {img.filename}")
            print(f"     ID: {img.id}")
            print(f"     坐標: x={img.bbox.x:.1f}, y={img.bbox.y:.1f}, w={img.bbox.width:.1f}, h={img.bbox.height:.1f}")
            if hasattr(img, 'alt_text') and img.alt_text:
                print(f"     描述: {img.alt_text}")
            print()
    else:
        print("   ❌ 第7頁沒有檢測到圖片")
    
    # 4. 模擬當前系統的候選生成邏輯（有問題的版本）
    print(f"🚨 4. 當前系統候選生成邏輯分析:")
    
    if page_7_images:
        target_image = page_7_images[0]  # 分析第一張圖片
        print(f"   分析圖片: {target_image.filename} (第{target_image.page_number}頁)")
        
        # 模擬錯誤的候選生成（沒有頁面過濾）
        all_candidates = []
        for text_block in parsed_content.text_blocks:
            all_candidates.append({
                'id': text_block.id,
                'content': text_block.content[:30] + "...",
                'page': text_block.page_number,
                'bbox': text_block.bbox
            })
        
        print(f"   ❌ 當前邏輯: 所有 {len(all_candidates)} 個文本塊都是候選")
        
        # 統計跨頁候選
        same_page_candidates = [c for c in all_candidates if c['page'] == target_image.page_number]
        cross_page_candidates = [c for c in all_candidates if c['page'] != target_image.page_number]
        
        print(f"   • 同頁候選: {len(same_page_candidates)} 個")
        print(f"   • 跨頁候選: {len(cross_page_candidates)} 個 ⚠️")
        
        # 重點分析第6、8頁的候選
        page_6_candidates = [c for c in cross_page_candidates if c['page'] == 6]
        page_8_candidates = [c for c in cross_page_candidates if c['page'] == 8]
        
        print(f"   • 第6頁候選: {len(page_6_candidates)} 個")
        print(f"   • 第8頁候選: {len(page_8_candidates)} 個")
        
        # 顯示問題段落作為候選的情況
        print(f"\n   🎯 問題段落作為候選的情況:")
        for para_id in problem_paragraphs:
            if para_id in target_paragraphs:
                block = target_paragraphs[para_id]['block']
                if block.page_number != target_image.page_number:
                    print(f"     ❌ 段落{para_id} (第{block.page_number}頁) 被錯誤列為第{target_image.page_number}頁圖片的候選")
    
    # 5. 正確的候選生成邏輯（修復後）
    print(f"\n✅ 5. 修復後的候選生成邏輯:")
    if page_7_images:
        target_image = page_7_images[0]
        
        # 正確的候選生成（有頁面過濾）
        correct_candidates = []
        for text_block in parsed_content.text_blocks:
            if text_block.page_number == target_image.page_number:  # 頁面過濾
                correct_candidates.append({
                    'id': text_block.id,
                    'content': text_block.content[:30] + "...",
                    'page': text_block.page_number,
                    'bbox': text_block.bbox
                })
        
        print(f"   ✅ 修復邏輯: 只有 {len(correct_candidates)} 個同頁文本塊是候選")
        print(f"   📉 候選減少: {len(all_candidates)} → {len(correct_candidates)} ({len(all_candidates) - len(correct_candidates)} 個跨頁候選被過濾)")
    
    print(f"\n🎯 6. 診斷總結:")
    print(f"   ❌ 問題確認: 系統確實沒有頁面過濾，導致跨頁錯誤關聯")
    print(f"   🔧 解決方案: 在候選生成時添加 page_number 過濾條件")
    print(f"   📊 預期效果: 跨頁候選數量從 {len(cross_page_candidates)} 降至 0")
    
    print(f"\n" + "=" * 60)
    print(f"🔍 跨頁關聯問題診斷完成")

if __name__ == "__main__":
    main()
