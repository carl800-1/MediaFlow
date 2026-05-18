#!/usr/bin/env python3
"""
绿联影视模块测试脚本
"""
import sys
import os

# 设置环境变量
os.environ['NASTOOL_CONFIG'] = './config/config.yaml'
sys.path.insert(0, '.')

from app.mediaserver.client.ugreen import Ugreen
from app.utils.types import MediaServerType

def test_ugreen_basic():
    """测试绿联影视基本属性和配置"""
    print("=" * 50)
    print("测试绿联影视基本属性")
    print("=" * 50)

    # 测试类属性
    assert Ugreen.client_id == "ugreen", f"client_id 错误: {Ugreen.client_id}"
    assert Ugreen.client_type == MediaServerType.UGREEN, f"client_type 错误: {Ugreen.client_type}"
    assert Ugreen.client_name == "绿联影视", f"client_name 错误: {Ugreen.client_name}"

    print(f"✓ 客户端ID: {Ugreen.client_id}")
    print(f"✓ 客户端类型: {Ugreen.client_type}")
    print(f"✓ 客户端名称: {Ugreen.client_name}")

    # 测试 match 方法
    assert Ugreen.match("ugreen") == True, "match ugreen 失败"
    assert Ugreen.match(MediaServerType.UGREEN) == True, "match MediaServerType.UGREEN 失败"
    assert Ugreen.match("绿联影视") == True, "match 绿联影视 失败"
    assert Ugreen.match("emby") == False, "match emby 应该返回 False"

    print("✓ match 方法测试通过")
    print()

def test_ugreen_init():
    """测试绿联影视初始化"""
    print("=" * 50)
    print("测试绿联影视初始化")
    print("=" * 50)

    # 测试空配置初始化
    client = Ugreen(config=None)
    assert client._host is None, "空配置时 _host 应该为 None"
    print("✓ 空配置初始化测试通过")

    # 测试带配置初始化
    config = {
        'host': 'http://192.168.1.100',
        'username': 'admin',
        'password': 'admin123',
        'play_host': 'http://192.168.1.100:8080'
    }
    client = Ugreen(config=config)
    assert client._host == 'http://192.168.1.100/', f"_host 错误: {client._host}"
    assert client._username == 'admin', f"_username 错误: {client._username}"
    assert client._password == 'admin123', f"_password 错误: {client._password}"
    assert client._play_host == 'http://192.168.1.100:8080/', f"_play_host 错误: {client._play_host}"
    assert client._api_base == 'http://192.168.1.100/ugreen/v1/', f"_api_base 错误: {client._api_base}"

    print("✓ 带配置初始化测试通过")
    print(f"  - Host: {client._host}")
    print(f"  - API Base: {client._api_base}")
    print()

def test_ugreen_host_formatting():
    """测试 host 格式处理"""
    print("=" * 50)
    print("测试 host 格式处理")
    print("=" * 50)

    # 测试不带 http 前缀
    config = {'host': '192.168.1.100', 'username': 'admin', 'password': 'pass'}
    client = Ugreen(config=config)
    assert client._host == 'http://192.168.1.100/', f"应该自动添加 http:// 前缀: {client._host}"
    print("✓ 自动添加 http:// 前缀测试通过")

    # 测试带斜杠后缀
    config = {'host': 'http://192.168.1.100/', 'username': 'admin', 'password': 'pass'}
    client = Ugreen(config=config)
    assert client._host == 'http://192.168.1.100/', f"不应该重复添加斜杠: {client._host}"
    print("✓ 斜杠处理测试通过")

    # 测试 play_host 默认使用 host
    config = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    client = Ugreen(config=config)
    assert client._play_host == client._host, "play_host 应该默认等于 host"
    print("✓ play_host 默认值测试通过")

    print()

