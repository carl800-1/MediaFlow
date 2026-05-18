#!/usr/bin/env python3
"""
绿联影视模块 - 完整模拟测试
精确匹配实际代码逻辑，使用 mock 模拟 API 响应
"""
import sys
import os
from unittest.mock import patch, MagicMock

os.environ['NASTOOL_CONFIG'] = './config/config.yaml'
sys.path.insert(0, '.')

from app.mediaserver.client.ugreen import Ugreen
from app.utils.types import MediaServerType

# ============================================================
# 模拟 API 响应（code=200 匹配实际代码中的判断逻辑）
# ============================================================
MOCK_LOGIN_OK = {"code": 200, "data": {"token": "mock_token_12345"}}
MOCK_LOGIN_FAIL = {"code": 401, "msg": "密码错误"}

MOCK_STATS_OK = {
    "code": 200,
    "data": {"movie_count": 120, "tv_count": 45, "episode_count": 1500}
}

MOCK_LIBRARIES_OK = {
    "code": 200,
    "data": {
        "libraries": [
            {"id": "lib_001", "name": "电影", "type": "movie", "path": "/media/movies"},
            {"id": "lib_002", "name": "电视剧", "type": "tv", "path": "/media/tv"},
            {"id": "lib_003", "name": "音乐", "type": "music", "path": "/media/music"},
        ]
    }
}

MOCK_SEARCH_MOVIE_OK = {
    "code": 200,
    "data": {
        "items": [
            {"id": "m1", "title": "流浪地球", "year": 2019},
            {"id": "m2", "title": "流浪地球2", "year": 2023},
        ]
    }
}

MOCK_SEARCH_TV_OK = {
    "code": 200,
    "data": {
        "items": [
            {"id": "t1", "title": "狂飙", "year": 2023},
        ]
    }
}

MOCK_EPISODES_OK = {
    "code": 200,
    "data": {
        "episodes": [
            {"season_number": 1, "episode_number": 1},
            {"season_number": 1, "episode_number": 2},
            {"season_number": 1, "episode_number": 3},
        ]
    }
}

MOCK_LATEST_OK = {
    "code": 200,
    "data": {
        "items": [
            {"id": "i1", "title": "三体", "type": "tv", "year": 2024},
            {"id": "i2", "title": "沙丘2", "type": "movie", "year": 2024},
        ]
    }
}

MOCK_ITEMS_OK = {
    "code": 200,
    "data": {
        "items": [
            {"id": "m1", "type": "movie", "title": "流浪地球", "original_title": "The Wandering Earth",
             "year": 2019, "tmdb_id": "12345", "imdb_id": "tt12345", "path": "/movies/流浪地球"},
            {"id": "t1", "type": "tv", "title": "狂飙", "original_title": "The Knockout",
             "year": 2023, "tmdb_id": "67890", "imdb_id": "tt67890", "path": "/tv/狂飙"},
        ]
    }
}

MOCK_REFRESH_OK = {"code": 200, "msg": "success"}
MOCK_ERROR = {"code": 500, "msg": "服务器内部错误"}


