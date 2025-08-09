"""
API數據模型

定義API請求和響應的Pydantic數據模型，確保類型安全和數據驗證。
"""

from .request_models import (
    DocumentUploadRequest,
    ProcessRequest,
    ChatRequest,
    EmbeddingRequest
)
from .response_models import (
    DocumentUploadResponse,
    ProcessResponse,
    ChatResponse,
    EmbeddingResponse,
    StatusResponse,
    ErrorResponse
)

__all__ = [
    "DocumentUploadRequest",
    "ProcessRequest",
    "ChatRequest", 
    "EmbeddingRequest",
    "DocumentUploadResponse",
    "ProcessResponse",
    "ChatResponse",
    "EmbeddingResponse", 
    "StatusResponse",
    "ErrorResponse"
]
