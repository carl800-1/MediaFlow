# MediaFlow 完整家庭媒体中心部署方案

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     绿联 NAS (UGREEN NAS)                    │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ MediaFlow   │───▶│  下载器     │    │ Jellyfin/   │     │
│  │ 刷流/搜索   │    │ Qbittorrent│    │ Emby       │     │
│  │ RSS/订阅    │    │            │    │ 媒体服务器  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                                      │           │
│         ▼                                      ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              共享媒体库目录 (/media)                 │   │
│  │   movies/    tv/    anime/    music/               │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                             │
└──────────────────────────────┼─────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   播放设备          │
                    │ 绿联播放器/TV/手机  │
                    └─────────────────────┘
```

## 一、绿联 NAS Docker 部署配置

### 1. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  # MediaFlow - 媒体库管理
  mediaflow:
    image: mediaflow:latest
    container_name: mediaflow
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./mediaflow/config:/app/config
      - ./mediaflow/data:/app/data
      - ./mediaflow/logs:/app/logs
      - /media:/media:ro  # 绿联NAS媒体目录（只读）
    environment:
      - MEDIAFLOW_CONFIG=/app/config/config.yaml
    networks:
      - media-center

  # Jellyfin - 媒体服务器
  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    restart: unless-stopped
    ports:
      - "8096:8096"
      - "8920:8920"  # HTTPS
    volumes:
      - ./jellyfin/config:/config
      - ./jellyfin/cache:/cache
      - ./jellyfin/media:/media  # 媒体库目录
      - /media:/media:ro  # 绿联NAS媒体目录（只读）
    environment:
      - JELLYFIN_PublishedServerUrl=http://your-nas:8096
    networks:
      - media-center

  # Qbittorrent - 下载器
  qbittorrent:
    image: qbittorrent/qbittorrenten:latest
    container_name: qbittorrent
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "6881:6881"
      - "6881:6881/udp"
    volumes:
      - ./qbittorrent/config:/config
      - ./qbittorrent/downloads:/downloads
      - /media:/media:ro
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Asia/Shanghai
    networks:
      - media-center

networks:
  media-center:
    driver: bridge
```

### 2. 目录结构

```
/volume1/docker/media-center/
├── docker-compose.yml
├── mediaflow/
│   ├── config/
│   │   └── config.yaml
│   ├── data/
│   └── logs/
├── jellyfin/
│   ├── config/
│   ├── cache/
│   └── media/
├── qbittorrent/
│   ├── config/
│   └── downloads/
└── media/ -> /volume1/media  # 绿联NAS媒体目录
```

## 二、MediaFlow 配置

### config/config.yaml

```yaml
# MediaFlow 配置文件

app:
  debug: false
  host: "0.0.0.0"
  port: 3000
  secret_key: "your-secret-key-change-this"
  timezone: "Asia/Shanghai"

# 数据库配置
database:
  type: "sqlite"
  path: "/app/data/mediaflow.db"

# 下载器配置
downloaders:
  - name: "Qbittorrent"
    type: "qbittorrent"
    host: "qbittorrent"
    port: 8080
    username: "admin"
    password: "adminadmin"

# 媒体服务器配置 (Jellyfin/Emby)
media_servers:
  - name: "Jellyfin"
    server_type: "jellyfin"
    host: "jellyfin"
    port: 8096
    api_key: "your-jellyfin-api-key"

# 索引器配置 (Jackett/Prowlarr)
indexers:
  - name: "Jackett"
    type: "jackett"
    url: "http://your-nas:9117"
    api_key: "your-jackett-api-key"

# 通知配置
notification:
  enabled: true
  telegram_bot_token: "your-bot-token"
  telegram_chat_id: "your-chat-id"

# 媒体刮削配置
scraper:
  tmdb_api_key: "your-tmdb-api-key"
  douban_cookie: "your-douban-cookie"

# 文件同步配置
sync:
  watch_paths:
    - "/downloads/completed"
  target_paths:
    movies: "/media/movies"
    tv: "/media/tv"
    anime: "/media/anime"
```

## 三、MediaFlow Web 管理界面

启动后访问 **http://绿联NAS:3000**

### 功能模块

| 模块 | 功能 |
|------|------|
| **刷流任务** | 自动刷PT站点、做种、删种 |
| **RSS订阅** | 监控订阅源、自动下载 |
| **媒体搜索** | 多索引器聚合搜索 |
| **下载器** | 管理Qbittorrent等下载任务 |
| **媒体库** | Jellyfin/Emby集成、刷新库 |
| **站点管理** | PT站点信息、签到 |
| **文件同步** | 下载完成后自动整理 |

## 四、Jellyfin 配置（媒体服务器）

### 1. 访问 Jellyfin
访问 **http://绿联NAS:8096**

### 2. 添加媒体库

| 媒体库类型 | 路径 |
|-----------|------|
| 电影 | `/media/movies` |
| 电视剧 | `/media/tv` |
| 动漫 | `/media/anime` |
| 音乐 | `/media/music` |

### 3. 配置实时转码（可选）

如果绿联播放器不支持原片格式，建议开启转码：

```yaml
jellyfin:
  environment:
    - JELLYFIN_FFMPEG_ARGS: "-c:v h264_qsv -c:a aac -q:v 5"
```

## 五、绿联播放器访问

### 方式1：Jellyfin/Emby App

在绿联播放器应用商店下载 **Jellyfin** 或 **Emby** 应用：

```
Jellyfin App → 添加服务器 → http://绿联NAS:8096
```

### 方式2：DLNA/投屏

Jellyfin 自带 DLNA 支持，绿联播放器可直接发现并播放。

### 方式3：Web 浏览器

```
绿联浏览器 → http://绿联NAS:8096
```

## 六、完整工作流程

```
1. PT刷流
   MediaFlow 刷流任务 ─▶ Qbittorrent 下载 ─▶ /downloads

2. 自动整理
   MediaFlow 文件同步 ─▶ 自动重命名 ─▶ /media/movies 或 /media/tv

3. 媒体刮削
   MediaFlow 自动刮削 ─▶ Jellyfin 识别 ─▶ 封面、简介、评分

4. 播放
   Jellyfin ─▶ 绿联播放器/TV/手机 ─▶ 观看
```

## 七、启动命令

```bash
# SSH 登录绿联 NAS
ssh admin@绿联NAS地址

# 进入目录
cd /volume1/docker/media-center

# 启动所有服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f mediaflow
```

## 八、常见问题

### Q1: 绿联 NAS 如何开启 SSH？
> 控制面板 → 终端机 → 启用 SSH

### Q2: Docker 端口冲突？
> 修改 docker-compose.yml 中的端口映射

### Q3: 如何获取 Jellyfin API Key？
> Jellyfin Web → 控制台 → API Key → 新建

### Q4: 媒体库路径如何共享？
> 确保 Jellyfin 和 MediaFlow 都能访问 `/volume1/media`
