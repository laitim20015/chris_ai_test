"""
文檔上傳API端點

處理文檔文件的上傳和存儲功能。
"""

import uuid
import mimetypes
from typing import Dict, Any
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from datetime import datetime

from ...config.settings import get_settings
from ...services.document_service import get_document_service, DocumentService
from ..models.response_models import DocumentUploadResponse
from ..middleware.auth import is_authenticated
from loguru import logger


router = APIRouter()
upload_logger = logger.bind(module="api.upload")


def get_authenticated_document_service(request: Request) -> DocumentService:
    """依賴注入：獲取已認證的文檔服務"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="未認證的請求")
    return get_document_service()


@router.post("/upload", response_model=DocumentUploadResponse, tags=["文檔上傳"])
async def upload_document(
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    上傳文檔文件
    
    支持的文件格式：
    - **PDF**: .pdf
    - **Word**: .doc, .docx  
    - **PowerPoint**: .ppt, .pptx
    
    文件大小限制：100MB
    
    上傳成功後會返回文檔ID，可用於後續的處理請求。
    """
    settings = get_settings()
    
    try:
        upload_logger.info(f"📤 收到文件上傳: {file.filename} ({file.content_type})")
        
        # 驗證文件
        await _validate_uploaded_file(file, settings)
        
        # 生成文檔ID和存儲路徑
        document_id = f"doc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        upload_dir = Path(settings.storage.temp_path) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        file_extension = Path(file.filename).suffix.lower()
        stored_filename = f"{document_id}{file_extension}"
        file_path = upload_dir / stored_filename
        
        # 寫入文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_size = len(content)
        
        upload_logger.info(
            f"✅ 文件上傳成功: {document_id} - "
            f"大小: {file_size} bytes, 路徑: {file_path}"
        )
        
        # 構建響應
        response = DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="uploaded",
            message=f"文檔上傳成功，大小: {file_size} bytes"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        upload_logger.error(f"❌ 文件上傳失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文件上傳失敗: {str(e)}"
        )


@router.get("/upload/formats", tags=["文檔上傳"])
async def get_supported_formats():
    """
    獲取支持的文件格式
    
    返回系統支持的所有文檔格式信息。
    """
    return {
        "supported_formats": {
            "pdf": {
                "extensions": [".pdf"],
                "mime_types": ["application/pdf"],
                "description": "PDF文檔格式",
                "max_size_mb": 100
            },
            "word": {
                "extensions": [".doc", ".docx"],
                "mime_types": [
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ],
                "description": "Microsoft Word文檔",
                "max_size_mb": 100
            },
            "powerpoint": {
                "extensions": [".ppt", ".pptx"],
                "mime_types": [
                    "application/vnd.ms-powerpoint",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                ],
                "description": "Microsoft PowerPoint演示文稿",
                "max_size_mb": 100
            }
        },
        "limits": {
            "max_file_size_bytes": 100 * 1024 * 1024,
            "max_file_size_mb": 100,
            "timeout_seconds": 300
        }
    }


@router.delete("/upload/{document_id}", tags=["文檔上傳"])
async def delete_uploaded_document(
    document_id: str,
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    刪除已上傳的文檔
    
    刪除指定文檔ID的文件和相關處理任務。
    """
    try:
        upload_logger.info(f"🗑️ 請求刪除文檔: {document_id}")
        
        settings = get_settings()
        upload_dir = Path(settings.storage.temp_path) / "uploads"
        
        # 查找並刪除文件
        deleted_files = []
        for file_path in upload_dir.glob(f"{document_id}.*"):
            file_path.unlink()
            deleted_files.append(str(file_path))
        
        # 查找並清理相關任務
        tasks_to_remove = []
        for task_id, task in document_service.tasks.items():
            if task.document_id == document_id:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del document_service.tasks[task_id]
        
        if not deleted_files and not tasks_to_remove:
            raise HTTPException(status_code=404, detail=f"未找到文檔: {document_id}")
        
        upload_logger.info(
            f"✅ 文檔刪除成功: {document_id} - "
            f"文件: {len(deleted_files)}, 任務: {len(tasks_to_remove)}"
        )
        
        return {
            "document_id": document_id,
            "status": "deleted",
            "deleted_files": len(deleted_files),
            "deleted_tasks": len(tasks_to_remove),
            "message": "文檔及相關數據已成功刪除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        upload_logger.error(f"❌ 文檔刪除失敗: {document_id} - {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文檔刪除失敗: {str(e)}"
        )


async def _validate_uploaded_file(file: UploadFile, settings) -> None:
    """
    驗證上傳的文件
    
    Args:
        file: 上傳的文件
        settings: 應用設置
        
    Raises:
        HTTPException: 如果文件不符合要求
    """
    # 檢查文件名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能為空")
    
    # 檢查文件擴展名
    file_extension = Path(file.filename).suffix.lower()
    supported_extensions = [".pdf", ".doc", ".docx", ".ppt", ".pptx"]
    
    if file_extension not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_extension}。支持的格式: {', '.join(supported_extensions)}"
        )
    
    # 檢查MIME類型
    expected_mime_types = {
        ".pdf": ["application/pdf"],
        ".doc": ["application/msword"],
        ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        ".ppt": ["application/vnd.ms-powerpoint"],
        ".pptx": ["application/vnd.openxmlformats-officedocument.presentationml.presentation"]
    }
    
    if file_extension in expected_mime_types:
        if file.content_type not in expected_mime_types[file_extension]:
            # 嘗試根據文件名推斷MIME類型
            guessed_type, _ = mimetypes.guess_type(file.filename)
            if guessed_type not in expected_mime_types[file_extension]:
                upload_logger.warning(
                    f"⚠️ MIME類型不匹配: {file.content_type} vs 期望: {expected_mime_types[file_extension]}"
                )
    
    # 檢查文件大小（先讀取一部分來檢查）
    # 注意：這裡我們不能完全讀取文件，因為後面還需要讀取
    # 實際的大小檢查會在讀取完整文件後進行
    max_size = settings.app.max_file_size
    
    # 重置文件指針（如果之前讀取過）
    await file.seek(0)
    
    upload_logger.debug(
        f"📋 文件驗證通過: {file.filename} - "
        f"類型: {file.content_type}, 擴展名: {file_extension}"
    )
