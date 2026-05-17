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

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# ============ 运行阶段 ============
FROM python:3.10-slim

LABEL maintainer="MediaFlow Team"
LABEL description="MediaFlow - 新一代NAS媒体库智能管理系统"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDIAFLOW_HOME="/app" \
    PATH="/root/.local/bin:$PATH"

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

RUN mkdir -p /app/data /app/logs /app/config \
    && chown -R mediaflow:mediaflow /app

USER mediaflow

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

ENTRYPOINT ["python", "run.py"]
CMD []
