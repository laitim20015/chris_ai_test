"""
AI對話API端點

提供基於Azure OpenAI的聊天功能，支持RAG增強和流式響應。
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
import json
from datetime import datetime

from ...services.azure_openai_service import get_azure_openai_service, AzureOpenAIService, ChatMessage
from ...services.document_service import get_document_service, DocumentService
from ..models.request_models import ChatRequest, ChatMessage as ApiChatMessage
from ..models.response_models import ChatResponse, ChatUsage, ErrorResponse
from ..middleware.auth import is_authenticated
from loguru import logger


router = APIRouter()
chat_logger = logger.bind(module="api.chat")


def get_authenticated_azure_openai_service(request: Request) -> AzureOpenAIService:
    """依賴注入：獲取已認證的Azure OpenAI服務"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="未認證的請求")
    return get_azure_openai_service()


def get_authenticated_document_service(request: Request) -> DocumentService:
    """依賴注入：獲取已認證的文檔服務"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="未認證的請求")
    return get_document_service()


@router.post("/chat", response_model=ChatResponse, tags=["AI對話"])
async def chat_completion(
    chat_request: ChatRequest,
    azure_service: AzureOpenAIService = Depends(get_authenticated_azure_openai_service),
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    AI聊天完成
    
    提供基於Azure OpenAI的智能對話功能，支持RAG文檔上下文增強。
    
    - **messages**: 對話歷史消息列表
    - **model**: 使用的GPT模型（gpt-4, gpt-35-turbo等）
    - **temperature**: 溫度參數，控制回復的創造性
    - **use_document_context**: 是否使用文檔上下文進行RAG增強
    - **document_ids**: 相關文檔ID列表（RAG模式下）
    - **include_images**: 是否在回復中包含相關圖片信息
    """
    try:
        chat_logger.info(f"💬 收到聊天請求 - 模型: {chat_request.model}, 消息數: {len(chat_request.messages)}")
        
        # 轉換消息格式
        messages = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in chat_request.messages
        ]
        
        # RAG增強：添加文檔上下文
        if chat_request.use_document_context and chat_request.document_ids:
            enhanced_messages = await _enhance_with_document_context(
                messages, 
                chat_request.document_ids,
                chat_request.include_images,
                document_service
            )
            messages = enhanced_messages
        
        # 調用Azure OpenAI
        response = await azure_service.chat_completion(
            messages=messages,
            model=chat_request.model,
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens
        )
        
        # 構建響應
        chat_response = ChatResponse(
            id=response["id"],
            model=response["model"],
            message=response["message"],
            usage=ChatUsage(
                prompt_tokens=response["usage"].prompt_tokens,
                completion_tokens=response["usage"].completion_tokens,
                total_tokens=response["usage"].total_tokens
            ),
            context_used=chat_request.use_document_context,
            source_documents=chat_request.document_ids if chat_request.use_document_context else None,
            related_images=[] if chat_request.include_images else None,  # TODO: 實現圖片關聯
            created_at=response["created_at"],
            processing_time=response["processing_time"]
        )
        
        chat_logger.info(f"✅ 聊天請求完成 - Token使用: {response['usage'].total_tokens}")
        return chat_response
        
    except Exception as e:
        chat_logger.error(f"❌ 聊天請求失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"聊天請求處理失敗: {str(e)}"
        )


