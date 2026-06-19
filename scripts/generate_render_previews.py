"""渲染所有模板为本地 PNG，用于检查文字重叠和卡片冲突。"""

import asyncio
import importlib.util
import os
import sys
import tempfile
import types
from pathlib import Path

from jinja2 import Environment, BaseLoader
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "astrbot_plugin_fishing_game"

if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PROJECT_ROOT)]
    sys.modules[PACKAGE_NAME] = package


def _load_module(module_name: str, file_name: str):
    path = PROJECT_ROOT / file_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


fish_data = _load_module(f"{PACKAGE_NAME}.fish_data", "fish_data.py")
models = _load_module(f"{PACKAGE_NAME}.models", "models.py")
fishing_renderer = _load_module(f"{PACKAGE_NAME}.fishing_renderer", "fishing_renderer.py")
backpack_renderer = _load_module(f"{PACKAGE_NAME}.backpack_renderer", "backpack_renderer.py")
gallery_renderer = _load_module(f"{PACKAGE_NAME}.gallery_renderer", "gallery_renderer.py")
market_renderer = _load_module(f"{PACKAGE_NAME}.market_renderer", "market_renderer.py")
result_renderer = _load_module(f"{PACKAGE_NAME}.result_renderer", "result_renderer.py")
UserData = models.UserData


def _render_template(template_str: str, data: dict) -> str:
    return Environment(loader=BaseLoader()).from_string(template_str).render(**data)


async def _screenshot(html: str, output_path: Path, width: int = 1280):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        temp_path = f.name
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_viewport_size({"width": width, "height": 1})
            await page.goto(f"file:///{temp_path.replace(os.sep, '/')}")
            await page.screenshot(path=str(output_path), full_page=True)
            await browser.close()
    finally:
        os.unlink(temp_path)


def _make_fishing_success_view() -> dict:
    text = """🎣 钓鱼成功！
✨ 本次钓鱼不消耗鱼饵！ 🌾 丰收触发！ 🌊 远航触发！额外8次

  [1] ⭐金色的龙鱼
  💰 售价: 1500 金币
  [2] 🔷红色的鲈鱼
  💰 售价: 112 金币
  [3] 普通的小杂鱼
  💰 售价: 45 金币
  [4] 健康的鱿鱼
  💰 售价: 60 金币
  [5] 普通的海星
  💰 售价: 80 金币
📈 经验 +2270
⏰ 冷却 23分16秒 ⚡-45% +12分16秒
🐟 累计钓鱼 4635 次

🎁 幸运奖励：获得 珍稀的蚯蚓 x1！"""
    return fishing_renderer.build_fishing_result_view(text, "奶小柒")


def _make_greedy_views() -> tuple:
    start_text = """🎣 钓鱼成功！
💰 无尽贪婪钓竿发出声音
🧿 你将 4 条渔获揉碎融合为【深紫结晶】
💎 结晶基础价值: 1880 金币
📈 结晶基础经验: 240"""
    continued_text = """🎣 第 3 层贪婪成功！
🐟 额外钓上: ⭐金色的龙鱼 💰1500
🧿 【深紫结晶】已膨胀至 8890 金币（5 条渔获聚合）
📈 当前累计经验: 660
⚠️ 下次断线概率: 32%"""
    cashout_text = """🎣 收杆成功！贪欲结晶稳稳落入你的背包...
🧿 结算层数: 3
💰 +8890 金币
📈 +660 经验
⏰ 冷却 2小时"""
    return (
        fishing_renderer.build_fishing_result_view(start_text, "Soulmao"),
        fishing_renderer.build_fishing_result_view(continued_text, "Soulmao"),
        fishing_renderer.build_fishing_result_view(cashout_text, "Soulmao"),
    )


def _make_backpack_view() -> dict:
    user = UserData("preview_user")
    user._data["level"] = 8
    user._data["exp"] = 36420
    user._data["coins"] = 128650
    user._data["total_fish_count"] = 1286
    user._data["consecutive_checkin_days"] = 5
    current_id = user.add_rod(
        "rod_004", "rod_pref_11", {"swift": 0.45, "lucky": 0.25}, 7, "rod_current"
    )
    user.add_rod("rod_006", "", {}, 0, "rod_gold")
    user.equip_rod(current_id)
    user.add_bait("bait_001", "bait_pref_02", 481)
    user.add_bait("bait_004", "bait_pref_09", 3)
    user.equip_bait("bait_004", "bait_pref_09")
    user.add_fish("fish_001", "pref_001", 5)
    user.add_fish("fish_011", "pref_007", 1)
    user.add_fish("fish_034", "pref_014", 1)
    user.add_fish("fish_025", "pref_006", 2)
    return backpack_renderer.build_backpack_view(user, "奶小柒")


def _make_rods_view() -> dict:
    user = UserData("preview_user")
    user.add_rod("rod_004", "rod_pref_11", {"swift": 0.45, "lucky": 0.25}, 7, "rod_current")
    user.add_rod(
        "rod_005", "rod_pref_17",
        {"treasure": 0.25, "tide": 0.12, "exp_boost": 0.18, "mending": 0.26},
        4, "rod_arrogant",
    )
    user.equip_rod("rod_arrogant")
    return backpack_renderer.build_rods_view(user, "真实玩家")


