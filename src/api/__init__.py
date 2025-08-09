"""
API模組 - FastAPI應用和Azure OpenAI集成

本模組提供RESTful API接口，集成文檔處理管道和Azure OpenAI服務。
包含文檔上傳、處理、AI對話和結果下載等功能。
"""

from .app import create_app
from .models.request_models import (
    DocumentUploadRequest,
    ProcessRequest,
    ChatRequest,
    EmbeddingRequest
)
from .models.response_models import (
    DocumentUploadResponse,
    ProcessResponse,
    ChatResponse,
    EmbeddingResponse,
    StatusResponse,
    ErrorResponse
)

__all__ = [
    "create_app",
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

__version__ = "1.0.0"
__description__ = "智能文檔轉換RAG系統 - API接口模組"
