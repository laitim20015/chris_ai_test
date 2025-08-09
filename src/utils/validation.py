"""
數據驗證工具
Data Validation Utilities

提供全面的數據驗證功能，包括：
- 文件路徑和格式驗證
- 文本編碼和內容驗證
- URL和電子郵件格式驗證
- 安全性檢查和數據清理
- JSON結構驗證
"""

import re
import json
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse
import magic
from src.config.logging_config import get_logger

logger = get_logger("validation")

class DataValidator:
    """數據驗證器類"""
    
    def __init__(self):
        """初始化數據驗證器"""
        # 常用驗證模式
        self.patterns = {
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'url': re.compile(r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/[^?\s]*)?(?:\?[^#\s]*)?(?:#[^\s]*)?$'),
            'filename': re.compile(r'^[^<>:"/\\|?*\x00-\x1f]+$'),
            'chinese': re.compile(r'[\u4e00-\u9fff]'),
            'english': re.compile(r'[a-zA-Z]'),
            'numeric': re.compile(r'^\d+$'),
            'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
        }
        
        # 危險文件擴展名
        self.dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.ps1', '.sh', '.php', '.asp', '.jsp', '.py'
        }
        
        # 允許的圖像格式
        self.image_formats = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
        }
        
        # 允許的文檔格式
        self.document_formats = {
            '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt', '.md'
        }

