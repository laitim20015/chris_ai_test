"""
文件操作工具
File Utilities

提供安全可靠的文件操作功能，包括：
- 文件信息獲取和驗證
- 安全的文件讀寫操作
- 文件格式檢測和驗證
- 唯一文件名生成
- 臨時文件清理
- 文件哈希計算
"""

import os
import hashlib
import mimetypes
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime
import magic
import aiofiles
from src.config.logging_config import get_logger, log_performance

logger = get_logger("file_utils")

def ensure_directory_exists(directory_path: Union[str, Path]) -> None:
    """
    確保目錄存在，如果不存在則創建
    
    Args:
        directory_path: 目錄路徑
    """
    path = Path(directory_path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"目錄已確保存在: {path}")
    except Exception as e:
        logger.error(f"創建目錄失敗: {path}, 錯誤: {e}")
        raise

def get_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
    """
    計算文件哈希值
    
    Args:
        file_path: 文件路徑
        algorithm: 哈希算法 (md5, sha1, sha256)
        
    Returns:
        str: 文件哈希值
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    
    hash_obj = hashlib.new(algorithm.lower())
    
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        file_hash = hash_obj.hexdigest()
        logger.debug(f"文件哈希計算完成: {path}, {algorithm.upper()}: {file_hash}")
        return file_hash
        
    except Exception as e:
        logger.error(f"計算文件哈希失敗: {path}, 錯誤: {e}")
        raise

class FileManager:
    """文件管理器類"""
    
    def __init__(self, base_path: Optional[Union[str, Path]] = None):
        """
        初始化文件管理器
        
        Args:
            base_path: 基礎路徑，如果為None則使用當前目錄
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.temp_files: List[Path] = []
        
    def create_temp_file(self, suffix: str = "", prefix: str = "temp_") -> Path:
        """
        創建臨時文件
        
        Args:
            suffix: 文件後綴
            prefix: 文件前綴
            
        Returns:
            Path: 臨時文件路徑
        """
        temp_file = Path(tempfile.mktemp(suffix=suffix, prefix=prefix))
        self.temp_files.append(temp_file)
        logger.debug(f"創建臨時文件: {temp_file}")
        return temp_file
    
    def cleanup_temp_files(self) -> int:
        """
        清理臨時文件
        
        Returns:
            int: 清理的文件數量
        """
        cleaned_count = 0
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    cleaned_count += 1
                    logger.debug(f"清理臨時文件: {temp_file}")
            except Exception as e:
                logger.error(f"清理臨時文件失敗: {temp_file}, 錯誤: {e}")
        
        self.temp_files.clear()
        logger.info(f"清理臨時文件完成，共清理 {cleaned_count} 個文件")
        return cleaned_count
    
    def __del__(self):
        """析構函數，自動清理臨時文件"""
        if hasattr(self, 'temp_files'):
            self.cleanup_temp_files()

def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    獲取文件詳細信息
    
    Args:
        file_path: 文件路徑
        
    Returns:
        Dict[str, Any]: 文件信息字典
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    stat = file_path.stat()
    
    # 獲取MIME類型
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        try:
            mime_type = magic.from_file(str(file_path), mime=True)
        except:
            mime_type = "application/octet-stream"
    
    return {
        "path": str(file_path.absolute()),
        "name": file_path.name,
        "stem": file_path.stem,
        "suffix": file_path.suffix,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / 1024 / 1024, 2),
        "mime_type": mime_type,
        "created_time": datetime.fromtimestamp(stat.st_ctime),
        "modified_time": datetime.fromtimestamp(stat.st_mtime),
        "accessed_time": datetime.fromtimestamp(stat.st_atime),
        "is_file": file_path.is_file(),
        "is_dir": file_path.is_dir(),
        "is_symlink": file_path.is_symlink(),
        "permissions": oct(stat.st_mode)[-3:],
    }

