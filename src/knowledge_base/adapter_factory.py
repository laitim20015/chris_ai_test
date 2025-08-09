"""
知識庫適配器工廠
Knowledge Base Adapter Factory

實現工廠模式，統一管理和創建不同的知識庫適配器實例。
提供便捷的API來獲取適配器、列出可用適配器和註冊新適配器。

設計模式：
- 工廠模式：統一創建不同類型的適配器
- 註冊機制：支援動態註冊新的適配器類型
- 配置驅動：根據配置文件自動選擇和配置適配器
- 錯誤處理：提供詳細的錯誤信息和回退機制
"""

from typing import Dict, Type, List, Optional, Any, Union
import importlib
from dataclasses import dataclass
from enum import Enum

from .base_adapter import BaseKnowledgeAdapter, IndexConfig, KnowledgeBaseError
from src.config.logging_config import get_logger

logger = get_logger("knowledge_base.factory")

class AdapterType(Enum):
    """適配器類型枚舉"""
    AZURE_AI_SEARCH = "azure"
    DIFFY = "diffy"
    COPILOT_STUDIO = "copilot"

@dataclass
class AdapterConfig:
    """適配器配置"""
    adapter_type: str
    adapter_class: Type[BaseKnowledgeAdapter]
    required_params: List[str]
    optional_params: List[str]
    description: str
    enabled: bool = True

