"""
Markdown格式化工具

提供Markdown內容的格式化、URL嵌入和後處理功能。
"""

import re
import os
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
from pathlib import Path

from ..config.settings import get_settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class URLEmbedder:
    """URL嵌入器 - 處理圖片URL的生成和嵌入"""
    
    def __init__(self):
        self.settings = get_settings()
        logger.info("URL嵌入器初始化完成")
    
    def generate_image_url(
        self, 
        image_id: str, 
        filename: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> str:
        """
        生成圖片URL
        
        Args:
            image_id: 圖片ID
            filename: 原始文件名
            base_url: 基礎URL
            
        Returns:
            完整的圖片URL
        """
        
        # 使用配置中的基礎URL或默認值
        if not base_url:
            base_url = getattr(self.settings.storage, 'base_url', './images/')
        
        # 生成文件名
        if not filename:
            filename = f"{image_id}.png"
        elif not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            filename = f"{filename}.png"
        
        # 組合完整URL
        if base_url.endswith('/'):
            return f"{base_url}{filename}"
        else:
            return f"{base_url}/{filename}"
    
    def replace_local_paths_with_urls(
        self, 
        markdown_content: str, 
        url_mapping: Dict[str, str]
    ) -> str:
        """
        將Markdown中的本地路徑替換為URL
        
        Args:
            markdown_content: 原始Markdown內容
            url_mapping: 本地路徑到URL的映射
            
        Returns:
            更新後的Markdown內容
        """
        
        updated_content = markdown_content
        
        # 正則表達式匹配Markdown圖片語法
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image_path(match):
            alt_text = match.group(1)
            image_path = match.group(2)
            
            # 檢查是否是本地路徑
            if image_path in url_mapping:
                new_url = url_mapping[image_path]
                logger.debug(f"替換圖片路徑: {image_path} -> {new_url}")
                return f"![{alt_text}]({new_url})"
            
            return match.group(0)  # 不變
        
        updated_content = re.sub(img_pattern, replace_image_path, updated_content)
        
        return updated_content
    
    def validate_urls(self, markdown_content: str) -> List[str]:
        """
        驗證Markdown中的URL是否有效
        
        Args:
            markdown_content: Markdown內容
            
        Returns:
            無效URL列表
        """
        
        invalid_urls = []
        
        # 提取所有圖片URL
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(img_pattern, markdown_content)
        
        for alt_text, url in matches:
            if not self._is_valid_url(url):
                invalid_urls.append(url)
        
        return invalid_urls
    
    def _is_valid_url(self, url: str) -> bool:
        """檢查URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) or url.startswith('./')
        except Exception:
            return False


class MarkdownFormatter:
    """Markdown格式化器 - 提供內容格式化和後處理功能"""
    
    def __init__(self):
        self.settings = get_settings()
        self.url_embedder = URLEmbedder()
        logger.info("Markdown格式化器初始化完成")
    
    def format_content(
        self, 
        markdown_content: str,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        格式化Markdown內容
        
        Args:
            markdown_content: 原始Markdown內容
            options: 格式化選項
            
        Returns:
            格式化後的Markdown內容
        """
        
        if not options:
            options = {}
        
        content = markdown_content
        
        # 應用各種格式化規則
        if options.get('normalize_whitespace', True):
            content = self._normalize_whitespace(content)
        
        if options.get('fix_line_endings', True):
            content = self._fix_line_endings(content)
        
        if options.get('add_table_formatting', True):
            content = self._format_tables(content)
        
        if options.get('add_code_highlighting', False):
            content = self._add_code_highlighting(content)
        
        if options.get('optimize_headings', True):
            content = self._optimize_headings(content)
        
        return content
    
    def _normalize_whitespace(self, content: str) -> str:
        """標準化空白字符"""
        
        # 移除行尾空格
        content = re.sub(r' +$', '', content, flags=re.MULTILINE)
        
        # 標準化多個空行為最多兩個空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 確保文檔結尾有且僅有一個換行符
        content = content.rstrip() + '\n'
        
        return content
    
    def _fix_line_endings(self, content: str) -> str:
        """修復行結束符"""
        # 統一使用\n作為行結束符
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        return content
    
    def _format_tables(self, content: str) -> str:
        """改進表格格式"""
        
        # 查找表格
        table_pattern = r'(\|.+\|\n\|[-\s|]+\|\n(?:\|.+\|\n)*)'
        
        def format_table(match):
            table_content = match.group(1)
            lines = table_content.strip().split('\n')
            
            if len(lines) < 2:
                return table_content
            
            # 分析列數
            header_cols = len([col for col in lines[0].split('|') if col.strip()])
            
            formatted_lines = []
            for line in lines:
                cols = [col.strip() for col in line.split('|')]
                # 確保列數一致
                while len(cols) < header_cols + 1:  # +1 for empty start/end
                    cols.append('')
                
                formatted_line = '| ' + ' | '.join(cols[1:-1]) + ' |'
                formatted_lines.append(formatted_line)
            
            return '\n'.join(formatted_lines) + '\n'
        
        return re.sub(table_pattern, format_table, content, flags=re.MULTILINE)
    
    def _add_code_highlighting(self, content: str) -> str:
        """添加代碼語法高亮"""
        
        # 檢測可能的代碼塊並添加語言標識
        code_patterns = {
            r'```\n((?:def |class |import |from ).+?)```': 'python',
            r'```\n((?:function |var |const |let ).+?)```': 'javascript',
            r'```\n((?:SELECT |INSERT |UPDATE |DELETE ).+?)```': 'sql',
        }
        
        for pattern, language in code_patterns.items():
            content = re.sub(
                pattern,
                f'```{language}\n\\1```',
                content,
                flags=re.IGNORECASE | re.DOTALL
            )
        
        return content
    
    def _optimize_headings(self, content: str) -> str:
        """優化標題結構"""
        
        lines = content.split('\n')
        optimized_lines = []
        
        for i, line in enumerate(lines):
            # 檢查是否是標題
            if line.startswith('#'):
                # 確保標題前後有空行（除非是文檔開始）
                if i > 0 and lines[i-1].strip() != '':
                    if optimized_lines and optimized_lines[-1].strip() != '':
                        optimized_lines.append('')
                
                optimized_lines.append(line)
                
                # 確保標題後有空行
                if i < len(lines) - 1 and lines[i+1].strip() != '':
                    optimized_lines.append('')
            else:
                optimized_lines.append(line)
        
        return '\n'.join(optimized_lines)
    
    def add_association_metadata(
        self, 
        markdown_content: str,
        associations: List[Dict[str, Any]]
    ) -> str:
        """
        在Markdown中添加關聯元數據註釋
        
        Args:
            markdown_content: 原始Markdown內容
            associations: 關聯信息列表
            
        Returns:
            包含元數據的Markdown內容
        """
        
        # 在文檔末尾添加關聯元數據
        metadata_section = "\n\n<!-- IMAGE-TEXT ASSOCIATIONS -->\n"
        metadata_section += "<!-- This section contains metadata about image-text associations -->\n"
        
        for i, assoc in enumerate(associations):
            metadata_section += f"<!-- Association {i+1}: "
            metadata_section += f"TextBlock={assoc.get('text_block_id', 'unknown')}, "
            metadata_section += f"Image={assoc.get('image_id', 'unknown')}, "
            metadata_section += f"Score={assoc.get('final_score', 0.0):.3f}, "
            metadata_section += f"Type={assoc.get('association_type', 'unknown')} -->\n"
        
        return markdown_content + metadata_section
    
    def extract_association_metadata(self, markdown_content: str) -> List[Dict[str, Any]]:
        """
        從Markdown中提取關聯元數據
        
        Args:
            markdown_content: 包含元數據的Markdown內容
            
        Returns:
            提取的關聯信息列表
        """
        
        associations = []
        
        # 查找關聯元數據註釋
        pattern = r'<!-- Association \d+: TextBlock=([^,]+), Image=([^,]+), Score=([^,]+), Type=([^)]+) -->'
        matches = re.findall(pattern, markdown_content)
        
        for text_block_id, image_id, score_str, assoc_type in matches:
            try:
                associations.append({
                    'text_block_id': text_block_id.strip(),
                    'image_id': image_id.strip(),
                    'final_score': float(score_str.strip()),
                    'association_type': assoc_type.strip()
                })
            except ValueError as e:
                logger.warning(f"解析關聯元數據失敗: {e}")
        
        return associations
    
    def create_toc(self, markdown_content: str) -> str:
        """
        生成目錄 (Table of Contents)
        
        Args:
            markdown_content: Markdown內容
            
        Returns:
            目錄內容
        """
        
        toc_lines = ["## 目錄\n"]
        
        # 提取所有標題
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        matches = re.findall(heading_pattern, markdown_content, re.MULTILINE)
        
        for level_marks, title in matches:
            level = len(level_marks)
            indent = "  " * (level - 1)
            
            # 生成錨點
            anchor = self._generate_anchor(title)
            
            toc_lines.append(f"{indent}- [{title}](#{anchor})")
        
        return "\n".join(toc_lines) + "\n\n"
    
    def _generate_anchor(self, title: str) -> str:
        """生成標題錨點"""
        # 移除特殊字符，轉為小寫，用連字符替換空格
        anchor = re.sub(r'[^\w\s-]', '', title)
        anchor = re.sub(r'[-\s]+', '-', anchor)
        return anchor.lower().strip('-')
    
    def optimize_for_platform(
        self, 
        markdown_content: str, 
        platform: str = "github"
    ) -> str:
        """
        針對特定平台優化Markdown格式
        
        Args:
            markdown_content: 原始Markdown內容
            platform: 目標平台 (github, azure, notion, etc.)
            
        Returns:
            優化後的Markdown內容
        """
        
        if platform.lower() == "github":
            return self._optimize_for_github(markdown_content)
        elif platform.lower() == "azure":
            return self._optimize_for_azure(markdown_content)
        elif platform.lower() == "notion":
            return self._optimize_for_notion(markdown_content)
        else:
            logger.warning(f"未知平台: {platform}，使用默認格式")
            return markdown_content
    
    def _optimize_for_github(self, content: str) -> str:
        """優化GitHub Markdown格式"""
        
        # GitHub支持表格、代碼塊、任務列表等
        # 添加GitHub特定的功能
        
        # 轉換為GitHub任務列表格式
        content = re.sub(r'- \[ \]', '- [ ]', content)
        content = re.sub(r'- \[x\]', '- [x]', content)
        
        return content
    
    def _optimize_for_azure(self, content: str) -> str:
        """優化Azure DevOps Markdown格式"""
        
        # Azure DevOps有一些特殊的Markdown擴展
        return content
    
    def _optimize_for_notion(self, content: str) -> str:
        """優化Notion Markdown格式"""
        
        # Notion對某些Markdown語法的支持有限
        # 簡化一些複雜的格式
        
        return content


def format_markdown_file(
    input_path: str, 
    output_path: str,
    options: Optional[Dict[str, Any]] = None
) -> None:
    """
    格式化Markdown文件的便捷函數
    
    Args:
        input_path: 輸入文件路徑
        output_path: 輸出文件路徑
        options: 格式化選項
    """
    
    formatter = MarkdownFormatter()
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        formatted_content = formatter.format_content(content, options)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        logger.info(f"Markdown文件格式化完成: {input_path} -> {output_path}")
        
    except Exception as e:
        logger.error(f"Markdown文件格式化失敗: {e}")
        raise
