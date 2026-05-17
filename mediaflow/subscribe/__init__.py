"""
订阅模块

提供RSS订阅管理功能
"""

from mediaflow.subscribe.subscription_manager import SubscriptionManager, get_subscription_manager
from mediaflow.subscribe.subscription import SubscriptionInfo

__all__ = [
    "SubscriptionManager",
    "get_subscription_manager",
    "SubscriptionInfo",
]
