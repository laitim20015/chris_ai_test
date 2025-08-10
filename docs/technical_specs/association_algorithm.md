# 圖文關聯算法技術規格
## Association Algorithm Technical Specification

**版本**：v1.2  
**創建日期**：2025年8月10日  
**負責人**：智能文檔轉換系統開發團隊

---

## 1. 算法概述

智能文檔轉換系統的圖文關聯算法是基於多層次分析的綜合評分模型，旨在建立文本段落與圖片之間的精準關聯關係。該算法融合了Caption檢測、空間關係分析、語義相似度計算等多種技術。

### 1.1 核心目標

- **準確性**：圖文關聯準確率 ≥ 85%
- **效率**：單文檔處理時間 < 30秒
- **可擴展性**：支持多種文檔格式和複雜佈局
- **可解釋性**：提供詳細的關聯度評分解釋

### 1.2 技術架構

```
輸入文檔
    ↓
文檔解析 (PyMuPDF/pymupdf4llm)
    ↓
內容提取 (文本塊 + 圖片)
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   Caption檢測    │   空間關係分析   │   語義相似度    │
│    (40%權重)    │    (30%權重)    │    (15%權重)   │
└─────────────────┴─────────────────┴─────────────────┘
    ↓                ↓                ↓
┌─────────────────┬─────────────────┐
│   佈局模式分析   │   距離計算       │
│    (10%權重)    │    (5%權重)     │
└─────────────────┴─────────────────┘
    ↓
加權融合評分
    ↓
關聯優化 (去重/過濾)
    ↓
最終關聯結果
```

---

## 2. 核心算法組件

### 2.1 Caption檢測算法 (40%權重)

Caption檢測是最重要的關聯指標，負責識別文本中對圖片的直接引用。

#### 2.1.1 正則表達式模式

```python
CAPTION_PATTERNS = [
    r'^(Figure|Fig|圖|表|Table)\s*\d+',        # 圖表標號
    r'^(Chart|Diagram|Image)\s*\d+',           # 圖表類型
    r'如圖\s*\d+|見圖\s*\d+',                    # 中文引用
    r'(圖片|圖像|示意圖)\s*\d*',                  # 通用圖片引用
    r'(上圖|下圖|左圖|右圖)',                     # 位置引用
]
```

#### 2.1.2 置信度計算

```python
def calculate_caption_confidence(matches: List[CaptionMatch]) -> float:
    """
    計算Caption檢測置信度
    
    規則：
    - 完全匹配標號：0.9
    - 位置引用：0.7
    - 通用引用：0.5
    - 無匹配：0.1
    """
    if not matches:
        return 0.1
    
    max_confidence = max(match.confidence for match in matches)
    
    # 應用位置權重
    position_boost = calculate_position_boost(matches)
    
    return min(1.0, max_confidence * position_boost)
```

### 2.2 Allen時間間隔邏輯空間分析 (30%權重)

基於Allen的13種時間間隔關係，擴展到2D空間進行圖文空間關係分析。

#### 2.2.1 Allen關係映射

| 時間關係 | 空間關係 | 描述 | 權重 |
|---------|---------|------|------|
| precedes | left-of | A在B左側 | 0.6 |
| meets | adjacent-left | A與B左鄰 | 0.8 |
| overlaps | overlaps-horizontal | A與B水平重疊 | 0.9 |
| during | inside | A在B內部 | 0.7 |
| above | above | A在B上方 | 0.8 |
| below | below | A在B下方 | 0.8 |

#### 2.2.2 空間特徵計算

```python
@dataclass
class SpatialFeatures:
    center_distance: float        # 中心點距離
    min_distance: float          # 最小邊界距離
    overlap_ratio: float         # 重疊比例
    alignment_score: float       # 對齊分數
    reading_order: float         # 閱讀順序分數
    relation_type: str          # Allen關係類型
```

### 2.3 語義相似度分析 (15%權重)

使用sentence-transformers計算文本內容與圖片描述的語義相似度。

#### 2.3.1 文本嵌入

```python
def get_text_embedding(text: str) -> np.ndarray:
    """
    獲取文本嵌入向量
    
    模型：all-MiniLM-L6-v2 (384維)
    回退：確定性零向量 (避免隨機性)
    """
    if self.model is None:
        return np.zeros(384, dtype=np.float32)
    
    return self.model.encode(text)
```

#### 2.3.2 相似度計算

```python
def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    計算語義相似度 (餘弦相似度)
    
    範圍：[0, 1]
    閾值：>0.3 為有意義的相似性
    """
    emb1 = get_text_embedding(text1)
    emb2 = get_text_embedding(text2)
    
    # 餘弦相似度
    similarity = np.dot(emb1, emb2) / (
        np.linalg.norm(emb1) * np.linalg.norm(emb2)
    )
    
    return max(0.0, similarity)  # 確保非負
```

### 2.4 佈局模式分析 (10%權重)

分析文檔的佈局模式，如多欄位、表格、列表等結構對圖文關聯的影響。

#### 2.4.1 佈局特徵

- **欄位檢測**：識別多欄位佈局
- **段落結構**：分析段落層次關係
- **表格識別**：檢測表格內的圖文關聯
- **列表模式**：處理有序/無序列表

### 2.5 距離計算 (5%權重)

計算文本塊與圖片之間的物理距離，作為輔助指標。

