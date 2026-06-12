"""命令基类模块"""
import asyncio
from .storage import StorageManager


class CommandBase:
    """命令基类，提供共享基础设施"""

    def __init__(self, star, storage: StorageManager):
        self.star = star
        self.storage = storage
        self.user_locks: dict[str, asyncio.Lock] = {}

    def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        """获取用户级锁（按需创建）"""
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]
