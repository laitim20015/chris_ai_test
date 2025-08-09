"""
圖像處理工具
Image Processing Utilities

提供全面的圖像處理功能，包括：
- 圖像信息獲取和驗證
- 圖像尺寸調整和格式轉換
- 圖像壓縮和優化
- 圖像元數據提取
- 圖像哈希計算
"""

import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union, List
from PIL import Image, ImageOps, ExifTags
from PIL.ExifTags import TAGS
import io
from src.config.logging_config import get_logger, log_performance

logger = get_logger("image_utils")

class ImageProcessor:
    """圖像處理器類"""
    
    def __init__(self):
        """初始化圖像處理器"""
        # 支持的圖像格式
        self.supported_formats = {
            'JPEG': ['.jpg', '.jpeg'],
            'PNG': ['.png'],
            'WEBP': ['.webp'],
            'BMP': ['.bmp'],
            'TIFF': ['.tiff', '.tif'],
            'GIF': ['.gif']
        }
        
        # 默認質量設置
        self.quality_settings = {
            'high': 95,
            'medium': 85,
            'low': 70,
            'web': 80
        }

def get_image_info(image_path: Union[str, Path]) -> Dict[str, Any]:
    """
    獲取圖像詳細信息
    
    Args:
        image_path: 圖像文件路徑
        
    Returns:
        Dict[str, Any]: 圖像信息字典
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"圖像文件不存在: {image_path}")
    
    try:
        with Image.open(image_path) as img:
            # 基本信息
            info = {
                "path": str(image_path.absolute()),
                "filename": image_path.name,
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
                "file_size_bytes": image_path.stat().st_size,
                "file_size_mb": round(image_path.stat().st_size / 1024 / 1024, 2),
            }
            
            # 計算圖像比例
            if img.height > 0:
                info["aspect_ratio"] = round(img.width / img.height, 2)
            else:
                info["aspect_ratio"] = 0
            
            # 提取EXIF數據
            exif_data = extract_image_metadata(image_path)
            if exif_data:
                info["exif"] = exif_data
            
            logger.debug(f"圖像信息獲取完成: {image_path.name}, 尺寸: {img.size}")
            return info
            
    except Exception as e:
        logger.error(f"獲取圖像信息失敗: {image_path}, 錯誤: {e}")
        raise ValueError(f"無效的圖像文件: {image_path}")

@log_performance("resize_image")
def resize_image(image_path: Union[str, Path], 
                max_width: int = 1920, 
                max_height: int = 1080,
                maintain_aspect_ratio: bool = True,
                output_path: Optional[Union[str, Path]] = None) -> str:
    """
    調整圖像尺寸
    
    Args:
        image_path: 原始圖像路徑
        max_width: 最大寬度
        max_height: 最大高度
        maintain_aspect_ratio: 是否保持寬高比
        output_path: 輸出路徑，如果為None則覆蓋原文件
        
    Returns:
        str: 輸出文件路徑
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"圖像文件不存在: {image_path}")
    
    if output_path is None:
        output_path = image_path
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with Image.open(image_path) as img:
            original_size = img.size
            
            if maintain_aspect_ratio:
                # 保持寬高比縮放
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                new_size = img.size
            else:
                # 強制調整到指定尺寸
                img = img.resize((max_width, max_height), Image.Resampling.LANCZOS)
                new_size = (max_width, max_height)
            
            # 保存圖像
            save_format = img.format or 'JPEG'
            if save_format == 'JPEG':
                # 轉換RGBA到RGB（JPEG不支持透明度）
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1])
                    img = rgb_img
                img.save(output_path, format=save_format, quality=85, optimize=True)
            else:
                img.save(output_path, format=save_format, optimize=True)
            
            logger.info(f"圖像調整完成: {image_path.name}, "
                       f"原尺寸: {original_size}, 新尺寸: {new_size}")
            
            return str(output_path)
            
    except Exception as e:
        logger.error(f"圖像調整失敗: {image_path}, 錯誤: {e}")
        raise

