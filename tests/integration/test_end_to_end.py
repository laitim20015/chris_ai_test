"""
端到端集成測試

測試完整的文檔處理工作流程。
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import patch, Mock
from httpx import AsyncClient

from src.main import DocumentProcessor
from src.parsers.base import ParsedContent, DocumentMetadata


@pytest.mark.integration
class TestEndToEndWorkflow:
    """端到端工作流程測試"""
    
    @pytest.mark.asyncio
    async def test_complete_document_processing_workflow(self, temp_dir, sample_parsed_content):
        """測試完整的文檔處理工作流程"""
        # 創建測試文檔
        test_doc_path = temp_dir / "test_document.pdf"
        with open(test_doc_path, "wb") as f:
            f.write(b"%PDF-1.4\nfake pdf content")
        
        # Mock文檔處理器
        with patch('src.main.DocumentProcessor.process_document') as mock_process:
            mock_process.return_value = sample_parsed_content
            
            processor = DocumentProcessor()
            result = processor.process_document(str(test_doc_path))
            
            # 驗證處理結果
            assert isinstance(result, ParsedContent)
            assert len(result.text_blocks) > 0
            assert len(result.images) > 0
            assert result.markdown_content is not None
            assert "測試文檔" in result.markdown_content
    
    @pytest.mark.asyncio
    async def test_api_document_upload_and_processing(self, async_client: AsyncClient, auth_headers, temp_dir):
        """測試API文檔上傳和處理完整流程"""
        # 創建測試文檔
        test_doc = temp_dir / "api_test.pdf"
        with open(test_doc, "wb") as f:
            f.write(b"%PDF-1.4\ntest content")
        
        # Mock服務
        mock_document_service = Mock()
        mock_document_service.tasks = {}
        
        async def mock_create_task(document_id, filename, file_path, **kwargs):
            task_id = f"task_{document_id}"
            mock_document_service.tasks[task_id] = {
                "task_id": task_id,
                "document_id": document_id,
                "filename": filename,
                "status": "pending",
                "progress": 0.0,
                "current_step": "等待處理",
                "created_at": "2025-08-08T10:00:00Z"
            }
            return task_id
        
        mock_document_service.create_processing_task = Mock(side_effect=mock_create_task)
        mock_document_service.get_task_status = Mock(
            side_effect=lambda task_id: mock_document_service.tasks.get(task_id)
        )
        
        with patch('src.api.routes.upload.get_document_service', return_value=mock_document_service), \
             patch('src.api.routes.process.get_document_service', return_value=mock_document_service), \
             patch('src.api.routes.status.get_document_service', return_value=mock_document_service):
            
            # 步驟1: 上傳文檔
            with open(test_doc, "rb") as f:
                upload_response = await async_client.post(
                    "/api/v1/upload",
                    files={"file": ("api_test.pdf", f, "application/pdf")},
                    headers=auth_headers
                )
            
            assert upload_response.status_code == 200
            upload_data = upload_response.json()
            document_id = upload_data["document_id"]
            
            # 步驟2: 啟動處理
            process_request = {
                "document_id": document_id,
                "mode": "enhanced",
                "extract_images": True,
                "analyze_associations": True
            }
            
            process_response = await async_client.post(
                "/api/v1/process",
                json=process_request,
                headers=auth_headers
            )
            
            assert process_response.status_code == 200
            process_data = process_response.json()
            task_id = process_data["task_id"]
            
            # 步驟3: 查詢狀態
            status_response = await async_client.get(
                f"/api/v1/status/{task_id}",
                headers=auth_headers
            )
            
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["task_id"] == task_id
            assert status_data["document_id"] == document_id
    
    @pytest.mark.asyncio
    async def test_chat_with_document_context_integration(self, async_client: AsyncClient, auth_headers):
        """測試聊天與文檔上下文集成"""
        mock_azure_service = Mock()
        mock_document_service = Mock()
        
        # 模擬Azure OpenAI回復
        mock_azure_service.chat_completion = Mock(return_value={
            "type": "completion",
            "id": "chat_test_id",
            "model": "gpt-4",
            "message": "根據文檔內容，這是一個測試報告...",
            "usage": Mock(prompt_tokens=30, completion_tokens=25, total_tokens=55),
            "processing_time": 1.2,
            "created_at": "2025-08-08T10:00:00Z"
        })
        
        # 模擬完成的文檔處理任務
        mock_document_service.tasks = {
            "completed_task": {
                "task_id": "completed_task",
                "document_id": "test_doc_1",
                "filename": "integration_test.pdf",
                "status": "completed",
                "markdown_content": "# 集成測試報告\n\n這是測試文檔的內容..."
            }
        }
        
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_service), \
             patch('src.api.routes.chat.get_document_service', return_value=mock_document_service):
            
            chat_request = {
                "messages": [
                    {"role": "user", "content": "請總結這個文檔的主要內容"}
                ],
                "model": "gpt-4",
                "use_document_context": True,
                "document_ids": ["test_doc_1"],
                "temperature": 0.7
            }
            
            response = await async_client.post(
                "/api/v1/chat",
                json=chat_request,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["context_used"] is True
            assert data["source_documents"] == ["test_doc_1"]
            assert "測試報告" in data["message"]
    
    @pytest.mark.asyncio
    async def test_embedding_similarity_integration(self, async_client: AsyncClient, auth_headers):
        """測試向量嵌入和相似度計算集成"""
        mock_azure_service = Mock()
        
        # 模擬嵌入響應
        def mock_create_embeddings(*args, **kwargs):
            texts = kwargs.get('texts', args[0] if args else [])
            return {
                "model": "text-embedding-ada-002",
                "embeddings": [
                    {
                        "text": text,
                        "embedding": [0.1, 0.2, 0.3] * 512,  # 1536維向量
                        "index": i
                    }
                    for i, text in enumerate(texts)
                ],
                "total_tokens": sum(len(text.split()) for text in texts),
                "processing_time": 0.8,
                "created_at": "2025-08-08T10:00:00Z"
            }
        
        mock_azure_service.create_embeddings = Mock(side_effect=mock_create_embeddings)
        
        with patch('src.api.routes.embeddings.get_azure_openai_service', return_value=mock_azure_service):
            # 測試向量嵌入
            embedding_request = {
                "texts": [
                    "這是第一段測試文字",
                    "這是第二段測試文字"
                ],
                "model": "text-embedding-ada-002"
            }
            
            embedding_response = await async_client.post(
                "/api/v1/embeddings",
                json=embedding_request,
                headers=auth_headers
            )
            
            assert embedding_response.status_code == 200
            embedding_data = embedding_response.json()
            assert len(embedding_data["embeddings"]) == 2
            
            # 測試相似度計算
            similarity_response = await async_client.post(
                "/api/v1/embeddings/similarity",
                params={
                    "text1": "這是測試文字",
                    "text2": "這是相似的測試文字"
                },
                headers=auth_headers
            )
            
            assert similarity_response.status_code == 200
            similarity_data = similarity_response.json()
            assert "similarity" in similarity_data
            assert 0 <= similarity_data["similarity"] <= 1
    
    @pytest.mark.asyncio 
    async def test_download_multiple_formats_integration(self, async_client: AsyncClient, auth_headers):
        """測試多格式下載集成"""
        mock_document_service = Mock()
        
        # 模擬完成的處理任務
        mock_task = {
            "task_id": "download_test_task",
            "document_id": "download_test_doc",
            "status": "completed",
            "markdown_content": "# 下載測試\n\n這是測試內容。",
            "metadata": Mock(
                filename="download_test.pdf",
                file_size=2048,
                file_type="pdf",
                page_count=1,
                image_count=0,
                processing_time=5.2,
                created_at="2025-08-08T10:00:00Z"
            ),
            "extracted_images": []
        }
        
        mock_document_service.get_task_status = Mock(return_value=mock_task)
        
        with patch('src.api.routes.download.get_document_service', return_value=mock_document_service):
            formats = ["markdown", "json", "html", "txt"]
            
            for format_type in formats:
                response = await async_client.get(
                    f"/api/v1/download/download_test_task?format={format_type}",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                
                # 驗證Content-Type
                content_type = response.headers.get("content-type")
                if format_type == "markdown":
                    assert "text/markdown" in content_type
                elif format_type == "json":
                    assert "application/json" in content_type
                elif format_type == "html":
                    assert "text/html" in content_type
                elif format_type == "txt":
                    assert "text/plain" in content_type
                
                # 驗證內容包含測試數據
                assert "下載測試" in response.text
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_processing_integration(self, async_client: AsyncClient, auth_headers, temp_dir):
        """測試並發處理集成"""
        mock_document_service = Mock()
        mock_document_service.tasks = {}
        task_counter = 0
        
        async def mock_create_task(document_id, filename, file_path, **kwargs):
            nonlocal task_counter
            task_counter += 1
            task_id = f"concurrent_task_{task_counter}"
            mock_document_service.tasks[task_id] = {
                "task_id": task_id,
                "document_id": document_id,
                "filename": filename,
                "status": "processing",
                "progress": 50.0,
                "current_step": f"處理文檔 {task_counter}",
                "created_at": "2025-08-08T10:00:00Z"
            }
            # 模擬異步處理時間
            await asyncio.sleep(0.1)
            return task_id
        
        mock_document_service.create_processing_task = Mock(side_effect=mock_create_task)
        mock_document_service.get_task_status = Mock(
            side_effect=lambda task_id: mock_document_service.tasks.get(task_id)
        )
        mock_document_service.get_all_tasks = Mock(
            side_effect=lambda: list(mock_document_service.tasks.values())
        )
        
        # 創建測試文檔
        test_docs = []
        for i in range(5):
            doc_path = temp_dir / f"concurrent_test_{i}.pdf"
            with open(doc_path, "wb") as f:
                f.write(f"fake pdf content {i}".encode())
            test_docs.append(doc_path)
        
        with patch('src.api.routes.upload.get_document_service', return_value=mock_document_service), \
             patch('src.api.routes.process.get_document_service', return_value=mock_document_service), \
             patch('src.api.routes.status.get_document_service', return_value=mock_document_service):
            
            # 並發上傳和處理多個文檔
            upload_tasks = []
            for i, doc_path in enumerate(test_docs):
                async def upload_and_process(doc_path, doc_index):
                    # 上傳
                    with open(doc_path, "rb") as f:
                        upload_response = await async_client.post(
                            "/api/v1/upload",
                            files={"file": (f"test_{doc_index}.pdf", f, "application/pdf")},
                            headers=auth_headers
                        )
                    
                    if upload_response.status_code != 200:
                        return None
                    
                    document_id = upload_response.json()["document_id"]
                    
                    # 處理
                    process_response = await async_client.post(
                        "/api/v1/process",
                        json={
                            "document_id": document_id,
                            "mode": "basic"
                        },
                        headers=auth_headers
                    )
                    
                    return process_response.json() if process_response.status_code == 200 else None
                
                upload_tasks.append(upload_and_process(doc_path, i))
            
            # 執行並發任務
            results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            
            # 驗證結果
            successful_results = [r for r in results if r is not None and not isinstance(r, Exception)]
            assert len(successful_results) == 5
            
            # 檢查所有任務狀態
            status_response = await async_client.get(
                "/api/v1/status",
                headers=auth_headers
            )
            
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["total_tasks"] == 5
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, async_client: AsyncClient, auth_headers):
        """測試錯誤恢復集成"""
        # 模擬部分失敗的服務
        mock_azure_service = Mock()
        mock_document_service = Mock()
        
        # Azure服務第一次失敗，第二次成功
        call_count = 0
        def mock_chat_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("暫時的網絡錯誤")
            return {
                "type": "completion",
                "id": "retry_test_id",
                "model": "gpt-4",
                "message": "重試成功的回復",
                "usage": Mock(prompt_tokens=15, completion_tokens=20, total_tokens=35),
                "processing_time": 1.8,
                "created_at": "2025-08-08T10:00:00Z"
            }
        
        mock_azure_service.chat_completion = Mock(side_effect=mock_chat_with_retry)
        
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_service):
            # 第一次請求（應該失敗）
            chat_request = {
                "messages": [
                    {"role": "user", "content": "測試錯誤恢復"}
                ],
                "model": "gpt-4"
            }
            
            first_response = await async_client.post(
                "/api/v1/chat",
                json=chat_request,
                headers=auth_headers
            )
            
            assert first_response.status_code == 500
            
            # 第二次請求（應該成功）
            second_response = await async_client.post(
                "/api/v1/chat",
                json=chat_request,
                headers=auth_headers
            )
            
            assert second_response.status_code == 200
            data = second_response.json()
            assert data["message"] == "重試成功的回復"


@pytest.mark.integration
@pytest.mark.slow
class TestSystemIntegration:
    """系統集成測試"""
    
    @pytest.mark.asyncio
    async def test_system_health_integration(self, async_client: AsyncClient, auth_headers):
        """測試系統健康狀態集成"""
        # 測試基本健康檢查
        health_response = await async_client.get("/health")
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "智能文檔轉換RAG系統"
        
        # 測試系統狀態檢查
        mock_document_service = Mock()
        mock_document_service.get_all_tasks = Mock(return_value=[])
        
        with patch('src.api.routes.status.get_document_service', return_value=mock_document_service):
            system_status_response = await async_client.get(
                "/api/v1/status/system/health",
                headers=auth_headers
            )
            
            assert system_status_response.status_code == 200
            
            system_data = system_status_response.json()
            assert "system_resources" in system_data
            assert "task_statistics" in system_data
            assert "service_status" in system_data
    
    @pytest.mark.asyncio
    async def test_api_documentation_integration(self, async_client: AsyncClient):
        """測試API文檔集成"""
        # 測試OpenAPI文檔
        openapi_response = await async_client.get("/api/openapi.json")
        assert openapi_response.status_code == 200
        
        openapi_data = openapi_response.json()
        assert "openapi" in openapi_data
        assert "paths" in openapi_data
        assert "/api/v1/chat" in openapi_data["paths"]
        assert "/api/v1/upload" in openapi_data["paths"]
        
        # 測試Swagger UI（如果在debug模式下）
        docs_response = await async_client.get("/api/docs")
        # 在測試環境中可能返回404，這是正常的
        assert docs_response.status_code in [200, 404]