```python
def calculate_proximity_score(text_bbox: BoundingBox, 
                            image_bbox: BoundingBox) -> float:
    """
    計算距離評分
    
    公式：score = 1.0 - min(distance / max_distance, 1.0)
    max_distance = 500px (可配置)
    """
    distance = calculate_min_distance(text_bbox, image_bbox)
    max_distance = 500.0
    
    return 1.0 - min(distance / max_distance, 1.0)
```

---

## 3. 加權融合評分模型

### 3.1 權重配置

根據項目規則，各組件權重嚴格按照以下配置：

```python
DEFAULT_WEIGHTS = {
    "caption_score": 0.4,      # Caption檢測（最高）
    "spatial_score": 0.3,      # 空間關係
    "semantic_score": 0.15,    # 語義相似度
    "layout_score": 0.1,       # 佈局模式
    "proximity_score": 0.05,   # 距離權重
}

# 權重約束
assert sum(DEFAULT_WEIGHTS.values()) == 1.0
assert DEFAULT_WEIGHTS["caption_score"] == max(DEFAULT_WEIGHTS.values())
```

### 3.2 最終評分計算

```python
def calculate_final_score(caption_score: float,
                         spatial_score: float,
                         semantic_score: float,
                         layout_score: float,
                         proximity_score: float) -> float:
    """
    計算最終關聯度評分
    
    範圍：[0, 1]
    閾值：>0.4 為有效關聯
    """
    final_score = (
        caption_score * 0.4 +
        spatial_score * 0.3 +
        semantic_score * 0.15 +
        layout_score * 0.1 +
        proximity_score * 0.05
    )
    
    return min(1.0, max(0.0, final_score))
```

---

## 4. 關聯優化策略

### 4.1 過度關聯問題

原始算法可能產生過多關聯（如7張圖片產生2534個關聯），需要智能優化。

### 4.2 優化機制

#### 4.2.1 質量分級

```python
class AssociationQuality(Enum):
    EXCELLENT = "excellent"    # 0.8+
    GOOD = "good"             # 0.6-0.8
    FAIR = "fair"             # 0.4-0.6
    POOR = "poor"             # 0.2-0.4
    INVALID = "invalid"       # <0.2
```

#### 4.2.2 數量控制

- **每圖限制**：最多5個關聯
- **總數限制**：最多100個關聯
- **閾值過濾**：分數<0.4自動過濾

#### 4.2.3 去重策略

```python
def deduplicate_associations(associations: List[Dict]) -> List[Dict]:
    """
    關聯去重處理
    
    規則：
    1. 移除重複的文本-圖片組合
    2. 保留最高分數的關聯
    3. Caption檢測優先保留
    """
    seen_combinations = set()
    deduplicated = []
    
    # 按分數排序
    sorted_assocs = sorted(associations, 
                          key=lambda x: x["final_score"], 
                          reverse=True)
    
    for assoc in sorted_assocs:
        key = (assoc["text_block_id"], assoc["image_id"])
        if key not in seen_combinations:
            deduplicated.append(assoc)
            seen_combinations.add(key)
    
    return deduplicated
```

---

## 5. 性能指標與基準

### 5.1 處理性能

- **單文檔處理**：< 30秒 (10MB文件)
- **關聯分析**：< 5秒 (100個文本塊 + 10張圖片)
- **內存使用**：< 2GB (100MB文件)

### 5.2 準確性指標

- **關聯準確率**：≥ 85%
- **Caption檢測**：≥ 90%
- **假陽性率**：< 10%
- **假陰性率**：< 15%

### 5.3 基準測試

使用性能基準測試模組定期評估：

```python
from src.utils.performance_benchmarks import profile

@profile("association_analysis")
def perform_association_analysis(text_blocks, images):
    # 執行關聯分析
    pass
```

---

## 6. 配置與調優

### 6.1 可調參數

```python
@dataclass
class AssociationConfig:
    min_score_threshold: float = 0.4
    max_associations_per_image: int = 5
    caption_boost_factor: float = 1.2
    spatial_weight_multiplier: float = 1.0
    semantic_threshold: float = 0.3
```

### 6.2 A/B測試框架

支援不同配置的對比測試：

```python
def ab_test_configurations(config_a: AssociationConfig,
                          config_b: AssociationConfig,
                          test_documents: List[str]) -> Dict:
    """
    A/B測試不同配置的效果
    """
    pass
```

---

## 7. 錯誤處理與容錯

### 7.1 異常處理

- **解析失敗**：使用備用解析器
- **模型加載失敗**：回退到確定性零向量
- **內存不足**：分塊處理大文檔

### 7.2 質量保證

- **結果驗證**：檢查關聯度分數範圍
- **一致性檢查**：確保權重總和為1.0
- **性能監控**：實時監控處理時間和內存使用

---

## 8. 未來改進方向

### 8.1 機器學習增強

- **深度學習模型**：使用BERT/GPT進行更精確的語義分析
- **圖像理解**：集成CLIP/BLIP進行圖像內容理解
- **端到端訓練**：訓練專門的圖文關聯模型

### 8.2 多模態融合

- **視覺特徵**：提取圖像視覺特徵進行匹配
- **OCR整合**：識別圖片中的文字內容
- **表格解析**：專門處理表格內的圖文關聯

### 8.3 用戶反饋學習

- **主動學習**：根據用戶反饋調整權重
- **個性化**：為不同類型文檔學習專門的配置
- **持續改進**：建立反饋循環機制

---

**文檔版本**：v1.2  
**最後更新**：2025年8月10日  
**審核狀態**：✅ 已審核  
**相關文件**：
- `src/association/` - 算法實現代碼
- `docs/api/association_api.md` - API文檔
- `tests/unit/test_association/` - 單元測試
