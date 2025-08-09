"""
Chat API端點單元測試

測試Azure OpenAI聊天功能的API端點。
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from httpx import AsyncClient

from src.api.models.request_models import ChatRequest, ChatMessage
from src.api.models.response_models import ChatResponse


@pytest.mark.unit
@pytest.mark.api
class TestChatEndpoints:
    """Chat API端點測試類"""
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, async_client: AsyncClient, auth_headers, mock_azure_openai_service):
        """測試成功的聊天完成請求"""
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_openai_service):
            request_data = {
                "messages": [
                    {"role": "user", "content": "你好，請介紹一下這個系統"}
                ],
                "model": "gpt-4",
                "temperature": 0.7
            }
            
            response = await async_client.post(
                "/api/v1/chat",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert "id" in data
            assert "model" in data
            assert "message" in data
            assert "usage" in data
            assert data["model"] == "gpt-4"
            assert data["message"] == "這是測試回復"
            
            # 驗證usage統計
            usage = data["usage"]
            assert "prompt_tokens" in usage
            assert "completion_tokens" in usage
            assert "total_tokens" in usage
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_rag_context(self, async_client: AsyncClient, auth_headers, mock_azure_openai_service, mock_document_service):
        """測試帶RAG上下文的聊天完成"""
        # 準備測試任務
        mock_document_service.tasks = {
            "test_task_1": {
                "task_id": "test_task_1",
                "document_id": "doc_1",
                "filename": "test.pdf",
                "status": "completed",
                "markdown_content": "# 測試文檔\n\n這是測試內容。"
            }
        }
        
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_openai_service), \
             patch('src.api.routes.chat.get_document_service', return_value=mock_document_service):
            
            request_data = {
                "messages": [
                    {"role": "user", "content": "請總結文檔內容"}
                ],
                "model": "gpt-4",
                "use_document_context": True,
                "document_ids": ["doc_1"],
                "include_images": True
            }
            
            response = await async_client.post(
                "/api/v1/chat",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["context_used"] is True
            assert data["source_documents"] == ["doc_1"]
            assert "related_images" in data
    
    @pytest.mark.asyncio
    async def test_chat_completion_invalid_request(self, async_client: AsyncClient, auth_headers):
        """測試無效請求"""
        # 空消息列表
        request_data = {
            "messages": [],
            "model": "gpt-4"
        }
        
        response = await async_client.post(
            "/api/v1/chat",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_chat_completion_unauthorized(self, async_client: AsyncClient):
        """測試未認證請求"""
        request_data = {
            "messages": [
                {"role": "user", "content": "測試"}
            ],
            "model": "gpt-4"
        }
        
        response = await async_client.post(
            "/api/v1/chat",
            json=request_data
            # 不提供認證頭部
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream(self, async_client: AsyncClient, auth_headers, mock_azure_openai_service):
        """測試流式聊天完成"""
        # Mock流式響應
        async def mock_stream_response(*args, **kwargs):
            yield {"id": "test", "content": "這是", "finish_reason": None}
            yield {"id": "test", "content": "測試", "finish_reason": None}
            yield {"id": "test", "content": "回復", "finish_reason": "stop"}
        
        mock_azure_openai_service.chat_completion_stream = AsyncMock(return_value=mock_stream_response())
        
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_openai_service):
            request_data = {
                "messages": [
                    {"role": "user", "content": "請簡短回復"}
                ],
                "model": "gpt-4"
            }
            
            response = await async_client.post(
                "/api/v1/chat/stream",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            
            # 驗證SSE格式
            content = response.text
            assert "data: " in content
            assert "[DONE]" in content
    
    @pytest.mark.asyncio
    async def test_chat_health_check(self, async_client: AsyncClient, auth_headers, mock_azure_openai_service):
        """測試聊天服務健康檢查"""
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_openai_service):
            response = await async_client.get(
                "/api/v1/chat/health",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "Azure OpenAI Chat"
            assert "models" in data
            assert "test_response_time" in data
    
    @pytest.mark.asyncio
    async def test_chat_health_check_unhealthy(self, async_client: AsyncClient, auth_headers):
        """測試不健康的聊天服務"""
        mock_unhealthy_service = Mock()
        mock_unhealthy_service.health_check = AsyncMock(return_value={
            "status": "unhealthy",
            "error": "連接失敗"
        })
        
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_unhealthy_service):
            response = await async_client.get(
                "/api/v1/chat/health",
                headers=auth_headers
            )
            
            assert response.status_code == 503
    
    @pytest.mark.parametrize("model,temperature,max_tokens", [
        ("gpt-4", 0.7, 1000),
        ("gpt-35-turbo", 0.5, 500),
        ("gpt-4-1106-preview", 1.0, 2000),
    ])
    @pytest.mark.asyncio
    async def test_chat_completion_different_models(self, async_client: AsyncClient, auth_headers, mock_azure_openai_service, model, temperature, max_tokens):
        """測試不同模型和參數"""
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_openai_service):
            request_data = {
                "messages": [
                    {"role": "user", "content": "測試不同模型"}
                ],
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = await async_client.post(
                "/api/v1/chat",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            # 驗證模型調用參數
            mock_azure_openai_service.chat_completion.assert_called_once()
            call_kwargs = mock_azure_openai_service.chat_completion.call_args.kwargs
            assert call_kwargs.get('model') == model
            assert call_kwargs.get('temperature') == temperature
            assert call_kwargs.get('max_tokens') == max_tokens
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_system_message(self, async_client: AsyncClient, auth_headers, mock_azure_openai_service):
        """測試帶系統消息的聊天"""
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_openai_service):
            request_data = {
                "messages": [
                    {"role": "system", "content": "你是一個專業的文檔分析助手"},
                    {"role": "user", "content": "請幫我分析這個文檔"}
                ],
                "model": "gpt-4"
            }
            
            response = await async_client.post(
                "/api/v1/chat",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            # 驗證系統消息被正確傳遞
            mock_azure_openai_service.chat_completion.assert_called_once()
            call_args = mock_azure_openai_service.chat_completion.call_args.args
            messages = call_args[0]
            assert len(messages) == 2
            assert messages[0].role == "system"
            assert messages[1].role == "user"
    
    @pytest.mark.asyncio
    async def test_chat_error_handling(self, async_client: AsyncClient, auth_headers):
        """測試聊天錯誤處理"""
        mock_failing_service = Mock()
        mock_failing_service.chat_completion = AsyncMock(side_effect=Exception("Azure OpenAI服務錯誤"))
        
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_failing_service):
            request_data = {
                "messages": [
                    {"role": "user", "content": "測試錯誤處理"}
                ],
                "model": "gpt-4"
            }
            
            response = await async_client.post(
                "/api/v1/chat",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 500
            
            data = response.json()
            assert "error" in data
            assert "聊天請求處理失敗" in data["message"]
    
    @pytest.mark.asyncio
    async def test_chat_request_validation(self, async_client: AsyncClient, auth_headers):
        """測試請求數據驗證"""
        # 測試無效的role
        invalid_request = {
            "messages": [
                {"role": "invalid_role", "content": "測試"}
            ],
            "model": "gpt-4"
        }
        
        response = await async_client.post(
            "/api/v1/chat",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        
        # 測試無效的temperature
        invalid_temp_request = {
            "messages": [
                {"role": "user", "content": "測試"}
            ],
            "model": "gpt-4",
            "temperature": 3.0  # 超出範圍
        }
        
        response = await async_client.post(
            "/api/v1/chat",
            json=invalid_temp_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.api  
class TestChatRAGIntegration:
    """Chat RAG集成測試"""
    
    @pytest.mark.asyncio
    async def test_rag_context_enhancement(self, async_client: AsyncClient, auth_headers):
        """測試RAG上下文增強功能"""
        mock_azure_service = Mock()
        mock_document_service = Mock()
        
        # 模擬成功的聊天回復
        mock_azure_service.chat_completion = AsyncMock(return_value={
            "type": "completion",
            "id": "test_id",
            "model": "gpt-4", 
            "message": "基於文檔內容的回復",
            "usage": Mock(prompt_tokens=50, completion_tokens=20, total_tokens=70),
            "processing_time": 1.5,
            "created_at": "2025-08-08T10:00:00Z"
        })
        
        # 模擬文檔服務
        mock_document_service.tasks = {
            "task_1": {
                "task_id": "task_1",
                "document_id": "doc_1",
                "filename": "research.pdf",
                "status": "completed",
                "markdown_content": "# 研究報告\n\n這是重要的研究發現..."
            }
        }
        
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_service), \
             patch('src.api.routes.chat.get_document_service', return_value=mock_document_service):
            
            request_data = {
                "messages": [
                    {"role": "user", "content": "根據文檔內容，主要發現是什麼？"}
                ],
                "model": "gpt-4",
                "use_document_context": True,
                "document_ids": ["doc_1"]
            }
            
            response = await async_client.post(
                "/api/v1/chat",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["context_used"] is True
            assert data["source_documents"] == ["doc_1"]
            
            # 驗證Azure OpenAI被調用時包含了文檔上下文
            mock_azure_service.chat_completion.assert_called_once()
            call_args = mock_azure_service.chat_completion.call_args.args
            messages = call_args[0]
            
            # 應該有系統消息包含文檔上下文
            system_messages = [m for m in messages if m.role == "system"]
            assert len(system_messages) > 0
            assert "研究報告" in system_messages[0].content
    
    @pytest.mark.asyncio
    async def test_rag_with_nonexistent_document(self, async_client: AsyncClient, auth_headers):
        """測試RAG使用不存在的文檔"""
        mock_azure_service = Mock()
        mock_document_service = Mock()
        
        mock_azure_service.chat_completion = AsyncMock(return_value={
            "type": "completion",
            "id": "test_id",
            "model": "gpt-4",
            "message": "沒有文檔上下文的回復",
            "usage": Mock(prompt_tokens=10, completion_tokens=15, total_tokens=25),
            "processing_time": 1.0,
            "created_at": "2025-08-08T10:00:00Z"
        })
        
        # 空的任務字典
        mock_document_service.tasks = {}
        
        with patch('src.api.routes.chat.get_azure_openai_service', return_value=mock_azure_service), \
             patch('src.api.routes.chat.get_document_service', return_value=mock_document_service):
            
            request_data = {
                "messages": [
                    {"role": "user", "content": "基於文檔回答問題"}
                ],
                "model": "gpt-4",
                "use_document_context": True,
                "document_ids": ["nonexistent_doc"]
            }
            
            response = await async_client.post(
                "/api/v1/chat",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            # 雖然請求了RAG，但由於文檔不存在，應該仍能正常回復
            data = response.json()
            assert data["context_used"] is True  # 嘗試使用了上下文
            assert data["source_documents"] == ["nonexistent_doc"]
