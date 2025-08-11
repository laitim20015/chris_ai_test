# 智能文件轉換與RAG知識庫系統
## 項目規格文件 v1.2

---

## 1. 項目背景與目的

### 1.1 背景
隨著企業數字化轉型的加速，大量的非結構化文件（Word、PDF、PowerPoint）需要被有效地整合到知識管理系統中。傳統的文件檢索方式無法充分利用文件中的圖像信息，導致知識檢索的準確性和完整性不足。

### 1.2 項目目的
開發一個智能文件轉換系統，能夠：
- 將多種格式文件轉換為標準化的Markdown格式
- 建立文本段落與圖片的智能關聯關係
- 提供高效的RAG（Retrieval-Augmented Generation）知識庫索引
- 支持多平台知識庫集成（Azure AI Search、Diffy、Microsoft Copilot Studio等）
- 實現圖文並茂的精準知識檢索

### 1.3 核心價值
- **提升檢索準確性**：通過圖文關聯，提供更完整的上下文信息
- **標準化處理**：統一的Markdown格式便於多平台集成
- **智能關聯**：自動識別圖片與文本的語義關係
- **可擴展性**：支持多種文件格式和知識庫平台

---

## 2. 系統設計架構

### 2.1 整體架構
```
文件輸入 → 格式解析 → 內容提取 → 圖文關聯 → Markdown生成 → 知識庫集成
    ↓           ↓           ↓           ↓           ↓            ↓
  多格式     結構化解析   文本+圖片   智能匹配   標準化輸出   RAG索引
```

### 2.2 核心模組
1. **文件解析模組**（File Parser Module）
2. **圖片處理模組**（Image Processing Module）  
3. **關聯分析模組**（Association Analysis Module）
4. **Markdown生成模組**（Markdown Generator Module）
5. **存儲管理模組**（Storage Management Module）
6. **知識庫集成模組**（Knowledge Base Integration Module）

### 2.3 數據流設計
```
原始文件 
  ├── 文本內容提取
  ├── 圖片資源提取
  ├── 結構信息解析
  └── 元數據收集
       ↓
段落-圖片關聯分析
  ├── 位置關係分析
  ├── 語義相似度計算
  └── 關聯度評分
       ↓
Markdown文件生成
  ├── 文本結構化
  ├── 圖片URL替換
  └── 元數據嵌入
       ↓
知識庫索引建立
  ├── 分塊策略
  ├── 向量化
  └── 關聯關係存儲
```

---

## 3. 技術方案設計

### 3.1 文件解析技術棧

#### 3.1.1 Word文件處理
- **主要庫**：`python-docx`、`mammoth`
- **功能**：
  - 提取文本內容和格式信息
  - 提取嵌入圖片和圖表
  - 保留段落結構和標題層級
  - 處理表格和列表

#### 3.1.2 PDF文件處理
- **主要庫**：`PyMuPDF (fitz)`、`pymupdf4llm`、`unstructured`
- **推薦層級**：
  1. **PyMuPDF** - 最佳性能 (0.003-0.2秒)
  2. **pymupdf4llm** - 最佳Markdown輸出 (0.12秒)
  3. **unstructured** - 最佳語義分塊 (1.29秒)
- **功能**：
  - 內建OCR支持，無需額外依賴
  - 原生表格和圖片提取
  - 直接輸出結構化Markdown
  - 語義感知的內容分塊

#### 3.1.3 PowerPoint文件處理
- **主要庫**：`python-pptx`、`comtypes`
- **功能**：
  - 幻燈片內容提取
  - 圖片和圖表提取
  - 演講者備註處理
  - 動畫和過渡效果忽略

### 3.2 圖片處理與存儲

#### 3.2.1 圖片處理流程
```python
原始圖片 → 格式標準化 → 尺寸優化 → 質量壓縮 → 命名規範 → 存儲上傳
```

#### 3.2.2 命名規範
```
{文件名}_{頁碼/幻燈片號}_{圖片序號}_{時間戳}.{格式}
例：report_p003_img001_20240315143022.jpg
```

#### 3.2.3 存儲方案
- **本地存儲**：開發和測試階段
- **雲端存儲**：
  - Azure Blob Storage
  - AWS S3
  - Google Cloud Storage
