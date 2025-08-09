"""
錯誤處理中間件

統一處理API請求中的異常，提供標準化的錯誤響應格式。
"""

import traceback
from typing import Union
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from pydantic import ValidationError
from loguru import logger

from ..models.response_models import ErrorResponse


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    統一錯誤處理中間件
    
    捕獲並處理應用中的各種異常，返回標準化的錯誤響應。
    """
    
    def __init__(self, app: ASGIApp):
        """
        初始化錯誤處理中間件
        
        Args:
            app: ASGI應用
        """
        super().__init__(app)
        self.logger = logger.bind(module="error_handler")
        self.logger.info("🛡️ 錯誤處理中間件已啟用")
    
    async def dispatch(self, request: Request, call_next):
        """
        處理請求並捕獲異常
        
        Args:
            request: 請求對象
            call_next: 下一個中間件或路由處理器
            
        Returns:
            響應對象
        """
        try:
            # 記錄請求開始
            method = request.method
            path = request.url.path
            self.logger.debug(f"🔄 處理請求: {method} {path}")
            
            response = await call_next(request)
            
            # 記錄響應狀態
            status_code = response.status_code
            if status_code >= 400:
                self.logger.warning(f"⚠️ 請求 {method} {path} 返回狀態碼: {status_code}")
            else:
                self.logger.debug(f"✅ 請求 {method} {path} 處理成功: {status_code}")
            
            return response
            
        except HTTPException as exc:
            # FastAPI HTTP異常
            self.logger.warning(f"🚫 HTTP異常: {exc.status_code} - {exc.detail}")
            return self._create_error_response(
                error_type="HTTP_ERROR",
                message=exc.detail,
                status_code=exc.status_code,
                request=request
            )
        
        except ValidationError as exc:
            # Pydantic驗證錯誤
            self.logger.warning(f"📝 數據驗證錯誤: {str(exc)}")
            return self._create_error_response(
                error_type="VALIDATION_ERROR",
                message="請求數據驗證失敗",
                status_code=422,
                details=self._format_validation_errors(exc),
                request=request
            )
        
        except FileNotFoundError as exc:
            # 文件未找到錯誤
            self.logger.error(f"📁 文件未找到: {str(exc)}")
            return self._create_error_response(
                error_type="FILE_NOT_FOUND",
                message="請求的文件不存在",
                status_code=404,
                request=request
            )
        
        except PermissionError as exc:
            # 權限錯誤
            self.logger.error(f"🔒 權限錯誤: {str(exc)}")
            return self._create_error_response(
                error_type="PERMISSION_ERROR",
                message="權限不足",
                status_code=403,
                request=request
            )
        
        except TimeoutError as exc:
            # 超時錯誤
            self.logger.error(f"⏰ 請求超時: {str(exc)}")
            return self._create_error_response(
                error_type="TIMEOUT_ERROR",
                message="請求處理超時",
                status_code=408,
                request=request
            )
        
        except Exception as exc:
            # 其他未處理的異常
            error_id = self._generate_error_id()
            self.logger.error(
                f"💥 未處理的異常 [ID: {error_id}]: {str(exc)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            return self._create_error_response(
                error_type="INTERNAL_SERVER_ERROR",
                message="內部服務器錯誤",
                status_code=500,
                details={"error_id": error_id, "type": type(exc).__name__},
                request=request
            )
    
    def _create_error_response(
        self,
        error_type: str,
        message: str,
        status_code: int,
        request: Request,
        details: dict = None
    ) -> JSONResponse:
        """
        創建標準化錯誤響應
        
        Args:
            error_type: 錯誤類型
            message: 錯誤消息
            status_code: HTTP狀態碼
            request: 請求對象
            details: 錯誤詳情
            
        Returns:
            JSON錯誤響應
        """
        error_response = ErrorResponse(
            error=error_type,
            message=message,
            status_code=status_code,
            details=details
        )
        
        # 添加請求追蹤信息
        if hasattr(request.state, "trace_id"):
            if error_response.details is None:
                error_response.details = {}
            error_response.details["trace_id"] = request.state.trace_id
        
        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump()
        )
    
    def _format_validation_errors(self, exc: ValidationError) -> dict:
        """
        格式化Pydantic驗證錯誤
        
        Args:
            exc: 驗證異常
            
        Returns:
            格式化的錯誤詳情
        """
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })
        
        return {"validation_errors": errors}
    
    def _generate_error_id(self) -> str:
        """
        生成錯誤追蹤ID
        
        Returns:
            唯一錯誤ID
        """
        import uuid
        return f"ERR_{uuid.uuid4().hex[:8].upper()}"
