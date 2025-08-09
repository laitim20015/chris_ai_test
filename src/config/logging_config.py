"""
日誌配置模組
Logging Configuration Module

基於loguru的現代日誌系統，提供：
- 結構化日誌輸出（JSON格式）
- 日誌輪轉和保留策略
- 多級別日誌記錄
- 異步日誌處理
- 上下文追蹤和性能監控
"""

import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
from contextlib import contextmanager
from loguru import logger
from src.config.settings import get_settings, LoggingSettings

class LogConfig:
    """日誌配置類"""
    
    def __init__(self, settings: Optional[LoggingSettings] = None):
        """
        初始化日誌配置
        
        Args:
            settings: 日誌設置，如果為None則使用默認設置
        """
        if settings is None:
            settings = get_settings().logging
        
        self.settings = settings
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """設置日誌記錄器"""
        # 移除默認處理器
        logger.remove()
        
        # 設置日誌格式
        if self.settings.format == "json":
            log_format = self._get_json_format()
        else:
            log_format = self._get_text_format()
        
        # 添加控制台處理器
        logger.add(
            sys.stderr,
            format=log_format,
            level=self.settings.level,
            colorize=True if self.settings.format == "text" else False,
            serialize=True if self.settings.format == "json" else False
        )
        
        # 添加文件處理器（如果配置了文件路徑）
        if self.settings.file_path:
            self._add_file_handler()
        
        # 設置異常處理
        logger.configure(
            handlers=[
                {
                    "sink": sys.stderr,
                    "level": "ERROR",
                    "format": log_format,
                    "backtrace": True,
                    "diagnose": True
                }
            ]
        )
    
    def _get_json_format(self) -> str:
        """獲取JSON格式模板"""
        return json.dumps({
            "timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}",
            "level": "{level}",
            "logger": "{name}",
            "module": "{module}",
            "function": "{function}",
            "line": "{line}",
            "message": "{message}",
            "extra": "{extra}"
        })
    
    def _get_text_format(self) -> str:
        """獲取文本格式模板"""
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    def _add_file_handler(self) -> None:
        """添加文件處理器"""
        file_path = Path(self.settings.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            str(file_path),
            format=self._get_json_format() if self.settings.format == "json" else self._get_text_format(),
            level=self.settings.level,
            rotation=self.settings.rotation,
            retention=self.settings.retention,
            compression="gz",
            serialize=True if self.settings.format == "json" else False,
            enqueue=True,  # 異步日誌
            backtrace=True,
            diagnose=True
        )

