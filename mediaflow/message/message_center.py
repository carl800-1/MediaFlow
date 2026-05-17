"""
消息中心

统一管理消息发送
"""

import threading
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field

from mediaflow.utils.cli import getLogger
from mediaflow.utils.config import get_config
from mediaflow.message.channels import (
    Message,
    MessageType,
    BaseMessageClient,
    TelegramClient,
    WechatClient,
    EmailClient,
    ServerChanClient,
    BarkClient,
)


logger = getLogger("message")


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = True
    telegram: Dict[str, Any] = field(default_factory=dict)
    wechat: Dict[str, Any] = field(default_factory=dict)
    email: Dict[str, Any] = field(default_factory=dict)
    serverchan: Dict[str, Any] = field(default_factory=dict)
    bark: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SendResult:
    """发送结果"""
    channel: str
    success: bool
    message: str = ""


class MessageCenter:
    """消息中心"""

    _instance: Optional["MessageCenter"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._clients: Dict[str, BaseMessageClient] = {}
        self._enabled = True
        self._init_clients()

    @classmethod
    def get_instance(cls) -> "MessageCenter":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _init_clients(self) -> None:
        """初始化客户端"""
        try:
            config = get_config().notification

            if config.telegram_bot_token:
                self._clients["telegram"] = TelegramClient({
                    "enabled": True,
                    "bot_token": config.telegram_bot_token,
                    "chat_id": config.telegram_chat_id,
                })
                logger.info("初始化Telegram通知客户端")

            if config.get("wechat_webhook"):
                self._clients["wechat"] = WechatClient({
                    "enabled": True,
                    "webhook_url": config["wechat_webhook"],
                })
                logger.info("初始化微信通知客户端")

            logger.info(f"已初始化 {len(self._clients)} 个通知渠道")
        except Exception as e:
            logger.error(f"初始化通知客户端失败: {e}")

    def send(
        self,
        title: str,
        content: str,
        channels: Optional[List[str]] = None,
        message_type: MessageType = MessageType.TEXT,
        **kwargs
    ) -> List[SendResult]:
        """
        发送消息

        Args:
            title: 消息标题
            content: 消息内容
            channels: 指定的渠道列表，None表示所有渠道
            message_type: 消息类型

        Returns:
            发送结果列表
        """
        if not self._enabled:
            return []

        message = Message(
            title=title,
            content=content,
            type=message_type,
            **kwargs
        )

        results = []
        target_channels = channels or list(self._clients.keys())

        for channel_name in target_channels:
            client = self._clients.get(channel_name)
            if not client or not client.is_enabled:
                results.append(SendResult(
                    channel=channel_name,
                    success=False,
                    message="渠道未启用"
                ))
                continue

            try:
                success = client.send(message)
                results.append(SendResult(
                    channel=channel_name,
                    success=success,
                    message="发送成功" if success else "发送失败"
                ))
            except Exception as e:
                logger.error(f"发送消息失败 [{channel_name}]: {e}")
                results.append(SendResult(
                    channel=channel_name,
                    success=False,
                    message=str(e)
                ))

        return results

    def send_text(
        self,
        title: str,
        content: str,
        channels: Optional[List[str]] = None
    ) -> List[SendResult]:
        """发送文本消息"""
        return self.send(title, content, channels, MessageType.TEXT)

    def send_html(
        self,
        title: str,
        content: str,
        channels: Optional[List[str]] = None
    ) -> List[SendResult]:
        """发送HTML消息"""
        return self.send(title, content, channels, MessageType.HTML)

    def send_image(
        self,
        title: str,
        image_url: str,
        channels: Optional[List[str]] = None
    ) -> List[SendResult]:
        """发送图片消息"""
        return self.send(
            title,
            "",
            channels,
            MessageType.IMAGE,
            image_url=image_url
        )

    def send_task_notification(
        self,
        task_name: str,
        status: str,
        details: str,
        channels: Optional[List[str]] = None
    ) -> List[SendResult]:
        """发送任务通知"""
        title = f"任务通知: {task_name}"
        content = f"状态: {status}\n详情: {details}"
        return self.send_text(title, content, channels)

    def send_download_notification(
        self,
        title: str,
        torrent_name: str,
        size: str,
        speed: str,
        channels: Optional[List[str]] = None
    ) -> List[SendResult]:
        """发送下载通知"""
        content = f"种子: {torrent_name}\n大小: {size}\n速度: {speed}"
        return self.send_text(title, content, channels)

    def send_sign_notification(
        self,
        site_name: str,
        success: bool,
        bonus: Optional[float] = None,
        channels: Optional[List[str]] = None
    ) -> List[SendResult]:
        """发送签到通知"""
        title = f"签到结果: {site_name}"
        if success:
            content = f"签到成功！"
            if bonus:
                content += f"\n获得魔力值: {bonus}"
        else:
            content = "签到失败"
        return self.send_text(title, content, channels)

    def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        channels: Optional[List[str]] = None
    ) -> List[SendResult]:
        """发送错误通知"""
        title = f"错误通知: {error_type}"
        content = f"错误信息: {error_message}"
        return self.send_text(title, content, channels)

    def enable_channel(self, channel: str) -> bool:
        """启用渠道"""
        if channel in self._clients:
            self._clients[channel]._enabled = True
            return True
        return False

    def disable_channel(self, channel: str) -> bool:
        """禁用渠道"""
        if channel in self._clients:
            self._clients[channel]._enabled = False
            return True
        return False

    def get_channels(self) -> List[str]:
        """获取可用渠道"""
        return list(self._clients.keys())

    def get_channel_status(self) -> Dict[str, bool]:
        """获取渠道状态"""
        return {
            name: client.is_enabled
            for name, client in self._clients.items()
        }

    @property
    def enabled(self) -> bool:
        """是否启用"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置启用状态"""
        self._enabled = value


_global_message_center: Optional[MessageCenter] = None


def get_message_center() -> MessageCenter:
    """获取全局消息中心"""
    global _global_message_center
    if _global_message_center is None:
        _global_message_center = MessageCenter.get_instance()
    return _global_message_center
