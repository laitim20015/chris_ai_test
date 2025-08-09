"""
文本處理工具
Text Processing Utilities

提供全面的文本處理功能，包括：
- 文本清理和標準化
- 語言檢測和編碼處理
- 文本分塊和關鍵詞提取
- 相似度計算
- HTML標籤處理和URL提取
"""

import re
import unicodedata
from typing import List, Dict, Any, Optional, Tuple, Union
from urllib.parse import urlparse
import html
from difflib import SequenceMatcher
from src.config.logging_config import get_logger, log_performance

logger = get_logger("text_utils")

class TextProcessor:
    """文本處理器類"""
    
    def __init__(self):
        """初始化文本處理器"""
        # 常用正則表達式模式
        self.patterns = {
            'html_tags': re.compile(r'<[^>]+>'),
            'urls': re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'),
            'emails': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'whitespace': re.compile(r'\s+'),
            'punctuation': re.compile(r'[^\w\s]'),
            'numbers': re.compile(r'\d+'),
            'chinese': re.compile(r'[\u4e00-\u9fff]+'),
            'english': re.compile(r'[a-zA-Z]+'),
        }
        
        # 停用詞列表（簡化版）
        self.stop_words_en = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
            'had', 'what', 'said', 'each', 'which', 'she', 'do', 'how', 'their'
        }
        
        self.stop_words_zh = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
            '一', '一個', '上', '也', '很', '到', '說', '要', '去', '你', '會',
            '著', '沒有', '看', '好', '自己', '這', '那', '裡', '把', '被'
        }

@log_performance("clean_text")
def clean_text(text: str, 
               remove_html: bool = True,
               remove_urls: bool = False,
               normalize_whitespace: bool = True,
               remove_extra_punctuation: bool = False) -> str:
    """
    清理文本內容
    
    Args:
        text: 原始文本
        remove_html: 是否移除HTML標籤
        remove_urls: 是否移除URL
        normalize_whitespace: 是否標準化空白字符
        remove_extra_punctuation: 是否移除多餘標點符號
        
    Returns:
        str: 清理後的文本
    """
    if not text:
        return ""
    
    processor = TextProcessor()
    cleaned_text = text
    
    # 移除HTML標籤
    if remove_html:
        cleaned_text = processor.patterns['html_tags'].sub('', cleaned_text)
        cleaned_text = html.unescape(cleaned_text)
    
    # 移除URL
    if remove_urls:
        cleaned_text = processor.patterns['urls'].sub('', cleaned_text)
    
    # 標準化Unicode
    cleaned_text = unicodedata.normalize('NFKC', cleaned_text)
    
    # 標準化空白字符
    if normalize_whitespace:
        cleaned_text = processor.patterns['whitespace'].sub(' ', cleaned_text)
        cleaned_text = cleaned_text.strip()
    
    # 移除多餘標點符號
    if remove_extra_punctuation:
        # 保留句號、逗號、感嘆號、問號等基本標點
        cleaned_text = re.sub(r'[^\w\s\u4e00-\u9fff。，！？；：""''（）【】]', '', cleaned_text)
    
    logger.debug(f"文本清理完成，原長度: {len(text)}, 清理後長度: {len(cleaned_text)}")
    return cleaned_text

def extract_sentences(text: str, language: str = "auto") -> List[str]:
    """
    提取句子
    
    Args:
        text: 文本內容
        language: 語言類型 ("auto", "en", "zh")
        
    Returns:
        List[str]: 句子列表
    """
    if not text:
        return []
    
    # 自動檢測語言
    if language == "auto":
        language = detect_language(text)
    
    if language == "zh":
        # 中文句子分割
        sentence_endings = r'[。！？；]'
        sentences = re.split(sentence_endings, text)
    else:
        # 英文句子分割
        sentence_endings = r'[.!?;]'
        sentences = re.split(sentence_endings, text)
    
    # 清理和過濾句子
    sentences = [s.strip() for s in sentences if s.strip()]
    
    logger.debug(f"句子提取完成，共提取 {len(sentences)} 個句子")
    return sentences

