#!/usr/bin/env python3
"""
MediaFlow 启动脚本
"""

import sys
import os
import argparse


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MediaFlow 媒体库管理系统")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config/config.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=None,
        help="服务端口"
    )
    parser.add_argument(
        "--host",
        "-H",
        type=str,
        default=None,
        help="服务地址"
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="调试模式"
    )
    parser.add_argument(
        "--version",
        "-v",
        action="store_true",
        help="显示版本信息"
    )

    args = parser.parse_args()

    # 导入版本信息
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mediaflow.version import __version__

    if args.version:
        print(f"MediaFlow {__version__}")
        return

    print(f"MediaFlow {__version__}")
    print("=" * 40)

    # 导入并启动应用
    try:
        from mediaflow.utils.config import ConfigManager
        from mediaflow.cli import app
        from mediaflow.utils.cli import getLogger

        logger = getLogger("main")

        # 初始化配置
        config = ConfigManager(args.config)

        # 启动Web服务
        host = args.host or config.app.host
        port = args.port or config.app.port
        debug = args.debug or config.app.debug

        print(f"启动服务: http://{host}:{port}")
        logger.info(f"启动 MediaFlow 服务: {host}:{port}")

        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )

    except KeyboardInterrupt:
        print("\n收到停止信号，正在退出...")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
