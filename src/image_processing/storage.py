"""
圖片存儲管理

實現本地和雲端圖片存儲，遵循項目規格文件中的存儲方案：
- 本地存儲：開發和測試階段
- 雲端存儲：Azure Blob Storage, AWS S3, Google Cloud Storage
- CDN加速：提高圖片訪問速度
"""

import os
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin
import hashlib
import time

from src.config.logging_config import get_logger
from src.config.settings import get_settings
from .optimizer import OptimizedImage

logger = get_logger(__name__)

@dataclass
class StorageConfig:
    """存儲配置"""
    storage_type: str                           # "local", "azure", "aws", "gcp"
    base_path: str                             # 基礎路徑
    public_url_base: Optional[str] = None      # 公共URL基礎地址
    access_key: Optional[str] = None           # 訪問密鑰
    secret_key: Optional[str] = None           # 秘密密鑰
    bucket_name: Optional[str] = None          # 存儲桶名稱
    region: Optional[str] = None               # 區域
    cdn_domain: Optional[str] = None           # CDN域名
    enable_cache: bool = True                  # 啟用緩存
    cache_ttl: int = 86400                     # 緩存TTL（秒）

@dataclass
class StoredImage:
    """已存儲的圖片信息"""
    url: str                                   # 圖片URL
    storage_path: str                          # 存儲路徑
    size: int                                  # 文件大小
    content_type: str                          # 內容類型
    etag: Optional[str] = None                 # ETag
    last_modified: Optional[float] = None      # 最後修改時間
    metadata: Optional[Dict[str, Any]] = None  # 額外元數據

