#!/bin/bash
# MediaFlow 启动脚本

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_info "检查系统要求..."

    if ! command -v python3 &> /dev/null; then
        print_error "未找到Python3，请先安装Python 3.10+"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]; }; then
        print_error "Python版本过旧: $PYTHON_VERSION，需要Python 3.10+"
        exit 1
    fi

    print_success "Python版本: $PYTHON_VERSION"
}

setup_venv() {
    if [ ! -d "venv" ]; then
        print_info "创建虚拟环境..."
        python3 -m venv venv
        print_success "虚拟环境创建完成"
    fi

    source venv/bin/activate
}

install_dependencies() {
    print_info "检查依赖..."

    if [ ! -f "venv/installed" ] || [ "requirements.txt" -nt "venv/installed" ]; then
        print_info "安装依赖..."
        pip install --upgrade pip
        pip install -r requirements.txt
        touch venv/installed
        print_success "依赖安装完成"
    fi
}

initialize_config() {
    if [ ! -f "config/config.yaml" ]; then
        print_info "初始化配置..."
        mkdir -p config data logs
        cp config/config.example.yaml config/config.yaml
        print_success "配置文件创建完成，请编辑 config/config.yaml"
    fi
}

start_server() {
    print_info "启动 MediaFlow..."
    print_success "服务已启动: http://localhost:3000"
    print_info "按 Ctrl+C 停止服务"

    python3 -m mediaflow.main "$@"
}

show_help() {
    echo "MediaFlow 启动脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start      启动服务（默认）"
    echo "  install    安装依赖"
    echo "  update     更新依赖"
    echo "  test       运行测试"
    echo "  help       显示帮助"
    echo ""
    echo "示例:"
    echo "  $0"
    echo "  $0 start"
    echo "  $0 install"
    echo "  $0 --port 3001"
}

# 主逻辑
case "${1:-start}" in
    "start")
        check_requirements
        setup_venv
        install_dependencies
        initialize_config
        start_server "${@:2}"
        ;;
    "install")
        check_requirements
        setup_venv
        install_dependencies
        initialize_config
        print_success "安装完成"
        ;;
    "update")
        setup_venv
        print_info "更新依赖..."
        pip install --upgrade -r requirements.txt
        touch venv/installed
        print_success "更新完成"
        ;;
    "test")
        setup_venv
        print_info "运行测试..."
        python -m pytest tests/ -v
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        # 直接传递参数给start命令
        check_requirements
        setup_venv
        install_dependencies
        initialize_config
        start_server "$@"
        ;;
esac
