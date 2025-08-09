# 📋 智能文檔轉換與RAG知識庫系統 - 詳細TODO任務清單

**文檔版本**: v1.0  
**創建日期**: 2025年8月9日  
**最後更新**: 2025年8月9日  
**狀態**: 待執行

---

## 🎯 總覽

基於完整分析報告，按優先級和執行順序整理的詳細任務清單。目標是將系統從當前的75%規格對齊度提升到95%以上，並解決所有架構風險和隱藏問題。

### 📊 任務統計
- **總任務數**: 12個主要任務
- **預估總工時**: 60-80小時
- **執行週期**: 3週
- **優先級分佈**: P0(3項) | P1(4項) | P2(5項)

---

## 🚨 Phase 1: 緊急修復 (P0) - 1-2天

### **Task 1.1: 修復DocumentProcessor API漂移問題** 🔴
**ID**: `fix_document_processor_api`  
**優先級**: P0 - 緊急  
**預估時間**: 4-6小時  
**負責模組**: `src/main.py`  
**狀態**: ⏳ 待執行

#### **問題描述**
DocumentProcessor._perform_association_analysis 使用的API與實際組件API完全不匹配，導致主要入口無法正常工作。

#### **詳細子任務**
- [ ] **1.1.1 修復Caption檢測API調用** (1.5小時)
  ```python
  # 修改 src/main.py L180-182
  # FROM: caption_score = self.caption_detector.detect_caption_relationship(...)
  # TO: caption_matches = self.caption_detector.detect_captions(
  #       text_block.content, text_block.bbox, image.bbox)
  #     caption_score = max((match.confidence for match in caption_matches), default=0.0)
  ```

- [ ] **1.1.2 修復空間分析API調用** (1.5小時)
  ```python
  # 修改 src/main.py L185-187
  # FROM: spatial_analysis = self.spatial_analyzer.analyze_spatial_relationship(...)
  # TO: spatial_features = self.spatial_analyzer.calculate_spatial_features(
  #       text_block.bbox, image.bbox)
  ```

- [ ] **1.1.3 修復語義分析API調用** (1小時)
  ```python
  # 修改 src/main.py L190-193
  # FROM: semantic_score = self.semantic_analyzer.calculate_semantic_similarity(...)
  # TO: semantic_score = self.semantic_analyzer.calculate_similarity(
  #       text_block.content, image.alt_text or f"Image {image.id}")
  ```

- [ ] **1.1.4 修復關聯評分調用** (1小時)
  ```python
  # 修改 src/main.py L196-202
  # 確保正確處理元組返回值和空間特徵屬性
  # 處理 spatial_features 的屬性訪問
  ```

#### **驗收標準**
- [ ] `DocumentProcessor.process_document()` 能成功執行不報錯
- [ ] 返回結果格式與規格文件一致
- [ ] 所有API調用使用正確的方法名和參數
- [ ] 單元測試全部通過

#### **風險與依賴**
- **風險**: API變更可能影響其他調用點
- **依賴**: 需要確保所有關聯組件API穩定
- **回滾計劃**: 保留原始代碼備份

---

### **Task 1.2: 建立生產入口端到端測試** 🔴
**ID**: `create_production_entry_test`  
**優先級**: P0 - 緊急  
**預估時間**: 2-3小時  
**負責模組**: `tests/integration/`  
**狀態**: ⏳ 待執行

#### **問題描述**
當前端到端測試繞過了DocumentProcessor主入口，需要建立真正的生產入口測試來確保API一致性。

#### **詳細子任務**
- [ ] **1.2.1 創建生產入口測試文件** (1小時)
  ```python
  # 創建 tests/integration/test_production_entry.py
  # 測試 DocumentProcessor.process_document() 完整流程
  ```

- [ ] **1.2.2 編寫關鍵測試案例** (1.5小時)
  - [ ] 正常文檔處理流程測試
  - [ ] 錯誤處理機制測試
  - [ ] 返回格式驗證測試
  - [ ] 性能基準測試

- [ ] **1.2.3 集成到CI/CD流程** (0.5小時)
  - [ ] 添加到pytest配置
  - [ ] 設置自動化運行觸發