def detect_language(text: str) -> str:
    """
    檢測文本語言
    
    Args:
        text: 文本內容
        
    Returns:
        str: 語言代碼 ("zh", "en", "mixed", "unknown")
    """
    if not text:
        return "unknown"
    
    processor = TextProcessor()
    
    # 統計中文字符
    chinese_chars = len(processor.patterns['chinese'].findall(text))
    
    # 統計英文字符
    english_chars = len(processor.patterns['english'].findall(text))
    
    total_chars = chinese_chars + english_chars
    
    if total_chars == 0:
        return "unknown"
    
    chinese_ratio = chinese_chars / total_chars
    english_ratio = english_chars / total_chars
    
    if chinese_ratio > 0.6:
        return "zh"
    elif english_ratio > 0.6:
        return "en"
    elif chinese_ratio > 0.2 and english_ratio > 0.2:
        return "mixed"
    else:
        return "unknown"

def normalize_whitespace(text: str) -> str:
    """
    標準化空白字符
    
    Args:
        text: 原始文本
        
    Returns:
        str: 標準化後的文本
    """
    if not text:
        return ""
    
    # 替換所有空白字符為單個空格
    normalized = re.sub(r'\s+', ' ', text)
    
    # 移除首尾空白
    normalized = normalized.strip()
    
    return normalized

def remove_html_tags(text: str) -> str:
    """
    移除HTML標籤
    
    Args:
        text: 包含HTML的文本
        
    Returns:
        str: 移除HTML標籤後的文本
    """
    if not text:
        return ""
    
    # 移除HTML標籤
    clean_text = re.sub(r'<[^>]+>', '', text)
    
    # 解碼HTML實體
    clean_text = html.unescape(clean_text)
    
    return clean_text

def extract_urls(text: str) -> List[str]:
    """
    提取文本中的URL
    
    Args:
        text: 文本內容
        
    Returns:
        List[str]: URL列表
    """
    if not text:
        return []
    
    processor = TextProcessor()
    urls = processor.patterns['urls'].findall(text)
    
    # 驗證和清理URL
    valid_urls = []
    for url in urls:
        try:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                valid_urls.append(url)
        except:
            continue
    
    logger.debug(f"URL提取完成，共找到 {len(valid_urls)} 個有效URL")
    return valid_urls

