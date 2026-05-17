# MediaFlow - 新一代NAS媒体库智能管理系统

## 功能特性

- **刷流任务**: 支持多站点、多下载器的自动化刷流
- **媒体搜索**: 聚合多个索引器，智能搜索和过滤
- **RSS订阅**: 支持自定义RSS订阅和自动下载
- **站点管理**: 统一管理PT站点，支持批量签到
- **多下载器**: 支持Qbittorrent、Transmission、Aria2等
- **消息通知**: 支持Telegram、微信、邮件等多种通知渠道

## 技术栈

- Python 3.10+
- 类型注解覆盖率 > 80%
- 单元测试覆盖率 > 60%
- 模块化架构设计

## 快速开始

### 安装

```bash
pip install -e .
```

### 配置

创建 `config/config.yaml`:

```yaml
app:
  debug: false
  host: "0.0.0.0"
  port: 3000

database:
  type: sqlite
  path: "data/mediaflow.db"

notification:
  enabled: true
  telegram_bot_token: "your-bot-token"
  telegram_chat_id: "your-chat-id"
```

### 运行

```bash
mediaflow
```

## 开发

### 代码规范

```bash
# 运行代码检查
ruff check mediaflow

# 运行代码格式化
black mediaflow

# 运行类型检查
mypy mediaflow

# 运行测试
pytest
```

### 项目结构

```
mediaflow/
├── mediaflow/           # 主包
│   ├── brushtask/       # 刷流任务模块
│   ├── database/        # 数据库模块
│   ├── downloader/      # 下载器模块
│   ├── media/           # 媒体信息模块
│   ├── message/         # 消息通知模块
│   ├── search/          # 搜索引擎模块
│   ├── sites/           # 站点管理模块
│   ├── subscribe/       # 订阅管理模块
│   ├── types/           # 类型定义模块
│   └── utils/           # 工具函数模块
├── tests/               # 测试目录
├── config/              # 配置文件目录
└── data/                # 数据目录
```

## 许可证

AGPL-3.0
