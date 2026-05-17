"""
日志配置模块
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    配置日志系统

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        log_to_file: 是否写入文件
        log_to_console: 是否输出到控制台

    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger("mediaflow")
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.handlers.clear()

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = ColoredFormatter(log_format, date_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    if log_to_file and log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


class Logger:
    """日志记录器类"""

    def __init__(self, name: str) -> None:
        self.logger = logging.getLogger(f"mediaflow.{name}")
        self.name = name

    def debug(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: object, **kwargs: object) -> None:
        self.logger.critical(msg, *args, **kwargs)


def getLogger(name: str) -> Logger:
    """获取日志记录器"""
    return Logger(name)
