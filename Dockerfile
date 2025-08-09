# 智能文件轉換與RAG知識庫系統 - Multi-stage Dockerfile
# 支持開發、生產和工作進程多種部署模式

# ====== 基礎鏡像配置 ======
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim as base

# 設置環境變量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 編譯工具
    build-essential \
    gcc \
    g++ \
    # 圖像處理依賴
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # PDF處理依賴
    libmupdf-dev \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    # 其他工具
    curl \
    wget \
    git \
    # 清理
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 創建應用用戶
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 設置工作目錄
WORKDIR /app

# ====== 依賴安裝階段 ======
FROM base as dependencies

# 複製依賴文件
COPY requirements.txt pyproject.toml ./

# 安裝Python依賴
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ====== 開發環境 ======
FROM dependencies as development

# 安裝開發依賴
RUN pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy

# 複製源代碼
COPY . .

# 設置權限
RUN chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 開發模式啟動命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ====== 生產環境 ======
FROM dependencies as production

# 複製應用代碼
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY pyproject.toml README.md ./

# 創建必要目錄
RUN mkdir -p /app/data/input /app/data/output /app/data/temp /app/logs && \
    chown -R appuser:appuser /app

# 設置權限
USER appuser

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 生產模式啟動命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ====== 工作進程環境 ======
FROM dependencies as worker

# 複製應用代碼
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY pyproject.toml ./

# 創建必要目錄
RUN mkdir -p /app/data/input /app/data/output /app/data/temp /app/logs && \
    chown -R appuser:appuser /app

# 設置權限
USER appuser

# 工作進程啟動命令
CMD ["python", "-m", "src.worker"]

# ====== 測試環境 ======
FROM development as test

# 複製測試文件
COPY tests/ ./tests/

# 運行測試
RUN python -m pytest tests/ -v --cov=src --cov-report=html

# ====== 構建說明 ======
#
# 構建命令：
# - 開發環境：docker build --target development -t ap-rag:dev .
# - 生產環境：docker build --target production -t ap-rag:prod .
# - 工作進程：docker build --target worker -t ap-rag:worker .
# - 測試環境：docker build --target test -t ap-rag:test .
#
# 運行命令：
# - 開發：docker run -p 8000:8000 -v $(pwd)/src:/app/src ap-rag:dev
# - 生產：docker run -p 8000:8000 ap-rag:prod
# - 工作進程：docker run ap-rag:worker
#
# 性能優化：
# - 使用 .dockerignore 排除不必要文件
# - 多階段構建減少最終鏡像大小
# - 非root用戶運行提高安全性
# - 健康檢查確保服務可用性
