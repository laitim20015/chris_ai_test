"""
API請求數據模型

定義API端點的請求數據結構，包含文檔上傳、處理、AI對話等請求模型。
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
from datetime import datetime


class DocumentType(str, Enum):
    """支持的文檔類型"""
    PDF = "pdf"
    WORD = "word" 
    POWERPOINT = "powerpoint"


class ProcessingMode(str, Enum):
    """處理模式"""
    BASIC = "basic"          # 基礎轉換
    ENHANCED = "enhanced"    # 增強版（包含圖文關聯）
    FULL = "full"           # 完整版（包含AI分析）


class ChatModel(str, Enum):
    """Azure OpenAI Chat模型"""
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-1106-preview"
    GPT_35_TURBO = "gpt-35-turbo"


class EmbeddingModel(str, Enum):
    """Azure OpenAI Embedding模型"""
    TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"


class DocumentUploadRequest(BaseModel):
    """文檔上傳請求"""
    filename: str = Field(..., description="文件名")
    content_type: str = Field(..., description="MIME類型")
    size: int = Field(..., gt=0, description="文件大小（字節）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "size": 1024000
            }
        }


class ProcessRequest(BaseModel):
    """文檔處理請求"""
    document_id: str = Field(..., description="文檔ID")
    mode: ProcessingMode = Field(
        default=ProcessingMode.ENHANCED, 
        description="處理模式"
    )
    extract_images: bool = Field(default=True, description="是否提取圖片")
    analyze_associations: bool = Field(default=True, description="是否分析圖文關聯")
    generate_embeddings: bool = Field(default=False, description="是否生成向量嵌入")
    
    # 圖文關聯配置
    association_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="圖文關聯算法配置"
    )
    
    # 輸出配置
    output_format: str = Field(default="markdown", description="輸出格式")
    include_metadata: bool = Field(default=True, description="是否包含元數據")
    
    @validator("association_config")
    def validate_association_config(cls, v):
        """驗證關聯配置"""
        if v is not None:
            required_keys = ["caption_weight", "spatial_weight", "semantic_weight"]
            if not all(key in v for key in required_keys):
                raise ValueError(f"關聯配置必須包含: {required_keys}")
            
            # 檢查權重總和
            total_weight = sum(v.get(key, 0) for key in required_keys)
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError("所有權重總和必須等於1.0")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_20250808_001",
                "mode": "enhanced",
                "extract_images": True,
                "analyze_associations": True,
                "generate_embeddings": False,
                "association_config": {
                    "caption_weight": 0.4,
                    "spatial_weight": 0.3,
                    "semantic_weight": 0.15,
                    "layout_weight": 0.1,
                    "proximity_weight": 0.05
                },
                "output_format": "markdown",
                "include_metadata": True
            }
        }


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色：user, assistant, system")
    content: str = Field(..., description="消息內容")
    
    @validator("role")
    def validate_role(cls, v):
        """驗證角色"""
        if v not in ["user", "assistant", "system"]:
            raise ValueError("角色必須是 user, assistant 或 system")
        return v


class ChatRequest(BaseModel):
    """AI對話請求"""
    messages: List[ChatMessage] = Field(..., description="對話歷史")
    model: ChatModel = Field(default=ChatModel.GPT_4, description="使用的模型")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="溫度參數")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4096, description="最大令牌數")
    
    # RAG相關參數
    use_document_context: bool = Field(default=False, description="是否使用文檔上下文")
    document_ids: Optional[List[str]] = Field(default=None, description="相關文檔ID列表")
    include_images: bool = Field(default=False, description="是否包含圖片信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "請總結這個文檔的主要內容"}
                ],
                "model": "gpt-4",
                "temperature": 0.7,
                "use_document_context": True,
                "document_ids": ["doc_20250808_001"],
                "include_images": True
            }
        }


class EmbeddingRequest(BaseModel):
    """向量嵌入請求"""
    texts: List[str] = Field(..., description="要嵌入的文本列表")
    model: EmbeddingModel = Field(
        default=EmbeddingModel.TEXT_EMBEDDING_ADA_002,
        description="嵌入模型"
    )
    
    # 批量處理配置
    batch_size: int = Field(default=100, ge=1, le=1000, description="批量大小")
    
    @validator("texts")
    def validate_texts(cls, v):
        """驗證文本列表"""
        if not v:
            raise ValueError("文本列表不能為空")
        if len(v) > 1000:
            raise ValueError("單次請求最多支持1000個文本")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "texts": [
                    "這是第一段文本內容",
                    "這是第二段文本內容"
                ],
                "model": "text-embedding-ada-002",
                "batch_size": 100
            }
        }