def validate_file_format(file_path: Union[str, Path], 
                        allowed_formats: List[str]) -> Tuple[bool, str]:
    """
    驗證文件格式
    
    Args:
        file_path: 文件路徑
        allowed_formats: 允許的格式列表
        
    Returns:
        Tuple[bool, str]: (是否有效, 檢測到的格式)
    """
    file_path = Path(file_path)
    
    # 檢查文件擴展名
    suffix = file_path.suffix.lower().lstrip('.')
    
    # 檢查MIME類型
    mime_type, _ = mimetypes.guess_type(str(file_path))
    
    # 格式映射
    format_map = {
        'pdf': ['pdf'],
        'word': ['doc', 'docx'],
        'powerpoint': ['ppt', 'pptx'],
        'image': ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff']
    }
    
    detected_format = None
    for fmt, extensions in format_map.items():
        if suffix in extensions:
            detected_format = fmt
            break
    
    if not detected_format:
        detected_format = suffix
    
    is_valid = detected_format in allowed_formats or suffix in allowed_formats
    
    logger.debug(f"文件格式驗證: {file_path.name}, 檢測格式: {detected_format}, 有效: {is_valid}")
    
    return is_valid, detected_format

@log_performance("calculate_file_hash")
def calculate_file_hash(file_path: Union[str, Path], 
                       algorithm: str = "sha256") -> str:
    """
    計算文件哈希值
    
    Args:
        file_path: 文件路徑
        algorithm: 哈希算法 (md5, sha1, sha256, sha512)
        
    Returns:
        str: 哈希值
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    
    hash_value = hash_obj.hexdigest()
    logger.debug(f"文件哈希計算完成: {file_path.name}, {algorithm}: {hash_value[:16]}...")
    
    return hash_value

def create_unique_filename(base_name: str, extension: str, 
                          directory: Union[str, Path] = ".") -> str:
    """
    創建唯一文件名
    
    Args:
        base_name: 基礎文件名
        extension: 文件擴展名
        directory: 目標目錄
        
    Returns:
        str: 唯一文件名
    """
    directory = Path(directory)
    extension = extension.lstrip('.')
    
    # 清理文件名
    base_name = "".join(c for c in base_name if c.isalnum() or c in "._- ")
    base_name = base_name.strip()
    
    if not base_name:
        base_name = "untitled"
    
    # 添加時間戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    counter = 0
    while True:
        if counter == 0:
            filename = f"{base_name}_{timestamp}.{extension}"
        else:
            filename = f"{base_name}_{timestamp}_{counter:03d}.{extension}"
        
        full_path = directory / filename
        if not full_path.exists():
            logger.debug(f"生成唯一文件名: {filename}")
            return filename
        
        counter += 1
        if counter > 999:
            raise RuntimeError("無法生成唯一文件名")

def safe_file_read(file_path: Union[str, Path], 
                  encoding: str = "utf-8", 
                  max_size_mb: int = 100) -> str:
    """
    安全讀取文件內容
    
    Args:
        file_path: 文件路徑
        encoding: 文件編碼
        max_size_mb: 最大文件大小限制（MB）
        
    Returns:
        str: 文件內容
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 檢查文件大小
    file_size_mb = file_path.stat().st_size / 1024 / 1024
    if file_size_mb > max_size_mb:
        raise ValueError(f"文件太大: {file_size_mb:.2f}MB > {max_size_mb}MB")
    
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        logger.debug(f"安全讀取文件: {file_path.name}, 大小: {file_size_mb:.2f}MB")
        return content
        
    except UnicodeDecodeError as e:
        logger.error(f"文件編碼錯誤: {file_path}, 錯誤: {e}")
        raise ValueError(f"文件編碼錯誤，無法使用 {encoding} 解碼")

