"""
API響應數據模型

定義API端點的響應數據結構，包含處理結果、狀態信息、錯誤信息等。
"""

from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class ProcessingStatus(str, Enum):
    """處理狀態"""
    PENDING = "pending"        # 等待中
    PROCESSING = "processing"  # 處理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"         # 失敗
    CANCELLED = "cancelled"   # 已取消


class ImageAssociation(BaseModel):
    """圖片關聯信息"""
    image_id: str = Field(..., description="圖片ID")
    image_url: str = Field(..., description="圖片URL")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="關聯度分數")
    association_type: str = Field(..., description="關聯類型")
    spatial_relation: Optional[str] = Field(None, description="空間關係")
    
    class Config:
        json_schema_extra = {
            "example": {
                "image_id": "img_001",
                "image_url": "https://storage.example.com/images/report_p003_img001.jpg",
                "relevance_score": 0.95,
                "association_type": "direct_reference",
                "spatial_relation": "below"
            }
        }


class TextBlock(BaseModel):
    """文本塊信息"""
    id: str = Field(..., description="文本塊ID")
    content: str = Field(..., description="文本內容")
    page: int = Field(..., description="頁碼")
    position: Dict[str, float] = Field(..., description="位置信息")
    associated_images: List[ImageAssociation] = Field(default=[], description="關聯圖片")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "text_001",
                "content": "圖表1顯示了銷售趨勢的變化...",
                "page": 1,
                "position": {"x1": 100, "y1": 200, "x2": 500, "y2": 250},
                "associated_images": []
            }
        }


class DocumentMetadata(BaseModel):
    """文檔元數據"""
    filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小")
    file_type: str = Field(..., description="文件類型")
    page_count: int = Field(..., description="頁面數量")
    image_count: int = Field(..., description="圖片數量")
    processing_time: float = Field(..., description="處理時間（秒）")
    created_at: datetime = Field(..., description="創建時間")
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "report.pdf",
                "file_size": 1024000,
                "file_type": "pdf",
                "page_count": 10,
                "image_count": 5,
                "processing_time": 15.5,
                "created_at": "2025-08-08T10:30:00Z"
            }
        }


class DocumentUploadResponse(BaseModel):
    """文檔上傳響應"""
    document_id: str = Field(..., description="文檔ID")
    filename: str = Field(..., description="文件名")
    upload_url: Optional[str] = Field(None, description="上傳URL（如果使用預簽名URL）")
    status: str = Field(default="uploaded", description="上傳狀態")
    message: str = Field(default="文檔上傳成功", description="響應消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_20250808_001",
                "filename": "report.pdf",
                "upload_url": None,
                "status": "uploaded",
                "message": "文檔上傳成功"
            }
        }


class ProcessResponse(BaseModel):
    """文檔處理響應"""
    task_id: str = Field(..., description="任務ID")
    document_id: str = Field(..., description="文檔ID")
    status: ProcessingStatus = Field(..., description="處理狀態")
    
    # 處理結果（完成時）
    markdown_content: Optional[str] = Field(None, description="Markdown內容")
    text_blocks: Optional[List[TextBlock]] = Field(None, description="文本塊列表")
    extracted_images: Optional[List[str]] = Field(None, description="提取的圖片URL列表")
    metadata: Optional[DocumentMetadata] = Field(None, description="文檔元數據")
    
    # 進度信息
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="處理進度百分比")
    current_step: Optional[str] = Field(None, description="當前處理步驟")
    estimated_time: Optional[float] = Field(None, description="預計剩餘時間（秒）")
    
    # 錯誤信息（失敗時）
    error_message: Optional[str] = Field(None, description="錯誤消息")
    error_details: Optional[Dict[str, Any]] = Field(None, description="錯誤詳情")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_20250808_001",
                "document_id": "doc_20250808_001",
                "status": "completed",
                "markdown_content": "# 報告標題\n\n這是報告內容...",
                "progress": 100.0,
                "current_step": "完成",
                "metadata": {
                    "filename": "report.pdf",
                    "file_size": 1024000,
                    "file_type": "pdf",
                    "page_count": 10,
                    "image_count": 5,
                    "processing_time": 15.5,
                    "created_at": "2025-08-08T10:30:00Z"
                }
            }
        }