#### **驗收標準**
- [ ] 生產入口測試100%通過
- [ ] 測試覆蓋DocumentProcessor主要方法
- [ ] 可以自動檢測API漂移問題
- [ ] 集成到自動化測試流程

---

### **Task 1.3: 解析器註冊警告修復** 🟡
**ID**: `fix_parser_registration_warning`  
**優先級**: P1 - 高  
**預估時間**: 1小時  
**負責模組**: `src/parsers/parser_factory.py`  
**狀態**: ⏳ 待執行

#### **問題描述**
解析器註冊時出現 `'ParserConfig' object has no attribute '__name__'` 警告，需要修復日誌記錄邏輯。

#### **詳細子任務**
- [ ] **1.3.1 修復日誌記錄屬性訪問** (0.5小時)
  ```python
  # 修改 src/parsers/parser_factory.py L85
  # FROM: f"註冊解析器: {parser_config.__name__}"
  # TO: f"註冊解析器: {parser_config.parser_class.__name__}"
  ```

- [ ] **1.3.2 統一解析器初始化** (0.5小時)
  - [ ] 檢查`parser_factory.py`和`__init__.py`的重複註冊
  - [ ] 合併到單一初始化點

#### **驗收標準**
- [ ] 無解析器註冊警告
- [ ] 所有解析器正常註冊和使用
- [ ] 日誌記錄清晰可讀

---

## 🔥 Phase 2: 重要功能補齊 (P1) - 1週

### **Task 2.1: 建立知識庫集成模組** 🔴
**ID**: `build_knowledge_base_module`  
**優先級**: P0 - 規格要求  
**預估時間**: 12-16小時  
**負責模組**: `src/knowledge_base/`  
**狀態**: ⏳ 待執行

#### **問題描述**
知識庫模組完全缺失，違背項目核心目標「RAG知識庫系統」，需要建立完整的知識庫集成架構。

#### **詳細子任務**
- [ ] **2.1.1 創建知識庫基礎架構** (3小時)
  ```python
  # 創建 src/knowledge_base/base_adapter.py
  class BaseKnowledgeAdapter(ABC):
      @abstractmethod
      async def index_document(self, markdown_content: str, associations: List[Dict]) -> str
      @abstractmethod  
      async def search(self, query: str, top_k: int = 10) -> List[Dict]
      @abstractmethod
      async def delete_document(self, document_id: str) -> bool
  ```

- [ ] **2.1.2 實現Azure AI Search適配器** (4小時)
  ```python
  # 創建 src/knowledge_base/azure_ai_search.py
  class AzureAISearchAdapter(BaseKnowledgeAdapter):
      # 實現索引創建、文檔上傳、搜索等核心功能
  ```

- [ ] **2.1.3 實現Diffy適配器骨架** (3小時)
  ```python
  # 創建 src/knowledge_base/diffy_adapter.py
  class DiffyAdapter(BaseKnowledgeAdapter):
      # 實現Diffy知識庫集成接口
  ```

- [ ] **2.1.4 實現Copilot Studio適配器骨架** (3小時)
  ```python
  # 創建 src/knowledge_base/copilot_studio.py  
  class CopilotStudioAdapter(BaseKnowledgeAdapter):
      # 實現Microsoft Copilot Studio集成接口
  ```

- [ ] **2.1.5 創建適配器工廠** (2小時)
  ```python
  # 創建 src/knowledge_base/adapter_factory.py
  class KnowledgeBaseFactory:
      def get_adapter(self, adapter_type: str) -> BaseKnowledgeAdapter
  ```

- [ ] **2.1.6 編寫單元測試** (2小時)
  ```python
  # 創建 tests/unit/test_knowledge_base/
  # 為每個適配器編寫基礎功能測試
  ```

#### **驗收標準**
- [ ] 知識庫模組目錄結構完整
- [ ] 所有適配器實現基礎接口
- [ ] 工廠模式可以正確創建適配器實例
- [ ] 單元測試覆蓋基本功能
- [ ] 與DocumentProcessor成功集成

---

### **Task 2.2: 補齊API中間件** 🟡
**ID**: `add_api_middleware`  
**優先級**: P1 - 生產必需  
**預估時間**: 6-8小時  
**負責模組**: `src/api/middleware/`  
**狀態**: ⏳ 待執行