- **CDN加速**：提高圖片訪問速度

### 3.3 圖文關聯算法

#### 3.3.1 多層次空間關聯分析
基於Allen時間間隔邏輯的13種空間關係：

```python
class SpatialAssociationAnalyzer:
    def __init__(self):
        self.spatial_relations = {
            "precedes": "<",     # 在...之前
            "meets": "|",        # 緊鄰
            "overlaps": "o",     # 重疊
            "during": "d",       # 在...期間
            "above": "^",        # 在...上方
            "below": "v",        # 在...下方
            "adjacent": "~",     # 鄰接
            # 加上逆關係
        }
    
    def analyze_multi_level_relations(self, text_blocks, images):
        """多層次空間關聯分析"""
        return {
            "geometric": self.geometric_analysis(text_blocks, images),
            "layout": self.layout_pattern_analysis(text_blocks, images),
            "semantic": self.semantic_proximity_analysis(text_blocks, images),
            "caption": self.caption_detection(text_blocks, images)
        }
```

#### 3.3.2 Caption檢測算法（最關鍵）
```python
def detect_caption_relationship(self, image, text_block):
    """檢測圖片標題關係 - 最重要的關聯指標"""
    caption_patterns = [
        r'^(Figure|Fig|圖|表|Table)\s*\d+',
        r'^(Chart|Diagram|Image)\s*\d+',
        r'如圖\s*\d+|見圖\s*\d+'
    ]
    
    text_content = text_block.get_text()
    
    # 檢查是否包含圖片引用
    for pattern in caption_patterns:
        if re.search(pattern, text_content, re.IGNORECASE):
            return 0.9  # 高分
    
    # 檢查位置關係 (標題通常在圖片下方或上方)
    if self.is_caption_positioned(image, text_block):
        return 0.7
        
    return 0.1
```

#### 3.3.3 增強的關聯度評分模型
```python
# 更新的權重分配（基於最新研究）
final_score = (
    w1 * caption_score +      # 0.4 - 最高權重
    w2 * spatial_score +      # 0.3 - 空間關係
    w3 * semantic_score +     # 0.15 - 語義相似度
    w4 * layout_score +       # 0.1 - 佈局模式
    w5 * proximity_score      # 0.05 - 距離權重
)
```

#### 3.3.4 空間特徵提取
```python
def enhanced_spatial_features(self, image, text_block):
    """增強的空間分析特性"""
    features = {}
    
    # 1. 距離特徵
    features['distance'] = self.calculate_minimum_distance(image.bbox, text_block.bbox)
    features['center_distance'] = self.calculate_center_distance(image, text_block)
    
    # 2. 對齊特徵
    features['horizontal_alignment'] = self.check_horizontal_alignment(image, text_block)
    features['vertical_alignment'] = self.check_vertical_alignment(image, text_block)
    
    # 3. 佈局模式
    features['column_relationship'] = self.analyze_column_layout(image, text_block)
    features['reading_order'] = self.determine_reading_order(image, text_block)
    
    return features
```

---

## 4. 項目結構設計

### 4.1 完整目錄結構

