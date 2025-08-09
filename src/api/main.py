"""
API應用啟動入口

提供獨立的API服務啟動接口。
"""

from .app import create_app, run_server
from ..config.settings import get_settings

# 創建應用實例
app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    run_server(
        host=settings.app.api_host,
        port=settings.app.api_port,
        reload=settings.app.debug
    )