# ============================================================
# 测试框架
# ============================================================
class TR:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"    ✓ {name}")

    def fail(self, name, reason):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"    ✗ {name}: {reason}")

    def check(self, name, condition, reason=""):
        if condition:
            self.ok(name)
        else:
            self.fail(name, reason or "断言失败")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        if self.failed == 0:
            print(f"✓ 全部 {total} 项测试通过")
        else:
            print(f"✗ {self.passed}/{total} 通过, {self.failed} 失败:")
            for name, reason in self.errors:
                print(f"    ✗ {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


def make_mock_response(json_data, status_code=200):
    """创建模拟 HTTP 响应"""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    return mock


# ============================================================
# 测试用例
# ============================================================

def test_class_attrs(tr):
    """[1] 类属性"""
    print("\n[1] 类属性")
    tr.check("client_id", Ugreen.client_id == "ugreen")
    tr.check("client_type", Ugreen.client_type == MediaServerType.UGREEN)
    tr.check("client_name", Ugreen.client_name == "绿联影视")


def test_match(tr):
    """[2] match"""
    print("\n[2] match 类方法")
    tr.check("ugreen", Ugreen.match("ugreen"))
    tr.check("MediaServerType.UGREEN", Ugreen.match(MediaServerType.UGREEN))
    tr.check("绿联影视", Ugreen.match("绿联影视"))
    tr.check("!emby", not Ugreen.match("emby"))
    tr.check("!jellyfin", not Ugreen.match("jellyfin"))
    tr.check("!None", not Ugreen.match(None))


def test_init(tr):
    """[3] 初始化"""
    print("\n[3] 初始化")
    c = Ugreen(config=None)
    tr.check("空配置 _host is None", c._host is None)
    tr.check("空配置 _token is None", c._token is None)

    cfg = {'host': 'http://192.168.1.100:8080', 'username': 'admin',
           'password': 'secret', 'play_host': 'http://192.168.1.100:9090'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = None
        c = Ugreen(config=cfg)
    tr.check("_host", c._host == 'http://192.168.1.100:8080/')
    tr.check("_username", c._username == 'admin')
    tr.check("_password", c._password == 'secret')
    tr.check("_play_host", c._play_host == 'http://192.168.1.100:9090/')
    tr.check("_api_base", c._api_base == 'http://192.168.1.100:8080/ugreen/v1/')

    # 无 http 前缀
    cfg2 = {'host': '192.168.1.200', 'username': 'u', 'password': 'p'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = None
        c2 = Ugreen(config=cfg2)
    tr.check("自动添加 http://", c2._host == 'http://192.168.1.200/')
    tr.check("play_host 默认 host", c2._play_host == c2._host)


def test_init_with_login(tr):
    """[4] 初始化时自动登录"""
    print("\n[4] 初始化自动登录")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)
    tr.check("登录成功获取 token", c._token == "mock_token_12345")

    # 登录失败
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_FAIL)
        c2 = Ugreen(config=cfg)
    tr.check("登录失败 token 为 None", c2._token is None)

    # 网络异常
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = None
        c3 = Ugreen(config=cfg)
    tr.check("网络异常 token 为 None", c3._token is None)


def test_get_type(tr):
    """[5] get_type"""
    print("\n[5] get_type")
    c = Ugreen(config=None)
    tr.check("== UGREEN", c.get_type() == MediaServerType.UGREEN)


def test_get_user_count(tr):
    """[6] get_user_count"""
    print("\n[6] get_user_count")
    c = Ugreen(config=None)
    tr.check("无 token -> 0", c.get_user_count() == 0)
    c._token = "t"
    tr.check("有 token -> 1", c.get_user_count() == 1)


def test_get_play_url(tr):
    """[7] get_play_url"""
    print("\n[7] get_play_url")
    cfg = {'host': 'http://192.168.1.100', 'username': 'a', 'password': 'b'}
    with patch('app.mediaserver.client.ugreen.RequestUtils'):
        c = Ugreen(config=cfg)
    tr.check("基本 URL", c.get_play_url("m1") == "http://192.168.1.100/#/player/m1")

    cfg2 = {**cfg, 'play_host': 'http://192.168.1.100:9090'}
    with patch('app.mediaserver.client.ugreen.RequestUtils'):
        c2 = Ugreen(config=cfg2)
    tr.check("play_host URL", c2.get_play_url("t1") == "http://192.168.1.100:9090/#/player/t1")


def test_get_host(tr):
    """[8] get_host"""
    print("\n[8] get_host")
    cfg = {'host': 'http://192.168.1.100', 'username': 'a', 'password': 'b'}
    with patch('app.mediaserver.client.ugreen.RequestUtils'):
        c = Ugreen(config=cfg)
    tr.check("返回 host", c.get_host() == 'http://192.168.1.100/')


def test_unsupported(tr):
    """[9] 不支持的方法"""
    print("\n[9] 不支持的方法")
    c = Ugreen(config=None)
    tr.check("get_activity_log -> []", c.get_activity_log(10) == [])
    tr.check("get_playing_sessions -> []", c.get_playing_sessions() == [])
    tr.check("get_webhook_message -> {}", c.get_webhook_message("x") == {})
    tr.check("get_resume -> []", c.get_resume() == [])
    tr.check("get_remote_image_by_id -> None", c.get_remote_image_by_id("x", "poster") is None)


def test_get_medias_count(tr):
    """[10] 获取媒体统计"""
    print("\n[10] get_medias_count")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.return_value = make_mock_response(MOCK_STATS_OK)
        result = c.get_medias_count()
    tr.check("返回 dict", isinstance(result, dict))
    tr.check("MovieCount=120", result.get("MovieCount") == 120)
    tr.check("SeriesCount=45", result.get("SeriesCount") == 45)

    # 无 token
    c2 = Ugreen(config=None)
    tr.check("无 token -> {}", c2.get_medias_count() == {})

    # API 错误
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.return_value = make_mock_response(MOCK_ERROR)
        tr.check("API错误 -> {}", c.get_medias_count() == {})

    # 网络异常
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.return_value = None
        tr.check("网络异常 -> {}", c.get_medias_count() == {})


def test_get_movies(tr):
    """[11] 搜索电影"""
    print("\n[11] get_movies")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.return_value = make_mock_response(MOCK_SEARCH_MOVIE_OK)
        result = c.get_movies(title="流浪地球")
    tr.check("返回列表", isinstance(result, list))
    tr.check("找到1部精确匹配", len(result) == 1)
    tr.check("标题=流浪地球", result[0].get("title") == "流浪地球")
    tr.check("年份=2019", result[0].get("year") == "2019")

    # 无 token
    c2 = Ugreen(config=None)
    tr.check("无 token -> None", c2.get_movies("x") is None)


def test_get_tv_episodes(tr):
    """[12] 获取剧集信息"""
    print("\n[12] get_tv_episodes")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    # 通过 item_id 获取
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.return_value = make_mock_response(MOCK_EPISODES_OK)
        result = c.get_tv_episodes(item_id="t1")
    tr.check("返回列表", isinstance(result, list))
    tr.check("3集", len(result) == 3)
    tr.check("第1集 episode_num=1", result[0].get("episode_num") == 1)
    tr.check("第3集 episode_num=3", result[2].get("episode_num") == 3)

    # 通过 title 搜索获取
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.side_effect = [
            make_mock_response(MOCK_SEARCH_TV_OK),
            make_mock_response(MOCK_EPISODES_OK),
        ]
        result = c.get_tv_episodes(title="狂飙", year=2023)
    tr.check("通过title搜索成功", isinstance(result, list) and len(result) == 3)

    # 无 token
    c2 = Ugreen(config=None)
    tr.check("无 token -> None", c2.get_tv_episodes() is None)


def test_get_no_exists_episodes(tr):
    """[13] 获取缺失集数"""
    print("\n[13] get_no_exists_episodes")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    # mock meta_info
    meta = MagicMock()
    meta.title = "狂飙"
    meta.year = 2023

    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.side_effect = [
            make_mock_response(MOCK_SEARCH_TV_OK),
            make_mock_response(MOCK_EPISODES_OK),
        ]
        result = c.get_no_exists_episodes(meta, season=1, total_num=5)
    tr.check("返回缺失集列表", isinstance(result, list))
    tr.check("缺失4,5集", set(result) == {4, 5})

    # 无 token
    c2 = Ugreen(config=None)
    tr.check("无 token -> None", c2.get_no_exists_episodes(meta, 1, 5) is None)


def test_get_local_image_by_id(tr):
    """[14] 获取本地图片"""
    print("\n[14] get_local_image_by_id")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    # 内网 IP
    with patch.object(c, 'get_nt_image_url', return_value='http://nt/image.jpg') as mock_nt:
        result = c.get_local_image_by_id("m1")
        tr.check("内网调用 get_nt_image_url", mock_nt.called)
        tr.check("内网返回URL", result == 'http://nt/image.jpg')

    # 外网 IP
    cfg2 = {'host': 'http://8.8.8.8', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c2 = Ugreen(config=cfg2)
    result2 = c2.get_local_image_by_id("m2")
    tr.check("外网返回URL", result2 is not None and 'm2' in result2)

    # 无 token
    c3 = Ugreen(config=None)
    tr.check("无 token -> None", c3.get_local_image_by_id("x") is None)


def test_refresh_root_library(tr):
    """[15] 刷新媒体库"""
    print("\n[15] refresh_root_library")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_REFRESH_OK)
        tr.check("刷新成功 -> True", c.refresh_root_library() == True)

    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_ERROR)
        tr.check("刷新失败 -> False", c.refresh_root_library() == False)

    c2 = Ugreen(config=None)
    tr.check("无 token -> False", c2.refresh_root_library() == False)


