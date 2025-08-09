"""
圖片元數據處理

管理圖片的元數據信息，包括技術參數、關聯信息和業務數據
遵循項目規格文件中的元數據管理要求
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path

from src.config.logging_config import get_logger
from src.parsers.base import BoundingBox
from .extractor import ExtractedImage
from .optimizer import OptimizedImage
from .storage import StoredImage

logger = get_logger(__name__)

@dataclass
class ImageMetadata:
    """
    圖片完整元數據
    
    按照規格文件要求包含：
    - 技術參數（尺寸、格式、質量等）
    - 來源信息（文檔、頁面、位置等）
    - 處理信息（優化、存儲等）
    - 關聯信息（文本關聯、評分等）
    """
    
    # 基本標識
    image_id: str                                # 圖片唯一標識
    filename: str                               # 文件名
    content_hash: str                           # 內容哈希
    
    # 來源信息
    source_document: str                        # 來源文檔
    source_page: int                           # 來源頁面
    source_position: BoundingBox               # 原始位置
    source_type: str                           # 來源類型 (embedded, vector_graphics, etc.)
    
    # 技術參數
    original_format: str                       # 原始格式
    final_format: str                         # 最終格式
    original_size: tuple                      # 原始尺寸 (width, height)
    final_size: tuple                        # 最終尺寸
    original_file_size: int                  # 原始文件大小
    final_file_size: int                     # 最終文件大小
    
    # 處理信息
    extraction_time: datetime                 # 提取時間
    optimization_applied: List[str]          # 應用的優化技術
    compression_ratio: float                 # 壓縮比
    storage_url: str                        # 存儲URL
    storage_path: str                       # 存儲路徑
    
    # 關聯信息
    associated_text_blocks: List[str] = None        # 關聯的文本塊ID
    association_scores: List[float] = None          # 關聯評分
    caption_references: List[str] = None            # Caption引用
    semantic_tags: List[str] = None                 # 語義標籤
    
    # 業務元數據
    created_at: datetime = None                     # 創建時間
    updated_at: datetime = None                     # 更新時間
    access_count: int = 0                          # 訪問次數
    last_access_time: datetime = None              # 最後訪問時間
    
    # 額外信息
    custom_metadata: Dict[str, Any] = None         # 自定義元數據

class ImageMetadataManager:
    """
    圖片元數據管理器
    
    負責：
    1. 元數據的創建和更新
    2. 元數據的持久化存儲
    3. 元數據的查詢和檢索
    4. 關聯關係的管理
    """
    
    def __init__(self, metadata_storage_path: str = "data/output/metadata"):
        """
        初始化元數據管理器
        
        Args:
            metadata_storage_path: 元數據存儲路徑
        """
        self.storage_path = Path(metadata_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 內存緩存
        self._metadata_cache: Dict[str, ImageMetadata] = {}
        self._load_existing_metadata()
        
        logger.info(f"圖片元數據管理器初始化: {self.storage_path}")
    
    def create_metadata_from_extraction(self, 
                                       extracted_image: ExtractedImage,
                                       source_document: str) -> ImageMetadata:
        """
        從提取的圖片創建元數據
        
        Args:
            extracted_image: 提取的圖片
            source_document: 來源文檔名稱
            
        Returns:
            圖片元數據
        """
        now = datetime.now()
        image_id = self._generate_image_id(extracted_image.hash, source_document)
        
        metadata = ImageMetadata(
            image_id=image_id,
            filename=extracted_image.filename,
            content_hash=extracted_image.hash,
            source_document=source_document,
            source_page=extracted_image.source_page,
            source_position=extracted_image.source_position,
            source_type=extracted_image.metadata.get("source_type", "unknown"),
            original_format=extracted_image.format,
            final_format=extracted_image.format,
            original_size=extracted_image.size,
            final_size=extracted_image.size,
            original_file_size=len(extracted_image.image_data),
            final_file_size=len(extracted_image.image_data),
            extraction_time=now,
            optimization_applied=[],
            compression_ratio=1.0,
            storage_url="",  # 待存儲後更新
            storage_path="",  # 待存儲後更新
            created_at=now,
            updated_at=now,
            custom_metadata=extracted_image.metadata
        )
        
        # 添加到緩存
        self._metadata_cache[image_id] = metadata
        
        logger.debug(f"創建圖片元數據: {image_id}")
        return metadata
    
    def update_metadata_after_optimization(self, 
                                          metadata: ImageMetadata,
                                          optimized_image: OptimizedImage) -> ImageMetadata:
        """
        優化後更新元數據
        
        Args:
            metadata: 原始元數據
            optimized_image: 優化後的圖片
            
        Returns:
            更新後的元數據
        """
        metadata.final_format = optimized_image.format
        metadata.final_size = optimized_image.size
        metadata.final_file_size = optimized_image.optimized_size
        metadata.optimization_applied = optimized_image.optimization_applied
        metadata.compression_ratio = optimized_image.compression_ratio
        metadata.updated_at = datetime.now()
        
        # 更新緩存
        self._metadata_cache[metadata.image_id] = metadata
        
        logger.debug(f"更新圖片優化元數據: {metadata.image_id}")
        return metadata
    
    def update_metadata_after_storage(self, 
                                     metadata: ImageMetadata,
                                     stored_image: StoredImage) -> ImageMetadata:
        """
        存儲後更新元數據
        
        Args:
            metadata: 原始元數據
            stored_image: 存儲後的圖片信息
            
        Returns:
            更新後的元數據
        """
        metadata.storage_url = stored_image.url
        metadata.storage_path = stored_image.storage_path
        metadata.updated_at = datetime.now()
        
        # 更新緩存
        self._metadata_cache[metadata.image_id] = metadata
        
        logger.debug(f"更新圖片存儲元數據: {metadata.image_id}")
        return metadata
    
    def add_text_association(self, 
                           image_id: str,
                           text_block_id: str,
                           association_score: float,
                           caption_reference: Optional[str] = None) -> bool:
        """
        添加文本關聯
        
        Args:
            image_id: 圖片ID
            text_block_id: 文本塊ID
            association_score: 關聯評分
            caption_reference: Caption引用
            
        Returns:
            是否成功添加
        """
        if image_id not in self._metadata_cache:
            logger.warning(f"圖片元數據不存在: {image_id}")
            return False
        
        metadata = self._metadata_cache[image_id]
        
        # 初始化關聯列表
        if metadata.associated_text_blocks is None:
            metadata.associated_text_blocks = []
        if metadata.association_scores is None:
            metadata.association_scores = []
        if metadata.caption_references is None:
            metadata.caption_references = []
        
        # 檢查是否已存在關聯
        if text_block_id in metadata.associated_text_blocks:
            # 更新現有關聯
            index = metadata.associated_text_blocks.index(text_block_id)
            metadata.association_scores[index] = association_score
            if caption_reference:
                metadata.caption_references[index] = caption_reference
        else:
            # 添加新關聯
            metadata.associated_text_blocks.append(text_block_id)
            metadata.association_scores.append(association_score)
            metadata.caption_references.append(caption_reference or "")
        
        metadata.updated_at = datetime.now()
        
        logger.debug(f"添加文本關聯: {image_id} ↔ {text_block_id} (評分: {association_score})")
        return True
    
    def add_semantic_tags(self, image_id: str, tags: List[str]) -> bool:
        """
        添加語義標籤
        
        Args:
            image_id: 圖片ID
            tags: 語義標籤列表
            
        Returns:
            是否成功添加
        """
        if image_id not in self._metadata_cache:
            logger.warning(f"圖片元數據不存在: {image_id}")
            return False
        
        metadata = self._metadata_cache[image_id]
        
        if metadata.semantic_tags is None:
            metadata.semantic_tags = []
        
        # 添加新標籤（去重）
        for tag in tags:
            if tag not in metadata.semantic_tags:
                metadata.semantic_tags.append(tag)
        
        metadata.updated_at = datetime.now()
        
        logger.debug(f"添加語義標籤: {image_id} - {tags}")
        return True
    
    def record_access(self, image_id: str) -> bool:
        """
        記錄圖片訪問
        
        Args:
            image_id: 圖片ID
            
        Returns:
            是否成功記錄
        """
        if image_id not in self._metadata_cache:
            return False
        
        metadata = self._metadata_cache[image_id]
        metadata.access_count += 1
        metadata.last_access_time = datetime.now()
        
        return True
    
    def get_metadata(self, image_id: str) -> Optional[ImageMetadata]:
        """
        獲取圖片元數據
        
        Args:
            image_id: 圖片ID
            
        Returns:
            圖片元數據，如果不存在則返回None
        """
        return self._metadata_cache.get(image_id)
    
    def search_by_document(self, document_name: str) -> List[ImageMetadata]:
        """
        按文檔搜索圖片元數據
        
        Args:
            document_name: 文檔名稱
            
        Returns:
            匹配的圖片元數據列表
        """
        results = []
        for metadata in self._metadata_cache.values():
            if metadata.source_document == document_name:
                results.append(metadata)
        
        return sorted(results, key=lambda x: x.source_page)
    
    def search_by_text_association(self, text_block_id: str) -> List[ImageMetadata]:
        """
        按文本關聯搜索圖片元數據
        
        Args:
            text_block_id: 文本塊ID
            
        Returns:
            關聯的圖片元數據列表
        """
        results = []
        for metadata in self._metadata_cache.values():
            if (metadata.associated_text_blocks and 
                text_block_id in metadata.associated_text_blocks):
                results.append(metadata)
        
        return results
    
    def search_by_semantic_tags(self, tags: List[str]) -> List[ImageMetadata]:
        """
        按語義標籤搜索圖片元數據
        
        Args:
            tags: 要搜索的標籤列表
            
        Returns:
            匹配的圖片元數據列表
        """
        results = []
        for metadata in self._metadata_cache.values():
            if metadata.semantic_tags:
                # 檢查是否有標籤匹配
                if any(tag in metadata.semantic_tags for tag in tags):
                    results.append(metadata)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取元數據統計信息
        
        Returns:
            統計信息字典
        """
        if not self._metadata_cache:
            return {"total_images": 0}
        
        total_images = len(self._metadata_cache)
        
        # 統計文檔分佈
        document_counts = {}
        format_counts = {}
        source_type_counts = {}
        total_original_size = 0
        total_final_size = 0
        total_associations = 0
        
        for metadata in self._metadata_cache.values():
            # 文檔統計
            doc = metadata.source_document
            document_counts[doc] = document_counts.get(doc, 0) + 1
            
            # 格式統計
            fmt = metadata.final_format
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
            
            # 來源類型統計
            src_type = metadata.source_type
            source_type_counts[src_type] = source_type_counts.get(src_type, 0) + 1
            
            # 大小統計
            total_original_size += metadata.original_file_size
            total_final_size += metadata.final_file_size
            
            # 關聯統計
            if metadata.associated_text_blocks:
                total_associations += len(metadata.associated_text_blocks)
        
        # 計算平均壓縮比
        avg_compression_ratio = sum(
            metadata.compression_ratio for metadata in self._metadata_cache.values()
        ) / total_images
        
        return {
            "total_images": total_images,
            "document_distribution": document_counts,
            "format_distribution": format_counts,
            "source_type_distribution": source_type_counts,
            "total_original_size": total_original_size,
            "total_final_size": total_final_size,
            "space_saved": total_original_size - total_final_size,
            "average_compression_ratio": avg_compression_ratio,
            "total_associations": total_associations,
            "images_with_associations": sum(
                1 for metadata in self._metadata_cache.values()
                if metadata.associated_text_blocks
            )
        }
    
    def export_metadata(self, output_path: str, format: str = "json") -> bool:
        """
        導出元數據
        
        Args:
            output_path: 輸出路徑
            format: 導出格式 ("json", "csv")
            
        Returns:
            是否成功導出
        """
        try:
            if format == "json":
                return self._export_to_json(output_path)
            elif format == "csv":
                return self._export_to_csv(output_path)
            else:
                logger.error(f"不支持的導出格式: {format}")
                return False
        except Exception as e:
            logger.error(f"元數據導出失敗: {e}")
            return False
    
    def save_metadata(self, image_id: Optional[str] = None) -> bool:
        """
        保存元數據到磁盤
        
        Args:
            image_id: 特定圖片ID，如果為None則保存所有
            
        Returns:
            是否成功保存
        """
        try:
            if image_id:
                # 保存單個元數據
                if image_id in self._metadata_cache:
                    return self._save_single_metadata(self._metadata_cache[image_id])
                else:
                    logger.warning(f"元數據不存在: {image_id}")
                    return False
            else:
                # 保存所有元數據
                success_count = 0
                for metadata in self._metadata_cache.values():
                    if self._save_single_metadata(metadata):
                        success_count += 1
                
                logger.info(f"元數據保存完成: {success_count}/{len(self._metadata_cache)}")
                return success_count > 0
                
        except Exception as e:
            logger.error(f"元數據保存失敗: {e}")
            return False
    
    def _generate_image_id(self, content_hash: str, source_document: str) -> str:
        """生成圖片ID"""
        combined = f"{source_document}_{content_hash}"
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    def _load_existing_metadata(self):
        """載入現有的元數據"""
        metadata_files = list(self.storage_path.glob("*.json"))
        
        for file_path in metadata_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 恢復datetime對象
                    for date_field in ['extraction_time', 'created_at', 'updated_at', 'last_access_time']:
                        if data.get(date_field):
                            data[date_field] = datetime.fromisoformat(data[date_field])
                    
                    # 恢復BoundingBox對象
                    if data.get('source_position'):
                        pos = data['source_position']
                        data['source_position'] = BoundingBox(pos['x1'], pos['y1'], pos['x2'], pos['y2'])
                    
                    metadata = ImageMetadata(**data)
                    self._metadata_cache[metadata.image_id] = metadata
                    
            except Exception as e:
                logger.warning(f"載入元數據失敗: {file_path} - {e}")
        
        logger.info(f"載入了 {len(self._metadata_cache)} 個圖片元數據")
    
    def _save_single_metadata(self, metadata: ImageMetadata) -> bool:
        """保存單個元數據"""
        file_path = self.storage_path / f"{metadata.image_id}.json"
        
        try:
            # 轉換為可序列化的格式
            data = asdict(metadata)
            
            # 處理datetime對象
            for date_field in ['extraction_time', 'created_at', 'updated_at', 'last_access_time']:
                if data.get(date_field):
                    data[date_field] = data[date_field].isoformat()
            
            # 處理BoundingBox對象
            if data.get('source_position'):
                bbox = data['source_position']
                if hasattr(bbox, 'x1'):  # 是BoundingBox對象
                    data['source_position'] = {
                        'x1': bbox.x1, 'y1': bbox.y1,
                        'x2': bbox.x2, 'y2': bbox.y2
                    }
                # 如果已經是dict，保持不變
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"保存元數據失敗: {metadata.image_id} - {e}")
            return False
    
    def _export_to_json(self, output_path: str) -> bool:
        """導出為JSON格式"""
        export_data = []
        
        for metadata in self._metadata_cache.values():
            data = asdict(metadata)
            
            # 處理datetime對象
            for date_field in ['extraction_time', 'created_at', 'updated_at', 'last_access_time']:
                if data.get(date_field):
                    data[date_field] = data[date_field].isoformat()
            
            # 處理BoundingBox對象
            if data.get('source_position'):
                bbox = data['source_position']
                if hasattr(bbox, 'x1'):  # 是BoundingBox對象
                    data['source_position'] = {
                        'x1': bbox.x1, 'y1': bbox.y1,
                        'x2': bbox.x2, 'y2': bbox.y2
                    }
                # 如果已經是dict，保持不變
            
            export_data.append(data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"元數據導出完成: {output_path}")
        return True
    
    def _export_to_csv(self, output_path: str) -> bool:
        """導出為CSV格式"""
        import csv
        
        if not self._metadata_cache:
            return False
        
        # 定義CSV字段
        csv_fields = [
            'image_id', 'filename', 'source_document', 'source_page',
            'original_format', 'final_format', 'original_size', 'final_size',
            'original_file_size', 'final_file_size', 'compression_ratio',
            'storage_url', 'optimization_applied', 'associated_text_blocks',
            'association_scores', 'created_at', 'access_count'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=csv_fields)
            writer.writeheader()
            
            for metadata in self._metadata_cache.values():
                row = {
                    'image_id': metadata.image_id,
                    'filename': metadata.filename,
                    'source_document': metadata.source_document,
                    'source_page': metadata.source_page,
                    'original_format': metadata.original_format,
                    'final_format': metadata.final_format,
                    'original_size': f"{metadata.original_size[0]}x{metadata.original_size[1]}",
                    'final_size': f"{metadata.final_size[0]}x{metadata.final_size[1]}",
                    'original_file_size': metadata.original_file_size,
                    'final_file_size': metadata.final_file_size,
                    'compression_ratio': metadata.compression_ratio,
                    'storage_url': metadata.storage_url,
                    'optimization_applied': ';'.join(metadata.optimization_applied),
                    'associated_text_blocks': ';'.join(metadata.associated_text_blocks or []),
                    'association_scores': ';'.join(map(str, metadata.association_scores or [])),
                    'created_at': metadata.created_at.isoformat() if metadata.created_at else '',
                    'access_count': metadata.access_count
                }
                writer.writerow(row)
        
        logger.info(f"元數據CSV導出完成: {output_path}")
        return True