def safe_file_write(file_path: Union[str, Path], 
                   content: str, 
                   encoding: str = "utf-8",
                   backup: bool = True) -> bool:
    """
    安全寫入文件內容
    
    Args:
        file_path: 文件路徑
        content: 文件內容
        encoding: 文件編碼
        backup: 是否備份現有文件
        
    Returns:
        bool: 是否寫入成功
    """
    file_path = Path(file_path)
    
    # 創建目錄
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 備份現有文件
    if backup and file_path.exists():
        backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
        shutil.copy2(file_path, backup_path)
        logger.debug(f"備份文件: {backup_path}")
    
    try:
        # 先寫入臨時文件
        temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
        
        with open(temp_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        # 原子性重命名
        temp_path.replace(file_path)
        
        logger.debug(f"安全寫入文件: {file_path.name}, 大小: {len(content)} 字符")
        return True
        
    except Exception as e:
        logger.error(f"文件寫入失敗: {file_path}, 錯誤: {e}")
        # 清理臨時文件
        temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
        if temp_path.exists():
            temp_path.unlink()
        return False

async def async_file_read(file_path: Union[str, Path], 
                         encoding: str = "utf-8") -> str:
    """
    異步讀取文件內容
    
    Args:
        file_path: 文件路徑
        encoding: 文件編碼
        
    Returns:
        str: 文件內容
    """
    async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
        content = await f.read()
    
    logger.debug(f"異步讀取文件: {Path(file_path).name}")
    return content

async def async_file_write(file_path: Union[str, Path], 
                          content: str, 
                          encoding: str = "utf-8") -> bool:
    """
    異步寫入文件內容
    
    Args:
        file_path: 文件路徑
        content: 文件內容
        encoding: 文件編碼
        
    Returns:
        bool: 是否寫入成功
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
            await f.write(content)
        
        logger.debug(f"異步寫入文件: {file_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"異步文件寫入失敗: {file_path}, 錯誤: {e}")
        return False

def cleanup_temp_files(temp_dir: Union[str, Path] = None, 
                      max_age_hours: int = 24) -> int:
    """
    清理臨時文件
    
    Args:
        temp_dir: 臨時目錄，如果為None則使用系統臨時目錄
        max_age_hours: 最大文件年齡（小時）
        
    Returns:
        int: 清理的文件數量
    """
    if temp_dir is None:
        temp_dir = Path(tempfile.gettempdir())
    else:
        temp_dir = Path(temp_dir)
    
    if not temp_dir.exists():
        return 0
    
    cleaned_count = 0
    current_time = datetime.now().timestamp()
    max_age_seconds = max_age_hours * 3600
    
    for file_path in temp_dir.iterdir():
        if file_path.is_file():
            try:
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    cleaned_count += 1
                    logger.debug(f"清理過期臨時文件: {file_path.name}")
            except Exception as e:
                logger.error(f"清理臨時文件失敗: {file_path}, 錯誤: {e}")
    
    logger.info(f"臨時文件清理完成，共清理 {cleaned_count} 個文件")
    return cleaned_count

def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """
    獲取文件大小（MB）
    
    Args:
        file_path: 文件路徑
        
    Returns:
        float: 文件大小（MB）
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / 1024 / 1024
    return round(size_mb, 2)

def is_file_accessible(file_path: Union[str, Path], 
                      check_read: bool = True, 
                      check_write: bool = False) -> bool:
    """
    檢查文件是否可訪問
    
    Args:
        file_path: 文件路徑
        check_read: 檢查讀權限
        check_write: 檢查寫權限
        
    Returns:
        bool: 是否可訪問
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    try:
        if check_read and not os.access(file_path, os.R_OK):
            return False
        
        if check_write and not os.access(file_path, os.W_OK):
            return False
        
        return True
        
    except Exception:
        return False

# 全局文件管理器實例
_global_file_manager: Optional[FileManager] = None

def get_file_manager() -> FileManager:
    """
    獲取全局文件管理器實例
    
    Returns:
        FileManager: 文件管理器實例
    """
    global _global_file_manager
    if _global_file_manager is None:
        _global_file_manager = FileManager()
    return _global_file_manager

