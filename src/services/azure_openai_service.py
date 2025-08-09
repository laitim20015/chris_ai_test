"""
Azure OpenAI服務

提供與Azure OpenAI的集成功能，包括Chat、Embedding等模型調用。
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime

from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletion
from openai.types import CreateEmbeddingResponse
import tiktoken
from loguru import logger

from ..config.settings import AzureOpenAISettings, get_settings


@dataclass
class TokenUsage:
    """Token使用統計"""
    prompt_tokens: int
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "user", "assistant", "system"
    content: str
    name: Optional[str] = None


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests_per_minute: int, max_tokens_per_minute: int):
        self.max_requests_per_minute = max_requests_per_minute
        self.max_tokens_per_minute = max_tokens_per_minute
        
        self.request_times: List[float] = []
        self.token_usage: List[tuple[float, int]] = []  # (timestamp, tokens)
        
        self.logger = logger.bind(module="rate_limiter")
    
    async def wait_if_needed(self, estimated_tokens: int = 0):
        """如果需要，等待以避免超過速率限制"""
        current_time = time.time()
        
        # 清理1分鐘前的記錄
        self._cleanup_old_records(current_time)
        
        # 檢查請求速率
        if len(self.request_times) >= self.max_requests_per_minute:
            wait_time = 60 - (current_time - self.request_times[0])
            if wait_time > 0:
                self.logger.warning(f"⏰ 請求速率限制，等待 {wait_time:.1f} 秒")
                await asyncio.sleep(wait_time)
                self._cleanup_old_records(time.time())
        
        # 檢查Token速率
        current_tokens = sum(tokens for _, tokens in self.token_usage)
        if current_tokens + estimated_tokens > self.max_tokens_per_minute:
            wait_time = 60 - (current_time - self.token_usage[0][0]) if self.token_usage else 0
            if wait_time > 0:
                self.logger.warning(f"🎯 Token速率限制，等待 {wait_time:.1f} 秒")
                await asyncio.sleep(wait_time)
                self._cleanup_old_records(time.time())
        
        # 記錄當前請求
        self.request_times.append(current_time)
        if estimated_tokens > 0:
            self.token_usage.append((current_time, estimated_tokens))
    
    def _cleanup_old_records(self, current_time: float):
        """清理1分鐘前的記錄"""
        cutoff_time = current_time - 60
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if t > cutoff_time]
    
    def record_usage(self, tokens_used: int):
        """記錄實際使用的Token數"""
        current_time = time.time()
        self.token_usage.append((current_time, tokens_used))


class AzureOpenAIService:
    """
    Azure OpenAI服務類
    
    提供與Azure OpenAI的完整集成功能。
    """
    
    def __init__(self, settings: Optional[AzureOpenAISettings] = None):
        """
        初始化Azure OpenAI服務
        
        Args:
            settings: Azure OpenAI配置，如果為None則使用默認配置
        """
        if settings is None:
            app_settings = get_settings()
            settings = app_settings.azure_openai
        
        self.settings = settings
        self.logger = logger.bind(module="azure_openai")
        
        # 驗證配置
        if not settings.endpoint or not settings.api_key:
            raise ValueError("Azure OpenAI endpoint和api_key必須配置")
        
        # 初始化客戶端
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.endpoint,
            api_key=settings.api_key,
            api_version=settings.api_version,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries
        )
        
        # 初始化速率限制器
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=settings.max_requests_per_minute,
            max_tokens_per_minute=settings.max_tokens_per_minute
        )
        
        # 初始化Token計數器
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4使用的編碼
        except Exception as e:
            self.logger.warning(f"無法初始化tiktoken編碼器: {e}")
            self.encoding = None
        
        self.logger.info(f"✅ Azure OpenAI服務已初始化")
        self.logger.info(f"📍 端點: {settings.endpoint}")
        self.logger.info(f"🤖 Chat模型: {settings.chat_deployment_name}")
        self.logger.info(f"🧠 Embedding模型: {settings.embedding_deployment_name}")
    
    def count_tokens(self, text: str) -> int:
        """
        計算文本的Token數量
        
        Args:
            text: 要計算的文本
            
        Returns:
            Token數量
        """
        if self.encoding is None:
            # 簡單估算：1 token ≈ 4 characters
            return len(text) // 4
        
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # 備用估算
            return len(text) // 4
    
    def estimate_chat_tokens(self, messages: List[ChatMessage], model: str = None) -> int:
        """
        估算聊天請求的Token數量
        
        Args:
            messages: 聊天消息列表
            model: 模型名稱
            
        Returns:
            估算的Token數量
        """
        # 基礎Token數（系統開銷）
        tokens = 3
        
        for message in messages:
            tokens += 3  # 每條消息的基礎開銷
            tokens += self.count_tokens(message.content)
            if message.name:
                tokens += self.count_tokens(message.name)
        
        tokens += 3  # 助手回復的基礎開銷
        
        return tokens
    
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        發送聊天完成請求
        
        Args:
            messages: 聊天消息列表
            model: 模型名稱，默認使用配置的chat_deployment_name
            temperature: 溫度參數
            max_tokens: 最大Token數
            stream: 是否流式響應
            **kwargs: 其他參數
            
        Returns:
            聊天完成響應
        """
        if model is None:
            model = self.settings.chat_deployment_name
        
        if temperature is None:
            temperature = self.settings.default_temperature
        
        if max_tokens is None:
            max_tokens = self.settings.default_max_tokens
        
        # 估算Token使用量
        estimated_tokens = self.estimate_chat_tokens(messages, model)
        estimated_tokens += max_tokens  # 加上回復Token估算
        
        # 等待速率限制
        await self.rate_limiter.wait_if_needed(estimated_tokens)
        
        # 準備消息
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        start_time = time.time()
        
        try:
            self.logger.info(f"🤖 發送Chat請求 - 模型: {model}, 消息數: {len(messages)}")
            
            # 發送請求
            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs
            )
            
            processing_time = time.time() - start_time
            
            if stream:
                # 流式響應
                return {
                    "type": "stream",
                    "response": response,
                    "processing_time": processing_time
                }
            else:
                # 標準響應
                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
                
                # 記錄實際Token使用量
                self.rate_limiter.record_usage(usage.total_tokens)
                
                self.logger.info(
                    f"✅ Chat請求完成 - "
                    f"用時: {processing_time:.2f}s, "
                    f"Token: {usage.total_tokens} "
                    f"(提示: {usage.prompt_tokens}, 完成: {usage.completion_tokens})"
                )
                
                return {
                    "type": "completion",
                    "id": response.id,
                    "model": response.model,
                    "message": response.choices[0].message.content,
                    "usage": usage,
                    "processing_time": processing_time,
                    "created_at": datetime.utcnow()
                }
        
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ Chat請求失敗: {str(e)} (用時: {processing_time:.2f}s)")
            raise
    
    async def create_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        創建文本嵌入向量
        
        Args:
            texts: 文本列表
            model: 模型名稱，默認使用配置的embedding_deployment_name
            batch_size: 批量大小
            
        Returns:
            嵌入向量響應
        """
        if model is None:
            model = self.settings.embedding_deployment_name
        
        if not texts:
            raise ValueError("文本列表不能為空")
        
        all_embeddings = []
        total_tokens = 0
        start_time = time.time()
        
        # 分批處理
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # 估算Token使用量
            estimated_tokens = sum(self.count_tokens(text) for text in batch_texts)
            
            # 等待速率限制
            await self.rate_limiter.wait_if_needed(estimated_tokens)
            
            try:
                self.logger.info(f"🧠 創建Embedding - 批次: {i//batch_size + 1}, 文本數: {len(batch_texts)}")
                
                # 發送請求
                response = await self.client.embeddings.create(
                    model=model,
                    input=batch_texts
                )
                
                # 記錄Token使用量
                batch_tokens = response.usage.total_tokens
                total_tokens += batch_tokens
                self.rate_limiter.record_usage(batch_tokens)
                
                # 收集結果
                for j, embedding_data in enumerate(response.data):
                    all_embeddings.append({
                        "text": batch_texts[j],
                        "embedding": embedding_data.embedding,
                        "index": i + j
                    })
                
                self.logger.debug(f"✅ 批次完成 - Token: {batch_tokens}")
                
            except Exception as e:
                self.logger.error(f"❌ Embedding批次失敗: {str(e)}")
                raise
        
        processing_time = time.time() - start_time
        
        self.logger.info(
            f"✅ Embedding創建完成 - "
            f"文本數: {len(texts)}, "
            f"用時: {processing_time:.2f}s, "
            f"總Token: {total_tokens}"
        )
        
        return {
            "model": model,
            "embeddings": all_embeddings,
            "total_tokens": total_tokens,
            "processing_time": processing_time,
            "created_at": datetime.utcnow()
        }
    
    async def chat_completion_stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式聊天完成
        
        Args:
            messages: 聊天消息列表
            model: 模型名稱
            temperature: 溫度參數
            max_tokens: 最大Token數
            **kwargs: 其他參數
            
        Yields:
            流式響應數據
        """
        response_data = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )
        
        if response_data["type"] != "stream":
            raise ValueError("期望流式響應但收到標準響應")
        
        async for chunk in response_data["response"]:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {
                    "id": chunk.id,
                    "content": chunk.choices[0].delta.content,
                    "finish_reason": chunk.choices[0].finish_reason
                }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查
        
        Returns:
            健康狀態信息
        """
        try:
            # 發送一個簡單的測試請求
            test_messages = [ChatMessage(role="user", content="Hello")]
            response = await self.chat_completion(
                messages=test_messages,
                max_tokens=5
            )
            
            return {
                "status": "healthy",
                "endpoint": self.settings.endpoint,
                "chat_model": self.settings.chat_deployment_name,
                "embedding_model": self.settings.embedding_deployment_name,
                "test_response_time": response["processing_time"]
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "endpoint": self.settings.endpoint
            }


# 全局服務實例（單例模式）
_azure_openai_service: Optional[AzureOpenAIService] = None


def get_azure_openai_service() -> AzureOpenAIService:
    """
    獲取Azure OpenAI服務實例（單例模式）
    
    Returns:
        Azure OpenAI服務實例
    """
    global _azure_openai_service
    
    if _azure_openai_service is None:
        _azure_openai_service = AzureOpenAIService()
    
    return _azure_openai_service
