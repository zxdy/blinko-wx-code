"""
依赖注入容器
管理服务的单例实例，解决重复创建问题
"""

from functools import lru_cache
from typing import Optional

from config.settings import settings
from config.constants import PENDING_NOTE_EXPIRE_SECONDS
from services.token_manager import TokenManager
from services.wecom_api import WeComAPI
from services.blinko_service import BlinkoService
from utils.cache import MessageIdCache, PendingNoteCache


class Container:
    """服务容器，管理单例实例"""

    _instance: Optional['Container'] = None

    def __new__(cls) -> 'Container':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    @lru_cache(maxsize=1)
    def get_token_manager() -> TokenManager:
        """获取 TokenManager 单例"""
        return TokenManager()

    @staticmethod
    @lru_cache(maxsize=1)
    def get_message_cache() -> MessageIdCache:
        """获取 MessageIdCache 单例"""
        return MessageIdCache(expire_seconds=settings.CACHE_EXPIRE_SECONDS)

    @staticmethod
    @lru_cache(maxsize=1)
    def get_pending_note_cache() -> PendingNoteCache:
        """获取 PendingNoteCache 单例"""
        return PendingNoteCache(expire_seconds=PENDING_NOTE_EXPIRE_SECONDS)

    @staticmethod
    @lru_cache(maxsize=1)
    def get_wecom_api() -> WeComAPI:
        """获取 WeComAPI 单例"""
        return WeComAPI()

    @staticmethod
    @lru_cache(maxsize=1)
    def get_blinko_service() -> BlinkoService:
        """获取 BlinkoService 单例"""
        return BlinkoService()

    @classmethod
    def clear_cache(cls):
        """清除所有缓存（用于测试或重置）"""
        cls.get_token_manager.cache_clear()
        cls.get_message_cache.cache_clear()
        cls.get_pending_note_cache.cache_clear()
        cls.get_wecom_api.cache_clear()
        cls.get_blinko_service.cache_clear()


# 全局容器实例
container = Container()