#### **問題描述**
API中間件缺少rate_limit.py限流中間件，生產環境安全性不足。

#### **詳細子任務**
- [ ] **2.2.1 實現限流中間件** (4小時)
  ```python
  # 創建 src/api/middleware/rate_limit.py
  class RateLimitMiddleware:
      # 實現基於IP和用戶的限流
      # 支援Redis緩存的分佈式限流
  ```

- [ ] **2.2.2 集成到FastAPI應用** (2小時)
  ```python
  # 修改 src/api/app.py
  # 添加限流中間件到應用中間件棧
  ```

- [ ] **2.2.3 配置限流策略** (1小時)
  ```python
  # 在 src/config/settings.py 添加限流配置
  class RateLimitSettings(BaseSettings):
      requests_per_minute: int = 60
      burst_limit: int = 10
  ```

- [ ] **2.2.4 編寫測試和文檔** (1小時)
  ```python
  # 創建限流中間件的測試用例
  # 更新API文檔說明限流政策
  ```

#### **驗收標準**
- [ ] 限流中間件正常工作
- [ ] 超過限制時正確返回429狀態碼
- [ ] 配置可以通過環境變量調整
- [ ] 支援分佈式限流(Redis)
- [ ] 有完整的測試覆蓋

---

### **Task 2.3: 統一命名規範** 🟡
**ID**: `unify_naming_convention`  
**優先級**: P1 - 規格對齊  
**預估時間**: 4-6小時  
**負責模組**: `src/image_processing/`  
**狀態**: ⏳ 待執行

#### **問題描述**
圖片命名存在兩套標準，需要統一為規格文件要求的格式：`{文件名}_{頁碼}_{圖片序號}_{時間戳}.{格式}`

#### **詳細子任務**
- [ ] **2.3.1 修改圖片命名生成邏輯** (2小時)
  ```python
  # 修改 src/image_processing/storage.py
  # 統一為: {文件名}_{頁碼}_{圖片序號}_{時間戳}.{格式}
  # 例如: workflows_sample_p001_img001_20250809143022.png
  ```

- [ ] **2.3.2 更新圖片提取器命名** (1小時)
  ```python
  # 修改 src/image_processing/extractor.py
  # 確保生成的filename符合規格要求
  ```

- [ ] **2.3.3 批量重命名現有圖片** (2小時)
  ```python
  # 創建 scripts/rename_images.py
  # 將現有圖片重命名為標準格式
  # 更新相關的URL引用
  ```

- [ ] **2.3.4 測試和驗證** (1小時)
  ```python
  # 驗證新命名格式在各個模組中正常工作
  # 確保Markdown中的圖片引用正確更新
  ```

#### **驗收標準**
- [ ] 所有新生成圖片使用統一命名格式
- [ ] 現有圖片已重命名為標準格式
- [ ] 圖片URL和引用正確更新
- [ ] 命名格式符合規格文件要求
- [ ] 重命名腳本可重複執行

---

### **Task 2.4: 統一元數據路徑** 🟡
**ID**: `unify_metadata_paths`  
**優先級**: P1 - 規格對齊  
**預估時間**: 2-3小時  
**負責模組**: `src/image_processing/metadata.py`  
**狀態**: ⏳ 待執行

#### **問題描述**
元數據路徑分散在不同位置，需要統一到`data/output/metadata/`以符合規格文件要求。

#### **詳細子任務**
- [ ] **2.4.1 修改默認元數據路徑** (0.5小時)
  ```python
  # 修改 src/image_processing/metadata.py L87
  # FROM: metadata_storage_path: str = "data/metadata"
  # TO: metadata_storage_path: str = "data/output/metadata"
  ```

- [ ] **2.4.2 遷移現有元數據文件** (1小時)
  ```python
  # 創建 scripts/migrate_metadata.py
  # 將 data/metadata/ 下文件遷移到 data/output/metadata/
  # 確保遷移過程安全可靠
  ```

- [ ] **2.4.3 更新配置文件** (0.5小時)
  ```python
  # 更新 src/config/settings.py 中相關路徑配置
  # 確保所有模組使用統一的元數據路徑
  ```

