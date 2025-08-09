"""
狀態查詢API端點

提供任務狀態查詢和系統監控功能。
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request

from ...services.document_service import get_document_service, DocumentService
from ..models.response_models import StatusResponse, ProcessingStatus
from ..middleware.auth import is_authenticated
from loguru import logger


router = APIRouter()
status_logger = logger.bind(module="api.status")


def get_authenticated_document_service(request: Request) -> DocumentService:
    """依賴注入：獲取已認證的文檔服務"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="未認證的請求")
    return get_document_service()


@router.get("/status/{task_id}", response_model=StatusResponse, tags=["狀態查詢"])
async def get_task_status(
    task_id: str,
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    查詢任務處理狀態
    
    根據任務ID查詢文檔處理的當前狀態和進度。
    
    **狀態說明：**
    - `pending`: 等待處理
    - `processing`: 正在處理
    - `completed`: 處理完成
    - `failed`: 處理失敗
    - `cancelled`: 已取消
    
    **進度信息：**
    - 進度百分比（0-100）
    - 當前處理步驟
    - 預計剩餘時間
    - 結果下載URL（完成時）
    """
    try:
        status_logger.debug(f"📊 查詢任務狀態: {task_id}")
        
        # 獲取任務狀態
        task_info = document_service.get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(
                status_code=404,
                detail=f"未找到任務: {task_id}"
            )
        
        # 構建響應
        response = StatusResponse(
            task_id=task_info["task_id"],
            status=task_info["status"],
            progress=task_info["progress"],
            current_step=task_info["current_step"],
            created_at=task_info["created_at"],
            started_at=task_info["started_at"],
            completed_at=task_info["completed_at"]
        )
        
        # 添加結果URL（如果已完成）
        if task_info["status"] == ProcessingStatus.COMPLETED:
            response.result_url = f"/api/v1/download/{task_id}"
        
        # 添加錯誤信息（如果失敗）
        if task_info["status"] == ProcessingStatus.FAILED:
            response.error_message = task_info.get("error_message")
        
        # 計算預計剩餘時間（簡單估算）
        if task_info["status"] == ProcessingStatus.PROCESSING:
            response.estimated_time = _estimate_remaining_time(
                task_info["progress"], 
                task_info["started_at"]
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        status_logger.error(f"❌ 狀態查詢失敗: {task_id} - {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"狀態查詢失敗: {str(e)}"
        )


@router.get("/status", tags=["狀態查詢"])
async def get_all_tasks_status(
    status_filter: ProcessingStatus = None,
    limit: int = 50,
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    查詢所有任務狀態
    
    獲取系統中所有處理任務的狀態列表。
    
    **參數：**
    - `status_filter`: 按狀態過濾（可選）
    - `limit`: 返回結果數量限制（默認50）
    """
    try:
        status_logger.debug(f"📋 查詢所有任務狀態 - 過濾: {status_filter}, 限制: {limit}")
        
        # 獲取所有任務
        all_tasks = document_service.get_all_tasks()
        
        # 應用過濾器
        if status_filter:
            all_tasks = [
                task for task in all_tasks 
                if task and task.get("status") == status_filter
            ]
        
        # 按創建時間排序（最新的在前）
        all_tasks.sort(
            key=lambda x: x.get("created_at", ""), 
            reverse=True
        )
        
        # 應用限制
        limited_tasks = all_tasks[:limit]
        
        # 統計信息
        status_counts = {}
        for task in all_tasks:
            if task:
                status = task.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_tasks": len(all_tasks),
            "returned_tasks": len(limited_tasks),
            "status_counts": status_counts,
            "tasks": limited_tasks,
            "filters_applied": {
                "status_filter": status_filter,
                "limit": limit
            }
        }
        
    except Exception as e:
        status_logger.error(f"❌ 批量狀態查詢失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"批量狀態查詢失敗: {str(e)}"
        )


