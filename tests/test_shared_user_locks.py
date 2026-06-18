"""共享用户锁回归测试。"""
import asyncio
import importlib.util
import os
import sys
import types
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_NAME = "astrbot_plugin_fishing_game"

if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [PROJECT_ROOT]
    sys.modules[PACKAGE_NAME] = package


def _load_module(module_name: str, file_name: str):
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = os.path.join(PROJECT_ROOT, file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_load_module(f"{PACKAGE_NAME}.fish_data", "fish_data.py")
_load_module(f"{PACKAGE_NAME}.models", "models.py")
storage_module = _load_module(f"{PACKAGE_NAME}.storage", "storage.py")
commands_base_module = _load_module(f"{PACKAGE_NAME}.commands_base", "commands_base.py")

StorageManager = storage_module.StorageManager
CommandBase = commands_base_module.CommandBase


class _MemoryStar:
    async def get_kv_data(self, key, default=None):
        return default

    async def put_kv_data(self, key, value):
        return None


class SharedUserLockTests(unittest.IsolatedAsyncioTestCase):
    """验证不同命令模块取得同一把用户锁。"""

    async def test_command_modules_share_same_lock(self):
        storage = StorageManager(_MemoryStar())
        first_module = CommandBase(object(), storage)
        second_module = CommandBase(object(), storage)

        self.assertIs(
            first_module._get_user_lock("user_1"),
            second_module._get_user_lock("user_1"),
        )
        self.assertIs(
            first_module._get_user_lock("user_1"),
            storage.get_user_lock("user_1"),
        )
        self.assertIsNot(
            storage.get_user_lock("user_1"),
            storage.get_user_lock("user_2"),
        )

    async def test_shared_lock_serializes_different_modules(self):
        storage = StorageManager(_MemoryStar())
        first_module = CommandBase(object(), storage)
        second_module = CommandBase(object(), storage)
        order = []

        async def first_operation():
            async with first_module._get_user_lock("user_1"):
                order.append("first_start")
                await asyncio.sleep(0.02)
                order.append("first_end")

        async def second_operation():
            await asyncio.sleep(0)
            async with second_module._get_user_lock("user_1"):
                order.append("second")

        await asyncio.gather(first_operation(), second_operation())
        self.assertEqual(order, ["first_start", "first_end", "second"])


if __name__ == "__main__":
    unittest.main()
