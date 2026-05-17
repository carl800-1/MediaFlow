"""
BT 磁力链下载模块

支持磁力链和种子文件的下载管理
"""

import re
import hashlib
import base64
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse


@dataclass
class MagnetInfo:
    """磁力链信息"""
    hash: str
    title: str = ""
    trackers: List[str] = None
    files: List[Dict[str, Any]] = None
    name: str = ""

    def __post_init__(self):
        if self.trackers is None:
            self.trackers = []
        if self.files is None:
            self.files = []


class MagnetParser:
    """磁力链解析器"""

    MAGNET_PREFIX = "magnet:?"

    @staticmethod
    def parse(magnet_link: str) -> Optional[MagnetInfo]:
        """解析磁力链"""
        if not magnet_link:
            return None

        magnet_link = magnet_link.strip()
        if not magnet_link.startswith(MagnetParser.MAGNET_PREFIX):
            return None

        try:
            params = {}
            hash_info = ""

            query = magnet_link[len(MagnetParser.MAGNET_PREFIX):]
            pairs = query.split("&")

            for pair in pairs:
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    key = key.lower()
                    value = MagnetParser._decode_value(value)

                    if key == "xt":
                        if value.startswith("urn:btih:"):
                            hash_info = value[9:]
                    elif key == "dn":
                        params["name"] = value
                    elif key == "tr":
                        if "trackers" not in params:
                            params["trackers"] = []
                        params["trackers"].append(value)
                    elif key == "xl":
                        params["size"] = value
                    elif key == "xt":
                        if "info_hash" not in params:
                            params["info_hash"] = value

            if not hash_info:
                return None

            hash_info = hash_info.upper()

            return MagnetInfo(
                hash=hash_info,
                name=params.get("name", ""),
                trackers=params.get("trackers", [])
            )

        except Exception:
            return None

    @staticmethod
    def _decode_value(value: str) -> str:
        """解码值"""
        try:
            return base64.b64decode(value + "==").decode("utf-8")
        except Exception:
            return value

    @staticmethod
    def create(hash_info: str, name: str = "", trackers: List[str] = None) -> str:
        """创建磁力链"""
        hash_info = hash_info.upper()

        parts = [f"urn:btih:{hash_info}"]

        if name:
            parts.append(f"dn={MagnetParser._encode_value(name)}")

        if trackers:
            for tracker in trackers:
                parts.append(f"tr={MagnetParser._encode_value(tracker)}")

        return MagnetParser.MAGNET_PREFIX + "&".join(parts)

    @staticmethod
    def _encode_value(value: str) -> str:
        """编码值"""
        return value

    @staticmethod
    def is_valid_hash(hash_str: str) -> bool:
        """验证哈希是否有效"""
        if not hash_str:
            return False

        hash_str = hash_str.upper()

        if len(hash_str) == 32:
            return bool(re.match(r"^[A-F0-9]{32}$", hash_str))

        if len(hash_str) == 40:
            return bool(re.match(r"^[A-F0-9]{40}$", hash_str))

        return False

    @staticmethod
    def normalize_hash(hash_str: str) -> str:
        """标准化哈希格式（转换为40位大写）"""
        if not hash_str:
            return ""

        hash_str = hash_str.upper()

        hash_str = re.sub(r"[^A-F0-9]", "", hash_str)

        if len(hash_str) == 32:
            hash_bytes = bytes.fromhex(hash_str)
            hash_str = hash_bytes.hex().upper()

        return hash_str


