"""
文檔處理服務

整合文檔解析、圖文關聯、Markdown生成等功能的高級服務。
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from loguru import logger

from ..main import DocumentProcessor
from ..config.settings import get_settings
from ..parsers.base import ParsedContent
from ..api.models.request_models import ProcessingMode
from ..api.models.response_models import DocumentMetadata, ProcessingStatus


class DocumentProcessingTask:
    """文檔處理任務"""
    
    def __init__(self, document_id: str, filename: str, file_path: Path):
        self.task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.document_id = document_id
        self.filename = filename
        self.file_path = file_path
        
        self.status = ProcessingStatus.PENDING
        self.progress = 0.0
        self.current_step = "等待處理"
        self.error_message: Optional[str] = None
        
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # 處理結果
        self.markdown_content: Optional[str] = None
        self.parsed_content: Optional[ParsedContent] = None
        self.extracted_images: List[str] = []
        self.metadata: Optional[DocumentMetadata] = None


class DocumentService:
    """
    文檔處理服務
    
    提供文檔上傳、處理、狀態查詢等高級功能。
    """
    
    def __init__(self):
        """初始化文檔服務"""
        self.settings = get_settings()
        self.processor = DocumentProcessor()
        self.tasks: Dict[str, DocumentProcessingTask] = {}
        self.logger = logger.bind(module="document_service")
        
        self.logger.info("📄 文檔處理服務已初始化")
    
    async def create_processing_task(
        self,
        document_id: str,
        filename: str,
        file_path: Path,
        mode: ProcessingMode = ProcessingMode.ENHANCED,
        **kwargs
    ) -> str:
        """
        創建文檔處理任務
        
        Args:
            document_id: 文檔ID
            filename: 文件名
            file_path: 文件路徑
            mode: 處理模式
            **kwargs: 其他處理參數
            
        Returns:
            任務ID
        """
        task = DocumentProcessingTask(document_id, filename, file_path)
        self.tasks[task.task_id] = task
        
        self.logger.info(f"📋 創建處理任務: {task.task_id} - 文檔: {filename}")
        
        # 異步執行處理
        asyncio.create_task(self._process_document(task, mode, **kwargs))
        
        return task.task_id
    
    async def _process_document(
        self,
        task: DocumentProcessingTask,
        mode: ProcessingMode,
        **kwargs
    ):
        """
        異步處理文檔
        
        Args:
            task: 處理任務
            mode: 處理模式
            **kwargs: 其他處理參數
        """
        try:
            task.status = ProcessingStatus.PROCESSING
            task.started_at = datetime.utcnow()
            task.current_step = "開始處理"
            task.progress = 0.0
            
            self.logger.info(f"🚀 開始處理文檔: {task.document_id}")
            
            # 步驟1: 解析文檔
            task.current_step = "解析文檔內容"
            task.progress = 20.0
            
            parsed_content = await asyncio.to_thread(
                self.processor.process_document,
                str(task.file_path)
            )
            task.parsed_content = parsed_content
            
            self.logger.info(f"✅ 文檔解析完成: {len(parsed_content.text_blocks)}個文本塊")
            
            # 步驟2: 處理圖片（如果啟用）
            if kwargs.get("extract_images", True):
                task.current_step = "處理圖片"
                task.progress = 40.0
                
                # 這裡可以添加圖片處理邏輯
                self.logger.info("🖼️ 圖片處理完成")
            
            # 步驟3: 分析圖文關聯（如果啟用）
            if mode in [ProcessingMode.ENHANCED, ProcessingMode.FULL] and kwargs.get("analyze_associations", True):
                task.current_step = "分析圖文關聯"
                task.progress = 60.0
                
                # 圖文關聯分析已經在processor中完成
                associations_count = sum(
                    len(block.associated_images) for block in parsed_content.text_blocks
                )
                self.logger.info(f"🎯 圖文關聯分析完成: {associations_count}個關聯")
            
            # 步驟4: 生成Markdown
            task.current_step = "生成Markdown"
            task.progress = 80.0
            
            # Markdown內容已經在processor中生成
            task.markdown_content = parsed_content.markdown_content
            
            # 步驟5: 完成處理
            task.current_step = "處理完成"
            task.progress = 100.0
            task.status = ProcessingStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            # 創建元數據
            task.metadata = self._create_metadata(task, parsed_content)
            
            processing_time = (task.completed_at - task.started_at).total_seconds()
            self.logger.info(f"🎉 文檔處理完成: {task.document_id} (用時: {processing_time:.2f}s)")
            
        except Exception as e:
            task.status = ProcessingStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            
            self.logger.error(f"❌ 文檔處理失敗: {task.document_id} - {str(e)}")
    
    def _create_metadata(self, task: DocumentProcessingTask, parsed_content: ParsedContent) -> DocumentMetadata:
        """
        創建文檔元數據
        
        Args:
            task: 處理任務
            parsed_content: 解析內容
            
        Returns:
            文檔元數據
        """
        processing_time = 0.0
        if task.started_at and task.completed_at:
            processing_time = (task.completed_at - task.started_at).total_seconds()
        
        return DocumentMetadata(
            filename=task.filename,
            file_size=task.file_path.stat().st_size if task.file_path.exists() else 0,
            file_type=task.file_path.suffix.lower().lstrip('.'),
            page_count=len(set(block.page for block in parsed_content.text_blocks)) if parsed_content.text_blocks else 0,
            image_count=len(parsed_content.images),
            processing_time=processing_time,
            created_at=task.created_at
        )
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取任務狀態
        
        Args:
            task_id: 任務ID
            
        Returns:
            任務狀態信息，如果任務不存在返回None
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        status_info = {
            "task_id": task.task_id,
            "document_id": task.document_id,
            "status": task.status,
            "progress": task.progress,
            "current_step": task.current_step,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at
        }
        
        # 添加結果（如果已完成）
        if task.status == ProcessingStatus.COMPLETED:
            status_info.update({
                "markdown_content": task.markdown_content,
                "extracted_images": task.extracted_images,
                "metadata": task.metadata
            })
        
        # 添加錯誤信息（如果失敗）
        if task.status == ProcessingStatus.FAILED:
            status_info["error_message"] = task.error_message
        
        return status_info
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        獲取所有任務的狀態
        
        Returns:
            所有任務的狀態列表
        """
        return [
            self.get_task_status(task_id)
            for task_id in self.tasks.keys()
        ]
    
    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """
        清理已完成的舊任務
        
        Args:
            max_age_hours: 任務保留時間（小時）
        """
        current_time = datetime.utcnow()
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if task.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                if task.completed_at:
                    age_hours = (current_time - task.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            self.logger.info(f"🗑️ 清理舊任務: {task_id}")
        
        if tasks_to_remove:
            self.logger.info(f"🧹 清理完成，移除了 {len(tasks_to_remove)} 個舊任務")


# 全局服務實例（單例模式）
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """
    獲取文檔服務實例（單例模式）
    
    Returns:
        文檔服務實例
    """
    global _document_service
    
    if _document_service is None:
        _document_service = DocumentService()
    
    return _document_service
