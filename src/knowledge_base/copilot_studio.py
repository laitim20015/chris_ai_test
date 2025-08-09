"""
Microsoft Copilot Studio適配器
Microsoft Copilot Studio Adapter

實現與Microsoft Copilot Studio的集成。
Copilot Studio是微軟的對話AI和聊天機器人開發平台，支援知識庫集成和自然語言查詢。

功能特性：
- 對話式查詢界面
- 知識庫文檔管理
- 自然語言理解
- 多語言支援
- Power Platform集成
- 企業級安全和合規

配置要求：
- Microsoft 365或Azure租戶
- Copilot Studio授權
- API端點和認證憑證
- 機器人ID和環境配置
"""

from typing import List, Dict, Any, Optional
import asyncio
import json
from datetime import datetime
import aiohttp

from .base_adapter import (
    BaseKnowledgeAdapter,
    DocumentRecord,
    SearchResult,
    SearchQuery,
    IndexConfig,
    DocumentStatus,
    SearchMode,
    KnowledgeBaseError,
    DocumentNotFoundError,
    IndexingError,
    SearchError
)

class CopilotStudioAdapter(BaseKnowledgeAdapter):
    """Microsoft Copilot Studio適配器實現"""
    
    def __init__(self, config: IndexConfig,
                 tenant_id: str,
                 client_id: str,
                 client_secret: str,
                 bot_id: str,
                 environment_id: str = "default",
                 **kwargs):
        """
        初始化Copilot Studio適配器
        
        Args:
            config: 索引配置
            tenant_id: Azure AD租戶ID
            client_id: 應用程序ID
            client_secret: 應用程序密鑰
            bot_id: 機器人ID
            environment_id: Power Platform環境ID
            **kwargs: 其他配置參數
        """
        super().__init__(config, **kwargs)
        
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.bot_id = bot_id
        self.environment_id = environment_id
        
        # API端點
        self.auth_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.api_base = f"https://api.powerplatform.com/appmanagement/environments/{environment_id}"
        self.bot_endpoint = f"{self.api_base}/bots/{bot_id}"
        self.knowledge_endpoint = f"{self.bot_endpoint}/knowledgebase"
        
        # 認證
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info(f"Copilot Studio適配器初始化: Bot {bot_id}")
    
    @property
    def adapter_name(self) -> str:
        """適配器名稱"""
        return "copilot_studio"
    
    @property
    def supported_features(self) -> List[str]:
        """支援的功能列表"""
        return [
            "conversational_query",
            "natural_language_search",
            "knowledge_base_management",
            "multi_language_support",
            "power_platform_integration",
            "enterprise_security",
            "analytics_reporting",
            "bot_integration"
        ]
    
    async def _get_access_token(self) -> str:
        """獲取訪問令牌"""
        # 檢查是否需要刷新令牌
        if (self._access_token and self._token_expires_at and 
            datetime.now() < self._token_expires_at):
            return self._access_token
        
        try:
            # 請求新的訪問令牌
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://api.powerplatform.com/.default"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.auth_endpoint, data=token_data) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        self._access_token = data["access_token"]
                        expires_in = data.get("expires_in", 3600)
                        self._token_expires_at = datetime.now().timestamp() + expires_in - 300  # 提前5分鐘過期
                        
                        self.logger.debug("Copilot Studio訪問令牌獲取成功")
                        return self._access_token
                    else:
                        error_text = await response.text()
                        raise KnowledgeBaseError(f"獲取訪問令牌失敗: {response.status} - {error_text}")
                        
        except Exception as e:
            self.logger.error(f"獲取Copilot Studio訪問令牌異常: {e}")
            raise KnowledgeBaseError(f"認證失敗: {e}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取HTTP會話"""
        if self._session is None or self._session.closed:
            token = await self._get_access_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            )
        return self._session
    
    async def initialize(self) -> bool:
        """初始化適配器"""
        try:
            # 測試認證和連接
            health = await self.health_check()
            
            if health.get("status") == "healthy":
                self._initialized = True
                self.logger.info("Copilot Studio適配器初始化成功")
                return True
            else:
                self.logger.error(f"Copilot Studio服務不健康: {health}")
                return False
                
        except Exception as e:
            self.logger.error(f"Copilot Studio適配器初始化失敗: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            session = await self._get_session()
            
            # 檢查機器人狀態
            async with session.get(self.bot_endpoint) as response:
                
                if response.status == 200:
                    bot_info = await response.json()
                    return {
                        "status": "healthy",
                        "bot_id": self.bot_id,
                        "environment_id": self.environment_id,
                        "bot_status": bot_info.get("properties", {}).get("state", "unknown"),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}",
                        "timestamp": datetime.now().isoformat()
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def create_index(self, index_config: Optional[IndexConfig] = None) -> bool:
        """
        創建索引（在Copilot Studio中對應創建知識庫）
        """
        try:
            config = index_config or self.config
            
            # 創建知識庫配置
            kb_data = {
                "name": config.index_name,
                "description": config.description,
                "settings": {
                    "language": "zh-CN",
                    "enableSemanticSearch": config.enable_semantic_search,
                    "enableHybridSearch": config.enable_hybrid_search,
                    "maxContentLength": config.max_content_length
                },
                "sources": []  # 知識來源列表
            }
            
            session = await self._get_session()
            
            async with session.post(self.knowledge_endpoint, json=kb_data) as response:
                
                if response.status in [200, 201]:
                    result = await response.json()
                    self.knowledge_base_id = result.get("id")
                    self.logger.info(f"Copilot Studio知識庫創建成功: {config.index_name}")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Copilot Studio知識庫創建失敗: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"創建Copilot Studio知識庫異常: {e}")
            raise IndexingError(f"創建知識庫失敗: {e}")
    
    async def delete_index(self, index_name: str) -> bool:
        """刪除索引"""
        try:
            session = await self._get_session()
            
            # 首先查找知識庫
            async with session.get(self.knowledge_endpoint) as response:
                
                if response.status == 200:
                    knowledge_bases = await response.json()
                    kb_id = None
                    
                    for kb in knowledge_bases.get("value", []):
                        if kb.get("name") == index_name:
                            kb_id = kb.get("id")
                            break
                    
                    if not kb_id:
                        self.logger.warning(f"Copilot Studio知識庫不存在: {index_name}")
                        return True
                    
                    # 刪除知識庫
                    async with session.delete(f"{self.knowledge_endpoint}/{kb_id}") as delete_response:
                        
                        if delete_response.status in [200, 204]:
                            self.logger.info(f"Copilot Studio知識庫刪除成功: {index_name}")
                            return True
                        else:
                            error_text = await delete_response.text()
                            self.logger.error(f"Copilot Studio知識庫刪除失敗: {delete_response.status} - {error_text}")
                            return False
                else:
                    self.logger.error(f"查詢Copilot Studio知識庫失敗: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"刪除Copilot Studio知識庫異常: {e}")
            return False
    
    async def list_indexes(self) -> List[str]:
        """列出所有索引"""
        try:
            session = await self._get_session()
            
            async with session.get(self.knowledge_endpoint) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return [kb["name"] for kb in data.get("value", [])]
                else:
                    self.logger.error(f"列出Copilot Studio知識庫失敗: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"列出Copilot Studio知識庫異常: {e}")
            return []
    
    async def index_document(self, document: DocumentRecord) -> str:
        """索引單個文檔"""
        try:
            self._ensure_initialized()
            
            # 驗證文檔
            errors = await self.validate_document(document)
            if errors:
                raise IndexingError(f"文檔驗證失敗: {', '.join(errors)}")
            
            # 準備文檔數據（轉換為QnA格式）
            qna_data = {
                "questions": [document.title],
                "answer": document.content,
                "metadata": {
                    "document_id": document.document_id,
                    "source_file": document.source_file,
                    "file_format": document.file_format,
                    "status": document.status.value,
                    "associations": json.dumps(document.associations),
                    "images": json.dumps(document.images),
                    "created_at": document.created_at.isoformat()
                },
                "alternateQuestions": [
                    f"關於{document.title}",
                    f"{document.title}的內容",
                    document.source_file.split('/')[-1] if document.source_file else ""
                ]
            }
            
            session = await self._get_session()
            
            async with session.post(
                f"{self.knowledge_endpoint}/qnas",
                json=qna_data
            ) as response:
                
                if response.status in [200, 201]:
                    result = await response.json()
                    self.logger.info(f"Copilot Studio文檔索引成功: {document.document_id}")
                    return document.document_id
                else:
                    error_text = await response.text()
                    raise IndexingError(f"Copilot Studio文檔索引失敗: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Copilot Studio索引文檔異常: {e}")
            raise IndexingError(f"索引文檔失敗: {e}")
    
    async def index_documents(self, documents: List[DocumentRecord]) -> List[str]:
        """批量索引文檔"""
        try:
            # 使用並發單個操作
            tasks = [self.index_document(doc) for doc in documents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_ids = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"文檔 {documents[i].document_id} 索引失敗: {result}")
                else:
                    successful_ids.append(result)
            
            self.logger.info(f"Copilot Studio批量索引完成: {len(successful_ids)}/{len(documents)}")
            return successful_ids
            
        except Exception as e:
            self.logger.error(f"Copilot Studio批量索引異常: {e}")
            raise IndexingError(f"批量索引失敗: {e}")
    
    async def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        """獲取文檔"""
        try:
            self._ensure_initialized()
            
            session = await self._get_session()
            
            # 搜索文檔（Copilot Studio可能需要通過搜索來獲取文檔）
            search_params = {
                "query": document_id,
                "top": 1
            }
            
            async with session.post(
                f"{self.knowledge_endpoint}/query",
                json=search_params
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    answers = data.get("answers", [])
                    
                    if answers:
                        for answer in answers:
                            metadata = answer.get("metadata", {})
                            if metadata.get("document_id") == document_id:
                                return self._convert_to_document_record(answer)
                    
                    return None
                else:
                    error_text = await response.text()
                    self.logger.error(f"獲取Copilot Studio文檔失敗: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"獲取Copilot Studio文檔異常: {e}")
            return None
    
    async def update_document(self, document_id: str, document: DocumentRecord) -> bool:
        """更新文檔"""
        try:
            # 先刪除舊文檔，再添加新文檔
            await self.delete_document(document_id)
            new_id = await self.index_document(document)
            return new_id == document.document_id
            
        except Exception as e:
            self.logger.error(f"更新Copilot Studio文檔異常: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """刪除文檔"""
        try:
            self._ensure_initialized()
            
            # 首先找到文檔
            doc = await self.get_document(document_id)
            if not doc:
                self.logger.warning(f"Copilot Studio文檔不存在: {document_id}")
                return True
            
            session = await self._get_session()
            
            # 刪除QnA條目（需要QnA ID）
            async with session.delete(
                f"{self.knowledge_endpoint}/qnas/{document_id}"
            ) as response:
                
                if response.status in [200, 204]:
                    self.logger.info(f"Copilot Studio文檔刪除成功: {document_id}")
                    return True
                elif response.status == 404:
                    self.logger.warning(f"Copilot Studio文檔不存在: {document_id}")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Copilot Studio文檔刪除失敗: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"刪除Copilot Studio文檔異常: {e}")
            return False
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """搜索文檔"""
        try:
            self._ensure_initialized()
            
            # 構建查詢參數
            query_params = {
                "question": query.query_text,
                "top": query.top_k,
                "scoreThreshold": query.min_score,
                "includeUnstructuredSources": True
            }
            
            # 添加過濾條件
            if query.filters:
                query_params["filters"] = query.filters
            
            session = await self._get_session()
            
            async with session.post(
                f"{self.knowledge_endpoint}/generateAnswer",
                json=query_params
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return self._convert_search_results(data, query.mode)
                else:
                    error_text = await response.text()
                    raise SearchError(f"Copilot Studio搜索失敗: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Copilot Studio搜索異常: {e}")
            raise SearchError(f"搜索失敗: {e}")
    
    async def semantic_search(self, query_text: str, top_k: int = 10, 
                            min_score: float = 0.5) -> List[SearchResult]:
        """語義搜索"""
        query = SearchQuery(
            query_text=query_text,
            mode=SearchMode.SEMANTIC,
            top_k=top_k,
            min_score=min_score
        )
        return await self.search(query)
    
    async def association_search(self, query_text: str, 
                               include_images: bool = True,
                               top_k: int = 10) -> List[SearchResult]:
        """關聯搜索"""
        query = SearchQuery(
            query_text=query_text,
            mode=SearchMode.ASSOCIATION,
            top_k=top_k,
            include_associations=include_images
        )
        return await self.search(query)
    
    def _convert_to_document_record(self, data: Dict[str, Any]) -> DocumentRecord:
        """轉換為文檔記錄"""
        metadata = data.get("metadata", {})
        
        # 解析關聯和圖片信息
        associations = []
        images = []
        
        try:
            if metadata.get("associations"):
                associations = json.loads(metadata["associations"])
        except (json.JSONDecodeError, TypeError):
            pass
        
        try:
            if metadata.get("images"):
                images = json.loads(metadata["images"])
        except (json.JSONDecodeError, TypeError):
            pass
        
        return DocumentRecord(
            document_id=metadata.get("document_id", ""),
            title=data.get("questions", [""])[0],
            content=data.get("answer", ""),
            source_file=metadata.get("source_file", ""),
            file_format=metadata.get("file_format", ""),
            created_at=datetime.fromisoformat(
                metadata.get("created_at", datetime.now().isoformat())
            ),
            status=DocumentStatus(metadata.get("status", "indexed")),
            associations=associations,
            images=images
        )
    
    def _convert_search_results(self, data: Dict[str, Any], 
                              mode: SearchMode) -> List[SearchResult]:
        """轉換搜索結果"""
        results = []
        
        answers = data.get("answers", [])
        
        for answer in answers:
            metadata = answer.get("metadata", {})
            
            # 解析關聯信息
            associations = []
            association_scores = []
            
            try:
                if metadata.get("associations"):
                    associations = json.loads(metadata["associations"])
                    association_scores = [
                        assoc.get("final_score", 0.0) for assoc in associations
                    ]
            except (json.JSONDecodeError, TypeError):
                pass
            
            # 解析圖片信息
            images = []
            try:
                if metadata.get("images"):
                    images = json.loads(metadata["images"])
            except (json.JSONDecodeError, TypeError):
                pass
            
            result = SearchResult(
                document_id=metadata.get("document_id", ""),
                title=answer.get("questions", [""])[0] if answer.get("questions") else "",
                content=answer.get("answer", ""),
                score=answer.get("confidenceScore", 0.0),
                highlights=[],  # Copilot Studio可能不提供高亮
                metadata={
                    "source_file": metadata.get("source_file", ""),
                    "file_format": metadata.get("file_format", ""),
                    "created_at": metadata.get("created_at", "")
                },
                associated_images=images,
                association_scores=association_scores,
                search_mode=mode,
                matched_fields=["answer"]  # 假設匹配在答案中
            )
            
            results.append(result)
        
        return results
    
    async def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.knowledge_endpoint}/analytics"
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "total_documents": data.get("qnaCount", 0),
                        "bot_id": self.bot_id,
                        "environment_id": self.environment_id,
                        "last_updated": datetime.now().isoformat(),
                        "knowledge_base_size": data.get("knowledgeBaseSize", 0),
                        "query_count": data.get("queryCount", 0)
                    }
                else:
                    return {"error": f"統計查詢失敗: {response.status}"}
                    
        except Exception as e:
            self.logger.error(f"獲取Copilot Studio統計信息異常: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """關閉資源"""
        if self._session and not self._session.closed:
            await self._session.close()