class TorrentInfo:
    """种子文件信息"""

    def __init__(self):
        self.info_hash: str = ""
        self.name: str = ""
        self.total_size: int = 0
        self.creation_date: Optional[int] = None
        self.comment: str = ""
        self.created_by: str = ""
        self.piece_length: int = 0
        self.pieces: bytes = b""
        self.files: List[Dict[str, Any]] = []
        self.is_private: bool = False
        self.dht_nodes: List[tuple] = []

    @classmethod
    def from_dict(cls, data: Dict) -> "TorrentInfo":
        """从字典创建"""
        info = cls()
        info.info_hash = data.get("info_hash", "")
        info.name = data.get("name", "")
        info.total_size = data.get("total_size", 0)
        info.creation_date = data.get("creation_date")
        info.comment = data.get("comment", "")
        info.created_by = data.get("created_by", "")
        info.piece_length = data.get("piece_length", 0)
        info.files = data.get("files", [])
        info.is_private = data.get("is_private", False)
        return info

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "info_hash": self.info_hash,
            "name": self.name,
            "total_size": self.total_size,
            "creation_date": self.creation_date,
            "comment": self.comment,
            "created_by": self.created_by,
            "piece_length": self.piece_length,
            "files": self.files,
            "is_private": self.is_private,
        }


class BTDownloader:
    """BT下载器（基于libtorrent协议）"""

    def __init__(self, host: str = "localhost", port: int = 6881):
        self.host = host
        self.port = port
        self._session = None
        self._use_libtorrent = False

    def connect(self) -> bool:
        """连接BT服务"""
        try:
            import libtorrent as lt
            self._session = lt.session()
            self._session.listen_on(self.port, self.port + 100)
            self._use_libtorrent = True
            return True
        except ImportError:
            self._use_libtorrent = False
            return True

    def add_magnet(self, magnet_link: str, save_path: str = "./downloads") -> Optional[str]:
        """添加磁力链下载"""
        if not magnet_link:
            return None

        magnet_info = MagnetParser.parse(magnet_link)
        if not magnet_info:
            return None

        if self._use_libtorrent and self._session:
            try:
                import libtorrent as lt

                params = {
                    "save_path": save_path,
                    "storage_mode": lt.storage_mode_t.storage_mode_sparse,
                }

                handle = lt.add_magnet_uri(self._session, magnet_link, params)

                return magnet_info.hash

            except Exception as e:
                return None

        return magnet_info.hash

    def add_torrent_file(self, torrent_path: str, save_path: str = "./downloads") -> Optional[str]:
        """添加种子文件下载"""
        if not torrent_path:
            return None

        if self._use_libtorrent and self._session:
            try:
                import libtorrent as lt

                ti = lt.torrent_info(torrent_path)
                params = {
                    "save_path": save_path,
                    "ti": ti,
                }

                handle = self._session.add_torrent(params)

                return str(ti.info_hash())

            except Exception:
                return None

        return None

    def get_download_status(self, info_hash: str) -> Dict[str, Any]:
        """获取下载状态"""
        if not self._session or not self._use_libtorrent:
            return {"state": "unknown", "progress": 0}

        try:
            for handle in self._session.get_torrents():
                if str(handle.info_hash()) == info_hash:
                    state = handle.status()

                    return {
                        "hash": info_hash,
                        "name": state.name,
                        "state": str(state.state),
                        "progress": state.progress * 100,
                        "download_speed": state.download_rate,
                        "upload_speed": state.upload_rate,
                        "seeds": state.num_seeds,
                        "peers": state.num_peers,
                        "total_download": state.total_download,
                        "total_upload": state.total_upload,
                        "total_size": state.total_wanted,
                    }

        except Exception:
            pass

        return {"state": "not_found", "progress": 0}

    def pause_download(self, info_hash: str) -> bool:
        """暂停下载"""
        if not self._session or not self._use_libtorrent:
            return False

        try:
            for handle in self._session.get_torrents():
                if str(handle.info_hash()) == info_hash:
                    handle.pause()
                    return True
        except Exception:
            pass

        return False

    def resume_download(self, info_hash: str) -> bool:
        """恢复下载"""
        if not self._session or not self._use_libtorrent:
            return False

        try:
            for handle in self._session.get_torrents():
                if str(handle.info_hash()) == info_hash:
                    handle.resume()
                    return True
        except Exception:
            pass

        return False

    def remove_download(self, info_hash: str, delete_files: bool = False) -> bool:
        """删除下载"""
        if not self._session or not self._use_libtorrent:
            return False

        try:
            for handle in self._session.get_torrents():
                if str(handle.info_hash()) == info_hash:
                    self._session.remove_torrent(handle, int(delete_files))
                    return True
        except Exception:
            pass

        return False
