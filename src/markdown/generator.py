"""
Markdown生成器

負責將解析的文檔內容轉換為結構化的Markdown格式，
支持圖文關聯信息的嵌入和模板系統。
"""

import os
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from jinja2 import Environment, FileSystemLoader, Template

from ..config.settings import get_settings
from ..config.logging_config import get_logger
from ..parsers.base import ParsedContent, TextBlock, ImageContent, TableContent
from ..utils.validation import validate_markdown_output

logger = get_logger(__name__)


@dataclass
class MarkdownMetadata:
    """Markdown文檔元數據"""
    document_id: str
    original_filename: str
    created_at: datetime
    processing_time: float
    total_pages: int
    total_images: int
    total_associations: int
    version: str = "1.0"
    
    def to_yaml_frontmatter(self) -> str:
        """轉換為YAML前言格式"""
        metadata = {
            "document_id": self.document_id,
            "original_filename": self.original_filename,
            "created_at": self.created_at.isoformat(),
            "processing_time": f"{self.processing_time:.2f}s",
            "total_pages": self.total_pages,
            "total_images": self.total_images,
            "total_associations": self.total_associations,
            "version": self.version
        }
        
        yaml_lines = ["---"]
        for key, value in metadata.items():
            yaml_lines.append(f"{key}: {value}")
        yaml_lines.append("---")
        
        return "\n".join(yaml_lines)


@dataclass 
class ImageAssociation:
    """圖片關聯信息"""
    image_id: str
    image_url: str
    relevance_score: float
    association_type: str
    spatial_relation: str
    caption_detected: bool
    
    def to_markdown_comment(self) -> str:
        """轉換為Markdown註釋格式"""
        return f"<!-- Image Association: {self.image_id}, Score: {self.relevance_score:.3f}, Type: {self.association_type} -->"


class MarkdownTemplate:
    """Markdown模板管理器"""
    
    def __init__(self, template_dir: Optional[str] = None):
        self.settings = get_settings()
        self.template_dir = template_dir or self._get_default_template_dir()
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=False  # Markdown不需要HTML轉義
        )
        logger.info(f"Markdown模板引擎初始化完成，模板目錄: {self.template_dir}")
    
    def _get_default_template_dir(self) -> str:
        """獲取默認模板目錄"""
        current_dir = Path(__file__).parent
        return str(current_dir / "templates")
    
    def render_template(self, template_name: str, **kwargs) -> str:
        """渲染指定模板"""
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"模板渲染失败: {template_name}, 錯誤: {e}")
            raise
    
    def create_custom_template(self, content: str) -> Template:
        """創建自定義模板"""
        return self.env.from_string(content)


