"""鱼饵、图鉴与成就专用图片视图测试。"""

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
    path = os.path.join(PROJECT_ROOT, file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


fish_data = sys.modules.get(f"{PACKAGE_NAME}.fish_data") or _load_module(
    f"{PACKAGE_NAME}.fish_data", "fish_data.py"
)
models = sys.modules.get(f"{PACKAGE_NAME}.models") or _load_module(
    f"{PACKAGE_NAME}.models", "models.py"
)
renderer = _load_module(f"{PACKAGE_NAME}.gallery_renderer", "gallery_renderer.py")

UserData = models.UserData


class GalleryRendererTests(unittest.TestCase):
    """覆盖三类页面的数据边界、排序与动态文本安全。"""

    def test_baits_view_keeps_original_indices_and_sorts_current_first(self):
        user = UserData("bait_user")
        user._data["baits"] = []
        user.add_bait("bait_001", "bait_pref_02", 481)
        user.add_bait("bait_004", "bait_pref_09", 3)
        user.add_bait("bait_003", "bait_pref_06", 8)
        user.equip_bait("bait_004", "bait_pref_09")

        view = renderer.build_baits_view(user, "奶小柒")
        self.assertEqual(view["total_types"], 3)
        self.assertEqual(view["total_count"], "492")
        self.assertTrue(view["items"][0]["current"])
        self.assertEqual(view["items"][0]["index"], 2)
        self.assertEqual(view["items"][0]["name"], "古龙收藏的传说饵")
        effects = {item["name"]: item["value"] for item in view["items"][0]["effects"]}
        self.assertEqual(effects["经验"], "×5.60")
        self.assertEqual(effects["稀有加成"], "+56%")
        self.assertEqual(effects["奇遇"], "+20%")

    def test_collection_view_uses_real_capacity_rarity_totals_and_recent_limit(self):
        user = UserData("collection_user")
        user._data["collection"] = {
            "fish_001#pref_001": {"count": 4, "first_at": 100},
            "fish_011#pref_007": {"count": 2, "first_at": 300},
            "fish_034#pref_014": {"count": 1, "first_at": 200},
            "broken-key": {"count": 99, "first_at": 999},
        }
        view = renderer.build_collection_view(user, "玩家", recent_limit=2)
        self.assertEqual(view["total"], len(fish_data.FISH_TYPES) * len(fish_data.FISH_PREFIXES))
        self.assertEqual(view["collected"], 4)
        self.assertEqual(len(view["recent"]), 2)
        self.assertEqual(view["recent"][0]["name"], "金色的龙鱼")
        self.assertEqual(view["recent"][1]["name"], "古龙收藏的巨型章鱼")
        self.assertTrue(view["recent"][1]["ancient"])
        stats = {item["rarity"]: item for item in view["rarities"]}
        common_fish_count = sum(1 for fish in fish_data.FISH_TYPES if fish["rarity"] == "common")
        self.assertEqual(stats["common"]["total"], common_fish_count * len(fish_data.FISH_PREFIXES))

    def test_achievements_view_contains_all_groups_and_caps_progress(self):
        user = UserData("achievement_user")
        user._data["total_fish_count"] = 4602
        user._data["coins"] = 4910
        user._data["level"] = 11
        user._data["rarity_catch_count"] = {
            "common": 3000, "rare": 400, "legendary": 80, "mythic": 12,
        }
        user._data["achievements"] = ["first_fish", "novice_angler", "level_3"]

        view = renderer.build_achievements_view(user, "奶小柒")
        self.assertEqual(view["total"], len(fish_data.ACHIEVEMENTS))
        self.assertEqual(len(view["groups"]), 9)
        all_items = [item for group in view["groups"] for item in group["items"]]
        self.assertEqual(len(all_items), len(fish_data.ACHIEVEMENTS))
        first_fish = next(item for item in all_items if item["name"] == "初出茅庐")
        self.assertTrue(first_fish["done"])
        self.assertEqual(first_fish["percent"], 100.0)
        self.assertEqual(first_fish["current"], "1")

    def test_dynamic_names_are_escaped(self):
        user = UserData("safe_user")
        self.assertEqual(
            renderer.build_baits_view(user, "<玩家>")["user_name"], "&lt;玩家&gt;",
        )
        self.assertEqual(
            renderer.build_collection_view(user, "<玩家>")["user_name"], "&lt;玩家&gt;",
        )
        self.assertEqual(
            renderer.build_achievements_view(user, "<玩家>")["user_name"], "&lt;玩家&gt;",
        )

    def test_templates_have_expected_card_density(self):
        self.assertIn("grid-template-columns:repeat(3", renderer.BAITS_IMAGE_TEMPLATE)
        self.assertIn("grid-template-columns:repeat(4", renderer.COLLECTION_IMAGE_TEMPLATE)
        self.assertIn("最近点亮", renderer.COLLECTION_IMAGE_TEMPLATE)
        self.assertIn("body{width:1560px", renderer.ACHIEVEMENTS_IMAGE_TEMPLATE)
        self.assertIn("grid-template-columns:repeat(4", renderer.ACHIEVEMENTS_IMAGE_TEMPLATE)
        self.assertIn("achievement.reward_coins", renderer.ACHIEVEMENTS_IMAGE_TEMPLATE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