```
AP_Project_RAG/
├── 項目規格文件_文件轉換RAG系統.md      # 🎯 主要項目規格文件
├── README.md                           # 項目簡介和快速開始指南
├── requirements.txt                    # Python依賴包
├── pyproject.toml                      # 項目配置文件
├── .env.example                        # 環境變量示例
├── .gitignore                          # Git忽略文件
├── docker-compose.yml                  # Docker容器編排
├── Dockerfile                          # Docker鏡像構建
│
├── docs/                               # 📚 項目文檔目錄
│   ├── project_structure.md            # 🏗️ 項目結構詳細說明
│   ├── api/                            # API文檔
│   │   ├── openapi.yaml                # OpenAPI規範
│   │   └── api_guide.md                # API使用指南
│   ├── user_guide/                     # 👥 用戶指南
│   │   ├── installation.md             # 安裝指南
│   │   ├── quick_start.md              # 快速開始
│   │   └── advanced_usage.md           # 高級用法
│   ├── developer_guide/                # 👨‍💻 開發者指南
│   │   ├── architecture.md             # 架構說明
│   │   ├── contributing.md             # 貢獻指南
│   │   └── coding_standards.md         # 編碼規範
│   ├── technical_specs/                # 🔬 技術規格
│   │   ├── spatial_analysis.md         # 空間分析算法詳解
│   │   ├── caption_detection.md        # Caption檢測算法
│   │   └── performance_benchmarks.md   # 性能基準測試
│   └── deployment/                     # 🚀 部署文檔
│       ├── local_deployment.md         # 本地部署
│       ├── cloud_deployment.md         # 雲端部署
│       └── scaling_guide.md            # 擴展指南
│
├── src/                                # 🔧 主要源代碼目錄
│   ├── __init__.py
│   ├── main.py                         # 應用程序入口點
│   ├── config/                         # ⚙️ 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py                 # 應用配置
│   │   └── logging_config.py           # 日誌配置
│   │
│   ├── parsers/                        # 📄 文件解析模組
│   │   ├── __init__.py
│   │   ├── base.py                     # 解析器基類
│   │   ├── pdf_parser.py               # PDF解析器 (PyMuPDF + pymupdf4llm)
│   │   ├── word_parser.py              # Word解析器 (python-docx)
│   │   ├── ppt_parser.py               # PowerPoint解析器 (python-pptx)
│   │   └── parser_factory.py           # 解析器工廠模式
│   │
│   ├── image_processing/               # 🖼️ 圖片處理模組
│   │   ├── __init__.py
│   │   ├── extractor.py                # 圖片提取器
│   │   ├── optimizer.py                # 圖片優化器 (壓縮、格式轉換)
│   │   ├── storage.py                  # 圖片存儲管理 (本地/雲端)
│   │   └── metadata.py                 # 圖片元數據處理
│   │
│   ├── association/                    # 🎯 圖文關聯分析模組 (核心)
│   │   ├── __init__.py
│   │   ├── spatial_analyzer.py         # 空間關係分析器
│   │   ├── allen_logic.py              # Allen區間邏輯實現
│   │   ├── caption_detector.py         # Caption檢測器 (40%權重)
│   │   ├── semantic_analyzer.py        # 語義分析器 (sentence-transformers)
│   │   └── association_scorer.py       # 關聯度評分器
│   │
│   ├── markdown/                       # 📝 Markdown生成模組
│   │   ├── __init__.py
│   │   ├── generator.py                # Markdown生成器
│   │   ├── templates/                  # Jinja2模板文件
│   │   │   ├── basic.md.j2             # 基礎模板
│   │   │   └── enhanced.md.j2          # 增強模板 (包含關聯信息)
│   │   └── formatter.py                # 格式化工具
│   │
│   ├── knowledge_base/                 # 🧠 知識庫集成模組
│   │   ├── __init__.py
│   │   ├── base_adapter.py             # 適配器基類
│   │   ├── azure_ai_search.py          # Azure AI Search適配器
│   │   ├── diffy_adapter.py            # Diffy適配器
│   │   └── copilot_studio.py           # Microsoft Copilot Studio適配器
│   │
│   ├── utils/                          # 🔨 工具模組
│   │   ├── __init__.py
│   │   ├── file_utils.py               # 文件操作工具
│   │   ├── text_utils.py               # 文本處理工具
│   │   ├── image_utils.py              # 圖像處理工具
│   │   └── validation.py               # 數據驗證工具
│   │
│   └── api/                            # 🌐 API接口模組 (FastAPI)
│       ├── __init__.py
│       ├── routes/                     # API路由
│       │   ├── __init__.py
│       │   ├── upload.py               # 文件上傳API
│       │   ├── process.py              # 處理API
│       │   └── download.py             # 結果下載API
│       ├── models/                     # Pydantic數據模型
│       │   ├── __init__.py
│       │   ├── request_models.py       # 請求模型
│       │   └── response_models.py      # 響應模型
│       └── middleware/                 # 中間件
│           ├── __init__.py
│           ├── auth.py                 # 認證中間件
│           └── rate_limit.py           # 限流中間件
│
├── tests/                              # 🧪 測試目錄
│   ├── __init__.py
│   ├── unit/                           # 單元測試
│   │   ├── test_parsers/               # 解析器測試
│   │   │   ├── __init__.py
│   │   │   ├── test_pdf_parser.py      # PDF解析器測試
│   │   │   ├── test_word_parser.py     # Word解析器測試
│   │   │   └── test_ppt_parser.py      # PPT解析器測試
│   │   ├── test_association/           # 關聯分析測試
│   │   │   ├── __init__.py
│   │   │   ├── test_spatial_analyzer.py    # 空間分析測試
│   │   │   ├── test_caption_detector.py    # Caption檢測測試
│   │   │   └── test_association_scorer.py  # 評分器測試
│   │   └── test_utils/                 # 工具函數測試
│   │       ├── __init__.py
│   │       ├── test_file_utils.py      # 文件工具測試
│   │       └── test_validation.py      # 驗證工具測試
│   ├── integration/                    # 集成測試
│   │   ├── __init__.py
│   │   ├── test_end_to_end.py          # 端到端測試
│   │   ├── test_api.py                 # API測試
│   │   └── test_workflow.py            # 工作流測試
│   ├── performance/                    # 性能測試
│   │   ├── __init__.py
│   │   ├── test_benchmarks.py          # 基準測試
│   │   └── test_load.py                # 負載測試
│   └── fixtures/                       # 測試數據
│       ├── documents/                  # 測試文檔
│       │   ├── sample.pdf              # 測試PDF文件
│       │   ├── sample.docx             # 測試Word文件
│       │   └── sample.pptx             # 測試PPT文件
│       ├── images/                     # 測試圖片
│       │   ├── chart_sample.jpg        # 圖表樣本
│       │   └── diagram_sample.png      # 圖示樣本
│       └── expected_outputs/           # 預期輸出結果
│           ├── sample_output.md        # 預期Markdown輸出
│           └── associations.json       # 預期關聯結果
│
├── scripts/                            # 📜 腳本目錄
│   ├── setup.py                        # 環境設置腳本
│   ├── migrate.py                      # 數據遷移腳本
│   ├── benchmark.py                    # 性能基準測試腳本
│   ├── update_docs.py                  # 文檔更新腳本
│   ├── clean_temp.py                   # 清理臨時文件腳本
│   └── deploy.py                       # 部署腳本
│
├── data/                               # 💾 數據目錄
│   ├── input/                          # 輸入文件目錄
│   │   ├── documents/                  # 待處理文檔
│   │   └── batch/                      # 批量處理文件
│   ├── output/                         # 輸出文件目錄
│   │   ├── markdown/                   # 生成的Markdown文件
│   │   ├── images/                     # 處理後的圖片
│   │   └── metadata/                   # 元數據文件
│   ├── temp/                           # 臨時文件目錄
│   │   ├── processing/                 # 處理中的文件
│   │   └── cache/                      # 緩存文件
│   └── models/                         # 機器學習模型
│       ├── sentence_transformers/     # 語義模型
│       └── custom/                     # 自定義模型
│
└── deploy/                             # 🚀 部署配置
    ├── k8s/                            # Kubernetes配置
    │   ├── namespace.yaml              # 命名空間配置
    │   ├── deployment.yaml             # 部署配置
    │   ├── service.yaml                # 服務配置
    │   └── ingress.yaml                # 入口配置
    ├── terraform/                      # Terraform基礎設施
    │   ├── main.tf                     # 主要配置
    │   ├── variables.tf                # 變量定義
    │   └── outputs.tf                  # 輸出定義
    └── ansible/                        # Ansible自動化部署
        ├── playbook.yml                # 部署劇本
        ├── inventory.ini               # 主機清單
        └── roles/                      # 角色定義
            ├── app/                    # 應用角色
            └── database/               # 數據庫角色
```