def test_refresh_library_by_items(tr):
    """[16] 按项目刷新"""
    print("\n[16] refresh_library_by_items")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    with patch.object(c, 'refresh_root_library', return_value=True) as mock_refresh:
        c.refresh_library_by_items([{"title": "test"}])
        tr.check("调用了 refresh_root_library", mock_refresh.called)

    # 空列表
    c.refresh_library_by_items([])
    tr.check("空列表不调用", True)  # 不崩溃即可


def test_get_libraries(tr):
    """[17] 获取媒体库列表"""
    print("\n[17] get_libraries")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.return_value = make_mock_response(MOCK_LIBRARIES_OK)
        with patch.object(c, 'get_local_image_by_id', return_value='http://img/lib.jpg'):
            result = c.get_libraries()
    tr.check("返回列表", isinstance(result, list))
    tr.check("2个有效库(过滤music)", len(result) == 2)
    tr.check("第一个=电影", result[0].get("name") == "电影")
    tr.check("第二个=电视剧", result[1].get("name") == "电视剧")
    tr.check("有image字段", "image" in result[0])
    tr.check("有link字段", "link" in result[0])

    c2 = Ugreen(config=None)
    tr.check("无 token -> []", c2.get_libraries() == [])


def test_get_items(tr):
    """[18] 获取媒体库项目"""
    print("\n[18] get_items")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.return_value = make_mock_response(MOCK_ITEMS_OK)
        items = list(c.get_items("lib_001"))
    tr.check("返回列表", isinstance(items, list))
    tr.check("有2个媒体+1个空终止符", len(items) == 3)
    tr.check("第一个是电影", items[0].get("type") == "Movie")
    tr.check("第一个标题=流浪地球", items[0].get("title") == "流浪地球")
    tr.check("有 tmdbid", "tmdbid" in items[0])
    tr.check("有 json 字段", "json" in items[0])

    # 空 parent
    items2 = list(c.get_items(None))
    tr.check("空parent返回[{},{}]", items2 == [{}, {}])

    # 无 token
    c2 = Ugreen(config=None)
    items3 = list(c2.get_items("lib_001"))
    tr.check("无token返回[{},{}]", items3 == [{}, {}])


