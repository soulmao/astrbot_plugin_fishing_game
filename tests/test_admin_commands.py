"""管理员发放钓竿与券类道具的回归测试。"""
import asyncio
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_NAME = "astrbot_plugin_fishing_game"

package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [PROJECT_ROOT]
sys.modules[PACKAGE_NAME] = package


def _load_module(module_name: str, file_name: str):
    path = os.path.join(PROJECT_ROOT, file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_load_module(f"{PACKAGE_NAME}.fish_data", "fish_data.py")
models_module = _load_module(f"{PACKAGE_NAME}.models", "models.py")
_load_module(f"{PACKAGE_NAME}.utils", "utils.py")
_load_module(f"{PACKAGE_NAME}.storage", "storage.py")
_load_module(f"{PACKAGE_NAME}.commands_base", "commands_base.py")
admin_module = _load_module(f"{PACKAGE_NAME}.command_admin", "command_admin.py")

UserData = models_module.UserData
AdminCommands = admin_module.AdminCommands


class _MockStar:
    admin_uids = {"admin"}


class _MockStorage:
    def __init__(self):
        self.users = {"user": UserData("user")}
        self.locks = {}
        self.values = {}

    def get_user_lock(self, user_id: str):
        if user_id not in self.locks:
            self.locks[user_id] = asyncio.Lock()
        return self.locks[user_id]

    async def user_exists(self, user_id: str) -> bool:
        return user_id in self.users

    async def get_user(self, user_id: str):
        return self.users[user_id]

    async def save_user(self, user):
        self.users[user.user_id] = user

    async def get_kv_data(self, key, default=None):
        return self.values.get(key, default)

    async def put_kv_data(self, key, value):
        self.values[key] = value


class AdminCommandTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.storage = _MockStorage()
        self.commands = AdminCommands(_MockStar(), self.storage)
        self.event = MagicMock()
        self.event.get_sender_id.return_value = "admin"

    async def test_add_rod_with_skill_value_and_enchant_count(self):
        result = await self.commands.cmd_admin(
            self.event, "加钓竿", "user", "rod_004", "rod_pref_10", "幸运", "25%", "8"
        )

        rod = self.storage.users["user"].get_owned_rods()[-1]
        self.assertIn("添加", result)
        self.assertEqual(rod["base_id"], "rod_004")
        self.assertEqual(rod["prefix_id"], "rod_pref_10")
        self.assertEqual(rod["skills"], {"lucky": 0.25})
        self.assertEqual(rod["enchant_count"], 8)

    async def test_add_rod_with_multiple_compact_skills(self):
        result = await self.commands.cmd_admin(
            self.event, "加钓竿", "user", "rod_002", "rod_pref_11",
            "迅捷45%", "幸运25%", "丰收20%", "寻宝25%", "潮汐8%",
            "神慧45%", "经验修补30%", "远航25%", "7",
        )

        rod = self.storage.users["user"].get_owned_rods()[-1]
        self.assertIn("累计附魔: 7 次", result)
        self.assertEqual(rod["enchant_count"], 7)
        self.assertEqual(rod["skills"], {
            "swift": 0.45,
            "lucky": 0.25,
            "harvest": 0.20,
            "treasure": 0.25,
            "tide": 0.08,
            "exp_boost": 0.45,
            "mending": 0.30,
            "voyage": 0.25,
        })

    async def test_add_special_rod_without_prefix(self):
        result = await self.commands.cmd_admin(
            self.event, "加钓竿", "user", "rod_006"
        )

        rod = self.storage.users["user"].get_owned_rods()[-1]
        self.assertIn("金币钓竿", result)
        self.assertEqual(rod["prefix_id"], "")

    async def test_reject_invalid_rod_skill_boundaries(self):
        result = await self.commands.cmd_admin(
            self.event, "加钓竿", "user", "rod_004", "rod_pref_10", "幸运", "101%", "1"
        )
        self.assertIn("不超过 100%", result)

        result = await self.commands.cmd_admin(
            self.event, "加钓竿", "user", "rod_004", "rod_pref_10", "幸运", "20", "101"
        )
        self.assertIn("0 到 100", result)

    async def test_add_all_ticket_types(self):
        await self.commands.cmd_admin(self.event, "加券", "user", "ench_ticket_002", "3")
        await self.commands.cmd_admin(self.event, "加券", "user", "refresh_token", "4")
        await self.commands.cmd_admin(
            self.event, "加券", "user", "directed_enchant_swift_15", "2"
        )

        user = self.storage.users["user"]
        self.assertEqual(user.get_enchant_ticket_count("ench_ticket_002"), 3)
        self.assertEqual(user.get_item_count("refresh_token"), 4)
        self.assertEqual(user.get_item_count("directed_enchant_swift_15"), 2)

    async def test_reject_unknown_or_invalid_ticket(self):
        unknown = await self.commands.cmd_admin(self.event, "加券", "user", "unknown", "1")
        invalid_tier = await self.commands.cmd_admin(
            self.event, "加券", "user", "directed_enchant_swift_99", "1"
        )
        invalid_count = await self.commands.cmd_admin(
            self.event, "加券", "user", "refresh_token", "0"
        )

        self.assertIn("未知的券", unknown)
        self.assertIn("无效的定向附魔券", invalid_tier)
        self.assertIn("1 到 10000", invalid_count)

    async def test_item_id_searches_by_name_and_id(self):
        by_name = await self.commands.cmd_admin(self.event, "物品ID", "贪婪")
        by_id = await self.commands.cmd_admin(self.event, "物品ID", "rod_006")

        self.assertIn("rod_pref_12", by_name)
        self.assertIn("rod_pref_19", by_name)
        self.assertIn("金币钓竿", by_id)

    async def test_item_id_filters_category_and_keyword(self):
        result = await self.commands.cmd_admin(self.event, "物品ID", "券", "swift")

        self.assertIn("directed_enchant_swift_5", result)
        self.assertNotIn("directed_enchant_lucky_5", result)

    async def test_item_id_supports_skill_alias_and_pagination(self):
        skills = await self.commands.cmd_admin(self.event, "物品ID", "技能")
        second_page = await self.commands.cmd_admin(self.event, "物品ID", "钓竿前缀", "2")
        invalid_page = await self.commands.cmd_admin(self.event, "物品ID", "钓竿", "99")

        self.assertIn("swift", skills)
        self.assertIn("第 2/", second_page)
        self.assertIn("页码超出范围", invalid_page)


if __name__ == "__main__":
    unittest.main()
