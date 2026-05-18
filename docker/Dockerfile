# MediaFlow Dockerfile
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDIAFLOW_HOME="/app" \
    PATH="/root/.local/bin:$PATH" \
    PYTHONPATH="/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 mediaflow

# 安装依赖（不使用--user，避免路径问题）
RUN pip install --no-cache-dir 'ruamel.yaml>=0.17.32'

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mediaflow ./mediaflow
COPY web ./web
COPY config ./config
COPY run.py .
COPY config.py .
COPY log.py .
COPY initializer.py .
COPY version.py .

# 创建软链接
RUN ln -s /app/mediaflow /app/app

RUN mkdir -p /app/data /app/logs /app/config && chown -R mediaflow:mediaflow /app

USER mediaflow

EXPOSE 3000

ENTRYPOINT ["python", "run.py"]
