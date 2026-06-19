"""背包专用图片视图测试。"""

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
renderer = _load_module(f"{PACKAGE_NAME}.backpack_renderer", "backpack_renderer.py")

UserData = models.UserData


def make_user() -> UserData:
    user = UserData("preview_user")
    user._data["level"] = 8
    user._data["exp"] = 36420
    user._data["coins"] = 128650
    user._data["total_fish_count"] = 1286
    user._data["owned_rods"] = []
    current_id = user.add_rod(
        "rod_004", "rod_pref_11", {"swift": 0.45, "lucky": 0.25}, 7, "rod_current"
    )
    user.add_rod("rod_006", "", {}, 0, "rod_gold")
    user.equip_rod(current_id)
    return user


class BackpackViewTests(unittest.TestCase):
    """结构化背包数据边界测试。"""

    def test_experience_uses_current_level_interval(self):
        view = renderer.build_backpack_view(make_user(), "示例玩家")
        # Lv.8 区间为 20,000 到 50,000，36,420 对应约 54.73%。
        self.assertAlmostEqual(view["exp"]["percent"], 54.73, places=2)
        self.assertEqual(view["exp"]["text"], "36,420 / 50,000")

    def test_current_rod_card_has_enhancement_and_effective_skills(self):
        view = renderer.build_backpack_view(make_user(), "示例玩家")
        current = view["rods"][0]
        self.assertTrue(current["current"])
        self.assertEqual(current["enhancement"], "+7")
        self.assertEqual(current["name"], "古龙收藏的金色钓竿")
        skill_values = {skill["name"]: skill["value"] for skill in current["skills"]}
        self.assertEqual(skill_values["⚡迅捷"], "45%")
        self.assertEqual(skill_values["🍀幸运"], "25%")
        # 前缀原生技能不能因实例技能字典不完整而丢失。
        self.assertEqual(skill_values["🌾丰收"], "20%")

    def test_special_rod_name_has_no_fake_normal_prefix(self):
        view = renderer.build_backpack_view(make_user(), "示例玩家")
        self.assertEqual(view["rods"][1]["name"], "金币钓竿")

    def test_fish_inventory_caps_at_sixty(self):
        user = make_user()
        entries = []
        combinations = [
            (fish["id"], prefix["id"])
            for fish in fish_data.FISH_TYPES
            for prefix in fish_data.FISH_PREFIXES
        ]
        for index, (fish_id, prefix_id) in enumerate(combinations[:67]):
            entries.append({
                "fish_id": fish_id,
                "prefix_id": prefix_id,
                "count": index + 1,
                "obtained_at": index,
            })
        user._data["fish_inventory"] = entries

        fishes = renderer.build_backpack_view(user, "示例玩家")["fishes"]
        self.assertEqual(len(fishes["items"]), 60)
        self.assertEqual(fishes["hidden_count"], 7)
        self.assertEqual(fishes["total_types"], 67)

    def test_fishes_are_sorted_by_stack_value_descending(self):
        user = make_user()
        user._data["fish_inventory"] = [
            {"fish_id": "fish_001", "prefix_id": "pref_001", "count": 1},
            {"fish_id": "fish_011", "prefix_id": "pref_007", "count": 1},
            {"fish_id": "fish_003", "prefix_id": "pref_001", "count": 100},
        ]
        items = renderer.build_backpack_view(user, "示例玩家")["fishes"]["items"]
        # 金色龙鱼 1500，100 条普通鲤鱼同为 1500；同价值时传说鱼优先。
        self.assertEqual(items[0]["name"], "金色的龙鱼")
        self.assertEqual(items[1]["name"], "普通的鲤鱼")
        self.assertEqual(items[2]["name"], "普通的小杂鱼")

    def test_small_real_inventory_keeps_value_order(self):
        user = make_user()
        user._data["fish_inventory"] = [
            {"fish_id": "fish_028", "prefix_id": "pref_001", "count": 2},
            {"fish_id": "fish_025", "prefix_id": "pref_006", "count": 1},
            {"fish_id": "fish_007", "prefix_id": "pref_005", "count": 1},
            {"fish_id": "fish_008", "prefix_id": "pref_001", "count": 1},
        ]
        fishes = renderer.build_backpack_view(user, "奶小柒")["fishes"]
        self.assertEqual([item["name"] for item in fishes["items"]], [
            "蓝色的鱿鱼", "红色的鲈鱼", "普通的海星", "普通的鳜鱼",
        ])

    def test_dynamic_text_is_escaped_and_ids_are_not_exposed(self):
        user = make_user()
        user.add_fish("fish_007", "pref_004", 2)
        view = renderer.build_backpack_view(user, "<script>玩家</script>")
        self.assertEqual(view["user_name"], "&lt;script&gt;玩家&lt;/script&gt;")
        self.assertNotIn("fish_007", str(view["fishes"]["items"]))

    def test_template_removes_old_branding_and_square_bracket_style(self):
        template = renderer.BACKPACK_IMAGE_TEMPLATE
        self.assertNotIn("深海回响", template)
        self.assertNotIn("ASTRBOT FISHING GAME", template)
        self.assertIn("{{ user_name }}", template)
        self.assertIn("还有 {{ fishes.hidden_count }} 条渔获未展示", template)
        self.assertIn('class="chip fish-chip"', template)
        self.assertNotIn('class="fish-grid"', template)

    def test_myrods_view_keeps_indices_price_warning_and_current_state(self):
        user = make_user()
        arrogant_id = user.add_rod(
            "rod_005", "rod_pref_17",
            {"treasure": 0.25, "tide": 0.12, "exp_boost": 0.18, "mending": 0.26},
            4, "rod_arrogant",
        )
        user.equip_rod(arrogant_id)

        view = renderer.build_rods_view(user, "真实玩家")
        self.assertEqual([rod["index"] for rod in view["rods"]], [1, 2, 3])
        self.assertFalse(view["rods"][0]["current"])
        self.assertTrue(view["rods"][2]["current"])
        self.assertTrue(view["rods"][2]["enchant_price"])
        self.assertIn("槽位已满", view["rods"][2]["warning"])
        self.assertNotIn("[当前]", str(view))

    def test_myrods_template_has_card_specific_details(self):
        template = renderer.RODS_IMAGE_TEMPLATE
        self.assertIn("第 {{ rod.index }} 根", template)
        self.assertIn("{{ rod.enchant_price }} 金币", template)
        self.assertIn("{{ rod.warning }}", template)
        self.assertIn("current-badge", template)


if __name__ == "__main__":
    unittest.main(verbosity=2)
