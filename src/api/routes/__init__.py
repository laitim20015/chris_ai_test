"""
API路由模組

包含所有API端點的路由定義和處理邏輯。
"""

from . import upload, process, chat, embeddings, status, download

__all__ = ["upload", "process", "chat", "embeddings", "status", "download"]
