import time
import threading
from typing import Optional


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
