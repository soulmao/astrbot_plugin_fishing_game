"""钓鱼游戏特殊钓竿收益模拟工具。"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
from pathlib import Path
import random
import sys
import time


SPECIAL_PREFIX_IDS = [
    "rod_pref_12", "rod_pref_19", "rod_pref_13", "rod_pref_14",
    "rod_pref_15", "rod_pref_16", "rod_pref_17", "rod_pref_18",
]

# 与商店购买逻辑保持一致：特种钓竿的固有能力存储在钓竿实例中。
def load_test_bootstrap(project: Path):
    """加载项目测试桩，使模拟无需安装完整 AstrBot。"""
    path = project / "tests" / "test_greedy.py"
    if not path.exists():
        raise FileNotFoundError(f"缺少模拟依赖：{path}")
    module_name = "fishing_game_balance_test_bootstrap"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def inventory_fish_value(user, calc_fish_value) -> int:
    """计算玩家当前全部渔获售价。"""
    return sum(
        calc_fish_value(item["fish_id"], item["prefix_id"], item["count"])
        for item in user.get_fish_inventory()
    )


def inventory_bait_value(user, calc_bait_value) -> int:
    """计算玩家当前全部鱼饵价值。"""
    return sum(
        calc_bait_value(item["base_id"], item["prefix_id"], item.get("count", 0))
        for item in user.get_baits()
    )


async def simulate_one(
    bootstrap, label: str, base_id: str, prefix_id: str,
    iterations: int, seed: int, greedy_target: int,
) -> dict:
    """按真实命令流程模拟一种钓竿。"""
    from astrbot_plugin_fishing_game.fish_data import (
        calc_bait_value, calc_fish_value, get_rod_by_id, get_rod_prefix,
        get_rod_builtin_skills, get_effective_rod_skills,
    )

    random.seed(seed)
    storage = bootstrap.MockStorage()

    async def get_higher_level_count(_level: int) -> int:
        return 8

    storage.get_higher_level_count = get_higher_level_count
    commands = bootstrap.FishingCommands(bootstrap.MockStar(), storage)
    user = await storage.get_user(f"sim_{label}")

    bait_id = "bait_003" if prefix_id == "rod_pref_17" else "bait_001"
    built_in_skills = get_rod_builtin_skills(base_id)
    uses_bait = base_id not in {"rod_006", "rod_007"}
    rod = {
        "base_id": base_id,
        "prefix_id": prefix_id,
        "instance_id": f"sim_{label}",
        "enchant_count": 0,
        "skills": built_in_skills,
    }
    user._data.update({
        "level": 10,
        "coins": 1_000_000,
        "current_rod": dict(rod),
        "owned_rods": [dict(rod)],
        "last_fish_date": time.strftime("%Y-%m-%d"),
        "fish_cooldown": 0,
    })
    if uses_bait:
        user._data["baits"] = [{
            "base_id": bait_id,
            "prefix_id": "bait_pref_02",
            "count": iterations * 100 + 100,
        }]
        user._data["current_bait"] = {
            "base_id": bait_id,
            "prefix_id": "bait_pref_02",
        }
    else:
        user._data["baits"] = []
    user.check_achievements = lambda: []

    event = bootstrap.make_event(user.user_id, "模拟玩家")
    start_coins = user.coins
    start_exp = user.exp
    start_bait_value = inventory_bait_value(user, calc_bait_value)
    total_cooldown = 0
    breaks = 0

    for _ in range(iterations):
        user._data["fish_cooldown"] = 0
        await commands.cmd_fish(event)
        if prefix_id in {"rod_pref_12", "rod_pref_19"}:
            while user.is_greedy_active() and user.greedy_state["stack"] < greedy_target:
                was_active = user.is_greedy_active()
                await commands.cmd_greedy_continue(event)
                if was_active and not user.is_greedy_active():
                    breaks += 1
            if user.is_greedy_active():
                await commands.cmd_greedy_cashout(event)
        total_cooldown += max(0, user.fish_cooldown - int(time.time()))

    fish_value = inventory_fish_value(user, calc_fish_value)
    coin_delta = user.coins - start_coins
    bait_delta = inventory_bait_value(user, calc_bait_value) - start_bait_value
    net_value = fish_value + coin_delta + bait_delta
    hours = total_cooldown / 3600
    name = (
        get_rod_prefix(prefix_id).get("name")
        if prefix_id else get_rod_by_id(base_id).get("name")
    )
    return {
        "name": name or label,
        "fish": user.total_fish_count,
        "net": net_value,
        "per_hour": net_value / hours if hours else 0,
        "exp": user.exp - start_exp,
        "breaks": breaks,
        "coins_left": user.coins,
        "initial_skills": len(get_effective_rod_skills(base_id, prefix_id, built_in_skills)),
        "skills": len(get_effective_rod_skills(
            base_id, prefix_id, user.current_rod.get("skills", {})
        )),
    }


async def run_balance(project: Path, iterations: int, seed: int, greedy_target: int) -> None:
    """运行全部特殊钓竿的收益模拟并输出 Markdown 表格。"""
    bootstrap = load_test_bootstrap(project)
    cases = [("普通基准", "rod_004", "rod_pref_03")]
    cases.extend((prefix_id, "rod_004", prefix_id) for prefix_id in SPECIAL_PREFIX_IDS)
    cases.extend([
        ("金币钓竿", "rod_006", ""),
        ("胡萝卜钓竿", "rod_007", ""),
    ])

    rows = []
    for index, (label, base_id, prefix_id) in enumerate(cases):
        rows.append(await simulate_one(
            bootstrap, label, base_id, prefix_id,
            iterations, seed + index, greedy_target,
        ))

    baseline = rows[0]["per_hour"] or 1
    print(
        f"\n模拟条件：每种 {iterations} 轮，随机种子 {seed}，"
        f"贪婪目标 {greedy_target} 层，嫉妒按 8 名高等级玩家。"
    )
    print("| 钓竿 | 渔获数 | 净价值 | 净价值/小时 | 相对基准 | 经验 | 断线 | 最终金币 | 初始/现有词条 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        ratio = row["per_hour"] / baseline
        marker = " [!]" if ratio < 0.8 or ratio > 2.5 else ""
        print(
            f"| {row['name']} | {row['fish']} | {row['net']} | {row['per_hour']:.2f} | "
            f"{ratio:.2f}x{marker} | {row['exp']} | {row['breaks']} | {row['coins_left']} | "
            f"{row['initial_skills']}/{row['skills']} |"
        )


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="钓鱼游戏特殊钓竿收益模拟")
    parser.add_argument("--project", default=".", help="项目根目录，默认当前目录")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260618)
    parser.add_argument("--greedy-target", type=int, default=3)
    args = parser.parse_args()
    if args.iterations <= 0:
        parser.error("--iterations 必须大于 0")
    if args.greedy_target <= 0:
        parser.error("--greedy-target 必须大于 0")
    return args


def main() -> int:
    """运行收益模拟。"""
    args = parse_args()
    project = Path(args.project).resolve()
    if not (project / "command_fishing.py").exists():
        print(f"[ERROR] 不是有效的钓鱼游戏项目目录：{project}", file=sys.stderr)
        return 2
    asyncio.run(run_balance(project, args.iterations, args.seed, args.greedy_target))
    print("\n[OK] 模拟完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
