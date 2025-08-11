#!/usr/bin/env python3
"""
使用PyMuPDF直接檢查第9頁的內容
"""

import fitz  # PyMuPDF

def main():
    print("=== PyMuPDF直接檢查第9頁 ===")
    
    # 打開PDF
    doc = fitz.open('tests/fixtures/documents/Workflows-sample.pdf')
    page = doc[8]  # 第9頁 (0-based索引)
    
    print(f"頁面尺寸: {page.rect}")
    
    # 1. 檢查圖片
    print(f"\n1. 圖片檢查:")
    images = page.get_images(full=True)
    print(f"   圖片數量: {len(images)}")
    
    if images:
        for i, img in enumerate(images):
            print(f"   圖片{i+1}: xref={img[0]}, width={img[2]}, height={img[3]}")
            
            # 獲取圖片坐標
            xref = img[0]
            try:
                rects = page.get_image_rects(xref)
                if rects:
                    for rect in rects:
                        print(f"     坐標: {rect}")
                else:
                    print(f"     無法獲取坐標")
            except Exception as e:
                print(f"     獲取坐標出錯: {e}")
    else:
        print("   ❌ 第9頁沒有圖片")
    
    # 2. 檢查繪圖對象
    print(f"\n2. 繪圖對象檢查:")
    drawings = page.get_drawings()
    print(f"   繪圖對象數量: {len(drawings)}")
    
    if drawings:
        for i, drawing in enumerate(drawings):
            print(f"   繪圖{i+1}: {drawing}")
    
    # 3. 檢查文本內容
    print(f"\n3. 文本內容檢查:")
    blocks = page.get_text("dict")
    print(f"   文本塊數量: {len(blocks['blocks'])}")
    
    # 查找段落102
    target_found = False
    target_y = None
    for block in blocks['blocks']:
        if 'lines' in block:
            for line in block['lines']:
                for span in line['spans']:
                    text = span['text']
                    if '下列圖表描述了工作對商務名片進行拼版的方式' in text:
                        print(f"\n   ✅ 找到段落102:")
                        print(f"     文本: {text}")
                        print(f"     坐標: {span['bbox']}")
                        target_y = span['bbox'][1]  # Y座標
                        target_found = True
                        break
    
    if not target_found:
        print("   ❌ 未找到段落102")
        doc.close()
        return
    
    # 4. 檢查段落102下方的內容
    print(f"\n4. 檢查段落102下方的內容:")
    print(f"   段落102的Y坐標: {target_y}")
    
    # 查找下一個文本塊
    next_texts = []
    for block in blocks['blocks']:
        if 'lines' in block:
            for line in block['lines']:
                for span in line['spans']:
                    y = span['bbox'][1]
                    if y > target_y + 10:  # 在段落102下方
                        text = span['text'].strip()
                        if text:  # 非空文本
                            next_texts.append((y, text, span['bbox']))
    
    # 排序並顯示
    next_texts.sort(key=lambda x: x[0])
    print(f"   段落102下方的文本 (前10個):")
    for i, (y, text, bbox) in enumerate(next_texts[:10]):
        print(f"     {i+1}. y={y:.1f}: \"{text}\" - {bbox}")
    
    # 5. 檢查是否有表格或其他元素
    print(f"\n5. 檢查表格:")
    try:
        tables = page.find_tables()
        print(f"   表格數量: {len(tables)}")
        for i, table in enumerate(tables):
            print(f"   表格{i+1}: {table.bbox}")
    except Exception as e:
        print(f"   表格檢查出錯: {e}")
    
    # 6. 保存頁面為圖片進行視覺檢查
    print(f"\n6. 保存第9頁為圖片...")
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2倍縮放
        pix.save("debug_page_9.png")
        print(f"   ✅ 已保存為 debug_page_9.png")
    except Exception as e:
        print(f"   保存失敗: {e}")
    
    doc.close()

if __name__ == "__main__":
    main()