@router.post("/chat/stream", tags=["AI對話"])
async def chat_completion_stream(
    chat_request: ChatRequest,
    azure_service: AzureOpenAIService = Depends(get_authenticated_azure_openai_service),
    document_service: DocumentService = Depends(get_authenticated_document_service)
):
    """
    流式AI聊天完成
    
    提供實時流式響應的AI對話功能，適合長回復和實時交互。
    
    返回格式：Server-Sent Events (SSE)
    """
    try:
        chat_logger.info(f"🌊 收到流式聊天請求 - 模型: {chat_request.model}")
        
        # 轉換消息格式
        messages = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in chat_request.messages
        ]
        
        # RAG增強：添加文檔上下文
        if chat_request.use_document_context and chat_request.document_ids:
            enhanced_messages = await _enhance_with_document_context(
                messages, 
                chat_request.document_ids,
                chat_request.include_images,
                document_service
            )
            messages = enhanced_messages
        
        # 流式響應生成器
        async def generate_stream():
            try:
                async for chunk in azure_service.chat_completion_stream(
                    messages=messages,
                    model=chat_request.model,
                    temperature=chat_request.temperature,
                    max_tokens=chat_request.max_tokens
                ):
                    # 構建SSE格式
                    sse_data = {
                        "id": chunk["id"],
                        "content": chunk["content"],
                        "finish_reason": chunk["finish_reason"]
                    }
                    
                    yield f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"
                    
                    # 如果對話結束
                    if chunk["finish_reason"]:
                        break
                
                # 發送結束標記
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                error_data = {"error": str(e)}
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Content-Type-Options": "nosniff"
            }
        )
        
    except Exception as e:
        chat_logger.error(f"❌ 流式聊天請求失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"流式聊天請求處理失敗: {str(e)}"
        )


@router.get("/chat/health", tags=["AI對話"])
async def chat_health_check(
    azure_service: AzureOpenAIService = Depends(get_authenticated_azure_openai_service)
):
    """
    聊天服務健康檢查
    
    檢查Azure OpenAI服務的連接狀態和可用性。
    """
    try:
        health_status = await azure_service.health_check()
        
        if health_status["status"] == "healthy":
            return {
                "status": "healthy",
                "service": "Azure OpenAI Chat",
                "endpoint": health_status["endpoint"],
                "models": {
                    "chat": health_status["chat_model"],
                    "embedding": health_status["embedding_model"]
                },
                "test_response_time": health_status["test_response_time"],
                "timestamp": datetime.utcnow()
            }
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Azure OpenAI服務不健康: {health_status.get('error', '未知錯誤')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        chat_logger.error(f"❌ 健康檢查失敗: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"健康檢查失敗: {str(e)}"
        )


async def _enhance_with_document_context(
    messages: List[ChatMessage],
    document_ids: List[str],
    include_images: bool,
    document_service: DocumentService
) -> List[ChatMessage]:
    """
    使用文檔上下文增強消息（RAG功能）
    
    Args:
        messages: 原始消息列表
        document_ids: 文檔ID列表
        include_images: 是否包含圖片信息
        document_service: 文檔服務
        
    Returns:
        增強後的消息列表
    """
    try:
        # 收集相關文檔內容
        context_parts = []
        
        for doc_id in document_ids:
            # 查找對應的處理任務
            for task_id, task in document_service.tasks.items():
                if task.document_id == doc_id and task.markdown_content:
                    context_parts.append(f"## 文檔: {task.filename}\n\n{task.markdown_content}")
                    break
        
        if not context_parts:
            chat_logger.warning(f"⚠️ 未找到文檔上下文: {document_ids}")
            return messages
        
        # 創建系統提示，包含文檔上下文
        context_content = "\n\n".join(context_parts)
        system_message = ChatMessage(
            role="system",
            content=f"""你是一個智能文檔助手。以下是相關的文檔內容：

{context_content}

請基於這些文檔內容來回答用戶的問題。如果問題與文檔內容相關，請引用具體的段落或圖表。如果文檔中沒有相關信息，請明確說明。"""
        )
        
        # 將系統消息添加到消息列表開頭
        enhanced_messages = [system_message] + messages
        
        chat_logger.info(f"📚 RAG上下文增強完成 - 文檔數: {len(document_ids)}, 上下文長度: {len(context_content)}字符")
        
        return enhanced_messages
        
    except Exception as e:
        chat_logger.error(f"❌ RAG上下文增強失敗: {str(e)}")
        # 如果增強失敗，返回原始消息
        return messages
