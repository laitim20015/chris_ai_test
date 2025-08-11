# 智能文件轉換與RAG系統 - 完整運行流程圖表

## 📊 系統架構總覽

```mermaid
graph TB
    A[用戶] --> B[API入口/CLI入口]
    B --> C[DocumentProcessor 核心引擎]
    
    C --> D[1. 文件解析階段]
    C --> E[2. 圖文關聯分析階段] 
    C --> F[3. Markdown生成階段]
    C --> G[4. 結果保存階段]
    
    D --> D1[ParserFactory]
    D1 --> D2[PDF/Word/PPT解析器]
    D2 --> D3[ParsedContent結構]
    
    E --> E1[Caption檢測]
    E --> E2[空間關係分析]
    E --> E3[語義相似度分析]
    E --> E4[關聯評分]
    E --> E5[關聯優化]
    
    F --> F1[MarkdownGenerator]
    F1 --> F2[Jinja2模板渲染]
    F2 --> F3[Markdown文件]
    
    G --> G1[文件系統存儲]
    G --> G2[統計信息收集]
```

## 🔄 詳細處理流程

### **階段一：系統初始化**

```mermaid
graph LR
    A[DocumentProcessor初始化] --> A1[載入系統設置]
    A1 --> A2[初始化ParserFactory]
    A2 --> A3[初始化MarkdownGenerator]
    A3 --> A4[初始化關聯分析組件]
    
    A4 --> A4a[AllenLogicAnalyzer<br/>空間邏輯分析]
    A4 --> A4b[CaptionDetector<br/>標題檢測器]
    A4 --> A4c[SpatialAnalyzer<br/>空間關係分析器]
    A4 --> A4d[SemanticAnalyzer<br/>語義分析器]
    A4 --> A4e[AssociationScorer<br/>關聯評分器]
    A4 --> A4f[AssociationOptimizer<br/>關聯優化器]
```

**核心組件說明:**
- **settings**: 系統配置管理 (Pydantic)
- **parser_factory**: 文件解析器工廠 (支援PDF/Word/PPT)
- **markdown_generator**: Markdown輸出生成器 (Jinja2模板)
- **allen_analyzer**: Allen時間邏輯分析器 (13種空間關係)
- **caption_detector**: Caption檢測器 (40%權重，正則匹配)
- **spatial_analyzer**: 空間關係分析器 (30%權重，增強算法)
- **semantic_analyzer**: 語義分析器 (15%權重，sentence-transformers)
- **association_scorer**: 關聯評分器 (加權融合計算)
- **association_optimizer**: 關聯優化器 (去重、過濾、質量提升)

### **階段二：文件解析**

```mermaid
graph TD
    B1[文件驗證] --> B2[確定文件類型]
    B2 --> B3[ParserFactory選擇解析器]
    
    B3 --> B3a[PDF文件] 
    B3 --> B3b[Word文件]
    B3 --> B3c[PowerPoint文件]
    
    B3a --> B4a[PyMuPDF解析<br/>備用pymupdf4llm<br/>最後unstructured]
    B3b --> B4b[python-docx解析]
    B3c --> B4c[python-pptx解析]
    
    B4a --> B5[提取文本塊]
    B4b --> B5
    B4c --> B5
    
    B5 --> B6[提取圖片]
    B6 --> B7[提取表格]
    B7 --> B8[生成ParsedContent結構]
    
    B8 --> B8a[TextBlock列表]
    B8 --> B8b[ImageContent列表]
    B8 --> B8c[TableContent列表]
    B8 --> B8d[DocumentMetadata]
```

**解析策略:**
- **PDF解析**: 優先使用PyMuPDF → pymupdf4llm → unstructured (多層備用機制)
- **Word解析**: python-docx (直接解析)
- **PPT解析**: python-pptx (幻燈片解析)
- **輸出結構**: ParsedContent包含所有提取的文本塊、圖片、表格和元數據

### **階段三：圖文關聯分析（核心）**

