"""
FastAPI應用主文件

創建和配置FastAPI應用實例，設置路由、中間件和異常處理。
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import uvicorn
from loguru import logger

from ..config.settings import AppSettings
from ..config.logging_config import setup_logging, get_logger
from .routes import upload, process, chat, embeddings, status, download
from .middleware.auth import AuthMiddleware
from .middleware.error_handler import ErrorHandlerMiddleware
from .models.response_models import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時
    logger.info("🚀 智能文檔轉換RAG系統 API 啟動中...")
    logger.info("📋 正在初始化Azure OpenAI連接...")
    yield
    # 關閉時
    logger.info("🛑 智能文檔轉換RAG系統 API 關閉中...")


def create_app(settings: AppSettings = None) -> FastAPI:
    """
    創建並配置FastAPI應用
    
    Args:
        settings: 應用配置，如果為None則使用默認配置
        
    Returns:
        配置好的FastAPI應用實例
    """
    if settings is None:
        settings = AppSettings()
    
    # 設置日誌
    setup_logging()
    app_logger = get_logger("api.app")
    
    # 創建FastAPI應用
    app = FastAPI(
        title="智能文檔轉換RAG系統 API",
        description="將Word、PDF、PowerPoint文檔轉換為Markdown，並建立圖文關聯關係的RAG知識庫系統",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json"
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # 添加自定義中間件
    app.add_middleware(ErrorHandlerMiddleware)
    if settings.auth_enabled:
        app.add_middleware(AuthMiddleware, api_keys=settings.api_keys)
    
    # 註冊路由
    app.include_router(upload.router, prefix="/api/v1", tags=["文檔上傳"])
    app.include_router(process.router, prefix="/api/v1", tags=["文檔處理"])
    app.include_router(chat.router, prefix="/api/v1", tags=["AI對話"])
    app.include_router(embeddings.router, prefix="/api/v1", tags=["向量嵌入"])
    app.include_router(status.router, prefix="/api/v1", tags=["狀態查詢"])
    app.include_router(download.router, prefix="/api/v1", tags=["結果下載"])
    
    # 健康檢查端點
    @app.get("/health", response_model=dict, tags=["系統"])
    async def health_check():
        """健康檢查端點"""
        return {
            "status": "healthy", 
            "service": "智能文檔轉換RAG系統",
            "version": "1.0.0"
        }
    
    # 根路徑
    @app.get("/", tags=["系統"])
    async def root():
        """API根路徑"""
        return {
            "message": "智能文檔轉換RAG系統 API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "health": "/health"
        }
    
    # 自定義異常處理器
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP異常處理器"""
        app_logger.warning(f"HTTP異常: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP_ERROR",
                message=exc.detail,
                status_code=exc.status_code
            ).model_dump()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用異常處理器"""
        app_logger.error(f"未處理的異常: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="INTERNAL_SERVER_ERROR",
                message="內部服務器錯誤",
                status_code=500
            ).model_dump()
        )
    
    app_logger.info("✅ FastAPI應用配置完成")
    return app


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    運行開發服務器
    
    Args:
        host: 綁定的主機地址
        port: 綁定的端口
        reload: 是否啟用自動重載
    """
    uvicorn.run(
        "src.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_config=None  # 使用我們自定義的日誌配置
    )


if __name__ == "__main__":
    # 開發模式運行
    run_server(reload=True)
