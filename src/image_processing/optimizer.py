"""
圖片優化器

負責圖片的格式轉換、尺寸調整和質量優化
遵循項目規格文件中的圖片處理流程：格式標準化 → 尺寸優化 → 質量壓縮
"""

import io
import os
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from PIL import Image, ImageOps
import pillow_heif  # 支持HEIF/HEIC格式

from src.config.logging_config import get_logger
from .extractor import ExtractedImage

logger = get_logger(__name__)

# 註冊HEIF支持
pillow_heif.register_heif_opener()

@dataclass
class OptimizationConfig:
    """圖片優化配置"""
    target_format: str = "PNG"                    # 目標格式
    max_width: int = 1920                        # 最大寬度
    max_height: int = 1080                       # 最大高度
    quality: int = 85                            # JPEG質量 (1-100)
    png_optimize: bool = True                    # PNG優化
    preserve_transparency: bool = True           # 保持透明度
    auto_orient: bool = True                     # 自動方向校正
    strip_metadata: bool = True                  # 移除元數據
    progressive: bool = True                     # 漸進式JPEG
    web_optimized: bool = True                   # Web優化

@dataclass
class OptimizedImage:
    """優化後的圖片"""
    image_data: bytes                            # 優化後的圖片數據
    format: str                                  # 最終格式
    size: Tuple[int, int]                       # 最終尺寸
    original_size: int                          # 原始文件大小
    optimized_size: int                         # 優化後文件大小
    compression_ratio: float                    # 壓縮比
    optimization_applied: List[str]             # 應用的優化技術

