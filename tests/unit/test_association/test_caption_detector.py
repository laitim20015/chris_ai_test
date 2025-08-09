"""
Caption檢測器單元測試

測試圖片標題檢測的核心算法。
"""

import pytest
from unittest.mock import Mock

from src.association.caption_detector import CaptionDetector
from src.parsers.base import TextBlock, ImageContent, BoundingBox


class TestCaptionDetector:
    """Caption檢測器測試類"""
    
    def setup_method(self):
        """設置測試方法"""
        self.detector = CaptionDetector()
    
    def test_detector_initialization(self):
        """測試檢測器初始化"""
        assert self.detector is not None
        assert hasattr(self.detector, 'detect_captions')
        assert len(self.detector.caption_patterns) > 0
    
    @pytest.mark.parametrize("text_content,expected_score", [
        ("圖1顯示了銷售趨勢", 0.9),
        ("Figure 1 shows the trend", 0.9),
        ("如圖2所示", 0.9),
        ("見表3的詳細數據", 0.9),
        ("Chart 4 demonstrates", 0.9),
        ("這是普通文字內容", 0.1),
        ("", 0.1),
    ])
    def test_caption_pattern_matching(self, text_content, expected_score):
        """測試標題模式匹配"""
        text_block = TextBlock(
            id="test_text",
            content=text_content,
            page=1,
            bbox=BoundingBox(x1=100, y1=200, x2=400, y2=250),
            associated_images=[]
        )
        
        image = ImageContent(
            id="test_image",
            filename="test.jpg",
            data=b"fake_data",
            page=1,
            bbox=BoundingBox(x1=450, y1=200, x2=650, y2=350),
            format="JPEG",
            size=(200, 150)
        )
        
        score = self.detector._calculate_caption_score(text_block, image)
        assert abs(score - expected_score) < 0.1
    
    def test_position_based_caption_detection(self):
        """測試基於位置的標題檢測"""
        # 圖片下方的文字（典型的caption位置）
        text_below = TextBlock(
            id="text_below",
            content="這是圖片說明文字",
            page=1,
            bbox=BoundingBox(x1=450, y1=360, x2=650, y2=380),  # 在圖片下方
            associated_images=[]
        )
        
        # 圖片上方的文字
        text_above = TextBlock(
            id="text_above", 
            content="這是圖片說明文字",
            page=1,
            bbox=BoundingBox(x1=450, y1=180, x2=650, y2=200),  # 在圖片上方
            associated_images=[]
        )
        
        # 遠離圖片的文字
        text_far = TextBlock(
            id="text_far",
            content="這是圖片說明文字",
            page=1,
            bbox=BoundingBox(x1=100, y1=500, x2=300, y2=520),  # 遠離圖片
            associated_images=[]
        )
        
        image = ImageContent(
            id="test_image",
            filename="test.jpg",
            data=b"fake_data",
            page=1,
            bbox=BoundingBox(x1=450, y1=200, x2=650, y2=350),
            format="JPEG",
            size=(200, 150)
        )
        
        # 測試位置評分
        score_below = self.detector._calculate_position_score(text_below, image)
        score_above = self.detector._calculate_position_score(text_above, image)
        score_far = self.detector._calculate_position_score(text_far, image)
        
        # 下方文字應該得分最高（典型caption位置）
        assert score_below > score_above
        assert score_below > score_far
        assert score_above > score_far
    
    def test_alignment_based_detection(self):
        """測試基於對齊的檢測"""
        # 與圖片對齊的文字
        text_aligned = TextBlock(
            id="text_aligned",
            content="對齊的說明文字",
            page=1,
            bbox=BoundingBox(x1=450, y1=360, x2=650, y2=380),  # 與圖片左右對齊
            associated_images=[]
        )
        
        # 未對齊的文字
        text_misaligned = TextBlock(
            id="text_misaligned",
            content="未對齊的文字",
            page=1,
            bbox=BoundingBox(x1=100, y1=360, x2=300, y2=380),  # 左偏移
            associated_images=[]
        )
        
        image = ImageContent(
            id="test_image",
            filename="test.jpg",
            data=b"fake_data",
            page=1,
            bbox=BoundingBox(x1=450, y1=200, x2=650, y2=350),
            format="JPEG",
            size=(200, 150)
        )
        
        score_aligned = self.detector._calculate_alignment_score(text_aligned, image)
        score_misaligned = self.detector._calculate_alignment_score(text_misaligned, image)
        
        assert score_aligned > score_misaligned
    
    def test_detect_captions_full_workflow(self, sample_text_blocks, sample_images):
        """測試完整的caption檢測工作流程"""
        # 修改一個文本塊為明確的caption
        sample_text_blocks[1].content = "圖1：銷售趨勢分析圖表"
        
        results = self.detector.detect_captions(sample_text_blocks, sample_images)
        
        assert len(results) > 0
        
        # 驗證結果結構
        for result in results:
            assert 'text_block_id' in result
            assert 'image_id' in result
            assert 'caption_score' in result
            assert 'confidence' in result
            assert 0 <= result['caption_score'] <= 1
            assert 0 <= result['confidence'] <= 1
    
    def test_multiple_caption_candidates(self):
        """測試多個caption候選的處理"""
        text_blocks = [
            TextBlock(
                id="text_1",
                content="圖1顯示了銷售數據",  # 強caption
                page=1,
                bbox=BoundingBox(x1=450, y1=360, x2=650, y2=380),
                associated_images=[]
            ),
            TextBlock(
                id="text_2", 
                content="這是相關的說明文字",  # 弱caption
                page=1,
                bbox=BoundingBox(x1=450, y1=385, x2=650, y2=405),
                associated_images=[]
            ),
            TextBlock(
                id="text_3",
                content="無關的文字內容",  # 非caption
                page=1,
                bbox=BoundingBox(x1=100, y1=500, x2=300, y2=520),
                associated_images=[]
            )
        ]
        
        image = ImageContent(
            id="test_image",
            filename="test.jpg",
            data=b"fake_data",
            page=1,
            bbox=BoundingBox(x1=450, y1=200, x2=650, y2=350),
            format="JPEG",
            size=(200, 150)
        )
        
        results = self.detector.detect_captions(text_blocks, [image])
        
        # 應該返回按分數排序的結果
        assert len(results) >= 1
        
        # 最高分應該是明確的caption
        best_result = max(results, key=lambda x: x['caption_score'])
        assert best_result['text_block_id'] == "text_1"
        assert best_result['caption_score'] > 0.8
    
    def test_cross_page_caption_handling(self):
        """測試跨頁面caption處理"""
        text_block_page1 = TextBlock(
            id="text_p1",
            content="圖1在下一頁顯示",
            page=1,
            bbox=BoundingBox(x1=100, y1=200, x2=400, y2=250),
            associated_images=[]
        )
        
        text_block_page2 = TextBlock(
            id="text_p2",
            content="圖1：詳細分析圖表",
            page=2,
            bbox=BoundingBox(x1=450, y1=360, x2=650, y2=380),
            associated_images=[]
        )
        
        image_page2 = ImageContent(
            id="image_p2",
            filename="chart.jpg",
            data=b"fake_data",
            page=2,
            bbox=BoundingBox(x1=450, y1=200, x2=650, y2=350),
            format="JPEG",
            size=(200, 150)
        )
        
        results = self.detector.detect_captions(
            [text_block_page1, text_block_page2], 
            [image_page2]
        )
        
        # 同頁面的caption應該得分更高
        page2_results = [r for r in results if r['text_block_id'] == "text_p2"]
        page1_results = [r for r in results if r['text_block_id'] == "text_p1"]
        
        if page2_results and page1_results:
            assert page2_results[0]['caption_score'] > page1_results[0]['caption_score']
    
    @pytest.mark.parametrize("language,patterns", [
        ("zh", ["圖", "表", "如圖", "見圖"]),
        ("en", ["Figure", "Fig", "Table", "Chart"]),
    ])
    def test_multilingual_caption_patterns(self, language, patterns):
        """測試多語言caption模式"""
        # 這個測試假設CaptionDetector支持多語言模式
        detector = CaptionDetector(language=language)
        
        for pattern in patterns:
            text = f"{pattern} 1 shows the data"
            text_block = TextBlock(
                id="test",
                content=text,
                page=1,
                bbox=BoundingBox(x1=100, y1=200, x2=400, y2=250),
                associated_images=[]
            )
            
            image = ImageContent(
                id="test_image",
                filename="test.jpg", 
                data=b"fake_data",
                page=1,
                bbox=BoundingBox(x1=450, y1=200, x2=650, y2=350),
                format="JPEG",
                size=(200, 150)
            )
            
            score = detector._calculate_caption_score(text_block, image)
            assert score > 0.5  # 應該識別為caption
    
    def test_confidence_calculation(self):
        """測試信心度計算"""
        # 高信心度的caption
        high_confidence_text = TextBlock(
            id="high_conf",
            content="圖1：銷售趨勢分析圖表",
            page=1,
            bbox=BoundingBox(x1=450, y1=360, x2=650, y2=380),
            associated_images=[]
        )
        
        # 低信心度的caption
        low_confidence_text = TextBlock(
            id="low_conf",
            content="這可能是圖片說明",
            page=1,
            bbox=BoundingBox(x1=100, y1=500, x2=300, y2=520),
            associated_images=[]
        )
        
        image = ImageContent(
            id="test_image",
            filename="test.jpg",
            data=b"fake_data",
            page=1,
            bbox=BoundingBox(x1=450, y1=200, x2=650, y2=350),
            format="JPEG",
            size=(200, 150)
        )
        
        high_conf_result = self.detector.detect_captions([high_confidence_text], [image])[0]
        low_conf_result = self.detector.detect_captions([low_confidence_text], [image])[0]
        
        assert high_conf_result['confidence'] > low_conf_result['confidence']
        assert high_conf_result['confidence'] > 0.8
        assert low_conf_result['confidence'] < 0.5
    
    def test_edge_cases(self):
        """測試邊界情況"""
        # 空文本
        empty_text = TextBlock(
            id="empty",
            content="",
            page=1,
            bbox=BoundingBox(x1=100, y1=200, x2=400, y2=250),
            associated_images=[]
        )
        
        # 超長文本
        long_text = TextBlock(
            id="long",
            content="這是一段非常長的文字" * 100,
            page=1,
            bbox=BoundingBox(x1=100, y1=200, x2=400, y2=250),
            associated_images=[]
        )
        
        image = ImageContent(
            id="test_image",
            filename="test.jpg",
            data=b"fake_data",
            page=1,
            bbox=BoundingBox(x1=450, y1=200, x2=650, y2=350),
            format="JPEG",
            size=(200, 150)
        )
        
        # 不應該拋出異常
        empty_results = self.detector.detect_captions([empty_text], [image])
        long_results = self.detector.detect_captions([long_text], [image])
        
        assert isinstance(empty_results, list)
        assert isinstance(long_results, list)