class MarkdownGenerator:
    """主要的Markdown生成器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.template_manager = MarkdownTemplate()
        logger.info("Markdown生成器初始化完成")
    
    def generate(
        self,
        parsed_content: ParsedContent,
        associations: List[Dict[str, Any]],
        output_path: Optional[str] = None,
        template_name: str = "enhanced.md.j2",
        include_metadata: bool = True
    ) -> str:
        """
        生成完整的Markdown文檔
        
        Args:
            parsed_content: 解析後的文檔內容
            associations: 圖文關聯信息列表
            output_path: 輸出文件路徑（可選）
            template_name: 使用的模板名稱
            include_metadata: 是否包含元數據
            
        Returns:
            生成的Markdown內容
        """
        start_time = datetime.now()
        
        try:
            # 1. 準備數據
            processed_data = self._prepare_template_data(
                parsed_content, associations
            )
            
            # 2. 生成元數據
            metadata = None
            if include_metadata:
                processing_time = (datetime.now() - start_time).total_seconds()
                metadata = self._create_metadata(
                    parsed_content, associations, processing_time
                )
            
            # 3. 渲染Markdown
            markdown_content = self._render_markdown(
                processed_data, metadata, template_name
            )
            
            # 4. 驗證輸出
            if not self._validate_output(markdown_content):
                logger.warning("生成的Markdown內容驗證失敗")
            
            # 5. 保存到文件（如果提供路徑）
            if output_path:
                self._save_to_file(markdown_content, output_path)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Markdown生成完成，處理時間: {processing_time:.2f}秒")
            
            return markdown_content
            
        except Exception as e:
            logger.error(f"Markdown生成失败: {e}")
            raise
    
    def _prepare_template_data(
        self, 
        parsed_content: ParsedContent, 
        associations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """準備模板渲染所需的數據"""
        
        # 處理圖文關聯數據
        processed_associations = []
        for assoc in associations:
            processed_associations.append({
                "text_block_id": assoc.get("text_block_id"),
                "image_id": assoc.get("image_id"),
                "score": assoc.get("final_score", 0.0),
                "association_type": assoc.get("association_type", "spatial"),
                "spatial_relation": assoc.get("spatial_relation", "unknown"),
                "caption_detected": assoc.get("caption_score", 0) > 0.5
            })
        
        # 為每個文本塊添加關聯的圖片信息
        text_blocks_with_images = []
        for text_block in parsed_content.text_blocks:
            # 找到與此文本塊關聯的圖片
            related_images = []
            for assoc in processed_associations:
                if assoc["text_block_id"] == text_block.id:
                    # 找到對應的圖片
                    image = next(
                        (img for img in parsed_content.images if img.id == assoc["image_id"]),
                        None
                    )
                    if image:
                        related_images.append({
                            "image": image,
                            "association": assoc
                        })
            
            text_blocks_with_images.append({
                "text_block": text_block,
                "related_images": related_images
            })
        
        return {
            "document": parsed_content,
            "text_blocks_with_images": text_blocks_with_images,
            "associations": processed_associations,
            "tables": parsed_content.tables,
            "metadata": parsed_content.metadata
        }
    
    def _create_metadata(
        self,
        parsed_content: ParsedContent,
        associations: List[Dict[str, Any]],
        processing_time: float
    ) -> MarkdownMetadata:
        """創建文檔元數據"""
        
        document_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return MarkdownMetadata(
            document_id=document_id,
            original_filename=parsed_content.metadata.filename,
            created_at=datetime.now(),
            processing_time=processing_time,
            total_pages=parsed_content.metadata.page_count,
            total_images=len(parsed_content.images),
            total_associations=len(associations)
        )
    
    def _render_markdown(
        self,
        data: Dict[str, Any],
        metadata: Optional[MarkdownMetadata],
        template_name: str
    ) -> str:
        """渲染Markdown內容"""
        
        template_data = {
            **data,
            "metadata": metadata,
            "generation_time": datetime.now(),
            "settings": self.settings
        }
        
        return self.template_manager.render_template(template_name, **template_data)
    
    def _validate_output(self, markdown_content: str) -> bool:
        """驗證生成的Markdown內容"""
        try:
            return validate_markdown_output(markdown_content)
        except Exception as e:
            logger.warning(f"Markdown驗證過程出錯: {e}")
            return False
    
    def _save_to_file(self, content: str, file_path: str) -> None:
        """保存Markdown內容到文件"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Markdown文件已保存: {file_path}")
        except Exception as e:
            logger.error(f"保存Markdown文件失败: {e}")
            raise
    
    def generate_simple_markdown(
        self,
        parsed_content: ParsedContent,
        associations: List[Dict[str, Any]]
    ) -> str:
        """生成簡化版本的Markdown（用於測試）"""
        
        lines = []
        
        # 標題
        lines.append(f"# {parsed_content.metadata.filename}")
        lines.append("")
        
        # 文檔信息
        lines.append("## 文檔信息")
        lines.append(f"- **原始文件**: {parsed_content.metadata.filename}")
        lines.append(f"- **頁數**: {parsed_content.metadata.page_count}")
        lines.append(f"- **圖片數量**: {len(parsed_content.images)}")
        lines.append(f"- **關聯數量**: {len(associations)}")
        lines.append("")
        
        # 內容
        lines.append("## 文檔內容")
        lines.append("")
        
        # 處理每個文本塊
        for text_block in parsed_content.text_blocks:
            # 添加文本內容
            lines.append(text_block.content.strip())
            lines.append("")
            
            # 查找相關圖片
            related_images = [
                assoc for assoc in associations 
                if assoc.get("text_block_id") == text_block.id
            ]
            
            # 添加相關圖片
            for assoc in related_images:
                image_id = assoc.get("image_id")
                score = assoc.get("final_score", 0.0)
                
                # 找到圖片對象
                image = next(
                    (img for img in parsed_content.images if img.id == image_id),
                    None
                )
                
                if image:
                    # 暫時使用本地路徑（Phase 3完成後會改為URL）
                    image_path = f"./images/{image.filename or f'{image_id}.png'}"
                    lines.append(f"![{image.alt_text or 'Image'}]({image_path})")
                    lines.append(f"*關聯度: {score:.3f}*")
                    lines.append("")
        
        # 添加表格
        if parsed_content.tables:
            lines.append("## 表格")
            lines.append("")
            for i, table in enumerate(parsed_content.tables, 1):
                lines.append(f"### 表格 {i}")
                lines.append("")
                # 簡化的表格渲染
                if table.headers:
                    header_line = "| " + " | ".join(table.headers) + " |"
                    separator_line = "|" + "|".join([" --- " for _ in table.headers]) + "|"
                    lines.append(header_line)
                    lines.append(separator_line)
                    
                    for row in table.rows[:5]:  # 限制顯示前5行
                        row_line = "| " + " | ".join(row) + " |"
                        lines.append(row_line)
                lines.append("")
        
        return "\n".join(lines)


