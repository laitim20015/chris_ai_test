"""
pytest配置文件

定義全局fixtures、測試配置和共用測試工具。
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock
import httpx

from src.config.settings import get_settings, Settings, AppSettings, AzureOpenAISettings
from src.services.azure_openai_service import AzureOpenAIService
from src.services.document_service import DocumentService
from src.api.app import create_app


# ============ 基礎配置 Fixtures ============

@pytest.fixture(scope="session")
def event_loop():
    """創建事件循環"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """創建臨時目錄"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_settings(temp_dir: Path) -> Settings:
    """測試用設置"""
    return Settings(
        app=AppSettings(
            debug=True,
            environment="testing",
            auth_enabled=False,  # 測試時禁用認證
            api_keys=["test-api-key"],
            max_file_size=10 * 1024 * 1024  # 10MB
        ),
        azure_openai=AzureOpenAISettings(
            endpoint=None,  # 測試時不配置Azure OpenAI
            api_key=None
        )
    )


# ============ 服務 Mock Fixtures ============

@pytest.fixture
def mock_azure_openai_service():
    """Mock Azure OpenAI服務"""
    service = Mock(spec=AzureOpenAIService)
    
    # Mock chat completion
    async def mock_chat_completion(*args, **kwargs):
        return {
            "type": "completion",
            "id": "test_completion_id",
            "model": "gpt-4",
            "message": "這是測試回復",
            "usage": Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            "processing_time": 1.5,
            "created_at": "2025-08-08T10:00:00Z"
        }
    
    service.chat_completion = AsyncMock(side_effect=mock_chat_completion)
    
    # Mock embeddings
    async def mock_create_embeddings(*args, **kwargs):
        texts = kwargs.get('texts', args[0] if args else [])
        return {
            "model": "text-embedding-ada-002",
            "embeddings": [
                {
                    "text": text,
                    "embedding": [0.1] * 1536,  # 模擬1536維向量
                    "index": i
                }
                for i, text in enumerate(texts)
            ],
            "total_tokens": len(' '.join(texts)),
            "processing_time": 0.5,
            "created_at": "2025-08-08T10:00:00Z"
        }
    
    service.create_embeddings = AsyncMock(side_effect=mock_create_embeddings)
    
    # Mock health check
    async def mock_health_check(*args, **kwargs):
        return {
            "status": "healthy",
            "endpoint": "test_endpoint",
            "chat_model": "gpt-4",
            "embedding_model": "text-embedding-ada-002",
            "test_response_time": 0.5
        }
    
    service.health_check = AsyncMock(side_effect=mock_health_check)
    
    return service


@pytest.fixture
def mock_document_service(temp_dir: Path):
    """Mock文檔服務"""
    service = Mock(spec=DocumentService)
    service.tasks = {}
    
    async def mock_create_processing_task(document_id, filename, file_path, **kwargs):
        task_id = f"test_task_{document_id}"
        # 模擬任務狀態
        service.tasks[task_id] = {
            "task_id": task_id,
            "document_id": document_id,
            "filename": filename,
            "status": "pending",
            "progress": 0.0,
            "current_step": "等待處理",
            "created_at": "2025-08-08T10:00:00Z",
            "started_at": None,
            "completed_at": None
        }
        return task_id
    
    service.create_processing_task = AsyncMock(side_effect=mock_create_processing_task)
    
    def mock_get_task_status(task_id):
        return service.tasks.get(task_id)
    
    service.get_task_status = Mock(side_effect=mock_get_task_status)
    
    def mock_get_all_tasks():
        return list(service.tasks.values())
    
    service.get_all_tasks = Mock(side_effect=mock_get_all_tasks)
    
    return service


# ============ API測試 Fixtures ============

@pytest.fixture
async def test_app(test_settings: Settings, monkeypatch):
    """測試用FastAPI應用"""
    # 注入測試設置
    monkeypatch.setattr("src.config.settings.get_settings", lambda: test_settings)
    
    app = create_app(test_settings.app)
    return app


@pytest.fixture
async def async_client(test_app):
    """異步HTTP客戶端"""
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers():
    """認證頭部"""
    return {"X-API-Key": "test-api-key"}


# ============ 測試數據 Fixtures ============

@pytest.fixture
def sample_text_blocks():
    """示例文本塊"""
    from src.parsers.base import TextBlock, BoundingBox
    
    return [
        TextBlock(
            id="text_001",
            content="這是第一段文字內容，描述了圖表的基本信息。",
            page=1,
            bbox=BoundingBox(x1=100, y1=200, x2=400, y2=250),
            associated_images=[]
        ),
        TextBlock(
            id="text_002", 
            content="圖1顯示了銷售趨勢的變化，可以看出明顯的增長。",
            page=1,
            bbox=BoundingBox(x1=100, y1=300, x2=400, y2=350),
            associated_images=[]
        ),
        TextBlock(
            id="text_003",
            content="根據表格2的數據分析，我們可以得出以下結論。",
            page=1,
            bbox=BoundingBox(x1=100, y1=400, x2=400, y2=450),
            associated_images=[]
        )
    ]


