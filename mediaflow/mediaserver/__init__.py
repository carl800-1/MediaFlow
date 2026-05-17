"""
MediaServer 模块

支持 Jellyfin、Plex、Emby、绿联影视 等媒体服务器
"""

from mediaflow.mediaserver.client import MediaServerClient
from mediaflow.mediaserver.jellyfin import JellyfinClient
from mediaflow.mediaserver.plex import PlexClient
from mediaflow.mediaserver.emby import EmbyClient
from mediaflow.mediaserver.ugreen import UGreenClient
from mediaflow.mediaserver.manager import MediaServerManager

__all__ = [
    "MediaServerClient",
    "JellyfinClient",
    "PlexClient",
    "EmbyClient",
    "UGreenClient",
    "MediaServerManager",
]
