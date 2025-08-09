"""
語義分析器
Semantic Analyzer

基於sentence-transformers的語義相似度分析器，用於計算文本和圖片描述之間的語義相似度。
權重：15%（項目規則）

主要功能：
1. 文本向量化 - 使用sentence-transformers模型
2. 語義相似度計算 - 餘弦相似度
3. 批量處理 - 支持批量文本處理
4. 緩存機制 - 緩存向量以提高性能
"""

from typing import List, Dict, Tuple, Optional, NamedTuple
import numpy as np
from dataclasses import dataclass
from src.config.logging_config import get_logger, log_performance

logger = get_logger("semantic_analyzer")

@dataclass
class SemanticSimilarity:
    """語義相似度結果"""
    similarity_score: float                # 相似度分數 (0-1)
    confidence: float                      # 置信度
    method: str                           # 計算方法
    embedding_dim: int                    # 向量維度

class SemanticAnalyzer:
    """語義分析器"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化語義分析器
        
        Args:
            model_name: sentence-transformers模型名稱
        """
        self.model_name = model_name
        self.model = None
        self.embedding_cache = {}
        
        # 嘗試加載模型
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            logger.info(f"語義分析模型載入成功: {model_name}")
        except ImportError:
            logger.warning("sentence-transformers未安裝，使用基礎相似度計算")
        except Exception as e:
            logger.error(f"模型載入失敗: {e}")
    
    def calculate_text_similarity(self, text1: str, text2: str) -> SemanticSimilarity:
        """
        計算兩個文本的語義相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            SemanticSimilarity: 語義相似度結果
        """
        if self.model is not None:
            return self._calculate_transformer_similarity(text1, text2)
        else:
            return self._calculate_basic_similarity(text1, text2)
    
    def _calculate_transformer_similarity(self, text1: str, text2: str) -> SemanticSimilarity:
        """使用transformer模型計算相似度"""
        try:
            # 獲取文本嵌入
            embedding1 = self._get_text_embedding(text1)
            embedding2 = self._get_text_embedding(text2)
            
            # 計算餘弦相似度
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            
            return SemanticSimilarity(
                similarity_score=float(similarity),
                confidence=0.9,
                method="sentence-transformers",
                embedding_dim=len(embedding1)
            )
            
        except Exception as e:
            logger.error(f"Transformer相似度計算失敗: {e}")
            return self._calculate_basic_similarity(text1, text2)
    
    def _calculate_basic_similarity(self, text1: str, text2: str) -> SemanticSimilarity:
        """基礎相似度計算（備用方法）"""
        from src.utils.text_utils import calculate_text_similarity
        
        similarity = calculate_text_similarity(text1, text2)
        
        return SemanticSimilarity(
            similarity_score=similarity,
            confidence=0.6,  # 基礎方法置信度較低
            method="basic_sequence_matching",
            embedding_dim=0
        )
    
    def _get_text_embedding(self, text: str) -> np.ndarray:
        """獲取文本嵌入向量（帶緩存）"""
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        if self.model is None:
            return np.random.rand(384)  # 默認維度
        
        embedding = self.model.encode(text)
        self.embedding_cache[text] = embedding
        
        return embedding

def extract_text_embeddings(texts: List[str], analyzer: Optional[SemanticAnalyzer] = None) -> List[np.ndarray]:
    """批量提取文本嵌入"""
    if analyzer is None:
        analyzer = SemanticAnalyzer()
    
    embeddings = []
    for text in texts:
        embedding = analyzer._get_text_embedding(text)
        embeddings.append(embedding)
    
    return embeddings

def compare_semantic_content(text: str, reference_texts: List[str]) -> List[float]:
    """比較文本與參考文本列表的語義相似度"""
    analyzer = SemanticAnalyzer()
    similarities = []
    
    for ref_text in reference_texts:
        result = analyzer.calculate_text_similarity(text, ref_text)
        similarities.append(result.similarity_score)
    
    return similarities

def calculate_semantic_score(similarity: SemanticSimilarity, weight_semantic: float = 0.15) -> float:
    """
    計算語義分析的最終評分
    
    Args:
        similarity: 語義相似度結果
        weight_semantic: 語義權重（項目規則規定為0.15）
        
    Returns:
        float: 語義評分
    """
    base_score = similarity.similarity_score * similarity.confidence
    return base_score * weight_semantic

