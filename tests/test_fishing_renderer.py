"""钓鱼结算专用图片视图测试。"""

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


sys.modules.get(f"{PACKAGE_NAME}.fish_data") or _load_module(
    f"{PACKAGE_NAME}.fish_data", "fish_data.py"
)
renderer = _load_module(f"{PACKAGE_NAME}.fishing_renderer", "fishing_renderer.py")


class MockResearchUser:
    def __init__(self, research=None, spendable=40000):
        self.research = research or {}
        self.spendable = spendable

    def get_research(self):
        return dict(self.research)

    def get_spendable_exp(self):
        return self.spendable


class FishingRendererTests(unittest.TestCase):
    """覆盖普通垂钓、折叠渔获、贪婪和失败分支。"""

    def test_normal_result_builds_fishes_stats_events_and_notices(self):
        text = """🎣 钓鱼成功！
✨ 双倍钓鱼！ 🌾 丰收触发！

  [1] ⭐金色的龙鱼
  💰 售价: 1500 金币
  [2] 蓝色的鱿鱼
  💰 售价: 112 金币
📈 经验 +88（含神慧+40%）
⏰ 冷却 2小时18分钟 ⚡-45%
🐟 累计钓鱼 4602 次

🎫 额外获得: 传说的附魔券 x1！"""
        view = renderer.build_fishing_result_view(text, "奶小柒")
        self.assertEqual(view["kind"], "success")
        self.assertEqual([fish["name"] for fish in view["fishes"]], ["金色的龙鱼", "蓝色的鱿鱼"])
        self.assertEqual(view["stats"][0]["value"], "1,612 金币")
        self.assertEqual(view["stats"][1]["value"], "+88")
        self.assertEqual(view["stats"][3]["value"], "4,602 次")
        self.assertEqual(len(view["events"]), 2)
        self.assertIn("额外获得", view["notices"][0])

    def test_folded_common_result_and_pig_noise_are_supported(self):
        text = """🎣 钓鱼成功！

🔹 常见鱼 x8 (合计 120 金币)
🌟古龙收哼藏的北海巨妖 💰57600
📈 经验 +120
⏰ 冷却 无需冷却 🌊
🐟 累计钓鱼 100 次"""
        view = renderer.build_fishing_result_view(text, "玩家")
        self.assertEqual(view["fishes"][0]["count"], "8")
        self.assertEqual(view["fishes"][1]["name"], "古龙收藏的北海巨妖")
        self.assertTrue(view["fishes"][1]["ancient"])
        self.assertEqual(view["stats"][0]["value"], "57,720 金币")

    def test_greedy_start_continue_and_cashout(self):
        start = """🎣 钓鱼成功！
💰 无尽贪婪钓竿发出声音
🧿 你将 4 条渔获揉碎融合为【深紫结晶】
💎 结晶基础价值: 1880 金币
📈 结晶基础经验: 240"""
        start_view = renderer.build_fishing_result_view(start, "玩家")
        self.assertEqual(start_view["kind"], "greedy")
        self.assertEqual(start_view["stats"][0]["value"], "4 条")
        self.assertEqual(start_view["stats"][1]["value"], "1,880 金币")

        continued = """🎣 第 3 层贪婪成功！
🐟 额外钓上: ⭐金色的龙鱼 💰1500
🧿 【深紫结晶】已膨胀至 8890 金币（5 条渔获聚合）
📈 当前累计经验: 660
⚠️ 下次断线概率: 32%"""
        continue_view = renderer.build_fishing_result_view(continued, "玩家")
        self.assertEqual(continue_view["stats"][0]["value"], "3")
        self.assertEqual(continue_view["fishes"][0]["name"], "金色的龙鱼")
        self.assertEqual(continue_view["stats"][3]["value"], "32%")

        cashout = """🎣 收杆成功！贪欲结晶稳稳落入你的背包...
🧿 结算层数: 3
💰 +8890 金币
📈 +660 经验
⏰ 冷却 2小时"""
        cashout_view = renderer.build_fishing_result_view(cashout, "玩家")
        self.assertEqual(cashout_view["kind"], "cashout")
        self.assertEqual(cashout_view["stats"][1]["value"], "+8,890")

    def test_failure_and_warning_results_remain_readable(self):
        failed = renderer.build_fishing_result_view(
            "💥 钓鱼失败！钓竿太不稳定了...\n⏰ 冷却 2小时", "<玩家>",
        )
        self.assertEqual(failed["kind"], "failure")
        self.assertEqual(failed["user_name"], "&lt;玩家&gt;")
        self.assertIn("冷却", failed["raw_lines"][0])

        warning = renderer.build_fishing_result_view("钓鱼冷却中，剩余 12分钟", "玩家")
        self.assertEqual(warning["kind"], "warning")
        self.assertEqual(warning["title"], "钓鱼冷却中")
        self.assertEqual(warning["subtitle"], "剩余 12分钟")

    def test_research_card_builds_compact_progress_data(self):
        state = {
            "target_type": "combo", "target_name": "神话的北海巨妖",
            "remaining": 21, "total": 30,
        }
        view = renderer.build_research_view(
            MockResearchUser(state, 60000), "🔬 正在研究：北海巨妖", "奶小柒",
        )
        self.assertEqual(view["kind"], "active")
        self.assertEqual(view["research"]["percent"], 30)
        self.assertEqual(view["research"]["target_type"], "图鉴组合")
        self.assertEqual(view["available_exp"], "60,000")
        self.assertEqual(view["research"]["multiplier"], "8.5 倍")

    def test_all_fishing_result_kinds_include_active_research(self):
        state = {
            "target_type": "prefix", "target_name": "神话的",
            "remaining": 10, "total": 25,
        }
        samples = [
            "🎣 钓鱼成功！\n普通的小杂鱼 💰5\n📈 经验 +10\n⏰ 冷却 1小时",
            "🎣 第 2 层贪婪成功！\n🐟 额外钓上: 普通的小杂鱼 💰5\n🧿 【结晶】已膨胀至 20 金币（2 条渔获聚合）\n📈 当前累计经验: 20\n⚠️ 下次断线概率: 20%",
            "🎣 收杆成功！\n🧿 结算层数: 2\n💰 +20 金币\n📈 +20 经验\n⏰ 冷却 1小时",
            "钓鱼冷却中，剩余 12分钟",
        ]
        for text in samples:
            with self.subTest(text=text.splitlines()[0]):
                view = renderer.build_fishing_result_view(text, "玩家", state)
                self.assertEqual(view["research"]["target"], "神话的")
                self.assertEqual(view["research"]["percent"], 60)

    def test_completed_research_is_visible_without_active_state(self):
        text = "🎣 钓鱼成功！\n🔬 研究完成！成功发现目标“北海巨妖”"
        view = renderer.build_fishing_result_view(text, "玩家")
        self.assertTrue(view["research"]["completed"])
        self.assertEqual(view["research"]["percent"], 100)

    def test_template_has_dedicated_fish_and_stat_cards(self):
        template = renderer.FISHING_IMAGE_TEMPLATE
        self.assertIn("fish-grid", template)
        self.assertIn("fish-grid.dense", template)
        self.assertIn("fishes|length <= 4", template)
        self.assertIn("body.greedy .stats", template)
        self.assertIn("font-size: 36px", template)
        self.assertIn("kind != 'warning'", template)
        self.assertIn("body.warning .subtitle", template)
        self.assertIn("stat-value", template)
        self.assertIn("hidden_fishes", template)
        self.assertIn("research-track", template)
        self.assertIn("research-fill", template)
        self.assertIn("当前加成", renderer.RESEARCH_IMAGE_TEMPLATE)
        self.assertIn("min-height: 64px", template)
        self.assertIn("RESEARCH_IMAGE_TEMPLATE", dir(renderer))


if __name__ == "__main__":
    unittest.main(verbosity=2)