- [ ] **2.4.4 測試路徑變更** (1小時)
  ```python
  # 運行完整測試確保路徑變更不影響功能
  # 驗證元數據讀寫正常
  ```

#### **驗收標準**
- [ ] 所有元數據文件位於`data/output/metadata/`
- [ ] 現有元數據文件已正確遷移
- [ ] 新生成的元數據使用統一路徑
- [ ] 配置文件已更新
- [ ] 所有相關測試通過

---

## ⚡ Phase 3: 優化和清理 (P2) - 2週

### **Task 3.1: 清理依賴文件** 🟢
**ID**: `clean_dependencies`  
**優先級**: P2 - 維護性  
**預估時間**: 2-3小時  
**負責模組**: `requirements.txt`  
**狀態**: ⏳ 待執行

#### **問題描述**
requirements.txt存在重複依賴、版本衝突和不必要的標準庫依賴，影響環境一致性和安裝效率。

#### **詳細子任務**
- [ ] **3.1.1 移除重複依賴** (1小時)
  ```bash
  # 刪除重複的依賴項
  # azure-storage-blob (保留最新版本 >=12.17.0)
  # boto3 (統一版本號，選擇 >=1.28.0)
  # google-cloud-storage (檢查並去除重複)
  ```

- [ ] **3.1.2 移除標準庫依賴** (0.5小時)
  ```bash
  # 刪除不必要的標準庫
  # asyncio>=3.4.3
  # concurrent-futures>=3.1.1  
  # mimetypes>=1.6.0
  ```

- [ ] **3.1.3 版本號統一** (0.5小時)
  ```bash
  # 統一衝突的版本號
  # boto3 統一為最新穩定版本
  # 檢查其他依賴的版本相容性
  ```

- [ ] **3.1.4 依賴分類整理** (1小時)
  ```bash
  # 按功能模組重新組織requirements.txt
  # 核心框架、文檔解析、圖片處理、雲端服務等
  # 添加清晰的註釋分組
  ```

#### **驗收標準**
- [ ] 無重複依賴項
- [ ] 無標準庫依賴
- [ ] 版本號一致且相容
- [ ] 依賴安裝和運行正常
- [ ] 依賴分類清晰有序

---

### **Task 3.2: 優化關聯重複問題** 🟢
**ID**: `optimize_association_deduplication`  
**優先級**: P2 - 性能優化  
**預估時間**: 8-10小時  
**負責模組**: `src/association/`  
**狀態**: ⏳ 待執行

#### **問題描述**
當前7張圖片產生345個關聯(約49倍重複)，需要實現關聯去重和品質控制，確保每圖片1-3個高品質關聯。

#### **詳細子任務**
- [ ] **3.2.1 分析關聯重複原因** (2小時)
  ```python
  # 調查為什麼7張圖片產生345個關聯
  # 檢查關聯邏輯是否過於寬鬆
  # 分析關聯分數分佈情況
  ```

- [ ] **3.2.2 實現關聯去重機制** (4小時)
  ```python
  # 修改 src/association/association_scorer.py
  # 添加關聯去重和排序邏輯
  class AssociationDeduplicator:
      def deduplicate_associations(self, associations: List[AssociationResult]) -> List[AssociationResult]
      def rank_by_quality(self, associations: List[AssociationResult]) -> List[AssociationResult]
  ```

- [ ] **3.2.3 調整關聯閾值** (2小時)
  ```python
  # 優化關聯度閾值設置
  # 確保每張圖片只保留最佳的1-3個關聯
  # 實現動態閾值調整機制
  ```

- [ ] **3.2.4 實現關聯品質評估** (2小時)
  ```python
  # 添加關聯品質檢查
  # 過濾低品質關聯，提高整體準確性
  # 實現關聯置信度評估
  ```

#### **驗收標準**
- [ ] 關聯數量合理(每圖片1-3個高品質關聯)
- [ ] 關聯準確性維持在85%以上
- [ ] 處理時間無顯著增加
- [ ] 去重機制可配置和調優
- [ ] 有詳細的關聯品質報告

---

### **Task 3.3: 增強錯誤處理和日誌** 🟢
**ID**: `enhance_error_handling`  
**優先級**: P2 - 穩定性  
**預估時間**: 6-8小時  
**負責模組**: 全域  
**狀態**: ⏳ 待執行

