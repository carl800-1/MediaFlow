# MediaFlow 部署指南

## Docker 部署

### 快速开始

```bash
# 进入docker目录
cd /Volumes/新加卷/program/MediaFlow/docker

# 构建并启动
./build.sh run

# 查看日志
./build.sh logs

# 停止服务
./build.sh stop
```

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| MEDIAFLOW_CONFIG | 配置文件路径 | /app/config/config.yaml |
| MEDIAFLOW_PORT | 服务端口 | 3000 |
| MEDIAFLOW_HOST | 服务地址 | 0.0.0.0 |

### 数据持久化

```yaml
# docker-compose.yml
volumes:
  - ./data:/app/data      # 数据库
  - ./logs:/app/logs      # 日志
  - ./config:/app/config  # 配置
```

## 手动部署

### 系统要求

- Python 3.10+
- SQLite3

### 安装步骤

1. 克隆代码
```bash
cd /path/to/deploy
git clone https://github.com/your-repo/MediaFlow.git
cd MediaFlow
```

2. 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置
```bash
cp config/config.example.yaml config/config.yaml
# 编辑 config/config.yaml
```

5. 运行
```bash
python -m mediaflow.cli
# or
mediaflow
```

## 配置说明

### 基础配置 (config/config.yaml)

```yaml
app:
  debug: false
  host: "0.0.0.0"
  port: 3000
  secret_key: "your-secret-key"
  log_level: "INFO"
  timezone: "Asia/Shanghai"

database:
  type: "sqlite"
  path: "data/mediaflow.db"

notification:
  enabled: true
  telegram_bot_token: "your-bot-token"
  telegram_chat_id: "your-chat-id"
```

### 下载器配置

```yaml
downloader:
  type: "qbittorrent"  # qbittorrent, transmission, aria2
  host: "localhost"
  port: 8080
  username: "admin"
  password: "password"
```

## 反向代理配置

### Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Caddy

```caddy
your-domain.com {
    reverse_proxy localhost:3000
}
```

## 进程管理

### Systemd (Linux)

```ini
[Unit]
Description=MediaFlow
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/MediaFlow
ExecStart=/path/to/venv/bin/python -m mediaflow.cli
Restart=always

[Install]
WantedBy=multi-user.target
```

安装服务：
```bash
sudo cp mediaflow.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mediaflow
sudo systemctl start mediaflow
```

## 备份与恢复

### 备份

```bash
# 备份数据库
cp data/mediaflow.db backup/mediaflow_$(date +%Y%m%d).db

# 备份配置
cp config/config.yaml backup/config_$(date +%Y%m%d).yaml
```

### 恢复

```bash
# 停止服务
docker-compose down

# 恢复数据库
cp backup/mediaflow_20240101.db data/mediaflow.db

# 启动服务
docker-compose up -d
```

## 安全建议

1. **修改默认密钥**
```yaml
app:
  secret_key: "your-random-secret-key"
```

2. **启用HTTPS**
使用反向代理配合Let's Encrypt证书

3. **限制访问**
```yaml
app:
  host: "127.0.0.1"  # 仅本地访问
```

4. **定期更新**
```bash
docker pull mediaflow:latest
docker-compose up -d
```

## 故障排查

### 查看日志

```bash
# Docker
docker-compose logs -f

# 直接运行
tail -f logs/mediaflow.log
```

### 常见问题

1. **端口被占用**
```bash
# 查找占用进程
lsof -i :3000
# 更改端口
MEDIAFLOW_PORT=3001 docker-compose up
```

2. **数据库锁定**
```bash
# 停止所有连接
pkill -f mediaflow
# 重试
```

3. **权限问题**
```bash
chown -R user:user /path/to/MediaFlow
```
