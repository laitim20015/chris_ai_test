"""
空間分析器單元測試

測試基於Allen區間邏輯的空間關係分析。
"""

import pytest
import numpy as np
from unittest.mock import Mock

from src.association.spatial_analyzer import SpatialAnalyzer
from src.association.allen_logic import AllenLogic
from src.parsers.base import TextBlock, ImageContent, BoundingBox


class TestSpatialAnalyzer:
    """空間分析器測試類"""
    
    def setup_method(self):
        """設置測試方法"""
        self.analyzer = SpatialAnalyzer()
    
    def test_analyzer_initialization(self):
        """測試分析器初始化"""
        assert self.analyzer is not None
        assert hasattr(self.analyzer, 'analyze_spatial_relations')
        assert isinstance(self.analyzer.allen_logic, AllenLogic)
    
    def test_distance_calculation(self):
        """測試距離計算"""
        text_bbox = BoundingBox(x1=100, y1=200, x2=300, y2=250)
        image_bbox = BoundingBox(x1=400, y1=200, x2=600, y2=350)
        
        # 測試最小距離
        min_distance = self.analyzer._calculate_minimum_distance(text_bbox, image_bbox)
        assert min_distance == 100  # 400 - 300 = 100
        
        # 測試中心距離
        center_distance = self.analyzer._calculate_center_distance(text_bbox, image_bbox)
        text_center = (200, 225)  # ((100+300)/2, (200+250)/2)
        image_center = (500, 275)  # ((400+600)/2, (200+350)/2)
        expected_distance = np.sqrt((500-200)**2 + (275-225)**2)
        assert abs(center_distance - expected_distance) < 0.1
    
    def test_alignment_detection(self):
        """測試對齊檢測"""
        # 水平對齊的元素
        text_bbox = BoundingBox(x1=100, y1=200, x2=300, y2=250)
        image_bbox_aligned = BoundingBox(x1=400, y1=210, x2=600, y2=240)  # 垂直對齊
        image_bbox_misaligned = BoundingBox(x1=400, y1=300, x2=600, y2=350)  # 不對齊
        
        # 測試水平對齊
        h_alignment_aligned = self.analyzer._check_horizontal_alignment(text_bbox, image_bbox_aligned)
        h_alignment_misaligned = self.analyzer._check_horizontal_alignment(text_bbox, image_bbox_misaligned)
        
        assert h_alignment_aligned > h_alignment_misaligned
        assert h_alignment_aligned > 0.7  # 高對齊度
        
        # 垂直對齊測試
        text_bbox_v = BoundingBox(x1=200, y1=100, x2=250, y2=300)
        image_bbox_v_aligned = BoundingBox(x1=210, y1=400, x2=240, y2=600)  # 水平對齊
        
        v_alignment = self.analyzer._check_vertical_alignment(text_bbox_v, image_bbox_v_aligned)
        assert v_alignment > 0.7
    
    def test_allen_relation_detection(self):
        """測試Allen邏輯關係檢測"""
        # Before關係
        text_bbox = BoundingBox(x1=100, y1=200, x2=200, y2=250)
        image_bbox = BoundingBox(x1=300, y1=200, x2=400, y2=250)
        
        relation = self.analyzer._get_allen_relation(text_bbox, image_bbox)
        assert "before" in relation or "precedes" in relation
        
        # Overlaps關係
        text_bbox_overlap = BoundingBox(x1=100, y1=200, x2=250, y2=300)
        image_bbox_overlap = BoundingBox(x1=200, y1=250, x2=350, y2=400)
        
        relation_overlap = self.analyzer._get_allen_relation(text_bbox_overlap, image_bbox_overlap)
        assert "overlaps" in relation_overlap or "overlap" in relation_overlap
    
    def test_layout_pattern_analysis(self):
        """測試佈局模式分析"""
        # 創建多欄佈局模式
        text_blocks = [
            TextBlock(
                id="text_1",
                content="左欄文字",
                page=1,
                bbox=BoundingBox(x1=100, y1=200, x2=300, y2=250),
                associated_images=[]
            ),
            TextBlock(
                id="text_2",
                content="右欄文字",
                page=1,
                bbox=BoundingBox(x1=400, y1=200, x2=600, y2=250),
                associated_images=[]
            )
        ]
        
        images = [
            ImageContent(
                id="image_1",
                filename="test1.jpg",
                data=b"fake_data",
                page=1,
                bbox=BoundingBox(x1=100, y1=300, x2=300, y2=450),
                format="JPEG",
                size=(200, 150)
            )
        ]
        
        layout_info = self.analyzer._analyze_layout_patterns(text_blocks, images)
        
        assert 'column_count' in layout_info
        assert 'text_columns' in layout_info
        assert 'image_placement' in layout_info
        assert layout_info['column_count'] >= 2  # 應該檢測到多欄
    
    def test_reading_order_analysis(self):
        """測試閱讀順序分析"""
        # 創建從左到右、從上到下的佈局
        elements = [
            {'bbox': BoundingBox(x1=100, y1=100, x2=200, y2=150), 'type': 'text', 'id': 'text_1'},
            {'bbox': BoundingBox(x1=300, y1=100, x2=400, y2=150), 'type': 'text', 'id': 'text_2'}, 
            {'bbox': BoundingBox(x1=100, y1=200, x2=200, y2=250), 'type': 'image', 'id': 'image_1'},
            {'bbox': BoundingBox(x1=300, y1=200, x2=400, y2=250), 'type': 'text', 'id': 'text_3'}
        ]
        
        reading_order = self.analyzer._determine_reading_order(elements)
        
        # 驗證順序：應該是從上到下，從左到右
        assert len(reading_order) == 4
        assert reading_order[0]['id'] in ['text_1', 'text_2']  # 第一行的元素
        assert reading_order[-1]['id'] in ['image_1', 'text_3']  # 第二行的元素
    
    def test_spatial_features_extraction(self):
        """測試空間特徵提取"""
        text_block = TextBlock(
            id="test_text",
            content="測試文字",
            page=1,
            bbox=BoundingBox(x1=100, y1=200, x2=300, y2=250),
            associated_images=[]
        )
        
        image = ImageContent(
            id="test_image",
            filename="test.jpg",
            data=b"fake_data",
            page=1,
            bbox=BoundingBox(x1=400, y1=200, x2=600, y2=350),
            format="JPEG",
            size=(200, 150)
        )
        
        features = self.analyzer.extract_spatial_features(text_block, image)
        
        # 驗證特徵完整性
        required_features = [
            'distance', 'center_distance', 'horizontal_alignment', 
            'vertical_alignment', 'allen_relation', 'relative_position',
            'size_ratio', 'aspect_ratio_similarity'
        ]
        
        for feature in required_features:
            assert feature in features
            assert isinstance(features[feature], (int, float, str, list))
    
    def test_analyze_spatial_relations_full_workflow(self, sample_text_blocks, sample_images):
        """測試完整的空間關係分析工作流程"""
        results = self.analyzer.analyze_spatial_relations(sample_text_blocks, sample_images)
        
        assert len(results) > 0
        
        # 驗證結果結構
        for result in results:
            assert 'text_block_id' in result
            assert 'image_id' in result
            assert 'spatial_score' in result
            assert 'features' in result
            assert 0 <= result['spatial_score'] <= 1
            
            # 驗證特徵結構
            features = result['features']
            assert isinstance(features, dict)
            assert 'distance' in features
            assert 'allen_relation' in features
    
    @pytest.mark.parametrize("text_pos,image_pos,expected_relation", [
        # 文字在圖片左邊
        ((100, 200, 200, 250), (300, 200, 400, 250), "before"),
        # 文字在圖片右邊  
        ((300, 200, 400, 250), (100, 200, 200, 250), "after"),
        # 文字在圖片上方
        ((200, 100, 300, 150), (200, 200, 300, 250), "above"),
        # 文字在圖片下方
        ((200, 300, 300, 350), (200, 200, 300, 250), "below"),
    ])
    def test_relative_position_detection(self, text_pos, image_pos, expected_relation):
        """測試相對位置檢測"""
        text_bbox = BoundingBox(*text_pos)
        image_bbox = BoundingBox(*image_pos)
        
        relative_pos = self.analyzer._get_relative_position(text_bbox, image_bbox)
        assert expected_relation in relative_pos.lower()
    
    def test_size_and_aspect_ratio_analysis(self):
        """測試尺寸和縱橫比分析"""
        text_bbox = BoundingBox(x1=100, y1=200, x2=300, y2=250)  # 200x50
        image_bbox = BoundingBox(x1=400, y1=200, x2=600, y2=400)  # 200x200
        
        size_ratio = self.analyzer._calculate_size_ratio(text_bbox, image_bbox)
        aspect_similarity = self.analyzer._calculate_aspect_ratio_similarity(text_bbox, image_bbox)
        
        # 文字區域 (200x50) vs 圖片區域 (200x200)
        # 面積比: (200*50) / (200*200) = 0.25
        assert abs(size_ratio - 0.25) < 0.01
        
        # 縱橫比相似度應該較低（4:1 vs 1:1）
        assert aspect_similarity < 0.5
    
    def test_multi_page_spatial_analysis(self):
        """測試多頁面空間分析"""
        text_blocks = [
            TextBlock(
                id="text_p1",
                content="第一頁文字",
                page=1,
                bbox=BoundingBox(x1=100, y1=200, x2=300, y2=250),
                associated_images=[]
            ),
            TextBlock(
                id="text_p2",
                content="第二頁文字", 
                page=2,
                bbox=BoundingBox(x1=100, y1=200, x2=300, y2=250),
                associated_images=[]
            )
        ]
        
        images = [
            ImageContent(
                id="image_p1",
                filename="page1.jpg",
                data=b"fake_data",
                page=1,
                bbox=BoundingBox(x1=400, y1=200, x2=600, y2=350),
                format="JPEG", 
                size=(200, 150)
            ),
            ImageContent(
                id="image_p2",
                filename="page2.jpg",
                data=b"fake_data",
                page=2,
                bbox=BoundingBox(x1=400, y1=200, x2=600, y2=350),
                format="JPEG",
                size=(200, 150)
            )
        ]
        
        results = self.analyzer.analyze_spatial_relations(text_blocks, images)
        
        # 同頁面的關聯應該得分更高
        same_page_results = [r for r in results if r['text_block_id'] == 'text_p1' and r['image_id'] == 'image_p1']
        cross_page_results = [r for r in results if r['text_block_id'] == 'text_p1' and r['image_id'] == 'image_p2']
        
        if same_page_results and cross_page_results:
            assert same_page_results[0]['spatial_score'] > cross_page_results[0]['spatial_score']
    
    def test_edge_cases_and_robustness(self):
        """測試邊界情況和魯棒性"""
        # 零尺寸邊界框
        zero_bbox = BoundingBox(x1=100, y1=200, x2=100, y2=200)
        normal_bbox = BoundingBox(x1=200, y1=300, x2=300, y2=400)
        
        # 不應該拋出異常
        distance = self.analyzer._calculate_minimum_distance(zero_bbox, normal_bbox)
        assert distance >= 0
        
        # 重疊的邊界框
        bbox1 = BoundingBox(x1=100, y1=200, x2=300, y2=400)
        bbox2 = BoundingBox(x1=200, y1=300, x2=400, y2=500)
        
        overlap_distance = self.analyzer._calculate_minimum_distance(bbox1, bbox2)
        assert overlap_distance == 0  # 重疊時距離為0
        
        # 空列表輸入
        empty_results = self.analyzer.analyze_spatial_relations([], [])
        assert empty_results == []
    
    @pytest.mark.slow
    def test_performance_large_dataset(self, performance_timer):
        """測試大數據集性能"""
        # 創建大量測試數據
        text_blocks = []
        images = []
        
        for i in range(50):
            text_blocks.append(TextBlock(
                id=f"text_{i}",
                content=f"文字{i}",
                page=i // 10 + 1,
                bbox=BoundingBox(x1=100+i*10, y1=200, x2=200+i*10, y2=250),
                associated_images=[]
            ))
        
        for i in range(10):
            images.append(ImageContent(
                id=f"image_{i}",
                filename=f"test_{i}.jpg",
                data=b"fake_data",
                page=i // 2 + 1,
                bbox=BoundingBox(x1=400+i*20, y1=200, x2=500+i*20, y2=350),
                format="JPEG",
                size=(100, 150)
            ))
        
        # 性能測試
        performance_timer.start()
        results = self.analyzer.analyze_spatial_relations(text_blocks, images)
        performance_timer.stop()
        
        # 應該在合理時間內完成（50個文字 × 10個圖片 = 500個關係）
        performance_timer.assert_under(3.0)
        assert len(results) == 500  # 50 * 10 = 500 個關係分析


