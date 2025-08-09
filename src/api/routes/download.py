"""
結果下載API端點

提供處理結果的下載功能，支持多種格式輸出。
"""

import json
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime

from ...services.document_service import get_document_service, DocumentService
from ..models.response_models import ProcessingStatus
from ..middleware.auth import is_authenticated
from loguru import logger


router = APIRouter()
download_logger = logger.bind(module="api.download")


def get_authenticated_document_service(request: Request) -> DocumentService:
    """依賴注入：獲取已認證的文檔服務"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="未認證的請求")
    return get_document_service()


@router.get("/download/{task_id}", tags=["結果下載"])
async def download_result(
    task_id: str,
    format: str = "markdown",
    include_metadata: bool = True,
    include_images: bool = False,
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    下載處理結果
    
    下載指定任務的處理結果，支持多種格式。
    
    **支持的格式：**
    - `markdown`: Markdown文檔（默認）
    - `json`: JSON格式的完整數據
    - `html`: HTML格式（轉換自Markdown）
    - `txt`: 純文本格式
    
    **參數：**
    - `include_metadata`: 是否包含文檔元數據
    - `include_images`: 是否包含圖片信息（JSON格式時）
    """
    try:
        download_logger.info(f"📥 下載請求: {task_id} - 格式: {format}")
        
        # 獲取任務信息
        task_info = document_service.get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(
                status_code=404,
                detail=f"未找到任務: {task_id}"
            )
        
        # 檢查任務狀態
        if task_info["status"] != ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"任務尚未完成，當前狀態: {task_info['status']}"
            )
        
        # 獲取處理結果
        if not task_info.get("markdown_content"):
            raise HTTPException(
                status_code=404,
                detail="處理結果不可用"
            )
        
        # 根據格式生成響應
        if format.lower() == "markdown":
            return await _download_markdown(task_info, include_metadata)
        elif format.lower() == "json":
            return await _download_json(task_info, include_metadata, include_images)
        elif format.lower() == "html":
            return await _download_html(task_info, include_metadata)
        elif format.lower() == "txt":
            return await _download_text(task_info, include_metadata)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的格式: {format}。支持的格式: markdown, json, html, txt"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        download_logger.error(f"❌ 下載失敗: {task_id} - {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"下載失敗: {str(e)}"
        )


