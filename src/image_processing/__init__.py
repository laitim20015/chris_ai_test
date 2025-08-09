"""
圖片處理模組

提供完整的圖片處理功能，包括：
- 圖片提取和轉換
- 圖片優化和壓縮  
- 圖片存儲管理（本地/雲端）
- 圖片元數據處理
"""

from .extractor import ImageExtractor, ExtractedImage
from .optimizer import ImageOptimizer, OptimizationConfig, OptimizedImage
from .storage import ImageStorage, LocalImageStorage, CloudImageStorage, StorageConfig, StoredImage
from .metadata import ImageMetadata, ImageMetadataManager

__all__ = [
    "ImageExtractor",
    "ExtractedImage",
    "ImageOptimizer", 
    "OptimizationConfig",
    "OptimizedImage",
    "ImageStorage",
    "LocalImageStorage",
    "CloudImageStorage",
    "StorageConfig",
    "StoredImage",
    "ImageMetadata",
    "ImageMetadataManager"
]
