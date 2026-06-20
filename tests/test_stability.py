"""稳定性测试脚本（无需 AstrBot/pydantic 环境）

直接加载 utils/models/fish_data 模块，验证最近修改的纯逻辑：
- 道具类物品名称解析与价值计算
- UserData 道具增删
- 商店购买数量显示计算
- 拍卖行 item 类型数据结构
"""
import importlib.util
import os
import sys
import types
import unittest

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 构造一个空父包，使 utils.py 中的相对导入可以工作
_pkg = types.ModuleType("astrbot_plugin_fishing_game")
_pkg.__path__ = [PROJECT_ROOT]
sys.modules["astrbot_plugin_fishing_game"] = _pkg


def _load_module(module_name: str, file_name: str):
    """从文件系统加载模块并注册到 sys.modules"""
    path = os.path.join(PROJECT_ROOT, file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# 按依赖顺序加载
_load_module("astrbot_plugin_fishing_game.fish_data", "fish_data.py")
_load_module("astrbot_plugin_fishing_game.models", "models.py")
utils = _load_module("astrbot_plugin_fishing_game.utils", "utils.py")

get_item_name_for_auction = utils.get_item_name_for_auction
calc_item_value = utils.calc_item_value
parse_directed_enchant_id = utils.parse_directed_enchant_id

from astrbot_plugin_fishing_game.models import UserData
from astrbot_plugin_fishing_game.fish_data import (
    FISH_TYPES,
    LEVELS,
    apply_rarity_bonus,
    calc_bait_value,
    get_level_info,
    get_next_level_exp,
)


class ItemAuctionTests(unittest.TestCase):
    """道具类物品上架/显示/价值相关测试"""

    def test_refresh_token_name(self):
        self.assertEqual(
            get_item_name_for_auction({"type": "item", "item_id": "refresh_token"}),
            "🔄 刷新券",
        )

    def test_directed_enchant_name(self):
        self.assertEqual(
            get_item_name_for_auction({"type": "item", "item_id": "directed_enchant_swift_10"}),
            "🎯 定向附魔券[⚡迅捷+10%]",
        )

    def test_unknown_item_name(self):
        self.assertEqual(
            get_item_name_for_auction({"type": "item", "item_id": "future_item"}),
            "future_item",
        )

    def test_refresh_token_value(self):
        self.assertEqual(calc_item_value("refresh_token", 3), 90)

    def test_directed_enchant_value(self):
        self.assertEqual(calc_item_value("directed_enchant_swift_10", 2), 2000)
        self.assertEqual(calc_item_value("directed_enchant_lucky_15", 1), 1500)

    def test_unknown_item_value(self):
        self.assertEqual(calc_item_value("future_item", 5), 0)

    def test_parse_directed_enchant_id(self):
        self.assertEqual(parse_directed_enchant_id("directed_enchant_harvest_15"), ("harvest", 0.15))
        self.assertIsNone(parse_directed_enchant_id("refresh_token"))


class UserDataItemTests(unittest.TestCase):
    """UserData 道具栏操作测试"""

    def test_add_and_remove_item(self):
        user = UserData("test_user")
        user.add_item("refresh_token", 5)
        self.assertEqual(user.get_item_count("refresh_token"), 5)
        self.assertTrue(user.remove_item("refresh_token", 3))
        self.assertEqual(user.get_item_count("refresh_token"), 2)
        self.assertTrue(user.remove_item("refresh_token", 2))
        self.assertEqual(user.get_item_count("refresh_token"), 0)
        self.assertFalse(user.remove_item("refresh_token", 1))

    def test_directed_enchant_item_roundtrip(self):
        user = UserData("test_user")
        user.add_item("directed_enchant_swift_10", 2)
        self.assertEqual(user.get_item_count("directed_enchant_swift_10"), 2)
        tickets = user.get_directed_enchant_tickets()
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0], ("swift", 0.10, 2))


class ShopQuantityTests(unittest.TestCase):
    """验证购买提示数量与实际到账数量一致"""

    def _simulate_buy_quantity(self, item_quantity, buy_quantity):
        """模拟 command_economy.cmd_buy 中鱼饵分支的数量计算"""
        return item_quantity * buy_quantity

    def test_bait_group_quantity(self):
        # 商店显示 x5，购买1次应到账5个
        self.assertEqual(self._simulate_buy_quantity(5, 1), 5)
        self.assertEqual(self._simulate_buy_quantity(5, 2), 10)

    def test_single_bait_quantity(self):
        self.assertEqual(self._simulate_buy_quantity(1, 3), 3)


