"""
向量嵌入API端點

提供基於Azure OpenAI的文本向量化功能。
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime

from ...services.azure_openai_service import get_azure_openai_service, AzureOpenAIService
from ..models.request_models import EmbeddingRequest
from ..models.response_models import EmbeddingResponse, EmbeddingVector
from ..middleware.auth import is_authenticated
from loguru import logger


router = APIRouter()
embedding_logger = logger.bind(module="api.embeddings")


def get_authenticated_azure_openai_service(request: Request) -> AzureOpenAIService:
    """依賴注入：獲取已認證的Azure OpenAI服務"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="未認證的請求")
    return get_azure_openai_service()


@router.post("/embeddings", response_model=EmbeddingResponse, tags=["向量嵌入"])
async def create_embeddings(
    embedding_request: EmbeddingRequest,
    azure_service: AzureOpenAIService = Depends(get_authenticated_azure_openai_service)
):
    """
    創建文本向量嵌入
    
    將文本轉換為高維向量，用於語義搜索、相似度計算等AI應用。
    
    - **texts**: 要嵌入的文本列表（最多1000個）
    - **model**: 嵌入模型（text-embedding-ada-002等）
    - **batch_size**: 批量處理大小，優化性能
    
    返回每個文本對應的向量表示，可用於：
    - 語義搜索和匹配
    - 文檔相似度計算
    - 聚類和分類
    - RAG系統的知識檢索
    """
    try:
        embedding_logger.info(
            f"🧬 收到嵌入請求 - 模型: {embedding_request.model}, "
            f"文本數: {len(embedding_request.texts)}, "
            f"批量大小: {embedding_request.batch_size}"
        )
        
        # 驗證輸入
        if not embedding_request.texts:
            raise HTTPException(status_code=400, detail="文本列表不能為空")
        
        if len(embedding_request.texts) > 1000:
            raise HTTPException(status_code=400, detail="單次請求最多支持1000個文本")
        
        # 調用Azure OpenAI嵌入服務
        response = await azure_service.create_embeddings(
            texts=embedding_request.texts,
            model=embedding_request.model,
            batch_size=embedding_request.batch_size
        )
        
        # 構建響應
        embedding_vectors = [
            EmbeddingVector(
                text=emb["text"],
                embedding=emb["embedding"],
                index=emb["index"]
            )
            for emb in response["embeddings"]
        ]
        
        embedding_response = EmbeddingResponse(
            model=response["model"],
            embeddings=embedding_vectors,
            total_tokens=response["total_tokens"],
            created_at=response["created_at"],
            processing_time=response["processing_time"]
        )
        
        embedding_logger.info(
            f"✅ 嵌入請求完成 - "
            f"Token使用: {response['total_tokens']}, "
            f"處理時間: {response['processing_time']:.2f}s"
        )
        
        return embedding_response
        
    except HTTPException:
        raise
    except Exception as e:
        embedding_logger.error(f"❌ 嵌入請求失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"嵌入請求處理失敗: {str(e)}"
        )


@router.post("/embeddings/similarity", tags=["向量嵌入"])
async def calculate_similarity(
    text1: str,
    text2: str,
    model: str = "text-embedding-ada-002",
    azure_service: AzureOpenAIService = Depends(get_authenticated_azure_openai_service)
):
    """
    計算兩個文本的語義相似度
    
    使用向量嵌入計算文本間的餘弦相似度，返回0-1之間的相似度分數。
    
    - **text1**: 第一個文本
    - **text2**: 第二個文本  
    - **model**: 嵌入模型
    
    返回：
    - **similarity**: 相似度分數（0-1，1表示完全相似）
    - **embeddings**: 兩個文本的向量（可選）
    """
    try:
        embedding_logger.info(f"📊 計算文本相似度 - 模型: {model}")
        
        # 獲取兩個文本的嵌入向量
        response = await azure_service.create_embeddings(
            texts=[text1, text2],
            model=model
        )
        
        if len(response["embeddings"]) != 2:
            raise ValueError("期望得到2個嵌入向量")
        
        # 計算餘弦相似度
        import numpy as np
        
        vec1 = np.array(response["embeddings"][0]["embedding"])
        vec2 = np.array(response["embeddings"][1]["embedding"])
        
        # 餘弦相似度公式
        cos_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
        # 確保相似度在[0, 1]範圍內
        similarity = float(max(0, (cos_sim + 1) / 2))
        
        result = {
            "text1": text1,
            "text2": text2,
            "similarity": similarity,
            "model": model,
            "processing_time": response["processing_time"],
            "created_at": datetime.utcnow()
        }
        
        embedding_logger.info(f"✅ 相似度計算完成 - 分數: {similarity:.4f}")
        
        return result
        
    except Exception as e:
        embedding_logger.error(f"❌ 相似度計算失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"相似度計算失敗: {str(e)}"
        )


@router.post("/embeddings/batch-similarity", tags=["向量嵌入"])
async def batch_similarity_search(
    query_text: str,
    candidate_texts: List[str],
    model: str = "text-embedding-ada-002",
    top_k: int = 5,
    azure_service: AzureOpenAIService = Depends(get_authenticated_azure_openai_service)
):
    """
    批量相似度搜索
    
    在候選文本列表中找到與查詢文本最相似的文本。
    
    - **query_text**: 查詢文本
    - **candidate_texts**: 候選文本列表
    - **model**: 嵌入模型
    - **top_k**: 返回最相似的前K個結果
    
    返回按相似度排序的結果列表。
    """
    try:
        embedding_logger.info(
            f"🔍 批量相似度搜索 - 查詢文本長度: {len(query_text)}, "
            f"候選文本數: {len(candidate_texts)}, Top-{top_k}"
        )
        
        if not candidate_texts:
            raise HTTPException(status_code=400, detail="候選文本列表不能為空")
        
        if len(candidate_texts) > 500:
            raise HTTPException(status_code=400, detail="候選文本列表最多支持500個")
        
        # 獲取所有文本的嵌入向量
        all_texts = [query_text] + candidate_texts
        response = await azure_service.create_embeddings(
            texts=all_texts,
            model=model
        )
        
        # 分離查詢向量和候選向量
        import numpy as np
        
        query_embedding = np.array(response["embeddings"][0]["embedding"])
        candidate_embeddings = [
            np.array(emb["embedding"]) 
            for emb in response["embeddings"][1:]
        ]
        
        # 計算所有相似度
        similarities = []
        for i, candidate_emb in enumerate(candidate_embeddings):
            cos_sim = np.dot(query_embedding, candidate_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(candidate_emb)
            )
            similarity = float(max(0, (cos_sim + 1) / 2))
            
            similarities.append({
                "index": i,
                "text": candidate_texts[i],
                "similarity": similarity
            })
        
        # 按相似度排序並取前K個
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = similarities[:top_k]
        
        result = {
            "query_text": query_text,
            "total_candidates": len(candidate_texts),
            "top_k": top_k,
            "results": top_results,
            "model": model,
            "processing_time": response["processing_time"],
            "created_at": datetime.utcnow()
        }
        
        embedding_logger.info(
            f"✅ 批量相似度搜索完成 - "
            f"最高相似度: {top_results[0]['similarity']:.4f} (如果有結果)"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        embedding_logger.error(f"❌ 批量相似度搜索失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"批量相似度搜索失敗: {str(e)}"
        )
