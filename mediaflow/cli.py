"""
CLI命令行入口
"""

import os
import sys
import argparse
from pathlib import Path

from mediaflow.version import __version__
from mediaflow.utils.cli import setup_logging, getLogger
from mediaflow.utils.config import get_config, ConfigManager


logger = getLogger("cli")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="MediaFlow - 新一代NAS媒体库智能管理系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"MediaFlow {__version__}"
    )

    parser.add_argument(
        "--config", "-c",
        default=os.getenv("MEDIAFLOW_CONFIG", "config/config.yaml"),
        help="配置文件路径"
    )

    parser.add_argument(
        "--host",
        default=None,
        help="服务地址"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="服务端口"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="调试模式"
    )

    parser.add_argument(
        "--init",
        action="store_true",
        help="初始化配置"
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    config_manager = ConfigManager(config_path)

    log_level = "DEBUG" if args.debug else config_manager.app.log_level
    setup_logging(
        log_level=log_level,
        log_to_file=True,
        log_to_console=True
    )

    logger.info(f"MediaFlow {__version__}")
    logger.info(f"Config: {config_path}")

    if args.init:
        init_config(config_path)
        return

    host = args.host or config_manager.app.host
    port = args.port or config_manager.app.port
    debug = args.debug or config_manager.app.debug

    try:
        from mediaflow.web.app import run_app
        logger.info(f"Starting server at {host}:{port}")
        run_app(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


def init_config(config_path: Path) -> None:
    """初始化配置"""
    if config_path.exists():
        logger.warning(f"Config file already exists: {config_path}")
        response = input("Overwrite? [y/N]: ")
        if response.lower() != "y":
            return

    config_path.parent.mkdir(parents=True, exist_ok=True)

    from mediaflow.utils.config import ConfigManager
    config_manager = ConfigManager()
    config_manager.save()

    logger.info(f"Config file created: {config_path}")
    logger.info("Please edit the config file to set your preferences")


if __name__ == "__main__":
    main()