@router.get("/status/system/health", tags=["狀態查詢"])
async def system_health_check(
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    系統健康檢查
    
    檢查各個系統組件的健康狀態和運行統計。
    """
    try:
        from datetime import datetime
        import psutil
        import os
        
        # 獲取系統資源使用情況
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 獲取任務統計
        all_tasks = document_service.get_all_tasks()
        task_stats = {}
        for task in all_tasks:
            if task:
                status = task.get("status", "unknown")
                task_stats[status] = task_stats.get(status, 0) + 1
        
        # 檢查處理中的任務
        processing_tasks = [
            task for task in all_tasks 
            if task and task.get("status") == ProcessingStatus.PROCESSING
        ]
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "system_resources": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent_used": round((disk.used / disk.total) * 100, 1)
                },
                "process_id": os.getpid()
            },
            "task_statistics": {
                "total_tasks": len(all_tasks),
                "processing_tasks": len(processing_tasks),
                "status_breakdown": task_stats
            },
            "service_status": {
                "document_service": "healthy",
                "azure_openai": "unknown",  # 需要實際檢查
                "file_storage": "healthy" if os.path.exists("./data") else "warning"
            }
        }
        
        # 判斷整體健康狀態
        if cpu_percent > 90:
            health_status["status"] = "warning"
            health_status["warnings"] = health_status.get("warnings", [])
            health_status["warnings"].append("CPU使用率過高")
        
        if memory.percent > 90:
            health_status["status"] = "warning"  
            health_status["warnings"] = health_status.get("warnings", [])
            health_status["warnings"].append("內存使用率過高")
        
        if len(processing_tasks) > 10:
            health_status["status"] = "warning"
            health_status["warnings"] = health_status.get("warnings", [])
            health_status["warnings"].append("處理任務積壓過多")
        
        return health_status
        
    except Exception as e:
        status_logger.error(f"❌ 系統健康檢查失敗: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow(),
            "error": str(e),
            "service_status": {
                "document_service": "error",
                "azure_openai": "unknown",
                "file_storage": "unknown"
            }
        }


@router.delete("/status/{task_id}", tags=["狀態查詢"])
async def cancel_task(
    task_id: str,
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    取消處理任務
    
    取消指定的文檔處理任務（僅對等待中或處理中的任務有效）。
    """
    try:
        status_logger.info(f"🚫 請求取消任務: {task_id}")
        
        # 獲取任務信息
        task_info = document_service.get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(
                status_code=404,
                detail=f"未找到任務: {task_id}"
            )
        
        # 檢查任務狀態
        current_status = task_info["status"]
        if current_status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
            raise HTTPException(
                status_code=400,
                detail=f"任務已結束，無法取消。當前狀態: {current_status}"
            )
        
        # 執行取消操作（這裡需要實際的取消邏輯）
        # TODO: 實現實際的任務取消功能
        if task_id in document_service.tasks:
            task = document_service.tasks[task_id]
            task.status = ProcessingStatus.CANCELLED
            task.current_step = "任務已取消"
            task.completed_at = datetime.utcnow()
        
        status_logger.info(f"✅ 任務取消成功: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "任務已成功取消",
            "cancelled_at": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        status_logger.error(f"❌ 任務取消失敗: {task_id} - {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"任務取消失敗: {str(e)}"
        )


def _estimate_remaining_time(progress: float, started_at) -> float:
    """
    估算剩餘處理時間
    
    Args:
        progress: 當前進度（0-100）
        started_at: 開始時間
        
    Returns:
        預計剩餘時間（秒）
    """
    if progress <= 0:
        return 0.0
    
    try:
        from datetime import datetime
        
        current_time = datetime.utcnow()
        elapsed_time = (current_time - started_at).total_seconds()
        
        if progress >= 100:
            return 0.0
        
        # 簡單的線性估算
        estimated_total_time = elapsed_time * (100 / progress)
        remaining_time = estimated_total_time - elapsed_time
        
        return max(0.0, remaining_time)
        
    except Exception:
        return 0.0