### 4.2 核心模組架構設計

#### 4.2.1 解析器模組架構
基於開放封閉原則和工廠模式設計的文件解析架構，支持多種文件格式的統一處理。

#### 4.2.2 關聯分析模組架構  
基於Allen區間邏輯的空間關係分析器，實現Caption檢測(40%權重)和多層次空間特徵提取。

#### 4.2.3 配置管理設計
基於Pydantic的類型安全配置管理，支持環境變量和動態配置更新。

### 4.3 部署架構設計

#### 4.3.1 容器化部署
使用Docker和Docker Compose實現一鍵部署，支持生產環境的高可用配置。

#### 4.3.2 文檔管理策略
- **主規格文件**: 根目錄 `項目規格文件_文件轉換RAG系統.md` (本文件)
- **技術文檔**: 存放在 `docs/technical_specs/` 目錄
- **API文檔**: 自動生成OpenAPI規範
- **用戶文檔**: 安裝和使用指南

---

## 5. 詳細開發流程

### 5.1 Phase 1: 基礎架構搭建（第1-2週）

#### 5.1.1 項目初始化
- [ ] 創建項目目錄結構
- [ ] 設置虛擬環境和依賴管理
- [ ] 配置開發工具（IDE、Git、測試框架）
- [ ] 建立代碼規範和文檔標準