@log_performance("compress_image")
def compress_image(image_path: Union[str, Path], 
                  quality: int = 85,
                  output_path: Optional[Union[str, Path]] = None) -> str:
    """
    壓縮圖像
    
    Args:
        image_path: 原始圖像路徑
        quality: 壓縮質量 (1-100)
        output_path: 輸出路徑
        
    Returns:
        str: 輸出文件路徑
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"圖像文件不存在: {image_path}")
    
    if output_path is None:
        output_path = image_path
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 驗證質量參數
    quality = max(1, min(100, quality))
    
    try:
        original_size = image_path.stat().st_size
        
        with Image.open(image_path) as img:
            # 轉換為RGB模式（如果是JPEG）
            if img.format == 'JPEG' and img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1])
                img = rgb_img
            
            # 壓縮保存
            if img.format in ['JPEG', 'WEBP']:
                img.save(output_path, format=img.format, 
                        quality=quality, optimize=True)
            else:
                img.save(output_path, format=img.format, optimize=True)
        
        compressed_size = Path(output_path).stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        logger.info(f"圖像壓縮完成: {image_path.name}, "
                   f"原大小: {original_size/1024:.1f}KB, "
                   f"壓縮後: {compressed_size/1024:.1f}KB, "
                   f"壓縮率: {compression_ratio:.1f}%")
        
        return str(output_path)
        
    except Exception as e:
        logger.error(f"圖像壓縮失敗: {image_path}, 錯誤: {e}")
        raise

def convert_image_format(image_path: Union[str, Path], 
                        target_format: str,
                        output_path: Optional[Union[str, Path]] = None,
                        quality: int = 85) -> str:
    """
    轉換圖像格式
    
    Args:
        image_path: 原始圖像路徑
        target_format: 目標格式 (JPEG, PNG, WEBP, etc.)
        output_path: 輸出路徑
        quality: 質量設置
        
    Returns:
        str: 輸出文件路徑
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"圖像文件不存在: {image_path}")
    
    target_format = target_format.upper()
    
    if output_path is None:
        # 根據目標格式生成輸出路徑
        format_extensions = {
            'JPEG': '.jpg',
            'PNG': '.png',
            'WEBP': '.webp',
            'BMP': '.bmp',
            'TIFF': '.tiff'
        }
        ext = format_extensions.get(target_format, '.jpg')
        output_path = image_path.with_suffix(ext)
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with Image.open(image_path) as img:
            # 處理不同格式的轉換
            if target_format == 'JPEG':
                # JPEG不支持透明度
                if img.mode in ('RGBA', 'LA'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img
                elif img.mode == 'P':
                    img = img.convert('RGB')
                
                img.save(output_path, format=target_format, 
                        quality=quality, optimize=True)
            
            elif target_format == 'PNG':
                # PNG支持透明度
                if img.mode not in ('RGBA', 'RGB', 'P'):
                    img = img.convert('RGBA')
                
                img.save(output_path, format=target_format, optimize=True)
            
            elif target_format == 'WEBP':
                # WebP支持透明度和動畫
                img.save(output_path, format=target_format, 
                        quality=quality, optimize=True)
            
            else:
                # 其他格式
                img.save(output_path, format=target_format)
            
            logger.info(f"圖像格式轉換完成: {image_path.name} -> {target_format}")
            return str(output_path)
            
    except Exception as e:
        logger.error(f"圖像格式轉換失敗: {image_path}, 錯誤: {e}")
        raise

def extract_image_metadata(image_path: Union[str, Path]) -> Dict[str, Any]:
    """
    提取圖像元數據
    
    Args:
        image_path: 圖像文件路徑
        
    Returns:
        Dict[str, Any]: 元數據字典
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"圖像文件不存在: {image_path}")
    
    metadata = {}
    
    try:
        with Image.open(image_path) as img:
            # 獲取基本信息
            info = img.info
            if info:
                metadata["info"] = info
            
            # 提取EXIF數據
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif_dict = {}
                exif = img._getexif()
                
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # 處理特殊值
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8')
                        except:
                            value = str(value)
                    
                    exif_dict[tag] = value
                
                metadata["exif"] = exif_dict
            
            logger.debug(f"圖像元數據提取完成: {image_path.name}")
            
    except Exception as e:
        logger.error(f"圖像元數據提取失敗: {image_path}, 錯誤: {e}")
    
    return metadata

def calculate_image_hash(image_path: Union[str, Path], 
                        hash_size: int = 8) -> str:
    """
    計算圖像感知哈希
    
    Args:
        image_path: 圖像文件路徑
        hash_size: 哈希大小
        
    Returns:
        str: 圖像哈希值
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"圖像文件不存在: {image_path}")
    
    try:
        with Image.open(image_path) as img:
            # 轉換為灰度圖像
            img = img.convert('L')
            
            # 調整大小
            img = img.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            
            # 計算差異哈希
            pixels = list(img.getdata())
            
            # 比較相鄰像素
            difference = []
            for row in range(hash_size):
                for col in range(hash_size):
                    pixel_left = pixels[row * (hash_size + 1) + col]
                    pixel_right = pixels[row * (hash_size + 1) + col + 1]
                    difference.append(pixel_left > pixel_right)
            
            # 轉換為十六進制字符串
            decimal_value = 0
            hex_string = []
            for index, pixel in enumerate(difference):
                if pixel:
                    decimal_value += 2 ** (index % 8)
                if (index % 8) == 7:
                    hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
                    decimal_value = 0
            
            hash_value = ''.join(hex_string)
            logger.debug(f"圖像哈希計算完成: {image_path.name}, 哈希: {hash_value[:16]}...")
            
            return hash_value
            
    except Exception as e:
        logger.error(f"圖像哈希計算失敗: {image_path}, 錯誤: {e}")
        raise

