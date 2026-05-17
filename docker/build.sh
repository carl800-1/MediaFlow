#!/bin/bash
set -e

# MediaFlow 构建脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_step() {
    echo -e "${GREEN}[构建]${NC} $1"
}

echo_error() {
    echo -e "${RED}[错误]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

# 构建Docker镜像
build_docker() {
    echo_step "开始构建 Docker 镜像..."
    
    docker build -t mediaflow:latest \
        -f docker/Dockerfile .
    
    echo_step "Docker 镜像构建完成!"
}

# 运行容器
run_container() {
    echo_step "启动 MediaFlow 容器..."
    
    docker-compose -f docker/docker-compose.yml up -d
    
    echo_step "容器启动完成!"
    echo "访问地址: http://localhost:3000"
}

# 停止容器
stop_container() {
    echo_step "停止 MediaFlow 容器..."
    
    docker-compose -f docker/docker-compose.yml down
    
    echo_step "容器已停止!"
}

# 显示帮助
show_help() {
    echo "MediaFlow 构建脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  build    构建 Docker 镜像"
    echo "  run      启动容器"
    echo "  stop     停止容器"
    echo "  restart  重启容器"
    echo "  logs     查看日志"
    echo "  help     显示帮助"
    echo ""
}

# 主逻辑
case "${1:-help}" in
    build)
        build_docker
        ;;
    run)
        build_docker
        run_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        stop_container
        run_container
        ;;
    logs)
        docker-compose -f docker/docker-compose.yml logs -f
        ;;
    help|*)
        show_help
        ;;
esac