@router.get("/download/{task_id}/metadata", tags=["結果下載"])
async def download_metadata(
    task_id: str,
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    下載任務元數據
    
    獲取處理任務的詳細元數據信息。
    """
    try:
        download_logger.debug(f"📊 元數據下載請求: {task_id}")
        
        # 獲取任務信息
        task_info = document_service.get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(
                status_code=404,
                detail=f"未找到任務: {task_id}"
            )
        
        # 構建元數據響應
        metadata = {
            "task_info": {
                "task_id": task_info["task_id"],
                "document_id": task_info["document_id"],
                "status": task_info["status"],
                "progress": task_info["progress"],
                "created_at": task_info["created_at"],
                "started_at": task_info["started_at"],
                "completed_at": task_info["completed_at"]
            },
            "document_metadata": task_info.get("metadata"),
            "processing_info": {
                "extracted_images": task_info.get("extracted_images", []),
                "image_count": len(task_info.get("extracted_images", [])),
                "has_markdown": bool(task_info.get("markdown_content")),
                "markdown_size": len(task_info.get("markdown_content", ""))
            },
            "download_info": {
                "available_formats": ["markdown", "json", "html", "txt"],
                "download_urls": {
                    "markdown": f"/api/v1/download/{task_id}?format=markdown",
                    "json": f"/api/v1/download/{task_id}?format=json",
                    "html": f"/api/v1/download/{task_id}?format=html",
                    "txt": f"/api/v1/download/{task_id}?format=txt"
                }
            }
        }
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        download_logger.error(f"❌ 元數據下載失敗: {task_id} - {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"元數據下載失敗: {str(e)}"
        )


@router.get("/download/formats", tags=["結果下載"])
async def get_download_formats():
    """
    獲取支持的下載格式
    
    返回所有可用的下載格式及其說明。
    """
    return {
        "supported_formats": {
            "markdown": {
                "name": "Markdown",
                "description": "標準Markdown格式，保留文檔結構和圖片鏈接",
                "mime_type": "text/markdown",
                "file_extension": ".md",
                "features": ["文檔結構", "圖片鏈接", "表格支持", "元數據"]
            },
            "json": {
                "name": "JSON",
                "description": "完整的結構化數據，包含所有解析信息",
                "mime_type": "application/json",
                "file_extension": ".json",
                "features": ["完整數據", "圖文關聯", "位置信息", "元數據"]
            },
            "html": {
                "name": "HTML",
                "description": "網頁格式，適合在瀏覽器中查看",
                "mime_type": "text/html",
                "file_extension": ".html",
                "features": ["網頁顯示", "樣式支持", "圖片嵌入", "導航"]
            },
            "txt": {
                "name": "純文本",
                "description": "純文本格式，僅包含文本內容",
                "mime_type": "text/plain",
                "file_extension": ".txt",
                "features": ["純文本", "無格式", "通用兼容"]
            }
        },
        "options": {
            "include_metadata": {
                "description": "是否包含文檔元數據",
                "default": True,
                "applicable_formats": ["markdown", "json", "html"]
            },
            "include_images": {
                "description": "是否包含圖片信息",
                "default": False,
                "applicable_formats": ["json"]
            }
        }
    }


async def _download_markdown(task_info: dict, include_metadata: bool) -> Response:
    """生成Markdown格式下載"""
    content = task_info["markdown_content"]
    
    if include_metadata and task_info.get("metadata"):
        metadata = task_info["metadata"]
        header = f"""---
title: {metadata.filename}
created: {metadata.created_at}
file_type: {metadata.file_type}
file_size: {metadata.file_size}
page_count: {metadata.page_count}
image_count: {metadata.image_count}
processing_time: {metadata.processing_time}s
---

"""
        content = header + content
    
    filename = f"document_{task_info['document_id']}.md"
    
    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/markdown; charset=utf-8"
        }
    )


async def _download_json(task_info: dict, include_metadata: bool, include_images: bool) -> Response:
    """生成JSON格式下載"""
    data = {
        "task_id": task_info["task_id"],
        "document_id": task_info["document_id"],
        "status": task_info["status"],
        "markdown_content": task_info["markdown_content"],
        "created_at": task_info["created_at"].isoformat() if task_info.get("created_at") else None,
        "completed_at": task_info["completed_at"].isoformat() if task_info.get("completed_at") else None
    }
    
    if include_metadata and task_info.get("metadata"):
        data["metadata"] = task_info["metadata"].__dict__ if hasattr(task_info["metadata"], "__dict__") else task_info["metadata"]
    
    if include_images:
        data["extracted_images"] = task_info.get("extracted_images", [])
    
    filename = f"document_{task_info['document_id']}.json"
    content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/json; charset=utf-8"
        }
    )


async def _download_html(task_info: dict, include_metadata: bool) -> Response:
    """生成HTML格式下載"""
    try:
        import markdown
        
        # 轉換Markdown為HTML
        md_content = task_info["markdown_content"]
        html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
        
        # 構建完整HTML
        title = f"文檔 {task_info['document_id']}"
        
        metadata_html = ""
        if include_metadata and task_info.get("metadata"):
            metadata = task_info["metadata"]
            metadata_html = f"""
            <div class="metadata">
                <h2>文檔信息</h2>
                <ul>
                    <li><strong>文件名:</strong> {metadata.filename if hasattr(metadata, 'filename') else 'N/A'}</li>
                    <li><strong>文件大小:</strong> {metadata.file_size if hasattr(metadata, 'file_size') else 'N/A'} bytes</li>
                    <li><strong>頁面數:</strong> {metadata.page_count if hasattr(metadata, 'page_count') else 'N/A'}</li>
                    <li><strong>圖片數:</strong> {metadata.image_count if hasattr(metadata, 'image_count') else 'N/A'}</li>
                    <li><strong>處理時間:</strong> {metadata.processing_time if hasattr(metadata, 'processing_time') else 'N/A'}秒</li>
                </ul>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
                .metadata {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .metadata h2 {{ margin-top: 0; }}
                .metadata ul {{ list-style-type: none; padding: 0; }}
                .metadata li {{ margin: 5px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
                pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            {metadata_html}
            {html_body}
        </body>
        </html>
        """
        
        filename = f"document_{task_info['document_id']}.html"
        
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/html; charset=utf-8"
            }
        )
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="HTML格式需要markdown庫支持"
        )


async def _download_text(task_info: dict, include_metadata: bool) -> Response:
    """生成純文本格式下載"""
    # 簡單地移除Markdown標記
    content = task_info["markdown_content"]
    
    # 基本的Markdown清理
    import re
    
    # 移除標題標記
    content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
    # 移除粗體和斜體標記
    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
    content = re.sub(r'\*(.*?)\*', r'\1', content)
    # 移除鏈接，保留文本
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
    # 移除圖片標記
    content = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', content)
    
    if include_metadata and task_info.get("metadata"):
        metadata = task_info["metadata"]
        header = f"""文檔信息:
文件名: {metadata.filename if hasattr(metadata, 'filename') else 'N/A'}
文件大小: {metadata.file_size if hasattr(metadata, 'file_size') else 'N/A'} bytes
頁面數: {metadata.page_count if hasattr(metadata, 'page_count') else 'N/A'}
圖片數: {metadata.image_count if hasattr(metadata, 'image_count') else 'N/A'}
處理時間: {metadata.processing_time if hasattr(metadata, 'processing_time') else 'N/A'}秒

{'='*50}

"""
        content = header + content
    
    filename = f"document_{task_info['document_id']}.txt"
    
    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )
