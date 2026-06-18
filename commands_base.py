"""命令基类模块"""
from .storage import StorageManager


class CommandBase:
    """命令基类，提供共享基础设施"""

    def __init__(self, star, storage: StorageManager):
        self.star = star
        self.storage = storage

    def _get_user_lock(self, user_id: str):
        """获取存储管理器中的共享用户锁。"""
        return self.storage.get_user_lock(user_id)
