# MediaFlow Dockerfile
# 使用官方 Python 3.10  slim 镜像作为基础
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    MEDIAFLOW_CONFIG=/app/config \
    MEDIAFLOW_DATA=/app/data

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml ./
COPY requirements.txt ./
COPY README.md ./
COPY setup.py ./
COPY version.py ./
COPY config.py ./
COPY log.py ./
COPY initializer.py ./
COPY run.py ./
COPY __init__.py ./

# 复制主要代码目录
COPY mediaflow/ ./mediaflow/
COPY config/ ./config/
COPY web/ ./web/

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/config

# 安装 Python 依赖
# 先安装 ruamel.yaml 和其他关键依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ruamel.yaml>=0.17.32 && \
    pip install --no-cache-dir -r requirements.txt

# 安装项目本身
RUN pip install --no-cache-dir -e .

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# 启动命令
CMD ["python", "run.py"]
