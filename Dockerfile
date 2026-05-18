# MediaFlow Dockerfile - 修复版
# 多阶段构建优化，确保 ruamel.yaml 正确安装

# ============ 构建阶段 ============
FROM python:3.10-slim as builder

WORKDIR /app

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 先安装 ruamel.yaml（关键依赖）
RUN pip install --no-cache-dir --user 'ruamel.yaml>=0.17.32' 'ruamel.yaml.clib>=0.2.0'

# 复制并安装其他依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 验证 ruamel.yaml 安装
RUN python -c "import ruamel.yaml; print('ruamel.yaml installed:', ruamel.yaml.__version__)"

# ============ 运行阶段 ============
FROM python:3.10-slim

LABEL maintainer="MediaFlow Team"
LABEL description="MediaFlow - 新一代NAS媒体库智能管理系统"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDIAFLOW_HOME="/app" \
    PATH="/root/.local/bin:$PATH" \
    PYTHONPATH="/root/.local/lib/python3.10/site-packages:$PYTHONPATH"

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libxml2 \
    libxslt1.1 \
    libffi8 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制所有 Python 包（关键修复）
COPY --from=builder /root/.local /root/.local

# 复制项目文件
COPY mediaflow ./mediaflow
COPY web ./web
COPY config ./config
COPY run.py .
COPY config.py .
COPY log.py .
COPY initializer.py .
COPY version.py .
COPY requirements.txt .
COPY third_party.txt .

# 创建必要的目录和符号链接
RUN mkdir -p /app/data /app/logs /app/config && \
    ln -sf mediaflow app

# 最终验证
RUN python -c "import ruamel.yaml; print('✓ ruamel.yaml available:', ruamel.yaml.__version__)" && \
    python -c "from config import Config; print('✓ Config module loaded')"

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

ENTRYPOINT ["python", "run.py"]
CMD []