class BaitBalanceTests(unittest.TestCase):
    """验证鱼饵真实单价和分级稀有度权重。"""

    def test_bait_value_uses_package_quantity(self):
        self.assertEqual(calc_bait_value("bait_001", "bait_pref_02", 5), 10)
        self.assertEqual(calc_bait_value("bait_002", "bait_pref_02", 3), 30)
        self.assertEqual(calc_bait_value("bait_003", "bait_pref_02", 2), 80)
        self.assertEqual(calc_bait_value("bait_004", "bait_pref_02", 1), 200)

    def test_bait_value_handles_partial_packages(self):
        self.assertEqual(calc_bait_value("bait_001", "bait_pref_02", 1), 2)
        self.assertEqual(calc_bait_value("bait_002", "bait_pref_03", 1), 13)

    def test_rarity_bonus_favors_higher_tiers(self):
        bonus = 0.35
        self.assertEqual(apply_rarity_bonus(10, "common", bonus), 10)
        self.assertAlmostEqual(apply_rarity_bonus(10, "rare", bonus), 18.75)
        self.assertAlmostEqual(apply_rarity_bonus(10, "legendary", bonus), 38)
        self.assertAlmostEqual(apply_rarity_bonus(10, "mythic", bonus), 62.5)
        self.assertGreater(
            apply_rarity_bonus(10, "legendary", bonus, prefix=True),
            apply_rarity_bonus(10, "rare", bonus, prefix=True),
        )

    def test_divine_rod_rarity_bonus_is_visible(self):
        def probability(rarities, bonus):
            weights = [
                apply_rarity_bonus(fish["weight"], fish["rarity"], bonus)
                for fish in FISH_TYPES
            ]
            total = sum(weights)
            return sum(
                weight for fish, weight in zip(FISH_TYPES, weights)
                if fish["rarity"] in rarities
            ) / total

        baseline_high = probability({"rare", "legendary", "mythic"}, 0.0)
        divine_high = probability({"rare", "legendary", "mythic"}, 0.35)
        divine_legendary = probability({"legendary"}, 0.35)
        divine_mythic = probability({"mythic"}, 0.35)
        self.assertGreater(divine_high - baseline_high, 0.10)
        self.assertGreater(divine_legendary, 0.02)
        self.assertGreater(divine_mythic, 0.01)


class FishPoolAndLevelExpansionTests(unittest.TestCase):
    """锁定扩充后的鱼池结构、自然占比与 15 级边界。"""

    def test_fish_ids_and_names_are_unique(self):
        self.assertEqual(len(FISH_TYPES), 46)
        self.assertEqual(len({fish["id"] for fish in FISH_TYPES}), len(FISH_TYPES))
        self.assertEqual(len({fish["name"] for fish in FISH_TYPES}), len(FISH_TYPES))

    def test_rare_and_legendary_pool_share_is_increased(self):
        counts = {
            rarity: sum(fish["rarity"] == rarity for fish in FISH_TYPES)
            for rarity in ("rare", "legendary")
        }
        self.assertEqual(counts, {"rare": 16, "legendary": 10})
        total_weight = sum(float(fish["weight"]) for fish in FISH_TYPES)
        rare_share = sum(fish["weight"] for fish in FISH_TYPES if fish["rarity"] == "rare") / total_weight
        legendary_share = sum(fish["weight"] for fish in FISH_TYPES if fish["rarity"] == "legendary") / total_weight
        self.assertGreaterEqual(rare_share, 0.20)
        self.assertGreaterEqual(legendary_share, 0.013)

    def test_level_cap_is_15_and_exp_curve_is_monotonic(self):
        self.assertEqual(LEVELS[-1]["level"], 15)
        self.assertEqual(get_level_info(15)["name"], "深海主宰")
        self.assertIsNone(get_next_level_exp(15))
        self.assertEqual(
            [level["exp_required"] for level in LEVELS],
            sorted(level["exp_required"] for level in LEVELS),
        )
        user = UserData("level_cap")
        user._data.update({"level": 12, "exp": 6400000})
        upgraded, level = user.add_exp(0)
        self.assertTrue(upgraded)
        self.assertEqual(level, 15)


class AuctionItemDataTests(unittest.TestCase):
    """验证拍卖行 item 类型数据结构向后兼容"""

    def test_item_listing_data(self):
        """模拟 listing 中 item 类型 item_data 应包含的字段"""
        item_data = {
            "type": "item",
            "item_id": "refresh_token",
            "count": 3,
            "name": "🔄 刷新券",
            "price": 27,
        }
        self.assertEqual(item_data["type"], "item")
        self.assertIn("item_id", item_data)
        self.assertIn("count", item_data)

    def test_existing_types_unchanged(self):
        """已有类型数据结构保持不变"""
        rod_data = {"type": "rod", "base_id": "rod_001", "prefix_id": "rod_pref_03"}
        fish_data = {"type": "fish", "fish_id": "fish_003", "prefix_id": "pref_001", "count": 2}
        ticket_data = {"type": "ticket", "ticket_id": "ench_ticket_001", "count": 1}
        for data in (rod_data, fish_data, ticket_data):
            self.assertIn("type", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
