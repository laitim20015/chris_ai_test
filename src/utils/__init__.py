"""
工具模組
Utilities Module

提供系統各個模組通用的工具函數，包括：
- 文件操作工具
- 文本處理工具
- 圖像處理工具
- 數據驗證工具
- 常用算法和計算函數

所有工具函數都經過充分測試，確保在整個系統中的可靠性。
"""

from src.utils.file_utils import (
    FileManager,
    get_file_info,
    validate_file_format,
    calculate_file_hash,
    create_unique_filename,
    safe_file_read,
    safe_file_write,
    cleanup_temp_files,
    get_file_size_mb,
    is_file_accessible,
)

from src.utils.text_utils import (
    TextProcessor,
    clean_text,
    extract_sentences,
    detect_language,
    normalize_whitespace,
    remove_html_tags,
    extract_urls,
    calculate_text_similarity,
    split_into_chunks,
    count_words,
    extract_keywords,
)

from src.utils.image_utils import (
    ImageProcessor,
    get_image_info,
    resize_image,
    compress_image,
    convert_image_format,
    extract_image_metadata,
    calculate_image_hash,
    is_valid_image,
    get_image_dimensions,
    optimize_for_web,
)

from src.utils.validation import (
    DataValidator,
    validate_file_path,
    validate_image_format,
    validate_text_encoding,
    validate_json_structure,
    validate_url_format,
    validate_email_format,
    sanitize_filename,
    sanitize_text_input,
    check_file_safety,
)

__all__ = [
    # 文件操作工具
    "FileManager",
    "get_file_info",
    "validate_file_format",
    "calculate_file_hash",
    "create_unique_filename",
    "safe_file_read",
    "safe_file_write",
    "cleanup_temp_files",
    "get_file_size_mb",
    "is_file_accessible",
    
    # 文本處理工具
    "TextProcessor",
    "clean_text",
    "extract_sentences",
    "detect_language",
    "normalize_whitespace",
    "remove_html_tags",
    "extract_urls",
    "calculate_text_similarity",
    "split_into_chunks",
    "count_words",
    "extract_keywords",
    
    # 圖像處理工具
    "ImageProcessor",
    "get_image_info",
    "resize_image",
    "compress_image",
    "convert_image_format",
    "extract_image_metadata",
    "calculate_image_hash",
    "is_valid_image",
    "get_image_dimensions",
    "optimize_for_web",
    
    # 數據驗證工具
    "DataValidator",
    "validate_file_path",
    "validate_image_format",
    "validate_text_encoding",
    "validate_json_structure",
    "validate_url_format",
    "validate_email_format",
    "sanitize_filename",
    "sanitize_text_input",
    "check_file_safety",
]

# 模組版本和元數據
__version__ = "1.0.0"
__description__ = "AP Project RAG System - 工具模組"

# 常用常量
SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "webp", "bmp", "tiff"]
SUPPORTED_TEXT_ENCODINGS = ["utf-8", "utf-16", "ascii", "latin-1"]
MAX_FILE_SIZE_MB = 100
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

# 性能配置
ENABLE_CACHING = True
CACHE_SIZE_LIMIT = 1000
PROCESSING_TIMEOUT = 300  # 5分鐘

def get_utils_info() -> dict:
    """
    獲取工具模組信息
    
    Returns:
        dict: 模組信息字典
    """
    return {
        "version": __version__,
        "description": __description__,
        "supported_image_formats": SUPPORTED_IMAGE_FORMATS,
        "supported_text_encodings": SUPPORTED_TEXT_ENCODINGS,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "default_chunk_size": DEFAULT_CHUNK_SIZE,
        "default_chunk_overlap": DEFAULT_CHUNK_OVERLAP,
        "performance_config": {
            "enable_caching": ENABLE_CACHING,
            "cache_size_limit": CACHE_SIZE_LIMIT,
            "processing_timeout": PROCESSING_TIMEOUT,
        }
    }

def validate_utils_environment() -> bool:
    """
    驗證工具模組運行環境
    
    Returns:
        bool: 環境是否有效
    """
    try:
        # 驗證必要的Python包是否可用
        import hashlib
        import mimetypes
        import urllib.parse
        import re
        import json
        import pathlib
        
        # 驗證可選的圖像處理包
        try:
            import PIL
            has_pil = True
        except ImportError:
            has_pil = False
        
        return True
        
    except ImportError as e:
        print(f"工具模組環境驗證失敗: {e}")
        return False

# 初始化時進行環境驗證
if not validate_utils_environment():
    raise RuntimeError("工具模組環境驗證失敗，請檢查依賴包安裝")

# 便捷的全局函數
def quick_file_info(file_path: str) -> dict:
    """快速獲取文件信息"""
    return get_file_info(file_path)

def quick_text_clean(text: str) -> str:
    """快速文本清理"""
    return clean_text(text)

def quick_image_resize(image_path: str, max_width: int = 1920, max_height: int = 1080) -> str:
    """快速圖片調整大小"""
    return resize_image(image_path, max_width, max_height)

def quick_validate_file(file_path: str) -> bool:
    """快速文件驗證"""
    return validate_file_path(file_path) and is_file_accessible(file_path)