class ContextLogger:
    """上下文日誌記錄器"""
    
    def __init__(self, logger_name: str = "app"):
        """
        初始化上下文日誌記錄器
        
        Args:
            logger_name: 日誌記錄器名稱
        """
        self.logger = logger.bind(name=logger_name)
        self.context: Dict[str, Any] = {}
    
    def add_context(self, **kwargs) -> "ContextLogger":
        """
        添加上下文信息
        
        Args:
            **kwargs: 上下文鍵值對
            
        Returns:
            ContextLogger: 返回自身以支持鏈式調用
        """
        self.context.update(kwargs)
        return self
    
    def clear_context(self) -> "ContextLogger":
        """
        清空上下文信息
        
        Returns:
            ContextLogger: 返回自身以支持鏈式調用
        """
        self.context.clear()
        return self
    
    def _log_with_context(self, level: str, message: str, **kwargs) -> None:
        """
        帶上下文的日誌記錄
        
        Args:
            level: 日誌級別
            message: 日誌消息
            **kwargs: 額外參數
        """
        extra_data = {**self.context, **kwargs}
        bound_logger = self.logger.bind(**extra_data)
        getattr(bound_logger, level.lower())(message)
    
    def debug(self, message: str, **kwargs) -> None:
        """記錄DEBUG級別日誌"""
        self._log_with_context("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """記錄INFO級別日誌"""
        self._log_with_context("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """記錄WARNING級別日誌"""
        self._log_with_context("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """記錄ERROR級別日誌"""
        self._log_with_context("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """記錄CRITICAL級別日誌"""
        self._log_with_context("CRITICAL", message, **kwargs)

class PerformanceLogger:
    """性能監控日誌記錄器"""
    
    def __init__(self, logger_name: str = "performance"):
        """
        初始化性能日誌記錄器
        
        Args:
            logger_name: 日誌記錄器名稱
        """
        self.logger = ContextLogger(logger_name)
        self._measurements = {}
    
    @contextmanager
    def measure(self, operation_name: str, **kwargs):
        """
        性能測量上下文管理器
        
        Args:
            operation_name: 操作名稱
            **kwargs: 額外參數
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self._measurements[operation_name] = duration
            self.logger.info(
                f"Operation '{operation_name}' completed",
                operation_name=operation_name,
                duration_seconds=duration,
                duration_ms=duration * 1000,
                **kwargs
            )
    
    def get_summary(self) -> Dict[str, float]:
        """獲取性能測量摘要"""
        return self._measurements.copy()
    
    def log_function_performance(self, func_name: str, duration: float, **kwargs) -> None:
        """
        記錄函數性能
        
        Args:
            func_name: 函數名稱
            duration: 執行時間（秒）
            **kwargs: 額外參數
        """
        self.logger.info(
            f"Function {func_name} executed",
            function_name=func_name,
            duration_seconds=duration,
            duration_ms=duration * 1000,
            **kwargs
        )
    
    def log_file_processing(self, file_path: str, file_size: int, 
                          processing_time: float, status: str, **kwargs) -> None:
        """
        記錄文件處理性能
        
        Args:
            file_path: 文件路徑
            file_size: 文件大小（字節）
            processing_time: 處理時間（秒）
            status: 處理狀態
            **kwargs: 額外參數
        """
        self.logger.info(
            f"File processing completed: {status}",
            file_path=file_path,
            file_size_bytes=file_size,
            file_size_mb=round(file_size / 1024 / 1024, 2),
            processing_time_seconds=processing_time,
            processing_speed_mb_per_sec=round((file_size / 1024 / 1024) / processing_time, 2),
            status=status,
            **kwargs
        )
    
    def log_association_analysis(self, image_count: int, text_blocks: int,
                               analysis_time: float, associations_found: int, **kwargs) -> None:
        """
        記錄關聯分析性能
        
        Args:
            image_count: 圖片數量
            text_blocks: 文本塊數量
            analysis_time: 分析時間（秒）
            associations_found: 找到的關聯數量
            **kwargs: 額外參數
        """
        self.logger.info(
            "Association analysis completed",
            image_count=image_count,
            text_blocks=text_blocks,
            total_combinations=image_count * text_blocks,
            analysis_time_seconds=analysis_time,
            associations_found=associations_found,
            association_rate=round(associations_found / (image_count * text_blocks), 3) if (image_count * text_blocks) > 0 else 0,
            **kwargs
        )

# 全局日誌配置實例
_log_config: Optional[LogConfig] = None
_app_logger: Optional[ContextLogger] = None
_perf_logger: Optional[PerformanceLogger] = None

def setup_logging(settings: Optional[LoggingSettings] = None) -> LogConfig:
    """
    設置日誌系統
    
    Args:
        settings: 日誌配置，如果為None則使用默認配置
        
    Returns:
        LogConfig: 日誌配置實例
    """
    global _log_config
    _log_config = LogConfig(settings)
    return _log_config

def get_logger(name: str = "app") -> ContextLogger:
    """
    獲取應用日誌記錄器
    
    Args:
        name: 日誌記錄器名稱
        
    Returns:
        ContextLogger: 上下文日誌記錄器
    """
    global _app_logger
    if _app_logger is None:
        _app_logger = ContextLogger(name)
    return _app_logger

def get_performance_logger() -> PerformanceLogger:
    """
    獲取性能日誌記錄器
    
    Returns:
        PerformanceLogger: 性能日誌記錄器
    """
    global _perf_logger
    if _perf_logger is None:
        _perf_logger = PerformanceLogger()
    return _perf_logger

# 便捷的日誌記錄函數
def log_info(message: str, **kwargs) -> None:
    """記錄INFO級別日誌"""
    get_logger().info(message, **kwargs)

def log_error(message: str, **kwargs) -> None:
    """記錄ERROR級別日誌"""
    get_logger().error(message, **kwargs)

def log_warning(message: str, **kwargs) -> None:
    """記錄WARNING級別日誌"""
    get_logger().warning(message, **kwargs)

def log_debug(message: str, **kwargs) -> None:
    """記錄DEBUG級別日誌"""
    get_logger().debug(message, **kwargs)

# 性能監控裝飾器
def log_performance(func_name: Optional[str] = None):
    """
    性能監控裝飾器
    
    Args:
        func_name: 自定義函數名稱，如果為None則使用實際函數名
    """
    import functools
    import time
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                get_performance_logger().log_function_performance(
                    func_name or func.__name__,
                    duration,
                    status="success"
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                get_performance_logger().log_function_performance(
                    func_name or func.__name__,
                    duration,
                    status="error",
                    error=str(e)
                )
                raise
        return wrapper
    return decorator

# 初始化日誌系統
def initialize_logging() -> None:
    """初始化日誌系統"""
    try:
        setup_logging()
        log_info("日誌系統初始化成功", module="logging_config")
    except Exception as e:
        print(f"日誌系統初始化失敗: {e}", file=sys.stderr)
        raise

# 模組加載時自動初始化
try:
    initialize_logging()
except Exception:
    # 如果初始化失敗，使用基本日誌配置
    logger.remove()
    logger.add(sys.stderr, level="INFO")