#### 5.1.2 核心模組框架
- [ ] 定義抽象基類和接口
- [ ] 實現配置管理系統
- [ ] 建立日誌和錯誤處理機制
- [ ] 設計模組間通信協議

### 5.2 Phase 2: 文件解析模組開發（第3-5週）

#### 5.2.1 Word文件處理器
```python
class WordParser(BaseParser):
    def extract_content(self, file_path):
        """提取Word文檔內容"""
        doc = docx.Document(file_path)
        
        content = {
            'text_blocks': self.extract_paragraphs(doc),
            'images': self.extract_images(doc),
            'tables': self.extract_tables(doc),
            'metadata': self.extract_metadata(doc)
        }
        
        return self.standardize_output(content)
```

#### 5.2.2 PDF文件處理器（更新版）
```python
class PDFParser(BaseParser):
    def __init__(self):
        self.primary_parser = "pymupdf"  # 主要解析器
        self.fallback_parsers = ["pymupdf4llm", "unstructured"]
    
    def extract_content(self, file_path):
        """多層次PDF解析策略"""
        try:
            # 主要解析器 - PyMuPDF (最快)
            return self.extract_with_pymupdf(file_path)
        except Exception:
            # 備用解析器 - pymupdf4llm (更好的結構)
            try:
                return self.extract_with_pymupdf4llm(file_path)
            except Exception:
                # 最後備用 - unstructured (語義分塊)
                return self.extract_with_unstructured(file_path)
    
    def extract_with_pymupdf(self, file_path):
        """使用PyMuPDF進行快速提取"""
        doc = fitz.open(file_path)
        content = {
            'text_blocks': [],
            'images': [],
            'tables': [],
            'metadata': doc.metadata
        }
        
        for page in doc:
            # 提取文本塊
            blocks = page.get_text("dict")
            content['text_blocks'].extend(self.process_text_blocks(blocks))
            
            # 提取圖片
            images = page.get_images()
            content['images'].extend(self.process_images(page, images))
            
            # 提取表格
            tables = page.find_tables()
            content['tables'].extend(self.process_tables(tables))
        
        return self.standardize_output(content)
```

#### 5.2.3 PowerPoint文件處理器
```python
class PPTParser(BaseParser):
    def extract_content(self, file_path):
        # 幻燈片內容提取
        # 圖片和圖表處理
        # 結構化信息提取
        pass
```

### 5.3 Phase 3: 圖片處理與存儲（第6-7週）

#### 5.3.1 圖片處理管道
- [ ] 圖片格式標準化
- [ ] 尺寸和質量優化
- [ ] 圖片命名和分類
- [ ] 元數據提取

#### 5.3.2 存儲服務整合
- [ ] 本地文件系統
- [ ] 雲端存儲服務
- [ ] URL生成和管理
- [ ] 訪問權限控制

### 5.4 Phase 4: 關聯分析引擎（第8-10週）

#### 5.4.1 空間關聯分析算法（優先級最高）
- [ ] Allen區間邏輯實現 - 13種空間關係
- [ ] Caption檢測算法 - 正則表達式模式匹配
- [ ] 位置相對關係計算 - 距離、方向、對齊
- [ ] 佈局模式識別 - 多欄位、表格、列表識別
- [ ] 閱讀順序分析 - 自然閱讀流程判斷

