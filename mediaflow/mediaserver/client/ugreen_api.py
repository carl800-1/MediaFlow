"""
绿联影视 API 客户端（统一加密通道）。

说明：
1. 所有业务接口调用都应走 request()；
2. request() 会自动将明文查询参数加密为 encrypt_query；
3. 若响应包含 encrypt_resp_body，会自动完成解密后再返回。

参考 moviepilot 的 Api 实现，适配 mediaflow/nastool 架构。
"""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Union
from urllib.parse import urlsplit, urlunsplit

import log
from app.utils import ExceptionUtils
from app.mediaserver.client.ugreen_crypto import UgreenCrypto

# 使用 requests.Session 直接发送请求，以支持 SSL 验证控制
import requests as req_lib


@dataclass
class ApiResult:
    """绿联 API 响应结果"""
    code: int = -1
    msg: str = ""
    data: Any = None
    debug: Optional[str] = None
    raw: Optional[dict] = None

    @property
    def success(self) -> bool:
        return self.code == 200


class UgreenApi:
    """
    绿联影视 API 客户端。

    使用方式：
    1. 创建实例：api = UgreenApi(host="https://192.168.1.100:8080")
    2. 登录：api.login(username, password)
    3. 调用业务接口：api.media_list(), api.search(keyword) 等
    """

    def __init__(
        self,
        host: str,
        client_version: str = "76363",
        language: str = "zh-CN",
        ug_agent: str = "PC/WEB",
        timeout: int = 20,
        verify_ssl: bool = True,
    ):
        self._host = self._normalize_base_url(host)
        self._session = req_lib.Session()
        self._token: Optional[str] = None
        self._static_token: Optional[str] = None
        self._is_ugk: bool = False
        self._public_key: Optional[str] = None
        self._crypto: Optional[UgreenCrypto] = None
        self._username: Optional[str] = None
        self._client_id = f"{uuid.uuid4()}-WEB"
        self._client_version = client_version
        self._language = language
        self._ug_agent = ug_agent
        self._timeout = timeout
        self._verify_ssl = bool(verify_ssl)

    @property
    def host(self) -> str:
        return self._host

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def static_token(self) -> Optional[str]:
        return self._static_token

    @property
    def is_ugk(self) -> bool:
        return self._is_ugk

    @property
    def public_key(self) -> Optional[str]:
        return self._public_key

    def close(self):
        """关闭客户端"""
        try:
            self._session.close()
        except Exception:
            pass
        self._token = None
        self._static_token = None
        self._crypto = None

    @staticmethod
    def _normalize_base_url(host: str) -> str:
        """标准化基础 URL"""
        if not host:
            return ""
        host = host.strip().rstrip("/")
        if not host.startswith("http"):
            host = "https://" + host
        parsed = urlsplit(host)
        return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")

    @staticmethod
    def _decode_public_key(raw: Optional[str]) -> Optional[str]:
        """解码 RSA 公钥（可能是 base64 编码的 PEM 格式）"""
        if not raw:
            return None
        value = str(raw).strip()
        if not value:
            return None
        if "BEGIN" in value:
            return value
        try:
            return base64.b64decode(value).decode("utf-8")
        except Exception:
            return value

    @staticmethod
    def _extract_rsa_token(resp_json: dict, headers: Mapping[str, str]) -> Optional[str]:
        """从登录检查响应中提取 RSA 公钥 token"""
        token = headers.get("x-rsa-token") or headers.get("X-Rsa-Token")
        if token:
            return token
        token = resp_json.get("xRsaToken") or resp_json.get("x-rsa-token")
        if token:
            return token
        data = resp_json.get("data") if isinstance(resp_json, Mapping) else None
        if isinstance(data, Mapping):
            return data.get("xRsaToken") or data.get("x-rsa-token")
        return None

    def _common_headers(self) -> dict:
        """获取绿联 Web 端通用请求头"""
        return {
            "Accept": "application/json, text/plain, */*",
            "Client-Id": self._client_id,
            "Client-Version": self._client_version,
            "UG-Agent": self._ug_agent,
            "X-Specify-Language": self._language,
        }

    def _request_json(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        发送 HTTP 请求并尝试解析为 JSON。
        使用 requests.Session 直接发送，以支持 SSL 验证控制。
        """
        try:
            method = method.upper()
            resp = self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=self._timeout,
                verify=self._verify_ssl,
            )
            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception:
                    return None
            return None
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            log.error(f"【绿联影视】请求接口失败：{url} {str(err)}")
            return None

    @staticmethod
    def _build_result(payload: Any) -> ApiResult:
        """构建 API 结果对象"""
        if not isinstance(payload, Mapping):
            return ApiResult(code=-1, msg="响应格式错误", raw=None)
        code = payload.get("code")
        try:
            code = int(code)
        except Exception:
            code = -1
        return ApiResult(
            code=code,
            msg=str(payload.get("msg") or ""),
            data=payload.get("data"),
            debug=payload.get("debug"),
            raw=dict(payload) if isinstance(payload, dict) else None,
        )

    def login(self, username: str, password: str, keepalive: bool = True) -> Optional[str]:
        """
        登录绿联账号并初始化加密上下文。

        登录流程：
        1. POST /ugreen/v1/verify/check -> 获取 RSA 公钥
        2. RSA 分段加密密码
        3. POST /ugreen/v1/verify/login -> 获取 token 和 API 公钥
        4. 初始化 UgreenCrypto 实例

        :param username: 用户名
        :param password: 密码
        :param keepalive: 是否保持登录
        :return: 登录成功返回 token
        """
        if not username or not password:
            return None

        headers = self._common_headers()

        # 第一步：获取登录 RSA 公钥
        try:
            check_resp = self._session.post(
                f"{self._host}/ugreen/v1/verify/check",
                headers=headers,
                json={"username": username},
                timeout=self._timeout,
                verify=self._verify_ssl,
            )

            if not check_resp:
                log.error("【绿联影视】获取登录公钥失败：无响应")
                return None

            try:
                check_json = check_resp.json()
            except Exception:
                log.error("【绿联影视】获取登录公钥失败：响应非 JSON")
                return None
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            log.error(f"【绿联影视】获取登录公钥失败：{str(err)}")
            return None

        check_result = self._build_result(check_json)
        if not check_result.success:
            log.error(f"【绿联影视】获取登录公钥失败：{check_result.msg}")
            return None

        rsa_token = self._extract_rsa_token(check_json, check_resp.headers)
        login_public_key = self._decode_public_key(rsa_token)
        if not login_public_key:
            log.error("【绿联影视】获取登录公钥失败：公钥为空")
            return None

        # 第二步：RSA 加密密码并登录
        crypto_for_login = UgreenCrypto(public_key=login_public_key)
        encrypted_password = crypto_for_login.rsa_encrypt_long(password)

        login_json = self._request_json(
            url=f"{self._host}/ugreen/v1/verify/login",
            method="POST",
            headers=headers,
            json_data={
                "username": username,
                "password": encrypted_password,
                "keepalive": keepalive,
                "otp": True,
                "is_simple": True,
            },
        )
        if not login_json:
            return None

        login_result = self._build_result(login_json)
        if not login_result.success or not isinstance(login_result.data, Mapping):
            log.error(f"【绿联影视】登录失败：{login_result.msg}")
            return None

        token = str(login_result.data.get("token") or "").strip()
        public_key = self._decode_public_key(str(login_result.data.get("public_key") or ""))
        if not token or not public_key:
            log.error("【绿联影视】登录失败：未返回 token/public_key")
            return None

        # 第三步：初始化加密上下文
        self._token = token
        static_token = str(login_result.data.get("static_token") or "").strip()
        self._static_token = static_token or self._token
        self._is_ugk = bool(login_result.data.get("is_ugk"))
        self._public_key = public_key
        self._crypto = UgreenCrypto(
            public_key=self._public_key,
            token=self._token,
            client_id=self._client_id,
            client_version=self._client_version,
            ug_agent=self._ug_agent,
            language=self._language,
        )
        self._username = username
        log.info(f"【绿联影视】用户 {username} 登录成功")
        return self._token

    def logout(self):
        """登出并清理本地认证状态"""
        if not self._token or not self._crypto:
            return
        try:
            req = self._crypto.build_encrypted_request(
                url=f"{self._host}/ugreen/v1/verify/logout",
                method="GET",
                params={},
            )
            self._request_json(
                url=req.url,
                method="GET",
                headers=req.headers,
                params=req.params,
            )
        except Exception:
            pass
        self._token = None
        self._static_token = None
        self._is_ugk = False
        self._public_key = None
        self._crypto = None
        self._username = None

    def export_session_state(self) -> Optional[dict]:
        """导出当前登录会话，供持久化存储使用"""
        if not self._token or not self._public_key:
            return None
        return {
            "token": self._token,
            "static_token": self._static_token,
            "is_ugk": self._is_ugk,
            "public_key": self._public_key,
            "username": self._username,
            "client_id": self._client_id,
            "client_version": self._client_version,
            "language": self._language,
            "ug_agent": self._ug_agent,
        }

    def import_session_state(self, state: Mapping[str, Any]) -> bool:
        """从持久化数据恢复登录会话"""
        if not isinstance(state, Mapping):
            return False

        token = str(state.get("token") or "").strip()
        public_key = self._decode_public_key(str(state.get("public_key") or ""))
        if not token or not public_key:
            return False

        self._static_token = str(state.get("static_token") or "").strip()
        self._is_ugk = bool(state.get("is_ugk"))

        client_id = str(state.get("client_id") or "").strip()
        if client_id:
            self._client_id = client_id

        client_version = str(state.get("client_version") or "").strip()
        if client_version:
            self._client_version = client_version

        language = str(state.get("language") or "").strip()
        if language:
            self._language = language

        ug_agent = str(state.get("ug_agent") or "").strip()
        if ug_agent:
            self._ug_agent = ug_agent

        self._username = str(state.get("username") or "").strip() or None

        self._token = token
        self._public_key = public_key
        self._crypto = UgreenCrypto(
            public_key=self._public_key,
            token=self._token,
            client_id=self._client_id,
            client_version=self._client_version,
            ug_agent=self._ug_agent,
            language=self._language,
        )
        return True

    def request(
        self,
        path: str,
        method: str = "GET",
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> ApiResult:
        """
        统一请求入口（加密通道）。

        核心行为：
        1. 自动把 params 明文序列化并加密为 encrypt_query
        2. 自动注入绿联安全头（X-Ugreen-*）
        3. 对 POST/PUT/PATCH 的 JSON 体加密
        4. 自动解密 encrypt_resp_body

        :param path: /ugreen/ 后的相对路径，例如 v1/video/homepage/media_list
        :param method: HTTP 方法
        :param params: 明文查询参数（无需自己处理 encrypt_query）
        :param data: 明文 JSON 请求体（自动加密）
        """
        if not self._crypto:
            return ApiResult(code=-1, msg="未登录")

        api_path = path.strip("/")
        req = self._crypto.build_encrypted_request(
            url=f"{self._host}/ugreen/{api_path}",
            method=method.upper(),
            params=params or {},
            data=data,
            encrypt_body=method.upper() in {"POST", "PUT", "PATCH"},
        )

        payload = self._request_json(
            url=req.url,
            method=method,
            headers=req.headers,
            params=req.params,
            json_data=req.json,
        )
        if payload is None:
            return ApiResult(code=-1, msg="接口请求失败")

        # 响应若包含 encrypt_resp_body，自动解密
        decrypted = self._crypto.decrypt_response(payload, req.aes_key)
        return self._build_result(decrypted)

    # ==================== 业务 API ====================

    def current_user(self) -> Optional[dict]:
        """获取当前登录用户信息"""
        result = self.request("v1/user/current/user")
        if not result.success or not isinstance(result.data, Mapping):
            return None
        return dict(result.data)

    def media_list(self) -> list:
        """获取首页媒体库列表（media_lib_info_list）"""
        result = self.request("v1/video/homepage/media_list")
        if not result.success or not isinstance(result.data, Mapping):
            return []
        items = result.data.get("media_lib_info_list")
        return items if isinstance(items, list) else []

    def media_lib_users(self) -> list:
        """获取媒体库用户列表"""
        result = self.request("v1/video/media_lib/get_user_list")
        if not result.success or not isinstance(result.data, Mapping):
            return []
        users = result.data.get("user_info_arr")
        return users if isinstance(users, list) else []

    def recently_played(self, page: int = 1, page_size: int = 12) -> Optional[dict]:
        """获取继续观看列表"""
        result = self.request(
            "v1/video/recently_played/get",
            params={
                "page": page,
                "page_size": page_size,
                "language": self._language,
                "create_time_order": "false",
            },
        )
        return result.data if result.success and isinstance(result.data, Mapping) else None

    def recently_updated(self, page: int = 1, page_size: int = 20) -> Optional[dict]:
        """获取最近更新列表"""
        result = self.request(
            "v1/video/recently_update/get",
            params={
                "page": page,
                "page_size": page_size,
                "language": self._language,
                "create_time_order": "false",
            },
        )
        return result.data if result.success and isinstance(result.data, Mapping) else None

    def recently_played_info(self, item_id: Union[str, int]) -> Optional[dict]:
        """获取单个视频的播放状态与基础详情信息"""
        result = self.request(
            "v1/video/recently_played/info",
            params={
                "ug_video_info_id": item_id,
                "version_control": "true",
            },
        )
        if result.code in {200, 1303} and isinstance(result.data, Mapping):
            return dict(result.data)
        return None

    def search(self, keyword: str, offset: int = 0, limit: int = 200) -> Optional[dict]:
        """搜索媒体（电影/剧集）"""
        result = self.request(
            "v1/video/search",
            params={
                "language": self._language,
                "search_type": 1,
                "offset": offset,
                "limit": limit,
                "keyword": keyword,
            },
        )
        return result.data if result.success and isinstance(result.data, Mapping) else None

    def video_all(self, classification: int, page: int = 1, page_size: int = 20) -> Optional[dict]:
        """
        获取分类列表。

        常用分类：
        -102: 电影
        -103: 电视剧
        """
        result = self.request(
            "v1/video/all",
            params={
                "page": page,
                "pageSize": page_size,
                "classification": classification,
                "sort_type": 2,
                "order_type": 2,
                "release_date_begin": -9999999999,
                "release_date_end": -9999999999,
                "identify_status": 0,
                "watch_status": -1,
                "ug_style_id": 0,
                "ug_country_id": 0,
                "clarity": -1,
            },
        )
        return result.data if result.success and isinstance(result.data, Mapping) else None

    def poster_wall_get_folder(
        self,
        path: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_type: int = 1,
        order_type: int = 1,
    ) -> Optional[dict]:
        """获取海报墙文件夹与条目（可按目录路径递归展开）"""
        params: Dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "sort_type": sort_type,
            "order_type": order_type,
        }
        if path:
            params["path"] = path
        result = self.request("v1/video/poster_wall/media_lib/get_folder", params=params)
        return result.data if result.success and isinstance(result.data, Mapping) else None

    def get_movie(
        self,
        item_id: Union[str, int],
        media_lib_set_id: Union[str, int],
        path: Optional[str] = None,
        folder_path: Optional[str] = None,
    ) -> Optional[dict]:
        """获取电影详情"""
        params: Dict[str, Any] = {
            "id": item_id,
            "media_lib_set_id": media_lib_set_id,
            "fileVersion": "true",
        }
        if path:
            params["path"] = path
        if folder_path:
            params["folder_path"] = folder_path
        result = self.request("v1/video/details/getMovie", params=params)
        return result.data if result.success and isinstance(result.data, Mapping) else None

    def get_tv(self, item_id: Union[str, int], folder_path: str = "ALL") -> Optional[dict]:
        """获取剧集详情（含季/集信息）"""
        result = self.request(
            "v2/video/details/getTV",
            params={
                "ug_video_info_id": item_id,
                "folder_path": folder_path,
            },
        )
        return result.data if result.success and isinstance(result.data, Mapping) else None

    def scan(self, media_lib_set_id: Union[str, int], scan_type: int = 2, op_type: int = 2) -> bool:
        """
        触发媒体库扫描。

        :param media_lib_set_id: 媒体库 ID
        :param scan_type: 扫描类型（1: 新添加和修改, 2: 补充缺失, 3: 覆盖扫描）
        :param op_type: 操作类型（网页端常用 2）
        """
        result = self.request(
            "v1/video/media_lib/scan",
            params={
                "op_type": op_type,
                "media_lib_set_id": media_lib_set_id,
                "media_lib_scan_type": scan_type,
            },
        )
        return result.success

    def scan_status(self, only_brief: bool = True) -> list:
        """获取媒体库扫描状态"""
        result = self.request(
            "v1/video/media_lib/scan/status",
            params={"only_brief": "true" if only_brief else "false"},
        )
        if not result.success or not isinstance(result.data, Mapping):
            return []
        arr = result.data.get("media_lib_scan_status_arr")
        return arr if isinstance(arr, list) else []

    def media_lib_get_all(self, req_type: int = 2) -> Optional[Any]:
        """获取全部媒体库集合"""
        result = self.request(
            "v1/video/media_lib/get_all",
            params={
                "mediaLib_get_all_req_type": req_type,
                "language": self._language,
            },
        )
        return result.data if result.success else None