@pytest.fixture
def sample_images():
    """示例圖片內容"""
    from src.parsers.base import ImageContent, BoundingBox
    
    return [
        ImageContent(
            id="img_001",
            filename="chart1.png",
            data=b"fake_image_data_1",
            page=1,
            bbox=BoundingBox(x1=450, y1=200, x2=650, y2=350),
            format="PNG",
            size=(200, 150)
        ),
        ImageContent(
            id="img_002",
            filename="table1.png", 
            data=b"fake_image_data_2",
            page=1,
            bbox=BoundingBox(x1=450, y1=400, x2=650, y2=550),
            format="PNG",
            size=(200, 150)
        )
    ]


@pytest.fixture
def sample_parsed_content(sample_text_blocks, sample_images):
    """示例解析內容"""
    from src.parsers.base import ParsedContent, DocumentMetadata
    
    return ParsedContent(
        text_blocks=sample_text_blocks,
        images=sample_images,
        tables=[],
        metadata=DocumentMetadata(
            filename="test_document.pdf",
            total_pages=1,
            created_date="2025-08-08T10:00:00Z",
            file_size=1024000,
            language="zh-TW"
        ),
        markdown_content="# 測試文檔\n\n這是測試用的Markdown內容。"
    )


@pytest.fixture
def sample_chat_messages():
    """示例聊天消息"""
    from src.api.models.request_models import ChatMessage
    
    return [
        ChatMessage(role="user", content="你好，請幫我分析這個文檔"),
        ChatMessage(role="assistant", content="我會幫您分析文檔內容"),
        ChatMessage(role="user", content="文檔中的圖表說明了什麼？")
    ]


# ============ 文件測試 Fixtures ============

@pytest.fixture
def create_test_pdf(temp_dir: Path) -> Path:
    """創建測試PDF文件"""
    test_pdf_path = temp_dir / "test_document.pdf"
    
    # 創建一個簡單的PDF文件（模擬）
    with open(test_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n")  # PDF頭部
        f.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        f.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        f.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n")
        f.write(b"xref\n0 4\n")
        f.write(b"trailer\n<< /Size 4 /Root 1 0 R >>\n")
        f.write(b"%%EOF\n")
    
    return test_pdf_path


@pytest.fixture  
def create_test_docx(temp_dir: Path) -> Path:
    """創建測試Word文件"""
    test_docx_path = temp_dir / "test_document.docx"
    
    # 創建一個簡單的DOCX文件（模擬）
    # 實際上這不是有效的DOCX，但足夠用於測試
    with open(test_docx_path, "wb") as f:
        f.write(b"PK\x03\x04")  # ZIP文件頭部
        f.write(b"fake_docx_content")
    
    return test_docx_path


# ============ 測試工具函數 ============

def assert_valid_uuid(uuid_string: str):
    """驗證UUID格式"""
    import uuid
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def assert_valid_iso_datetime(datetime_string: str):
    """驗證ISO日期時間格式"""
    from datetime import datetime
    try:
        datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


@pytest.fixture
def assert_helpers():
    """測試斷言幫助函數"""
    return {
        "assert_valid_uuid": assert_valid_uuid,
        "assert_valid_iso_datetime": assert_valid_iso_datetime
    }


# ============ 性能測試 Fixtures ============

@pytest.fixture
def performance_timer():
    """性能計時器"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
            return self
        
        def stop(self):
            self.end_time = time.time()
            return self
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
        
        def assert_under(self, max_seconds):
            assert self.elapsed is not None, "計時器未啟動或停止"
            assert self.elapsed < max_seconds, f"執行時間 {self.elapsed:.3f}s 超過限制 {max_seconds}s"
    
    return Timer()


# ============ 環境標記 ============

def pytest_runtest_setup(item):
    """根據標記跳過測試"""
    import os
    
    # 跳過需要Azure的測試（如果沒有配置）
    if "azure" in item.keywords:
        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            pytest.skip("需要Azure OpenAI配置")
    
    # 跳過慢測試（除非明確要求）
    if "slow" in item.keywords:
        if not item.config.getoption("--runslow"):
            pytest.skip("跳過慢速測試（使用 --runslow 運行）")


def pytest_addoption(parser):
    """添加pytest命令行選項"""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="運行慢速測試"
    )
    parser.addoption(
        "--runazure", action="store_true", default=False, help="運行Azure OpenAI測試"
    )
