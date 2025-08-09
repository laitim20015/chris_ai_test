"""
Word解析器單元測試

測試python-docx解析器的核心功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.parsers.word_parser import WordParser
from src.parsers.base import ParsedContent, TextBlock, ImageContent, BoundingBox


class TestWordParser:
    """Word解析器測試類"""
    
    def setup_method(self):
        """設置測試方法"""
        self.parser = WordParser()
    
    def test_parser_initialization(self):
        """測試解析器初始化"""
        assert self.parser is not None
        assert hasattr(self.parser, 'extract_content')
    
    @patch('src.parsers.word_parser.docx.Document')
    def test_extract_content_success(self, mock_document):
        """測試成功提取Word內容"""
        # 模擬Word文檔
        mock_doc = Mock()
        
        # 模擬段落
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "這是第一段內容"
        mock_paragraph1.style.name = "Normal"
        
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "這是第二段內容"
        mock_paragraph2.style.name = "Heading 1"
        
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        
        # 模擬圖片
        mock_shape = Mock()
        mock_shape.shape_type = 13  # PICTURE
        mock_image = Mock()
        mock_image.blob = b'fake_image_data'
        mock_image.content_type = 'image/jpeg'
        mock_image.filename = 'test_image.jpg'
        mock_shape.image = mock_image
        
        # 模擬inline shapes
        mock_doc.inline_shapes = [mock_shape]
        
        # 模擬核心屬性
        mock_properties = Mock()
        mock_properties.title = "測試文檔"
        mock_properties.author = "測試作者"
        mock_properties.created = "2025-08-08T10:00:00Z"
        mock_doc.core_properties = mock_properties
        
        mock_document.return_value = mock_doc
        
        # 執行測試
        result = self.parser.extract_content("test.docx")
        
        # 驗證結果
        assert isinstance(result, ParsedContent)
        assert len(result.text_blocks) == 2
        assert len(result.images) == 1
        assert result.metadata.filename == "test.docx"
        
        # 驗證文本塊
        text_block1 = result.text_blocks[0]
        assert text_block1.content == "這是第一段內容"
        assert text_block1.page == 1
        
        text_block2 = result.text_blocks[1]
        assert text_block2.content == "這是第二段內容"
        
        # 驗證圖片
        image = result.images[0]
        assert image.data == b'fake_image_data'
        assert image.format == 'JPEG'
        assert image.filename == 'test_image.jpg'
    
    @patch('src.parsers.word_parser.docx.Document')
    def test_extract_content_file_not_found(self, mock_document):
        """測試文件不存在的情況"""
        mock_document.side_effect = FileNotFoundError("文件不存在")
        
        with pytest.raises(FileNotFoundError):
            self.parser.extract_content("nonexistent.docx")
    
    @patch('src.parsers.word_parser.docx.Document')
    def test_extract_content_corrupted_word(self, mock_document):
        """測試損壞的Word文件"""
        mock_document.side_effect = Exception("Word文件損壞")
        
        with pytest.raises(Exception):
            self.parser.extract_content("corrupted.docx")
    
    @patch('src.parsers.word_parser.docx.Document')
    def test_extract_content_empty_word(self, mock_document):
        """測試空Word文件"""
        mock_doc = Mock()
        mock_doc.paragraphs = []
        mock_doc.inline_shapes = []
        mock_doc.tables = []
        
        mock_properties = Mock()
        mock_properties.title = ""
        mock_properties.author = ""
        mock_doc.core_properties = mock_properties
        
        mock_document.return_value = mock_doc
        
        result = self.parser.extract_content("empty.docx")
        
        assert isinstance(result, ParsedContent)
        assert len(result.text_blocks) == 0
        assert len(result.images) == 0
        assert result.metadata.filename == "empty.docx"
    
    @patch('src.parsers.word_parser.docx.Document')
    def test_extract_tables(self, mock_document):
        """測試表格提取"""
        mock_doc = Mock()
        mock_doc.paragraphs = []
        mock_doc.inline_shapes = []
        
        # 模擬表格
        mock_table = Mock()
        mock_row1 = Mock()
        mock_row2 = Mock()
        
        mock_cell1 = Mock()
        mock_cell1.text = "標題1"
        mock_cell2 = Mock()
        mock_cell2.text = "標題2"
        mock_row1.cells = [mock_cell1, mock_cell2]
        
        mock_cell3 = Mock()
        mock_cell3.text = "數據1"
        mock_cell4 = Mock()
        mock_cell4.text = "數據2"
        mock_row2.cells = [mock_cell3, mock_cell4]
        
        mock_table.rows = [mock_row1, mock_row2]
        mock_doc.tables = [mock_table]
        
        mock_properties = Mock()
        mock_doc.core_properties = mock_properties
        
        mock_document.return_value = mock_doc
        
        result = self.parser.extract_content("table.docx")
        
        assert isinstance(result, ParsedContent)
        assert len(result.tables) == 1
        
        table = result.tables[0]
        assert len(table.rows) == 2
        assert len(table.rows[0]) == 2
        assert table.rows[0][0] == "標題1"
        assert table.rows[1][1] == "數據2"
    
    def test_extract_styles(self):
        """測試樣式提取"""
        with patch('src.parsers.word_parser.docx.Document') as mock_document:
            mock_doc = Mock()
            
            # 模擬不同樣式的段落
            mock_heading = Mock()
            mock_heading.text = "這是標題"
            mock_heading.style.name = "Heading 1"
            
            mock_normal = Mock()
            mock_normal.text = "這是正文"
            mock_normal.style.name = "Normal"
            
            mock_doc.paragraphs = [mock_heading, mock_normal]
            mock_doc.inline_shapes = []
            mock_doc.tables = []
            mock_doc.core_properties = Mock()
            
            mock_document.return_value = mock_doc
            
            result = self.parser.extract_content("styled.docx")
            
            # 驗證標題識別
            heading_block = next((b for b in result.text_blocks if "標題" in b.content), None)
            assert heading_block is not None
            assert heading_block.style == "Heading 1"
    
    @pytest.mark.parametrize("file_extension,expected_valid", [
        (".docx", True),
        (".doc", True),
        (".txt", False),
        (".pdf", False),
    ])
    def test_file_format_validation(self, file_extension, expected_valid):
        """測試文件格式驗證"""
        result = self.parser.is_supported_format(f"test{file_extension}")
        assert result == expected_valid
    
    def test_text_cleaning_word_specific(self):
        """測試Word特定的文本清理"""
        # Word文檔可能包含特殊字符
        dirty_text = "這是\x0b測試\x0c文字\x0d\x0a"
        clean_text = self.parser._clean_text(dirty_text)
        assert "\x0b" not in clean_text
        assert "\x0c" not in clean_text
        assert clean_text == "這是 測試 文字"
    
    @pytest.mark.slow
    def test_performance_large_document(self, performance_timer):
        """測試大文檔處理性能"""
        with patch('src.parsers.word_parser.docx.Document') as mock_document:
            mock_doc = Mock()
            
            # 模擬大量段落
            mock_paragraphs = []
            for i in range(1000):
                mock_para = Mock()
                mock_para.text = f"這是第{i+1}段內容"
                mock_para.style.name = "Normal"
                mock_paragraphs.append(mock_para)
            
            mock_doc.paragraphs = mock_paragraphs
            mock_doc.inline_shapes = []
            mock_doc.tables = []
            mock_doc.core_properties = Mock()
            
            mock_document.return_value = mock_doc
            
            # 性能測試
            performance_timer.start()
            result = self.parser.extract_content("large.docx")
            performance_timer.stop()
            
            # 驗證結果和性能
            assert len(result.text_blocks) == 1000
            performance_timer.assert_under(3.0)  # 應在3秒內完成


@pytest.mark.unit
@pytest.mark.parser
class TestWordParserIntegration:
    """Word解析器集成測試"""
    
    def test_real_docx_structure(self, create_test_docx):
        """測試真實DOCX文件結構解析"""
        parser = WordParser()
        
        # 由於create_test_docx創建的是模擬DOCX，這裡只測試錯誤處理
        with pytest.raises(Exception):  # 期望解析失敗
            parser.extract_content(str(create_test_docx))
    
    def test_supported_formats(self):
        """測試支持的格式"""
        parser = WordParser()
        supported = parser.get_supported_formats()
        
        assert 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in supported
        assert 'application/msword' in supported
        assert '.docx' in supported
        assert '.doc' in supported
