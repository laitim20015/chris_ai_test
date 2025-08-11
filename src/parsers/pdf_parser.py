"""
PDF解析器 - 三層備用架構
PDF Parser - Three-tier Fallback Architecture

嚴格按照項目規格文件實現的PDF解析器，採用三層備用架構：

1. PyMuPDF (主要解析器) - 最佳性能 (0.003-0.2秒)
2. pymupdf4llm - 最佳Markdown輸出 (0.12秒)  
3. unstructured - 最佳語義分塊 (1.29秒)

技術特點：
- 內建OCR支持，無需額外依賴
- 原生表格和圖片提取
- 直接輸出結構化Markdown
- 語義感知的內容分塊

性能基準（項目規格）：
- PyMuPDF: 0.003-0.2秒（最快）
- pymupdf4llm: 0.12秒（結構最好）
- unstructured: 1.29秒（語義最強）
"""

from typing import List, Dict, Optional, Union, Any, Tuple
from pathlib import Path
import time
import hashlib
from dataclasses import dataclass

from src.parsers.base import (
    BaseParser, ParsedContent, TextBlock, ImageContent, TableContent,
    DocumentMetadata, ContentType, ImageFormat, ParserError, 
    create_bounding_box, generate_content_id
)
from src.config.logging_config import get_logger, log_performance
from src.association.allen_logic import BoundingBox

logger = get_logger("pdf_parser")

@dataclass
class PDFParsingConfig:
    """PDF解析配置"""
    
    # 主解析器選擇
    primary_parser: str = "pymupdf"         # 主要解析器
    enable_fallback: bool = True            # 啟用備用機制
    fallback_order: List[str] = None        # 備用順序
    
    # 性能配置
    max_file_size_mb: float = 200.0         # 最大文件大小
    timeout_seconds: int = 300              # 超時時間
    
    # 提取配置
    extract_images: bool = True             # 提取圖片
    extract_tables: bool = True             # 提取表格
    extract_metadata: bool = True           # 提取元數據
    
    # OCR配置
    enable_ocr: bool = True                 # 啟用OCR
    ocr_language: str = "chi_sim+eng"      # OCR語言
    
    # 圖片配置
    min_image_size: Tuple[int, int] = (50, 50)     # 最小圖片尺寸
    image_quality: int = 85                 # 圖片質量
    
    def __post_init__(self):
        if self.fallback_order is None:
            self.fallback_order = ["pymupdf", "pymupdf4llm", "unstructured"]

