import time
import threading
from typing import Optional, Dict, List, Tuple, Any


class MessageIdCache:
    """消息ID缓存,用于幂等性控制"""

    def __init__(self, expire_seconds: int = 600):
        """
        初始化缓存

        Args:
            expire_seconds: 缓存过期时间(秒),默认600秒(10分钟)
        """
        self._cache = {}
        self._lock = threading.Lock()
        self._expire_seconds = expire_seconds

    def is_processed(self, msgid: Optional[str]) -> bool:
        """
        检查消息ID是否已处理且未过期

        Args:
            msgid: 消息ID

        Returns:
            True表示已处理,False表示未处理
        """
        if not msgid:
            return False

        with self._lock:
            self._cleanup_expired()

            if msgid not in self._cache:
                return False

            current_time = time.time()
            if current_time < self._cache[msgid]:
                return True
            else:
                # 已过期,删除记录
                del self._cache[msgid]
                return False

    def mark_processed(self, msgid: Optional[str]):
        """
        标记消息ID为已处理

        Args:
            msgid: 消息ID
        """
        if not msgid:
            return

        with self._lock:
            self._cache[msgid] = time.time() + self._expire_seconds

    def _cleanup_expired(self):
        """清理过期的缓存记录"""
        current_time = time.time()
        expired_keys = [
            msgid for msgid, expire_time in self._cache.items()
            if current_time >= expire_time
        ]
        for key in expired_keys:
            del self._cache[key]

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()


class PendingNoteCache:
    """
    待更新笔记缓存
    用于缓存用户发送的图片笔记，支持 2 分钟窗口期内追加图片或添加描述

    缓存结构: {user_id: {note_id, created_at, attachments}}
    """

    def __init__(self, expire_seconds: int = 120):
        """
        初始化缓存

        Args:
            expire_seconds: 过期时间(秒)，默认120秒(2分钟)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._expire_seconds = expire_seconds

    def get_pending(self, user_id: str) -> Optional[Tuple[int, List[Dict]]]:
        """
        获取用户的待更新笔记信息

        Args:
            user_id: 用户ID

        Returns:
            (note_id, attachments) 或 None（无缓存或已过期）
        """
        with self._lock:
            self._cleanup_expired()

            if user_id not in self._cache:
                return None

            record = self._cache[user_id]

            # 检查是否过期
            if self._is_expired(record["created_at"]):
                del self._cache[user_id]
                return None

            return (record["note_id"], record["attachments"])

    def set_pending(
        self,
        user_id: str,
        note_id: int,
        attachments: List[Dict]
    ):
        """
        设置用户的待更新笔记缓存

        Args:
            user_id: 用户ID
            note_id: Blinko 笔记 ID
            attachments: 图片附件列表
        """
        with self._lock:
            self._cache[user_id] = {
                "note_id": note_id,
                "created_at": time.time(),
                "attachments": attachments
            }

    def clear_pending(self, user_id: str):
        """
        清除用户的待更新笔记缓存

        Args:
            user_id: 用户ID
        """
        with self._lock:
            if user_id in self._cache:
                del self._cache[user_id]

    def _is_expired(self, created_at: float) -> bool:
        """
        检查缓存记录是否过期

        Args:
            created_at: 创建时间戳

        Returns:
            True 表示已过期，False 表示未过期
        """
        current_time = time.time()
        return current_time >= created_at + self._expire_seconds

    def _cleanup_expired(self):
        """清理过期的缓存记录"""
        current_time = time.time()
        expired_keys = [
            user_id for user_id, record in self._cache.items()
            if self._is_expired(record["created_at"])
        ]
        for key in expired_keys:
            del self._cache[key]