#### 5.4.2 語義分析系統
- [ ] 文本向量化 - 使用sentence-transformers
- [ ] 圖片描述生成 - BLIP/CLIP模型
- [ ] 語義相似度計算 - 餘弦相似度
- [ ] 多模態特徵融合 - 注意力機制
- [ ] 關聯度評分機制 - 加權融合算法

#### 5.4.3 實時關聯優化
- [ ] 動態閾值調整
- [ ] 用戶反饋學習機制
- [ ] A/B測試框架
- [ ] 性能監控和調優

### 5.5 Phase 5: Markdown生成器（第11-12週）

#### 5.5.1 結構化輸出
```python
class MarkdownGenerator:
    def generate(self, parsed_content, associations):
        # 生成標準Markdown格式
        # 嵌入圖片URL和關聯信息
        # 添加元數據標記
        pass
```

#### 5.5.2 元數據管理
```json
{
    "文檔信息": {
        "原始文件": "report.docx",
        "轉換時間": "2024-03-15T14:30:22Z",
        "版本": "1.0"
    },
    "圖文關聯": [
        {
            "段落ID": "p001",
            "相關圖片": ["img001.jpg", "img002.jpg"],
            "關聯度": [0.85, 0.72]
        }
    ]
}
```

### 5.6 Phase 6: 知識庫集成（第13-15週）

#### 5.6.1 Azure AI Search整合
- [ ] 索引schema設計
- [ ] 分塊策略實現
- [ ] 向量化處理
- [ ] 搜索API開發

#### 5.6.2 其他平台適配
- [ ] Diffy知識庫適配器
- [ ] Microsoft Copilot Studio適配器
- [ ] 通用RAG接口設計

### 5.7 Phase 7: 測試與優化（第16-18週）

#### 5.7.1 功能測試
- [ ] 單元測試
- [ ] 集成測試
- [ ] 性能測試
- [ ] 用戶接受測試

#### 5.7.2 性能優化
- [ ] 處理速度優化
- [ ] 內存使用優化
- [ ] 關聯算法調優
- [ ] 並發處理能力

---

## 6. 工作分解結構 (WBS)

### 6.1 主要里程碑
1. **M1 - 基礎架構完成**（第2週）
2. **M2 - 文件解析模組完成**（第5週）
3. **M3 - 圖片處理完成**（第7週）
4. **M4 - 關聯分析完成**（第10週）
5. **M5 - Markdown生成完成**（第12週）
6. **M6 - 知識庫集成完成**（第15週）
7. **M7 - 系統測試完成**（第18週）

### 6.2 詳細任務清單

#### 6.2.1 開發環境準備
- [ ] **Task 1.1**: 項目結構設計和創建
- [ ] **Task 1.2**: 虛擬環境配置
- [ ] **Task 1.3**: 依賴包管理（requirements.txt）
- [ ] **Task 1.4**: Git倉庫初始化
- [ ] **Task 1.5**: CI/CD流程設計

#### 6.2.2 核心框架開發
- [ ] **Task 2.1**: 抽象基類設計
- [ ] **Task 2.2**: 配置管理系統
- [ ] **Task 2.3**: 日誌系統設計
- [ ] **Task 2.4**: 錯誤處理機制
- [ ] **Task 2.5**: 模組註冊和發現機制

#### 6.2.3 文件解析器開發（優先級更新）
- [ ] **Task 3.1**: PyMuPDF主要解析器實現（優先級最高）
- [ ] **Task 3.2**: pymupdf4llm Markdown輸出器實現
- [ ] **Task 3.3**: unstructured語義分塊器整合
- [ ] **Task 3.4**: Word解析器（python-docx）實現
- [ ] **Task 3.5**: PowerPoint解析器（python-pptx）實現
- [ ] **Task 3.6**: 解析結果標準化和備用機制
- [ ] **Task 3.7**: 性能基準測試套件

#### 6.2.4 圖片處理系統
- [ ] **Task 4.1**: 圖片提取和轉換
- [ ] **Task 4.2**: 圖片優化和壓縮
- [ ] **Task 4.3**: 命名規範實現
- [ ] **Task 4.4**: 存儲服務整合
- [ ] **Task 4.5**: URL生成和管理