def create_default_templates():
    """創建默認的Jinja2模板文件"""
    
    template_dir = Path(__file__).parent / "templates"
    template_dir.mkdir(exist_ok=True)
    
    # 基礎模板
    basic_template = '''# {{ document.metadata.filename }}

{% if metadata %}
---
{{ metadata.to_yaml_frontmatter() }}
---
{% endif %}

## 文檔信息
- **原始文件**: {{ document.metadata.filename }}
- **頁數**: {{ document.metadata.page_count }}
- **圖片數量**: {{ document.images|length }}
- **處理時間**: {{ generation_time.strftime('%Y-%m-%d %H:%M:%S') }}

## 內容

{% for block_data in text_blocks_with_images %}
{{ block_data.text_block.content }}

{% for image_data in block_data.related_images %}
![{{ image_data.image.alt_text or 'Image' }}](./images/{{ image_data.image.filename or (image_data.image.id + '.png') }})
*關聯度: {{ "%.3f"|format(image_data.association.score) }}*

{% endfor %}
{% endfor %}

{% if tables %}
## 表格

{% for table in tables %}
### 表格 {{ loop.index }}

{% if table.headers %}
| {{ table.headers|join(' | ') }} |
|{{ table.headers|map('replace', table.headers[0], ' --- ')|join('|') }}|
{% for row in table.rows[:10] %}
| {{ row|join(' | ') }} |
{% endfor %}
{% endif %}

{% endfor %}
{% endif %}
'''

    # 增強模板
    enhanced_template = '''# {{ document.metadata.filename }}

{% if metadata %}
{{ metadata.to_yaml_frontmatter() }}

{% endif %}

## 📋 文檔概覽

| 項目 | 詳情 |
|------|------|
| 📄 原始文件 | {{ document.metadata.filename }} |
| 📊 頁數 | {{ document.metadata.page_count }} |
| 🖼️ 圖片數量 | {{ document.images|length }} |
| 🔗 關聯數量 | {{ associations|length }} |
| ⏱️ 處理時間 | {{ generation_time.strftime('%Y-%m-%d %H:%M:%S') }} |

---

## 📝 文檔內容

{% for block_data in text_blocks_with_images %}
### 段落 {{ loop.index }}

{{ block_data.text_block.content }}

{% if block_data.related_images %}
#### 📸 相關圖片

{% for image_data in block_data.related_images %}
<div class="image-association">

![{{ image_data.image.alt_text or 'Image' }}](./images/{{ image_data.image.filename or (image_data.image.id + '.png') }})

**圖片信息:**
- 🎯 關聯度: {{ "%.3f"|format(image_data.association.score) }}
- 📍 關聯類型: {{ image_data.association.association_type }}
- 🔍 Caption檢測: {{ '✅' if image_data.association.caption_detected else '❌' }}

</div>

{% endfor %}
{% endif %}

---

{% endfor %}

{% if tables %}
## 📊 數據表格

{% for table in tables %}
### 表格 {{ loop.index }}

{% if table.headers %}
| {{ table.headers|join(' | ') }} |
|{{ table.headers|map('replace', table.headers[0], ' --- ')|join('|') }}|
{% for row in table.rows[:10] %}
| {{ row|join(' | ') }} |
{% endfor %}

{% if table.rows|length > 10 %}
*註: 僅顯示前10行數據*
{% endif %}
{% endif %}

{% endfor %}
{% endif %}

---

## 🔍 處理詳情

{% if associations %}
### 圖文關聯分析

| 文本塊 | 圖片 | 關聯度 | 類型 | Caption |
|--------|------|--------|------|---------|
{% for assoc in associations %}
| {{ assoc.text_block_id }} | {{ assoc.image_id }} | {{ "%.3f"|format(assoc.score) }} | {{ assoc.association_type }} | {{ '✅' if assoc.caption_detected else '❌' }} |
{% endfor %}
{% endif %}

*Generated by 智能文件轉換與RAG知識庫系統 v{{ metadata.version if metadata else '1.0' }}*
'''

    # 保存模板文件
    with open(template_dir / "basic.md.j2", 'w', encoding='utf-8') as f:
        f.write(basic_template)
    
    with open(template_dir / "enhanced.md.j2", 'w', encoding='utf-8') as f:
        f.write(enhanced_template)
    
    logger.info(f"默認模板已創建於: {template_dir}")


# 模組初始化時創建默認模板
if __name__ == "__main__":
    create_default_templates()
