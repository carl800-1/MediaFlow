"""
绿联影视接口请求加解密工具。

绿联 NAS 的所有 API 通信都经过 RSA + AES-256-GCM 双层加密：
1. RSA 加密：用于加密密码、token、AES 密钥
2. AES-GCM 加密：用于加密查询参数和请求/响应体

参考 moviepilot 的 UgreenCrypto 实现，适配 mediaflow/nastool 架构。
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Optional, Union
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import log
from app.utils import ExceptionUtils


@dataclass
class UgreenEncryptedRequest:
    """绿联加密请求数据结构"""
    url: str
    headers: dict
    params: dict
    json: Optional[dict]
    aes_key: str
    plain_query: str


class UgreenCrypto:
    """
    绿联接口请求加解密工具。

    使用方式：
    1. 登录时获取 RSA 公钥
    2. 用公钥初始化 UgreenCrypto
    3. 调用 build_encrypted_request 构建加密请求
    4. 调用 decrypt_response 解密响应
    """

    def __init__(
        self,
        public_key: str,
        token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_version: Optional[str] = "76363",
        ug_agent: Optional[str] = "PC/WEB",
        language: str = "zh-CN",
    ) -> None:
        self.public_key_pem = self._normalize_public_key(public_key)
        self.public_key = self._load_rsa_public_key(self.public_key_pem)
        self.token = token
        self.client_id = client_id
        self.client_version = client_version
        self.ug_agent = ug_agent
        self.language = language

    @staticmethod
    def _normalize_public_key(public_key: str) -> str:
        """标准化 RSA 公钥格式"""
        key = (public_key or "").strip().strip('"').replace("\\n", "\n")
        if "BEGIN" in key:
            return key if key.endswith("\n") else f"{key}\n"
        return (
            "-----BEGIN RSA PUBLIC KEY-----\n"
            f"{key}\n"
            "-----END RSA PUBLIC KEY-----\n"
        )

    def _load_rsa_public_key(self, pem_key: str):
        """加载 RSA 公钥"""
        try:
            from cryptography.hazmat.primitives import serialization
            return serialization.load_pem_public_key(pem_key.encode("utf-8"))
        except ImportError:
            log.error("【绿联影视】缺少 cryptography 库，请安装：pip install cryptography")
            return None
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【绿联影视】加载 RSA 公钥失败：{str(e)}")
            return None

    @staticmethod
    def generate_aes_key() -> str:
        """生成随机 AES 密钥"""
        return uuid.uuid4().hex

    @staticmethod
    def _flatten_query(prefix: str, value: Any) -> list:
        """将嵌套参数扁平化为键值对列表"""
        pairs = []
        if isinstance(value, Mapping):
            for key, item in value.items():
                next_prefix = f"{prefix}[{key}]" if prefix else str(key)
                pairs.extend(UgreenCrypto._flatten_query(next_prefix, item))
            return pairs
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                next_prefix = f"{prefix}[]"
                pairs.extend(UgreenCrypto._flatten_query(next_prefix, item))
            return pairs
        if isinstance(value, bool):
            pairs.append((prefix, "true" if value else "false"))
            return pairs
        if value is None:
            pairs.append((prefix, ""))
            return pairs
        pairs.append((prefix, str(value)))
        return pairs

    @classmethod
    def encode_query(cls, params: Optional[Mapping[str, Any]]) -> str:
        """将参数字典编码为查询字符串"""
        if not params:
            return ""
        pairs = []
        for key, value in params.items():
            pairs.extend(cls._flatten_query(str(key), value))
        return urlencode(pairs, doseq=False, quote_via=quote, safe="")

    def rsa_encrypt_long(self, plaintext: str) -> str:
        """
        RSA 分段加密（PKCS1v15 填充）。

        当明文长度超过 RSA 密钥块大小时，自动分段加密后拼接。
        """
        if not plaintext or not self.public_key:
            return ""
        try:
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
            key_size = self.public_key.key_size // 8
            max_chunk = key_size - 11  # PKCS1v15 填充开销
            encrypted_chunks = []
            raw = plaintext.encode("utf-8")
            for start in range(0, len(raw), max_chunk):
                chunk = raw[start: start + max_chunk]
                encrypted_chunks.append(
                    self.public_key.encrypt(chunk, asym_padding.PKCS1v15())
                )
            return base64.b64encode(b"".join(encrypted_chunks)).decode("utf-8")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【绿联影视】RSA 加密失败：{str(e)}")
            return ""

    @staticmethod
    def aes_gcm_encrypt(plaintext: str, aes_key: str) -> str:
        """
        AES-256-GCM 加密。

        返回格式：base64(IV + ciphertext + tag)
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            iv = os.urandom(12)
            cipher = AESGCM(aes_key.encode("utf-8"))
            encrypted = cipher.encrypt(iv, plaintext.encode("utf-8"), None)
            return base64.b64encode(iv + encrypted).decode("utf-8")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【绿联影视】AES-GCM 加密失败：{str(e)}")
            return ""

    @staticmethod
    def aes_gcm_decrypt(payload_b64: str, aes_key: str) -> str:
        """
        AES-256-GCM 解密。

        输入格式：base64(IV + ciphertext + tag)
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            raw = base64.b64decode(payload_b64)
            iv = raw[:12]
            encrypted = raw[12:]
            cipher = AESGCM(aes_key.encode("utf-8"))
            plain = cipher.decrypt(iv, encrypted, None)
            return plain.decode("utf-8")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【绿联影视】AES-GCM 解密失败：{str(e)}")
            return ""

    @staticmethod
    def build_security_key(token: str) -> str:
        """构建安全密钥（MD5(token)）"""
        return hashlib.md5(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_body(data: Any) -> str:
        """标准化请求体为字符串"""
        if isinstance(data, str):
            return data
        if isinstance(data, (bytes, bytearray)):
            return bytes(data).decode("utf-8")
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    def encrypt_body(self, data: Any, aes_key: str) -> dict:
        """加密请求体"""
        plain = self._normalize_body(data)
        return {
            "encrypt_req_body": self.aes_gcm_encrypt(plain, aes_key),
            "req_body_sha256": hashlib.sha256(plain.encode("utf-8")).hexdigest(),
        }

    def build_headers(
        self,
        aes_key: str,
        token: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        encrypt_token: bool = True,
    ) -> dict:
        """
        构建绿联加密请求头。

        包含：
        - X-Ugreen-Security-Key: MD5(token)
        - X-Ugreen-Security-Code: RSA_Encrypt(AES_Key)
        - X-Ugreen-Token: RSA_Encrypt(token)
        - Client-Id: UUID-WEB
        - Client-Version: 76363
        - UG-Agent: PC/WEB
        - X-Specify-Language: zh-CN
        """
        token_value = token if token is not None else self.token
        headers = dict(extra_headers or {})

        if self.client_id:
            headers.setdefault("Client-Id", self.client_id)
        if self.client_version:
            headers.setdefault("Client-Version", self.client_version)
        if self.ug_agent:
            headers.setdefault("UG-Agent", self.ug_agent)
        headers.setdefault("X-Specify-Language", self.language)
        headers.setdefault("Accept", "application/json, text/plain, */*")

        if token_value:
            headers["X-Ugreen-Security-Key"] = self.build_security_key(token_value)
            headers["X-Ugreen-Security-Code"] = self.rsa_encrypt_long(aes_key)
            headers["X-Ugreen-Token"] = (
                self.rsa_encrypt_long(token_value) if encrypt_token else token_value
            )
        return headers

    def build_encrypted_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Any] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        token: Optional[str] = None,
        encrypt_token: bool = True,
        encrypt_body: bool = True,
    ) -> UgreenEncryptedRequest:
        """
        构建绿联加密请求。

        关键点：
        - 传入的是明文 params；
        - 方法内部会将其序列化并加密成 encrypt_query；
        - 业务侧不需要、也不应该手工拼接 encrypt_query。
        """
        parsed = urlsplit(url)
        clean_url = urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, "", parsed.fragment)
        )

        url_query_plain = parsed.query
        input_query_plain = self.encode_query(params)
        plain_query = "&".join(filter(None, [url_query_plain, input_query_plain]))

        aes_key = self.generate_aes_key()
        encrypted_query = self.aes_gcm_encrypt(plain_query, aes_key)

        req_json = None
        if data is not None:
            req_json = self.encrypt_body(data, aes_key) if encrypt_body else data

        headers = self.build_headers(
            aes_key=aes_key,
            token=token,
            extra_headers=extra_headers,
            encrypt_token=encrypt_token,
        )
        if req_json is not None:
            headers.setdefault("Content-Type", "application/json")

        return UgreenEncryptedRequest(
            url=clean_url,
            headers=headers,
            params={"encrypt_query": encrypted_query},
            json=req_json,
            aes_key=aes_key,
            plain_query=plain_query,
        )

    def decrypt_response(self, response_json: Any, aes_key: str) -> Any:
        """
        解密绿联 API 响应。

        如果响应包含 encrypt_resp_body 字段，则用 AES-GCM 解密。
        """
        if not isinstance(response_json, Mapping):
            return response_json
        encrypted = response_json.get("encrypt_resp_body")
        if not encrypted:
            return response_json
        plain = self.aes_gcm_decrypt(str(encrypted), aes_key)
        try:
            return json.loads(plain)
        except json.JSONDecodeError:
            return plain
