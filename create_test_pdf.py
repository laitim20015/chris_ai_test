"""
創建測試PDF文件

由於還沒有Workflows-sample.pdf，我們創建一個包含文字和圖像的簡單測試PDF。
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib import colors
import io

def create_test_pdf(filename: str = "test-document.pdf"):
    """創建測試PDF文件"""
    
    # 創建PDF文檔
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    
    # 樣式
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading1']
    normal_style = styles['Normal']
    
    # 標題
    title = Paragraph("測試文檔：工作流程分析報告", title_style)
    story.append(title)
    story.append(Spacer(1, 12))
    
    # 章節1
    heading1 = Paragraph("1. 項目概述", heading_style)
    story.append(heading1)
    story.append(Spacer(1, 12))
    
    para1 = Paragraph("""
    本文檔是一個測試文檔，用於驗證智能文件轉換與RAG知識庫系統的功能。
    該系統能夠自動識別文檔中的文本內容，提取圖片，並建立文本與圖片之間的關聯關係。
    """, normal_style)
    story.append(para1)
    story.append(Spacer(1, 12))
    
    # 參考圖片的文本
    para2 = Paragraph("""
    圖1顯示了系統的整體架構。如圖所示，整個流程包括文件解析、內容提取、
    關聯分析和Markdown生成等步驟。
    """, normal_style)
    story.append(para2)
    story.append(Spacer(1, 12))
    
    # 章節2
    heading2 = Paragraph("2. 技術實現", heading_style)
    story.append(heading2)
    story.append(Spacer(1, 12))
    
    para3 = Paragraph("""
    系統採用PyMuPDF作為主要的PDF解析器，具有高效的性能表現。
    Caption檢測算法能夠識別「圖1」、「Figure 1」等圖片引用模式。
    """, normal_style)
    story.append(para3)
    story.append(Spacer(1, 12))
    
    para4 = Paragraph("""
    下圖展示了關聯度評分模型的權重分配：Caption檢測40%，空間關係30%，
    語義相似度15%，佈局模式10%，距離權重5%。
    """, normal_style)
    story.append(para4)
    story.append(Spacer(1, 12))
    
    # 章節3
    heading3 = Paragraph("3. 測試結果", heading_style)
    story.append(heading3)
    story.append(Spacer(1, 12))
    
    para5 = Paragraph("""
    表1總結了不同文件格式的解析性能。PDF格式的解析速度最快，
    Word文檔的圖片提取準確率最高。
    """, normal_style)
    story.append(para5)
    story.append(Spacer(1, 12))
    
    # 構建PDF
    doc.build(story)
    print(f"✅ 測試PDF已創建: {filename}")

if __name__ == "__main__":
    try:
        create_test_pdf("test-document.pdf")
    except ImportError:
        print("⚠️ reportlab未安裝，使用簡單方式創建測試PDF")
        
        # 使用更簡單的方式創建PDF
        from reportlab.pdfgen import canvas
        
        filename = "test-document.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        
        # 添加標題
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "測試文檔：工作流程分析報告")
        
        # 添加內容
        c.setFont("Helvetica", 12)
        y = 700
        
        lines = [
            "1. 項目概述",
            "",
            "本文檔是一個測試文檔，用於驗證智能文件轉換與RAG知識庫系統的功能。",
            "該系統能夠自動識別文檔中的文本內容，提取圖片，並建立關聯關係。",
            "",
            "圖1顯示了系統的整體架構。如圖所示，整個流程包括文件解析、",
            "內容提取、關聯分析和Markdown生成等步驟。",
            "",
            "2. 技術實現", 
            "",
            "系統採用PyMuPDF作為主要的PDF解析器，具有高效的性能表現。",
            "Caption檢測算法能夠識別「圖1」、「Figure 1」等圖片引用模式。",
            "",
            "下圖展示了關聯度評分模型的權重分配：Caption檢測40%，",
            "空間關係30%，語義相似度15%，佈局模式10%，距離權重5%。",
            "",
            "3. 測試結果",
            "",
            "表1總結了不同文件格式的解析性能。PDF格式的解析速度最快，",
            "Word文檔的圖片提取準確率最高。",
        ]
        
        for line in lines:
            if line.startswith(("1.", "2.", "3.")):
                c.setFont("Helvetica-Bold", 14)
            else:
                c.setFont("Helvetica", 12)
            
            c.drawString(100, y, line)
            y -= 20
            
            if y < 100:
                c.showPage()
                y = 750
        
        c.save()
        print(f"✅ 簡單測試PDF已創建: {filename}")
