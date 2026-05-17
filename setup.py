"""
CLI入口点安装脚本
"""

from setuptools import setup

setup(
    entry_points={
        "console_scripts": [
            "mediaflow=mediaflow.cli:main",
        ],
    },
)