#### **問題描述**
需要建立統一的錯誤處理機制和結構化日誌系統，提高系統穩定性和可維護性。

#### **詳細子任務**
- [ ] **3.3.1 統一錯誤處理模式** (3小時)
  ```python
  # 創建 src/utils/error_handler.py
  # 定義統一的錯誤類型和處理策略
  class DocumentProcessingError(Exception)
  class ImageProcessingError(Exception)
  class AssociationAnalysisError(Exception)
  ```

- [ ] **3.3.2 增強日誌記錄** (2小時)
  ```python
  # 優化 src/config/logging_config.py
  # 添加結構化日誌和性能監控
  # 實現日誌分級和輪轉機制
  ```

- [ ] **3.3.3 添加健康檢查端點** (2小時)
  ```python
  # 添加 src/api/routes/health.py
  # 實現系統健康狀態檢查API
  # 監控各個模組的運行狀態
  ```

- [ ] **3.3.4 集成監控和告警** (1小時)
  ```python
  # 添加性能監控和異常告警
  # 實現系統指標收集
  ```

#### **驗收標準**
- [ ] 統一的錯誤處理機制
- [ ] 詳細的操作日誌記錄
- [ ] 健康檢查端點正常工作
- [ ] 錯誤可以被正確捕獲和處理
- [ ] 日誌格式結構化且可搜索

---

### **Task 3.4: 性能基準測試和文檔** 🟢
**ID**: `performance_benchmarks_docs`  
**優先級**: P2 - 品質保證  
**預估時間**: 8-12小時  
**負責模組**: `tests/performance/`, `docs/`  
**狀態**: ⏳ 待執行

#### **問題描述**
需要建立完整的性能基準測試體系和更新技術文檔，確保系統性能可測量和文檔準確性。

#### **詳細子任務**
- [ ] **3.4.1 建立性能基準測試** (4小時)
  ```python
  # 創建 tests/performance/test_benchmarks.py
  # 測試不同文件大小和格式的處理性能
  # 建立性能回歸檢測機制
  ```

- [ ] **3.4.2 更新技術文檔** (4小時)
  ```markdown
  # 更新 docs/technical_specs/ 下的技術文檔
  # 包含最新的API規範和性能指標
  # 更新架構圖和流程圖
  ```

- [ ] **3.4.3 生成API文檔** (2小時)
  ```python
  # 更新 docs/api/openapi.yaml
  # 自動生成最新的API文檔
  # 確保文檔與實際API一致
  ```

- [ ] **3.4.4 創建用戶指南** (2小時)
  ```markdown
  # 更新 docs/user_guide/ 下的用戶文檔
  # 包含安裝、配置和使用指南
  # 添加常見問題和故障排除
  ```

#### **驗收標準**
- [ ] 性能基準測試可重現運行
- [ ] 技術文檔與實際實現一致
- [ ] API文檔完整且準確
- [ ] 用戶指南清晰易懂
- [ ] 文檔自動化生成和更新

---

## 📊 執行計劃和監控

### **時間線總覽**
```
Week 1: Phase 1 (P0緊急修復) + Phase 2 Task 2.1-2.2
├── Day 1-2: Task 1.1 (DocumentProcessor API修復)
├── Day 2-3: Task 1.2 (生產入口測試)
├── Day 3: Task 1.3 (解析器警告修復)
├── Day 4-6: Task 2.1 (知識庫模組)
└── Day 7: Task 2.2 (API中間件)

Week 2: Phase 2 Task 2.3-2.4 + Phase 3 Task 3.1-3.2  
├── Day 8-9: Task 2.3 (命名規範統一)
├── Day 10: Task 2.4 (元數據路徑統一)
├── Day 11: Task 3.1 (依賴清理)
└── Day 12-14: Task 3.2 (關聯優化)

Week 3: Phase 3 Task 3.3-3.4 + 整體驗收測試
├── Day 15-17: Task 3.3 (錯誤處理增強)
├── Day 18-20: Task 3.4 (性能測試和文檔)
└── Day 21: 整體驗收和交付
```

