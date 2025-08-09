"""
解析器工廠模式
Parser Factory Pattern

負責根據文件類型自動選擇和創建合適的解析器。
支持解析器註冊、配置管理和動態選擇。

設計模式：
- 工廠模式：根據文件類型創建解析器
- 註冊模式：動態註冊新的解析器
- 策略模式：根據配置選擇解析策略
"""

from typing import Dict, List, Optional, Type, Union, Any
from pathlib import Path
import mimetypes
from dataclasses import dataclass

from src.parsers.base import BaseParser, UnsupportedFormatError, ParserError
from src.config.logging_config import get_logger

logger = get_logger("parser_factory")

@dataclass
class ParserConfig:
    """解析器配置"""
    
    # 基本配置
    parser_class: Type[BaseParser]   # 解析器類
    priority: int = 1                # 優先級（數字越小優先級越高）
    enabled: bool = True             # 是否啟用
    
    # 性能配置
    max_file_size_mb: float = 100.0  # 最大文件大小（MB）
    timeout_seconds: int = 300       # 超時時間（秒）
    
    # 功能配置
    features: List[str] = None       # 支持的功能
    fallback_parsers: List[str] = None  # 備用解析器
    
    def __post_init__(self):
        if self.features is None:
            self.features = []
        if self.fallback_parsers is None:
            self.fallback_parsers = []

class ParserRegistry:
    """解析器註冊表"""
    
    def __init__(self):
        """初始化註冊表"""
        self._parsers: Dict[str, List[ParserConfig]] = {}  # 格式 -> 解析器配置列表
        self._parser_instances: Dict[str, BaseParser] = {}  # 解析器實例緩存
        
        logger.debug("解析器註冊表初始化完成")
    
    def register(self, file_extensions: Union[str, List[str]], 
                parser_class: Type[BaseParser], **config_kwargs) -> None:
        """
        註冊解析器
        
        Args:
            file_extensions: 支持的文件擴展名
            parser_class: 解析器類
            **config_kwargs: 配置參數
        """
        if isinstance(file_extensions, str):
            file_extensions = [file_extensions]
        
        config = ParserConfig(parser_class=parser_class, **config_kwargs)
        
        for ext in file_extensions:
            ext = ext.lower()
            if not ext.startswith('.'):
                ext = '.' + ext
            
            if ext not in self._parsers:
                self._parsers[ext] = []
            
            self._parsers[ext].append(config)
            
            # 按優先級排序
            self._parsers[ext].sort(key=lambda x: x.priority)
        
        logger.info(f"註冊解析器: {parser_class.__name__} for {file_extensions}")
    
    def get_parsers(self, file_extension: str) -> List[ParserConfig]:
        """
        獲取指定格式的解析器配置列表
        
        Args:
            file_extension: 文件擴展名
            
        Returns:
            List[ParserConfig]: 解析器配置列表
        """
        ext = file_extension.lower()
        if not ext.startswith('.'):
            ext = '.' + ext
        
        return [config for config in self._parsers.get(ext, []) if config.enabled]
    
    def get_parser_instance(self, parser_class: Type[BaseParser]) -> BaseParser:
        """
        獲取解析器實例（帶緩存）
        
        Args:
            parser_class: 解析器類
            
        Returns:
            BaseParser: 解析器實例
        """
        class_name = parser_class.__name__
        
        if class_name not in self._parser_instances:
            self._parser_instances[class_name] = parser_class()
        
        return self._parser_instances[class_name]
    
    def get_parser(self, file_extension: str) -> Optional[BaseParser]:
        """
        根據文件擴展名獲取解析器實例
        
        Args:
            file_extension: 文件擴展名（如 .pdf, .docx）
            
        Returns:
            Optional[BaseParser]: 解析器實例，如果不支持則返回None
        """
        try:
            parsers = self.get_parsers(file_extension)
            if not parsers:
                logger.warning(f"沒有找到支持的解析器: {file_extension}")
                return None
            
            # 返回優先級最高的解析器
            parser_config = parsers[0]
            return self.get_parser_instance(parser_config.parser_class)
            
        except Exception as e:
            logger.error(f"獲取解析器失敗: {file_extension}, 錯誤: {e}")
            return None
    
    def list_supported_formats(self) -> Dict[str, List[str]]:
        """
        列出所有支持的格式
        
        Returns:
            Dict[str, List[str]]: 格式 -> 解析器名稱列表
        """
        result = {}
        
        for ext, configs in self._parsers.items():
            result[ext] = [config.parser_class.__name__ for config in configs if config.enabled]
        
        return result
    
    def unregister(self, file_extension: str, parser_class: Type[BaseParser] = None) -> bool:
        """
        取消註冊解析器
        
        Args:
            file_extension: 文件擴展名
            parser_class: 解析器類（如果為None則移除該格式的所有解析器）
            
        Returns:
            bool: 是否成功移除
        """
        ext = file_extension.lower()
        if not ext.startswith('.'):
            ext = '.' + ext
        
        if ext not in self._parsers:
            return False
        
        if parser_class is None:
            # 移除該格式的所有解析器
            del self._parsers[ext]
            return True
        else:
            # 移除特定解析器
            original_count = len(self._parsers[ext])
            self._parsers[ext] = [
                config for config in self._parsers[ext] 
                if config.parser_class != parser_class
            ]
            return len(self._parsers[ext]) < original_count

