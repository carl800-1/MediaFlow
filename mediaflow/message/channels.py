"""
消息渠道

定义消息通知接口和实现
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    HTML = "html"
    IMAGE = "image"
    FILE = "file"


@dataclass
class Message:
    """消息内容"""
    title: str
    content: str
    type: MessageType = MessageType.TEXT
    image_url: Optional[str] = None
    file_path: Optional[str] = None


class BaseMessageClient(ABC):
    """消息客户端基类"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._enabled = config.get("enabled", True)

    @abstractmethod
    def send(self, message: Message) -> bool:
        """发送消息"""
        pass

    @property
    def is_enabled(self) -> bool:
        """是否启用"""
        return self._enabled

    def validate_config(self) -> bool:
        """验证配置"""
        return True


class TelegramClient(BaseMessageClient):
    """Telegram客户端"""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._bot_token = config.get("bot_token")
        self._chat_id = config.get("chat_id")
        self._api_url = f"https://api.telegram.org/bot{self._bot_token}"

    def send(self, message: Message) -> bool:
        """发送Telegram消息"""
        if not self._bot_token or not self._chat_id:
            return False

        try:
            import requests

            text = f"*{message.title}*\n\n{message.content}"
            url = f"{self._api_url}/sendMessage"
            response = requests.post(
                url,
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                },
                timeout=10
            )

            return response.status_code == 200
        except Exception:
            return False

    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self._bot_token and self._chat_id)


class WechatClient(BaseMessageClient):
    """微信客户端"""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._webhook_url = config.get("webhook_url")

    def send(self, message: Message) -> bool:
        """发送微信消息"""
        if not self._webhook_url:
            return False

        try:
            import requests

            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"{message.title}\n\n{message.content}"
                }
            }

            response = requests.post(
                self._webhook_url,
                json=payload,
                timeout=10
            )

            return response.status_code == 200
        except Exception:
            return False

    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self._webhook_url)


class EmailClient(BaseMessageClient):
    """邮件客户端"""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._smtp_host = config.get("smtp_host")
        self._smtp_port = config.get("smtp_port", 587)
        self._smtp_user = config.get("smtp_user")
        self._smtp_password = config.get("smtp_password")
        self._from_addr = config.get("from_addr")
        self._to_addrs = config.get("to_addrs", [])

    def send(self, message: Message) -> bool:
        """发送邮件"""
        if not all([self._smtp_host, self._smtp_user, self._to_addrs]):
            return False

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.header import Header

            msg = MIMEText(message.content, "plain", "utf-8")
            msg["Subject"] = Header(message.title, "utf-8")
            msg["From"] = self._from_addr or self._smtp_user
            msg["To"] = ",".join(self._to_addrs)

            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._smtp_user, self._smtp_password)
                server.send_message(msg)

            return True
        except Exception:
            return False

    def validate_config(self) -> bool:
        """验证配置"""
        return bool(
            self._smtp_host and
            self._smtp_user and
            self._smtp_password and
            self._to_addrs
        )


class ServerChanClient(BaseMessageClient):
    """Server酱客户端"""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._sendkey = config.get("sendkey")

    def send(self, message: Message) -> bool:
        """发送Server酱消息"""
        if not self._sendkey:
            return False

        try:
            import requests

            url = f"https://sctapi.ftqq.com/{self._sendkey}.send"
            response = requests.post(
                url,
                data={
                    "title": message.title,
                    "desp": message.content
                },
                timeout=10
            )

            return response.status_code == 200
        except Exception:
            return False


class BarkClient(BaseMessageClient):
    """Bark客户端"""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._server_url = config.get("server_url")
        self._device_key = config.get("device_key")

    def send(self, message: Message) -> bool:
        """发送Bark消息"""
        if not self._device_key:
            return False

        try:
            import requests

            url = f"{self._server_url}/{self._device_key}/{message.title}"
            if message.content:
                url += f"/{message.content}"

            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