def test_ugreen_api_url():
    """测试 API URL 构建"""
    print("=" * 50)
    print("测试 API URL 构建")
    print("=" * 50)

    config = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    client = Ugreen(config=config)

    # 模拟设置 token
    client._token = "test_token_123"

    # 测试 API URL 构建
    api_url = client._Ugreen__get_api_url("media/library/stats")
    expected = "http://192.168.1.100/ugreen/v1/media/library/stats?token=test_token_123"
    assert api_url == expected, f"API URL 错误: {api_url}"

    print(f"✓ API URL 构建测试通过")
    print(f"  - URL: {api_url}")

    # 测试带问号的 endpoint
    api_url = client._Ugreen__get_api_url("media/search?keyword=test")
    expected = "http://192.168.1.100/ugreen/v1/media/search?keyword=test&token=test_token_123"
    assert api_url == expected, f"API URL 错误: {api_url}"

    print("✓ 带参数 endpoint 测试通过")
    print()

def test_ugreen_get_type():
    """测试 get_type 方法"""
    print("=" * 50)
    print("测试 get_type 方法")
    print("=" * 50)

    client = Ugreen(config=None)
    assert client.get_type() == MediaServerType.UGREEN, "get_type 应该返回 MediaServerType.UGREEN"

    print("✓ get_type 测试通过")
    print()

def test_ugreen_get_user_count():
    """测试 get_user_count 方法"""
    print("=" * 50)
    print("测试 get_user_count 方法")
    print("=" * 50)

    # 无 token 时返回 0
    client = Ugreen(config=None)
    assert client.get_user_count() == 0, "无 token 时应该返回 0"
    print("✓ 无 token 时返回 0 测试通过")

    # 有 token 时返回 1
    config = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    client = Ugreen(config=config)
    client._token = "test_token"
    assert client.get_user_count() == 1, "有 token 时应该返回 1"
    print("✓ 有 token 时返回 1 测试通过")

    print()

def test_ugreen_get_play_url():
    """测试 get_play_url 方法"""
    print("=" * 50)
    print("测试 get_play_url 方法")
    print("=" * 50)

    config = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    client = Ugreen(config=config)

    play_url = client.get_play_url("item_123")
    expected = "http://192.168.1.100/#/player/item_123"
    assert play_url == expected, f"播放 URL 错误: {play_url}"

    print(f"✓ 播放 URL 测试通过")
    print(f"  - URL: {play_url}")
    print()

def test_ugreen_unsupported_methods():
    """测试不支持的方法"""
    print("=" * 50)
    print("测试不支持的方法")
    print("=" * 50)

    client = Ugreen(config=None)

    # 这些功能在绿联影视中暂不支持
    assert client.get_activity_log(10) == [], "get_activity_log 应该返回空列表"
    print("✓ get_activity_log 返回空列表")

    assert client.get_playing_sessions() == [], "get_playing_sessions 应该返回空列表"
    print("✓ get_playing_sessions 返回空列表")

    assert client.get_webhook_message("test") == {}, "get_webhook_message 应该返回空字典"
    print("✓ get_webhook_message 返回空字典")

    assert client.get_resume() == [], "get_resume 应该返回空列表"
    print("✓ get_resume 返回空列表")

    assert client.get_remote_image_by_id("item_123", "poster") is None, "get_remote_image_by_id 应该返回 None"
    print("✓ get_remote_image_by_id 返回 None")

    print()

def test_ugreen_match():
    """测试 match 类方法"""
    print("=" * 50)
    print("测试 match 类方法")
    print("=" * 50)

    # 测试各种匹配情况
    assert Ugreen.match("ugreen") == True
    assert Ugreen.match(MediaServerType.UGREEN) == True
    assert Ugreen.match("绿联影视") == True
    assert Ugreen.match("emby") == False
    assert Ugreen.match("jellyfin") == False
    assert Ugreen.match("plex") == False
    assert Ugreen.match("unknown") == False

    print("✓ match 方法各种情况测试通过")
    print()

def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("绿联影视模块测试开始")
    print("=" * 50 + "\n")

    try:
        test_ugreen_basic()
        test_ugreen_init()
        test_ugreen_host_formatting()
        test_ugreen_api_url()
        test_ugreen_get_type()
        test_ugreen_get_user_count()
        test_ugreen_get_play_url()
        test_ugreen_unsupported_methods()
        test_ugreen_match()

        print("=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
        return True
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
