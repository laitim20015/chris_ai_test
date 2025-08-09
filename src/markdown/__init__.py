"""
Markdown生成模組

此模組負責將解析後的文檔內容和圖文關聯信息轉換為標準化的Markdown格式。
支持模板系統、URL嵌入和元數據管理。

主要功能：
- Markdown文檔生成
- 圖片URL嵌入
- 關聯信息元數據
- 模板化輸出
- 格式驗證
"""

from .generator import MarkdownGenerator, MarkdownTemplate
from .formatter import MarkdownFormatter, URLEmbedder

__all__ = [
    "MarkdownGenerator",
    "MarkdownTemplate", 
    "MarkdownFormatter",
    "URLEmbedder"
]

__version__ = "1.0.0"