@log_performance("calculate_text_similarity")
def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    計算文本相似度
    
    Args:
        text1: 第一個文本
        text2: 第二個文本
        
    Returns:
        float: 相似度分數 (0-1)
    """
    if not text1 or not text2:
        return 0.0
    
    # 清理文本
    clean_text1 = clean_text(text1.lower())
    clean_text2 = clean_text(text2.lower())
    
    # 使用SequenceMatcher計算相似度
    similarity = SequenceMatcher(None, clean_text1, clean_text2).ratio()
    
    logger.debug(f"文本相似度計算完成，相似度: {similarity:.3f}")
    return similarity

def split_into_chunks(text: str, 
                     chunk_size: int = 1000, 
                     overlap: int = 200,
                     preserve_sentences: bool = True) -> List[str]:
    """
    將文本分割成塊
    
    Args:
        text: 原始文本
        chunk_size: 塊大小（字符數）
        overlap: 重疊字符數
        preserve_sentences: 是否保持句子完整性
        
    Returns:
        List[str]: 文本塊列表
    """
    if not text:
        return []
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    
    if preserve_sentences:
        # 先分割成句子
        sentences = extract_sentences(text)
        
        current_chunk = ""
        for sentence in sentences:
            # 檢查添加當前句子是否會超過塊大小
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                # 如果當前塊不為空，保存它
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # 如果單個句子就超過塊大小，強制分割
                if len(sentence) > chunk_size:
                    # 分割長句子
                    for i in range(0, len(sentence), chunk_size - overlap):
                        chunk_part = sentence[i:i + chunk_size]
                        chunks.append(chunk_part)
                    current_chunk = ""
                else:
                    current_chunk = sentence
        
        # 添加最後一個塊
        if current_chunk:
            chunks.append(current_chunk.strip())
    
    else:
        # 簡單字符分割
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            chunks.append(chunk)
    
    logger.debug(f"文本分塊完成，原長度: {len(text)}, 分成 {len(chunks)} 塊")
    return chunks

def count_words(text: str, language: str = "auto") -> Dict[str, int]:
    """
    統計詞語數量
    
    Args:
        text: 文本內容
        language: 語言類型
        
    Returns:
        Dict[str, int]: 詞語統計結果
    """
    if not text:
        return {}
    
    if language == "auto":
        language = detect_language(text)
    
    # 清理文本
    clean = clean_text(text, remove_html=True, normalize_whitespace=True)
    
    if language == "zh":
        # 中文按字符統計（簡化版）
        words = list(clean)
        words = [w for w in words if w.strip() and not w.isspace()]
    else:
        # 英文按單詞統計
        words = re.findall(r'\b\w+\b', clean.lower())
    
    # 統計詞頻
    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    logger.debug(f"詞語統計完成，共 {len(word_counts)} 個唯一詞語")
    return word_counts

def extract_keywords(text: str, 
                    top_k: int = 10, 
                    min_length: int = 2,
                    remove_stop_words: bool = True) -> List[Tuple[str, int]]:
    """
    提取關鍵詞
    
    Args:
        text: 文本內容
        top_k: 返回前K個關鍵詞
        min_length: 最小詞長
        remove_stop_words: 是否移除停用詞
        
    Returns:
        List[Tuple[str, int]]: (關鍵詞, 頻次) 列表
    """
    if not text:
        return []
    
    # 統計詞頻
    word_counts = count_words(text)
    
    if remove_stop_words:
        processor = TextProcessor()
        language = detect_language(text)
        
        if language == "zh":
            stop_words = processor.stop_words_zh
        else:
            stop_words = processor.stop_words_en
        
        # 移除停用詞
        filtered_counts = {
            word: count for word, count in word_counts.items()
            if word.lower() not in stop_words and len(word) >= min_length
        }
    else:
        filtered_counts = {
            word: count for word, count in word_counts.items()
            if len(word) >= min_length
        }
    
    # 按頻次排序
    keywords = sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True)
    
    # 返回前K個
    result = keywords[:top_k]
    
    logger.debug(f"關鍵詞提取完成，提取 {len(result)} 個關鍵詞")
    return result

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
            text.decode(encoding)
        elif isinstance(text, str):
            text.encode(encoding)
        
        return True, ""
        
    except UnicodeError as e:
        return False, f"編碼錯誤: {str(e)}"

def sanitize_text_input(text: str, 
                       max_length: int = 10000,
                       allow_html: bool = False) -> str:
    """
    清理和安全化文本輸入
    
    Args:
        text: 輸入文本
        max_length: 最大長度
        allow_html: 是否允許HTML
        
    Returns:
        str: 清理後的文本
    """
    if not text:
        return ""
    
    # 截斷過長文本
    if len(text) > max_length:
        text = text[:max_length]
    
    # 移除控制字符
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # 處理HTML
    if not allow_html:
        text = remove_html_tags(text)
    
    # 標準化空白
    text = normalize_whitespace(text)
    
    return text

# 全局文本處理器實例
_global_processor: Optional[TextProcessor] = None

def get_text_processor() -> TextProcessor:
    """
    獲取全局文本處理器實例
    
    Returns:
        TextProcessor: 文本處理器實例
    """
    global _global_processor
    if _global_processor is None:
        _global_processor = TextProcessor()
    return _global_processor
