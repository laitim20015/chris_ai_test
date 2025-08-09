"""
文檔處理API端點

處理文檔轉換、圖文關聯分析等核心功能。
"""

from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Request

from ...config.settings import get_settings
from ...services.document_service import get_document_service, DocumentService
from ..models.request_models import ProcessRequest
from ..models.response_models import ProcessResponse, ProcessingStatus
from ..middleware.auth import is_authenticated
from loguru import logger


router = APIRouter()
process_logger = logger.bind(module="api.process")


def get_authenticated_document_service(request: Request) -> DocumentService:
    """依賴注入：獲取已認證的文檔服務"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="未認證的請求")
    return get_document_service()


@router.post("/process", response_model=ProcessResponse, tags=["文檔處理"])
async def process_document(
    process_request: ProcessRequest,
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    處理文檔
    
    將上傳的文檔進行解析、圖文關聯分析，並生成Markdown格式輸出。
    
    處理流程：
    1. **文檔解析** - 提取文本、圖片、表格等內容
    2. **圖片處理** - 優化圖片並生成存儲URL（可選）
    3. **圖文關聯** - 分析圖片與文本的關聯關係（可選）
    4. **Markdown生成** - 生成結構化的Markdown文檔
    5. **向量嵌入** - 生成文本向量用於RAG檢索（可選）
    
    **處理模式：**
    - `basic`: 基礎轉換，僅文本提取和Markdown生成
    - `enhanced`: 增強版，包含圖文關聯分析
    - `full`: 完整版，包含所有功能和AI分析
    
    返回任務ID，可用於查詢處理狀態和結果。
    """
    try:
        process_logger.info(
            f"⚙️ 收到處理請求 - 文檔: {process_request.document_id}, "
            f"模式: {process_request.mode}"
        )
        
        # 驗證文檔是否存在
        document_file_path = await _find_document_file(process_request.document_id)
        if not document_file_path:
            raise HTTPException(
                status_code=404,
                detail=f"未找到文檔: {process_request.document_id}"
            )
        
        # 提取文件名
        filename = document_file_path.name
        
        # 創建處理任務
        task_id = await document_service.create_processing_task(
            document_id=process_request.document_id,
            filename=filename,
            file_path=document_file_path,
            mode=process_request.mode,
            extract_images=process_request.extract_images,
            analyze_associations=process_request.analyze_associations,
            generate_embeddings=process_request.generate_embeddings,
            association_config=process_request.association_config,
            output_format=process_request.output_format,
            include_metadata=process_request.include_metadata
        )
        
        process_logger.info(f"✅ 處理任務已創建: {task_id}")
        
        # 構建初始響應
        response = ProcessResponse(
            task_id=task_id,
            document_id=process_request.document_id,
            status=ProcessingStatus.PENDING,
            progress=0.0,
            current_step="任務已創建，等待處理"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        process_logger.error(f"❌ 處理請求失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"處理請求失敗: {str(e)}"
        )


@router.get("/process/modes", tags=["文檔處理"])
async def get_processing_modes():
    """
    獲取可用的處理模式
    
    返回所有支持的文檔處理模式及其功能說明。
    """
    return {
        "processing_modes": {
            "basic": {
                "name": "基礎模式",
                "description": "僅進行文檔解析和Markdown轉換",
                "features": [
                    "文本內容提取",
                    "基礎結構解析",
                    "Markdown格式輸出"
                ],
                "estimated_time": "10-30秒",
                "resource_usage": "低"
            },
            "enhanced": {
                "name": "增強模式",
                "description": "包含圖文關聯分析的完整處理",
                "features": [
                    "文本內容提取",
                    "圖片提取和優化",
                    "圖文關聯分析",
                    "空間關係計算",
                    "增強Markdown輸出"
                ],
                "estimated_time": "30-120秒",
                "resource_usage": "中等"
            },
            "full": {
                "name": "完整模式",
                "description": "包含AI分析的全功能處理",
                "features": [
                    "所有增強模式功能",
                    "AI語義分析",
                    "向量嵌入生成",
                    "智能標籤生成",
                    "高級圖文關聯"
                ],
                "estimated_time": "60-300秒",
                "resource_usage": "高"
            }
        },
        "algorithms": {
            "spatial_analysis": {
                "name": "空間關係分析",
                "description": "基於Allen區間邏輯的13種空間關係分析",
                "accuracy": "85-95%"
            },
            "caption_detection": {
                "name": "標題檢測",
                "description": "正則表達式 + 位置分析的標題檢測",
                "weight": "40%",
                "accuracy": "90-98%"
            },
            "semantic_similarity": {
                "name": "語義相似度",
                "description": "基於sentence-transformers的語義分析",
                "weight": "15%",
                "accuracy": "75-85%"
            }
        }
    }


@router.get("/process/config", tags=["文檔處理"])
async def get_processing_config():
    """
    獲取處理配置信息
    
    返回當前的圖文關聯算法權重配置等設定。
    """
    settings = get_settings()
    
    return {
        "association_weights": {
            "caption_weight": settings.association.caption_weight,
            "spatial_weight": settings.association.spatial_weight,
            "semantic_weight": settings.association.semantic_weight,
            "layout_weight": settings.association.layout_weight,
            "proximity_weight": settings.association.proximity_weight
        },
        "image_processing": {
            "target_format": settings.image.target_format,
            "quality": settings.image.quality,
            "max_width": settings.image.max_width,
            "max_height": settings.image.max_height,
            "supported_formats": settings.image.supported_formats
        },
        "performance": {
            "max_concurrent_processing": settings.max_concurrent_processing,
            "enable_parallel_processing": settings.enable_parallel_processing,
            "enable_caching": settings.enable_caching,
            "cache_ttl_seconds": settings.cache_ttl
        },
        "limits": {
            "max_file_size_mb": settings.app.max_file_size // (1024 * 1024),
            "processing_timeout_seconds": 1800,  # 30分鐘
            "max_concurrent_tasks": 10
        }
    }


async def _find_document_file(document_id: str) -> Optional[Path]:
    """
    查找文檔文件
    
    Args:
        document_id: 文檔ID
        
    Returns:
        文件路徑，如果未找到返回None
    """
    settings = get_settings()
    upload_dir = Path(settings.storage.temp_path) / "uploads"
    
    # 查找匹配的文件
    for file_path in upload_dir.glob(f"{document_id}.*"):
        if file_path.is_file():
            return file_path
    
    return None
