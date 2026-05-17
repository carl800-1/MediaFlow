@echo off
REM MediaFlow 启动脚本 (Windows)

setlocal

cd /d "%~dp0"

echo MediaFlow 启动脚本
echo =================

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    exit /b 1
)

echo [信息] 检查系统要求...

REM 创建虚拟环境
if not exist "venv" (
    echo [信息] 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
if not exist "venv\installed" (
    echo [信息] 安装依赖...
    pip install --upgrade pip
    pip install -r requirements.txt
    type nul > venv\installed
) else (
    echo [信息] 依赖已安装
)

REM 初始化配置
if not exist "config\config.yaml" (
    echo [信息] 初始化配置...
    if not exist "config" mkdir config
    if not exist "data" mkdir data
    if not exist "logs" mkdir logs
    copy config\config.example.yaml config\config.yaml
    echo [成功] 配置文件创建完成，请编辑 config\config.yaml
)

echo [成功] 启动 MediaFlow...
echo [信息] 访问: http://localhost:3000
echo [信息] 按 Ctrl+C 停止服务

python -m mediaflow.main %*

endlocal