def _make_gallery_views() -> tuple:
    bait_user = UserData("bait_user")
    bait_user.add_bait("bait_001", "bait_pref_02", 481)
    bait_user.add_bait("bait_004", "bait_pref_09", 3)
    bait_user.add_bait("bait_003", "bait_pref_06", 8)
    bait_user.equip_bait("bait_004", "bait_pref_09")

    collection_user = UserData("collection_user")
    collection_user._data["collection"] = {
        "fish_001#pref_001": {"count": 4, "first_at": 100},
        "fish_011#pref_007": {"count": 2, "first_at": 300},
        "fish_034#pref_014": {"count": 1, "first_at": 200},
    }

    achievement_user = UserData("achievement_user")
    achievement_user._data["total_fish_count"] = 4602
    achievement_user._data["coins"] = 4910
    achievement_user._data["level"] = 11
    achievement_user._data["rarity_catch_count"] = {
        "common": 3000, "rare": 400, "legendary": 80, "mythic": 12,
    }
    achievement_user._data["achievements"] = ["first_fish", "novice_angler", "level_3"]

    return (
        gallery_renderer.build_baits_view(bait_user, "奶小柒"),
        gallery_renderer.build_collection_view(collection_user, "奶小柒", recent_limit=12),
        gallery_renderer.build_achievements_view(achievement_user, "奶小柒"),
    )


def _make_market_views() -> tuple:
    shop_user = UserData("shop_user")
    shop_user._data["coins"] = 5000
    shop_user._data["shop_level"] = 2
    shop_user._data["shop_refresh_cd"] = 0
    shop_user._data["current_shop"] = [
        {"type": "rod", "base_id": "rod_004", "prefix_id": "rod_pref_11", "quantity": 1, "price": 3200},
        {"type": "bait", "base_id": "bait_001", "prefix_id": "bait_pref_02", "quantity": 10, "price": 800},
        {"type": "directed_enchant", "name": "[定向附魔券 · 迅捷 +25%]", "quantity": 1, "price": 1200},
        {"type": "refresh_token", "name": "刷新券", "quantity": 3, "price": 300},
    ]

    listings = [
        {
            "id": "auc_001",
            "seller_id": "viewer",
            "seller_name": "我自己",
            "expires_at": 9999999999,
            "item_data": {"type": "rod", "base_id": "rod_004", "prefix_id": "rod_pref_11", "enchant_count": 5},
        },
        {
            "id": "auc_002",
            "seller_id": "other",
            "seller_name": "另一个玩家名字很长",
            "expires_at": 9999999999,
            "item_data": {"type": "fish", "fish_id": "fish_011", "prefix_id": "pref_007", "count": 3},
        },
        {
            "id": "auc_003",
            "seller_id": "other2",
            "seller_name": "卖家C",
            "expires_at": 9999999999,
            "item_data": {"type": "bait", "base_id": "bait_004", "prefix_id": "bait_pref_09", "count": 20},
        },
    ]
    auction_view = market_renderer.build_auction_view(listings, 3, viewer_id="viewer")
    return market_renderer.build_shop_view(shop_user, "奶小柒"), auction_view


def _make_result_view() -> dict:
    text = """# 🎣 钓鱼成功！
✨ 双倍钓鱼触发
**获得渔获：**
- ⭐金色的龙鱼 💰 1500 金币
- 🔷红色的鲈鱼 💰 112 金币
- 普通的小杂鱼 💰 45 金币

💰 本次价值：1657 金币
📈 经验 +2270
⏰ 冷却 23分16秒
🐟 累计钓鱼 4635 次"""
    return {
        "sender_name": "奶小柒",
        "content_html": result_renderer.render_result_html(text),
    }


async def main():
    output_dir = PROJECT_ROOT / "docs" / "compact_preview"
    output_dir.mkdir(exist_ok=True)

    cases = [
        ("fishing_success", _make_fishing_success_view(), fishing_renderer.FISHING_IMAGE_TEMPLATE, 1040 + 48),
        ("greedy_start", _make_greedy_views()[0], fishing_renderer.FISHING_IMAGE_TEMPLATE, 720 + 48),
        ("greedy_continue", _make_greedy_views()[1], fishing_renderer.FISHING_IMAGE_TEMPLATE, 720 + 48),
        ("greedy_cashout", _make_greedy_views()[2], fishing_renderer.FISHING_IMAGE_TEMPLATE, 720 + 48),
        ("backpack", _make_backpack_view(), backpack_renderer.BACKPACK_IMAGE_TEMPLATE, 1200 + 48),
        ("rods", _make_rods_view(), backpack_renderer.RODS_IMAGE_TEMPLATE, 920 + 48),
        ("baits", _make_gallery_views()[0], gallery_renderer.BAITS_IMAGE_TEMPLATE, 1200 + 48),
        ("collection", _make_gallery_views()[1], gallery_renderer.COLLECTION_IMAGE_TEMPLATE, 1200 + 48),
        ("achievements", _make_gallery_views()[2], gallery_renderer.ACHIEVEMENTS_IMAGE_TEMPLATE, 1560 + 48),
        ("shop", _make_market_views()[0], market_renderer.SHOP_IMAGE_TEMPLATE, 1200 + 48),
        ("auction", _make_market_views()[1], market_renderer.AUCTION_IMAGE_TEMPLATE, 1200 + 48),
        ("result", _make_result_view(), result_renderer.RESULT_IMAGE_TEMPLATE, 760 + 48),
    ]

    for name, data, template, width in cases:
        html = _render_template(template, data)
        output_path = output_dir / f"{name}.png"
        await _screenshot(html, output_path, width=width)
        print(f"Generated {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