@pytest.mark.unit
@pytest.mark.association
class TestSpatialAnalyzerIntegration:
    """空間分析器集成測試"""
    
    def test_integration_with_allen_logic(self):
        """測試與Allen邏輯的集成"""
        analyzer = SpatialAnalyzer()
        
        # 測試Allen邏輯實例可用
        assert analyzer.allen_logic is not None
        
        # 測試基本Allen關係計算
        interval1 = (100, 200)
        interval2 = (150, 250)
        
        relation = analyzer.allen_logic.get_relation(interval1, interval2)
        assert relation in analyzer.allen_logic.relations
    
    def test_coordinate_system_consistency(self):
        """測試坐標系統一致性"""
        analyzer = SpatialAnalyzer()
        
        # 確保所有計算使用一致的坐標系統（左上角為原點）
        bbox1 = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        bbox2 = BoundingBox(x1=100, y1=100, x2=200, y2=200)
        
        # 測試距離計算的一致性
        distance = analyzer._calculate_minimum_distance(bbox1, bbox2)
        assert distance == 0  # 對角相鄰，最小距離應為0
        
        # 測試中心距離
        center_distance = analyzer._calculate_center_distance(bbox1, bbox2)
        expected = np.sqrt((150-50)**2 + (150-50)**2)  # 對角距離
        assert abs(center_distance - expected) < 0.1
