"""贪婪机制测试（无需完整 AstrBot 环境）

验证贪欲结晶状态机、倍率/断线计算、继续/收杆命令等核心逻辑。
"""
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 构造一个空父包
_pkg = types.ModuleType("astrbot_plugin_fishing_game")
_pkg.__path__ = [PROJECT_ROOT]
sys.modules["astrbot_plugin_fishing_game"] = _pkg


def _load_module(module_name: str, file_name: str):
    path = os.path.join(PROJECT_ROOT, file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# 按依赖顺序加载
_load_module("astrbot_plugin_fishing_game.fish_data", "fish_data.py")
_load_module("astrbot_plugin_fishing_game.models", "models.py")
_load_module("astrbot_plugin_fishing_game.utils", "utils.py")
_load_module("astrbot_plugin_fishing_game.storage", "storage.py")
_load_module("astrbot_plugin_fishing_game.commands_base", "commands_base.py")
command_fishing = _load_module("astrbot_plugin_fishing_game.command_fishing", "command_fishing.py")

from astrbot_plugin_fishing_game.models import UserData
from astrbot_plugin_fishing_game.command_fishing import FishingCommands, GREEDY_CONFIG
from astrbot_plugin_fishing_game.fish_data import (
    get_rod_prefix, calc_rod_value, SPECIAL_PREFIX_BALANCE, SPECIAL_ROD_BALANCE,
)
from astrbot_plugin_fishing_game.utils import calc_enchant_price


class MockStar:
    fishing_cooldown = 14400


class MockStorage:
    def __init__(self):
        self.users = {}
        self.user_locks = {}

    def get_user_lock(self, user_id: str):
        if user_id not in self.user_locks:
            import asyncio
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]

    async def get_user(self, user_id: str):
        if user_id not in self.users:
            self.users[user_id] = UserData(user_id)
        return self.users[user_id]

    async def save_user(self, user):
        self.users[user.user_id] = user

    async def add_user_to_leaderboard(self, *args, **kwargs):
        pass


def make_event(user_id="u1", name="Test"):
    ev = MagicMock()
    ev.get_sender_id.return_value = user_id
    ev.get_sender_name.return_value = name
    return ev


def make_rod(prefix_id="rod_pref_12", instance_id="inst_rod_1"):
    return {
        "base_id": "rod_001",
        "prefix_id": prefix_id,
        "instance_id": instance_id,
        "enchant_count": 0,
        "skills": {},
    }


class GreedyStateMachineTests(unittest.TestCase):
    """UserData 贪婪状态机方法"""

    def test_start_and_active(self):
        user = UserData("u1")
        chip = {"name": "贪欲结晶", "total_price": 100, "total_exp": 10, "fish_count": 1}
        user.start_greedy("inst_1", "rod_pref_12", {"base_id": "bait_001", "prefix_id": "bait_pref_02"}, chip, 2)
        self.assertTrue(user.is_greedy_active())
        self.assertEqual(user.greedy_state["stack"], 1)
        self.assertEqual(user.greedy_state["bait_cost_total"], 2)

    def test_update_greedy_chip(self):
        user = UserData("u1")
        chip = {"name": "贪欲结晶", "total_price": 100, "total_exp": 10, "fish_count": 1}
        user.start_greedy("inst_1", "rod_pref_12", {}, chip, 2)
        new_chip = {"name": "贪欲结晶", "total_price": 300, "total_exp": 30, "fish_count": 2}
        self.assertTrue(user.update_greedy_chip(new_chip, bait_cost_delta=0, stack_delta=1))
        self.assertEqual(user.greedy_state["stack"], 2)
        self.assertEqual(user.greedy_state["chip"]["total_price"], 300)

    def test_clear_greedy(self):
        user = UserData("u1")
        chip = {"name": "贪欲结晶", "total_price": 100, "total_exp": 10, "fish_count": 1}
        user.start_greedy("inst_1", "rod_pref_12", {}, chip, 2)
        old = user.clear_greedy()
        self.assertIsNotNone(old)
        self.assertFalse(user.is_greedy_active())
        self.assertIsNone(user.greedy_state)

    def test_update_without_active_returns_false(self):
        user = UserData("u1")
        self.assertFalse(user.update_greedy_chip({}, stack_delta=1))

    def test_add_coins_rejects_negative(self):
        user = UserData("u1")
        self.assertFalse(user.add_coins(-100))
        self.assertEqual(user.coins, 100)  # 默认值不变


