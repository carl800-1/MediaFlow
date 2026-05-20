# MediaFlow Dockerfile
# 多阶段构建优化，确保依赖正确安装

# ============ 构建阶段 ============
FROM python:3.10-slim as builder

WORKDIR /app

# 安装编译依赖（包含 Python 包编译所需的全部系统库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    python3-dev \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    && rm -rf /var/lib/apt/lists/*

# 先安装 ruamel.yaml（关键依赖）
RUN pip install --no-cache-dir --user 'ruamel.yaml>=0.17.32' 'ruamel.yaml.clib>=0.2.0'

# 复制并安装其他依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============ 运行阶段 ============
FROM python:3.10-slim

LABEL maintainer="MediaFlow Team"
LABEL description="MediaFlow - 新一代NAS媒体库智能管理系统"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDIAFLOW_HOME="/app" \
    PATH="/root/.local/bin:$PATH" \
    PYTHONPATH="/root/.local/lib/python3.10/site-packages:$PYTHONPATH" \
    NASTOOL_CONFIG="/app/config/config.yaml"

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libxml2 \
    libxslt1.1 \
    libffi8 \
    libjpeg62-turbo \
    libpng16-16 \
    libfreetype6 \
    liblcms2-2 \
    libopenjp2-7 \
    libtiff6 \
    libwebp7 \
    libharfbuzz0b \
    libfribidi0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制所有 Python 包
COPY --from=builder /root/.local /root/.local

# 复制项目文件
COPY mediaflow ./mediaflow
COPY web ./web
COPY run.py .
COPY config.py .
COPY log.py .
COPY initializer.py .
COPY version.py .
COPY third_party.txt .
COPY config/config.example.yaml ./config/config.example.yaml

# 创建必要的目录、符号链接和默认配置
RUN mkdir -p /app/data /app/logs && \
    ln -sf /app/mediaflow /app/app && \
    cp /app/config/config.example.yaml /app/config/config.yaml

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

ENTRYPOINT ["python", "run.py"]
