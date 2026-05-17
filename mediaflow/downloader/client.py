"""
具体下载器客户端实现
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin

from mediaflow.downloader.client import BaseDownloader, DownloaderConfig, TorrentDetail
from mediaflow.utils.cli import getLogger


logger = getLogger("qbittorrent")


class QbittorrentClient(BaseDownloader):
    """Qbittorrent下载器客户端"""

    def __init__(self, config: DownloaderConfig) -> None:
        super().__init__(config)
        self._session = requests.Session()
        self._base_url = f"http://{config.host}:{config.port}"

    def connect(self) -> bool:
        """连接下载器"""
        try:
            if self.config.username and self.config.password:
                login_url = urljoin(self._base_url, "/api/v2/auth/login")
                response = self._session.post(
                    login_url,
                    data={
                        "username": self.config.username,
                        "password": self.config.password,
                    },
                    timeout=10,
                )
                if response.status_code != 200:
                    return False
                cookie = response.cookies.get("SID")
                if not cookie:
                    return False

            prefs_url = urljoin(self._base_url, "/api/v2/app/preferences")
            response = self._session.get(prefs_url, timeout=5)
            self._connected = response.status_code == 200
            return self._connected
        except Exception as e:
            logger.error(f"连接Qbittorrent失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开连接"""
        self._session.close()
        self._connected = False

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """发送GET请求"""
        url = urljoin(self._base_url, endpoint)
        try:
            response = self._session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Qbittorrent请求失败: {e}")
            return None

    def _post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """发送POST请求"""
        url = urljoin(self._base_url, endpoint)
        try:
            response = self._session.post(url, data=data, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Qbittorrent请求失败: {e}")
            return False

    def get_torrents(self) -> List[TorrentDetail]:
        """获取种子列表"""
        data = self._get("/api/v2/torrents/info")
        if not data:
            return []

        torrents = []
        for t in data:
            torrent = TorrentDetail(
                hash=t.get("hash", ""),
                name=t.get("name", ""),
                size=t.get("size", 0),
                progress=t.get("progress", 0) * 100,
                state=t.get("state", ""),
                seeds=t.get("num_seeds", 0),
                peers=t.get("num_leechs", 0),
                download_speed=t.get("dlspeed", 0),
                upload_speed=t.get("upspeed", 0),
                ratio=t.get("ratio", 0),
                added_time=datetime.fromtimestamp(t.get("added_on", 0)),
                completed_time=datetime.fromtimestamp(t.get("completion_on", 0))
                    if t.get("completion_on") else None,
                save_path=t.get("save_path", ""),
                tags=t.get("tags", "").split(",") if t.get("tags") else [],
            )
            torrents.append(torrent)
        return torrents

    def get_torrent(self, hash: str) -> Optional[TorrentDetail]:
        """获取指定种子"""
        torrents = self.get_torrents()
        for t in torrents:
            if t.hash.lower() == hash.lower():
                return t
        return None

    def add_torrent(self, url: str, save_path: Optional[str] = None) -> bool:
        """添加种子"""
        data = {"urls": url}
        if save_path:
            data["savepath"] = save_path
        return self._post("/api/v2/torrents/add", data)

    def delete_torrent(self, hash: str, delete_files: bool = False) -> bool:
        """删除种子"""
        return self._post(
            "/api/v2/torrents/delete",
            {"hashes": hash, "deleteFiles": "true" if delete_files else "false"}
        )

    def pause_torrent(self, hash: str) -> bool:
        """暂停种子"""
        return self._post("/api/v2/torrents/pause", {"hashes": hash})

    def resume_torrent(self, hash: str) -> bool:
        """恢复种子"""
        return self._post("/api/v2/torrents/resume", {"hashes": hash})

    def set_torrent_tags(self, hash: str, tags: List[str]) -> bool:
        """设置种子标签"""
        return self._post(
            "/api/v2/torrents/addTags",
            {"hashes": hash, "tags": ",".join(tags)}
        )

    @property
    def free_space(self) -> int:
        """获取剩余空间"""
        data = self._get("/api/v2/app/freeSpace", {"path": "/"})
        if data and "free_space" in data:
            return data["free_space"]
        return 0


class TransmissionClient(BaseDownloader):
    """Transmission下载器客户端"""

    def __init__(self, config: DownloaderConfig) -> None:
        super().__init__(config)
        self._session = requests.Session()
        self._base_url = f"http://{config.host}:{config.port}/transmission/rpc"
        self._session_id = None

    def connect(self) -> bool:
        """连接下载器"""
        try:
            response = self._session.get(self._base_url, timeout=10)
            if response.status_code == 401:
                auth = requests.auth.HTTPBasicAuth(
                    self.config.username or "",
                    self.config.password or ""
                )
                response = self._session.get(self._base_url, auth=auth, timeout=10)
            self._connected = response.status_code == 200
            return self._connected
        except Exception as e:
            logger.error(f"连接Transmission失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开连接"""
        self._session.close()
        self._connected = False

    def _rpc(self, method: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """发送RPC请求"""
        import json
        headers = {"X-Transmission-Session-Id": self._session_id} if self._session_id else {}

        payload = {"method": method}
        if arguments:
            payload["arguments"] = arguments

        try:
            response = self._session.post(
                self._base_url,
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code == 409:
                self._session_id = response.headers.get("X-Transmission-Session-Id")
                headers["X-Transmission-Session-Id"] = self._session_id
                response = self._session.post(
                    self._base_url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )

            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Transmission RPC失败: {e}")
        return None

    def get_torrents(self) -> List[TorrentDetail]:
        """获取种子列表"""
        result = self._rpc("torrent-get", {"fields": [
            "hashString", "name", "totalSize", "percentDone",
            "status", "seeders", "leechers", "rateDownload", "rateUpload",
            "uploadRatio", "addedDate", "doneDate", "downloadDir", "labels"
        ]})

        if not result or "arguments" not in result:
            return []

        torrents = []
        for t in result["arguments"].get("torrents", []):
            state_map = {
                0: "stopped",
                1: "queued",
                2: "seeding",
                3: "queued",
                4: "downloading",
                5: "queued",
                6: "seeding",
            }

            torrent = TorrentDetail(
                hash=t.get("hashString", ""),
                name=t.get("name", ""),
                size=t.get("totalSize", 0),
                progress=t.get("percentDone", 0) * 100,
                state=state_map.get(t.get("status", 0), "unknown"),
                seeds=t.get("seeders", 0),
                peers=t.get("leechers", 0),
                download_speed=t.get("rateDownload", 0),
                upload_speed=t.get("rateUpload", 0),
                ratio=t.get("uploadRatio", 0),
                added_time=datetime.fromtimestamp(t.get("addedDate", 0)),
                completed_time=datetime.fromtimestamp(t.get("doneDate", 0))
                    if t.get("doneDate") else None,
                save_path=t.get("downloadDir", ""),
                tags=t.get("labels", []),
            )
            torrents.append(torrent)
        return torrents

    def get_torrent(self, hash: str) -> Optional[TorrentDetail]:
        """获取指定种子"""
        torrents = self.get_torrents()
        for t in torrents:
            if t.hash.lower() == hash.lower():
                return t
        return None

    def add_torrent(self, url: str, save_path: Optional[str] = None) -> bool:
        """添加种子"""
        args = {"filename": url}
        if save_path:
            args["download-dir"] = save_path
        result = self._rpc("torrent-add", args)
        return result is not None

    def delete_torrent(self, hash: str, delete_files: bool = False) -> bool:
        """删除种子"""
        result = self._rpc("torrent-remove", {
            "ids": [hash],
            "delete-local-data": delete_files
        })
        return result is not None

    def pause_torrent(self, hash: str) -> bool:
        """暂停种子"""
        result = self._rpc("torrent-stop", {"ids": [hash]})
        return result is not None

    def resume_torrent(self, hash: str) -> bool:
        """恢复种子"""
        result = self._rpc("torrent-start", {"ids": [hash]})
        return result is not None

    def set_torrent_tags(self, hash: str, tags: List[str]) -> bool:
        """设置种子标签"""
        result = self._rpc("torrent-set", {"ids": [hash], "labels": tags})
        return result is not None

    @property
    def free_space(self) -> int:
        """获取剩余空间"""
        return 0


class Aria2Client(BaseDownloader):
    """Aria2下载器客户端"""

    def __init__(self, config: DownloaderConfig) -> None:
        super().__init__(config)
        self._session = requests.Session()
        self._base_url = f"http://{config.host}:{config.port}/jsonrpc"

    def connect(self) -> bool:
        """连接下载器"""
        try:
            response = self._session.post(
                self._base_url,
                json={"jsonrpc": "2.0", "method": "aria2.getVersion", "id": 1},
                timeout=5
            )
            self._connected = response.status_code == 200
            return self._connected
        except Exception as e:
            logger.error(f"连接Aria2失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开连接"""
        self._session.close()
        self._connected = False

    def _call(self, method: str, params: Optional[List] = None) -> Optional[Dict[str, Any]]:
        """发送JSON-RPC调用"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1
        }
        if params:
            payload["params"] = params

        try:
            response = self._session.post(self._base_url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Aria2 RPC失败: {e}")
        return None

    def get_torrents(self) -> List[TorrentDetail]:
        """获取种子列表"""
        return []

    def get_torrent(self, hash: str) -> Optional[TorrentDetail]:
        """获取指定种子"""
        return None

    def add_torrent(self, url: str, save_path: Optional[str] = None) -> bool:
        """添加种子"""
        params = [url]
        if save_path:
            params.append({"dir": save_path})
        result = self._call("aria2.addUri", params)
        return result is not None

    def delete_torrent(self, hash: str, delete_files: bool = False) -> bool:
        """删除种子"""
        method = "aria2.remove" if not delete_files else "aria2.removeDownloadResult"
        result = self._call(method, [hash])
        return result is not None

    def pause_torrent(self, hash: str) -> bool:
        """暂停种子"""
        result = self._call("aria2.pause", [hash])
        return result is not None

    def resume_torrent(self, hash: str) -> bool:
        """恢复种子"""
        result = self._call("aria2.unpause", [hash])
        return result is not None

    def set_torrent_tags(self, hash: str, tags: List[str]) -> bool:
        """设置种子标签"""
        return True

    @property
    def free_space(self) -> int:
        """获取剩余空间"""
        return 0