# 全局解析器註冊表
_global_registry = ParserRegistry()

class ParserFactory:
    """解析器工廠"""
    
    def __init__(self, registry: Optional[ParserRegistry] = None):
        """
        初始化工廠
        
        Args:
            registry: 解析器註冊表（如果為None則使用全局註冊表）
        """
        self.registry = registry if registry is not None else _global_registry
        self.logger = get_logger("parser_factory")
    
    def get_parser(self, file_extension: str) -> Optional[BaseParser]:
        """
        根據文件擴展名獲取解析器實例
        
        Args:
            file_extension: 文件擴展名（如 .pdf, .docx）
            
        Returns:
            Optional[BaseParser]: 解析器實例，如果不支持則返回None
        """
        try:
            # 確保解析器已初始化
            _auto_initialize()
            
            parsers = self.registry.get_parsers(file_extension)
            if not parsers:
                self.logger.warning(f"沒有找到支持的解析器: {file_extension}")
                return None
            
            # 返回優先級最高的解析器
            parser_config = parsers[0]
            return self.registry.get_parser_instance(parser_config.parser_class)
            
        except Exception as e:
            self.logger.error(f"獲取解析器失敗: {file_extension}, 錯誤: {e}")
            return None
    
    def create_parser(self, file_path: Union[str, Path], 
                     prefer_parser: Optional[str] = None,
                     **parser_kwargs) -> BaseParser:
        """
        為指定文件創建解析器
        
        Args:
            file_path: 文件路徑
            prefer_parser: 偏好的解析器名稱
            **parser_kwargs: 解析器初始化參數
            
        Returns:
            BaseParser: 解析器實例
            
        Raises:
            UnsupportedFormatError: 不支持的文件格式
            ParserError: 解析器創建失敗
        """
        path = Path(file_path)
        file_extension = path.suffix.lower()
        
        # 獲取可用的解析器配置
        parser_configs = self.registry.get_parsers(file_extension)
        
        if not parser_configs:
            raise UnsupportedFormatError(
                f"不支持的文件格式: {file_extension}",
                file_path=str(file_path)
            )
        
        # 如果指定了偏好解析器，優先使用
        if prefer_parser:
            for config in parser_configs:
                if config.parser_class.__name__.lower() == prefer_parser.lower():
                    try:
                        parser = self.registry.get_parser_instance(config.parser_class)
                        self.logger.info(f"使用偏好解析器: {parser.name} for {path.name}")
                        return parser
                    except Exception as e:
                        self.logger.warning(f"偏好解析器創建失敗: {e}")
                        break
        
        # 按優先級嘗試創建解析器
        for config in parser_configs:
            try:
                # 檢查文件大小限制
                file_size_mb = path.stat().st_size / (1024 * 1024)
                if file_size_mb > config.max_file_size_mb:
                    self.logger.warning(
                        f"文件太大 ({file_size_mb:.1f}MB > {config.max_file_size_mb}MB)，"
                        f"跳過解析器: {config.parser_class.__name__}"
                    )
                    continue
                
                parser = self.registry.get_parser_instance(config.parser_class)
                
                # 驗證解析器是否可以處理該文件
                if parser.can_parse(file_path):
                    self.logger.info(f"選擇解析器: {parser.name} for {path.name}")
                    return parser
                
            except Exception as e:
                self.logger.warning(f"解析器 {config.parser_class.__name__} 創建失敗: {e}")
                continue
        
        # 所有解析器都失敗
        available_parsers = [config.parser_class.__name__ for config in parser_configs]
        raise ParserError(
            f"無法為文件 {path.name} 創建解析器，嘗試的解析器: {available_parsers}",
            file_path=str(file_path)
        )
    
    def parse_file(self, file_path: Union[str, Path], 
                  with_fallback: bool = True,
                  prefer_parser: Optional[str] = None,
                  **parse_kwargs) -> 'ParsedContent':
        """
        解析文件（支持備用機制）
        
        Args:
            file_path: 文件路徑
            with_fallback: 是否使用備用解析器
            prefer_parser: 偏好的解析器名稱
            **parse_kwargs: 解析參數
            
        Returns:
            ParsedContent: 解析結果
        """
        path = Path(file_path)
        file_extension = path.suffix.lower()
        
        parser_configs = self.registry.get_parsers(file_extension)
        
        if not parser_configs:
            raise UnsupportedFormatError(
                f"不支持的文件格式: {file_extension}",
                file_path=str(file_path)
            )
        
        # 構建嘗試順序
        attempt_order = []
        
        # 1. 偏好解析器優先
        if prefer_parser:
            for config in parser_configs:
                if config.parser_class.__name__.lower() == prefer_parser.lower():
                    attempt_order.append(config)
                    break
        
        # 2. 按優先級添加其他解析器
        for config in parser_configs:
            if config not in attempt_order:
                attempt_order.append(config)
        
        # 逐個嘗試解析器
        last_error = None
        
        for i, config in enumerate(attempt_order):
            try:
                parser = self.registry.get_parser_instance(config.parser_class)
                
                if not parser.can_parse(file_path):
                    continue
                
                self.logger.info(f"嘗試解析器 {i+1}/{len(attempt_order)}: {parser.name}")
                
                result = parser.parse_with_metadata(file_path, **parse_kwargs)
                
                if result.success:
                    self.logger.info(f"解析成功: {parser.name}")
                    return result
                else:
                    self.logger.warning(f"解析失敗: {parser.name}, 錯誤: {result.error_message}")
                    last_error = result.error_message
                
                # 如果不使用備用機制，第一次失敗就退出
                if not with_fallback:
                    break
                    
            except Exception as e:
                self.logger.error(f"解析器 {config.parser_class.__name__} 異常: {e}")
                last_error = str(e)
                
                if not with_fallback:
                    break
                continue
        
        # 所有解析器都失敗
        from src.parsers.base import ParsedContent, DocumentMetadata
        
        return ParsedContent(
            success=False,
            error_message=f"所有解析器都失敗，最後錯誤: {last_error}",
            metadata=DocumentMetadata(
                filename=path.name,
                file_path=str(path.absolute()),
                file_size=path.stat().st_size,
                file_format=file_extension,
                parser_name="ParserFactory",
                parser_version="1.0.0"
            )
        )
    
    def get_parser_recommendations(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        獲取文件的解析器推薦
        
        Args:
            file_path: 文件路徑
            
        Returns:
            List[Dict[str, Any]]: 推薦信息列表
        """
        path = Path(file_path)
        file_extension = path.suffix.lower()
        
        parser_configs = self.registry.get_parsers(file_extension)
        
        recommendations = []
        
        for config in parser_configs:
            parser = self.registry.get_parser_instance(config.parser_class)
            
            rec = {
                "parser_name": parser.name,
                "parser_class": config.parser_class.__name__,
                "priority": config.priority,
                "can_parse": parser.can_parse(file_path),
                "features": config.features,
                "max_file_size_mb": config.max_file_size_mb,
                "timeout_seconds": config.timeout_seconds,
                "fallback_parsers": config.fallback_parsers
            }
            
            recommendations.append(rec)
        
        return recommendations

# 全局工廠實例
_global_factory = ParserFactory()

def register_parser(file_extensions: Union[str, List[str]], 
                   parser_class: Type[BaseParser], **config_kwargs) -> None:
    """
    註冊解析器到全局註冊表
    
    Args:
        file_extensions: 支持的文件擴展名
        parser_class: 解析器類
        **config_kwargs: 配置參數
    """
    _global_registry.register(file_extensions, parser_class, **config_kwargs)

def get_parser_for_file(file_path: Union[str, Path], 
                       prefer_parser: Optional[str] = None) -> BaseParser:
    """
    為文件獲取解析器
    
    Args:
        file_path: 文件路徑
        prefer_parser: 偏好的解析器名稱
        
    Returns:
        BaseParser: 解析器實例
    """
    return _global_factory.create_parser(file_path, prefer_parser)

def parse_file_with_factory(file_path: Union[str, Path], 
                          with_fallback: bool = True,
                          prefer_parser: Optional[str] = None,
                          **parse_kwargs) -> 'ParsedContent':
    """
    使用工廠解析文件
    
    Args:
        file_path: 文件路徑
        with_fallback: 是否使用備用機制
        prefer_parser: 偏好的解析器名稱
        **parse_kwargs: 解析參數
        
    Returns:
        ParsedContent: 解析結果
    """
    return _global_factory.parse_file(file_path, with_fallback, prefer_parser, **parse_kwargs)

def list_supported_formats() -> Dict[str, List[str]]:
    """
    列出所有支持的格式
    
    Returns:
        Dict[str, List[str]]: 格式 -> 解析器名稱列表
    """
    return _global_registry.list_supported_formats()

def create_parser_from_config(parser_name: str, config: Dict[str, Any]) -> Optional[BaseParser]:
    """
    從配置創建解析器
    
    Args:
        parser_name: 解析器名稱
        config: 配置字典
        
    Returns:
        Optional[BaseParser]: 解析器實例
    """
    try:
        # 這裡可以根據配置動態創建解析器
        # 目前返回None，具體實現依賴於實際需求
        return None
    except Exception as e:
        logger.error(f"從配置創建解析器失敗: {e}")
        return None

def initialize_default_parsers():
    """初始化默認解析器"""
    try:
        # 延遲導入避免循環依賴
        from src.parsers.pdf_parser import PDFParser
        from src.parsers.word_parser import WordParser
        from src.parsers.ppt_parser import PowerPointParser
        
        # 註冊PDF解析器（最高優先級）
        register_parser(
            ['.pdf'], 
            PDFParser,
            priority=1,
            features=['fast_parsing', 'ocr_support', 'fallback_chain'],
            max_file_size_mb=200.0
        )
        
        # 註冊Word解析器
        register_parser(
            ['.docx', '.doc'],
            WordParser, 
            priority=1,
            features=['format_preservation', 'metadata_extraction'],
            max_file_size_mb=100.0
        )
        
        # 註冊PowerPoint解析器
        register_parser(
            ['.pptx', '.ppt'],
            PowerPointParser,
            priority=1,
            features=['slide_structure', 'speaker_notes'],
            max_file_size_mb=150.0
        )
        
        logger.info("默認解析器註冊完成")
        
        # 顯示已註冊的格式
        supported_formats = _global_registry.list_supported_formats()
        logger.info(f"已註冊格式: {list(supported_formats.keys())}")
        
    except ImportError as e:
        logger.warning(f"默認解析器註冊失敗，某些解析器不可用: {e}")

# 自動初始化默認解析器（延遲加載）
def _auto_initialize():
    """自動初始化（僅在需要時調用）"""
    if not _global_registry._parsers:
        initialize_default_parsers()

# 工廠實例的懶加載包裝
class LazyParserFactory:
    """懶加載解析器工廠"""
    
    def __getattr__(self, name):
        _auto_initialize()
        return getattr(_global_factory, name)

# 導出懶加載工廠
lazy_factory = LazyParserFactory()

