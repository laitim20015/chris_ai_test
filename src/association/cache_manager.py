"""
緩存管理器
Cache Manager

為空間分析提供高效的緩存機制，支持以下功能：
1. 結果緩存 - 緩存空間分析結果
2. 佈局緩存 - 緩存文檔佈局分析結果
3. 語義緩存 - 緩存語義相似度計算結果
4. 自動清理 - 定期清理過期緩存
5. 性能監控 - 提供詳細的緩存性能統計

權重：支持性工具（項目規則）
"""

from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import time
import threading
import pickle
import json
from pathlib import Path
from src.config.logging_config import get_logger

logger = get_logger("cache_manager")

class CacheType(Enum):
    """緩存類型"""
    SPATIAL = "spatial"          # 空間分析緩存
    LAYOUT = "layout"            # 佈局分析緩存
    SEMANTIC = "semantic"        # 語義分析緩存
    CAPTION = "caption"          # Caption檢測緩存

@dataclass
class CacheEntry:
    """緩存項"""
    data: Any
    timestamp: float
    access_count: int = 0
    ttl: float = 3600.0  # 默認1小時過期
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """檢查是否過期"""
        return time.time() - self.timestamp > self.ttl
    
    def touch(self):
        """更新訪問記錄"""
        self.access_count += 1

@dataclass
class CacheStats:
    """緩存統計"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    memory_usage_bytes: int = 0
    
    def hit_rate(self) -> float:
        """計算命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

