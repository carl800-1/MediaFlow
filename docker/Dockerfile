# MediaFlow Dockerfile
# 多阶段构建优化

# ============ 构建阶段 ============
FROM python:3.10-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# 【2025-05-18 修复】先安装 ruamel.yaml
RUN pip install --no-cache-dir --user 'ruamel.yaml>=0.17.32' 'ruamel.yaml.clib>=0.2.0'

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============ 运行阶段 ============
FROM python:3.10-slim

LABEL maintainer="MediaFlow Team"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDIAFLOW_HOME="/app" \
    PATH="/root/.local/bin:$PATH" \
    PYTHONPATH="/app:/root/.local/lib/python3.10/site-packages"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 mediaflow

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/requirements.txt .

COPY mediaflow ./mediaflow
COPY web ./web
COPY config ./config
COPY run.py .
COPY config.py .
COPY log.py .
COPY initializer.py .
COPY version.py .

# 【2025-05-18 修复】创建 app 软链接
RUN ln -s /app/mediaflow /app/app

RUN mkdir -p /app/data /app/logs /app/config && chown -R mediaflow:mediaflow /app

# ============ 验证步骤（每步独立显示） ============
RUN echo "=== Step 1: Check Python version ===" && python --version

RUN echo "=== Step 2: Check ruamel.yaml ===" && python -c "import ruamel.yaml; print('ruamel.yaml version:', ruamel.yaml.__version__)"

RUN echo "=== Step 3: Check /app directory ===" && ls -la /app/

RUN echo "=== Step 4: Check app symlink ===" && ls -la /app/app

RUN echo "=== Step 5: Check mediaflow/brushtask exists ===" && ls /app/mediaflow/brushtask/

RUN echo "=== Step 6: Import app.brushtask ===" && python -c "from app.brushtask import BrushTask; print('SUCCESS: app.brushtask imported')"

RUN echo "=== All verification steps completed ==="

USER mediaflow

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

ENTRYPOINT ["python", "run.py"]
CMD []
