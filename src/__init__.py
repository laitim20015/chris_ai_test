"""
智能文件轉換與RAG知識庫系統
Intelligent Document Conversion & RAG Knowledge Base System

本系統旨在將多種格式文件（Word、PDF、PowerPoint）轉換為標準化Markdown格式，
並建立精準的圖文關聯關係，用於RAG知識庫的高效檢索。

核心功能：
- 多格式文件解析（PDF、Word、PowerPoint）
- 基於Allen邏輯的智能圖文關聯分析
- Caption檢測（40%權重）和空間關係分析
- 語義相似度計算和加權融合評分
- 標準化Markdown輸出
- 多平台知識庫集成支持

技術特點：
- 基於PyMuPDF的高性能PDF解析
- 工廠模式的可擴展解析器架構
- 基於Pydantic的類型安全配置管理
- FastAPI的現代API框架
- 全面的測試覆蓋和文檔支持

項目規格版本: v1.2
創建日期: 2025年8月8日
更新日期: 2025年8月8日
"""

__version__ = "1.0.0"
__author__ = "AP Project Team"
__email__ = "team@ap-project.com"
__license__ = "MIT"

# 版本信息
VERSION = __version__
VERSION_INFO = tuple(int(x) for x in __version__.split('.'))

# 核心模組導入
from src.config.settings import Settings
from src.config.logging_config import setup_logging

# 初始化配置
_settings = Settings()
_logger = setup_logging()

# 導出主要組件
__all__ = [
    "VERSION",
    "VERSION_INFO", 
    "Settings",
    "setup_logging",
]

# 項目元數據
PROJECT_NAME = "AP Project RAG System"
PROJECT_DESCRIPTION = "智能文件轉換與RAG知識庫系統"
PROJECT_URL = "https://github.com/ap-project/rag-system"

# 支持的文件格式
SUPPORTED_FORMATS = {
    'pdf': ['.pdf'],
    'word': ['.docx', '.doc'],
    'powerpoint': ['.pptx', '.ppt']
}

# 核心常量
CORE_MODULES = [
    "parsers",
    "association", 
    "image_processing",
    "markdown",
    "knowledge_base",
    "api"
]

# 算法優先級配置（嚴格按照項目規則）
ALGORITHM_PRIORITIES = {
    "caption_detection": "highest",    # Caption檢測 - 最高優先級
    "allen_logic": "high",            # Allen區間邏輯 - 高優先級
    "spatial_analysis": "high",       # 空間分析 - 高優先級
    "semantic_analysis": "medium",    # 語義分析 - 中等優先級
}

# 關聯度評分權重（必須嚴格遵循）
ASSOCIATION_WEIGHTS = {
    "caption_score": 0.4,      # Caption檢測權重（最高）
    "spatial_score": 0.3,      # 空間關係權重
    "semantic_score": 0.15,    # 語義相似度權重
    "layout_score": 0.1,       # 佈局模式權重
    "proximity_score": 0.05,   # 距離權重
}

# 驗證權重總和
assert abs(sum(ASSOCIATION_WEIGHTS.values()) - 1.0) < 1e-6, "權重總和必須為1.0"

def get_version() -> str:
    """獲取當前版本號"""
    return __version__

def get_project_info() -> dict:
    """獲取項目基本信息"""
    return {
        "name": PROJECT_NAME,
        "version": __version__,
        "description": PROJECT_DESCRIPTION,
        "url": PROJECT_URL,
        "supported_formats": SUPPORTED_FORMATS,
        "core_modules": CORE_MODULES,
        "algorithm_priorities": ALGORITHM_PRIORITIES,
        "association_weights": ASSOCIATION_WEIGHTS,
    }

def validate_association_weights(weights: dict) -> bool:
    """驗證關聯度權重配置是否符合項目規則"""
    expected_keys = set(ASSOCIATION_WEIGHTS.keys())
    actual_keys = set(weights.keys())
    
    if expected_keys != actual_keys:
        return False
    
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 1e-6:
        return False
    
    # 驗證Caption權重是否為最高
    if weights["caption_score"] != max(weights.values()):
        return False
    
    return True

# 初始化檢查
def _validate_environment():
    """初始化環境驗證"""
    import sys
    
    # 檢查Python版本
    if sys.version_info < (3, 9):
        raise RuntimeError("此項目需要Python 3.9或更高版本")
    
    # 驗證權重配置
    if not validate_association_weights(ASSOCIATION_WEIGHTS):
        raise ValueError("關聯度權重配置不符合項目規則")
    
    return True

# 執行初始化驗證
_validate_environment()