#### 6.2.5 關聯分析引擎（核心模組）
- [ ] **Task 5.1**: Allen區間邏輯空間關係實現（最高優先級）
- [ ] **Task 5.2**: Caption檢測正則表達式系統（關鍵功能）
- [ ] **Task 5.3**: 多層次空間特徵提取算法
- [ ] **Task 5.4**: 語義相似度計算（sentence-transformers）
- [ ] **Task 5.5**: 加權融合評分模型（Caption 40%權重）
- [ ] **Task 5.6**: 實時閾值調整機制
- [ ] **Task 5.7**: A/B測試框架建設

#### 6.2.6 Markdown生成器
- [ ] **Task 6.1**: 模板系統設計
- [ ] **Task 6.2**: 結構化輸出實現
- [ ] **Task 6.3**: 圖片URL嵌入
- [ ] **Task 6.4**: 元數據管理
- [ ] **Task 6.5**: 輸出格式驗證

#### 6.2.7 知識庫集成
- [ ] **Task 7.1**: Azure AI Search適配器
- [ ] **Task 7.2**: Diffy知識庫適配器
- [ ] **Task 7.3**: Copilot Studio適配器
- [ ] **Task 7.4**: 通用RAG接口
- [ ] **Task 7.5**: 索引性能優化

#### 6.2.8 測試和部署
- [ ] **Task 8.1**: 單元測試實現
- [ ] **Task 8.2**: 集成測試設計
- [ ] **Task 8.3**: 性能基準測試
- [ ] **Task 8.4**: 文檔和說明書
- [ ] **Task 8.5**: 部署腳本和配置

---

## 7. 技術實現細節

### 7.1 關聯關係數據結構
```json
{
    "document_id": "doc_20240315_001",
    "paragraphs": [
        {
            "id": "p001",
            "content": "圖表1顯示了銷售趨勢的變化...",
            "position": {"page": 1, "x": 100, "y": 200},
            "associated_images": [
                {
                    "image_id": "img001",
                    "url": "https://storage.example.com/images/doc_001_img001.jpg",
                    "relevance_score": 0.95,
                    "association_type": "direct_reference"
                }
            ]
        }
    ]
}
```

### 7.2 搜索增強策略（更新版）
1. **智能分塊索引**：使用unstructured進行語義感知分塊
2. **圖文關聯索引**：建立圖片與段落的雙向索引
3. **Caption增強檢索**：優先返回具有直接引用的內容
4. **空間關係檢索**：支持「圖片下方的文字」等空間查詢
5. **多模態融合檢索**：同時返回相關文本和圖片
6. **關聯度排序**：根據圖文關聯度重新排序搜索結果

### 7.3 性能優化策略
1. **並行處理**：文件解析和圖片處理並行執行
2. **緩存機制**：重複文件的解析結果緩存
3. **分塊處理**：大文件分塊處理避免內存溢出
4. **增量更新**：支持文件的增量更新和索引

---

## 8. 風險評估與應對

### 8.1 技術風險（更新評估）
| 風險項目 | 風險級別 | 應對策略 | 更新狀態 |
|---------|---------|---------|---------|
| OCR識別準確性 | 低 | PyMuPDF內建優化，備用OCR引擎 | 風險降低 |
| 圖文關聯準確性 | 中 | Allen空間邏輯+Caption檢測，測試驅動優化 | 有所改善 |
| 大文件處理性能 | 低 | PyMuPDF高效率，分塊+並行處理 | 風險降低 |
| 多格式兼容性 | 低 | 備用解析器機制，測試套件完善 | 有所改善 |
| 空間關係計算複雜度 | 中 | 優化算法，緩存機制 | 新增風險 |

### 8.2 業務風險
| 風險項目 | 風險級別 | 應對策略 |
|---------|---------|---------|
| 用戶需求變更 | 中 | 模組化設計，靈活配置 |
| 平台集成困難 | 高 | 提前調研，標準化接口 |
| 數據安全問題 | 高 | 加密存儲，訪問控制 |

---

## 9. 成功標準與驗收標準

### 9.1 功能性標準
- [ ] 支持Word、PDF、PowerPoint三種格式
- [ ] 圖片提取準確率 ≥ 95%
- [ ] 文本提取準確率 ≥ 98%
- [ ] 圖文關聯準確率 ≥ 85%
- [ ] Markdown格式符合標準

