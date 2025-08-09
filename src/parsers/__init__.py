"""
文件解析模組
Document Parser Module

本模組負責解析多種文件格式，提取文本、圖片和結構化信息。
嚴格按照項目規格文件的技術選型實現。

支持的文件格式：
1. PDF文件 - PyMuPDF (主要) + pymupdf4llm + unstructured (備用)
2. Word文件 - python-docx
3. PowerPoint文件 - python-pptx

核心設計原則：
- 基於抽象基類的統一接口
- 工廠模式自動選擇解析器
- 分層備用機制確保解析成功
- 標準化輸出格式
- 性能優化和錯誤處理

主要類和函數：
- BaseParser: 抽象基類
- ParserFactory: 解析器工廠
- PDFParser: PDF解析器（3層備用）
- WordParser: Word解析器
- PowerPointParser: PowerPoint解析器
"""

from src.parsers.base import (
    BaseParser,
    ParsedContent,
    TextBlock,
    ImageContent,
    TableContent,
    DocumentMetadata,
    ParserError,
    UnsupportedFormatError,
    ParsedResult
)

from src.parsers.parser_factory import (
    ParserFactory,
    get_parser_for_file,
    register_parser,
    list_supported_formats,
    create_parser_from_config,
    _global_registry
)

from src.parsers.pdf_parser import (
    PDFParser,
    PyMuPDFParser,
    PyMuPDF4LLMParser,
    UnstructuredPDFParser,
    parse_pdf_with_fallback
)

from src.parsers.word_parser import (
    WordParser,
    parse_word_document,
    extract_word_images,
    extract_word_tables
)

from src.parsers.ppt_parser import (
    PowerPointParser,
    parse_powerpoint_slides,
    extract_slide_content,
    extract_ppt_images
)

__all__ = [
    # 基類和數據結構
    "BaseParser",
    "ParsedContent", 
    "TextBlock",
    "ImageContent",
    "TableContent",
    "DocumentMetadata",
    "ParsedResult",
    "ParserError",
    "UnsupportedFormatError",
    
    # 工廠模式
    "ParserFactory",
    "get_parser_for_file",
    "register_parser",
    "list_supported_formats",
    "create_parser_from_config",
    
    # PDF解析器（三層架構）
    "PDFParser",
    "PyMuPDFParser",
    "PyMuPDF4LLMParser", 
    "UnstructuredPDFParser",
    "parse_pdf_with_fallback",
    
    # Word解析器
    "WordParser",
    "parse_word_document",
    "extract_word_images",
    "extract_word_tables",
    
    # PowerPoint解析器
    "PowerPointParser",
    "parse_powerpoint_slides",
    "extract_slide_content",
    "extract_ppt_images",
]

# 支持的文件格式
SUPPORTED_FORMATS = {
    '.pdf': 'PDF文檔',
    '.docx': 'Word文檔',
    '.doc': 'Word文檔 (舊版)',
    '.pptx': 'PowerPoint演示文稿',
    '.ppt': 'PowerPoint演示文稿 (舊版)',
}

# 解析器性能配置（基於項目規格文件的基準）
PARSER_PERFORMANCE_BENCHMARKS = {
    'pymupdf': {
        'speed': 'fastest',           # 0.003-0.2秒
        'accuracy': 'high',
        'features': ['text', 'images', 'tables', 'ocr'],
        'recommended_for': ['performance', 'general']
    },
    'pymupdf4llm': {
        'speed': 'fast',              # 0.12秒
        'accuracy': 'highest',
        'features': ['markdown_output', 'structure'],
        'recommended_for': ['markdown', 'structure']
    },
    'unstructured': {
        'speed': 'moderate',          # 1.29秒
        'accuracy': 'excellent',
        'features': ['semantic_chunking', 'ai_powered'],
        'recommended_for': ['semantic', 'complex_layouts']
    },
    'python_docx': {
        'speed': 'fast',
        'accuracy': 'excellent',
        'features': ['format_preservation', 'metadata'],
        'recommended_for': ['word_documents']
    },
    'python_pptx': {
        'speed': 'fast',
        'accuracy': 'good',
        'features': ['slide_structure', 'animations_ignore'],
        'recommended_for': ['presentations']
    }
}

def get_parser_info() -> dict:
    """
    獲取解析器模組信息
    
    Returns:
        dict: 模組信息
    """
    return {
        "version": "1.0.0",
        "supported_formats": SUPPORTED_FORMATS,
        "performance_benchmarks": PARSER_PERFORMANCE_BENCHMARKS,
        "parser_count": len(SUPPORTED_FORMATS),
        "fallback_levels": 3,  # PDF解析器的備用層數
        "features": [
            "multi_format_support",
            "fallback_mechanisms",
            "performance_optimization",
            "unified_interface",
            "error_recovery"
        ]
    }

def validate_parser_environment() -> bool:
    """
    驗證解析器模組環境
    
    Returns:
        bool: 環境是否有效
    """
    try:
        # 檢查必要的依賴
        import pathlib
        from typing import Dict, List, Optional, Union
        from abc import ABC, abstractmethod
        
        return True
        
    except ImportError as e:
        print(f"解析器模組環境驗證失敗: {e}")
        return False

def get_recommended_parser(file_extension: str, priority: str = "performance") -> str:
    """
    根據文件類型和優先級推薦解析器
    
    Args:
        file_extension: 文件擴展名
        priority: 優先級 ("performance", "accuracy", "features")
        
    Returns:
        str: 推薦的解析器名稱
    """
    recommendations = {
        '.pdf': {
            'performance': 'pymupdf',
            'accuracy': 'pymupdf4llm', 
            'features': 'unstructured'
        },
        '.docx': {
            'performance': 'python_docx',
            'accuracy': 'python_docx',
            'features': 'python_docx'
        },
        '.doc': {
            'performance': 'python_docx',
            'accuracy': 'python_docx', 
            'features': 'python_docx'
        },
        '.pptx': {
            'performance': 'python_pptx',
            'accuracy': 'python_pptx',
            'features': 'python_pptx'
        },
        '.ppt': {
            'performance': 'python_pptx',
            'accuracy': 'python_pptx',
            'features': 'python_pptx'
        }
    }
    
    return recommendations.get(file_extension, {}).get(priority, 'pymupdf')

# 初始化驗證
if not validate_parser_environment():
    raise RuntimeError("解析器模組環境驗證失敗")

# 模組初始化日誌
from src.config.logging_config import get_logger
logger = get_logger("parsers")

# 解析器初始化移至parser_factory.py，避免重複註冊
# 使用_auto_initialize()進行懶加載初始化
logger.info("解析器模組已加載，將使用懶加載方式註冊默認解析器")

logger.info("📄 文件解析模組初始化完成")
logger.info(f"支持格式: {list(SUPPORTED_FORMATS.keys())}")
logger.info(f"解析器數量: {len(SUPPORTED_FORMATS)}")

