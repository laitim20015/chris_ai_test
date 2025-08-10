# 智能文檔轉換系統 - 快速開始指南
## Quick Start Guide

**版本**：v1.2  
**創建日期**：2025年8月10日

---

## 📋 目錄

1. [系統要求](#系統要求)
2. [安裝與配置](#安裝與配置)
3. [基本使用](#基本使用)
4. [API接口](#api接口)
5. [進階配置](#進階配置)
6. [故障排除](#故障排除)

---

## 🔧 系統要求

### 基本要求
- **Python**: >= 3.9 (推薦 3.11)
- **內存**: >= 4GB (推薦 8GB+)
- **存儲**: >= 2GB 可用空間
- **操作系統**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+

### 可選要求（提升性能）
- **GPU**: NVIDIA GPU (支援CUDA) - 語義分析加速
- **Redis**: 用於分散式限流和緩存
- **雲端存儲**: Azure Blob Storage / AWS S3 / Google Cloud Storage

---

## 🚀 安裝與配置

### 1. 克隆專案

```bash
git clone https://github.com/your-org/AP_Project_RAG.git
cd AP_Project_RAG
```

### 2. 創建虛擬環境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安裝依賴

```bash
pip install -r requirements.txt
```

### 4. 環境配置

複製環境變數範本並配置：

```bash
cp .env.example .env
```

編輯 `.env` 文件：

```env
# 基本配置
APP_DEBUG=true
APP_LOG_LEVEL=INFO

# 文件處理配置
MAX_FILE_SIZE_MB=100
SUPPORTED_FORMATS=pdf,docx,pptx

# Azure OpenAI配置（可選）
AZURE_OPENAI_ENDPOINT=your-endpoint
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment

# 存儲配置（可選）
STORAGE_TYPE=local  # local, azure, aws, gcs
AZURE_STORAGE_CONNECTION_STRING=your-connection-string

# 限流配置
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

---

## 💻 基本使用

### 1. 命令行處理單個文檔

```bash
python -m src.main process-document tests/fixtures/documents/sample.pdf
```

### 2. Python API使用

```python
import asyncio
from pathlib import Path
from src.main import DocumentProcessor

async def main():
    # 初始化處理器
    processor = DocumentProcessor()
    
    # 處理文檔
    result = await processor.process_document("path/to/document.pdf")
    
    # 獲取結果
    markdown_content = result["markdown_content"]
    associations = result["associations"] 
    metadata = result["metadata"]
    
    print(f"生成了 {len(associations)} 個圖文關聯")
    print(f"文檔包含 {len(metadata['text_blocks'])} 個文本塊")
    
    # 保存結果
    with open("output.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)

# 運行
asyncio.run(main())
```

### 3. 批量處理

```python
import asyncio
from pathlib import Path
from src.main import DocumentProcessor

async def batch_process():
    processor = DocumentProcessor()
    input_dir = Path("data/input/documents")
    output_dir = Path("data/output/markdown")
    
    for file_path in input_dir.glob("*.pdf"):
        print(f"處理文檔: {file_path.name}")
        
        try:
            result = await processor.process_document(file_path)
            
            # 保存Markdown
            output_file = output_dir / f"{file_path.stem}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result["markdown_content"])
                
            print(f"✅ 完成: {output_file}")
            
        except Exception as e:
            print(f"❌ 錯誤: {e}")

asyncio.run(batch_process())
```

---

## 🌐 API接口

### 1. 啟動API服務器

```bash
python -m src.api.main
```

或使用uvicorn：

```bash
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### 2. 上傳文檔

```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf"
```

響應：
```json
{
  "status": "success",
  "file_id": "doc_20250810_001",
  "filename": "sample.pdf",
  "size": 1024000
}
```

### 3. 處理文檔

```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "doc_20250810_001",
    "options": {
      "include_associations": true,
      "template": "enhanced"
    }
  }'
```

響應：
```json
{
  "status": "success",
  "processing_id": "proc_20250810_001",
  "estimated_time": 30
}
```

### 4. 查詢處理狀態

```bash
curl "http://localhost:8000/status/proc_20250810_001"
```

響應：
```json
{
  "status": "completed",
  "progress": 100,
  "result": {
    "markdown_url": "/download/markdown/proc_20250810_001.md",
    "associations_count": 15,
    "processing_time": 25.6
  }
}
```

### 5. 下載結果

```bash
# 下載Markdown
curl "http://localhost:8000/download/markdown/proc_20250810_001.md" -o result.md

# 下載關聯數據
curl "http://localhost:8000/download/associations/proc_20250810_001.json" -o associations.json
```

---

## ⚙️ 進階配置

### 1. 關聯算法調優

```python
from src.association import OptimizationConfig, create_balanced_config

# 使用預設配置
config = create_balanced_config()

# 自定義配置
custom_config = OptimizationConfig(
    min_score_threshold=0.5,        # 提高閾值，減少低質量關聯
    max_associations_per_image=3,   # 限制每圖關聯數
    caption_boost_factor=1.3,       # 增強Caption權重
    prioritize_quality=True         # 優先保留高質量關聯
)
```

### 2. 性能監控

```python
from src.utils.performance_benchmarks import get_profiler

# 獲取性能分析器
profiler = get_profiler()

# 創建測試套件
suite = profiler.create_benchmark_suite(
    "production_benchmark",
    "生產環境性能基準測試"
)

# 基準測試
results = profiler.benchmark_function(
    processor.process_document,
    args=("sample.pdf",),
    iterations=5
)

# 生成報告
report = profiler.generate_report("production_benchmark")
print(f"平均處理時間: {report['performance_stats']['execution_time']['avg']:.2f}s")
```

### 3. 錯誤處理配置

```python
from src.utils.error_handling import get_error_handler, ErrorCategory, ErrorSeverity

# 獲取錯誤處理器
error_handler = get_error_handler()

# 自定義錯誤處理
try:
    result = await processor.process_document("problematic.pdf")
except Exception as e:
    error_info = error_handler.handle_error(
        e,
        category=ErrorCategory.PARSING,
        severity=ErrorSeverity.HIGH,
        context={"file": "problematic.pdf", "user": "admin"}
    )
    
    # 獲取錯誤統計
    stats = error_handler.get_error_statistics()
    print(f"總錯誤數: {stats['total_errors']}")
```

### 4. 雲端存儲配置

```python
# Azure Blob Storage
storage_config = {
    "type": "azure",
    "connection_string": "your-connection-string",
    "container_name": "documents"
}

# AWS S3
storage_config = {
    "type": "aws",
    "access_key": "your-access-key",
    "secret_key": "your-secret-key",
    "bucket_name": "documents",
    "region": "us-east-1"
}

# 初始化帶存儲的處理器
processor = DocumentProcessor(storage_config=storage_config)
```

---

## 🔧 故障排除

### 常見問題

#### 1. 內存不足錯誤

**錯誤**: `MemoryError: Unable to allocate memory`

**解決方案**:
```python
# 啟用分塊處理
processor = DocumentProcessor(
    chunk_size=1000,  # 減小塊大小
    max_memory_usage="2GB"  # 限制內存使用
)
```

#### 2. PDF解析失敗

**錯誤**: `PDFParsingError: Cannot parse PDF`

**解決方案**:
```python
# 檢查PDF解析器優先級
from src.parsers import get_parser_info
print(get_parser_info())

# 強制使用特定解析器
result = await processor.process_document(
    "problematic.pdf",
    parser_preference=["pymupdf4llm", "unstructured"]
)
```

#### 3. 模型加載失敗

**錯誤**: `ModelNotFoundError: sentence-transformers model not found`

**解決方案**:
```bash
# 手動下載模型
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# 或使用離線模式
export TRANSFORMERS_OFFLINE=1
```

#### 4. API限流問題

**錯誤**: `429 Too Many Requests`

**解決方案**:
```env
# 調整限流配置
RATE_LIMIT_REQUESTS_PER_MINUTE=120
RATE_LIMIT_REQUESTS_PER_HOUR=2000

# 或禁用限流（僅開發環境）
RATE_LIMIT_ENABLED=false
```

### 日誌調試

啟用詳細日誌：

```python
import logging
from src.config.logging_config import setup_logging

# 設置調試級別
setup_logging(level=logging.DEBUG)

# 查看特定組件日誌
logger = logging.getLogger("association_analyzer")
logger.setLevel(logging.DEBUG)
```

### 性能調優

```python
# 檢查系統資源
import psutil
print(f"CPU核心數: {psutil.cpu_count()}")
print(f"可用內存: {psutil.virtual_memory().available / 1024**3:.1f}GB")

# 調整並發配置
processor = DocumentProcessor(
    max_workers=psutil.cpu_count() // 2,  # 使用一半CPU核心
    enable_gpu=True,  # 如果有GPU
    cache_embeddings=True  # 啟用嵌入緩存
)
```

---

## 📚 進階主題

### 1. 自定義解析器

```python
from src.parsers.base import BaseParser
from src.parsers import register_parser

class CustomParser(BaseParser):
    def parse(self, file_path: str) -> ParsedContent:
        # 實現自定義解析邏輯
        pass

# 註冊自定義解析器
register_parser("custom", CustomParser, priority=1)
```

### 2. 知識庫集成

```python
from src.knowledge_base import KnowledgeBaseFactory

# 初始化知識庫適配器
factory = KnowledgeBaseFactory()
adapter = factory.get_adapter("azure_ai_search")

# 配置連接
await adapter.initialize({
    "endpoint": "your-search-endpoint",
    "api_key": "your-api-key",
    "index_name": "documents"
})

# 索引文檔
documents = [create_document_from_markdown(markdown_content, "source.pdf")]
await adapter.index_documents(documents, "documents")
```

### 3. 自定義Markdown模板

創建自定義模板 `templates/custom.md.j2`：

```jinja2
# {{ title }}

{{ description }}

## 文檔內容

{% for block in text_blocks %}
### {{ block.heading or "段落 " ~ loop.index }}

{{ block.content }}

{% if block.associated_images %}
**相關圖片:**
{% for image in block.associated_images %}
- ![{{ image.alt_text }}]({{ image.url }}) (關聯度: {{ "%.2f" | format(image.score) }})
{% endfor %}
{% endif %}

{% endfor %}

## 圖片總覽

{% for image in images %}
![{{ image.alt_text }}]({{ image.url }})
{% endfor %}

---
*由智能文檔轉換系統生成於 {{ generation_time }}*
```

使用自定義模板：

```python
result = await processor.process_document(
    "document.pdf",
    template_name="custom.md.j2"
)
```

---

## 📞 技術支援

### 文檔資源
- **技術規格**: `docs/technical_specs/`
- **API文檔**: `docs/api/`
- **開發者指南**: `docs/developer_guide/`

### 社群支援
- **GitHub Issues**: [專案Issues](https://github.com/your-org/AP_Project_RAG/issues)
- **討論區**: [GitHub Discussions](https://github.com/your-org/AP_Project_RAG/discussions)

### 聯繫方式
- **技術問題**: tech-support@your-org.com
- **功能建議**: feature-requests@your-org.com

---

**最後更新**: 2025年8月10日  
**版本**: v1.2  
**維護團隊**: 智能文檔轉換系統開發團隊
