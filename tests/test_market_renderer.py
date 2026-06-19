"""商店与拍卖行专用图片视图测试。"""

import importlib.util
import os
import sys
import time
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


sys.modules.get(f"{PACKAGE_NAME}.fish_data") or _load_module(
    f"{PACKAGE_NAME}.fish_data", "fish_data.py"
)
models = sys.modules.get(f"{PACKAGE_NAME}.models") or _load_module(
    f"{PACKAGE_NAME}.models", "models.py"
)
renderer = _load_module(f"{PACKAGE_NAME}.market_renderer", "market_renderer.py")

UserData = models.UserData


class MarketRendererTests(unittest.TestCase):
    """覆盖市场图片中的价格、分页、时间和动态文本边界。"""

    def test_shop_view_builds_types_skills_and_affordability(self):
        user = UserData("shop_user")
        user._data["coins"] = 500
        user._data["shop_level"] = 2
        user._data["current_shop"] = [
            {
                "type": "rod", "base_id": "rod_002", "prefix_id": "rod_pref_11",
                "price": 300,
            },
            {
                "type": "bait", "base_id": "bait_001", "prefix_id": "bait_pref_01",
                "quantity": 5, "price": 800,
            },
            {
                "type": "directed_enchant", "name": "定向附魔券[⚡迅捷+15%]",
                "price": 450,
            },
        ]

        view = renderer.build_shop_view(user, "测试玩家")
        self.assertEqual(view["slot_count"], 10)
        self.assertEqual(view["coins"], "500")
        self.assertTrue(view["items"][0]["affordable"])
        self.assertFalse(view["items"][1]["affordable"])
        self.assertEqual(view["items"][1]["quantity"], "5")
        self.assertNotIn("[", view["items"][2]["name"])
        skill_names = [skill["name"] for skill in view["items"][0]["skills"]]
        self.assertIn("🌾丰收", skill_names)

    def test_shop_view_escapes_player_and_item_name(self):
        user = UserData("shop_user")
        user._data["current_shop"] = [
            {"type": "directed_enchant", "name": "<迅捷>", "price": 10},
        ]
        view = renderer.build_shop_view(user, "<script>玩家</script>")
        self.assertEqual(view["user_name"], "&lt;script&gt;玩家&lt;/script&gt;")
        self.assertEqual(view["items"][0]["name"], "&lt;迅捷&gt;")

    def test_auction_view_formats_page_owner_time_and_quantity(self):
        now = int(time.time())
        listings = [{
            "id": "auc_100_1",
            "seller_id": "viewer",
            "seller_name": "奶小柒",
            "type": "bait",
            "price": 12345,
            "expires_at": now + 3660,
            "item_data": {
                "type": "bait", "base_id": "bait_001", "prefix_id": "bait_pref_01",
                "count": 12,
            },
        }]
        view = renderer.build_auction_view(
            listings, total=23, page=2, viewer_id="viewer", now=now,
        )
        self.assertEqual(view["total_pages"], 3)
        self.assertTrue(view["listings"][0]["own"])
        self.assertEqual(view["listings"][0]["price"], "12,345")
        self.assertEqual(view["listings"][0]["quantity"], "12")
        self.assertEqual(view["listings"][0]["remaining"], "1小时1分")

    def test_auction_search_and_rod_details_are_rendered(self):
        listing = {
            "id": "<auc>", "seller_id": "seller", "seller_name": "<卖家>",
            "price": 999, "expires_at": 2000,
            "item_data": {
                "type": "rod", "base_id": "rod_002", "prefix_id": "rod_pref_11",
                "skills": {"swift": 0.45}, "enchant_count": 7,
            },
        }
        view = renderer.build_auction_view(
            [listing], total=1, keyword="古龙", now=1000,
        )
        item = view["listings"][0]
        self.assertEqual(view["title"], "拍卖行搜索")
        self.assertEqual(item["enhancement"], "+7")
        self.assertEqual(item["id"], "&lt;auc&gt;")
        self.assertEqual(item["seller"], "&lt;卖家&gt;")
        skills = {skill["name"]: skill["value"] for skill in item["skills"]}
        self.assertEqual(skills["⚡迅捷"], "45%")
        self.assertEqual(skills["🌾丰收"], "20%")

    def test_templates_use_cards_without_bracket_ids(self):
        self.assertIn("grid-template-columns:repeat(3", renderer.SHOP_IMAGE_TEMPLATE)
        self.assertIn("grid-template-columns:repeat(2", renderer.AUCTION_IMAGE_TEMPLATE)
        self.assertIn("编号 {{ item.id }}", renderer.AUCTION_IMAGE_TEMPLATE)
        self.assertNotIn("[{{ item.id }}]", renderer.AUCTION_IMAGE_TEMPLATE)
        self.assertIn("金币不足", renderer.SHOP_IMAGE_TEMPLATE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