class ImageStorage(ABC):
    """圖片存儲抽象基類"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.settings = get_settings()
        
    @abstractmethod
    async def store_image(self, optimized_image: OptimizedImage, 
                         filename: str) -> StoredImage:
        """存儲單張圖片"""
        pass
    
    @abstractmethod
    async def store_batch(self, images_with_filenames: List[Tuple[OptimizedImage, str]]) -> List[StoredImage]:
        """批量存儲圖片"""
        pass
    
    @abstractmethod
    async def delete_image(self, storage_path: str) -> bool:
        """刪除圖片"""
        pass
    
    @abstractmethod
    async def get_image_info(self, storage_path: str) -> Optional[StoredImage]:
        """獲取圖片信息"""
        pass
    
    @abstractmethod
    async def list_images(self, prefix: str = "") -> List[StoredImage]:
        """列出圖片"""
        pass
    
    def generate_storage_path(self, filename: str, content_hash: Optional[str] = None) -> str:
        """
        生成存儲路徑
        
        遵循規格文件的命名規範：
        {文件名}_{頁碼/幻燈片號}_{圖片序號}_{時間戳}.{格式}
        """
        # 按日期組織目錄結構
        import datetime
        now = datetime.datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        
        # 如果有內容哈希，用於去重
        if content_hash:
            name_part, ext = os.path.splitext(filename)
            filename = f"{name_part}_{content_hash[:8]}{ext}"
        
        return f"{date_path}/{filename}"
    
    def generate_public_url(self, storage_path: str) -> str:
        """生成公共訪問URL"""
        if self.config.cdn_domain:
            return urljoin(f"https://{self.config.cdn_domain}/", storage_path)
        elif self.config.public_url_base:
            return urljoin(self.config.public_url_base, storage_path)
        else:
            # 本地存儲情況
            return urljoin(f"http://localhost:8000/images/", storage_path)

class LocalImageStorage(ImageStorage):
    """
    本地圖片存儲
    
    適用於開發和測試階段
    """
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.base_dir = Path(config.base_path)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"本地圖片存儲初始化: {self.base_dir}")
    
    async def store_image(self, optimized_image: OptimizedImage, 
                         filename: str) -> StoredImage:
        """存儲單張圖片到本地"""
        
        # 生成內容哈希用於去重
        content_hash = hashlib.md5(optimized_image.image_data).hexdigest()
        storage_path = self.generate_storage_path(filename, content_hash)
        
        # 創建完整文件路徑
        full_path = self.base_dir / storage_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 檢查文件是否已存在（去重）
        if full_path.exists():
            logger.debug(f"圖片已存在，跳過存儲: {storage_path}")
            return await self.get_image_info(storage_path)
        
        # 寫入文件
        try:
            with open(full_path, 'wb') as f:
                f.write(optimized_image.image_data)
            
            # 生成URL
            public_url = self.generate_public_url(storage_path)
            
            # 確定內容類型
            content_type = f"image/{optimized_image.format.lower()}"
            if optimized_image.format.upper() == "JPEG":
                content_type = "image/jpeg"
            
            stored_image = StoredImage(
                url=public_url,
                storage_path=storage_path,
                size=len(optimized_image.image_data),
                content_type=content_type,
                etag=content_hash,
                last_modified=time.time(),
                metadata={
                    "optimization_applied": optimized_image.optimization_applied,
                    "compression_ratio": optimized_image.compression_ratio,
                    "original_size": optimized_image.original_size
                }
            )
            
            logger.debug(f"本地圖片存儲成功: {storage_path}")
            return stored_image
            
        except Exception as e:
            logger.error(f"本地圖片存儲失敗: {storage_path} - {e}")
            raise
    
    async def store_batch(self, images_with_filenames: List[Tuple[OptimizedImage, str]]) -> List[StoredImage]:
        """批量存儲圖片到本地"""
        logger.info(f"開始批量本地存儲 {len(images_with_filenames)} 張圖片")
        
        stored_images = []
        
        for optimized_image, filename in images_with_filenames:
            try:
                stored_image = await self.store_image(optimized_image, filename)
                stored_images.append(stored_image)
            except Exception as e:
                logger.warning(f"批量存儲跳過圖片 {filename}: {e}")
                continue
        
        logger.info(f"批量本地存儲完成: {len(stored_images)}/{len(images_with_filenames)} 成功")
        return stored_images
    
    async def delete_image(self, storage_path: str) -> bool:
        """刪除本地圖片"""
        full_path = self.base_dir / storage_path
        
        try:
            if full_path.exists():
                full_path.unlink()
                logger.debug(f"本地圖片刪除成功: {storage_path}")
                return True
            else:
                logger.warning(f"本地圖片不存在: {storage_path}")
                return False
        except Exception as e:
            logger.error(f"本地圖片刪除失敗: {storage_path} - {e}")
            return False
    
    async def get_image_info(self, storage_path: str) -> Optional[StoredImage]:
        """獲取本地圖片信息"""
        full_path = self.base_dir / storage_path
        
        if not full_path.exists():
            return None
        
        try:
            stat = full_path.stat()
            
            # 計算ETag
            with open(full_path, 'rb') as f:
                content = f.read()
                etag = hashlib.md5(content).hexdigest()
            
            # 確定內容類型
            suffix = full_path.suffix.lower()
            content_type_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            content_type = content_type_map.get(suffix, 'image/png')
            
            public_url = self.generate_public_url(storage_path)
            
            return StoredImage(
                url=public_url,
                storage_path=storage_path,
                size=stat.st_size,
                content_type=content_type,
                etag=etag,
                last_modified=stat.st_mtime
            )
            
        except Exception as e:
            logger.error(f"獲取本地圖片信息失敗: {storage_path} - {e}")
            return None
    
    async def list_images(self, prefix: str = "") -> List[StoredImage]:
        """列出本地圖片"""
        images = []
        search_path = self.base_dir / prefix if prefix else self.base_dir
        
        try:
            if search_path.is_dir():
                for file_path in search_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                        relative_path = str(file_path.relative_to(self.base_dir))
                        image_info = await self.get_image_info(relative_path)
                        if image_info:
                            images.append(image_info)
        except Exception as e:
            logger.error(f"列出本地圖片失敗: {prefix} - {e}")
        
        return images

class CloudImageStorage(ImageStorage):
    """
    雲端圖片存儲基類
    
    支持Azure Blob Storage, AWS S3, Google Cloud Storage
    """
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化雲端存儲客戶端"""
        if self.config.storage_type == "azure":
            self._initialize_azure_client()
        elif self.config.storage_type == "aws":
            self._initialize_aws_client()
        elif self.config.storage_type == "gcp":
            self._initialize_gcp_client()
        else:
            raise ValueError(f"不支持的存儲類型: {self.config.storage_type}")
    
    def _initialize_azure_client(self):
        """初始化Azure Blob Storage客戶端"""
        try:
            from azure.storage.blob import BlobServiceClient
            
            self.client = BlobServiceClient(
                account_url=f"https://{self.config.access_key}.blob.core.windows.net",
                credential=self.config.secret_key
            )
            logger.info("Azure Blob Storage客戶端初始化成功")
            
        except ImportError:
            logger.error("Azure Storage SDK未安裝: pip install azure-storage-blob")
            raise
        except Exception as e:
            logger.error(f"Azure Blob Storage客戶端初始化失敗: {e}")
            raise
    
    def _initialize_aws_client(self):
        """初始化AWS S3客戶端"""
        try:
            import boto3
            
            self.client = boto3.client(
                's3',
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_key,
                region_name=self.config.region
            )
            logger.info("AWS S3客戶端初始化成功")
            
        except ImportError:
            logger.error("AWS SDK未安裝: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"AWS S3客戶端初始化失敗: {e}")
            raise
    
    def _initialize_gcp_client(self):
        """初始化Google Cloud Storage客戶端"""
        try:
            from google.cloud import storage
            
            self.client = storage.Client()
            logger.info("Google Cloud Storage客戶端初始化成功")
            
        except ImportError:
            logger.error("Google Cloud SDK未安裝: pip install google-cloud-storage")
            raise
        except Exception as e:
            logger.error(f"Google Cloud Storage客戶端初始化失敗: {e}")
            raise
    
    async def store_image(self, optimized_image: OptimizedImage, 
                         filename: str) -> StoredImage:
        """存儲圖片到雲端"""
        
        content_hash = hashlib.md5(optimized_image.image_data).hexdigest()
        storage_path = self.generate_storage_path(filename, content_hash)
        
        try:
            if self.config.storage_type == "azure":
                return await self._store_to_azure(optimized_image, storage_path, content_hash)
            elif self.config.storage_type == "aws":
                return await self._store_to_aws(optimized_image, storage_path, content_hash)
            elif self.config.storage_type == "gcp":
                return await self._store_to_gcp(optimized_image, storage_path, content_hash)
            else:
                raise ValueError(f"不支持的存儲類型: {self.config.storage_type}")
                
        except Exception as e:
            logger.error(f"雲端圖片存儲失敗: {storage_path} - {e}")
            raise
    
    async def _store_to_azure(self, optimized_image: OptimizedImage, 
                             storage_path: str, content_hash: str) -> StoredImage:
        """存儲到Azure Blob Storage"""
        
        blob_client = self.client.get_blob_client(
            container=self.config.bucket_name,
            blob=storage_path
        )
        
        # 檢查blob是否已存在
        if await blob_client.exists():
            logger.debug(f"Azure blob已存在: {storage_path}")
            return await self.get_image_info(storage_path)
        
        # 上傳blob
        content_type = f"image/{optimized_image.format.lower()}"
        if optimized_image.format.upper() == "JPEG":
            content_type = "image/jpeg"
        
        await blob_client.upload_blob(
            optimized_image.image_data,
            content_type=content_type,
            metadata={
                "optimization_applied": ",".join(optimized_image.optimization_applied),
                "compression_ratio": str(optimized_image.compression_ratio),
                "original_size": str(optimized_image.original_size)
            }
        )
        
        public_url = self.generate_public_url(storage_path)
        
        return StoredImage(
            url=public_url,
            storage_path=storage_path,
            size=len(optimized_image.image_data),
            content_type=content_type,
            etag=content_hash,
            last_modified=time.time()
        )
    
    async def _store_to_aws(self, optimized_image: OptimizedImage, 
                           storage_path: str, content_hash: str) -> StoredImage:
        """存儲到AWS S3"""
        
        # 檢查對象是否已存在
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.client.head_object(
                    Bucket=self.config.bucket_name,
                    Key=storage_path
                )
            )
            logger.debug(f"AWS S3對象已存在: {storage_path}")
            return await self.get_image_info(storage_path)
        except:
            pass
        
        # 上傳對象
        content_type = f"image/{optimized_image.format.lower()}"
        if optimized_image.format.upper() == "JPEG":
            content_type = "image/jpeg"
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.put_object(
                Bucket=self.config.bucket_name,
                Key=storage_path,
                Body=optimized_image.image_data,
                ContentType=content_type,
                Metadata={
                    "optimization_applied": ",".join(optimized_image.optimization_applied),
                    "compression_ratio": str(optimized_image.compression_ratio),
                    "original_size": str(optimized_image.original_size)
                }
            )
        )
        
        public_url = self.generate_public_url(storage_path)
        
        return StoredImage(
            url=public_url,
            storage_path=storage_path,
            size=len(optimized_image.image_data),
            content_type=content_type,
            etag=content_hash,
            last_modified=time.time()
        )
    
    async def _store_to_gcp(self, optimized_image: OptimizedImage, 
                           storage_path: str, content_hash: str) -> StoredImage:
        """存儲到Google Cloud Storage"""
        
        bucket = self.client.bucket(self.config.bucket_name)
        blob = bucket.blob(storage_path)
        
        # 檢查blob是否已存在
        if await asyncio.get_event_loop().run_in_executor(None, blob.exists):
            logger.debug(f"GCP blob已存在: {storage_path}")
            return await self.get_image_info(storage_path)
        
        # 上傳blob
        content_type = f"image/{optimized_image.format.lower()}"
        if optimized_image.format.upper() == "JPEG":
            content_type = "image/jpeg"
        
        blob.metadata = {
            "optimization_applied": ",".join(optimized_image.optimization_applied),
            "compression_ratio": str(optimized_image.compression_ratio),
            "original_size": str(optimized_image.original_size)
        }
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: blob.upload_from_string(
                optimized_image.image_data,
                content_type=content_type
            )
        )
        
        public_url = self.generate_public_url(storage_path)
        
        return StoredImage(
            url=public_url,
            storage_path=storage_path,
            size=len(optimized_image.image_data),
            content_type=content_type,
            etag=content_hash,
            last_modified=time.time()
        )
    
    async def store_batch(self, images_with_filenames: List[Tuple[OptimizedImage, str]]) -> List[StoredImage]:
        """批量存儲圖片到雲端"""
        logger.info(f"開始批量雲端存儲 {len(images_with_filenames)} 張圖片")
        
        # 使用並發上傳提高效率
        tasks = []
        for optimized_image, filename in images_with_filenames:
            task = self.store_image(optimized_image, filename)
            tasks.append(task)
        
        # 執行並發上傳
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        stored_images = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                filename = images_with_filenames[i][1]
                logger.warning(f"批量存儲失敗 {filename}: {result}")
            else:
                stored_images.append(result)
        
        logger.info(f"批量雲端存儲完成: {len(stored_images)}/{len(images_with_filenames)} 成功")
        return stored_images
    
    async def delete_image(self, storage_path: str) -> bool:
        """從雲端刪除圖片"""
        try:
            if self.config.storage_type == "azure":
                blob_client = self.client.get_blob_client(
                    container=self.config.bucket_name,
                    blob=storage_path
                )
                await blob_client.delete_blob()
                
            elif self.config.storage_type == "aws":
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.delete_object(
                        Bucket=self.config.bucket_name,
                        Key=storage_path
                    )
                )
                
            elif self.config.storage_type == "gcp":
                bucket = self.client.bucket(self.config.bucket_name)
                blob = bucket.blob(storage_path)
                await asyncio.get_event_loop().run_in_executor(None, blob.delete)
            
            logger.debug(f"雲端圖片刪除成功: {storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"雲端圖片刪除失敗: {storage_path} - {e}")
            return False
    
    async def get_image_info(self, storage_path: str) -> Optional[StoredImage]:
        """獲取雲端圖片信息"""
        # 實現根據不同雲端平台的API獲取圖片信息
        # 這裡提供基本框架，具體實現需要根據各平台API
        return None
    
    async def list_images(self, prefix: str = "") -> List[StoredImage]:
        """列出雲端圖片"""
        # 實現根據不同雲端平台的API列出圖片
        # 這裡提供基本框架，具體實現需要根據各平台API
        return []

def create_image_storage(storage_type: str = "local") -> ImageStorage:
    """
    創建圖片存儲實例
    
    Args:
        storage_type: 存儲類型 ("local", "azure", "aws", "gcp")
        
    Returns:
        圖片存儲實例
    """
    settings = get_settings()
    
    if storage_type == "local":
        config = StorageConfig(
            storage_type="local",
            base_path=settings.image_storage_path,
            public_url_base=settings.image_public_url_base
        )
        return LocalImageStorage(config)
    
    elif storage_type == "azure":
        config = StorageConfig(
            storage_type="azure",
            base_path="images",
            access_key=settings.azure_storage_account,
            secret_key=settings.azure_storage_key,
            bucket_name=settings.azure_container_name,
            cdn_domain=settings.azure_cdn_domain
        )
        return CloudImageStorage(config)
    
    elif storage_type == "aws":
        config = StorageConfig(
            storage_type="aws",
            base_path="images",
            access_key=settings.aws_access_key,
            secret_key=settings.aws_secret_key,
            bucket_name=settings.aws_bucket_name,
            region=settings.aws_region,
            cdn_domain=settings.aws_cloudfront_domain
        )
        return CloudImageStorage(config)
    
    elif storage_type == "gcp":
        config = StorageConfig(
            storage_type="gcp",
            base_path="images",
            bucket_name=settings.gcp_bucket_name,
            cdn_domain=settings.gcp_cdn_domain
        )
        return CloudImageStorage(config)
    
    else:
        raise ValueError(f"不支持的存儲類型: {storage_type}")