class KnowledgeBaseFactory:
    """知識庫適配器工廠"""
    
    def __init__(self):
        """初始化工廠"""
        self._adapters: Dict[str, AdapterConfig] = {}
        self._instances: Dict[str, BaseKnowledgeAdapter] = {}
        
        # 註冊默認適配器
        self._register_default_adapters()
        
        logger.info("知識庫適配器工廠初始化完成")
    
    def _register_default_adapters(self):
        """註冊默認適配器"""
        try:
            # 註冊Azure AI Search適配器
            try:
                from .azure_ai_search import AzureAISearchAdapter
                self.register_adapter(
                    adapter_type="azure",
                    adapter_class=AzureAISearchAdapter,
                    required_params=["service_name", "api_key"],
                    optional_params=["api_version"],
                    description="Azure AI Search知識庫適配器"
                )
                logger.info("Azure AI Search適配器註冊成功")
            except ImportError as e:
                logger.warning(f"Azure AI Search適配器不可用: {e}")
            
            # 註冊Diffy適配器
            try:
                from .diffy_adapter import DiffyAdapter
                self.register_adapter(
                    adapter_type="diffy",
                    adapter_class=DiffyAdapter,
                    required_params=["server_url", "api_key", "workspace_id"],
                    optional_params=[],
                    description="Diffy知識庫適配器"
                )
                logger.info("Diffy適配器註冊成功")
            except ImportError as e:
                logger.warning(f"Diffy適配器不可用: {e}")
            
            # 註冊Copilot Studio適配器
            try:
                from .copilot_studio import CopilotStudioAdapter
                self.register_adapter(
                    adapter_type="copilot",
                    adapter_class=CopilotStudioAdapter,
                    required_params=["tenant_id", "client_id", "client_secret", "bot_id"],
                    optional_params=["environment_id"],
                    description="Microsoft Copilot Studio適配器"
                )
                logger.info("Copilot Studio適配器註冊成功")
            except ImportError as e:
                logger.warning(f"Copilot Studio適配器不可用: {e}")
                
        except Exception as e:
            logger.error(f"註冊默認適配器失敗: {e}")
    
    def register_adapter(self, 
                        adapter_type: str,
                        adapter_class: Type[BaseKnowledgeAdapter],
                        required_params: List[str],
                        optional_params: List[str] = None,
                        description: str = "",
                        enabled: bool = True):
        """
        註冊適配器
        
        Args:
            adapter_type: 適配器類型標識
            adapter_class: 適配器類
            required_params: 必需參數列表
            optional_params: 可選參數列表
            description: 適配器描述
            enabled: 是否啟用
        """
        try:
            # 驗證適配器類
            if not issubclass(adapter_class, BaseKnowledgeAdapter):
                raise ValueError(f"適配器類必須繼承自BaseKnowledgeAdapter: {adapter_class}")
            
            config = AdapterConfig(
                adapter_type=adapter_type,
                adapter_class=adapter_class,
                required_params=required_params,
                optional_params=optional_params or [],
                description=description,
                enabled=enabled
            )
            
            self._adapters[adapter_type] = config
            logger.info(f"適配器註冊成功: {adapter_type} - {description}")
            
        except Exception as e:
            logger.error(f"註冊適配器失敗: {adapter_type} - {e}")
            raise KnowledgeBaseError(f"註冊適配器失敗: {e}")
    
    def unregister_adapter(self, adapter_type: str):
        """
        取消註冊適配器
        
        Args:
            adapter_type: 適配器類型
        """
        if adapter_type in self._adapters:
            del self._adapters[adapter_type]
            logger.info(f"適配器取消註冊: {adapter_type}")
        
        # 清理實例緩存
        if adapter_type in self._instances:
            del self._instances[adapter_type]
    
    def list_available_adapters(self) -> Dict[str, Dict[str, Any]]:
        """
        列出可用的適配器
        
        Returns:
            Dict[str, Dict[str, Any]]: 適配器信息字典
        """
        adapters_info = {}
        
        for adapter_type, config in self._adapters.items():
            if config.enabled:
                adapters_info[adapter_type] = {
                    "description": config.description,
                    "required_params": config.required_params,
                    "optional_params": config.optional_params,
                    "class_name": config.adapter_class.__name__
                }
        
        return adapters_info
    
    def get_adapter_config(self, adapter_type: str) -> Optional[AdapterConfig]:
        """
        獲取適配器配置
        
        Args:
            adapter_type: 適配器類型
            
        Returns:
            Optional[AdapterConfig]: 適配器配置，如果不存在則返回None
        """
        return self._adapters.get(adapter_type)
    
    def create_adapter(self, 
                      adapter_type: str,
                      index_config: IndexConfig,
                      **kwargs) -> BaseKnowledgeAdapter:
        """
        創建適配器實例
        
        Args:
            adapter_type: 適配器類型
            index_config: 索引配置
            **kwargs: 適配器特定的配置參數
            
        Returns:
            BaseKnowledgeAdapter: 適配器實例
            
        Raises:
            KnowledgeBaseError: 創建失敗時拋出
        """
        try:
            # 檢查適配器是否已註冊
            if adapter_type not in self._adapters:
                available = list(self._adapters.keys())
                raise KnowledgeBaseError(
                    f"未知的適配器類型: {adapter_type}. 可用類型: {available}"
                )
            
            config = self._adapters[adapter_type]
            
            # 檢查適配器是否啟用
            if not config.enabled:
                raise KnowledgeBaseError(f"適配器已禁用: {adapter_type}")
            
            # 驗證必需參數
            missing_params = []
            for param in config.required_params:
                if param not in kwargs:
                    missing_params.append(param)
            
            if missing_params:
                raise KnowledgeBaseError(
                    f"缺少必需參數: {missing_params}. "
                    f"適配器 {adapter_type} 需要: {config.required_params}"
                )
            
            # 創建適配器實例
            adapter = config.adapter_class(index_config, **kwargs)
            
            logger.info(f"適配器創建成功: {adapter_type}")
            return adapter
            
        except Exception as e:
            logger.error(f"創建適配器失敗: {adapter_type} - {e}")
            raise KnowledgeBaseError(f"創建適配器失敗: {e}")
    
    def get_or_create_adapter(self,
                             adapter_type: str,
                             index_config: IndexConfig,
                             use_cache: bool = True,
                             **kwargs) -> BaseKnowledgeAdapter:
        """
        獲取或創建適配器實例（支援實例緩存）
        
        Args:
            adapter_type: 適配器類型
            index_config: 索引配置
            use_cache: 是否使用緩存
            **kwargs: 適配器配置參數
            
        Returns:
            BaseKnowledgeAdapter: 適配器實例
        """
        cache_key = f"{adapter_type}_{index_config.index_name}"
        
        # 檢查緩存
        if use_cache and cache_key in self._instances:
            logger.debug(f"使用緩存的適配器實例: {cache_key}")
            return self._instances[cache_key]
        
        # 創建新實例
        adapter = self.create_adapter(adapter_type, index_config, **kwargs)
        
        # 緩存實例
        if use_cache:
            self._instances[cache_key] = adapter
            logger.debug(f"適配器實例已緩存: {cache_key}")
        
        return adapter
    
    def clear_cache(self, adapter_type: Optional[str] = None):
        """
        清理實例緩存
        
        Args:
            adapter_type: 指定適配器類型，如果為None則清理所有
        """
        if adapter_type:
            # 清理指定類型的緩存
            keys_to_remove = [
                key for key in self._instances.keys() 
                if key.startswith(f"{adapter_type}_")
            ]
            for key in keys_to_remove:
                del self._instances[key]
            logger.info(f"適配器緩存已清理: {adapter_type}")
        else:
            # 清理所有緩存
            self._instances.clear()
            logger.info("所有適配器緩存已清理")
    
    def validate_adapter_params(self, 
                               adapter_type: str,
                               params: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        驗證適配器參數
        
        Args:
            adapter_type: 適配器類型
            params: 參數字典
            
        Returns:
            Dict[str, List[str]]: 驗證結果，包含missing和unknown字段
        """
        if adapter_type not in self._adapters:
            return {
                "missing": [],
                "unknown": [],
                "error": f"未知的適配器類型: {adapter_type}"
            }
        
        config = self._adapters[adapter_type]
        
        # 檢查缺失的必需參數
        missing = [
            param for param in config.required_params 
            if param not in params
        ]
        
        # 檢查未知參數
        all_known_params = set(config.required_params + config.optional_params)
        unknown = [
            param for param in params.keys()
            if param not in all_known_params
        ]
        
        return {
            "missing": missing,
            "unknown": unknown
        }
    
    def get_adapter_info(self, adapter_type: str) -> Optional[Dict[str, Any]]:
        """
        獲取適配器詳細信息
        
        Args:
            adapter_type: 適配器類型
            
        Returns:
            Optional[Dict[str, Any]]: 適配器信息
        """
        if adapter_type not in self._adapters:
            return None
        
        config = self._adapters[adapter_type]
        adapter_class = config.adapter_class
        
        # 創建臨時實例以獲取特性信息
        try:
            temp_config = IndexConfig(index_name="temp")
            temp_instance = adapter_class(temp_config)
            
            return {
                "adapter_type": adapter_type,
                "adapter_name": temp_instance.adapter_name,
                "description": config.description,
                "class_name": adapter_class.__name__,
                "module": adapter_class.__module__,
                "required_params": config.required_params,
                "optional_params": config.optional_params,
                "supported_features": temp_instance.supported_features,
                "enabled": config.enabled
            }
        except Exception as e:
            logger.error(f"獲取適配器信息失敗: {adapter_type} - {e}")
            return {
                "adapter_type": adapter_type,
                "description": config.description,
                "class_name": adapter_class.__name__,
                "required_params": config.required_params,
                "optional_params": config.optional_params,
                "enabled": config.enabled,
                "error": str(e)
            }

# 全局工廠實例
_global_factory = KnowledgeBaseFactory()

# 便捷函數
def get_knowledge_adapter(adapter_type: str,
                         index_config: IndexConfig,
                         **kwargs) -> BaseKnowledgeAdapter:
    """
    獲取知識庫適配器（便捷函數）
    
    Args:
        adapter_type: 適配器類型
        index_config: 索引配置
        **kwargs: 適配器配置參數
        
    Returns:
        BaseKnowledgeAdapter: 適配器實例
    """
    return _global_factory.create_adapter(adapter_type, index_config, **kwargs)

def list_available_adapters() -> Dict[str, Dict[str, Any]]:
    """
    列出可用適配器（便捷函數）
    
    Returns:
        Dict[str, Dict[str, Any]]: 適配器信息
    """
    return _global_factory.list_available_adapters()

def register_adapter(adapter_type: str,
                    adapter_class: Type[BaseKnowledgeAdapter],
                    required_params: List[str],
                    optional_params: List[str] = None,
                    description: str = ""):
    """
    註冊適配器（便捷函數）
    
    Args:
        adapter_type: 適配器類型
        adapter_class: 適配器類
        required_params: 必需參數
        optional_params: 可選參數
        description: 描述
    """
    _global_factory.register_adapter(
        adapter_type, adapter_class, required_params, 
        optional_params, description
    )

def get_adapter_info(adapter_type: str) -> Optional[Dict[str, Any]]:
    """
    獲取適配器信息（便捷函數）
    
    Args:
        adapter_type: 適配器類型
        
    Returns:
        Optional[Dict[str, Any]]: 適配器信息
    """
    return _global_factory.get_adapter_info(adapter_type)

def validate_adapter_config(adapter_type: str, 
                           config: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    驗證適配器配置（便捷函數）
    
    Args:
        adapter_type: 適配器類型
        config: 配置字典
        
    Returns:
        Dict[str, List[str]]: 驗證結果
    """
    return _global_factory.validate_adapter_params(adapter_type, config)