@pytest.mark.unit
@pytest.mark.association
class TestCaptionDetectorPerformance:
    """Caption檢測器性能測試"""
    
    def test_large_dataset_performance(self, performance_timer):
        """測試大數據集性能"""
        detector = CaptionDetector()
        
        # 創建大量測試數據
        text_blocks = []
        images = []
        
        for i in range(100):
            text_blocks.append(TextBlock(
                id=f"text_{i}",
                content=f"這是第{i}段文字內容",
                page=i // 10 + 1,
                bbox=BoundingBox(x1=100, y1=200+i*10, x2=400, y2=250+i*10),
                associated_images=[]
            ))
            
            if i % 10 == 0:  # 每10個文本塊一個圖片
                images.append(ImageContent(
                    id=f"image_{i}",
                    filename=f"test_{i}.jpg",
                    data=b"fake_data",
                    page=i // 10 + 1,
                    bbox=BoundingBox(x1=450, y1=200+i*10, x2=650, y2=350+i*10),
                    format="JPEG",
                    size=(200, 150)
                ))
        
        # 性能測試
        performance_timer.start()
        results = detector.detect_captions(text_blocks, images)
        performance_timer.stop()
        
        # 應該在合理時間內完成
        performance_timer.assert_under(2.0)
        assert len(results) > 0
