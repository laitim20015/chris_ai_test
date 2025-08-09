"""
配置管理模組
Configuration Management Module

本模組負責整個系統的配置管理，包括：
- 基於Pydantic的類型安全配置
- 環境變量管理
- 日誌配置
- 各模組配置驗證

嚴格遵循項目規則的配置項：
- 解析器優先級配置（PyMuPDF -> pymupdf4llm -> unstructured）
- 關聯度評分權重（Caption: 0.4, Spatial: 0.3, Semantic: 0.15, Layout: 0.1, Proximity: 0.05）
- FastAPI和Pydantic配置管理
"""

from src.config.settings import (
    Settings,
    AppSettings,
    ParserSettings,
    AssociationSettings,
    ImageSettings,
    StorageSettings,
    DatabaseSettings,
    APISettings,
    LoggingSettings,
    get_settings
)

from src.config.logging_config import (
    setup_logging,
    get_logger,
    LogConfig
)

__all__ = [
    # 主要配置類
    "Settings",
    "AppSettings", 
    "ParserSettings",
    "AssociationSettings",
    "ImageSettings",
    "StorageSettings",
    "DatabaseSettings",
    "APISettings",
    "LoggingSettings",
    
    # 配置獲取函數
    "get_settings",
    
    # 日誌配置
    "setup_logging",
    "get_logger",
    "LogConfig",
]

# 配置模組元數據
__version__ = "1.0.0"
__description__ = "智能文件轉換系統配置管理模組"

# 配置驗證常量
REQUIRED_ENV_VARS = [
    "APP_NAME",
    "APP_VERSION", 
    "SECRET_KEY",
]

OPTIONAL_ENV_VARS = [
    "APP_DEBUG",
    "APP_ENVIRONMENT",
    "HOST",
    "PORT",
    "LOG_LEVEL",
]

def validate_config() -> bool:
    """
    驗證系統配置是否完整且符合項目規則
    
    Returns:
        bool: 配置是否有效
    """
    try:
        settings = get_settings()
        
        # 驗證關聯度權重總和
        weights = settings.association
        total_weight = (
            weights.caption_weight + 
            weights.spatial_weight + 
            weights.semantic_weight + 
            weights.layout_weight + 
            weights.proximity_weight
        )
        
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(f"關聯度權重總和必須為1.0，當前為: {total_weight}")
        
        # 驗證Caption權重是否為最高
        max_weight = max(
            weights.caption_weight,
            weights.spatial_weight, 
            weights.semantic_weight,
            weights.layout_weight,
            weights.proximity_weight
        )
        
        if weights.caption_weight != max_weight:
            raise ValueError("Caption權重必須為最高（項目規則）")
        
        # 驗證解析器優先級
        parser_priority = [
            settings.parser.pdf_primary_parser,
            settings.parser.pdf_markdown_parser,
            settings.parser.pdf_semantic_parser
        ]
        
        expected_priority = ["pymupdf", "pymupdf4llm", "unstructured"]
        if parser_priority != expected_priority:
            raise ValueError(f"PDF解析器優先級必須為: {expected_priority}")
        
        return True
        
    except Exception as e:
        print(f"配置驗證失敗: {e}")
        return False

def get_config_summary() -> dict:
    """
    獲取配置摘要信息
    
    Returns:
        dict: 配置摘要
    """
    settings = get_settings()
    
    return {
        "app": {
            "name": settings.app.name,
            "version": settings.app.version,
            "environment": settings.app.environment,
            "debug": settings.app.debug,
        },
        "association_weights": {
            "caption": settings.association.caption_weight,
            "spatial": settings.association.spatial_weight,
            "semantic": settings.association.semantic_weight,
            "layout": settings.association.layout_weight,
            "proximity": settings.association.proximity_weight,
        },
        "parser_priority": {
            "primary": settings.parser.pdf_primary_parser,
            "markdown": settings.parser.pdf_markdown_parser,
            "semantic": settings.parser.pdf_semantic_parser,
        },
        "api": {
            "host": settings.api.host,
            "port": settings.api.port,
            "workers": settings.api.workers,
        },
        "storage": {
            "type": settings.storage.storage_type,
            "local_path": settings.storage.local_path,
        }
    }

# 模組初始化時進行配置驗證
_config_valid = validate_config()
if not _config_valid:
    raise RuntimeError("系統配置驗證失敗，請檢查配置文件和環境變量")

