# MediaFlow Dockerfile
# 多阶段构建优化

# ============ 构建阶段 ============
FROM python:3.10-slim as builder

WORKDIR /app

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# 【2025-05-18 修复】先安装 ruamel.yaml，确保关键依赖优先安装
RUN pip install --no-cache-dir --user 'ruamel.yaml>=0.17.32' 'ruamel.yaml.clib>=0.2.0'

# 复制并安装其他依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 【2025-05-18 修复】验证 builder 阶段安装成功
RUN python -c "import ruamel.yaml; print('Builder: ruamel.yaml OK')"

# ============ 运行阶段 ============
FROM python:3.10-slim

LABEL maintainer="MediaFlow Team"
LABEL description="MediaFlow - 新一代NAS媒体库智能管理系统"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDIAFLOW_HOME="/app" \
    PATH="/root/.local/bin:$PATH"

# 【2025-05-18 修复】添加 PYTHONPATH 包含 /app 目录
ENV PYTHONPATH="/app:/root/.local/lib/python3.10/site-packages"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 mediaflow

WORKDIR /app

# 从构建阶段复制所有 Python 包
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/requirements.txt .

# 复制项目文件
COPY mediaflow ./mediaflow
COPY web ./web
COPY config ./config
COPY run.py .
COPY config.py .
COPY log.py .
COPY initializer.py .
COPY version.py .

# 【2025-05-18 修复】创建 app 软链接指向 mediaflow
RUN ln -s /app/mediaflow /app/app

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/config \
    && chown -R mediaflow:mediaflow /app

# 【2025-05-18 修复】分步验证，便于排查问题
RUN echo "=== 验证 ruamel.yaml ===" && \
    python -c "import ruamel.yaml; print('✓ ruamel.yaml OK, version:', ruamel.yaml.__version__)" && \
    echo "=== 验证 app 软链接 ===" && \
    ls -la /app/ && \
    echo "=== 验证 app.brushtask ===" && \
    python -c "from app.brushtask import BrushTask; print('✓ app.brushtask OK')" && \
    echo "=== 所有验证通过 ==="

USER mediaflow

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

ENTRYPOINT ["python", "run.py"]
CMD []