class ImageOptimizer:
    """
    圖片優化器
    
    按照規格文件要求提供：
    1. 格式標準化 - 統一轉換為PNG/JPEG
    2. 尺寸優化 - 智能縮放保持品質
    3. 質量壓縮 - 平衡文件大小和視覺效果
    4. Web優化 - 適合網絡傳輸和顯示
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        初始化圖片優化器
        
        Args:
            config: 優化配置，如果為None使用默認配置
        """
        self.config = config or OptimizationConfig()
        
        # 支持的輸入格式
        self.supported_input_formats = {
            'JPEG', 'JPG', 'PNG', 'GIF', 'BMP', 'TIFF', 'TIF', 
            'WEBP', 'HEIF', 'HEIC', 'ICO'
        }
        
        # 支持的輸出格式
        self.supported_output_formats = ['PNG', 'JPEG', 'WEBP']
        
        logger.info(f"圖片優化器初始化完成 - 目標格式: {self.config.target_format}")
    
    def optimize_image(self, extracted_image: ExtractedImage) -> OptimizedImage:
        """
        優化單張圖片
        
        Args:
            extracted_image: 提取的原始圖片
            
        Returns:
            優化後的圖片
        """
        logger.debug(f"開始優化圖片: {extracted_image.filename}")
        
        optimization_applied = []
        original_size = len(extracted_image.image_data)
        
        try:
            # 載入圖片
            pil_image = Image.open(io.BytesIO(extracted_image.image_data))
            original_format = pil_image.format or "unknown"
            
            # 1. 自動方向校正
            if self.config.auto_orient:
                pil_image = ImageOps.exif_transpose(pil_image)
                optimization_applied.append("auto_orient")
            
            # 2. 格式標準化和色彩空間處理
            pil_image = self._normalize_format(pil_image, optimization_applied)
            
            # 3. 尺寸優化
            pil_image = self._optimize_size(pil_image, optimization_applied)
            
            # 4. 質量優化和壓縮
            optimized_data = self._compress_image(pil_image, optimization_applied)
            
            optimized_size = len(optimized_data)
            compression_ratio = original_size / optimized_size if optimized_size > 0 else 1.0
            
            # 創建優化結果
            optimized_image = OptimizedImage(
                image_data=optimized_data,
                format=self.config.target_format,
                size=pil_image.size,
                original_size=original_size,
                optimized_size=optimized_size,
                compression_ratio=compression_ratio,
                optimization_applied=optimization_applied
            )
            
            logger.debug(f"圖片優化完成: {extracted_image.filename} "
                        f"({original_size} → {optimized_size} bytes, "
                        f"壓縮比: {compression_ratio:.2f})")
            
            return optimized_image
            
        except Exception as e:
            logger.error(f"圖片優化失敗: {extracted_image.filename} - {e}")
            raise
    
    def _normalize_format(self, pil_image: Image.Image, 
                         optimization_applied: List[str]) -> Image.Image:
        """
        格式標準化處理
        
        Args:
            pil_image: PIL圖片對象
            optimization_applied: 優化記錄列表
            
        Returns:
            標準化後的圖片
        """
        original_mode = pil_image.mode
        
        # 處理不同的色彩模式
        if self.config.target_format == "PNG":
            # PNG支持透明度
            if pil_image.mode in ('RGBA', 'LA'):
                # 已經有透明通道
                pass
            elif pil_image.mode == 'P':
                # 調色板模式，檢查是否有透明度
                if 'transparency' in pil_image.info:
                    pil_image = pil_image.convert('RGBA')
                else:
                    pil_image = pil_image.convert('RGB')
            elif pil_image.mode in ('1', 'L'):
                # 灰度圖轉RGB
                pil_image = pil_image.convert('RGB')
            elif pil_image.mode == 'CMYK':
                # CMYK轉RGB
                pil_image = pil_image.convert('RGB')
                
        elif self.config.target_format == "JPEG":
            # JPEG不支持透明度，需要轉換
            if pil_image.mode in ('RGBA', 'LA', 'P'):
                # 創建白色背景
                if pil_image.mode == 'P' and 'transparency' in pil_image.info:
                    pil_image = pil_image.convert('RGBA')
                
                if pil_image.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', pil_image.size, (255, 255, 255))
                    if pil_image.mode == 'LA':
                        pil_image = pil_image.convert('RGBA')
                    background.paste(pil_image, mask=pil_image.split()[-1])
                    pil_image = background
                else:
                    pil_image = pil_image.convert('RGB')
            elif pil_image.mode in ('1', 'L'):
                pil_image = pil_image.convert('RGB')
            elif pil_image.mode == 'CMYK':
                pil_image = pil_image.convert('RGB')
        
        if pil_image.mode != original_mode:
            optimization_applied.append(f"format_normalize({original_mode}→{pil_image.mode})")
        
        return pil_image
    
    def _optimize_size(self, pil_image: Image.Image, 
                      optimization_applied: List[str]) -> Image.Image:
        """
        尺寸優化
        
        Args:
            pil_image: PIL圖片對象
            optimization_applied: 優化記錄列表
            
        Returns:
            尺寸優化後的圖片
        """
        original_size = pil_image.size
        width, height = original_size
        
        # 檢查是否需要縮放
        if width <= self.config.max_width and height <= self.config.max_height:
            return pil_image
        
        # 計算縮放比例，保持寬高比
        width_ratio = self.config.max_width / width
        height_ratio = self.config.max_height / height
        scale_ratio = min(width_ratio, height_ratio)
        
        new_width = int(width * scale_ratio)
        new_height = int(height * scale_ratio)
        
        # 使用高質量重採樣算法
        resample_method = Image.Resampling.LANCZOS
        pil_image = pil_image.resize((new_width, new_height), resample_method)
        
        optimization_applied.append(f"resize({original_size}→{pil_image.size})")
        
        logger.debug(f"圖片尺寸優化: {original_size} → {pil_image.size}")
        
        return pil_image
    
    def _compress_image(self, pil_image: Image.Image, 
                       optimization_applied: List[str]) -> bytes:
        """
        圖片壓縮
        
        Args:
            pil_image: PIL圖片對象
            optimization_applied: 優化記錄列表
            
        Returns:
            壓縮後的圖片數據
        """
        output = io.BytesIO()
        
        save_kwargs = {}
        
        if self.config.target_format == "PNG":
            save_kwargs.update({
                'format': 'PNG',
                'optimize': self.config.png_optimize
            })
            if self.config.png_optimize:
                optimization_applied.append("png_optimize")
                
        elif self.config.target_format == "JPEG":
            save_kwargs.update({
                'format': 'JPEG',
                'quality': self.config.quality,
                'optimize': True,
                'progressive': self.config.progressive
            })
            optimization_applied.extend(["jpeg_quality", "jpeg_optimize"])
            if self.config.progressive:
                optimization_applied.append("progressive_jpeg")
                
        elif self.config.target_format == "WEBP":
            save_kwargs.update({
                'format': 'WEBP',
                'quality': self.config.quality,
                'method': 6,  # 最佳壓縮
                'lossless': False
            })
            optimization_applied.append("webp_compress")
        
        # 移除元數據
        if self.config.strip_metadata:
            save_kwargs['exif'] = b''
            optimization_applied.append("strip_metadata")
        
        pil_image.save(output, **save_kwargs)
        
        return output.getvalue()
    
    def optimize_batch(self, extracted_images: List[ExtractedImage]) -> List[OptimizedImage]:
        """
        批量優化圖片
        
        Args:
            extracted_images: 提取的原始圖片列表
            
        Returns:
            優化後的圖片列表
        """
        logger.info(f"開始批量優化 {len(extracted_images)} 張圖片")
        
        optimized_images = []
        success_count = 0
        
        for i, extracted_image in enumerate(extracted_images):
            try:
                optimized_image = self.optimize_image(extracted_image)
                optimized_images.append(optimized_image)
                success_count += 1
                
                if (i + 1) % 10 == 0:
                    logger.info(f"批量優化進度: {i + 1}/{len(extracted_images)}")
                    
            except Exception as e:
                logger.warning(f"批量優化跳過圖片 {extracted_image.filename}: {e}")
                continue
        
        logger.info(f"批量優化完成: {success_count}/{len(extracted_images)} 成功")
        
        return optimized_images
    
    def calculate_total_compression_stats(self, optimized_images: List[OptimizedImage]) -> Dict[str, Any]:
        """
        計算總體壓縮統計
        
        Args:
            optimized_images: 優化後的圖片列表
            
        Returns:
            壓縮統計信息
        """
        if not optimized_images:
            return {}
        
        total_original_size = sum(img.original_size for img in optimized_images)
        total_optimized_size = sum(img.optimized_size for img in optimized_images)
        
        avg_compression_ratio = sum(img.compression_ratio for img in optimized_images) / len(optimized_images)
        
        # 統計優化技術使用情況
        technique_counts = {}
        for img in optimized_images:
            for technique in img.optimization_applied:
                technique_counts[technique] = technique_counts.get(technique, 0) + 1
        
        # 計算尺寸分佈
        size_categories = {
            "small": 0,    # < 100KB
            "medium": 0,   # 100KB - 500KB  
            "large": 0,    # 500KB - 2MB
            "xlarge": 0    # > 2MB
        }
        
        for img in optimized_images:
            size_kb = img.optimized_size / 1024
            if size_kb < 100:
                size_categories["small"] += 1
            elif size_kb < 500:
                size_categories["medium"] += 1
            elif size_kb < 2048:
                size_categories["large"] += 1
            else:
                size_categories["xlarge"] += 1
        
        return {
            "total_images": len(optimized_images),
            "total_original_size": total_original_size,
            "total_optimized_size": total_optimized_size,
            "total_space_saved": total_original_size - total_optimized_size,
            "average_compression_ratio": avg_compression_ratio,
            "space_saved_percentage": ((total_original_size - total_optimized_size) / total_original_size * 100) if total_original_size > 0 else 0,
            "optimization_techniques": technique_counts,
            "size_distribution": size_categories,
            "target_format": self.config.target_format
        }
    
    def update_config(self, **kwargs):
        """
        更新優化配置
        
        Args:
            **kwargs: 配置參數
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.debug(f"更新優化配置: {key} = {value}")
            else:
                logger.warning(f"未知的配置參數: {key}")
    
    def get_recommended_config(self, use_case: str = "web") -> OptimizationConfig:
        """
        獲取推薦的優化配置
        
        Args:
            use_case: 使用場景 ("web", "print", "archive", "thumbnail")
            
        Returns:
            推薦的優化配置
        """
        configs = {
            "web": OptimizationConfig(
                target_format="PNG",
                max_width=1920,
                max_height=1080,
                quality=85,
                web_optimized=True
            ),
            "print": OptimizationConfig(
                target_format="PNG",
                max_width=3840,
                max_height=2160,
                quality=95,
                png_optimize=False,
                strip_metadata=False
            ),
            "archive": OptimizationConfig(
                target_format="PNG",
                max_width=4096,
                max_height=4096,
                quality=100,
                png_optimize=False,
                strip_metadata=False
            ),
            "thumbnail": OptimizationConfig(
                target_format="JPEG",
                max_width=300,
                max_height=300,
                quality=75,
                progressive=False
            )
        }
        
        return configs.get(use_case, self.config)
