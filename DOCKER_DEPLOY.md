# MediaFlow Docker 部署指南

## GitHub Secrets 配置

要让 GitHub Actions 自动构建并推送 Docker 镜像到 Docker Hub，你需要在 GitHub 仓库中配置以下 Secrets：

### 必需的配置项

1. 访问你的 GitHub 仓库: https://github.com/carl800-1/MediaFlow/settings/secrets/actions

2. 点击 "New repository secret" 添加以下两个 Secrets：

   | Secret 名称 | 说明 | 如何获取 |
   |-------------|------|---------|
   | `DOCKERHUB_USERNAME` | Docker Hub 用户名 | 登录 Docker Hub，点击右上角头像查看 |
   | `DOCKERHUB_TOKEN` | Docker Hub 访问令牌 | Docker Hub → Account Settings → Security → Access Tokens → New Access Token |

3. **重要**: 确保 Access Token 包含以下权限：
   - `Create/Update Repositories`
   - `Delete Repositories`
   - `Read, Write, Delete Images`

### 验证配置

配置完成后，推送一个 commit 到 main 分支，应该能看到：

1. **CI workflow** 运行测试和语法检查
2. **Docker workflow** 构建并推送镜像到 `carl800-1/mediaflow`

### 手动触发构建

如果你想手动触发 Docker 构建：

1. 进入仓库页面
2. 点击 "Actions" 标签
3. 选择 "Build and Push Docker Image"
4. 点击 "Run workflow" 按钮

### 查看构建日志

如果构建失败，查看日志的方法：

1. 进入仓库页面
2. 点击 "Actions" 标签
3. 点击失败的 workflow 运行
4. 查看详细的错误信息

### 常见问题

#### Docker Hub 登录失败

**错误信息**:
```
Error: Cannot perform an interactive login from a non-interactive shell.
```

**解决方案**:
1. 确认 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_TOKEN` 已正确配置
2. 确认 Docker Hub Access Token 有正确的权限
3. 确认 Token 没有过期

#### 构建超时

**解决方案**:
- 首次构建可能需要较长时间（约 5-10 分钟）
- GitHub Actions 免费账户有使用限制

#### 推送权限被拒绝

**错误信息**:
```
denied: requested access to the resource is denied
```

**解决方案**:
1. 确认 Docker Hub 仓库名称是 `carl800-1/mediaflow`
2. 如果你使用其他用户名，需要修改 `.github/workflows/docker.yml` 中的 `IMAGE_NAME`
