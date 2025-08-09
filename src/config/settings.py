"""
系統配置設置
System Configuration Settings

基於Pydantic的類型安全配置管理，嚴格遵循項目規則：
- PDF解析器優先級：PyMuPDF -> pymupdf4llm -> unstructured
- 關聯度權重：Caption(0.4) > Spatial(0.3) > Semantic(0.15) > Layout(0.1) > Proximity(0.05)
- FastAPI和現代Python配置最佳實踐
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from functools import lru_cache

class AppSettings(BaseSettings):
    """應用程序基本配置"""
    
    name: str = Field(default="AP Project RAG System", description="應用名稱")
    version: str = Field(default="1.0.0", description="應用版本")
    description: str = Field(default="智能文件轉換與RAG知識庫系統", description="應用描述")
    debug: bool = Field(default=False, description="調試模式")
    environment: Literal["development", "staging", "production"] = Field(
        default="production", description="運行環境"
    )
    
    class Config:
        env_prefix = "APP_"
        case_sensitive = False

class ParserSettings(BaseSettings):
    """文件解析器配置（嚴格按照項目規則）"""
    
    # PDF解析器優先級（必須按此順序）
    pdf_primary_parser: Literal["pymupdf"] = Field(
        default="pymupdf", description="主要PDF解析器（性能優先）"
    )
    pdf_markdown_parser: Literal["pymupdf4llm"] = Field(
        default="pymupdf4llm", description="Markdown輸出專用解析器"
    )
    pdf_semantic_parser: Literal["unstructured"] = Field(
        default="unstructured", description="語義分塊專用解析器"
    )
    
    # 解析超時配置
    pdf_parse_timeout: int = Field(default=120, description="PDF解析超時（秒）")
    word_parse_timeout: int = Field(default=60, description="Word解析超時（秒）")
    ppt_parse_timeout: int = Field(default=90, description="PPT解析超時（秒）")
    
    # 支持的文件格式
    supported_formats: List[str] = Field(
        default=["pdf", "docx", "pptx"], description="支持的文件格式"
    )
    
    # 文件大小限制（MB）
    max_file_size: int = Field(default=100, description="最大文件大小（MB）")
    max_batch_size: int = Field(default=10, description="批量處理最大文件數")
    
    class Config:
        env_prefix = "PDF_"
        case_sensitive = False

class AssociationSettings(BaseSettings):
    """圖文關聯分析配置（核心算法配置）"""
    
    # 關聯度評分權重（必須嚴格遵循項目規則）
    caption_weight: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Caption檢測權重（最高優先級）"
    )
    spatial_weight: float = Field(
        default=0.3, ge=0.0, le=1.0, description="空間關係權重"
    )
    semantic_weight: float = Field(
        default=0.15, ge=0.0, le=1.0, description="語義相似度權重"
    )
    layout_weight: float = Field(
        default=0.1, ge=0.0, le=1.0, description="佈局模式權重"
    )
    proximity_weight: float = Field(
        default=0.05, ge=0.0, le=1.0, description="距離權重"
    )
    
    # 關聯度閾值
    min_association_score: float = Field(
        default=0.3, ge=0.0, le=1.0, description="最小關聯度閾值"
    )
    high_confidence_score: float = Field(
        default=0.8, ge=0.0, le=1.0, description="高置信度閾值"
    )
    
    # Caption檢測配置
    caption_patterns: List[str] = Field(
        default=[
            r'^(Figure|Fig|圖|表|Table)\s*\d+',
            r'^(Chart|Diagram|Image)\s*\d+',
            r'如圖\s*\d+|見圖\s*\d+'
        ],
        description="Caption檢測正則表達式模式"
    )
    
    # Allen邏輯空間關係
    allen_relations: Dict[str, str] = Field(
        default={
            "precedes": "<",
            "meets": "|", 
            "overlaps": "o",
            "during": "d",
            "above": "^",
            "below": "v",
            "adjacent": "~"
        },
        description="Allen區間邏輯空間關係映射"
    )
    
    @model_validator(mode='after')
    def validate_weights(self):
        """驗證權重總和必須為1.0且Caption權重最高"""
        weights = [
            self.caption_weight,
            self.spatial_weight,
            self.semantic_weight,
            self.layout_weight,
            self.proximity_weight
        ]
        
        total = sum(weights)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"權重總和必須為1.0，當前為: {total}")
        
        max_weight = max(weights)
        if self.caption_weight != max_weight:
            raise ValueError("Caption權重必須為最高（項目規則要求）")
        
        return self
    
    class Config:
        env_prefix = "CAPTION_"
        case_sensitive = False

class ImageSettings(BaseSettings):
    """圖片處理配置"""
    
    # 圖片質量和尺寸
    quality: int = Field(default=85, ge=1, le=100, description="圖片質量")
    max_width: int = Field(default=1920, description="最大寬度")
    max_height: int = Field(default=1080, description="最大高度")
    format: Literal["jpg", "png", "webp"] = Field(default="jpg", description="圖片格式")
    
    # 命名規範
    naming_pattern: str = Field(
        default="{filename}_{page}_{image_seq}_{timestamp}.{format}",
        description="圖片命名規範"
    )
    
    class Config:
        env_prefix = "IMAGE_"
        case_sensitive = False

class StorageSettings(BaseSettings):
    """存儲配置"""
    
    # 存儲類型
    storage_type: Literal["local", "azure", "aws", "gcp"] = Field(
        default="local", description="存儲類型"
    )
    
    # 本地存儲路徑
    local_path: Path = Field(default="./data", description="本地存儲路徑")
    temp_path: Path = Field(default="./data/temp", description="臨時文件路徑")
    output_path: Path = Field(default="./data/output", description="輸出文件路徑")
    
    # 雲存儲配置
    azure_account_name: Optional[str] = Field(default=None, description="Azure存儲賬戶名")
    azure_container_name: str = Field(default="rag-documents", description="Azure容器名")
    
    aws_bucket: str = Field(default="rag-documents", description="AWS S3桶名")
    aws_region: str = Field(default="us-east-1", description="AWS區域")
    
    gcp_bucket: str = Field(default="rag-documents", description="GCP存儲桶名")
    
    class Config:
        env_prefix = "STORAGE_"
        case_sensitive = False

class DatabaseSettings(BaseSettings):
    """數據庫配置"""
    
    # Redis配置
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis連接URL")
    redis_password: Optional[str] = Field(default=None, description="Redis密碼")
    redis_db: int = Field(default=0, description="Redis數據庫編號")
    
    # PostgreSQL配置
    postgres_url: Optional[str] = Field(default=None, description="PostgreSQL連接URL")
    db_pool_size: int = Field(default=10, description="數據庫連接池大小")
    db_max_overflow: int = Field(default=20, description="數據庫連接池最大溢出")
    
    class Config:
        env_prefix = "REDIS_"
        case_sensitive = False

class APISettings(BaseSettings):
    """API配置"""
    
    # 服務器配置
    host: str = Field(default="0.0.0.0", description="主機地址")
    port: int = Field(default=8000, description="端口號")
    workers: int = Field(default=4, description="工作進程數")
    reload: bool = Field(default=False, description="自動重載")
    
    # 安全配置
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="密鑰")
    api_key: Optional[str] = Field(default=None, description="API密鑰")
    access_token_expire_minutes: int = Field(default=30, description="訪問令牌過期時間")
    
    # CORS配置
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"], description="CORS允許的源"
    )
    
    # 限流配置
    rate_limit_enabled: bool = Field(default=True, description="啟用限流")
    rate_limit_requests_per_minute: int = Field(default=60, description="每分鐘請求數限制")
    
    class Config:
        env_prefix = ""
        case_sensitive = False

class LoggingSettings(BaseSettings):
    """日誌配置"""
    
    # 日誌級別
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="日誌級別"
    )
    format: Literal["text", "json"] = Field(default="json", description="日誌格式")
    
    # 日誌文件
    file_path: Optional[Path] = Field(default="./logs/app.log", description="日誌文件路徑")
    rotation: str = Field(default="1 week", description="日誌輪轉")
    retention: str = Field(default="30 days", description="日誌保留時間")
    
    class Config:
        env_prefix = "LOG_"
        case_sensitive = False

class Settings(BaseSettings):
    """主配置類，包含所有子配置"""
    
    app: AppSettings = Field(default_factory=AppSettings)
    parser: ParserSettings = Field(default_factory=ParserSettings)
    association: AssociationSettings = Field(default_factory=AssociationSettings)
    image: ImageSettings = Field(default_factory=ImageSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    # AI模型配置
    sentence_transformer_model: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence Transformer模型名稱"
    )
    model_cache_dir: Path = Field(default="./data/models", description="模型緩存目錄")
    embedding_dimension: int = Field(default=384, description="向量維度")
    
    # 性能配置
    max_concurrent_processing: int = Field(default=5, description="最大並發處理數")
    enable_parallel_processing: bool = Field(default=True, description="啟用並行處理")
    enable_caching: bool = Field(default=True, description="啟用緩存")
    cache_ttl: int = Field(default=3600, description="緩存TTL（秒）")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def create_directories(self) -> None:
        """創建必要的目錄"""
        directories = [
            self.storage.local_path,
            self.storage.temp_path,
            self.storage.output_path,
            self.model_cache_dir,
            Path("./logs") if self.logging.file_path else None
        ]
        
        for directory in directories:
            if directory:
                directory.mkdir(parents=True, exist_ok=True)

@lru_cache()
def get_settings() -> Settings:
    """
    獲取配置實例（單例模式）
    
    Returns:
        Settings: 配置實例
    """
    settings = Settings()
    settings.create_directories()
    return settings

# 導出便捷函數
def get_association_weights() -> Dict[str, float]:
    """獲取關聯度評分權重"""
    settings = get_settings()
    return {
        "caption_score": settings.association.caption_weight,
        "spatial_score": settings.association.spatial_weight,
        "semantic_score": settings.association.semantic_weight,
        "layout_score": settings.association.layout_weight,
        "proximity_score": settings.association.proximity_weight,
    }

def get_parser_priority() -> List[str]:
    """獲取PDF解析器優先級列表"""
    settings = get_settings()
    return [
        settings.parser.pdf_primary_parser,
        settings.parser.pdf_markdown_parser,
        settings.parser.pdf_semantic_parser
    ]

def validate_project_rules() -> bool:
    """驗證配置是否符合項目規則"""
    try:
        settings = get_settings()
        
        # 驗證解析器優先級
        priority = get_parser_priority()
        expected = ["pymupdf", "pymupdf4llm", "unstructured"]
        if priority != expected:
            return False
        
        # 驗證權重配置
        weights = get_association_weights()
        if abs(sum(weights.values()) - 1.0) > 1e-6:
            return False
        
        if weights["caption_score"] != max(weights.values()):
            return False
        
        return True
        
    except Exception:
        return False
