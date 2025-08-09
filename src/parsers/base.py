"""
解析器基類
Base Parser Classes

定義所有文件解析器的統一接口和數據結構。
採用抽象基類模式確保一致的API設計。

核心設計原則：
1. 統一的輸入輸出接口
2. 標準化的數據結構
3. 錯誤處理和恢復機制
4. 可擴展的解析器架構
5. 性能監控和日誌記錄
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import time
from datetime import datetime

from src.config.logging_config import get_logger, log_performance
from src.association.allen_logic import BoundingBox

logger = get_logger("parser_base")

class ContentType(Enum):
    """內容類型枚舉"""
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    HEADER = "header"
    FOOTER = "footer"
    PARAGRAPH = "paragraph"
    LIST = "list"
    QUOTE = "quote"
    CODE = "code"
    UNKNOWN = "unknown"

class ImageFormat(Enum):
    """圖片格式枚舉"""
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    BMP = "bmp"
    TIFF = "tiff"
    WEBP = "webp"
    UNKNOWN = "unknown"

@dataclass
class TextBlock:
    """文本塊數據結構"""
    
    # 基本信息
    id: str                          # 文本塊唯一ID
    content: str                     # 文本內容
    content_type: ContentType        # 內容類型
    
    # 位置信息
    bbox: Optional[BoundingBox] = None    # 邊界框
    page_number: int = 0             # 頁碼/幻燈片號
    paragraph_index: int = 0         # 段落索引
    
    # 格式信息
    font_name: str = ""              # 字體名稱
    font_size: float = 0.0           # 字體大小
    is_bold: bool = False            # 是否粗體
    is_italic: bool = False          # 是否斜體
    text_color: str = ""             # 文字顏色
    
    # 結構信息
    heading_level: int = 0           # 標題級別 (0=普通文本, 1-6=標題級別)
    list_level: int = 0              # 列表層級
    is_bullet_point: bool = False    # 是否為項目符號
    
    # 元數據
    confidence: float = 1.0          # 提取置信度
    language: str = "auto"           # 語言識別
    char_count: int = field(init=False)  # 字符數
    word_count: int = field(init=False)  # 詞數
    
    def __post_init__(self):
        """初始化後處理"""
        self.char_count = len(self.content)
        self.word_count = len(self.content.split()) if self.content else 0
        
        # 自動設置內容類型
        if self.heading_level > 0:
            self.content_type = ContentType.HEADER
        elif self.is_bullet_point or self.list_level > 0:
            self.content_type = ContentType.LIST
    
    def get_clean_text(self) -> str:
        """獲取清理後的文本"""
        return self.content.strip()
    
    def is_empty(self) -> bool:
        """檢查是否為空文本塊"""
        return not self.content or not self.content.strip()

@dataclass
class ImageContent:
    """圖片內容數據結構"""
    
    # 基本信息
    id: str                          # 圖片唯一ID
    filename: str                    # 原始文件名
    format: ImageFormat              # 圖片格式
    
    # 二進制數據
    data: bytes                      # 圖片二進制數據
    size: int = field(init=False)    # 文件大小（字節）
    
    # 尺寸信息
    width: int = 0                   # 寬度（像素）
    height: int = 0                  # 高度（像素）
    dpi: Tuple[int, int] = (72, 72)  # DPI（水平, 垂直）
    
    # 位置信息
    bbox: Optional[BoundingBox] = None    # 邊界框
    page_number: int = 0             # 頁碼/幻燈片號
    image_index: int = 0             # 圖片索引
    
    # 元數據
    alt_text: str = ""               # 替代文字
    caption: str = ""                # 圖片說明
    title: str = ""                  # 圖片標題
    
    # 處理信息
    extracted_at: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0          # 提取置信度
    checksum: str = ""               # 數據校驗和
    
    def __post_init__(self):
        """初始化後處理"""
        self.size = len(self.data) if self.data else 0
        
        # 生成校驗和
        if self.data:
            import hashlib
            self.checksum = hashlib.md5(self.data).hexdigest()
    
    @property
    def aspect_ratio(self) -> float:
        """寬高比"""
        return self.width / max(self.height, 1)
    
    @property
    def megapixels(self) -> float:
        """百萬像素"""
        return (self.width * self.height) / 1_000_000
    
    def get_suggested_filename(self, document_name: str = "document") -> str:
        """
        獲取建議的文件名（按項目規則命名）
        格式：{文件名}_{頁碼}_{圖片序號}_{時間戳}.{格式}
        """
        timestamp = int(time.time())
        return f"{document_name}_p{self.page_number:03d}_img{self.image_index:03d}_{timestamp}.{self.format.value}"

@dataclass 
class TableContent:
    """表格內容數據結構"""
    
    # 基本信息
    id: str                          # 表格唯一ID
    rows: List[List[str]]            # 表格數據（行x列）
    headers: List[str] = field(default_factory=list)  # 表頭
    
    # 位置信息
    bbox: Optional[BoundingBox] = None    # 邊界框
    page_number: int = 0             # 頁碼/幻燈片號
    table_index: int = 0             # 表格索引
    
    # 結構信息
    row_count: int = field(init=False)    # 行數
    col_count: int = field(init=False)    # 列數
    has_header: bool = field(init=False)  # 是否有表頭
    
    # 元數據
    caption: str = ""                # 表格說明
    title: str = ""                  # 表格標題
    confidence: float = 1.0          # 提取置信度
    
    def __post_init__(self):
        """初始化後處理"""
        self.row_count = len(self.rows)
        self.col_count = max(len(row) for row in self.rows) if self.rows else 0
        self.has_header = bool(self.headers)
    
    def get_cell(self, row: int, col: int) -> str:
        """獲取單元格內容"""
        if 0 <= row < self.row_count and 0 <= col < len(self.rows[row]):
            return self.rows[row][col]
        return ""
    
    def to_markdown(self) -> str:
        """轉換為Markdown表格格式"""
        if not self.rows:
            return ""
        
        lines = []
        
        # 表頭
        if self.has_header:
            lines.append("| " + " | ".join(self.headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(self.headers)) + " |")
        
        # 數據行
        for row in self.rows:
            if len(row) > 0:
                lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(lines)

@dataclass
class DocumentMetadata:
    """文檔元數據"""
    
    # 基本信息
    filename: str                    # 文件名
    file_path: str                   # 文件路徑
    file_size: int                   # 文件大小（字節）
    file_format: str                 # 文件格式
    
    # 文檔屬性
    title: str = ""                  # 文檔標題
    author: str = ""                 # 作者
    subject: str = ""                # 主題
    creator: str = ""                # 創建者
    producer: str = ""               # 生產者
    keywords: List[str] = field(default_factory=list)  # 關鍵詞
    
    # 時間信息
    created_date: Optional[datetime] = None      # 創建時間
    modified_date: Optional[datetime] = None     # 修改時間
    accessed_date: Optional[datetime] = None     # 訪問時間
    
    # 結構信息
    page_count: int = 0              # 頁數/幻燈片數
    text_blocks_count: int = 0       # 文本塊數量
    images_count: int = 0            # 圖片數量
    tables_count: int = 0            # 表格數量
    
    # 解析信息
    parser_name: str = ""            # 解析器名稱
    parser_version: str = ""         # 解析器版本
    parsing_time: float = 0.0        # 解析耗時（秒）
    parsing_date: datetime = field(default_factory=datetime.now)
    
    # 語言和編碼
    language: str = "auto"           # 主要語言
    encoding: str = "utf-8"          # 文本編碼
    
    def get_file_size_mb(self) -> float:
        """獲取文件大小（MB）"""
        return self.file_size / (1024 * 1024)

@dataclass
class ParsedContent:
    """解析結果數據結構"""
    
    # 內容數據
    text_blocks: List[TextBlock] = field(default_factory=list)
    images: List[ImageContent] = field(default_factory=list)  
    tables: List[TableContent] = field(default_factory=list)
    metadata: Optional[DocumentMetadata] = None
    
    # 解析狀態
    success: bool = True             # 解析是否成功
    error_message: str = ""          # 錯誤信息
    warnings: List[str] = field(default_factory=list)  # 警告信息
    
    # 統計信息
    total_text_length: int = field(init=False)
    total_images: int = field(init=False)
    total_tables: int = field(init=False)
    
    def __post_init__(self):
        """初始化後處理"""
        self.total_text_length = sum(len(block.content) for block in self.text_blocks)
        self.total_images = len(self.images)
        self.total_tables = len(self.tables)
    
    def get_all_text(self) -> str:
        """獲取所有文本內容"""
        return "\n".join(block.content for block in self.text_blocks if not block.is_empty())
    
    def get_text_by_page(self, page_number: int) -> List[TextBlock]:
        """獲取指定頁面的文本塊"""
        return [block for block in self.text_blocks if block.page_number == page_number]
    
    def get_images_by_page(self, page_number: int) -> List[ImageContent]:
        """獲取指定頁面的圖片"""
        return [img for img in self.images if img.page_number == page_number]
    
    def validate(self) -> List[str]:
        """驗證解析結果"""
        issues = []
        
        if not self.text_blocks and not self.images and not self.tables:
            issues.append("解析結果為空")
        
        # 檢查文本塊
        for i, block in enumerate(self.text_blocks):
            if block.is_empty():
                issues.append(f"文本塊 {i} 為空")
        
        # 檢查圖片
        for i, img in enumerate(self.images):
            if not img.data:
                issues.append(f"圖片 {i} 數據為空")
            if img.width <= 0 or img.height <= 0:
                issues.append(f"圖片 {i} 尺寸無效")
        
        return issues

# 解析結果類型別名
ParsedResult = ParsedContent

class ParserError(Exception):
    """解析器基礎錯誤"""
    
    def __init__(self, message: str, parser_name: str = "", file_path: str = ""):
        self.message = message
        self.parser_name = parser_name
        self.file_path = file_path
        super().__init__(self.message)

class UnsupportedFormatError(ParserError):
    """不支持的文件格式錯誤"""
    pass

class ParsingFailedError(ParserError):
    """解析失敗錯誤"""
    pass

class BaseParser(ABC):
    """文件解析器基類"""
    
    def __init__(self, name: str = "BaseParser"):
        """
        初始化解析器
        
        Args:
            name: 解析器名稱
        """
        self.name = name
        self.version = "1.0.0"
        self.supported_formats: List[str] = []
        self.logger = get_logger(f"parser_{name.lower()}")
        
        self.logger.debug(f"解析器 {self.name} 初始化完成")
    
    @abstractmethod
    def can_parse(self, file_path: Union[str, Path]) -> bool:
        """
        檢查是否可以解析指定文件
        
        Args:
            file_path: 文件路徑
            
        Returns:
            bool: 是否可以解析
        """
        pass
    
    @abstractmethod
    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedContent:
        """
        解析文件
        
        Args:
            file_path: 文件路徑
            **kwargs: 額外參數
            
        Returns:
            ParsedContent: 解析結果
            
        Raises:
            ParserError: 解析失敗時拋出
        """
        pass
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        獲取文件基本信息
        
        Args:
            file_path: 文件路徑
            
        Returns:
            Dict[str, Any]: 文件信息
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        stat = path.stat()
        
        return {
            "filename": path.name,
            "file_path": str(path.absolute()),
            "file_size": stat.st_size,
            "file_format": path.suffix.lower(),
            "created_date": datetime.fromtimestamp(stat.st_ctime),
            "modified_date": datetime.fromtimestamp(stat.st_mtime),
            "accessed_date": datetime.fromtimestamp(stat.st_atime),
        }
    
    @log_performance("parse_with_metadata")
    def parse_with_metadata(self, file_path: Union[str, Path], **kwargs) -> ParsedContent:
        """
        解析文件並自動填充元數據
        
        Args:
            file_path: 文件路徑
            **kwargs: 解析參數
            
        Returns:
            ParsedContent: 包含完整元數據的解析結果
        """
        start_time = time.time()
        
        try:
            # 獲取文件信息
            file_info = self.get_file_info(file_path)
            
            # 執行解析
            result = self.parse(file_path, **kwargs)
            
            # 計算解析時間
            parsing_time = time.time() - start_time
            
            # 創建或更新元數據
            if result.metadata is None:
                result.metadata = DocumentMetadata(**file_info)
            else:
                # 更新基本信息
                for key, value in file_info.items():
                    if hasattr(result.metadata, key):
                        setattr(result.metadata, key, value)
            
            # 設置解析信息
            result.metadata.parser_name = self.name
            result.metadata.parser_version = self.version
            result.metadata.parsing_time = parsing_time
            
            # 更新統計信息
            result.metadata.text_blocks_count = len(result.text_blocks)
            result.metadata.images_count = len(result.images)
            result.metadata.tables_count = len(result.tables)
            
            self.logger.info(f"文件解析完成: {file_info['filename']}, 耗時: {parsing_time:.3f}秒")
            
            return result
            
        except Exception as e:
            parsing_time = time.time() - start_time
            self.logger.error(f"文件解析失敗: {file_path}, 耗時: {parsing_time:.3f}秒, 錯誤: {e}")
            
            # 返回失敗結果
            return ParsedContent(
                success=False,
                error_message=str(e),
                metadata=DocumentMetadata(
                    **self.get_file_info(file_path),
                    parser_name=self.name,
                    parser_version=self.version,
                    parsing_time=parsing_time
                )
            )
    
    def validate_file(self, file_path: Union[str, Path]) -> None:
        """
        驗證文件有效性
        
        Args:
            file_path: 文件路徑
            
        Raises:
            FileNotFoundError: 文件不存在
            UnsupportedFormatError: 文件格式不支持
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not self.can_parse(file_path):
            raise UnsupportedFormatError(
                f"解析器 {self.name} 不支持文件格式: {path.suffix}",
                parser_name=self.name,
                file_path=str(file_path)
            )
    
    def get_parser_info(self) -> Dict[str, Any]:
        """
        獲取解析器信息
        
        Returns:
            Dict[str, Any]: 解析器信息
        """
        return {
            "name": self.name,
            "version": self.version,
            "supported_formats": self.supported_formats,
            "features": getattr(self, 'features', []),
            "performance": getattr(self, 'performance_info', {}),
        }

def create_bounding_box(x: float, y: float, width: float, height: float) -> BoundingBox:
    """
    創建邊界框的便捷函數
    
    Args:
        x, y: 左上角坐標
        width, height: 寬度和高度
        
    Returns:
        BoundingBox: 邊界框對象
    """
    return BoundingBox(x=x, y=y, width=width, height=height)

def generate_content_id(content_type: str, page: int, index: int) -> str:
    """
    生成內容ID的便捷函數
    
    Args:
        content_type: 內容類型
        page: 頁碼
        index: 索引
        
    Returns:
        str: 生成的ID
    """
    return f"{content_type}_{page:03d}_{index:03d}"

