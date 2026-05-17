"""基础配置测试"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_version_available():
    """测试版本信息"""
    try:
        from mediaflow.version import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)
    except ImportError as e:
        pytest.skip(f"Version module not available: {e}")


def test_module_structure():
    """测试模块结构"""
    required_modules = [
        'mediaflow.brushtask',
        'mediaflow.database',
        'mediaflow.downloader',
        'mediaflow.mediaserver',
        'mediaflow.scraper',
        'mediaflow.indexers',
        'mediaflow.sites',
        'mediaflow.subscribe',
        'mediaflow.web',
    ]

    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    assert len(missing) == 0, f"Missing modules: {', '.join(missing)}"