```mermaid
graph TD
    C1[圖文關聯分析開始] --> C2[逐一配對：文本塊 × 圖片]
    
    C2 --> C3[單個關聯分析]
    
    C3 --> C3a[1. Caption檢測<br/>權重40%]
    C3 --> C3b[2. 空間關係分析<br/>權重30%]  
    C3 --> C3c[3. 語義相似度分析<br/>權重15%]
    C3 --> C3d[4. 佈局分析<br/>權重10%]
    C3 --> C3e[5. 距離分析<br/>權重5%]
    
    C3a --> C4a[正則表達式匹配<br/>圖/Figure/Table等]
    C3b --> C4b[Allen時間邏輯<br/>垂直/水平關係]
    C3c --> C4c[sentence-transformers<br/>語義向量相似度]
    C3d --> C4d[對齊度/同行列]
    C3e --> C4e[中心距離/最小距離]
    
    C4a --> C5[AssociationScorer<br/>加權融合計算]
    C4b --> C5
    C4c --> C5
    C4d --> C5
    C4e --> C5
    
    C5 --> C6[閾值過濾]
    C6 --> C7[關聯優化器處理]
    
    C7 --> C7a[Caption加成]
    C7 --> C7b[去重處理]
    C7 --> C7c[質量分級]
    C7 --> C7d[數量限制]
    
    C7d --> C8[最終關聯列表]
```

**權重分配 (嚴格按照項目規則):**
- Caption檢測: **40%** (最高優先級)
- 空間關係: **30%** (次高優先級)
- 語義相似度: **15%**
- 佈局模式: **10%**
- 距離計算: **5%**

**關聯分析詳細步驟:**
1. **Caption檢測**: 使用正則表達式匹配「圖1」、「Figure 1」、「如圖所示」等模式
2. **空間關係**: 基於Allen邏輯的13種空間關係，包含垂直優先算法
3. **語義分析**: sentence-transformers計算文本與圖片描述的向量相似度
4. **評分融合**: AssociationScorer按權重進行加權平均
5. **關聯優化**: Caption加成、去重、質量分級、數量限制

### **階段四：Markdown生成**

```mermaid
graph TD
    D1[Markdown生成開始] --> D2[準備模板數據]
    
    D2 --> D2a[處理關聯信息]
    D2 --> D2b[組織文本塊與圖片]
    D2 --> D2c[準備表格數據]
    
    D2a --> D3[創建元數據]
    D2b --> D3
    D2c --> D3
    
    D3 --> D4[選擇Jinja2模板]
    D4 --> D4a[basic.md.j2<br/>基礎模板]
    D4 --> D4b[enhanced.md.j2<br/>增強模板]
    
    D4b --> D5[模板渲染]
    
    D5 --> D5a[YAML前言元數據]
    D5 --> D5b[文檔概覽表格]
    D5 --> D5c[段落內容循環]
    D5 --> D5d[圖片關聯信息]
    D5 --> D5e[關聯分析表格]
    
    D5e --> D6[內容驗證]
    D6 --> D7[保存到文件]
    D7 --> D8[最終Markdown文件]
```

**模板結構:**
- **YAML前言**: 文檔元數據 (document_id, 處理時間, 統計信息)
- **文檔概覽**: 基本信息表格
- **段落內容**: 循環渲染每個文本塊
- **圖片關聯**: 在相關段落下方顯示關聯的圖片
- **關聯分析**: 底部顯示完整的關聯分析表格

## 📱 API接口流程（可選）

```mermaid
sequenceDiagram
    participant Client as 客戶端
    participant API as FastAPI服務
    participant DS as DocumentService
    participant DP as DocumentProcessor
    
    Client->>API: POST /upload (上傳文件)
    API->>DS: 保存文件到臨時目錄
    DS-->>API: 返回document_id
    API-->>Client: 返回上傳成功響應
    
    Client->>API: POST /process (處理請求)
    API->>DS: 創建處理任務
    DS->>DP: 異步調用process_document
    DS-->>API: 返回task_id
    API-->>Client: 返回任務創建響應
    
    loop 處理進度查詢
        Client->>API: GET /process/status/{task_id}
        API->>DS: 查詢任務狀態
        DS-->>API: 返回進度信息
        API-->>Client: 返回當前進度
    end
    
    DP->>DP: 執行完整處理流程
    DP-->>DS: 處理完成，返回結果
    
    Client->>API: GET /process/result/{task_id}
    API->>DS: 獲取處理結果
    DS-->>API: 返回Markdown等文件
    API-->>Client: 返回最終結果
```

