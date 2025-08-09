"""
知識庫適配器基類
Base Knowledge Base Adapter

定義所有知識庫適配器的統一接口和數據結構。
使用抽象基類確保所有適配器實現相同的接口，提供一致的API體驗。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from src.config.logging_config import get_logger

logger = get_logger("knowledge_base.base")

class DocumentStatus(Enum):
    """文檔狀態枚舉"""
    PENDING = "pending"       # 待處理
    INDEXING = "indexing"     # 索引中
    INDEXED = "indexed"       # 已索引
    ERROR = "error"           # 錯誤
    DELETED = "deleted"       # 已刪除

class SearchMode(Enum):
    """搜索模式枚舉"""
    SEMANTIC = "semantic"     # 語義搜索
    KEYWORD = "keyword"       # 關鍵詞搜索
    HYBRID = "hybrid"         # 混合搜索
    ASSOCIATION = "association"  # 關聯搜索（圖文關聯）

@dataclass
class DocumentRecord:
    """
    文檔記錄數據類
    
    表示知識庫中的一個文檔記錄，包含文檔內容、元數據和關聯信息。
    """
    # 基本信息
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    content: str = ""  # Markdown內容
    
    # 元數據
    source_file: str = ""
    file_format: str = ""
    file_size: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 狀態和版本
    status: DocumentStatus = DocumentStatus.PENDING
    version: int = 1
    
    # 關聯信息
    associations: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    
    # 向量信息
    content_vector: Optional[List[float]] = None
    vector_dimension: int = 0
    
    # 自定義字段
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "document_id": self.document_id,
            "title": self.title,
            "content": self.content,
            "source_file": self.source_file,
            "file_format": self.file_format,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "version": self.version,
            "associations": self.associations,
            "images": self.images,
            "content_vector": self.content_vector,
            "vector_dimension": self.vector_dimension,
            "custom_fields": self.custom_fields
        }

@dataclass 
class SearchQuery:
    """
    搜索查詢數據類
    
    封裝搜索請求的所有參數。
    """
    query_text: str
    mode: SearchMode = SearchMode.SEMANTIC
    top_k: int = 10
    min_score: float = 0.5
    
    # 過濾條件
    filters: Dict[str, Any] = field(default_factory=dict)
    file_formats: List[str] = field(default_factory=list)
    date_range: Optional[tuple] = None
    
    # 關聯搜索特定
    include_associations: bool = True
    association_threshold: float = 0.7
    
    # 高級選項
    highlight: bool = True
    include_vectors: bool = False
    expand_query: bool = False

@dataclass
class SearchResult:
    """
    搜索結果數據類
    
    封裝搜索響應的結構。
    """
    document_id: str
    title: str
    content: str
    score: float
    
    # 高亮信息
    highlights: List[str] = field(default_factory=list)
    
    # 元數據
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 關聯信息
    associated_images: List[Dict[str, Any]] = field(default_factory=list)
    association_scores: List[float] = field(default_factory=list)
    
    # 搜索上下文
    search_mode: Optional[SearchMode] = None
    matched_fields: List[str] = field(default_factory=list)

@dataclass
class IndexConfig:
    """
    索引配置數據類
    
    定義知識庫索引的配置參數。
    """
    index_name: str
    description: str = ""
    
    # 向量配置
    vector_dimension: int = 384  # sentence-transformers默認維度
    vector_model: str = "all-MiniLM-L6-v2"
    
    # 搜索配置
    enable_semantic_search: bool = True
    enable_keyword_search: bool = True
    enable_hybrid_search: bool = True
    
    # 關聯配置
    enable_association_search: bool = True
    association_weight: float = 0.3
    
    # 性能配置
    batch_size: int = 100
    max_content_length: int = 10000
    
    # 自定義字段定義
    custom_fields: Dict[str, str] = field(default_factory=dict)

# 異常類定義
class KnowledgeBaseError(Exception):
    """知識庫操作基礎異常"""
    pass

class DocumentNotFoundError(KnowledgeBaseError):
    """文檔未找到異常"""
    pass

class IndexingError(KnowledgeBaseError):
    """索引操作異常"""
    pass

class SearchError(KnowledgeBaseError):
    """搜索操作異常"""
    pass

class BaseKnowledgeAdapter(ABC):
    """
    知識庫適配器抽象基類
    
    定義所有知識庫適配器必須實現的接口。
    使用異步方法支援高效的I/O操作。
    """
    
    def __init__(self, config: IndexConfig, **kwargs):
        """
        初始化適配器
        
        Args:
            config: 索引配置
            **kwargs: 平台特定的配置參數
        """
        self.config = config
        self.logger = get_logger(f"knowledge_base.{self.__class__.__name__.lower()}")
        self._initialized = False
        
    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """適配器名稱"""
        pass
    
    @property
    @abstractmethod
    def supported_features(self) -> List[str]:
        """支援的功能列表"""
        pass
    
    # 初始化和配置方法
    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化適配器
        
        Returns:
            bool: 是否初始化成功
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查
        
        Returns:
            Dict[str, Any]: 健康狀態信息
        """
        pass
    
    # 索引管理方法
    @abstractmethod
    async def create_index(self, index_config: Optional[IndexConfig] = None) -> bool:
        """
        創建索引
        
        Args:
            index_config: 索引配置（如果為None則使用默認配置）
            
        Returns:
            bool: 是否創建成功
        """
        pass
    
    @abstractmethod
    async def delete_index(self, index_name: str) -> bool:
        """
        刪除索引
        
        Args:
            index_name: 索引名稱
            
        Returns:
            bool: 是否刪除成功
        """
        pass
    
    @abstractmethod
    async def list_indexes(self) -> List[str]:
        """
        列出所有索引
        
        Returns:
            List[str]: 索引名稱列表
        """
        pass
    
    # 文檔操作方法
    @abstractmethod
    async def index_document(self, document: DocumentRecord) -> str:
        """
        索引單個文檔
        
        Args:
            document: 文檔記錄
            
        Returns:
            str: 文檔ID
            
        Raises:
            IndexingError: 索引失敗時拋出
        """
        pass
    
    @abstractmethod
    async def index_documents(self, documents: List[DocumentRecord]) -> List[str]:
        """
        批量索引文檔
        
        Args:
            documents: 文檔記錄列表
            
        Returns:
            List[str]: 文檔ID列表
            
        Raises:
            IndexingError: 索引失敗時拋出
        """
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        """
        獲取文檔
        
        Args:
            document_id: 文檔ID
            
        Returns:
            Optional[DocumentRecord]: 文檔記錄，如果不存在則返回None
        """
        pass
    
    @abstractmethod
    async def update_document(self, document_id: str, document: DocumentRecord) -> bool:
        """
        更新文檔
        
        Args:
            document_id: 文檔ID
            document: 更新的文檔記錄
            
        Returns:
            bool: 是否更新成功
            
        Raises:
            DocumentNotFoundError: 文檔不存在時拋出
        """
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """
        刪除文檔
        
        Args:
            document_id: 文檔ID
            
        Returns:
            bool: 是否刪除成功
        """
        pass
    
    # 搜索方法
    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        搜索文檔
        
        Args:
            query: 搜索查詢
            
        Returns:
            List[SearchResult]: 搜索結果列表
            
        Raises:
            SearchError: 搜索失敗時拋出
        """
        pass
    
    @abstractmethod
    async def semantic_search(self, query_text: str, top_k: int = 10, 
                            min_score: float = 0.5) -> List[SearchResult]:
        """
        語義搜索
        
        Args:
            query_text: 查詢文本
            top_k: 返回結果數量
            min_score: 最小相關度分數
            
        Returns:
            List[SearchResult]: 搜索結果列表
        """
        pass
    
    @abstractmethod
    async def association_search(self, query_text: str, 
                               include_images: bool = True,
                               top_k: int = 10) -> List[SearchResult]:
        """
        關聯搜索（基於圖文關聯）
        
        Args:
            query_text: 查詢文本
            include_images: 是否包含圖片關聯
            top_k: 返回結果數量
            
        Returns:
            List[SearchResult]: 搜索結果列表
        """
        pass
    
    # 統計和監控方法
    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """
        獲取統計信息
        
        Returns:
            Dict[str, Any]: 統計信息
        """
        pass
    
    # 工具方法
    async def validate_document(self, document: DocumentRecord) -> List[str]:
        """
        驗證文檔有效性
        
        Args:
            document: 文檔記錄
            
        Returns:
            List[str]: 驗證錯誤列表，空列表表示無錯誤
        """
        errors = []
        
        if not document.document_id:
            errors.append("document_id不能為空")
            
        if not document.title and not document.content:
            errors.append("title和content不能同時為空")
            
        if document.content and len(document.content) > self.config.max_content_length:
            errors.append(f"content長度不能超過{self.config.max_content_length}")
            
        return errors
    
    def _ensure_initialized(self):
        """確保適配器已初始化"""
        if not self._initialized:
            raise KnowledgeBaseError(f"適配器 {self.adapter_name} 尚未初始化")

# 工具函數
def create_document_from_markdown(markdown_content: str, 
                                source_file: str,
                                associations: List[Dict[str, Any]] = None,
                                **kwargs) -> DocumentRecord:
    """
    從Markdown內容創建文檔記錄
    
    Args:
        markdown_content: Markdown內容
        source_file: 來源文件路徑
        associations: 關聯信息
        **kwargs: 其他文檔屬性
        
    Returns:
        DocumentRecord: 文檔記錄
    """
    # 從文件路徑提取標題
    from pathlib import Path
    title = kwargs.pop('title', None) or Path(source_file).stem
    
    return DocumentRecord(
        title=title,
        content=markdown_content,
        source_file=source_file,
        file_format=Path(source_file).suffix.lower(),
        file_size=len(markdown_content.encode('utf-8')),
        associations=associations or [],
        **kwargs
    )
