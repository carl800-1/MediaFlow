# MediaFlow 快速开始

## 5分钟快速部署

### 方式一：使用启动脚本 (推荐)

```bash
# 克隆或进入项目目录
cd /Volumes/新加卷/program/MediaFlow

# 启动（自动检查环境、安装依赖）
./start.sh
```

### 方式二：手动启动

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate   # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化配置
mkdir -p config data logs
cp config/config.example.yaml config/config.yaml

# 4. 启动服务
python -m mediaflow.main
```

### 方式三：Docker

```bash
cd docker
./build.sh run
```

## 访问服务

打开浏览器访问：**http://localhost:3000**

## 功能说明

### 1. 添加站点

点击"站点管理" → "添加站点"

填写站点信息：
- 站点名称：例如 "MTEAM"
- 站点URL：站点主页地址
- Cookie：登录后的Cookie内容
- 签到URL：签到页面地址
- RSS地址：RSS订阅地址

### 2. 添加下载器

点击"下载器" → "添加下载器"

支持的下载器：
- Qbittorrent
- Transmission
- Aria2

### 3. 创建刷流任务

点击"刷流任务" → "新建任务"

配置：
- 选择站点
- 选择下载器
- 设置检查间隔
- 配置过滤规则

### 4. RSS订阅

点击"订阅" → "新建订阅"

配置：
- RSS地址
- 下载器
- 关键词过滤

### 5. 搜索资源

在搜索页面输入关键词即可搜索多个站点

## 配置说明

### 修改端口

编辑 `config/config.yaml`：

```yaml
app:
  port: 3000  # 修改为你想要的端口
```

或使用命令行参数：

```bash
./start.sh --port 8080
```

### 配置通知

在 `config/config.yaml` 中配置：

```yaml
notification:
  enabled: true
  telegram_bot_token: "your-bot-token"
  telegram_chat_id: "your-chat-id"
```

## 常见问题

### Q: 端口被占用怎么办？

A: 更改端口号：
```bash
./start.sh --port 3001
```

### Q: 如何查看日志？

A: 查看 `logs/mediaflow.log`

### Q: 如何重置配置？

A: 删除 `config/config.yaml` 后重新启动

### Q: 数据存储在哪里？

A: 所有数据存储在 `data/` 目录

## 目录结构

```
MediaFlow/
├── config/          # 配置文件
├── data/            # 数据存储
├── logs/            # 日志文件
├── mediaflow/       # 源码
├── tests/           # 测试
├── docs/            # 文档
└── docker/          # Docker配置
```

## 下一步

- 查看 [API文档](docs/API.md)
- 查看 [部署指南](docs/DEPLOY.md)
- 访问项目主页：http://localhost:3000

## 技术支持

如遇到问题，请检查日志文件 `logs/mediaflow.log`