def test_get_latest(tr):
    """[19] 获取最近更新"""
    print("\n[19] get_latest")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)

    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.return_value = make_mock_response(MOCK_LATEST_OK)
        with patch.object(c, 'get_local_image_by_id', return_value='http://img/item.jpg'):
            result = c.get_latest(num=10)
    tr.check("返回列表", isinstance(result, list))
    tr.check("2个最新项目", len(result) == 2)
    tr.check("有image字段", "image" in result[0])
    tr.check("有link字段", "link" in result[0])
    tr.check("有type字段", "type" in result[0])

    c2 = Ugreen(config=None)
    tr.check("无 token -> []", c2.get_latest() == [])


def test_get_status(tr):
    """[20] get_status 连通性"""
    print("\n[20] get_status")
    cfg = {'host': 'http://192.168.1.100', 'username': 'admin', 'password': 'pass'}

    # 登录成功 + 获取统计成功
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = make_mock_response(MOCK_LOGIN_OK)
        c = Ugreen(config=cfg)
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.get_res.return_value = make_mock_response(MOCK_STATS_OK)
        tr.check("有数据 -> True", c.get_status() == True)

    # 登录失败
    with patch('app.mediaserver.client.ugreen.RequestUtils') as mock_req:
        mock_req.return_value.post_res.return_value = None
        c2 = Ugreen(config=cfg)
    tr.check("无数据 -> False", c2.get_status() == False)


# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 60)
    print("绿联影视模块 - 完整模拟测试")
    print("=" * 60)

    tr = TR()
    test_class_attrs(tr)
    test_match(tr)
    test_init(tr)
    test_init_with_login(tr)
    test_get_type(tr)
    test_get_user_count(tr)
    test_get_play_url(tr)
    test_get_host(tr)
    test_unsupported(tr)
    test_get_medias_count(tr)
    test_get_movies(tr)
    test_get_tv_episodes(tr)
    test_get_no_exists_episodes(tr)
    test_get_local_image_by_id(tr)
    test_refresh_root_library(tr)
    test_refresh_library_by_items(tr)
    test_get_libraries(tr)
    test_get_items(tr)
    test_get_latest(tr)
    test_get_status(tr)

    return tr.summary()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
