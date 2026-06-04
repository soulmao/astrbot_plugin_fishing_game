"""信息查询命令模块"""
import time

from .commands_base import CommandBase
from .utils import format_rod_name, format_rod_skills, format_time, format_bait_name
from .fish_data import (
    FISH_TYPES, FISH_PREFIXES, get_fish_by_id, get_prefix_by_id,
    get_level_info, get_next_level_exp, get_bait_prefix, get_bait_by_id,
)
from .storage import StorageManager


class InfoCommands(CommandBase):
    """信息查询命令处理器"""

    async def cmd_help(self, event) -> str:
        """帮助命令"""
        fishing_cd = format_time(self.star.fishing_cooldown)
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
  查看综合价值排行榜（库存价值 + 经验）

🎁 `/赠送 @用户 类型 ID [数量]` 或 `/give @用户 类型 ID [数量]`
  赠送金币/渔获/鱼饵/钓竿给其他用户
  类型: coins(金币), fish(渔获), bait(鱼饵), rod(钓竿)

🏪 `/拍卖` 或 `/auction`
  拍卖行：浏览/搜索/上架/出售/取消/购买物品
  /拍卖 列表 [页码] | /拍卖 搜索 <关键词>
  /拍卖 上架 <类型> <编号> [价格] | /拍卖 出售 <类型> <编号>
  /拍卖 取消 <编号> | /拍卖 购买 <编号>

✨ `/附魔 <钓竿编号>` 或 `/enchant <钓竿编号>`
  为钓竿随机附魔技能，消耗金币或附魔券

⬆️ `/附魔升级 <钓竿编号> <技能名>` 或 `/enchant_upgrade <编号> <技能>`
  升级指定钓竿的指定技能，消耗金币

————————————————

🐟 **游戏玩法：**
• 初始获得 100 金币、木制钓竿、10条蚯蚓
• 钓鱼获得渔获 → 卖鱼赚金币 → 购买更好的钓竿和鱼饵
• 更好的钓竿/鱼饵 = 更高稀有度 + 更多经验
• 升级解锁更强力的钓竿和鱼饵
• 高品质钓竿前缀自带词条技能（迅捷、幸运、丰收等）
• 钓竿可附魔和升级技能，每次附魔价格倍增
• 每日可赠送 10 次给好友
• 拍卖行可买卖物品，保留24小时

🔱 **钓竿词条技能：**
高品质钓竿前缀自带技能：
• ⚡迅捷 - 减少钓鱼冷却时间
• 🍀幸运 - 提升幸运事件触发概率
• 🌾丰收 - 概率额外钓到一条鱼
• 💎寻宝 - 概率获得额外金币
• 🌊潮汐 - 概率本次钓鱼无需冷却
• ✨神慧 - 获得额外经验加成
• 🧭远航 - 概率触发额外钓鱼
• 🔧经验修补 - 部分经验转化为金币

👻 **特殊前缀钓竿：**
神秘的词缀，拥有独特机制：
• 💰 贪婪的 - 有概率一次钓到多条鱼，但需要付出额外代价
• 👻 诅咒的 - 附魔和升级异常便宜，但钓竿不太稳定
• ⚡ 迅捷的 - 冷却极快，偶尔会出现失误
• 📚 学徒的 - 获得大量经验加成，但金币收益受限
• 🎲 幸运方块的 - 随机获得或失去技能，充满变数

🐉 **古龙收藏系列：**
稀有词缀，仅高级玩家可获得：
• 🎣 古龙收藏钓竿 - 极高幸运与全技能加成
• 🐟 古龙收藏鱼类 - 售价远超普通传说鱼
• 🪤 古龙收藏鱼饵 - 大幅加成随机事件触发率

📖 `/图鉴` - 查看已收集的鱼类图鉴进度"""
    
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

🎣 拥有的钓竿:"""
            
            current = user.current_rod
            for i, rod in enumerate(user.get_owned_rods(), 1):
                rod_name = format_rod_name(rod)
                skill_text = format_rod_skills(rod["prefix_id"], rod.get("skills"))
                enchant_text = f" [附魔{rod.get('enchant_count', 0)}次]" if rod.get('enchant_count', 0) > 0 else ""
                is_current = (rod.get("instance_id") == current.get("instance_id"))
                marker = " [当前装备]" if is_current else ""
                result += f"\n  {i}. {rod_name}{skill_text}{enchant_text}{marker}"
            
            if not user.get_owned_rods():
                result += "\n  (无)"
            
            result += "\n\n🪤 鱼饵:"
            for bait in user.get_baits():
                bait_base = get_bait_by_id(bait["base_id"])
                bait_prefix = get_bait_prefix(bait["prefix_id"])
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
            cd_text = "好了" if fishing_cd <= 0 else format_time(fishing_cd)
            result += f"\n\n⏰ 钓鱼冷却: {cd_text}"
            
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
                result += format_time(fishing_cd)
            
            result += "\n🏪 商店刷新: "
            if user.is_shop_refresh_ready():
                result += "好了 ✓"
            else:
                result += format_time(shop_cd)
            
            return result

    async def cmd_rank(self, event) -> str:
        """排行榜命令（库存价值 + 经验综合排行）"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            leaderboard = await self.storage.get_leaderboard()
            
            if not leaderboard:
                return "🏆 排行榜\n\n暂无数据"
            
            result = "🏆 富豪排行榜（库存价值 + 经验）\n\n"
            for i, data in enumerate(leaderboard[:10], 1):
                uid, score, name = data
                display = f"{name}({uid})" if name else uid
                emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                result += f"{emoji} {display}  综合价值: {score}\n"
            
            # 查找当前用户排名（遍历全部确保准确）
            my_score = user.get_total_inventory_value() + user.exp
            my_rank = 1
            for uid, score, _ in leaderboard:
                if uid == user_id:
                    break
                my_rank += 1
            else:
                my_rank = len(leaderboard) + 1
            
            my_name = event.get_sender_name() or user_id[:10]
            result += f"\n📍 你的排名: 第{my_rank}名 ({my_name} 综合价值: {my_score})"
            
            return result