class ChatUsage(BaseModel):
    """Token使用統計"""
    prompt_tokens: int = Field(..., description="提示詞Token數")
    completion_tokens: int = Field(..., description="回復Token數")
    total_tokens: int = Field(..., description="總Token數")


class ChatResponse(BaseModel):
    """AI對話響應"""
    id: str = Field(..., description="響應ID")
    model: str = Field(..., description="使用的模型")
    message: str = Field(..., description="AI回復內容")
    
    # 使用統計
    usage: ChatUsage = Field(..., description="Token使用統計")
    
    # RAG相關信息
    context_used: bool = Field(default=False, description="是否使用了文檔上下文")
    source_documents: Optional[List[str]] = Field(None, description="引用的源文檔")
    related_images: Optional[List[str]] = Field(None, description="相關圖片URL")
    
    # 元數據
    created_at: datetime = Field(..., description="創建時間")
    processing_time: float = Field(..., description="處理時間（秒）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "chat_20250808_001",
                "model": "gpt-4",
                "message": "根據您提供的文檔，主要內容包括...",
                "usage": {
                    "prompt_tokens": 150,
                    "completion_tokens": 200,
                    "total_tokens": 350
                },
                "context_used": True,
                "source_documents": ["doc_20250808_001"],
                "related_images": ["https://storage.example.com/images/chart1.jpg"],
                "created_at": "2025-08-08T10:35:00Z",
                "processing_time": 2.5
            }
        }


class EmbeddingVector(BaseModel):
    """嵌入向量"""
    text: str = Field(..., description="原始文本")
    embedding: List[float] = Field(..., description="向量數據")
    index: int = Field(..., description="在批量中的索引")


class EmbeddingResponse(BaseModel):
    """向量嵌入響應"""
    model: str = Field(..., description="使用的模型")
    embeddings: List[EmbeddingVector] = Field(..., description="嵌入向量列表")
    
    # 使用統計
    total_tokens: int = Field(..., description="總Token數")
    
    # 元數據
    created_at: datetime = Field(..., description="創建時間")
    processing_time: float = Field(..., description="處理時間（秒）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "text-embedding-ada-002",
                "embeddings": [
                    {
                        "text": "這是第一段文本",
                        "embedding": [0.1, 0.2, 0.3],  # 實際會有1536維
                        "index": 0
                    }
                ],
                "total_tokens": 50,
                "created_at": "2025-08-08T10:40:00Z",
                "processing_time": 1.2
            }
        }


class StatusResponse(BaseModel):
    """狀態查詢響應"""
    task_id: str = Field(..., description="任務ID")
    status: ProcessingStatus = Field(..., description="處理狀態")
    progress: float = Field(..., ge=0.0, le=100.0, description="進度百分比")
    current_step: Optional[str] = Field(None, description="當前步驟")
    estimated_time: Optional[float] = Field(None, description="預計剩餘時間（秒）")
    
    # 結果URL（完成時）
    result_url: Optional[str] = Field(None, description="結果下載URL")
    
    # 錯誤信息（失敗時）
    error_message: Optional[str] = Field(None, description="錯誤消息")
    
    # 時間信息
    created_at: datetime = Field(..., description="任務創建時間")
    started_at: Optional[datetime] = Field(None, description="開始處理時間")
    completed_at: Optional[datetime] = Field(None, description="完成時間")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_20250808_001",
                "status": "processing",
                "progress": 65.0,
                "current_step": "分析圖文關聯",
                "estimated_time": 8.5,
                "created_at": "2025-08-08T10:30:00Z",
                "started_at": "2025-08-08T10:30:15Z"
            }
        }


class ErrorResponse(BaseModel):
    """錯誤響應"""
    error: str = Field(..., description="錯誤類型")
    message: str = Field(..., description="錯誤消息")
    status_code: int = Field(..., description="HTTP狀態碼")
    details: Optional[Dict[str, Any]] = Field(None, description="錯誤詳情")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="錯誤時間")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "請求參數驗證失敗",
                "status_code": 400,
                "details": {"field": "document_id", "issue": "不能為空"},
                "timestamp": "2025-08-08T10:45:00Z"
            }
        }
