"""
PDF解析器單元測試

測試PyMuPDF解析器的核心功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.parsers.pdf_parser import PDFParser
from src.parsers.base import ParsedContent, TextBlock, ImageContent, BoundingBox


class TestPDFParser:
    """PDF解析器測試類"""
    
    def setup_method(self):
        """設置測試方法"""
        self.parser = PDFParser()
    
    def test_parser_initialization(self):
        """測試解析器初始化"""
        assert self.parser is not None
        assert hasattr(self.parser, 'extract_content')
    
    @patch('src.parsers.pdf_parser.fitz.open')
    def test_extract_content_success(self, mock_fitz_open):
        """測試成功提取PDF內容"""
        # 模擬PDF文檔
        mock_doc = Mock()
        mock_doc.metadata = {
            'title': 'Test Document',
            'author': 'Test Author',
            'subject': 'Test Subject'
        }
        mock_doc.page_count = 2
        
        # 模擬頁面
        mock_page = Mock()
        mock_page.number = 0
        
        # 模擬文本塊
        mock_page.get_text.return_value = {
            'blocks': [
                {
                    'type': 0,  # 文本塊
                    'bbox': (100, 200, 400, 250),
                    'lines': [
                        {
                            'spans': [
                                {
                                    'text': '這是測試文字內容',
                                    'size': 12,
                                    'font': 'Arial'
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # 模擬圖片
        mock_page.get_images.return_value = [
            (0, 0, 100, 150, 8, 'DCTDecode', 'DeviceRGB', '', 'Im1', 'JPEG')
        ]
        
        # 模擬get_pixmap
        mock_pixmap = Mock()
        mock_pixmap.tobytes.return_value = b'fake_image_data'
        mock_pixmap.width = 100
        mock_pixmap.height = 150
        mock_pixmap.n = 3
        mock_page.get_pixmap.return_value = mock_pixmap
        
        # 設置文檔迭代
        mock_doc.__iter__ = Mock(return_value=iter([mock_page]))
        mock_fitz_open.return_value = mock_doc
        
        # 執行測試
        result = self.parser.extract_content("test.pdf")
        
        # 驗證結果
        assert isinstance(result, ParsedContent)
        assert len(result.text_blocks) > 0
        assert len(result.images) > 0
        assert result.metadata.filename == "test.pdf"
        assert result.metadata.total_pages == 2
        
        # 驗證文本塊
        text_block = result.text_blocks[0]
        assert isinstance(text_block, TextBlock)
        assert text_block.content == '這是測試文字內容'
        assert text_block.page == 1  # 1-based
        assert isinstance(text_block.bbox, BoundingBox)
        
        # 驗證圖片
        image = result.images[0]
        assert isinstance(image, ImageContent)
        assert image.data == b'fake_image_data'
        assert image.format == 'JPEG'
        assert image.size == (100, 150)
    
    @patch('src.parsers.pdf_parser.fitz.open')
    def test_extract_content_file_not_found(self, mock_fitz_open):
        """測試文件不存在的情況"""
        mock_fitz_open.side_effect = FileNotFoundError("文件不存在")
        
        with pytest.raises(FileNotFoundError):
            self.parser.extract_content("nonexistent.pdf")
    
    @patch('src.parsers.pdf_parser.fitz.open')
    def test_extract_content_corrupted_pdf(self, mock_fitz_open):
        """測試損壞的PDF文件"""
        mock_fitz_open.side_effect = Exception("PDF文件損壞")
        
        with pytest.raises(Exception):
            self.parser.extract_content("corrupted.pdf")
    
    @patch('src.parsers.pdf_parser.fitz.open')
    def test_extract_content_empty_pdf(self, mock_fitz_open):
        """測試空PDF文件"""
        mock_doc = Mock()
        mock_doc.metadata = {}
        mock_doc.page_count = 0
        mock_doc.__iter__ = Mock(return_value=iter([]))
        mock_fitz_open.return_value = mock_doc
        
        result = self.parser.extract_content("empty.pdf")
        
        assert isinstance(result, ParsedContent)
        assert len(result.text_blocks) == 0
        assert len(result.images) == 0
        assert result.metadata.total_pages == 0
    
    def test_standardize_output(self):
        """測試輸出標準化"""
        # 測試數據
        content = {
            'text_blocks': [
                {
                    'id': 'text_001',
                    'content': '測試文字',
                    'page': 1,
                    'bbox': (100, 200, 400, 250)
                }
            ],
            'images': [],
            'tables': [],
            'metadata': {
                'filename': 'test.pdf',
                'total_pages': 1,
                'created_date': '2025-08-08T10:00:00Z',
                'file_size': 1024
            }
        }
        
        result = self.parser.standardize_output(content)
        
        assert isinstance(result, ParsedContent)
        assert len(result.text_blocks) == 1
        assert result.text_blocks[0].content == '測試文字'
        assert result.metadata.filename == 'test.pdf'
    
    @pytest.mark.parametrize("bbox_input,expected", [
        ((100, 200, 400, 250), BoundingBox(x1=100, y1=200, x2=400, y2=250)),
        ([50, 100, 300, 150], BoundingBox(x1=50, y1=100, x2=300, y2=150)),
    ])
    def test_bbox_conversion(self, bbox_input, expected):
        """測試邊界框轉換"""
        result = self.parser._convert_bbox(bbox_input)
        assert result.x1 == expected.x1
        assert result.y1 == expected.y1
        assert result.x2 == expected.x2
        assert result.y2 == expected.y2
    
    def test_text_cleaning(self):
        """測試文本清理"""
        dirty_text = "  這是\n\n測試\t文字  \r\n  "
        clean_text = self.parser._clean_text(dirty_text)
        assert clean_text == "這是 測試 文字"
    
    @pytest.mark.slow
    def test_performance_large_document(self, performance_timer):
        """測試大文檔處理性能"""
        with patch('src.parsers.pdf_parser.fitz.open') as mock_fitz_open:
            # 模擬大文檔
            mock_doc = Mock()
            mock_doc.metadata = {}
            mock_doc.page_count = 100
            
            # 創建100頁的模擬內容
            mock_pages = []
            for i in range(100):
                mock_page = Mock()
                mock_page.number = i
                mock_page.get_text.return_value = {'blocks': []}
                mock_page.get_images.return_value = []
                mock_pages.append(mock_page)
            
            mock_doc.__iter__ = Mock(return_value=iter(mock_pages))
            mock_fitz_open.return_value = mock_doc
            
            # 性能測試
            performance_timer.start()
            result = self.parser.extract_content("large.pdf")
            performance_timer.stop()
            
            # 驗證結果和性能
            assert isinstance(result, ParsedContent)
            performance_timer.assert_under(5.0)  # 應在5秒內完成


@pytest.mark.unit
@pytest.mark.parser
class TestPDFParserIntegration:
    """PDF解析器集成測試"""
    
    def test_real_pdf_structure(self, create_test_pdf):
        """測試真實PDF文件結構解析"""
        parser = PDFParser()
        
        # 由於create_test_pdf創建的是模擬PDF，這裡只測試錯誤處理
        with pytest.raises(Exception):  # 期望解析失敗
            parser.extract_content(str(create_test_pdf))
    
    def test_multiple_formats_support(self):
        """測試多種PDF格式支持"""
        parser = PDFParser()
        
        # 測試不同版本的PDF格式標識
        supported_formats = parser.get_supported_formats()
        assert 'application/pdf' in supported_formats
        assert '.pdf' in supported_formats
