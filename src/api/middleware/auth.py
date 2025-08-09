"""
API認證中間件

提供基於API Key的簡單認證機制，支援後續擴展JWT等高級認證。
"""

from typing import List, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger

from ..models.response_models import ErrorResponse


class AuthMiddleware(BaseHTTPMiddleware):
    """
    API認證中間件
    
    提供基於API Key的認證功能，支援白名單路徑跳過認證。
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        api_keys: List[str],
        header_name: str = "X-API-Key",
        whitelist_paths: Optional[List[str]] = None
    ):
        """
        初始化認證中間件
        
        Args:
            app: ASGI應用
            api_keys: 有效的API密鑰列表
            header_name: API密鑰頭部名稱
            whitelist_paths: 白名單路徑（無需認證）
        """
        super().__init__(app)
        self.api_keys = set(api_keys)
        self.header_name = header_name
        self.whitelist_paths = whitelist_paths or [
            "/health",
            "/",
            "/api/docs",
            "/api/redoc", 
            "/api/openapi.json"
        ]
        self.logger = logger.bind(module="auth_middleware")
        
        self.logger.info(f"🔐 認證中間件已啟用，支援{len(api_keys)}個API密鑰")
    
    async def dispatch(self, request: Request, call_next):
        """
        處理請求認證
        
        Args:
            request: 請求對象
            call_next: 下一個中間件或路由處理器
            
        Returns:
            響應對象
        """
        path = request.url.path
        method = request.method
        
        # 檢查是否在白名單中
        if self._is_whitelisted(path):
            self.logger.debug(f"路徑 {path} 在白名單中，跳過認證")
            return await call_next(request)
        
        # OPTIONS請求跳過認證（CORS預檢請求）
        if method == "OPTIONS":
            return await call_next(request)
        
        # 檢查API密鑰
        api_key = request.headers.get(self.header_name)
        
        if not api_key:
            self.logger.warning(f"請求 {method} {path} 缺少API密鑰")
            return self._create_auth_error("缺少API密鑰")
        
        if api_key not in self.api_keys:
            self.logger.warning(f"請求 {method} {path} 使用無效API密鑰: {api_key[:8]}...")
            return self._create_auth_error("無效的API密鑰")
        
        # 認證成功，記錄日誌
        self.logger.debug(f"請求 {method} {path} 認證成功")
        
        # 將API密鑰信息添加到請求狀態中
        request.state.api_key = api_key
        request.state.authenticated = True
        
        return await call_next(request)
    
    def _is_whitelisted(self, path: str) -> bool:
        """
        檢查路徑是否在白名單中
        
        Args:
            path: 請求路徑
            
        Returns:
            是否在白名單中
        """
        for whitelist_path in self.whitelist_paths:
            if path.startswith(whitelist_path):
                return True
        return False
    
    def _create_auth_error(self, message: str) -> JSONResponse:
        """
        創建認證錯誤響應
        
        Args:
            message: 錯誤消息
            
        Returns:
            JSON錯誤響應
        """
        error_response = ErrorResponse(
            error="AUTHENTICATION_ERROR",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error_response.model_dump(),
            headers={"WWW-Authenticate": f"{self.header_name}"}
        )


# 輔助函數：從請求中獲取認證信息
def get_api_key(request: Request) -> Optional[str]:
    """
    從請求中獲取API密鑰
    
    Args:
        request: 請求對象
        
    Returns:
        API密鑰，如果未認證則返回None
    """
    return getattr(request.state, "api_key", None)


def is_authenticated(request: Request) -> bool:
    """
    檢查請求是否已認證
    
    Args:
        request: 請求對象
        
    Returns:
        是否已認證
    """
    return getattr(request.state, "authenticated", False)