### **里程碑檢查點**
- [ ] **Milestone 1** (Day 2): DocumentProcessor API修復完成，生產入口測試通過
- [ ] **Milestone 2** (Day 7): 知識庫模組骨架完成，API中間件補齊  
- [ ] **Milestone 3** (Day 14): 命名統一，依賴清理完成，關聯優化完成
- [ ] **Milestone 4** (Day 21): 全系統優化完成，文檔更新，最終驗收

### **每日檢查清單**
- [ ] 當日任務進度追蹤
- [ ] 程式碼變更的測試覆蓋
- [ ] 新功能的文檔更新
- [ ] 性能回歸檢查
- [ ] 錯誤和警告處理

### **風險緩解策略**
- [ ] **每日進度檢查**: 確保P0任務按時完成
- [ ] **API測試覆蓋**: 每個修復都要有對應測試
- [ ] **回滾計劃**: 重要修改前創建代碼備份點
- [ ] **漸進式交付**: 每個Task完成後立即測試和驗收
- [ ] **並行開發**: 獨立Task可並行進行以加速進度

### **品質控制**
- [ ] **程式碼審查**: 所有變更必須經過審查
- [ ] **自動化測試**: 每次提交觸發完整測試套件
- [ ] **性能監控**: 每個Task完成後運行性能基準測試
- [ ] **文檔同步**: 程式碼變更必須同步更新文檔

---

## 🎯 最終驗收標準

### **功能性驗收**
- [ ] 端到端測試100%通過
- [ ] 生產入口API穩定可用
- [ ] 知識庫模組基礎功能可用
- [ ] 所有API中間件正常工作

### **規格對齊度驗收**
- [ ] 規格文件對齊度達到95%以上
- [ ] 所有必需模組都已實現
- [ ] 命名規範完全統一
- [ ] 路徑配置標準化

### **品質和維護性驗收**
- [ ] 無重複依賴和命名衝突  
- [ ] 錯誤處理機制完善
- [ ] 日誌記錄詳細可查
- [ ] 性能指標達到預期

### **文檔和測試驗收**
- [ ] 技術文檔完整且準確
- [ ] API文檔與實現一致
- [ ] 測試覆蓋率達到90%以上
- [ ] 用戶指南清晰易懂

---

## 📝 執行記錄

### **進度追蹤**
| Task ID | 任務名稱 | 狀態 | 開始日期 | 完成日期 | 實際工時 | 備註 |
|---------|----------|------|----------|----------|----------|------|
| fix_document_processor_api | DocumentProcessor API修復 | ⏳ 待執行 | - | - | - | P0緊急 |
| create_production_entry_test | 生產入口測試 | ⏳ 待執行 | - | - | - | P0緊急 |
| fix_parser_registration_warning | 解析器警告修復 | ⏳ 待執行 | - | - | - | P1高 |
| build_knowledge_base_module | 知識庫模組建立 | ⏳ 待執行 | - | - | - | P0規格要求 |
| add_api_middleware | API中間件補齊 | ⏳ 待執行 | - | - | - | P1生產必需 |
| unify_naming_convention | 命名規範統一 | ⏳ 待執行 | - | - | - | P1規格對齊 |
| unify_metadata_paths | 元數據路徑統一 | ⏳ 待執行 | - | - | - | P1規格對齊 |
| clean_dependencies | 依賴清理 | ⏳ 待執行 | - | - | - | P2維護性 |
| optimize_association_deduplication | 關聯優化 | ⏳ 待執行 | - | - | - | P2性能優化 |
| enhance_error_handling | 錯誤處理增強 | ⏳ 待執行 | - | - | - | P2穩定性 |
| performance_benchmarks_docs | 性能測試和文檔 | ⏳ 待執行 | - | - | - | P2品質保證 |

### **問題和風險記錄**
| 日期 | 問題描述 | 影響程度 | 解決方案 | 狀態 |
|------|----------|----------|----------|------|
| - | - | - | - | - |

### **變更記錄**
| 版本 | 日期 | 變更內容 | 負責人 |
|------|------|----------|--------|
| v1.0 | 2025-08-09 | 初始版本創建 | 系統分析師 |

---

**此任務清單將確保智能文檔轉換與RAG知識庫系統從當前的75%規格對齊度提升到95%以上，並解決所有架構風險和隱藏問題，實現完整的生產級系統。**