def is_valid_image(file_path: Union[str, Path]) -> bool:
    """
    檢查文件是否為有效圖像
    
    Args:
        file_path: 文件路徑
        
    Returns:
        bool: 是否為有效圖像
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except:
        return False

def get_image_dimensions(image_path: Union[str, Path]) -> Tuple[int, int]:
    """
    獲取圖像尺寸
    
    Args:
        image_path: 圖像文件路徑
        
    Returns:
        Tuple[int, int]: (寬度, 高度)
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"圖像文件不存在: {image_path}")
    
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"獲取圖像尺寸失敗: {image_path}, 錯誤: {e}")
        raise

def optimize_for_web(image_path: Union[str, Path], 
                    max_width: int = 1920,
                    max_height: int = 1080,
                    quality: int = 80,
                    output_path: Optional[Union[str, Path]] = None) -> str:
    """
    優化圖像用於Web顯示
    
    Args:
        image_path: 原始圖像路徑
        max_width: 最大寬度
        max_height: 最大高度
        quality: 壓縮質量
        output_path: 輸出路徑
        
    Returns:
        str: 輸出文件路徑
    """
    image_path = Path(image_path)
    
    if output_path is None:
        output_path = image_path.with_suffix('.jpg')
    else:
        output_path = Path(output_path)
    
    # 先調整尺寸
    resized_path = resize_image(
        image_path, max_width, max_height, 
        maintain_aspect_ratio=True, output_path=output_path
    )
    
    # 再壓縮
    optimized_path = compress_image(
        resized_path, quality=quality, output_path=output_path
    )
    
    logger.info(f"Web優化完成: {image_path.name}")
    return optimized_path

# 全局圖像處理器實例
_global_processor: Optional[ImageProcessor] = None

def get_image_processor() -> ImageProcessor:
    """
    獲取全局圖像處理器實例
    
    Returns:
        ImageProcessor: 圖像處理器實例
    """
    global _global_processor
    if _global_processor is None:
        _global_processor = ImageProcessor()
    return _global_processor