class PyMuPDFParser:
    """PyMuPDF解析器 - 主要解析器（最快）"""
    
    def __init__(self, config: PDFParsingConfig):
        """
        初始化PyMuPDF解析器
        
        Args:
            config: 解析配置
        """
        self.config = config
        self.name = "PyMuPDF"
        
        # 檢查依賴
        try:
            import fitz  # PyMuPDF
            self.fitz = fitz
            self.available = True
            logger.debug("PyMuPDF解析器可用")
        except ImportError:
            self.fitz = None
            self.available = False
            logger.warning("PyMuPDF不可用，請安裝: pip install PyMuPDF")
    
    @log_performance("pymupdf_parse")
    def parse(self, file_path: Union[str, Path]) -> ParsedContent:
        """
        使用PyMuPDF解析PDF
        
        Args:
            file_path: PDF文件路徑
            
        Returns:
            ParsedContent: 解析結果
        """
        if not self.available:
            raise ParserError("PyMuPDF不可用", parser_name=self.name)
        
        path = Path(file_path)
        
        try:
            # 打開PDF文檔
            doc = self.fitz.open(str(path))
            
            text_blocks = []
            images = []
            tables = []
            
            # 逐頁處理
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 提取文本塊
                if True:  # 總是提取文本
                    page_text_blocks = self._extract_text_blocks(page, page_num + 1)
                    text_blocks.extend(page_text_blocks)
                
                # 提取圖片
                if self.config.extract_images:
                    page_images = self._extract_images(page, page_num + 1)
                    images.extend(page_images)
                
                # 提取表格
                if self.config.extract_tables:
                    page_tables = self._extract_tables(page, page_num + 1)
                    tables.extend(page_tables)
            
            # 提取元數據
            metadata = self._extract_metadata(doc, path) if self.config.extract_metadata else None
            
            doc.close()
            
            result = ParsedContent(
                text_blocks=text_blocks,
                images=images,
                tables=tables,
                metadata=metadata,
                success=True
            )
            
            logger.info(f"PyMuPDF解析完成: {len(text_blocks)}文本塊, {len(images)}圖片, {len(tables)}表格")
            return result
            
        except Exception as e:
            logger.error(f"PyMuPDF解析失敗: {e}")
            return ParsedContent(
                success=False,
                error_message=f"PyMuPDF解析失敗: {str(e)}"
            )
    
    def _extract_text_blocks(self, page, page_num: int) -> List[TextBlock]:
        """提取頁面文本塊"""
        text_blocks = []
        
        try:
            # 獲取文本字典格式
            text_dict = page.get_text("dict")
            
            block_index = 0
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                
                # 合併行文本
                block_text = ""
                bbox_list = []
                
                for line in block["lines"]:
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                        bbox_list.append(span.get("bbox", [0, 0, 0, 0]))
                    
                    if line_text.strip():
                        block_text += line_text + "\n"
                
                block_text = block_text.strip()
                
                if block_text:
                    # 計算邊界框
                    if bbox_list:
                        min_x = min(bbox[0] for bbox in bbox_list)
                        min_y = min(bbox[1] for bbox in bbox_list)
                        max_x = max(bbox[2] for bbox in bbox_list)
                        max_y = max(bbox[3] for bbox in bbox_list)
                        bbox = create_bounding_box(min_x, min_y, max_x - min_x, max_y - min_y)
                    else:
                        bbox = None
                    
                    # 檢測內容類型（簡化版）
                    content_type = ContentType.PARAGRAPH
                    if len(block_text) < 100 and block_text.isupper():
                        content_type = ContentType.HEADER
                    
                    text_block = TextBlock(
                        id=generate_content_id("text", page_num, block_index),
                        content=block_text,
                        content_type=content_type,
                        bbox=bbox,
                        page_number=page_num,
                        paragraph_index=block_index
                    )
                    
                    text_blocks.append(text_block)
                    block_index += 1
        
        except Exception as e:
            logger.warning(f"頁面 {page_num} 文本提取失敗: {e}")
        
        return text_blocks
    
    def _extract_images(self, page, page_num: int) -> List[ImageContent]:
        """提取頁面圖片（包括嵌入圖片和向量圖形）"""
        images = []
        
        try:
            # 1. 獲取傳統嵌入圖片
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                try:
                    # 獲取圖片對象
                    xref = img[0]
                    pix = self.fitz.Pixmap(page.parent, xref)
                    
                    # 檢查圖片尺寸
                    if (pix.width < self.config.min_image_size[0] or 
                        pix.height < self.config.min_image_size[1]):
                        pix = None
                        continue
                    
                    # 轉換為PNG格式
                    if pix.n - pix.alpha < 4:  # GRAY或RGB
                        img_data = pix.tobytes("png")
                    else:  # CMYK需要轉換
                        pix_rgb = self.fitz.Pixmap(self.fitz.csRGB, pix)
                        img_data = pix_rgb.tobytes("png")
                        pix_rgb = None
                    
                    # 獲取圖片位置（簡化）
                    img_rect = page.get_image_rects(xref)
                    if img_rect:
                        rect = img_rect[0]
                        bbox = create_bounding_box(
                            rect.x0, rect.y0, 
                            rect.width, rect.height
                        )
                    else:
                        bbox = None
                    
                    # 創建圖片對象
                    image_content = ImageContent(
                        id=generate_content_id("image", page_num, img_index),
                        filename=f"page_{page_num:03d}_image_{img_index:03d}.png",
                        format=ImageFormat.PNG,
                        data=img_data,
                        width=pix.width,
                        height=pix.height,
                        bbox=bbox,
                        page_number=page_num,
                        image_index=img_index
                    )
                    
                    images.append(image_content)
                    pix = None
                    
                except Exception as e:
                    logger.warning(f"圖片 {img_index} 提取失敗: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"頁面 {page_num} 圖片提取失敗: {e}")
        
        # 2. 檢測向量圖形
        try:
            vector_images = self._extract_vector_graphics(page, page_num, len(images))
            images.extend(vector_images)
            if vector_images:
                logger.info(f"頁面 {page_num} 檢測到 {len(vector_images)} 個向量圖形")
        except Exception as e:
            logger.warning(f"頁面 {page_num} 向量圖形檢測失敗: {e}")
        
        return images
    
    def _extract_vector_graphics(self, page, page_num: int, start_index: int) -> List[ImageContent]:
        """檢測並提取向量圖形"""
        vector_images = []
        
        try:
            import math
            from collections import defaultdict
            
            # 獲取所有繪圖對象
            drawings = page.get_drawings()
            
            if not drawings:
                return vector_images
            
            logger.debug(f"頁面 {page_num} 檢測到 {len(drawings)} 個繪圖對象")
            
            # 按空間接近度分組繪圖對象
            drawing_groups = self._group_drawings_by_proximity(drawings)
            
            # 識別圖表區域
            min_drawing_density = 10  # 最小繪圖對象數量
            min_area = 5000  # 最小面積
            
            for group_id, group_drawings in drawing_groups.items():
                if len(group_drawings) >= min_drawing_density:
                    bbox = self._calculate_group_bbox(group_drawings)
                    area = bbox.width * bbox.height
                    
                    if area >= min_area:
                        # 創建向量圖形ImageContent
                        img_index = start_index + len(vector_images)
                        filename = f"page_{page_num:03d}_vector_{img_index:03d}.png"
                        
                        # 生成占位圖片數據（實際可以渲染向量圖形）
                        placeholder_data = self._create_vector_placeholder(bbox, len(group_drawings))
                        
                        vector_image = ImageContent(
                            id=generate_content_id("vector", page_num, img_index),
                            filename=filename,
                            format=ImageFormat.PNG,
                            data=placeholder_data,
                            width=int(bbox.width),
                            height=int(bbox.height),
                            bbox=bbox,
                            page_number=page_num,
                            image_index=img_index,
                            alt_text=f"向量圖表 ({len(group_drawings)}個繪圖對象)"
                        )
                        
                        vector_images.append(vector_image)
                        
                        logger.debug(f"創建向量圖形: {filename}, 位置({bbox.x:.1f}, {bbox.y:.1f}), "
                                   f"尺寸({bbox.width:.1f}x{bbox.height:.1f}), "
                                   f"{len(group_drawings)}個對象")
            
        except Exception as e:
            logger.warning(f"向量圖形檢測失敗: {e}")
        
        return vector_images
    
    def _group_drawings_by_proximity(self, drawings: list, proximity_threshold: float = 100) -> dict:
        """按空間接近度分組繪圖對象"""
        if not drawings:
            return {}
        
        import math
        from collections import defaultdict
        
        # 為每個繪圖對象計算中心點
        drawing_centers = []
        for drawing in drawings:
            rect = drawing.get('rect')
            if rect:
                center_x = rect.x0 + (rect.x1 - rect.x0) / 2
                center_y = rect.y0 + (rect.y1 - rect.y0) / 2
                drawing_centers.append((center_x, center_y, drawing))
        
        # 使用簡單的連通分量算法分組
        groups = defaultdict(list)
        visited = set()
        group_id = 0
        
        for i, (x1, y1, drawing1) in enumerate(drawing_centers):
            if i in visited:
                continue
                
            # 開始新組
            current_group = [drawing1]
            visited.add(i)
            stack = [(x1, y1, i)]
            
            while stack:
                cx, cy, idx = stack.pop()
                
                # 查找附近的未訪問對象
                for j, (x2, y2, drawing2) in enumerate(drawing_centers):
                    if j in visited:
                        continue
                    
                    distance = math.sqrt((x2 - cx) ** 2 + (y2 - cy) ** 2)
                    if distance <= proximity_threshold:
                        current_group.append(drawing2)
                        visited.add(j)
                        stack.append((x2, y2, j))
            
            if len(current_group) > 1:  # 只保留多對象組
                groups[group_id] = current_group
                group_id += 1
        
        return groups
    
    def _calculate_group_bbox(self, drawings: list):
        """計算繪圖組的邊界框"""
        if not drawings:
            return create_bounding_box(0, 0, 0, 0)
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for drawing in drawings:
            rect = drawing.get('rect')
            if rect:
                min_x = min(min_x, rect.x0)
                min_y = min(min_y, rect.y0)
                max_x = max(max_x, rect.x1)
                max_y = max(max_y, rect.y1)
        
        return create_bounding_box(
            min_x, min_y,
            max_x - min_x, max_y - min_y
        )
    
    def _create_vector_placeholder(self, bbox, drawing_count: int) -> bytes:
        """創建向量圖形的占位數據"""
        # 創建一個簡單的占位PNG
        # 實際實現中可以渲染真實的向量圖形
        try:
            from PIL import Image, ImageDraw
            
            # 創建占位圖片
            width = max(100, int(bbox.width))
            height = max(100, int(bbox.height))
            
            img = Image.new('RGB', (width, height), color='lightgray')
            draw = ImageDraw.Draw(img)
            
            # 繪製簡單的占位內容
            draw.rectangle([10, 10, width-10, height-10], outline='blue', width=2)
            draw.text((20, 20), f"向量圖表\n{drawing_count}個對象", fill='blue')
            
            # 轉換為bytes
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
            
        except ImportError:
            # 如果沒有PIL，返回簡單的占位數據
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00d\x00\x00\x00d\x08\x02\x00\x00\x00\xff\x80\x02\x03'
    
    def _extract_tables(self, page, page_num: int) -> List[TableContent]:
        """提取頁面表格"""
        tables = []
        
        try:
            # PyMuPDF表格提取
            tabs = page.find_tables()
            
            for tab_index, tab in enumerate(tabs):
                try:
                    # 提取表格數據
                    table_data = tab.extract()
                    
                    if not table_data:
                        continue
                    
                    # 檢測表頭
                    headers = []
                    rows = table_data
                    
                    if len(table_data) > 1:
                        # 假設第一行是表頭
                        potential_header = table_data[0]
                        if all(cell and isinstance(cell, str) and cell.strip() for cell in potential_header):
                            headers = potential_header
                            rows = table_data[1:]
                    
                    # 獲取表格位置
                    bbox = create_bounding_box(
                        tab.bbox.x0, tab.bbox.y0,
                        tab.bbox.width, tab.bbox.height
                    )
                    
                    table_content = TableContent(
                        id=generate_content_id("table", page_num, tab_index),
                        rows=rows,
                        headers=headers,
                        bbox=bbox,
                        page_number=page_num,
                        table_index=tab_index
                    )
                    
                    tables.append(table_content)
                    
                except Exception as e:
                    logger.warning(f"表格 {tab_index} 提取失敗: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"頁面 {page_num} 表格提取失敗: {e}")
        
        return tables
    
    def _extract_metadata(self, doc, file_path: Path) -> DocumentMetadata:
        """提取文檔元數據"""
        try:
            doc_metadata = doc.metadata
            
            metadata = DocumentMetadata(
                filename=file_path.name,
                file_path=str(file_path.absolute()),
                file_size=file_path.stat().st_size,
                file_format=".pdf",
                title=doc_metadata.get("title", ""),
                author=doc_metadata.get("author", ""),
                subject=doc_metadata.get("subject", ""),
                creator=doc_metadata.get("creator", ""),
                producer=doc_metadata.get("producer", ""),
                page_count=len(doc),
                parser_name=self.name,
                parser_version="1.0.0"
            )
            
            # 處理關鍵詞
            keywords_str = doc_metadata.get("keywords", "")
            if keywords_str:
                metadata.keywords = [kw.strip() for kw in keywords_str.split(",")]
            
            return metadata
            
        except Exception as e:
            logger.warning(f"元數據提取失敗: {e}")
            return DocumentMetadata(
                filename=file_path.name,
                file_path=str(file_path.absolute()),
                file_size=file_path.stat().st_size,
                file_format=".pdf",
                parser_name=self.name,
                parser_version="1.0.0"
            )

class PyMuPDF4LLMParser:
    """pymupdf4llm解析器 - 最佳Markdown輸出"""
    
    def __init__(self, config: PDFParsingConfig):
        """
        初始化pymupdf4llm解析器
        
        Args:
            config: 解析配置
        """
        self.config = config
        self.name = "PyMuPDF4LLM"
        
        # 檢查依賴
        try:
            import pymupdf4llm
            self.pymupdf4llm = pymupdf4llm
            self.available = True
            logger.debug("pymupdf4llm解析器可用")
        except ImportError:
            self.pymupdf4llm = None
            self.available = False
            logger.warning("pymupdf4llm不可用，請安裝: pip install pymupdf4llm")
    
    @log_performance("pymupdf4llm_parse")
    def parse(self, file_path: Union[str, Path]) -> ParsedContent:
        """
        使用pymupdf4llm解析PDF
        
        Args:
            file_path: PDF文件路徑
            
        Returns:
            ParsedContent: 解析結果
        """
        if not self.available:
            raise ParserError("pymupdf4llm不可用", parser_name=self.name)
        
        try:
            # 使用pymupdf4llm提取Markdown
            markdown_text = self.pymupdf4llm.to_markdown(str(file_path))
            
            # 簡單解析Markdown為文本塊
            text_blocks = self._parse_markdown_to_blocks(markdown_text)
            
            result = ParsedContent(
                text_blocks=text_blocks,
                images=[],  # pymupdf4llm主要專注於文本結構
                tables=[],
                success=True
            )
            
            logger.info(f"pymupdf4llm解析完成: {len(text_blocks)}文本塊")
            return result
            
        except Exception as e:
            logger.error(f"pymupdf4llm解析失敗: {e}")
            return ParsedContent(
                success=False,
                error_message=f"pymupdf4llm解析失敗: {str(e)}"
            )
    
    def _parse_markdown_to_blocks(self, markdown_text: str) -> List[TextBlock]:
        """將Markdown文本解析為文本塊"""
        text_blocks = []
        
        lines = markdown_text.split('\n')
        current_block = ""
        block_index = 0
        
        for line in lines:
            line = line.strip()
            
            if not line:
                # 空行，結束當前塊
                if current_block.strip():
                    text_block = TextBlock(
                        id=generate_content_id("text", 1, block_index),
                        content=current_block.strip(),
                        content_type=ContentType.PARAGRAPH,
                        page_number=1,
                        paragraph_index=block_index
                    )
                    text_blocks.append(text_block)
                    block_index += 1
                
                current_block = ""
            else:
                current_block += line + "\n"
        
        # 處理最後一個塊
        if current_block.strip():
            text_block = TextBlock(
                id=generate_content_id("text", 1, block_index),
                content=current_block.strip(),
                content_type=ContentType.PARAGRAPH,
                page_number=1,
                paragraph_index=block_index
            )
            text_blocks.append(text_block)
        
        return text_blocks

class UnstructuredPDFParser:
    """unstructured解析器 - 最佳語義分塊"""
    
    def __init__(self, config: PDFParsingConfig):
        """
        初始化unstructured解析器
        
        Args:
            config: 解析配置
        """
        self.config = config
        self.name = "Unstructured"
        
        # 檢查依賴
        try:
            from unstructured.partition.pdf import partition_pdf
            self.partition_pdf = partition_pdf
            self.available = True
            logger.debug("unstructured解析器可用")
        except ImportError:
            self.partition_pdf = None
            self.available = False
            logger.warning("unstructured不可用，請安裝: pip install unstructured")
    
    @log_performance("unstructured_parse")
    def parse(self, file_path: Union[str, Path]) -> ParsedContent:
        """
        使用unstructured解析PDF
        
        Args:
            file_path: PDF文件路徑
            
        Returns:
            ParsedContent: 解析結果
        """
        if not self.available:
            raise ParserError("unstructured不可用", parser_name=self.name)
        
        try:
            # 使用unstructured分割PDF
            elements = self.partition_pdf(str(file_path))
            
            text_blocks = []
            
            for i, element in enumerate(elements):
                # 轉換為TextBlock
                content_type = ContentType.PARAGRAPH
                
                # 根據元素類型設置content_type
                element_type = str(type(element).__name__).lower()
                if "title" in element_type:
                    content_type = ContentType.HEADER
                elif "table" in element_type:
                    content_type = ContentType.TABLE
                elif "list" in element_type:
                    content_type = ContentType.LIST
                
                text_block = TextBlock(
                    id=generate_content_id("text", 1, i),
                    content=str(element),
                    content_type=content_type,
                    page_number=getattr(element, 'metadata', {}).get('page_number', 1),
                    paragraph_index=i
                )
                
                text_blocks.append(text_block)
            
            result = ParsedContent(
                text_blocks=text_blocks,
                images=[],  # unstructured主要專注於語義分塊
                tables=[],
                success=True
            )
            
            logger.info(f"unstructured解析完成: {len(text_blocks)}文本塊")
            return result
            
        except Exception as e:
            logger.error(f"unstructured解析失敗: {e}")
            return ParsedContent(
                success=False,
                error_message=f"unstructured解析失敗: {str(e)}"
            )

class PDFParser(BaseParser):
    """PDF解析器主類 - 三層備用架構"""
    
    def __init__(self, config: Optional[PDFParsingConfig] = None):
        """
        初始化PDF解析器
        
        Args:
            config: 解析配置
        """
        super().__init__("PDFParser")
        
        self.config = config if config is not None else PDFParsingConfig()
        self.supported_formats = ['.pdf']
        
        # 初始化三個解析器
        self.pymupdf_parser = PyMuPDFParser(self.config)
        self.pymupdf4llm_parser = PyMuPDF4LLMParser(self.config)
        self.unstructured_parser = UnstructuredPDFParser(self.config)
        
        # 性能信息
        self.performance_info = {
            "pymupdf": {"speed": "fastest", "time_range": "0.003-0.2s"},
            "pymupdf4llm": {"speed": "fast", "time_range": "0.12s"},
            "unstructured": {"speed": "moderate", "time_range": "1.29s"}
        }
        
        logger.info("PDF解析器初始化完成，三層備用架構就緒")
    
    def can_parse(self, file_path: Union[str, Path]) -> bool:
        """
        檢查是否可以解析PDF文件
        
        Args:
            file_path: 文件路徑
            
        Returns:
            bool: 是否可以解析
        """
        path = Path(file_path)
        return path.suffix.lower() == '.pdf' and path.exists()
    
    @log_performance("pdf_parse_with_fallback")
    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedContent:
        """
        解析PDF文件（支持三層備用）
        
        Args:
            file_path: PDF文件路徑
            **kwargs: 額外參數
            
        Returns:
            ParsedContent: 解析結果
        """
        self.validate_file(file_path)
        
        # 檢查文件大小
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        if file_size_mb > self.config.max_file_size_mb:
            raise ParserError(
                f"文件太大 ({file_size_mb:.1f}MB > {self.config.max_file_size_mb}MB)",
                parser_name=self.name,
                file_path=str(file_path)
            )
        
        # 獲取解析器順序
        parsers_to_try = []
        
        for parser_name in self.config.fallback_order:
            if parser_name == "pymupdf" and self.pymupdf_parser.available:
                parsers_to_try.append(("PyMuPDF", self.pymupdf_parser))
            elif parser_name == "pymupdf4llm" and self.pymupdf4llm_parser.available:
                parsers_to_try.append(("PyMuPDF4LLM", self.pymupdf4llm_parser))
            elif parser_name == "unstructured" and self.unstructured_parser.available:
                parsers_to_try.append(("Unstructured", self.unstructured_parser))
        
        if not parsers_to_try:
            raise ParserError("沒有可用的PDF解析器", parser_name=self.name)
        
        # 逐個嘗試解析器
        last_error = None
        
        for parser_name, parser in parsers_to_try:
            try:
                logger.info(f"嘗試使用 {parser_name} 解析PDF: {Path(file_path).name}")
                
                result = parser.parse(file_path)
                
                if result.success and result.text_blocks:
                    logger.info(f"PDF解析成功，使用解析器: {parser_name}")
                    return result
                else:
                    logger.warning(f"{parser_name} 解析結果為空或失敗")
                    last_error = result.error_message or f"{parser_name} 解析結果為空"
                
                # 如果不啟用備用機制，第一次失敗就退出
                if not self.config.enable_fallback:
                    break
                    
            except Exception as e:
                logger.error(f"{parser_name} 解析異常: {e}")
                last_error = str(e)
                
                if not self.config.enable_fallback:
                    break
                continue
        
        # 所有解析器都失敗
        return ParsedContent(
            success=False,
            error_message=f"所有PDF解析器都失敗，最後錯誤: {last_error}"
        )

def parse_pdf_with_fallback(file_path: Union[str, Path], 
                          config: Optional[PDFParsingConfig] = None) -> ParsedContent:
    """
    便捷的PDF解析函數
    
    Args:
        file_path: PDF文件路徑
        config: 解析配置
        
    Returns:
        ParsedContent: 解析結果
    """
    parser = PDFParser(config)
    return parser.parse_with_metadata(file_path)

