"""
智能文件轉換與RAG知識庫系統 - 主應用入口
Main Application Entry Point

基於FastAPI的現代Web應用，提供：
- RESTful API接口
- 文件上傳和處理
- 實時處理狀態
- 健康檢查和監控
- 完整的錯誤處理
"""

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
from typing import Dict, Any

from src.config.settings import get_settings
from src.config.logging_config import get_logger, setup_logging
from src import get_project_info, validate_association_weights

# 初始化日誌
setup_logging()
logger = get_logger("main")

# 獲取配置
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    
    # 啟動時的初始化
    logger.info("🚀 智能文件轉換與RAG知識庫系統啟動中...")
    
    try:
        # 驗證配置
        logger.info("⚙️  驗證系統配置...")
        
        # 驗證關聯度權重配置
        from src.config.settings import get_association_weights
        weights = get_association_weights()
        if not validate_association_weights(weights):
            raise RuntimeError("關聯度權重配置不符合項目規則")
        
        # 創建必要目錄
        settings.create_directories()
        logger.info("📁 目錄結構創建完成")
        
        # 初始化各個模組（如果需要）
        logger.info("🔧 初始化核心模組...")
        
        # 這裡可以添加其他初始化邏輯，如：
        # - 數據庫連接
        # - 緩存系統
        # - AI模型加載
        # - 外部服務連接
        
        logger.info("✅ 系統初始化完成")
        
        yield  # 應用運行期間
        
    except Exception as e:
        logger.error(f"❌ 系統初始化失敗: {e}")
        raise
    
    finally:
        # 關閉時的清理工作
        logger.info("🔄 正在關閉系統...")
        
        # 這裡可以添加清理邏輯，如：
        # - 關閉數據庫連接
        # - 清理臨時文件
        # - 保存狀態
        
        logger.info("👋 系統已安全關閉")

# 創建FastAPI應用
app = FastAPI(
    title=settings.app.name,
    description=settings.app.description,
    version=settings.app.version,
    docs_url="/docs" if settings.app.debug else None,
    redoc_url="/redoc" if settings.app.debug else None,
    openapi_url="/openapi.json" if settings.app.debug else None,
    lifespan=lifespan
)

# 添加中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 全局異常處理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP異常處理器"""
    logger.error(f"HTTP異常: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP錯誤",
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用異常處理器"""
    logger.error(f"未處理的異常: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "內部服務器錯誤",
            "detail": "系統發生未預期的錯誤，請稍後重試",
            "type": type(exc).__name__
        }
    )

# 基本路由
@app.get("/")
async def root() -> Dict[str, Any]:
    """根路由 - 返回API基本信息"""
    project_info = get_project_info()
    return {
        "message": "歡迎使用智能文件轉換與RAG知識庫系統",
        "status": "running",
        "project": project_info,
        "api_docs": "/docs" if settings.app.debug else "disabled",
        "environment": settings.app.environment
    }

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """健康檢查端點"""
    try:
        # 檢查各個子系統狀態
        health_status = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "version": settings.app.version,
            "environment": settings.app.environment,
            "components": {
                "api": "healthy",
                "config": "healthy",
                "logging": "healthy",
                "storage": "healthy"
            }
        }
        
        # 檢查配置是否有效
        try:
            weights = get_association_weights()
            if validate_association_weights(weights):
                health_status["components"]["association_config"] = "healthy"
            else:
                health_status["components"]["association_config"] = "error"
                health_status["status"] = "degraded"
        except Exception:
            health_status["components"]["association_config"] = "error"
            health_status["status"] = "degraded"
        
        # 檢查存儲目錄
        try:
            settings.storage.local_path.exists()
            health_status["components"]["storage"] = "healthy"
        except Exception:
            health_status["components"]["storage"] = "error"
            health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e)
            },
            status_code=503
        )

@app.get("/info")
async def system_info() -> Dict[str, Any]:
    """系統信息端點"""
    from src.config import get_config_summary
    
    try:
        config_summary = get_config_summary()
        project_info = get_project_info()
        
        return {
            "project": project_info,
            "config": config_summary,
            "features": {
                "supported_formats": ["pdf", "docx", "pptx"],
                "output_format": "markdown",
                "association_analysis": True,
                "spatial_analysis": True,
                "caption_detection": True,
                "semantic_analysis": True
            },
            "algorithms": {
                "allen_logic": "13種空間關係",
                "caption_detection": "正則表達式 + 位置分析",
                "association_scoring": "5項加權融合模型",
                "pdf_parsing": "PyMuPDF + pymupdf4llm + unstructured"
            }
        }
        
    except Exception as e:
        logger.error(f"獲取系統信息失敗: {e}")
        raise HTTPException(status_code=500, detail="無法獲取系統信息")

@app.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """監控指標端點"""
    try:
        import psutil
        import time
        
        # 系統資源指標
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": time.time(),
            "system": {
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory.percent,
                "memory_available_mb": memory.available // 1024 // 1024,
                "disk_usage_percent": disk.percent,
                "disk_free_gb": disk.free // 1024 // 1024 // 1024
            },
            "application": {
                "status": "running",
                "version": settings.app.version,
                "environment": settings.app.environment,
                "debug_mode": settings.app.debug
            }
        }
        
    except ImportError:
        # 如果psutil不可用，返回基本信息
        return {
            "timestamp": asyncio.get_event_loop().time(),
            "application": {
                "status": "running",
                "version": settings.app.version,
                "environment": settings.app.environment
            },
            "note": "詳細系統指標需要安裝psutil"
        }
    except Exception as e:
        logger.error(f"獲取監控指標失敗: {e}")
        raise HTTPException(status_code=500, detail="無法獲取監控指標")

# 註冊API路由（當其他模組完成後會添加）
# TODO: 當API模組完成後，在這裡註冊路由
# from src.api.routes import upload, process, download
# app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
# app.include_router(process.router, prefix="/api/v1", tags=["process"])
# app.include_router(download.router, prefix="/api/v1", tags=["download"])

def main():
    """主函數 - 啟動應用"""
    logger.info(f"🌟 啟動 {settings.app.name} v{settings.app.version}")
    logger.info(f"📍 環境: {settings.app.environment}")
    logger.info(f"🔧 調試模式: {settings.app.debug}")
    logger.info(f"🌐 監聽: {settings.api.host}:{settings.api.port}")
    
    # 啟動服務器
    uvicorn.run(
        "src.main:app",
        host=settings.api.host,
        port=settings.api.port,
        workers=settings.api.workers if not settings.app.debug else 1,
        reload=settings.api.reload and settings.app.debug,
        log_level=settings.logging.level.lower(),
        access_log=settings.app.debug,
        loop="asyncio"
    )

if __name__ == "__main__":
    main()
