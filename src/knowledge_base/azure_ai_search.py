"""
Azure AI Search適配器
Azure AI Search Adapter

實現與Azure AI Search（原Azure Cognitive Search）的集成。
Azure AI Search是微軟提供的雲端搜索服務，支援全文搜索、語義搜索和向量搜索。

功能特性：
- 全文搜索和語義搜索
- 向量搜索（支援sentence-transformers）
- 自動完成和建議
- 分面導航和過濾
- 多語言支援
- 高可用性和擴展性

配置要求：
- Azure訂閱和Azure AI Search服務
- 服務端點URL和API金鑰
- 可選：Azure OpenAI服務用於高級語義功能
"""

from typing import List, Dict, Any, Optional, AsyncIterator
import asyncio
import json
import uuid
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

class AzureAISearchAdapter(BaseKnowledgeAdapter):
    """Azure AI Search適配器實現"""
    
    def __init__(self, config: IndexConfig, 
                 service_name: str,
                 api_key: str,
                 api_version: str = "2023-11-01",
                 **kwargs):
        """
        初始化Azure AI Search適配器
        
        Args:
            config: 索引配置
            service_name: Azure AI Search服務名稱
            api_key: API金鑰
            api_version: API版本
            **kwargs: 其他配置參數
        """
        super().__init__(config, **kwargs)
        
        self.service_name = service_name
        self.api_key = api_key
        self.api_version = api_version
        
        # 構建服務端點
        self.base_url = f"https://{service_name}.search.windows.net"
        self.indexes_url = f"{self.base_url}/indexes"
        self.search_url = f"{self.base_url}/indexes/{config.index_name}/docs"
        
        # HTTP會話
        self._session: Optional[aiohttp.ClientSession] = None
        
        # 請求標頭
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
        self.logger.info(f"Azure AI Search適配器初始化: {service_name}")
    
    @property
    def adapter_name(self) -> str:
        """適配器名稱"""
        return "azure_ai_search"
    
    @property
    def supported_features(self) -> List[str]:
        """支援的功能列表"""
        return [
            "semantic_search",
            "keyword_search", 
            "hybrid_search",
            "vector_search",
            "association_search",
            "faceted_search",
            "auto_complete",
            "suggestions",
            "batch_indexing",
            "real_time_indexing"
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
            # 測試連接
            health = await self.health_check()
            
            if health.get("status") == "healthy":
                self._initialized = True
                self.logger.info("Azure AI Search適配器初始化成功")
                return True
            else:
                self.logger.error(f"Azure AI Search服務不健康: {health}")
                return False
                
        except Exception as e:
            self.logger.error(f"Azure AI Search適配器初始化失敗: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            session = await self._get_session()
            
            # 檢查服務狀態
            async with session.get(
                f"{self.base_url}/servicestats?api-version={self.api_version}"
            ) as response:
                
                if response.status == 200:
                    stats = await response.json()
                    return {
                        "status": "healthy",
                        "service_name": self.service_name,
                        "api_version": self.api_version,
                        "counters": stats.get("counters", {}),
                        "limits": stats.get("limits", {}),
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
        """創建索引"""
        try:
            config = index_config or self.config
            
            # 定義索引schema
            index_definition = {
                "name": config.index_name,
                "description": config.description,
                "fields": [
                    {
                        "name": "document_id",
                        "type": "Edm.String",
                        "key": True,
                        "searchable": False,
                        "filterable": True,
                        "retrievable": True
                    },
                    {
                        "name": "title",
                        "type": "Edm.String",
                        "searchable": True,
                        "filterable": True,
                        "retrievable": True,
                        "analyzer": "zh-Hans.microsoft"
                    },
                    {
                        "name": "content",
                        "type": "Edm.String", 
                        "searchable": True,
                        "retrievable": True,
                        "analyzer": "zh-Hans.microsoft"
                    },
                    {
                        "name": "source_file",
                        "type": "Edm.String",
                        "searchable": False,
                        "filterable": True,
                        "retrievable": True
                    },
                    {
                        "name": "file_format",
                        "type": "Edm.String",
                        "searchable": False,
                        "filterable": True,
                        "facetable": True,
                        "retrievable": True
                    },
                    {
                        "name": "created_at",
                        "type": "Edm.DateTimeOffset",
                        "filterable": True,
                        "sortable": True,
                        "facetable": True,
                        "retrievable": True
                    },
                    {
                        "name": "status",
                        "type": "Edm.String",
                        "filterable": True,
                        "facetable": True,
                        "retrievable": True
                    },
                    {
                        "name": "associations",
                        "type": "Edm.String",
                        "searchable": True,
                        "retrievable": True
                    },
                    {
                        "name": "images", 
                        "type": "Edm.String",
                        "searchable": True,
                        "retrievable": True
                    }
                ]
            }
            
            # 如果啟用向量搜索，添加向量字段
            if config.enable_semantic_search and config.vector_dimension > 0:
                index_definition["fields"].append({
                    "name": "content_vector",
                    "type": "Collection(Edm.Single)",
                    "searchable": True,
                    "dimensions": config.vector_dimension,
                    "vectorSearchProfile": "default-vector-profile"
                })
                
                # 添加向量搜索配置
                index_definition["vectorSearch"] = {
                    "profiles": [
                        {
                            "name": "default-vector-profile",
                            "algorithm": "hnsw-config"
                        }
                    ],
                    "algorithms": [
                        {
                            "name": "hnsw-config",
                            "kind": "hnsw",
                            "hnswParameters": {
                                "metric": "cosine",
                                "m": 4,
                                "efConstruction": 400,
                                "efSearch": 500
                            }
                        }
                    ]
                }
            
            # 如果啟用語義搜索，添加語義配置
            if config.enable_semantic_search:
                index_definition["semantic"] = {
                    "configurations": [
                        {
                            "name": "semantic-config",
                            "prioritizedFields": {
                                "titleField": {
                                    "fieldName": "title"
                                },
                                "contentFields": [
                                    {"fieldName": "content"},
                                    {"fieldName": "associations"}
                                ],
                                "keywordFields": [
                                    {"fieldName": "source_file"},
                                    {"fieldName": "file_format"}
                                ]
                            }
                        }
                    ]
                }
            
            # 發送創建請求
            session = await self._get_session()
            
            async with session.put(
                f"{self.indexes_url}/{config.index_name}?api-version={self.api_version}",
                json=index_definition
            ) as response:
                
                if response.status in [200, 201]:
                    self.logger.info(f"索引創建成功: {config.index_name}")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"索引創建失敗: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"創建索引異常: {e}")
            raise IndexingError(f"創建索引失敗: {e}")
    
    async def delete_index(self, index_name: str) -> bool:
        """刪除索引"""
        try:
            session = await self._get_session()
            
            async with session.delete(
                f"{self.indexes_url}/{index_name}?api-version={self.api_version}"
            ) as response:
                
                if response.status == 204:
                    self.logger.info(f"索引刪除成功: {index_name}")
                    return True
                elif response.status == 404:
                    self.logger.warning(f"索引不存在: {index_name}")
                    return True  # 視為成功
                else:
                    error_text = await response.text()
                    self.logger.error(f"索引刪除失敗: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"刪除索引異常: {e}")
            return False
    
    async def list_indexes(self) -> List[str]:
        """列出所有索引"""
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.indexes_url}?api-version={self.api_version}"
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return [index["name"] for index in data.get("value", [])]
                else:
                    self.logger.error(f"列出索引失敗: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"列出索引異常: {e}")
            return []
    
    async def index_document(self, document: DocumentRecord) -> str:
        """索引單個文檔"""
        return (await self.index_documents([document]))[0]
    
    async def index_documents(self, documents: List[DocumentRecord]) -> List[str]:
        """批量索引文檔"""
        try:
            self._ensure_initialized()
            
            # 驗證文檔
            for doc in documents:
                errors = await self.validate_document(doc)
                if errors:
                    raise IndexingError(f"文檔驗證失敗: {', '.join(errors)}")
            
            # 準備批量操作
            actions = []
            for doc in documents:
                # 轉換為Azure AI Search格式
                search_doc = {
                    "document_id": doc.document_id,
                    "title": doc.title,
                    "content": doc.content,
                    "source_file": doc.source_file,
                    "file_format": doc.file_format,
                    "created_at": doc.created_at.isoformat(),
                    "status": doc.status.value,
                    "associations": json.dumps(doc.associations, ensure_ascii=False),
                    "images": json.dumps(doc.images, ensure_ascii=False)
                }
                
                # 添加向量（如果有）
                if doc.content_vector:
                    search_doc["content_vector"] = doc.content_vector
                
                actions.append({
                    "@search.action": "mergeOrUpload",
                    **search_doc
                })
            
            # 發送批量索引請求
            session = await self._get_session()
            
            async with session.post(
                f"{self.search_url}/index?api-version={self.api_version}",
                json={"value": actions}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    successful_ids = []
                    
                    for item in result.get("value", []):
                        if item.get("status"):
                            successful_ids.append(item.get("key"))
                        else:
                            self.logger.warning(f"文檔索引失敗: {item}")
                    
                    self.logger.info(f"成功索引 {len(successful_ids)}/{len(documents)} 個文檔")
                    return successful_ids
                else:
                    error_text = await response.text()
                    raise IndexingError(f"批量索引失敗: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"索引文檔異常: {e}")
            raise IndexingError(f"索引文檔失敗: {e}")
    
    async def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        """獲取文檔"""
        try:
            self._ensure_initialized()
            
            session = await self._get_session()
            
            async with session.get(
                f"{self.search_url}/{document_id}?api-version={self.api_version}"
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return self._convert_to_document_record(data)
                elif response.status == 404:
                    return None
                else:
                    error_text = await response.text()
                    self.logger.error(f"獲取文檔失敗: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"獲取文檔異常: {e}")
            return None
    
    async def update_document(self, document_id: str, document: DocumentRecord) -> bool:
        """更新文檔"""
        try:
            # 設置文檔ID確保一致性
            document.document_id = document_id
            document.updated_at = datetime.now()
            document.version += 1
            
            # 使用索引方法更新（mergeOrUpload）
            result = await self.index_document(document)
            return result == document_id
            
        except Exception as e:
            self.logger.error(f"更新文檔異常: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """刪除文檔"""
        try:
            self._ensure_initialized()
            
            session = await self._get_session()
            
            # 使用批量刪除API
            actions = [{
                "@search.action": "delete",
                "document_id": document_id
            }]
            
            async with session.post(
                f"{self.search_url}/index?api-version={self.api_version}",
                json={"value": actions}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    success = any(
                        item.get("status") and item.get("key") == document_id
                        for item in result.get("value", [])
                    )
                    
                    if success:
                        self.logger.info(f"文檔刪除成功: {document_id}")
                    else:
                        self.logger.warning(f"文檔刪除失敗: {document_id}")
                    
                    return success
                else:
                    error_text = await response.text()
                    self.logger.error(f"刪除文檔失敗: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"刪除文檔異常: {e}")
            return False
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """搜索文檔"""
        try:
            self._ensure_initialized()
            
            # 根據搜索模式選擇適當的搜索方法
            if query.mode == SearchMode.SEMANTIC:
                return await self.semantic_search(query.query_text, query.top_k, query.min_score)
            elif query.mode == SearchMode.ASSOCIATION:
                return await self.association_search(query.query_text, query.include_associations, query.top_k)
            else:
                # 默認使用混合搜索
                return await self._hybrid_search(query)
                
        except Exception as e:
            self.logger.error(f"搜索異常: {e}")
            raise SearchError(f"搜索失敗: {e}")
    
    async def semantic_search(self, query_text: str, top_k: int = 10, 
                            min_score: float = 0.5) -> List[SearchResult]:
        """語義搜索"""
        try:
            search_params = {
                "search": query_text,
                "top": top_k,
                "queryType": "semantic",
                "semanticConfiguration": "semantic-config",
                "highlight": "title,content",
                "select": "document_id,title,content,source_file,file_format,created_at,associations,images"
            }
            
            return await self._execute_search(search_params, SearchMode.SEMANTIC)
            
        except Exception as e:
            self.logger.error(f"語義搜索異常: {e}")
            raise SearchError(f"語義搜索失敗: {e}")
    
    async def association_search(self, query_text: str, 
                               include_images: bool = True,
                               top_k: int = 10) -> List[SearchResult]:
        """關聯搜索"""
        try:
            # 構建關聯搜索查詢
            search_fields = ["title", "content", "associations"]
            if include_images:
                search_fields.append("images")
            
            search_params = {
                "search": query_text,
                "searchFields": ",".join(search_fields),
                "top": top_k,
                "highlight": "associations,images",
                "select": "document_id,title,content,source_file,associations,images"
            }
            
            return await self._execute_search(search_params, SearchMode.ASSOCIATION)
            
        except Exception as e:
            self.logger.error(f"關聯搜索異常: {e}")
            raise SearchError(f"關聯搜索失敗: {e}")
    
    async def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """混合搜索"""
        search_params = {
            "search": query.query_text,
            "top": query.top_k,
            "queryType": "simple",
            "highlight": "title,content",
            "select": "document_id,title,content,source_file,file_format,created_at,associations,images"
        }
        
        # 添加過濾條件
        if query.filters:
            filter_clauses = []
            for field, value in query.filters.items():
                if isinstance(value, str):
                    filter_clauses.append(f"{field} eq '{value}'")
                elif isinstance(value, list):
                    or_clauses = [f"{field} eq '{v}'" for v in value]
                    filter_clauses.append(f"({' or '.join(or_clauses)})")
            
            if filter_clauses:
                search_params["filter"] = " and ".join(filter_clauses)
        
        return await self._execute_search(search_params, SearchMode.HYBRID)
    
    async def _execute_search(self, search_params: Dict[str, Any], 
                            mode: SearchMode) -> List[SearchResult]:
        """執行搜索請求"""
        session = await self._get_session()
        
        async with session.post(
            f"{self.search_url}/search?api-version={self.api_version}",
            json=search_params
        ) as response:
            
            if response.status == 200:
                data = await response.json()
                return self._convert_search_results(data, mode)
            else:
                error_text = await response.text()
                raise SearchError(f"搜索請求失敗: {response.status} - {error_text}")
    
    def _convert_search_results(self, data: Dict[str, Any], 
                              mode: SearchMode) -> List[SearchResult]:
        """轉換搜索結果"""
        results = []
        
        for item in data.get("value", []):
            # 提取高亮信息
            highlights = []
            if "@search.highlights" in item:
                for field, highlight_list in item["@search.highlights"].items():
                    highlights.extend(highlight_list)
            
            # 解析關聯信息
            associations = []
            association_scores = []
            
            try:
                if item.get("associations"):
                    associations = json.loads(item["associations"])
                    # 提取關聯分數
                    association_scores = [
                        assoc.get("final_score", 0.0) for assoc in associations
                    ]
            except json.JSONDecodeError:
                pass
            
            # 解析圖片信息
            images = []
            try:
                if item.get("images"):
                    images = json.loads(item["images"])
            except json.JSONDecodeError:
                pass
            
            result = SearchResult(
                document_id=item.get("document_id", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                score=item.get("@search.score", 0.0),
                highlights=highlights,
                metadata={
                    "source_file": item.get("source_file", ""),
                    "file_format": item.get("file_format", ""),
                    "created_at": item.get("created_at", "")
                },
                associated_images=images,
                association_scores=association_scores,
                search_mode=mode,
                matched_fields=list(item.get("@search.highlights", {}).keys())
            )
            
            results.append(result)
        
        return results
    
    def _convert_to_document_record(self, data: Dict[str, Any]) -> DocumentRecord:
        """轉換為文檔記錄"""
        # 解析關聯和圖片信息
        associations = []
        images = []
        
        try:
            if data.get("associations"):
                associations = json.loads(data["associations"])
        except json.JSONDecodeError:
            pass
        
        try:
            if data.get("images"):
                images = json.loads(data["images"])
        except json.JSONDecodeError:
            pass
        
        return DocumentRecord(
            document_id=data.get("document_id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            source_file=data.get("source_file", ""),
            file_format=data.get("file_format", ""),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            status=DocumentStatus(data.get("status", "indexed")),
            associations=associations,
            images=images
        )
    
    async def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        try:
            # 執行聚合查詢獲取統計信息
            search_params = {
                "search": "*",
                "top": 0,
                "facets": ["file_format", "status"],
                "count": True
            }
            
            session = await self._get_session()
            
            async with session.post(
                f"{self.search_url}/search?api-version={self.api_version}",
                json=search_params
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    stats = {
                        "total_documents": data.get("@odata.count", 0),
                        "index_name": self.config.index_name,
                        "service_name": self.service_name,
                        "last_updated": datetime.now().isoformat()
                    }
                    
                    # 添加分面統計
                    if "@search.facets" in data:
                        facets = data["@search.facets"]
                        
                        if "file_format" in facets:
                            stats["by_format"] = {
                                item["value"]: item["count"] 
                                for item in facets["file_format"]
                            }
                        
                        if "status" in facets:
                            stats["by_status"] = {
                                item["value"]: item["count"]
                                for item in facets["status"]
                            }
                    
                    return stats
                else:
                    return {"error": f"統計查詢失敗: {response.status}"}
                    
        except Exception as e:
            self.logger.error(f"獲取統計信息異常: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """關閉資源"""
        if self._session and not self._session.closed:
            await self._session.close()