class CacheManager:
    """
    高效的緩存管理器
    支持多級緩存、LRU驅逐、自動清理等功能
    """
    
    def __init__(self, 
                 max_memory_mb: int = 100,
                 default_ttl: float = 3600.0,
                 cleanup_interval: float = 300.0,
                 enable_persistence: bool = False,
                 persistence_path: Optional[str] = None):
        """
        初始化緩存管理器
        
        Args:
            max_memory_mb: 最大內存使用量（MB）
            default_ttl: 默認過期時間（秒）
            cleanup_interval: 清理間隔（秒）
            enable_persistence: 是否啟用持久化
            persistence_path: 持久化文件路徑
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.enable_persistence = enable_persistence
        self.persistence_path = Path(persistence_path) if persistence_path else Path("data/cache")
        
        # 分類存儲不同類型的緩存
        self._caches: Dict[CacheType, Dict[str, CacheEntry]] = {
            cache_type: {} for cache_type in CacheType
        }
        
        # 統計信息
        self._stats: Dict[CacheType, CacheStats] = {
            cache_type: CacheStats() for cache_type in CacheType
        }
        
        # 線程安全
        self._lock = threading.RLock()
        self._cleanup_timer: Optional[threading.Timer] = None
        
        # 啟動自動清理
        self._start_cleanup_timer()
        
        # 從持久化存儲加載
        if self.enable_persistence:
            self._load_from_persistence()
        
        logger.info(f"緩存管理器初始化完成，最大內存: {max_memory_mb}MB，TTL: {default_ttl}s")
    
    def get(self, cache_type: CacheType, key: str) -> Optional[Any]:
        """
        從緩存獲取數據
        
        Args:
            cache_type: 緩存類型
            key: 緩存鍵
            
        Returns:
            緩存的數據，如果不存在或過期則返回None
        """
        with self._lock:
            cache = self._caches[cache_type]
            stats = self._stats[cache_type]
            
            if key not in cache:
                stats.misses += 1
                return None
            
            entry = cache[key]
            
            # 檢查是否過期
            if entry.is_expired():
                del cache[key]
                stats.misses += 1
                stats.evictions += 1
                self._update_stats()
                return None
            
            # 命中，更新統計
            entry.touch()
            stats.hits += 1
            
            logger.debug(f"緩存命中: {cache_type.value}.{key[:12]}...")
            return entry.data
    
    def put(self, cache_type: CacheType, key: str, data: Any, ttl: Optional[float] = None) -> bool:
        """
        存入緩存
        
        Args:
            cache_type: 緩存類型
            key: 緩存鍵
            data: 要緩存的數據
            ttl: 過期時間（秒），如果為None則使用默認值
            
        Returns:
            是否成功存入
        """
        with self._lock:
            cache = self._caches[cache_type]
            stats = self._stats[cache_type]
            
            # 計算數據大小
            try:
                data_size = len(pickle.dumps(data))
            except Exception:
                data_size = 1024  # 估算默認大小
            
            # 檢查內存限制
            if self._total_memory_usage() + data_size > self.max_memory_bytes:
                # 嘗試清理過期項
                self._cleanup_expired()
                
                # 如果還是超限，執行LRU驅逐
                if self._total_memory_usage() + data_size > self.max_memory_bytes:
                    self._lru_evict(data_size)
            
            # 創建緩存項
            entry = CacheEntry(
                data=data,
                timestamp=time.time(),
                ttl=ttl or self.default_ttl,
                size_bytes=data_size
            )
            
            cache[key] = entry
            stats.size += 1
            self._update_stats()
            
            logger.debug(f"緩存存入: {cache_type.value}.{key[:12]}..., 大小: {data_size}B")
            return True
    
    def invalidate(self, cache_type: CacheType, key: str) -> bool:
        """
        使特定緩存項失效
        
        Args:
            cache_type: 緩存類型
            key: 緩存鍵
            
        Returns:
            是否成功失效
        """
        with self._lock:
            cache = self._caches[cache_type]
            stats = self._stats[cache_type]
            
            if key in cache:
                del cache[key]
                stats.size -= 1
                stats.evictions += 1
                self._update_stats()
                logger.debug(f"緩存失效: {cache_type.value}.{key[:12]}...")
                return True
            return False
    
    def clear(self, cache_type: Optional[CacheType] = None):
        """
        清空緩存
        
        Args:
            cache_type: 要清空的緩存類型，如果為None則清空所有
        """
        with self._lock:
            if cache_type:
                self._caches[cache_type].clear()
                self._stats[cache_type] = CacheStats()
                logger.info(f"已清空 {cache_type.value} 緩存")
            else:
                for ct in CacheType:
                    self._caches[ct].clear()
                    self._stats[ct] = CacheStats()
                logger.info("已清空所有緩存")
            
            self._update_stats()
    
    def get_stats(self, cache_type: Optional[CacheType] = None) -> Union[CacheStats, Dict[str, CacheStats]]:
        """
        獲取緩存統計
        
        Args:
            cache_type: 緩存類型，如果為None則返回所有統計
            
        Returns:
            緩存統計信息
        """
        with self._lock:
            if cache_type:
                return self._stats[cache_type]
            else:
                return {ct.value: stats for ct, stats in self._stats.items()}
    
    def create_key(self, *args, **kwargs) -> str:
        """
        創建緩存鍵
        
        Args:
            *args: 位置參數
            **kwargs: 關鍵字參數
            
        Returns:
            緩存鍵字符串
        """
        # 將所有參數轉換為字符串並創建哈希
        key_parts = []
        
        for arg in args:
            if hasattr(arg, '__dict__'):
                # 對於對象，使用其屬性
                key_parts.append(str(sorted(arg.__dict__.items())))
            else:
                key_parts.append(str(arg))
        
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _total_memory_usage(self) -> int:
        """計算總內存使用量"""
        total = 0
        for cache in self._caches.values():
            for entry in cache.values():
                total += entry.size_bytes
        return total
    
    def _update_stats(self):
        """更新統計信息"""
        for cache_type in CacheType:
            cache = self._caches[cache_type]
            stats = self._stats[cache_type]
            
            stats.size = len(cache)
            stats.memory_usage_bytes = sum(entry.size_bytes for entry in cache.values())
    
    def _cleanup_expired(self):
        """清理過期項"""
        expired_count = 0
        
        for cache_type in CacheType:
            cache = self._caches[cache_type]
            stats = self._stats[cache_type]
            
            expired_keys = [key for key, entry in cache.items() if entry.is_expired()]
            
            for key in expired_keys:
                del cache[key]
                expired_count += 1
            
            stats.evictions += len(expired_keys)
        
        if expired_count > 0:
            logger.debug(f"清理過期緩存項: {expired_count}")
            self._update_stats()
    
    def _lru_evict(self, needed_space: int):
        """LRU驅逐策略"""
        # 收集所有緩存項並按訪問時間排序
        all_entries = []
        for cache_type in CacheType:
            cache = self._caches[cache_type]
            for key, entry in cache.items():
                all_entries.append((cache_type, key, entry))
        
        # 按最後訪問時間排序（最少使用的在前）
        all_entries.sort(key=lambda x: x[2].timestamp)
        
        freed_space = 0
        evicted_count = 0
        
        for cache_type, key, entry in all_entries:
            if freed_space >= needed_space:
                break
            
            cache = self._caches[cache_type]
            stats = self._stats[cache_type]
            
            del cache[key]
            freed_space += entry.size_bytes
            evicted_count += 1
            stats.evictions += 1
        
        logger.debug(f"LRU驅逐: {evicted_count} 項，釋放空間: {freed_space}B")
        self._update_stats()
    
    def _start_cleanup_timer(self):
        """啟動自動清理定時器"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
        
        self._cleanup_timer = threading.Timer(self.cleanup_interval, self._scheduled_cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()
    
    def _scheduled_cleanup(self):
        """定時清理任務"""
        try:
            self._cleanup_expired()
            
            # 如果啟用持久化，保存緩存
            if self.enable_persistence:
                self._save_to_persistence()
            
        except Exception as e:
            logger.error(f"定時清理失敗: {e}")
        finally:
            # 重新調度下次清理
            self._start_cleanup_timer()
    
    def _save_to_persistence(self):
        """保存緩存到持久化存儲"""
        try:
            self.persistence_path.mkdir(parents=True, exist_ok=True)
            
            for cache_type in CacheType:
                cache = self._caches[cache_type]
                if not cache:
                    continue
                
                file_path = self.persistence_path / f"{cache_type.value}.cache"
                with open(file_path, 'wb') as f:
                    pickle.dump(cache, f)
            
            logger.debug("緩存已保存到持久化存儲")
            
        except Exception as e:
            logger.error(f"保存緩存失敗: {e}")
    
    def _load_from_persistence(self):
        """從持久化存儲加載緩存"""
        try:
            if not self.persistence_path.exists():
                return
            
            loaded_count = 0
            
            for cache_type in CacheType:
                file_path = self.persistence_path / f"{cache_type.value}.cache"
                if not file_path.exists():
                    continue
                
                with open(file_path, 'rb') as f:
                    cache = pickle.load(f)
                    
                # 過濾過期項
                current_time = time.time()
                valid_cache = {
                    k: v for k, v in cache.items() 
                    if current_time - v.timestamp <= v.ttl
                }
                
                self._caches[cache_type] = valid_cache
                loaded_count += len(valid_cache)
            
            if loaded_count > 0:
                logger.info(f"從持久化存儲加載緩存項: {loaded_count}")
                self._update_stats()
                
        except Exception as e:
            logger.error(f"加載緩存失敗: {e}")
    
    def __del__(self):
        """析構函數，清理資源"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
        
        if self.enable_persistence:
            self._save_to_persistence()

# 全局緩存管理器實例
_global_cache_manager: Optional[CacheManager] = None

def get_cache_manager(
    max_memory_mb: int = 100,
    default_ttl: float = 3600.0,
    cleanup_interval: float = 300.0,
    enable_persistence: bool = False,
    persistence_path: Optional[str] = None
) -> CacheManager:
    """
    獲取全局緩存管理器實例（單例模式）
    
    Returns:
        CacheManager: 緩存管理器實例
    """
    global _global_cache_manager
    
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager(
            max_memory_mb=max_memory_mb,
            default_ttl=default_ttl,
            cleanup_interval=cleanup_interval,
            enable_persistence=enable_persistence,
            persistence_path=persistence_path
        )
    
    return _global_cache_manager

def clear_global_cache():
    """清空全局緩存"""
    global _global_cache_manager
    if _global_cache_manager:
        _global_cache_manager.clear()

