"""钓鱼游戏命令模块"""
from .fish_data import (
    FISH_TYPES, FISH_PREFIXES, ROD_BASES, ROD_PREFIXES,
    BAIT_BASES, BAIT_PREFIXES, LEVELS, SHOP_ITEMS,
    get_fish_by_id, get_prefix_by_id, get_rod_by_id, get_bait_by_id,
    get_level_info, get_next_level_exp, ROD_SKILL_DESCRIPTIONS
)
from .storage import StorageManager, UserData
import random
import time
import json
import asyncio
from typing import Optional


class FishingGameCommands:
    """钓鱼游戏命令处理器"""
    
    def __init__(self, star, storage=None):
        self.star = star
        self.storage = storage or StorageManager(star)
        self.user_locks: dict[str, asyncio.Lock] = {}
    
    def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]
    
    def _format_time(self, seconds: int) -> str:
        """格式化时间"""
        if seconds <= 0:
            return "好了"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        parts = []
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分")
        if secs > 0:
            parts.append(f"{secs}秒")
        if not parts:
            return "好了"
        return "".join(parts)
    
    def _format_rod_name(self, rod: dict) -> str:
        """格式化钓竿名称"""
        base = get_rod_by_id(rod["base_id"])
        prefix = self._get_rod_prefix(rod["prefix_id"])
        if base and prefix:
            return f"{prefix['name']}{base['name']}"
        return "木制钓竿"
    
    def _get_rod_prefix(self, prefix_id: str) -> dict:
        for p in ROD_PREFIXES:
            if p["id"] == prefix_id:
                return p
        return ROD_PREFIXES[2]  # 默认"普通的"
    
    def _get_bait_prefix(self, prefix_id: str) -> dict:
        for p in BAIT_PREFIXES:
            if p["id"] == prefix_id:
                return p
        return BAIT_PREFIXES[1]  # 默认"普通的"

    def _format_rod_skills(self, prefix_id: str) -> str:
        """格式化钓竿技能文本"""
        prefix = self._get_rod_prefix(prefix_id)
        skills = prefix.get("skills", {})
        if not skills:
            return ""
        parts = []
        for sid, val in skills.items():
            label = ROD_SKILL_DESCRIPTIONS.get(sid, sid)
            if sid in ("lucky", "exp_boost"):
                parts.append(f"{label}+{int(val*100)}%")
            else:
                parts.append(f"{label}{int(val*100)}%")
        return " [" + " | ".join(parts) + "]"
    
    def _extract_target_user_id(self, raw: str) -> Optional[str]:
        """从命令参数中提取目标用户ID"""
        if not raw:
            return None
        cleaned = raw.lstrip("@").strip()
        if not cleaned:
            return None
        return cleaned
    
    async def cmd_help(self, event) -> str:
        """帮助命令"""
        fishing_cd = self._format_time(self.star.fishing_cooldown)
        return f"""🎣 钓鱼游戏帮助

📋 **命令列表：**

🎯 `/钓鱼` 或 `/fish`
  消耗1个鱼饵钓鱼，获得随机鱼类
  冷却 {fishing_cd}

📦 `/背包` 或 `/bag`
  查看渔获、鱼饵、金币、钓竿等信息

💰 `/卖鱼 [ID/全部]` 或 `/sell [ID/全部]`
  出售渔获获取金币

📊 `/等级` 或 `/level`
  查看当前等级和经验进度

⏰ `/冷却` 或 `/cd`
  查看钓鱼和商店刷新的冷却状态

🏪 `/商店` 或 `/shop`
  查看可购买的钓竿和鱼饵（随机刷新6件）

🛒 `/购买 [编号] [数量]` 或 `/buy [编号] [数量]`
  从商店购买物品

🔄 `/刷新商店` 或 `/shop_refresh`
  手动刷新商店，消耗50金币或刷新券
  冷却 1 小时

🎣 `/我的钓竿` 或 `/myrods`
  查看所有拥有的钓竿

🔧 `/装备钓竿 [编号]` 或 `/equip [编号]`
  切换当前使用的钓竿

🪤 `/我的鱼饵` 或 `/mybaits`
  查看所有拥有的鱼饵

🔧 `/装备鱼饵 [编号]` 或 `/equip_bait [编号]`
  切换当前使用的鱼饵，钓鱼时优先消耗该鱼饵

🏆 `/排行榜` 或 `/rank`
  查看钓鱼次数排行榜

🎁 `/赠送 @用户 类型 ID [数量]` 或 `/give @用户 类型 ID [数量]`
  赠送金币/渔获/鱼饵给其他用户
  类型: coins(金币), fish(渔获), bait(鱼饵)

————————————————

🐟 **游戏玩法：**
• 初始获得 100 金币、木制钓竿、10条蚯蚓
• 钓鱼获得渔获 → 卖鱼赚金币 → 购买更好的钓竿和鱼饵
• 更好的钓竿/鱼饵 = 更高稀有度 + 更多经验
• 升级解锁更强力的钓竿和鱼饵
• 高品质钓竿前缀自带词条技能（迅捷、幸运、丰收等）
• 每日可赠送 10 次给好友

🔱 **钓竿词条技能：**
高品质钓竿前缀自带技能：
• ⚡迅捷 - 减少钓鱼冷却时间
• 🍀幸运 - 提升幸运事件触发概率
• 🌾丰收 - 概率额外钓到一条鱼
• 💎寻宝 - 概率获得额外金币
• 🌊潮汐 - 概率本次钓鱼无需冷却
• ✨神慧 - 获得额外经验加成

🐉 **古龙收藏系列：**
稀有词缀，仅高级玩家可获得：
• 🎣 古龙收藏钓竿 - 极高幸运与全技能加成
• 🐟 古龙收藏鱼类 - 售价远超普通传说鱼
• 🪤 古龙收藏鱼饵 - 大幅加成随机事件触发率

📖 `/图鉴` - 查看已收集的鱼类图鉴进度"""
    
    async def cmd_myrods(self, event) -> str:
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            result = "[钓鱼] 我的钓竿\n\n"
            current = user.current_rod
            
            for i, rod in enumerate(user.get_owned_rods(), 1):
                rod_name = self._format_rod_name(rod)
                skill_text = self._format_rod_skills(rod["prefix_id"])
                is_current = (rod["base_id"] == current["base_id"] and rod["prefix_id"] == current["prefix_id"])
                marker = " [当前]" if is_current else ""
                result += f"{i}. {rod_name}{skill_text}{marker}\n"
            
            if not user.get_owned_rods():
                result += "(无)\n"
            
            result += "\n提示: 使用 /装备钓竿 [编号] 切换"
            return result
    
    async def cmd_equip_rod(self, event, index: int) -> str:
        """装备钓竿"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            rods = user.get_owned_rods()
            if index < 1 or index > len(rods):
                return f"编号无效，你有 {len(rods)} 根钓竿"
            
            rod = rods[index - 1]
            if user.equip_rod(rod["base_id"], rod["prefix_id"]):
                await self.storage.save_user(user)
                rod_name = self._format_rod_name(rod)
                return f"✅ 已装备: {rod_name}"
            return "装备失败"

    async def _format_bait_name(self, bait: dict) -> str:
        """格式化鱼饵名称"""
        base = get_bait_by_id(bait["base_id"])
        prefix = self._get_bait_prefix(bait["prefix_id"])
        if base and prefix:
            return f"{prefix['name']}{base['name']}"
        return "普通的蚯蚓"

    async def cmd_mybaits(self, event) -> str:
        """我的鱼饵 - 查看所有鱼饵"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            result = "[钓鱼] 我的鱼饵\n\n"
            current = user.current_bait
            
            for i, bait in enumerate(user.get_baits(), 1):
                bait_name = await self._format_bait_name(bait)
                is_current = (bait["base_id"] == current["base_id"] and bait["prefix_id"] == current["prefix_id"])
                marker = " [当前]" if is_current else ""
                result += f"{i}. {bait_name} x{bait.get('count', 0)}{marker}\n"
            
            if not user.get_baits():
                result += "(无)\n"
            
            result += "\n提示: 使用 /装备鱼饵 [编号] 切换"
            return result

    async def cmd_equip_bait(self, event, index: int) -> str:
        """装备鱼饵"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            baits = user.get_baits()
            if index < 1 or index > len(baits):
                return f"编号无效，你有 {len(baits)} 种鱼饵"
            
            bait = baits[index - 1]
            if bait.get("count", 0) <= 0:
                return f"该鱼饵数量为0，无法装备"
            
            if user.equip_bait(bait["base_id"], bait["prefix_id"]):
                await self.storage.save_user(user)
                bait_name = await self._format_bait_name(bait)
                return f"✅ 已装备: {bait_name}"
            return "装备失败"

    def _do_fish_once(self, user, rod, selected_bait) -> Optional[dict]:
        """执行一次钓鱼随机计算，返回结果字典；若无可选池则返回None"""
        rod_base = get_rod_by_id(rod["base_id"])
        rod_prefix = self._get_rod_prefix(rod["prefix_id"])
        bait_base = get_bait_by_id(selected_bait["base_id"])
        bait_prefix = self._get_bait_prefix(selected_bait["prefix_id"])
        
        rod_exp_mult = rod_base["exp_multiplier"] * rod_prefix["multiplier"]
        rod_rarity_bonus = rod_base["rarity_bonus"] * rod_prefix["multiplier"]
        bait_exp_mult = bait_base["exp_multiplier"] * bait_prefix["multiplier"]
        bait_quality_bonus = bait_base["quality_bonus"] * bait_prefix["multiplier"]
        
        # 选择鱼种
        fish_pool = []
        for fish in FISH_TYPES:
            if fish["rarity"] == "rare" and user.level < 2:
                continue
            if fish["rarity"] == "legendary" and user.level < 5:
                continue
            if fish["rarity"] == "mythic" and user.level < 6:
                continue
            if fish["rarity"] == "mythic" and rod["base_id"] not in ["rod_004", "rod_005"]:
                continue
            if fish["rarity"] in ("rare", "legendary", "mythic"):
                weight = fish["weight"] * (1 + rod_rarity_bonus + bait_quality_bonus)
            else:
                weight = fish["weight"]
            fish_pool.append((fish, weight))
        
        if not fish_pool:
            return None
        
        selected_fish, _ = random.choices(fish_pool, weights=[w for _, w in fish_pool], k=1)[0]
        
        # 选择前缀
        prefix_pool = []
        for prefix in FISH_PREFIXES:
            if "min_level" in prefix and user.level < prefix["min_level"]:
                continue
            if prefix.get("requires_gold_rod") and rod["base_id"] not in ["rod_004", "rod_005"]:
                continue
            if prefix.get("requires_divine_rod") and rod["base_id"] != "rod_005":
                continue
            prefix_pool.append((prefix, prefix["weight"]))
        
        if not prefix_pool:
            return None
        
        selected_prefix = random.choices([p for p, _ in prefix_pool], weights=[w for _, w in prefix_pool], k=1)[0]
        
        price = int(selected_fish["base_price"] * selected_prefix["price_multiplier"])
        exp_gained = int(10 * rod_exp_mult * bait_exp_mult)
        fish_name = f"{selected_prefix['name']}{selected_fish['name']}"
        rarity_emoji = {"common": "", "rare": "", "legendary": "⭐", "mythic": "🌟"}[selected_fish["rarity"]]
        
        return {
            "fish_name": fish_name,
            "price": price,
            "exp": exp_gained,
            "fish_id": selected_fish["id"],
            "prefix_id": selected_prefix["id"],
            "rarity": selected_fish["rarity"],
            "rarity_emoji": rarity_emoji,
            "desc": selected_fish.get("desc", ""),
        }
    
    def _generate_random_bait(self) -> tuple:
        """随机生成不受等级限制的鱼饵，返回 (base_id, prefix_id, count, name)"""
        base = random.choice(BAIT_BASES)
        prefix = random.choice(BAIT_PREFIXES)
        count = random.randint(1, 3)
        name = f"{prefix['name']}{base['name']}"
        return base["id"], prefix["id"], count, name
    
    def _generate_random_rod(self) -> tuple:
        """随机生成不受等级限制的钓竿，返回 (base_id, prefix_id, name)"""
        base = random.choice(ROD_BASES)
        prefix = random.choice(ROD_PREFIXES)
        name = f"{prefix['name']}{base['name']}"
        return base["id"], prefix["id"], name

    async def cmd_fish(self, event) -> str:
        """钓鱼命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            # 检查冷却
            if not user.is_fishing_ready():
                remaining = user.get_fishing_cd_remaining()
                return f"钓鱼冷却中，剩余 {self._format_time(remaining)}"
            
            # 检查鱼饵
            if user.get_total_bait_count() <= 0:
                return "你没有鱼饵了，请先在商店购买或接受赠送！"
            
            # 使用当前装备的鱼饵
            selected_bait = user.current_bait
            
            # 检查该鱼饵是否有库存
            bait_count = user.get_bait_count(selected_bait["base_id"], selected_bait["prefix_id"])
            if bait_count <= 0:
                selected_bait = None
                for bait in user.get_baits():
                    if bait.get("count", 0) > 0:
                        selected_bait = bait
                        break
                if not selected_bait:
                    return "你没有鱼饵了！"
            
            rod = user.current_rod
            rod_prefix = self._get_rod_prefix(rod["prefix_id"])
            skills = rod_prefix.get("skills", {})
            
            # 解析钓竿技能数值
            swift_val = skills.get("swift", 0)
            lucky_val = skills.get("lucky", 0)
            harvest_val = skills.get("harvest", 0)
            treasure_val = skills.get("treasure", 0)
            tide_val = skills.get("tide", 0)
            exp_boost_val = skills.get("exp_boost", 0)
            
            # 获取鱼饵的事件加成（古龙收藏系列鱼饵特有）
            bait_prefix_obj = self._get_bait_prefix(selected_bait["prefix_id"])
            bait_event_bonus = bait_prefix_obj.get("event_bonus", 0)
            
            # 计算实际冷却时间
            effective_cooldown = int(self.star.fishing_cooldown * (1 - swift_val))
            
            # 触发幸运事件（受 lucky + 鱼饵 event_bonus 共同加成）
            lucky_events = {
                "double_fish": random.random() < min(0.10 + lucky_val + bait_event_bonus, 0.50),
                "free_bait": random.random() < min(0.10 + lucky_val + bait_event_bonus, 0.50),
                "bonus_bait": random.random() < min(0.10 + lucky_val + bait_event_bonus, 0.50),
                "bonus_rod": random.random() < min(0.01 + lucky_val * 0.05 + bait_event_bonus * 0.05, 0.15),
            }
            
            # 消耗鱼饵（除非触发不消耗鱼饵）
            if not lucky_events["free_bait"]:
                if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], 1):
                    return "鱼饵消耗失败，请检查背包！"
            
            # 执行钓鱼（1次或2次）
            fish_count = 2 if lucky_events["double_fish"] else 1
            fish_results = []
            total_exp = 0
            
            for _ in range(fish_count):
                result = self._do_fish_once(user, rod, selected_bait)
                if result is None:
                    return "钓鱼出现异常，请联系管理员"
                fish_results.append(result)
                user.add_fish(result["fish_id"], result["prefix_id"], 1)
                user.add_to_collection(result["fish_id"], result["prefix_id"])
                user.increment_fish_count()
                total_exp += result["exp"]
            
            # 丰收：概率额外钓到一条鱼
            harvest_triggered = random.random() < harvest_val
            if harvest_triggered:
                result = self._do_fish_once(user, rod, selected_bait)
                if result:
                    fish_results.append(result)
                    user.add_fish(result["fish_id"], result["prefix_id"], 1)
                    user.add_to_collection(result["fish_id"], result["prefix_id"])
                    user.increment_fish_count()
                    total_exp += result["exp"]
            
            # 经验加成
            if exp_boost_val > 0:
                bonus_exp = int(total_exp * exp_boost_val)
                total_exp += bonus_exp
            
            # 设置冷却（受 tide 影响）
            tide_triggered = random.random() < tide_val
            if not tide_triggered:
                user.set_fishing_cooldown(effective_cooldown)
            
            # 增加经验
            leveled_up, new_level = user.add_exp(total_exp)
            
            # 处理额外奖励
            bonus_msgs = []
            
            if lucky_events["bonus_bait"]:
                bait_base_id, bait_prefix_id, bait_count, bait_name = self._generate_random_bait()
                user.add_bait(bait_base_id, bait_prefix_id, bait_count)
                bonus_msgs.append(f"🎁 幸运奖励：获得 {bait_name} x{bait_count}！")
            
            if lucky_events["bonus_rod"]:
                rod_base_id, rod_prefix_id, rod_name = self._generate_random_rod()
                user.add_rod(rod_base_id, rod_prefix_id)
                bonus_msgs.append(f"🎁 超级幸运：获得 {rod_name}！")
            
            # 寻宝
            treasure_triggered = random.random() < treasure_val
            if treasure_triggered:
                treasure_gold = random.randint(
                    int(50 + treasure_val * 200),
                    int(150 + treasure_val * 500)
                )
                user.add_coins(treasure_gold)
                bonus_msgs.append(f"💎 寻宝发现：获得 {treasure_gold} 金币！")
            
            # 保存
            await self.storage.save_user(user)
            
            # 更新排行榜
            await self.storage.add_user_to_leaderboard(
                user_id, 
                user.total_fish_count, 
                event.get_sender_name(), 
                user.level
            )
            
            # 构建结果
            event_msgs = []
            if lucky_events["free_bait"]:
                event_msgs.append("✨ 本次钓鱼不消耗鱼饵！")
            if lucky_events["double_fish"]:
                event_msgs.append("✨ 双倍钓鱼！")
            if harvest_triggered:
                event_msgs.append("🌾 丰收触发！")
            if tide_triggered:
                event_msgs.append("🌊 潮汐之力涌动！")
            
            fish_lines = []
            for i, r in enumerate(fish_results, 1):
                if len(fish_results) > 1:
                    fish_lines.append(f"  [{i}] {r['rarity_emoji']}{r['fish_name']}")
                    fish_lines.append(f"  💰 售价: {r['price']} 金币")
                else:
                    fish_lines.append(f"{r['rarity_emoji']}{r['fish_name']}")
                    fish_lines.append(f"💰 售价: {r['price']} 金币")
            
            result_lines = ["🎣 钓鱼成功！"]
            if event_msgs:
                result_lines.append(" ".join(event_msgs))
            result_lines.append("")
            result_lines.extend(fish_lines)
            exp_line = f"📈 经验 +{total_exp}"
            if exp_boost_val > 0:
                exp_line += f"（含神慧+{int(exp_boost_val*100)}%）"
            result_lines.append(exp_line)
            if tide_triggered:
                result_lines.append("⏰ 冷却: 无需冷却 🌊")
            else:
                cd_line = f"⏰ 冷却 {self._format_time(effective_cooldown)}"
                if swift_val > 0:
                    cd_line += f" ⚡-{int(swift_val*100)}%"
                result_lines.append(cd_line)
            result_lines.append(f"🐟 累计钓鱼 {user.total_fish_count} 次")
            
            result = "\n".join(result_lines)
            
            # 神话鱼显示描述
            for r in fish_results:
                if r.get("desc"):
                    result += f"\n📖 {r['desc']}"
            
            if bonus_msgs:
                result += "\n\n" + "\n".join(bonus_msgs)
            
            if leveled_up:
                level_info = get_level_info(new_level)
                result += f"\n\n🎉 升级！现在是 {level_info['name']}！"
            
            return result
    
    async def cmd_bag(self, event) -> str:
        """背包命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            # 基础信息
            level_info = get_level_info(user.level)
            next_exp = get_next_level_exp(user.level)
            
            result = f"""📦 背包信息

