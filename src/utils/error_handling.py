"""
增強錯誤處理模組
Enhanced Error Handling Module

提供統一的錯誤處理、異常恢復和日誌記錄機制。
包含重試機制、錯誤分類和恢復策略。
"""

import sys
import time
import traceback
import functools
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio

from src.config.logging_config import get_logger

logger = get_logger("error_handling")

class ErrorSeverity(Enum):
    """錯誤嚴重程度"""
    CRITICAL = "critical"      # 系統崩潰級錯誤
    HIGH = "high"             # 高優先級錯誤
    MEDIUM = "medium"         # 中等錯誤
    LOW = "low"               # 低優先級錯誤
    WARNING = "warning"       # 警告級別

class ErrorCategory(Enum):
    """錯誤分類"""
    SYSTEM = "system"                 # 系統級錯誤
    NETWORK = "network"               # 網絡錯誤
    FILE_IO = "file_io"              # 文件I/O錯誤
    PARSING = "parsing"               # 解析錯誤
    ASSOCIATION = "association"       # 關聯分析錯誤
    VALIDATION = "validation"         # 驗證錯誤
    CONFIGURATION = "configuration"   # 配置錯誤
    EXTERNAL_API = "external_api"     # 外部API錯誤

@dataclass
class ErrorInfo:
    """錯誤信息結構"""
    error_id: str                               # 錯誤唯一ID
    timestamp: datetime = field(default_factory=datetime.now)
    category: ErrorCategory = ErrorCategory.SYSTEM
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    message: str = ""                           # 錯誤消息
    exception: Optional[Exception] = None       # 原始異常
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: str = ""                       # 堆棧跟踪
    recovery_attempted: bool = False            # 是否嘗試恢復
    recovery_successful: bool = False           # 恢復是否成功
    retry_count: int = 0                        # 重試次數

@dataclass
class RetryConfig:
    """重試配置"""
    max_retries: int = 3                        # 最大重試次數
    initial_delay: float = 1.0                  # 初始延遲（秒）
    max_delay: float = 60.0                     # 最大延遲（秒）
    exponential_base: float = 2.0               # 指數退避基數
    jitter: bool = True                         # 是否添加隨機抖動
    retryable_exceptions: List[Type[Exception]] = field(
        default_factory=lambda: [
            ConnectionError,
            TimeoutError,
            FileNotFoundError,
            PermissionError
        ]
    )

