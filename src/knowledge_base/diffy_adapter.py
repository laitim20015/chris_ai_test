"""
Diffy適配器
Diffy Adapter

實現與Diffy知識庫平台的集成。
Diffy是一個開源的知識管理和文檔協作平台，支援Markdown文檔管理和搜索。

功能特性：
- Markdown原生支援
- 全文搜索
- 文檔版本管理
- 協作編輯
- API訪問
- 自託管選項

配置要求：
- Diffy服務器URL
- API金鑰或認證憑證
- 工作空間/項目標識
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

class DiffyAdapter(BaseKnowledgeAdapter):
    """Diffy知識庫適配器實現"""
    
    def __init__(self, config: IndexConfig,
                 server_url: str,
                 api_key: str,
                 workspace_id: str,
                 **kwargs):
        """
        初始化Diffy適配器
        
        Args:
            config: 索引配置
            server_url: Diffy服務器URL
            api_key: API金鑰
            workspace_id: 工作空間ID
            **kwargs: 其他配置參數
        """
        super().__init__(config, **kwargs)
        
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.workspace_id = workspace_id
        
        # API端點
        self.api_base = f"{self.server_url}/api/v1"
        self.docs_endpoint = f"{self.api_base}/workspaces/{workspace_id}/documents"
        self.search_endpoint = f"{self.api_base}/workspaces/{workspace_id}/search"
        
        # HTTP會話
        self._session: Optional[aiohttp.ClientSession] = None
        
        # 請求標頭
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "RAG-System-Diffy-Adapter/1.0"
        }
        
        self.logger.info(f"Diffy適配器初始化: {server_url}")
    
    @property
    def adapter_name(self) -> str:
        """適配器名稱"""
        return "diffy"
    
    @property  
    def supported_features(self) -> List[str]:
        """支援的功能列表"""
        return [
            "markdown_native",
            "full_text_search",
            "document_versioning", 
            "collaborative_editing",
            "folder_organization",
            "tag_management",
            "comment_system",
            "real_time_sync"
        ]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取HTTP會話"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
    
    async def initialize(self) -> bool:
        """初始化適配器"""
        try:
            # 測試連接和認證
            health = await self.health_check()
            
            if health.get("status") == "healthy":
                self._initialized = True
                self.logger.info("Diffy適配器初始化成功")
                return True
            else:
                self.logger.error(f"Diffy服務不健康: {health}")
                return False
                
        except Exception as e:
            self.logger.error(f"Diffy適配器初始化失敗: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            session = await self._get_session()
            
            # 檢查服務狀態
            async with session.get(f"{self.api_base}/health") as response:
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "server_url": self.server_url,
                        "workspace_id": self.workspace_id,
                        "server_info": data,
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
        創建索引（在Diffy中對應創建文檔集合或文件夾）
        """
        try:
            config = index_config or self.config
            
            # 在Diffy中創建文檔集合
            collection_data = {
                "name": config.index_name,
                "description": config.description,
                "type": "collection",
                "settings": {
                    "enable_full_text_search": True,
                    "enable_version_control": True,
                    "max_file_size": config.max_content_length
                }
            }
            
            session = await self._get_session()
            
            async with session.post(
                f"{self.api_base}/workspaces/{self.workspace_id}/collections",
                json=collection_data
            ) as response:
                
                if response.status in [200, 201]:
                    result = await response.json()
                    self.collection_id = result.get("id")
                    self.logger.info(f"Diffy集合創建成功: {config.index_name}")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Diffy集合創建失敗: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"創建Diffy集合異常: {e}")
            raise IndexingError(f"創建集合失敗: {e}")
    
    async def delete_index(self, index_name: str) -> bool:
        """刪除索引"""
        try:
            # 在Diffy中刪除對應的集合
            session = await self._get_session()
            
            # 首先查找集合ID
            async with session.get(
                f"{self.api_base}/workspaces/{self.workspace_id}/collections"
            ) as response:
                
                if response.status == 200:
                    collections = await response.json()
                    collection_id = None
                    
                    for collection in collections.get("data", []):
                        if collection.get("name") == index_name:
                            collection_id = collection.get("id")
                            break
                    
                    if not collection_id:
                        self.logger.warning(f"Diffy集合不存在: {index_name}")
                        return True
                    
                    # 刪除集合
                    async with session.delete(
                        f"{self.api_base}/workspaces/{self.workspace_id}/collections/{collection_id}"
                    ) as delete_response:
                        
                        if delete_response.status in [200, 204]:
                            self.logger.info(f"Diffy集合刪除成功: {index_name}")
                            return True
                        else:
                            error_text = await delete_response.text()
                            self.logger.error(f"Diffy集合刪除失敗: {delete_response.status} - {error_text}")
                            return False
                else:
                    self.logger.error(f"查詢Diffy集合失敗: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"刪除Diffy集合異常: {e}")
            return False
    
    async def list_indexes(self) -> List[str]:
        """列出所有索引"""
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.api_base}/workspaces/{self.workspace_id}/collections"
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return [
                        collection["name"] 
                        for collection in data.get("data", [])
                    ]
                else:
                    self.logger.error(f"列出Diffy集合失敗: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"列出Diffy集合異常: {e}")
            return []
    
    async def index_document(self, document: DocumentRecord) -> str:
        """索引單個文檔"""
        try:
            self._ensure_initialized()
            
            # 驗證文檔
            errors = await self.validate_document(document)
            if errors:
                raise IndexingError(f"文檔驗證失敗: {', '.join(errors)}")
            
            # 準備文檔數據
            doc_data = {
                "id": document.document_id,
                "title": document.title,
                "content": document.content,
                "format": "markdown",
                "metadata": {
                    "source_file": document.source_file,
                    "file_format": document.file_format,
                    "file_size": document.file_size,
                    "status": document.status.value,
                    "associations": document.associations,
                    "images": document.images,
                    "custom_fields": document.custom_fields
                },
                "tags": [document.file_format.lstrip('.'), "auto-imported"],
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat()
            }
            
            session = await self._get_session()
            
            async with session.post(
                self.docs_endpoint,
                json=doc_data
            ) as response:
                
                if response.status in [200, 201]:
                    result = await response.json()
                    self.logger.info(f"Diffy文檔索引成功: {document.document_id}")
                    return document.document_id
                else:
                    error_text = await response.text()
                    raise IndexingError(f"Diffy文檔索引失敗: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Diffy索引文檔異常: {e}")
            raise IndexingError(f"索引文檔失敗: {e}")
    
    async def index_documents(self, documents: List[DocumentRecord]) -> List[str]:
        """批量索引文檔"""
        try:
            # Diffy可能不支援批量操作，使用並發單個操作
            tasks = [self.index_document(doc) for doc in documents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_ids = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"文檔 {documents[i].document_id} 索引失敗: {result}")
                else:
                    successful_ids.append(result)
            
            self.logger.info(f"Diffy批量索引完成: {len(successful_ids)}/{len(documents)}")
            return successful_ids
            
        except Exception as e:
            self.logger.error(f"Diffy批量索引異常: {e}")
            raise IndexingError(f"批量索引失敗: {e}")
    
    async def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        """獲取文檔"""
        try:
            self._ensure_initialized()
            
            session = await self._get_session()
            
            async with session.get(f"{self.docs_endpoint}/{document_id}") as response:
                
                if response.status == 200:
                    data = await response.json()
                    return self._convert_to_document_record(data)
                elif response.status == 404:
                    return None
                else:
                    error_text = await response.text()
                    self.logger.error(f"獲取Diffy文檔失敗: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"獲取Diffy文檔異常: {e}")
            return None
    
    async def update_document(self, document_id: str, document: DocumentRecord) -> bool:
        """更新文檔"""
        try:
            self._ensure_initialized()
            
            # 準備更新數據
            update_data = {
                "title": document.title,
                "content": document.content,
                "metadata": {
                    "source_file": document.source_file,
                    "file_format": document.file_format,
                    "associations": document.associations,
                    "images": document.images,
                    "custom_fields": document.custom_fields
                },
                "updated_at": datetime.now().isoformat()
            }
            
            session = await self._get_session()
            
            async with session.put(
                f"{self.docs_endpoint}/{document_id}",
                json=update_data
            ) as response:
                
                if response.status == 200:
                    self.logger.info(f"Diffy文檔更新成功: {document_id}")
                    return True
                elif response.status == 404:
                    raise DocumentNotFoundError(f"文檔不存在: {document_id}")
                else:
                    error_text = await response.text()
                    self.logger.error(f"Diffy文檔更新失敗: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"更新Diffy文檔異常: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """刪除文檔"""
        try:
            self._ensure_initialized()
            
            session = await self._get_session()
            
            async with session.delete(f"{self.docs_endpoint}/{document_id}") as response:
                
                if response.status in [200, 204]:
                    self.logger.info(f"Diffy文檔刪除成功: {document_id}")
                    return True
                elif response.status == 404:
                    self.logger.warning(f"Diffy文檔不存在: {document_id}")
                    return True  # 視為成功
                else:
                    error_text = await response.text()
                    self.logger.error(f"Diffy文檔刪除失敗: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"刪除Diffy文檔異常: {e}")
            return False
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """搜索文檔"""
        try:
            self._ensure_initialized()
            
            # 構建搜索參數
            search_params = {
                "query": query.query_text,
                "limit": query.top_k,
                "workspace_id": self.workspace_id
            }
            
            # 添加過濾條件
            if query.filters:
                search_params["filters"] = query.filters
            
            if query.file_formats:
                search_params["file_formats"] = query.file_formats
            
            session = await self._get_session()
            
            async with session.post(self.search_endpoint, json=search_params) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return self._convert_search_results(data, query.mode)
                else:
                    error_text = await response.text()
                    raise SearchError(f"Diffy搜索失敗: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Diffy搜索異常: {e}")
            raise SearchError(f"搜索失敗: {e}")
    
    async def semantic_search(self, query_text: str, top_k: int = 10, 
                            min_score: float = 0.5) -> List[SearchResult]:
        """語義搜索（Diffy可能不原生支援，使用全文搜索）"""
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
        
        return DocumentRecord(
            document_id=data.get("id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            source_file=metadata.get("source_file", ""),
            file_format=metadata.get("file_format", ""),
            file_size=metadata.get("file_size", 0),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            status=DocumentStatus(metadata.get("status", "indexed")),
            associations=metadata.get("associations", []),
            images=metadata.get("images", []),
            custom_fields=metadata.get("custom_fields", {})
        )
    
    def _convert_search_results(self, data: Dict[str, Any], 
                              mode: SearchMode) -> List[SearchResult]:
        """轉換搜索結果"""
        results = []
        
        for item in data.get("results", []):
            # 提取元數據
            metadata = item.get("metadata", {})
            
            # 構建搜索結果
            result = SearchResult(
                document_id=item.get("id", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                score=item.get("score", 0.0),
                highlights=item.get("highlights", []),
                metadata={
                    "source_file": metadata.get("source_file", ""),
                    "file_format": metadata.get("file_format", ""),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", "")
                },
                associated_images=metadata.get("images", []),
                association_scores=[
                    assoc.get("final_score", 0.0) 
                    for assoc in metadata.get("associations", [])
                ],
                search_mode=mode,
                matched_fields=item.get("matched_fields", [])
            )
            
            results.append(result)
        
        return results
    
    async def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.api_base}/workspaces/{self.workspace_id}/stats"
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "total_documents": data.get("document_count", 0),
                        "workspace_id": self.workspace_id,
                        "server_url": self.server_url,
                        "last_updated": datetime.now().isoformat(),
                        "storage_used": data.get("storage_used", 0),
                        "collections": data.get("collection_count", 0)
                    }
                else:
                    return {"error": f"統計查詢失敗: {response.status}"}
                    
        except Exception as e:
            self.logger.error(f"獲取Diffy統計信息異常: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """關閉資源"""
        if self._session and not self._session.closed:
            await self._session.close()