👤 {event.get_sender_name()}
🏷️ {level_info['name']} (Lv.{user.level})
💰 金币: {user.coins}
📈 经验: {user.exp}{'' if next_exp is None else f' / {next_exp}'}
🐟 累计钓鱼: {user.total_fish_count} 次

🎣 当前钓竿: {self._format_rod_name(user.current_rod)}{self._format_rod_skills(user.current_rod["prefix_id"])}

🪤 鱼饵:"""
            
            for bait in user.get_baits():
                bait_base = get_bait_by_id(bait["base_id"])
                bait_prefix = self._get_bait_prefix(bait["prefix_id"])
                if bait_base and bait_prefix:
                    result += f"\n  • {bait_prefix['name']}{bait_base['name']} x{bait['count']}"
            
            if not user.get_baits():
                result += "\n  (无)"
            
            result += "\n\n🐠 渔获:"
            for fish in user.get_fish_inventory():
                fish_info = get_fish_by_id(fish["fish_id"])
                prefix = get_prefix_by_id(fish["prefix_id"])
                if fish_info and prefix:
                    result += f"\n  • [{fish['fish_id']}] {prefix['name']}{fish_info['name']} x{fish['count']}"
            
            if not user.get_fish_inventory():
                result += "\n  (无)"
            
            # 添加冷却倒计时
            fishing_cd = user.get_fishing_cd_remaining()
            cd_text = "好了" if fishing_cd <= 0 else self._format_time(fishing_cd)
            result += f"\n\n⏰ 钓鱼冷却: {cd_text}"
            
            return result
    
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
    
    async def cmd_level(self, event) -> str:
        """等级命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            level_info = get_level_info(user.level)
            next_exp = get_next_level_exp(user.level)
            
            result = f"""📊 等级信息

🏷️ {level_info['name']} (Lv.{user.level})
📈 经验: {user.exp}
"""
            
            if next_exp:
                need_exp = next_exp - user.exp
                denom = next_exp - level_info["exp_required"]
                if denom > 0:
                    progress = (user.exp - level_info["exp_required"]) / denom * 100
                    progress = max(0, min(100, progress))
                else:
                    progress = 100.0
                result += f"⬆️ 下一级需要: {need_exp} 经验\n"
                result += f"[{'█' * int(progress/5)}{'░' * (20-int(progress/5))}] {progress:.1f}%"
            else:
                result += "🏆 已达满级！"
            
            return result
    
    async def cmd_collection(self, event) -> str:
        """图鉴命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            collection = user.get_collection()
            
            # 计算总可收集数（所有鱼种 × 所有前缀组合）
            total_collectible = len(FISH_TYPES) * len(FISH_PREFIXES)
            collected_count = len(collection)
            progress_pct = (collected_count / total_collectible * 100) if total_collectible > 0 else 0
            
            result = f"""📖 钓鱼图鉴