### 9.2 性能標準
- [ ] 單個文件處理時間 < 30秒（10MB文件）
- [ ] 系統並發處理能力 ≥ 10個文件
- [ ] 圖片存儲和訪問響應時間 < 2秒
- [ ] 內存使用量 < 2GB（處理100MB文件）

### 9.3 可用性標準
- [ ] 系統可用性 ≥ 99.5%
- [ ] 錯誤恢復時間 < 5分鐘
- [ ] 用戶界面響應時間 < 3秒
- [ ] 支持批量文件處理

---

## 10. 項目進度追蹤

### 10.1 每週檢查點
- **週一**：週進度評估和任務調整
- **週三**：技術難點討論和解決方案
- **週五**：週總結和下週計劃

### 10.2 月度里程碑評估
- 功能完成度評估
- 代碼質量審查
- 性能基準測試
- 用戶反饋收集

### 10.3 風險監控機制
- 每日技術風險評估
- 每週業務風險回顧
- 每月風險應對策略調整

---

## 11. 附錄

### 11.1 技術選型對比（2024-2025年最新評估）
| 功能模組 | 選項A | 選項B | 選項C | 推薦選擇 | 性能評分 | 理由 |
|---------|-------|-------|-------|----------|----------|------|
| PDF解析 | PyMuPDF | pymupdf4llm | unstructured | PyMuPDF + pymupdf4llm | A: 9.5/10, B: 9.0/10 | 速度最快+最佳Markdown輸出 |
| Word解析 | python-docx | mammoth | - | python-docx | 8.5/10 | 更好的格式支持和穩定性 |
| PPT解析 | python-pptx | comtypes | - | python-pptx | 8.0/10 | 原生支持，跨平台兼容 |
| 空間分析 | 傳統幾何算法 | Allen區間邏輯 | - | Allen區間邏輯 | 9.0/10 | 更準確的空間關係建模 |
| Caption檢測 | 基礎正則 | 增強正則+位置 | ML模型 | 增強正則+位置 | 8.5/10 | 準確率高，計算效率好 |
| 圖片存儲 | 本地存儲 | 雲端存儲 | CDN | 雲端+CDN | 9.0/10 | 擴展性+訪問速度 |
| 向量化 | OpenAI API | 本地模型 | 混合方案 | 混合方案 | 8.5/10 | 平衡成本、性能和隱私 |

### 11.2 參考資料和標準
- Markdown規範：CommonMark
- RAG最佳實踐：LangChain文檔
- 圖像處理：OpenCV官方文檔
- 知識庫設計：Azure AI Search文檔
- Allen時間邏輯：Allen's Interval Algebra論文
- 空間關聯分析：Document Layout Analysis最新研究

### 11.3 實施建議（基於2024-2025最新研究）

#### 11.3.1 技術棧更新建議
```python
# 推薦的核心技術棧
CORE_LIBRARIES = {
    "pdf_primary": "PyMuPDF",           # 主要PDF解析器 (速度最快)
    "pdf_markdown": "pymupdf4llm",      # Markdown輸出專用
    "pdf_semantic": "unstructured",     # 語義分塊專用  
    "word": "python-docx",              # Word文檔解析
    "ppt": "python-pptx",               # PowerPoint解析
    "spatial_logic": "custom_allen",    # 自實現Allen邏輯
    "nlp": "sentence-transformers",     # 語義向量化
}
```

#### 11.3.2 開發優先順序
1. **第一階段**：PyMuPDF + Caption檢測（核心功能）
2. **第二階段**：Allen空間邏輯實現（關鍵算法）
3. **第三階段**：語義融合和優化（增強功能）

#### 11.3.3 性能基準
- PDF解析：< 0.2秒（PyMuPDF）
- 圖文關聯：Caption檢測準確率 > 90%
- 空間關係：Allen邏輯計算 < 0.1秒
- 整體處理：10MB文件 < 30秒

---

**文檔版本**：1.2  
**創建日期**：2025年8月8日  
**更新日期**：2025年8月8日  
**負責人**：[項目負責人姓名]  
**審核人**：[審核人姓名]  
**更新內容**：新增第4章項目結構設計，整合完整的代碼架構和部署配置設計
