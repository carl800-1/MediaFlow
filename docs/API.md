# MediaFlow API 文档

## 概述

MediaFlow API 提供了一套完整的 RESTful API 接口，用于管理媒体库、刷流任务、下载器、站点和订阅等资源。

## 基础信息

- **基础URL**: `http://localhost:3000/api`
- **认证方式**: Bearer Token
- **响应格式**: JSON

## 认证

所有需要认证的API需要在请求头中包含：

```
Authorization: Bearer <token>
```

## 通用响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

- `code`: 0 表示成功，其他值表示错误
- `message`: 错误信息
- `data`: 响应数据

## API 端点

### 系统

#### 健康检查
```
GET /api/health
```

响应：
```json
{
  "status": "healthy",
  "service": "MediaFlow"
}
```

#### 获取系统信息
```
GET /api/system/info
```

响应：
```json
{
  "code": 0,
  "data": {
    "name": "MediaFlow",
    "version": "1.0.0",
    "description": "新一代NAS媒体库智能管理系统"
  }
}
```

#### 获取系统配置
```
GET /api/system/config
```

### 刷流任务

#### 获取所有任务
```
GET /api/brushtask/
```

响应：
```json
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "name": "刷流任务1",
      "site_id": 1,
      "downloader_id": 1,
      "interval": "30",
      "state": "Y",
      "enabled": true
    }
  ]
}
```

#### 创建任务
```
POST /api/brushtask/
```

请求体：
```json
{
  "name": "新任务",
  "site_id": 1,
  "downloader_id": 1,
  "interval": "30",
  "filter_rule": "{\"include_keywords\": [\"1080p\"]}"
}
```

#### 启动任务
```
POST /api/brushtask/{task_id}/start
```

#### 停止任务
```
POST /api/brushtask/{task_id}/stop
```

### 下载器

#### 获取所有下载器
```
GET /api/downloader/
```

响应：
```json
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "name": "Qbittorrent",
      "type": "qbittorrent",
      "host": "localhost",
      "port": 8080,
      "enabled": true,
      "torrents_count": 10,
      "download_speed": 1024000,
      "upload_speed": 512000
    }
  ]
}
```

#### 添加下载器
```
POST /api/downloader/
```

请求体：
```json
{
  "name": "Qbittorrent",
  "type": "qbittorrent",
  "host": "localhost",
  "port": 8080,
  "username": "admin",
  "password": "admin123"
}
```

### 搜索

#### 搜索资源
```
GET /api/search/?keyword=电影名&media_type=movie
```

参数：
- `keyword` (必需): 搜索关键词
- `media_type`: 电影或剧集
- `year`: 年份
- `page`: 页码
- `page_size`: 每页数量

响应：
```json
{
  "code": 0,
  "data": {
    "keyword": "电影名",
    "total": 10,
    "page": 1,
    "page_size": 20,
    "results": [
      {
        "title": "电影名",
        "year": 2023,
        "media_type": "movie",
        "tmdb_id": 123,
        "score": 95.5,
        "torrents": [
          {
            "title": "电影名.1080p",
            "size": 2147483648,
            "seeders": 100,
            "leechers": 20
          }
        ]
      }
    ]
  }
}
```

### 站点

#### 获取所有站点
```
GET /api/site/
```

#### 添加站点
```
POST /api/site/
```

请求体：
```json
{
  "name": "MTEAM",
  "url": "https://www.mteam.cc",
  "cookie": "cookie内容",
  "sign_url": "https://www.mteam.cc/sign",
  "rss_url": "https://www.mteam.cc/rss"
}
```

#### 站点签到
```
POST /api/site/{site_id}/signin
```

#### 批量签到
```
POST /api/site/signin/all
```

### 订阅

#### 获取所有订阅
```
GET /api/subscription/
```

#### 创建订阅
```
POST /api/subscription/
```

请求体：
```json
{
  "name": "RSS订阅",
  "rss_url": "https://example.com/rss",
  "downloader_id": 1,
  "keywords": "1080p,蓝光",
  "auto_download": true
}
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

## 速率限制

暂无速率限制。