已收集: {collected_count} / {total_collectible} ({progress_pct:.1f}%)"""
            
            # 按稀有度分组统计
            rarity_counts = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
            rarity_totals = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
            
            # 先计算各稀有度理论总数
            for fish in FISH_TYPES:
                for prefix in FISH_PREFIXES:
                    rarity_counts.setdefault(fish["rarity"], 0)
                    rarity_totals.setdefault(fish["rarity"], 0)
                    rarity_totals[fish["rarity"]] += 1
            
            # 再统计实际收集数
            rarity_counts = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
            rarity_items = {"common": [], "rare": [], "legendary": [], "mythic": []}
            
            for key, info in collection.items():
                fish_id, prefix_id = key.split("#")
                fish = get_fish_by_id(fish_id)
                prefix = get_prefix_by_id(prefix_id)
                if fish and prefix:
                    rarity = fish["rarity"]
                    fish_name = f"{prefix['name']}{fish['name']}"
                    count = info.get("count", 1)
                    rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
                    rarity_items.setdefault(rarity, []).append(f"{fish_name} x{count}")
            
            # 重新计算理论总数（确保稀有度键存在）
            rarity_totals = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
            for fish in FISH_TYPES:
                for prefix in FISH_PREFIXES:
                    rarity_totals[fish["rarity"]] = rarity_totals.get(fish["rarity"], 0) + 1
            
            rarity_names = {"common": "常见", "rare": "稀有", "legendary": "传说", "mythic": "神话"}
            rarity_emojis = {"common": "🔹", "rare": "🔷", "legendary": "⭐", "mythic": "🌟"}
            
            result += "\n\n📊 稀有度统计:"
            for rarity in ["mythic", "legendary", "rare", "common"]:
                cnt = rarity_counts.get(rarity, 0)
                tot = rarity_totals.get(rarity, 0)
                pct = (cnt / tot * 100) if tot > 0 else 0
                result += f"\n{rarity_emojis[rarity]} {rarity_names[rarity]}: {cnt}/{tot} ({pct:.1f}%)"
            
            # 显示最近收集的鱼类（按首次获得时间排序）
            sorted_items = sorted(collection.items(), key=lambda x: x[1].get("first_at", 0), reverse=True)
            if sorted_items:
                result += "\n\n📜 最近收集:"
                for key, info in sorted_items[:10]:
                    fish_id, prefix_id = key.split("#")
                    fish = get_fish_by_id(fish_id)
                    prefix = get_prefix_by_id(prefix_id)
                    if fish and prefix:
                        fish_name = f"{prefix['name']}{fish['name']}"
                        rarity_emoji = {"common": "", "rare": "", "legendary": "⭐", "mythic": "🌟"}.get(fish["rarity"], "")
                        result += f"\n  {rarity_emoji}{fish_name}"
            
            return result
    
    async def cmd_cd(self, event) -> str:
        """冷却命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            fishing_cd = user.get_fishing_cd_remaining()
            shop_cd = max(0, user.shop_refresh_cd - int(time.time())) if user.shop_refresh_cd > int(time.time()) else 0
            
            result = """⏰ 冷却状态

🎣 钓鱼: """
            if user.is_fishing_ready():
                result += "好了 ✓"
            else:
                result += self._format_time(fishing_cd)
            
            result += "\n🏪 商店刷新: "
            if user.is_shop_refresh_ready():
                result += "好了 ✓"
            else:
                result += self._format_time(shop_cd)
            
            return result
    
    def _render_shop_text(self, items: list) -> str:
        """将商品列表渲染为商店文本（纯渲染，无IO/无锁）"""
        # 特殊物品的名称映射（不需要 base_id/prefix_id 的物品）
        SPECIAL_NAMES = {
            "refresh_token": "🔄 刷新券",
        }
        result = """🏪 钓鱼商店

"""
        for i, item in enumerate(items, 1):
            item_type = item["type"]
            if item_type == "rod":
                base = get_rod_by_id(item["base_id"])
                prefix = self._get_rod_prefix(item["prefix_id"])
                name = f"{prefix['name']}{base['name']}"
            elif item_type in SPECIAL_NAMES:
                # 特殊物品（如刷新券）：使用映射名称，不访问 base_id
                name = SPECIAL_NAMES[item_type]
            else:
                base = get_bait_by_id(item["base_id"])
                prefix = self._get_bait_prefix(item["prefix_id"])
                name = f"{prefix['name']}{base['name']}"
            
            result += f"{i}. [{item_type}] {name}"
            if "quantity" in item:
                result += f" x{item['quantity']}"
            result += f" - {item['price']} 金币\n"
        
        result += "\n💡 使用 /购买 [编号] [数量] 购买"
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
                items = self._generate_shop_items(user)
                user.set("current_shop", items)
                await self.storage.save_user(user)
            
            return self._render_shop_text(items)
    
    async def cmd_buy(self, event, index: int, quantity: int = 1) -> str:
        """购买命令"""
        # 特殊物品名称映射（与 _render_shop_text 保持一致）
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
            
            # 执行购买
            user.remove_coins(total_price)
            
            if item["type"] == "rod":
                if quantity > 1:
                    return "钓竿每次只能购买 1 根"
                if user.has_rod(item["base_id"], item["prefix_id"]):
                    return "你已经拥有这根钓竿，无需重复购买"
                user.add_rod(item["base_id"], item["prefix_id"])
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
                prefix = self._get_rod_prefix(item["prefix_id"])
                name = f"{prefix['name']}{base['name']}"
            elif item["type"] in SPECIAL_NAMES:
                name = SPECIAL_NAMES[item["type"]]
            else:
                base = get_bait_by_id(item["base_id"])
                prefix = self._get_bait_prefix(item["prefix_id"])
                name = f"{prefix['name']}{base['name']}"
            
            return f"✅ 购买成功！\n\n获得: {name} x{quantity}\n花费: {total_price} 金币\n剩余: {user.coins} 金币"
    
    def _generate_shop_items(self, user: UserData) -> list:
        """根据用户等级和已拥有物品生成商店商品"""
        level = user.level
        items = []
        
        # 钓竿（过滤已拥有的）
        for rod in SHOP_ITEMS["rods"]:
            if rod["min_level"] <= level:
                for prefix in ROD_PREFIXES:
                    if "min_level" not in prefix or prefix["min_level"] <= level:
                        # 过滤已拥有的钓竿
                        if user.has_rod(rod["base_id"], prefix["id"]):
                            continue
                        base = get_rod_by_id(rod["base_id"])
                        price = rod["price"] * prefix["multiplier"]
                        if price > 0:  # 0价格为赠品
                            items.append({
                                "type": "rod",
                                "base_id": rod["base_id"],
                                "prefix_id": prefix["id"],
                                "price": int(price)
                            })
        
        # 鱼饵
        for bait in SHOP_ITEMS["baits"]:
            if bait["min_level"] <= level:
                for prefix in BAIT_PREFIXES:
                    if "min_level" not in prefix or prefix["min_level"] <= level:
                        base = get_bait_by_id(bait["base_id"])
                        price = bait["price"] * prefix["multiplier"]
                        items.append({
                            "type": "bait",
                            "base_id": bait["base_id"],
                            "prefix_id": prefix["id"],
                            "quantity": bait["quantity"],
                            "price": int(price)
                        })
        
        # 刷新券
        for special in SHOP_ITEMS.get("special", []):
            if special["min_level"] <= level:
                items.append({
                    "type": special["id"],
                    "price": special["price"]
                })
        
        # 随机选最多6个（不足6个时全量展示）
        if len(items) > 6:
            items = random.sample(items, 6)
        
        return items
    
    async def cmd_shop_refresh(self, event) -> str:
        """刷新商店命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            # 检查冷却
            if not user.is_shop_refresh_ready():
                remaining = max(0, user.shop_refresh_cd - int(time.time()))
                return f"商店刷新冷却中，剩余 {self._format_time(remaining)}"
            
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
            items = self._generate_shop_items(user)
            user.set("current_shop", items)
            await self.storage.save_user(user)
            
            result = self._render_shop_text(items)
            refresh_msg = "（使用刷新券）" if refresh_token_used else "（消耗 50 金币）"
            return f"✅ 商店已刷新{refresh_msg}！\n\n" + result
    
    async def cmd_rank(self, event) -> str:
        """排行榜命令"""
        user_id = event.get_sender_id()
        user = await self.storage.get_user(user_id)
        
        leaderboard = await self.storage.get_leaderboard()
        
        if not leaderboard:
            return "🏆 排行榜\n\n暂无数据"
        
        result = "🏆 钓鱼排行榜\n\n"
        for i, data in enumerate(leaderboard, 1):
            if len(data) == 4:
                uid, count, name, level = data
            else:
                uid, count = data
                name, level = "未知", 1
            emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            result += f"{emoji} {name} Lv.{level}  {count} 次钓鱼\n"
        
        # 查找当前用户排名（基于排行榜数据，仅参考）
        user_count = user.total_fish_count
        rank = sum(1 for _, count, _, _ in leaderboard if count > user_count) + 1 if leaderboard else 1
        
        result += f"\n📍 你的排名: 第{rank}名 ({user_count}次)"
        
        return result
    
    async def cmd_give(self, event, target_user: str, item_type: str, item_id: str, quantity: int = 1) -> str:
        """赠送命令"""
        from .fish_data import GIVE_LIMITS
        
        sender_id = event.get_sender_id()
        receiver_id = self._extract_target_user_id(target_user)
        
        if not receiver_id:
            return "无法识别目标用户，请使用 @用户 的格式"
        if sender_id == receiver_id:
            return "不能赠送给自己"
        
        # 排序加锁，防止死锁
        first_id, second_id = sorted([sender_id, receiver_id])
        async with self._get_user_lock(first_id):
            async with self._get_user_lock(second_id):
                sender = await self.storage.get_user(sender_id)
                
                # 检查赠送次数（自动重置过期的计数）
                sender.check_and_reset_daily_give()
                if sender.daily_give_count >= GIVE_LIMITS["daily_limit"]:
                    return f"今日赠送次数已用完（{GIVE_LIMITS['daily_limit']}/天）"
                
                # 限制数量
                if quantity > GIVE_LIMITS["max_per_give"]:
                    return f"单次最多赠送 {GIVE_LIMITS['max_per_give']} 个"
                
                # 检查接收者是否存在
                if not await self.storage.user_exists(receiver_id):
                    return f"目标用户不存在或尚未玩过钓鱼游戏"
                
                receiver = await self.storage.get_user(receiver_id)
                
                # 计算被赠送者获得的经验
                exp_gained = 0
                if item_type == "coins":
                    exp_gained = int(quantity * 0.05)
                elif item_type == "fish":
                    fish_info = get_fish_by_id(item_id)
                    if fish_info:
                        exp_gained = int(fish_info["base_price"] * quantity * 0.05)
                    else:
                        exp_gained = int(quantity * 10 * 0.05)
                elif item_type == "bait":
                    bait_info = get_bait_by_id(item_id)
                    if bait_info:
                        exp_gained = int((bait_info.get("exp_multiplier", 1.0) * 50) * quantity * 0.05)
                    else:
                        exp_gained = int(quantity * 5 * 0.05)
                
                # 验证：赠送渔获/鱼饵时必须提供ID
                if item_type in ("fish", "bait") and not item_id:
                    return "请指定要赠送的物品ID，先使用 /背包 查看你拥有的物品ID，如 /赠送 @用户 fish fish_003 2"
                
                # 处理金币赠送
                if item_type == "coins":
                    if sender.coins < quantity:
                        return f"金币不足！你只有 {sender.coins} 金币"
                    sender.remove_coins(quantity)
                    sender.add_give()
                    
                    # 保存 sender，失败则回滚
                    try:
                        await self.storage.save_user(sender)
                    except Exception as e:
                        sender.add_coins(quantity)
                        return f"赠送失败：无法保存你的数据（{e}）"
                    
                    # 给 receiver 增加金币和经验
                    try:
                        receiver.add_coins(quantity)
                        receiver.add_exp(exp_gained)
                        await self.storage.save_user(receiver)
                    except Exception as e:
                        # receiver 保存失败，尝试回滚 sender
                        try:
                            sender.add_coins(quantity)
                            sender._data["daily_give_count"] = max(0, sender._data.get("daily_give_count", 1) - 1)
                            await self.storage.save_user(sender)
                        except Exception:
                            pass
                        return f"赠送失败：目标用户数据保存异常（{e}），已尝试回滚"
                    
                    return f"✅ 已赠送 {quantity} 金币给 {target_user}（+{exp_gained} 经验）"
                
                # 处理渔获/鱼饵
                if item_type == "fish":
                    actual_prefix_id = None
                    for fish in sender.get_fish_inventory():
                        if fish["fish_id"] == item_id and fish.get("count", 0) >= quantity:
                            actual_prefix_id = fish["prefix_id"]
                            break
                    if not actual_prefix_id:
                        return f"背包中没有足够的 ID 为 {item_id} 的渔获"
                    
                    if not sender.remove_fish(item_id, actual_prefix_id, quantity):
                        return "你没有足够的渔获可以赠送"
                    sender.add_give()
                    
                    try:
                        await self.storage.save_user(sender)
                    except Exception as e:
                        sender.add_fish(item_id, actual_prefix_id, quantity)
                        return f"赠送失败：无法保存你的数据（{e}）"
                    
                    try:
                        receiver.add_fish(item_id, actual_prefix_id, quantity)
                        receiver.add_exp(exp_gained)
                        await self.storage.save_user(receiver)
                    except Exception as e:
                        try:
                            sender.add_fish(item_id, actual_prefix_id, quantity)
                            sender._data["daily_give_count"] = max(0, sender._data.get("daily_give_count", 1) - 1)
                            await self.storage.save_user(sender)
                        except Exception:
                            pass
                        return f"赠送失败：目标用户数据保存异常（{e}），已尝试回滚"
                    
                    return f"✅ 已赠送渔获 x{quantity} 给 {target_user}（+{exp_gained} 经验）"
                
                if item_type == "bait":
                    actual_prefix_id = None
                    for bait in sender.get_baits():
                        if bait["base_id"] == item_id and bait.get("count", 0) >= quantity:
                            actual_prefix_id = bait["prefix_id"]
                            break
                    if not actual_prefix_id:
                        return f"背包中没有足够的 ID 为 {item_id} 的鱼饵"
                    
                    if not sender.remove_bait(item_id, actual_prefix_id, quantity):
                        return "你没有足够的鱼饵可以赠送"
                    sender.add_give()
                    
                    try:
                        await self.storage.save_user(sender)
                    except Exception as e:
                        sender.add_bait(item_id, actual_prefix_id, quantity)
                        return f"赠送失败：无法保存你的数据（{e}）"
                    
                    try:
                        receiver.add_bait(item_id, actual_prefix_id, quantity)
                        receiver.add_exp(exp_gained)
                        await self.storage.save_user(receiver)
                    except Exception as e:
                        try:
                            sender.add_bait(item_id, actual_prefix_id, quantity)
                            sender._data["daily_give_count"] = max(0, sender._data.get("daily_give_count", 1) - 1)
                            await self.storage.save_user(sender)
                        except Exception:
                            pass
                        return f"赠送失败：目标用户数据保存异常（{e}），已尝试回滚"
                    
                    return f"✅ 已赠送鱼饵 x{quantity} 给 {target_user}（+{exp_gained} 经验）"
                
                return "无效的物品类型"