class ErrorHandler:
    """統一錯誤處理器"""
    
    def __init__(self):
        """初始化錯誤處理器"""
        self.logger = logger
        self.error_history: List[ErrorInfo] = []
        self.error_counts: Dict[str, int] = {}
        
        self.logger.info("錯誤處理器初始化完成")
    
    def handle_error(self, 
                    error: Exception,
                    category: ErrorCategory = ErrorCategory.SYSTEM,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Dict[str, Any] = None,
                    recovery_function: Optional[Callable] = None) -> ErrorInfo:
        """
        處理錯誤
        
        Args:
            error: 異常對象
            category: 錯誤分類
            severity: 錯誤嚴重程度
            context: 錯誤上下文
            recovery_function: 恢復函數
            
        Returns:
            ErrorInfo: 錯誤信息
        """
        error_id = self._generate_error_id(error, category)
        
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            exception=error,
            context=context or {},
            stack_trace=traceback.format_exc()
        )
        
        # 記錄錯誤
        self._log_error(error_info)
        
        # 嘗試恢復
        if recovery_function:
            error_info.recovery_attempted = True
            try:
                recovery_function()
                error_info.recovery_successful = True
                self.logger.info(f"錯誤恢復成功: {error_id}")
            except Exception as recovery_error:
                self.logger.error(f"錯誤恢復失敗: {error_id} - {recovery_error}")
        
        # 保存錯誤信息
        self.error_history.append(error_info)
        self.error_counts[error_id] = self.error_counts.get(error_id, 0) + 1
        
        return error_info
    
    def _generate_error_id(self, error: Exception, category: ErrorCategory) -> str:
        """生成錯誤ID"""
        error_type = type(error).__name__
        error_hash = abs(hash(str(error))) % 10000
        return f"{category.value}_{error_type}_{error_hash:04d}"
    
    def _log_error(self, error_info: ErrorInfo):
        """記錄錯誤日誌"""
        log_message = (
            f"[{error_info.severity.value.upper()}] "
            f"{error_info.category.value}: {error_info.message}"
        )
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # 記錄詳細信息
        if error_info.context:
            self.logger.debug(f"錯誤上下文: {error_info.context}")
        
        if error_info.stack_trace:
            self.logger.debug(f"堆棧跟踪: {error_info.stack_trace}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """獲取錯誤統計"""
        total_errors = len(self.error_history)
        
        if total_errors == 0:
            return {"total_errors": 0}
        
        # 按分類統計
        category_counts = {}
        for error in self.error_history:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 按嚴重程度統計
        severity_counts = {}
        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # 最近24小時錯誤
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_errors = sum(1 for error in self.error_history if error.timestamp >= recent_cutoff)
        
        return {
            "total_errors": total_errors,
            "category_distribution": category_counts,
            "severity_distribution": severity_counts,
            "recent_24h_errors": recent_errors,
            "most_common_errors": dict(
                sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            )
        }

def retry_on_error(config: RetryConfig = None):
    """
    重試裝飾器
    
    Args:
        config: 重試配置
        
    Returns:
        裝飾後的函數
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await _retry_async_function(func, config, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return _retry_sync_function(func, config, *args, **kwargs)
            return sync_wrapper
    
    return decorator

def _retry_sync_function(func: Callable, config: RetryConfig, *args, **kwargs):
    """同步函數重試邏輯"""
    last_exception = None
    delay = config.initial_delay
    
    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            # 檢查是否為可重試的異常
            if not any(isinstance(e, exc_type) for exc_type in config.retryable_exceptions):
                logger.warning(f"不可重試的異常: {type(e).__name__}")
                raise
            
            if attempt < config.max_retries:
                # 計算延遲時間
                actual_delay = min(delay, config.max_delay)
                if config.jitter:
                    import random
                    actual_delay *= (0.5 + random.random() * 0.5)
                
                logger.warning(f"重試 {attempt + 1}/{config.max_retries}，延遲 {actual_delay:.2f}s: {e}")
                time.sleep(actual_delay)
                
                # 指數退避
                delay *= config.exponential_base
    
    # 所有重試都失敗了
    raise last_exception

async def _retry_async_function(func: Callable, config: RetryConfig, *args, **kwargs):
    """異步函數重試邏輯"""
    last_exception = None
    delay = config.initial_delay
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            # 檢查是否為可重試的異常
            if not any(isinstance(e, exc_type) for exc_type in config.retryable_exceptions):
                logger.warning(f"不可重試的異常: {type(e).__name__}")
                raise
            
            if attempt < config.max_retries:
                # 計算延遲時間
                actual_delay = min(delay, config.max_delay)
                if config.jitter:
                    import random
                    actual_delay *= (0.5 + random.random() * 0.5)
                
                logger.warning(f"重試 {attempt + 1}/{config.max_retries}，延遲 {actual_delay:.2f}s: {e}")
                await asyncio.sleep(actual_delay)
                
                # 指數退避
                delay *= config.exponential_base
    
    # 所有重試都失敗了
    raise last_exception

def safe_execute(func: Callable, 
                default_return: Any = None,
                error_handler: Optional[ErrorHandler] = None,
                category: ErrorCategory = ErrorCategory.SYSTEM,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> Any:
    """
    安全執行函數
    
    Args:
        func: 要執行的函數
        default_return: 默認返回值
        error_handler: 錯誤處理器
        category: 錯誤分類
        severity: 錯誤嚴重程度
        
    Returns:
        函數執行結果或默認值
    """
    try:
        return func()
    except Exception as e:
        if error_handler:
            error_handler.handle_error(e, category, severity)
        else:
            logger.error(f"執行函數時發生錯誤: {e}")
        
        return default_return

def critical_section(func: Callable) -> Callable:
    """
    關鍵區段裝飾器 - 為關鍵代碼段提供特殊錯誤處理
    
    Args:
        func: 被裝飾的函數
        
    Returns:
        裝飾後的函數
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logger.debug(f"進入關鍵區段: {func.__name__}")
            result = func(*args, **kwargs)
            logger.debug(f"關鍵區段執行成功: {func.__name__}")
            return result
        except Exception as e:
            logger.critical(f"關鍵區段執行失敗: {func.__name__} - {e}")
            logger.critical(f"堆棧跟踪: {traceback.format_exc()}")
            raise
    
    return wrapper

# 全局錯誤處理器實例
_global_error_handler = ErrorHandler()

def get_error_handler() -> ErrorHandler:
    """獲取全局錯誤處理器"""
    return _global_error_handler

def log_and_ignore(exception_types: Union[Type[Exception], List[Type[Exception]]] = Exception):
    """
    記錄異常但不拋出的裝飾器
    
    Args:
        exception_types: 要忽略的異常類型
        
    Returns:
        裝飾後的函數
    """
    if not isinstance(exception_types, (list, tuple)):
        exception_types = [exception_types]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if any(isinstance(e, exc_type) for exc_type in exception_types):
                    logger.warning(f"忽略異常 {func.__name__}: {e}")
                    return None
                else:
                    raise
        return wrapper
    return decorator