## 📋 完整流程總結

### **入口點選擇**
- **CLI模式**: `python -m src.main input.pdf -o output/`
- **API模式**: FastAPI服務 + 異步處理

### **核心處理階段**
1. **初始化** (DocumentProcessor.__init__)
2. **文件解析** (ParserFactory + 具體Parser)
3. **關聯分析** (5種分析器 + 評分融合 + 優化)
4. **生成輸出** (MarkdownGenerator + Jinja2模板)
5. **結果保存** (文件系統存儲)

### **關鍵組件調用鏈**
```
DocumentProcessor → ParserFactory → [PDF/Word/PPT]Parser → 
ParsedContent → AssociationAnalysis → [Caption/Spatial/Semantic/Layout/Proximity]Analyzers → 
AssociationScorer → AssociationOptimizer → MarkdownGenerator → 
Jinja2Templates → FinalOutput
```

### **核心文件結構**
```
src/
├── main.py                    # 主入口點，DocumentProcessor
├── parsers/                   # 文件解析器
│   ├── parser_factory.py     # 解析器工廠
│   ├── pdf_parser.py         # PDF解析 (PyMuPDF)
│   ├── word_parser.py        # Word解析 (python-docx)
│   └── ppt_parser.py         # PPT解析 (python-pptx)
├── association/               # 圖文關聯分析
│   ├── caption_detector.py   # Caption檢測 (40%權重)
│   ├── spatial_analyzer.py   # 空間關係分析 (30%權重)
│   ├── semantic_analyzer.py  # 語義分析 (15%權重)
│   ├── association_scorer.py # 評分融合計算
│   ├── association_optimizer.py # 關聯優化
│   ├── candidate_ranker.py   # 候選排序器
│   └── allen_logic.py        # Allen邏輯分析
├── markdown/                  # Markdown生成
│   ├── generator.py          # 主生成器
│   ├── formatter.py          # 格式化工具
│   └── templates/            # Jinja2模板
└── api/                      # FastAPI接口
    ├── app.py               # 應用入口
    └── routes/              # 路由定義
```

## 🚨 當前發現的問題點

基於對workflows_sample_complete.md的分析，發現以下關鍵問題：

### **1. 佈局檢測被禁用**
**位置**: `src/main.py:221`
```python
'layout_type': 'single_column',  # 硬編碼禁用動態檢測
```
**影響**: 無法正確識別多欄佈局，空間距離歸一化失效

### **2. 關聯策略原始**  
**位置**: `src/main.py:162-163`
```python
for text_block in parsed_content.text_blocks:
    for image in parsed_content.images:  # 簡單逐一配對
```
**影響**: 未使用CandidateRanker的最近上方優先策略

### **3. 類型判定過早**
**位置**: `src/main.py:281`
```python
"association_type": "caption" if caption_score > 0.5 else "spatial",
```
**影響**: 在優化前決定類型，導致Caption檢測✅但類型顯示spatial的不一致

### **4. 段落102問題根源**
**現象**: "下列圖表描述了工作對商務名片進行拼版的方式" 未被優先關聯到其下方圖片
**根因**: 
- 缺乏最近上方優先規則
- 空間距離計算被固定佈局設置削弱
- Caption指示詞檢測到但權重計算後仍被空間近距離候選超越

## 🔧 修正建議

1. **啟用動態佈局檢測**: 移除硬編碼的single_column設置
2. **整合CandidateRanker**: 使用智能候選排序替代簡單逐一配對
3. **同步關聯類型更新**: 在優化階段同步更新association_type
4. **實施最近上方優先**: 對於Caption指示詞明確的文本，給予位置加權

---

*文檔生成時間: 2025年1月11日*  
*系統版本: 智能文件轉換與RAG知識庫系統 v1.0*