def validate_file_path(file_path: Union[str, Path]) -> bool:
    """
    驗證文件路徑是否有效
    
    Args:
        file_path: 文件路徑
        
    Returns:
        bool: 路徑是否有效
    """
    try:
        path = Path(file_path)
        
        # 檢查路徑是否存在
        if not path.exists():
            logger.debug(f"文件路徑不存在: {file_path}")
            return False
        
        # 檢查是否為文件
        if not path.is_file():
            logger.debug(f"路徑不是文件: {file_path}")
            return False
        
        # 檢查是否可讀
        if not path.stat().st_size > 0:
            logger.debug(f"文件為空: {file_path}")
            return False
        
        logger.debug(f"文件路徑驗證通過: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"文件路徑驗證失敗: {file_path}, 錯誤: {e}")
        return False

def validate_image_format(file_path: Union[str, Path]) -> Tuple[bool, str]:
    """
    驗證圖像格式
    
    Args:
        file_path: 圖像文件路徑
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)
    """
    path = Path(file_path)
    validator = DataValidator()
    
    # 檢查文件擴展名
    if path.suffix.lower() not in validator.image_formats:
        return False, f"不支持的圖像格式: {path.suffix}"
    
    # 檢查MIME類型
    try:
        mime_type = magic.from_file(str(path), mime=True)
        if not mime_type.startswith('image/'):
            return False, f"文件不是圖像: MIME類型為 {mime_type}"
    except Exception as e:
        logger.warning(f"MIME類型檢查失敗: {e}")
    
    # 嘗試打開圖像驗證
    try:
        from PIL import Image
        with Image.open(path) as img:
            img.verify()
        return True, ""
    except Exception as e:
        return False, f"圖像文件損壞: {str(e)}"

def validate_text_encoding(text: Union[str, bytes], 
                          encoding: str = "utf-8") -> Tuple[bool, str]:
    """
    驗證文本編碼
    
    Args:
        text: 文本內容
        encoding: 預期編碼
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)
    """
    try:
        if isinstance(text, bytes):
            decoded = text.decode(encoding)
        elif isinstance(text, str):
            encoded = text.encode(encoding)
            decoded = encoded.decode(encoding)
        else:
            return False, "無效的文本類型"
        
        # 檢查是否包含控制字符
        control_chars = re.findall(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', decoded)
        if control_chars:
            return False, f"文本包含控制字符: {len(control_chars)} 個"
        
        return True, ""
        
    except UnicodeError as e:
        return False, f"編碼錯誤: {str(e)}"
    except Exception as e:
        return False, f"驗證失敗: {str(e)}"

def validate_json_structure(data: str, 
                          expected_schema: Optional[Dict] = None) -> Tuple[bool, str, Any]:
    """
    驗證JSON結構
    
    Args:
        data: JSON字符串
        expected_schema: 期望的schema結構
        
    Returns:
        Tuple[bool, str, Any]: (是否有效, 錯誤信息, 解析後的數據)
    """
    try:
        # 解析JSON
        parsed_data = json.loads(data)
        
        # 如果提供了schema，進行驗證
        if expected_schema:
            if not isinstance(parsed_data, dict):
                return False, "JSON必須是對象格式", None
            
            # 簡單的schema驗證（檢查必需字段）
            if 'required' in expected_schema:
                missing_fields = []
                for field in expected_schema['required']:
                    if field not in parsed_data:
                        missing_fields.append(field)
                
                if missing_fields:
                    return False, f"缺少必需字段: {missing_fields}", None
        
        return True, "", parsed_data
        
    except json.JSONDecodeError as e:
        return False, f"JSON格式錯誤: {str(e)}", None
    except Exception as e:
        return False, f"驗證失敗: {str(e)}", None

def validate_url_format(url: str) -> Tuple[bool, str]:
    """
    驗證URL格式
    
    Args:
        url: URL字符串
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)
    """
    validator = DataValidator()
    
    # 正則表達式驗證
    if not validator.patterns['url'].match(url):
        return False, "URL格式不正確"
    
    try:
        # 使用urlparse進一步驗證
        parsed = urlparse(url)
        
        if not parsed.scheme:
            return False, "URL缺少協議（http/https）"
        
        if not parsed.netloc:
            return False, "URL缺少主機名"
        
        if parsed.scheme not in ['http', 'https']:
            return False, f"不支持的協議: {parsed.scheme}"
        
        return True, ""
        
    except Exception as e:
        return False, f"URL解析失敗: {str(e)}"

def validate_email_format(email: str) -> Tuple[bool, str]:
    """
    驗證電子郵件格式
    
    Args:
        email: 電子郵件地址
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)
    """
    validator = DataValidator()
    
    if not email or not isinstance(email, str):
        return False, "電子郵件地址不能為空"
    
    # 長度檢查
    if len(email) > 254:  # RFC 5321 限制
        return False, "電子郵件地址太長"
    
    # 正則表達式驗證
    if not validator.patterns['email'].match(email):
        return False, "電子郵件格式不正確"
    
    # 分割本地部分和域名部分
    try:
        local, domain = email.split('@')
        
        # 本地部分檢查
        if len(local) > 64:  # RFC 5321 限制
            return False, "電子郵件本地部分太長"
        
        # 域名部分檢查
        if len(domain) > 253:  # RFC 1034 限制
            return False, "電子郵件域名太長"
        
        # 檢查域名格式
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            return False, "域名格式不正確"
        
        for part in domain_parts:
            if not part or len(part) > 63:
                return False, "域名部分格式不正確"
        
        return True, ""
        
    except ValueError:
        return False, "電子郵件格式錯誤"

def sanitize_filename(filename: str, 
                     max_length: int = 255,
                     replace_char: str = "_") -> str:
    """
    清理文件名，移除危險字符
    
    Args:
        filename: 原始文件名
        max_length: 最大長度
        replace_char: 替換字符
        
    Returns:
        str: 清理後的文件名
    """
    if not filename:
        return "untitled"
    
    # 移除危險字符
    dangerous_chars = r'<>:"/\\|?*\x00-\x1f'
    cleaned = re.sub(f'[{re.escape(dangerous_chars)}]', replace_char, filename)
    
    # 移除連續的替換字符
    cleaned = re.sub(f'{re.escape(replace_char)}+', replace_char, cleaned)
    
    # 移除首尾的替換字符和空格
    cleaned = cleaned.strip(f'{replace_char} ')
    
    # 截斷過長的文件名
    if len(cleaned) > max_length:
        name, ext = Path(cleaned).stem, Path(cleaned).suffix
        max_name_length = max_length - len(ext)
        if max_name_length > 0:
            cleaned = name[:max_name_length] + ext
        else:
            cleaned = cleaned[:max_length]
    
    # 確保不為空
    if not cleaned:
        cleaned = "untitled"
    
    logger.debug(f"文件名清理: {filename} -> {cleaned}")
    return cleaned

def sanitize_text_input(text: str, 
                       max_length: int = 10000,
                       allow_html: bool = False,
                       remove_control_chars: bool = True) -> str:
    """
    清理文本輸入
    
    Args:
        text: 原始文本
        max_length: 最大長度
        allow_html: 是否允許HTML
        remove_control_chars: 是否移除控制字符
        
    Returns:
        str: 清理後的文本
    """
    if not text:
        return ""
    
    # 截斷過長文本
    if len(text) > max_length:
        text = text[:max_length]
    
    # 移除控制字符
    if remove_control_chars:
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # 處理HTML
    if not allow_html:
        # 移除HTML標籤
        text = re.sub(r'<[^>]+>', '', text)
        # 解碼HTML實體
        import html
        text = html.unescape(text)
    
    # 標準化空白字符
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def check_file_safety(file_path: Union[str, Path]) -> Tuple[bool, List[str]]:
    """
    檢查文件安全性
    
    Args:
        file_path: 文件路徑
        
    Returns:
        Tuple[bool, List[str]]: (是否安全, 警告列表)
    """
    path = Path(file_path)
    validator = DataValidator()
    warnings = []
    
    # 檢查文件擴展名
    if path.suffix.lower() in validator.dangerous_extensions:
        warnings.append(f"危險的文件擴展名: {path.suffix}")
    
    # 檢查文件大小（100MB限制）
    try:
        file_size = path.stat().st_size
        if file_size > 100 * 1024 * 1024:  # 100MB
            warnings.append(f"文件過大: {file_size / 1024 / 1024:.1f}MB")
    except:
        warnings.append("無法獲取文件大小")
    
    # 檢查文件名
    if not validator.patterns['filename'].match(path.name):
        warnings.append("文件名包含非法字符")
    
    # 檢查路徑長度
    if len(str(path)) > 260:  # Windows路徑長度限制
        warnings.append("文件路徑過長")
    
    # 檢查是否為隱藏文件
    if path.name.startswith('.'):
        warnings.append("隱藏文件")
    
    is_safe = len(warnings) == 0
    
    if warnings:
        logger.warning(f"文件安全檢查發現問題: {path.name}, 警告: {warnings}")
    else:
        logger.debug(f"文件安全檢查通過: {path.name}")
    
    return is_safe, warnings

def validate_association_weights(weights: Dict[str, float]) -> Tuple[bool, str]:
    """
    驗證關聯度權重配置是否符合項目規則
    
    Args:
        weights: 權重字典
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)
    """
    # 檢查必需的權重字段
    required_fields = [
        'caption_score', 'spatial_score', 'semantic_score',
        'layout_score', 'proximity_score'
    ]
    
    for field in required_fields:
        if field not in weights:
            return False, f"缺少權重字段: {field}"
        
        if not isinstance(weights[field], (int, float)):
            return False, f"權重必須為數值: {field}"
        
        if weights[field] < 0 or weights[field] > 1:
            return False, f"權重必須在0-1範圍內: {field}"
    
    # 檢查權重總和
    total_weight = sum(weights[field] for field in required_fields)
    if abs(total_weight - 1.0) > 1e-6:
        return False, f"權重總和必須為1.0，當前為: {total_weight}"
    
    # 檢查Caption權重是否最高（項目規則）
    caption_weight = weights['caption_score']
    max_weight = max(weights[field] for field in required_fields)
    
    if caption_weight != max_weight:
        return False, "Caption權重必須為最高（項目規則要求）"
    
    return True, ""

def validate_parser_config(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    驗證解析器配置是否符合項目規則
    
    Args:
        config: 解析器配置字典
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)
    """
    # 檢查PDF解析器優先級
    expected_priority = ["pymupdf", "pymupdf4llm", "unstructured"]
    
    if 'pdf_parsers' in config:
        parsers = config['pdf_parsers']
        if parsers != expected_priority:
            return False, f"PDF解析器優先級必須為: {expected_priority}, 當前為: {parsers}"
    
    # 檢查支持的格式
    if 'supported_formats' in config:
        required_formats = ['pdf', 'docx', 'pptx']
        formats = config['supported_formats']
        
        for fmt in required_formats:
            if fmt not in formats:
                return False, f"必須支持的格式: {fmt}"
    
    return True, ""

def validate_markdown_output(markdown_content: str) -> bool:
    """
    驗證Markdown輸出的基本格式
    
    Args:
        markdown_content: Markdown內容
        
    Returns:
        bool: 是否是有效的Markdown
    """
    if not markdown_content or not isinstance(markdown_content, str):
        logger.warning("Markdown內容為空或不是字符串")
        return False
    
    # 基本格式檢查
    try:
        # 檢查是否包含基本的Markdown元素
        lines = markdown_content.split('\n')
        
        # 至少應該有標題
        has_heading = any(line.strip().startswith('#') for line in lines)
        if not has_heading:
            logger.debug("Markdown缺少標題")
            # 不算錯誤，只是建議
        
        # 檢查圖片語法格式
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        img_matches = re.findall(img_pattern, markdown_content)
        
        # 驗證圖片URL格式
        for alt_text, img_url in img_matches:
            if not img_url.strip():
                logger.warning("發現空的圖片URL")
                return False
        
        # 檢查表格格式
        table_lines = [line for line in lines if '|' in line]
        if table_lines:
            # 簡單檢查表格格式
            for line in table_lines:
                if line.strip().startswith('|') and line.strip().endswith('|'):
                    continue  # 正確格式
                elif '|' in line:
                    continue  # 部分正確格式也可接受
        
        # 檢查是否有無效的控制字符
        control_chars = re.findall(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', markdown_content)
        if control_chars:
            logger.warning(f"Markdown包含控制字符: {len(control_chars)} 個")
            return False
        
        logger.debug("Markdown格式驗證通過")
        return True
        
    except Exception as e:
        logger.error(f"Markdown驗證過程出錯: {e}")
        return False

# 全局驗證器實例
_global_validator: Optional[DataValidator] = None

def get_validator() -> DataValidator:
    """
    獲取全局驗證器實例
    
    Returns:
        DataValidator: 驗證器實例
    """
    global _global_validator
    if _global_validator is None:
        _global_validator = DataValidator()
    return _global_validator

