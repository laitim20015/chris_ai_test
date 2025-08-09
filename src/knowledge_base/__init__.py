"""
知識庫集成模組
Knowledge Base Integration Module

這個模組提供與各種RAG知識庫平台的集成功能，是整個「智能文檔轉換與RAG知識庫系統」的核心組件。

支援的知識庫平台：
- Azure AI Search: 微軟的搜索和索引服務
- Diffy: 開源知識庫平台
- Microsoft Copilot Studio: 微軟的對話AI平台

架構設計：
- 使用適配器模式統一不同平台的API
- 工廠模式管理適配器實例
- 異步操作支援高效的文檔處理
- 統一的錯誤處理和日誌記錄

主要功能：
1. 文檔索引 - 將Markdown文檔和關聯信息索引到知識庫
2. 語義搜索 - 基於向量相似度的智能搜索
3. 文檔管理 - 文檔的增刪改查操作
4. 關聯查詢 - 基於圖文關聯的增強檢索
"""

from .base_adapter import (
    BaseKnowledgeAdapter,
    DocumentRecord,
    SearchResult, 
    IndexConfig,
    SearchQuery,
    KnowledgeBaseError,
    DocumentNotFoundError,
    IndexingError,
    SearchError
)

from .adapter_factory import (
    KnowledgeBaseFactory,
    get_knowledge_adapter,
    list_available_adapters,
    register_adapter
)

# 導入各個適配器
try:
    from .azure_ai_search import AzureAISearchAdapter
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

try:
    from .diffy_adapter import DiffyAdapter  
    DIFFY_AVAILABLE = True
except ImportError:
    DIFFY_AVAILABLE = False

try:
    from .copilot_studio import CopilotStudioAdapter
    COPILOT_AVAILABLE = True
except ImportError:
    COPILOT_AVAILABLE = False

__all__ = [
    # 基礎類和接口
    "BaseKnowledgeAdapter",
    "DocumentRecord", 
    "SearchResult",
    "IndexConfig",
    "SearchQuery",
    
    # 異常類
    "KnowledgeBaseError",
    "DocumentNotFoundError", 
    "IndexingError",
    "SearchError",
    
    # 工廠和管理
    "KnowledgeBaseFactory",
    "get_knowledge_adapter",
    "list_available_adapters",
    "register_adapter",
    
    # 適配器（如果可用）
] + (["AzureAISearchAdapter"] if AZURE_AVAILABLE else []) + \
    (["DiffyAdapter"] if DIFFY_AVAILABLE else []) + \
    (["CopilotStudioAdapter"] if COPILOT_AVAILABLE else [])

# 模組版本和信息
__version__ = "1.0.0"
__description__ = "RAG知識庫集成模組 - 支援多平台統一API"

# 可用適配器註冊表
AVAILABLE_ADAPTERS = {}

if AZURE_AVAILABLE:
    AVAILABLE_ADAPTERS["azure"] = AzureAISearchAdapter
    
if DIFFY_AVAILABLE:
    AVAILABLE_ADAPTERS["diffy"] = DiffyAdapter
    
if COPILOT_AVAILABLE:
    AVAILABLE_ADAPTERS["copilot"] = CopilotStudioAdapter

def get_module_info() -> dict:
    """
    獲取模組信息
    
    Returns:
        dict: 模組信息字典
    """
    return {
        "version": __version__,
        "description": __description__,
        "available_adapters": list(AVAILABLE_ADAPTERS.keys()),
        "azure_available": AZURE_AVAILABLE,
        "diffy_available": DIFFY_AVAILABLE, 
        "copilot_available": COPILOT_AVAILABLE,
        "total_adapters": len(AVAILABLE_ADAPTERS)
    }