class GreedyPureLogicTests(unittest.TestCase):
    """不依赖实例状态或 I/O 的纯函数逻辑"""

    def test_build_chip_aggregates(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        results = [
            {"fish_name": "普通草鱼", "price": 10, "exp": 5, "fish_id": "fish_001", "prefix_id": "pref_001", "rarity": "common"},
            {"fish_name": "稀有鲤鱼", "price": 50, "exp": 15, "fish_id": "fish_002", "prefix_id": "pref_002", "rarity": "rare"},
        ]
        chip = cmds._build_greedy_chip(results)
        self.assertEqual(chip["total_price"], 60)
        self.assertEqual(chip["total_exp"], 20)
        self.assertEqual(chip["fish_count"], 2)
        self.assertEqual(chip["max_rarity"], "rare")
        self.assertEqual(chip["rarity_counts"]["common"], 1)
        self.assertEqual(chip["rarity_counts"]["rare"], 1)

    def test_multiplier_tables(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        # stack=1 使用首层保底收益倍率
        self.assertEqual(cmds._get_greedy_total_multiplier(1, "normal"), 1.2)
        self.assertEqual(cmds._get_greedy_total_multiplier(1, "endless"), 1.4)
        # stack=2 对应表第一项
        self.assertEqual(cmds._get_greedy_total_multiplier(2, "normal"), 1.55)
        self.assertEqual(cmds._get_greedy_total_multiplier(2, "endless"), 1.9)
        # stack=3
        self.assertEqual(cmds._get_greedy_total_multiplier(3, "normal"), 2.05)
        self.assertEqual(cmds._get_greedy_total_multiplier(3, "endless"), 2.7)

    def test_multiplier_extrapolation(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        # normal 表长度 10，对应 stack 2..11；stack=12 应线性外推
        expected = 9.65 + (9.65 - 8.35)  # last + step
        self.assertAlmostEqual(cmds._get_greedy_total_multiplier(12, "normal"), expected)

    def test_extra_rarity_bonus(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        self.assertEqual(cmds._get_greedy_extra_rarity_bonus(1, "normal"), 0.0)
        self.assertEqual(cmds._get_greedy_extra_rarity_bonus(3, "normal"), 0.16)
        self.assertEqual(cmds._get_greedy_extra_rarity_bonus(3, "endless"), 0.20)

    def test_break_chance_stack_and_fish_count(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        # stack=1, 1条鱼：仅基础概率
        self.assertEqual(cmds._calc_greedy_break_chance(1, 1, "normal"), 0.15)
        self.assertEqual(cmds._calc_greedy_break_chance(1, 1, "endless"), 0.22)
        # stack=2, 1条鱼：基础+一层增量
        self.assertEqual(cmds._calc_greedy_break_chance(2, 1, "normal"), 0.27)
        self.assertEqual(cmds._calc_greedy_break_chance(2, 1, "endless"), 0.36)
        # stack=1, 3条鱼：基础 + 2*0.06
        self.assertAlmostEqual(cmds._calc_greedy_break_chance(1, 3, "normal"), 0.27, places=5)
        # 丰收/远航产生大量首轮渔获时，额外鱼数风险最多按 3 条计算。
        self.assertAlmostEqual(cmds._calc_greedy_break_chance(1, 100, "normal"), 0.27, places=5)
        # 封顶 95%
        self.assertEqual(cmds._calc_greedy_break_chance(100, 1000, "normal"), 0.95)

    def test_repair_cost_is_capped_by_chip_value(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        # 富裕玩家不再按总资产无限放大损失：2% 钱包费用受结晶价值 10% 封顶。
        self.assertEqual(cmds._calc_greedy_repair_cost(1_000_000, 1_000, "normal"), 100)

    def test_repair_cost_uses_wallet_rate_for_low_balance(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        self.assertEqual(cmds._calc_greedy_repair_cost(1_000, 10_000, "endless"), 20)
        self.assertEqual(cmds._calc_greedy_repair_cost(0, 10_000, "normal"), 0)

    def test_greedy_cooldown_uses_initial_effect_snapshot(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        state = {"effects": {"swift": 0.50, "tide_triggered": False, "voyage_extra_cd": 0}}
        expected = int(MockStar.fishing_cooldown * 0.50 * 1.15)
        self.assertEqual(cmds._get_greedy_effective_cooldown(state, "normal"), expected)
        state["effects"]["tide_triggered"] = True
        self.assertEqual(cmds._get_greedy_effective_cooldown(state, "normal"), 0)


class SpecialPrefixBalanceTests(unittest.TestCase):
    """特殊前缀的数值护栏。"""

    def test_special_prefix_power_budgets(self):
        expected = {
            "rod_pref_12": (1.6, 4),
            "rod_pref_19": (1.9, 5),
            "rod_pref_13": (0.9, 5),
            "rod_pref_14": (1.35, 3),
            "rod_pref_15": (0.85, 2),
            "rod_pref_16": (1.4, 6),
            "rod_pref_17": (1.8, 4),
            "rod_pref_18": (1.7, 4),
        }
        for prefix_id, (multiplier, max_slots) in expected.items():
            prefix = get_rod_prefix(prefix_id)
            self.assertEqual(prefix["multiplier"], multiplier)
            self.assertEqual(prefix["max_slots"], max_slots)

    def test_cursed_enchant_discount_is_bounded(self):
        rod = {
            "base_id": "rod_004", "prefix_id": "rod_pref_13",
            "skills": {}, "enchant_count": 0,
        }
        normal_base_price = int(calc_rod_value("rod_004", "rod_pref_13", {}) * 0.30)
        expected = int(normal_base_price * SPECIAL_PREFIX_BALANCE["cursed"]["enchant_price_multiplier"])
        self.assertEqual(calc_enchant_price(rod), expected)
        self.assertGreaterEqual(SPECIAL_PREFIX_BALANCE["cursed"]["enchant_price_multiplier"], 0.30)

    def test_marker_and_penalty_skills_do_not_inflate_value(self):
        plain_value = calc_rod_value("rod_004", "rod_pref_12", {})
        marker_value = calc_rod_value(
            "rod_004", "rod_pref_12", {"greedy": 1.0, "fail_chance": 0.50}
        )
        boosted_value = calc_rod_value("rod_004", "rod_pref_12", {"lucky": 0.20})
        self.assertEqual(marker_value, plain_value)
        self.assertEqual(boosted_value, int(plain_value * 1.20))

    def test_gold_rod_uses_sustainable_fixed_cost(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        self.assertEqual(cmds._calc_gold_rod_cast_cost(), 10)
        self.assertEqual(SPECIAL_ROD_BALANCE["gold_rod"]["treasure_chance"], 0.15)

    def test_lucky_block_has_positive_long_term_bias(self):
        cfg = SPECIAL_PREFIX_BALANCE["lucky_block"]
        self.assertGreater(cfg["gain_chance"], cfg["lose_chance"])
        self.assertGreaterEqual(cfg["new_skill_min"], 0.12)
        self.assertLessEqual(cfg["skill_value_cap"], 0.25)

    def test_arrogant_pool_keeps_rare_fish(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        user = UserData("u1")
        user._data["level"] = 10
        rod = {"base_id": "rod_004", "prefix_id": "rod_pref_17", "skills": {}}
        bait = {"base_id": "bait_003", "prefix_id": "bait_pref_02"}
        captured_fish = []

        def choose_first(sequence, **kwargs):
            if sequence and isinstance(sequence[0], tuple):
                candidates = [entry[0] for entry in sequence]
                if candidates[0].get("id", "").startswith("fish_"):
                    captured_fish.extend(candidates)
            return [sequence[0]]

        with patch("random.choices", side_effect=choose_first):
            result = cmds._do_fish_once(user, rod, bait)

        self.assertIsNotNone(result)
        self.assertTrue(captured_fish)
        self.assertTrue(all(fish["rarity"] != "common" for fish in captured_fish))
        self.assertTrue(any(fish["rarity"] == "rare" for fish in captured_fish))


class GreedyCommandFlowTests(unittest.IsolatedAsyncioTestCase):
    """完整的继续/收杆命令流程"""

    async def test_cashout_no_state(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        ev = make_event()
        result = await cmds.cmd_greedy_cashout(ev)
        self.assertIn("没有挂起的贪婪状态", result)

    async def test_continue_no_state(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        ev = make_event()
        result = await cmds.cmd_greedy_continue(ev)
        self.assertIn("没有挂起的贪婪状态", result)

    async def test_cashout_success(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        storage = cmds.storage
        user = await storage.get_user("u1")
        user._data["current_rod"] = make_rod("rod_pref_12")
        chip = {"name": "贪欲结晶", "total_price": 500, "total_exp": 50, "fish_count": 2,
                "rarity_counts": {"common": 1, "rare": 1, "legendary": 0, "mythic": 0}, "max_rarity": "rare", "details": []}
        user.start_greedy("inst_rod_1", "rod_pref_12", {}, chip, 2)

        result = await cmds.cmd_greedy_cashout(make_event())
        self.assertIn("收杆成功", result)
        self.assertIn("+500 金币", result)
        self.assertIn("+50 经验", result)
        self.assertFalse(user.is_greedy_active())
        self.assertEqual(user.coins, 600)  # 默认 100 + 500
        self.assertGreater(user.fish_cooldown, 0)

    async def test_continue_break(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        user = await cmds.storage.get_user("u1")
        user._data["current_rod"] = make_rod("rod_pref_12")
        user.add_coins(900)  # 总共 1000
        chip = {"name": "贪欲结晶", "total_price": 500, "total_exp": 50, "fish_count": 1,
                "rarity_counts": {"common": 1, "rare": 0, "legendary": 0, "mythic": 0}, "max_rarity": "common", "details": []}
        user.start_greedy("inst_rod_1", "rod_pref_12", {}, chip, 2)

        with patch("random.random", return_value=0.0):  # 0.0 < break_chance，必定断线
            result = await cmds.cmd_greedy_continue(make_event())
        self.assertIn("断线", result)
        self.assertIn("修理鱼竿花费", result)
        self.assertFalse(user.is_greedy_active())
        self.assertEqual(user.coins, 980)  # 1000 的 2%，且未触及结晶价值上限

    async def test_continue_success_no_break(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        user = await cmds.storage.get_user("u1")
        user._data["level"] = 10
        user._data["current_rod"] = make_rod("rod_pref_12")
        chip = {"name": "贪欲结晶", "total_price": 100, "total_exp": 10, "fish_count": 1,
                "rarity_counts": {"common": 1, "rare": 0, "legendary": 0, "mythic": 0}, "max_rarity": "common", "details": []}
        user.start_greedy("inst_rod_1", "rod_pref_12", {}, chip, 2)

        with patch("random.random", return_value=1.0):  # 1.0 >= break_chance，必定成功
            with patch.object(cmds, "_do_fish_once", return_value={
                "fish_name": "测试鱼", "price": 20, "exp": 5,
                "fish_id": "fish_001", "prefix_id": "pref_001", "rarity": "common", "rarity_emoji": ""
            }):
                result = await cmds.cmd_greedy_continue(make_event())
        self.assertIn("第 2 层贪婪成功", result)
        self.assertTrue(user.is_greedy_active())
        # 初始 total_price=100，新鱼 price=20，按新倍率比率复利增长。
        self.assertEqual(user.greedy_state["chip"]["total_price"], 155)
        self.assertEqual(user.greedy_state["stack"], 2)

    async def test_continue_with_rod_changed_fails(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        user = await cmds.storage.get_user("u1")
        user._data["current_rod"] = make_rod("rod_pref_12", "inst_other")
        chip = {"name": "贪欲结晶", "total_price": 100, "total_exp": 10, "fish_count": 1,
                "rarity_counts": {"common": 1, "rare": 0, "legendary": 0, "mythic": 0}, "max_rarity": "common", "details": []}
        user.start_greedy("inst_rod_1", "rod_pref_12", {}, chip, 2)

        with patch("random.random", return_value=1.0):
            result = await cmds.cmd_greedy_continue(make_event())
        self.assertIn("更换了触发贪婪的钓竿", result)
        self.assertTrue(user.is_greedy_active())  # 状态冻结，未清除


class GreedyActivationFlowTests(unittest.IsolatedAsyncioTestCase):
    """钓鱼命令中贪婪模式激活路径"""

    async def test_greedy_mode_variable_resolved(self):
        """确保 cmd_fish 不会因 greedy_mode 未定义而抛出 NameError"""
        cmds = FishingCommands(MockStar(), MockStorage())
        user = await cmds.storage.get_user("u1")
        # 给用户装备普通贪婪钓竿，并补充足够鱼饵
        user._data["current_rod"] = make_rod("rod_pref_12")
        user._data["baits"] = [{"base_id": "bait_001", "prefix_id": "bait_pref_02", "count": 10}]
        user._data["current_bait"] = {"base_id": "bait_001", "prefix_id": "bait_pref_02"}
        user._data["fish_cooldown"] = 0

        with patch.object(cmds, "_do_fish_once", return_value={
            "fish_name": "测试鱼", "price": 10, "exp": 5,
            "fish_id": "fish_001", "prefix_id": "pref_001", "rarity": "common", "rarity_emoji": ""
        }):
            result = await cmds.cmd_fish(make_event())
        self.assertIn("贪欲结晶", result)
        self.assertTrue(user.is_greedy_active())

    async def test_endless_greedy_uses_endless_config(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        user = await cmds.storage.get_user("u1")
        user._data["current_rod"] = make_rod("rod_pref_19")  # 无尽贪婪
        user._data["baits"] = [{"base_id": "bait_001", "prefix_id": "bait_pref_02", "count": 10}]
        user._data["current_bait"] = {"base_id": "bait_001", "prefix_id": "bait_pref_02"}
        user._data["fish_cooldown"] = 0

        with patch.object(cmds, "_do_fish_once", return_value={
            "fish_name": "测试鱼", "price": 10, "exp": 5,
            "fish_id": "fish_001", "prefix_id": "pref_001", "rarity": "common", "rarity_emoji": ""
        }):
            result = await cmds.cmd_fish(make_event())
        self.assertIn("贪欲结晶", result)
        self.assertEqual(user.greedy_state["rod_prefix_id"], "rod_pref_19")

    async def test_all_regular_skills_apply_on_initial_greedy_cast(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        user = await cmds.storage.get_user("u1")
        rod = make_rod("rod_pref_12")
        rod["skills"] = {
            "swift": 0.25, "lucky": 1.0, "harvest": 1.0, "treasure": 1.0,
            "tide": 1.0, "exp_boost": 0.50, "mending": 1.0, "voyage": 1.0,
        }
        user._data["level"] = 10
        user._data["current_rod"] = dict(rod)
        user._data["owned_rods"] = [dict(rod)]
        user._data["baits"] = [{"base_id": "bait_001", "prefix_id": "bait_pref_02", "count": 100}]
        user._data["current_bait"] = {"base_id": "bait_001", "prefix_id": "bait_pref_02"}
        user._data["fish_cooldown"] = 0

        fixed_fish = {
            "fish_name": "测试鱼", "price": 10, "exp": 20,
            "fish_id": "fish_001", "prefix_id": "pref_001",
            "rarity": "common", "rarity_emoji": "", "desc": "",
        }
        with patch("random.random", return_value=0.0):
            with patch.object(cmds, "_do_fish_once", return_value=fixed_fish):
                result = await cmds.cmd_fish(make_event())

        state = user.greedy_state
        self.assertIsNotNone(state)
        self.assertGreater(state["chip"]["fish_count"], 2)  # 双倍、丰收与远航均已生效
        self.assertEqual(state["effects"]["swift"], 0.25)
        self.assertTrue(state["effects"]["tide_triggered"])
        self.assertGreater(state["effects"]["voyage_extra_cd"], 0)
        self.assertIn("神慧生效", result)
        self.assertIn("经验修补", result)
        self.assertIn("寻宝发现", result)

    async def test_greedy_continue_does_not_reapply_jealous_bonus(self):
        cmds = FishingCommands(MockStar(), MockStorage())
        user = await cmds.storage.get_user("u1")
        rod = make_rod("rod_pref_12")
        rod["skills"] = {"jealous": 1.0}
        user._data["level"] = 10
        user._data["current_rod"] = dict(rod)
        chip = {
            "name": "贪欲结晶", "total_price": 100, "total_exp": 10, "fish_count": 1,
            "rarity_counts": {"common": 1, "rare": 0, "legendary": 0, "mythic": 0},
            "max_rarity": "common", "details": [],
        }
        user.start_greedy("inst_rod_1", "rod_pref_12", {}, chip, 2)
        cmds._calc_jealous_bonus = AsyncMock(return_value=0.64)

        fixed_fish = {
            "fish_name": "测试鱼", "price": 20, "exp": 5,
            "fish_id": "fish_001", "prefix_id": "pref_001",
            "rarity": "common", "rarity_emoji": "", "desc": "",
        }
        with patch("random.random", return_value=1.0):
            with patch.object(cmds, "_do_fish_once", return_value=fixed_fish) as do_fish:
                await cmds.cmd_greedy_continue(make_event())

        cmds._calc_jealous_bonus.assert_not_awaited()
        self.assertEqual(do_fish.call_args.kwargs["jealous_bonus"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
