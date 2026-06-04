"""经济系统命令模块"""
import time

from .commands_base import CommandBase
from .utils import (
    format_rod_name, format_bait_name, render_shop_text, generate_shop_items,
    format_time,
)
from .fish_data import (
    get_fish_by_id, get_prefix_by_id, get_rod_by_id, get_bait_by_id,
    get_rod_prefix, get_bait_prefix, get_level_info,
)
from .storage import StorageManager


class EconomyCommands(CommandBase):
    """经济系统命令处理器"""

    async def cmd_sell(self, event, fish_id_or_all: str = "all") -> str:
        """卖鱼命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            if not user.get_fish_inventory():
                return "你没有渔获可以出售！"
            
            total_earned = 0
            
            if fish_id_or_all.lower() in ["all", "全部", ""]:
                # 全部卖出
                for fish in user.get_fish_inventory()[:]:
                    fish_info = get_fish_by_id(fish["fish_id"])
                    prefix = get_prefix_by_id(fish["prefix_id"])
                    if fish_info and prefix:
                        base_price = fish_info["base_price"] * prefix["price_multiplier"]
                        # 古龙收藏系列鱼额外 20% 收藏家溢价
                        if prefix["id"] == "pref_014":
                            base_price *= 1.2
                        price = int(base_price)
                        earned = price * fish["count"]
                        total_earned += earned
                        user._data["fish_inventory"].remove(fish)
            else:
                # 单个卖出
                fish_found = None
                for fish in user.get_fish_inventory():
                    if fish["fish_id"] == fish_id_or_all:
                        fish_found = fish
                        break
                
                if not fish_found:
                    return f"背包中没有 ID 为 {fish_id_or_all} 的鱼"
                
                fish_info = get_fish_by_id(fish_found["fish_id"])
                prefix = get_prefix_by_id(fish_found["prefix_id"])
                if fish_info and prefix:
                    base_price = fish_info["base_price"] * prefix["price_multiplier"]
                    # 古龙收藏系列鱼额外 20% 收藏家溢价
                    if prefix["id"] == "pref_014":
                        base_price *= 1.2
                    price = int(base_price)
                    total_earned = price * fish_found["count"]
                    user._data["fish_inventory"].remove(fish_found)
            
            if total_earned == 0:
                return "没有可出售的渔获"
            
            # 获得金币和经验
            user.add_coins(total_earned)
            exp_gained = int(total_earned * 0.1)
            leveled_up, new_level = user.add_exp(exp_gained)
            
            await self.storage.save_user(user)
            
            result = f"""💰 出售成功！

获得: {total_earned} 金币 (+{exp_gained} 经验)"""
            
            if leveled_up:
                level_info = get_level_info(new_level)
                result += f"\n🎉 升级！现在是 {level_info['name']}！"
            
            return result
    
    async def cmd_shop(self, event) -> str:
        """商店命令 - 优先展示缓存的商店，为空或含已拥有钓竿时清洗/重新生成"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            items = user.get("current_shop", [])
            # 清洗缓存：移除已拥有的钓竿（兼容老版本缓存数据）
            cleaned = []
            dirty = False
            for item in items:
                if item.get("type") == "rod" and user.has_rod(item["base_id"], item["prefix_id"]):
                    dirty = True
                    continue
                cleaned.append(item)
            
            if dirty:
                items = cleaned
                user.set("current_shop", items)
            
            if not items:
                items = generate_shop_items(user)
                user.set("current_shop", items)
                await self.storage.save_user(user)
            
            return render_shop_text(items)
    
    async def cmd_buy(self, event, index: int, quantity: int = 1) -> str:
        """购买命令"""
        # 特殊物品名称映射（与 render_shop_text 保持一致）
        SPECIAL_NAMES = {
            "refresh_token": "🔄 刷新券",
        }
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            items = user.get("current_shop", [])
            
            if index < 1 or index > len(items):
                return "商品编号无效"
            
            item = items[index - 1]
            
            # 计算总价
            total_price = item["price"] * quantity
            
            # 检查金币
            if user.coins < total_price:
                return f"金币不足！需要 {total_price} 金币，你只有 {user.coins} 金币"
            
            # 钓竿购买前置检查（必须在扣费之前）
            if item["type"] == "rod":
                if quantity > 1:
                    return "钓竿每次只能购买 1 根"
                if user.has_rod(item["base_id"], item["prefix_id"]):
                    return "你已经拥有这根钓竿，无需重复购买"
            
            # 执行购买（扣费）
            user.remove_coins(total_price)
            if item["type"] == "rod":
                # 特种钓竿自带技能
                built_in_skills = {}
                if item["base_id"] == "rod_006":
                    built_in_skills = {"treasure": 0.80}
                elif item["base_id"] == "rod_007":
                    built_in_skills = {"voyage": 0.80}
                user.add_rod(item["base_id"], item["prefix_id"], built_in_skills)
                # 钓竿只能买一次，从当前商店移除
                items.pop(index - 1)
                user.set("current_shop", items)
            elif item["type"] in SPECIAL_NAMES:
                # 特殊物品：添加到用户专属存储（如刷新券存入道具栏）
                user.add_item(item["type"], quantity)
            else:
                user.add_bait(item["base_id"], item["prefix_id"], item.get("quantity", 1) * quantity)
            
            await self.storage.save_user(user)
            
            # 构建名称
            if item["type"] == "rod":
                base = get_rod_by_id(item["base_id"])
                prefix = get_rod_prefix(item["prefix_id"])
                name = f"{prefix['name']}{base['name']}"
            elif item["type"] in SPECIAL_NAMES:
                name = SPECIAL_NAMES[item["type"]]
            else:
                base = get_bait_by_id(item["base_id"])
                prefix = get_bait_prefix(item["prefix_id"])
                name = f"{prefix['name']}{base['name']}"
            
            return f"✅ 购买成功！\n\n获得: {name} x{quantity}\n花费: {total_price} 金币\n剩余: {user.coins} 金币"
    
    async def cmd_shop_refresh(self, event) -> str:
        """刷新商店命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            # 检查冷却
            if not user.is_shop_refresh_ready():
                remaining = max(0, user.shop_refresh_cd - int(time.time()))
                return f"商店刷新冷却中，剩余 {format_time(remaining)}"
            
            # 检查金币或刷新券
            has_refresh_token = user.get_item_count("refresh_token") > 0
            
            if not has_refresh_token and user.coins < 50:
                return f"金币不足且无刷新券！需要 50 金币，你只有 {user.coins} 金币"
            
            # 扣费
            refresh_token_used = False
            if has_refresh_token:
                refresh_token_used = user.remove_item("refresh_token")
            else:
                user.remove_coins(50)
            
            user.set_shop_refresh_cd(self.star.shop_refresh_cooldown)
            
            # 强制重新生成商店（清空缓存后生成）
            items = generate_shop_items(user)
            user.set("current_shop", items)
            await self.storage.save_user(user)
            
            result = render_shop_text(items)
            refresh_msg = "（使用刷新券）" if refresh_token_used else "（消耗 50 金币）"
            return f"✅ 商店已刷新{refresh_msg}！\n\n" + result
