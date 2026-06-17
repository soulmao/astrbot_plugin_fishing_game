"""附魔系统命令模块"""
from .commands_base import CommandBase
from .utils import (
    format_rod_name, calc_enchant_price, calc_upgrade_price, get_available_skills,
    SKILL_NAME_MAP, parse_directed_enchant_id, ROD_SKILL_DESCRIPTIONS,
)
from .fish_data import get_rod_prefix, ENCHANT_CONFIG
from .storage import StorageManager
import random


class EnchantCommands(CommandBase):
    """附魔系统命令处理器"""

    async def cmd_enchant(self, event, rod_index: int = 0) -> str:
        """附魔命令 - 随机为钓竿附加/替换技能。rod_index=0 时默认附魔当前装备钓竿"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            rods = user.get_owned_rods()
            # rod_index=0 或未提供时，使用当前装备钓竿
            if rod_index < 1 or rod_index > len(rods):
                current = user.current_rod
                found = False
                for i, r in enumerate(rods, 1):
                    if r.get("instance_id") == current.get("instance_id"):
                        rod_index = i
                        found = True
                        break
                if not found:
                    return f"钓竿编号无效，你有 {len(rods)} 根钓竿"
            
            rod = dict(rods[rod_index - 1])
            prefix = get_rod_prefix(rod["prefix_id"])
            max_slots = prefix.get("max_slots", 0)
            
            if max_slots <= 0:
                return "这根钓竿没有附魔槽位，无法附魔"
            
            current_skills = dict(rod.get("skills", {}) or {})
            
            # 计算价格
            price = calc_enchant_price(rod)
            
            # 检查附魔券
            best_ticket = user.get_best_enchant_ticket()
            use_ticket = False
            ticket_discount = 0
            if best_ticket:
                use_ticket = True
                ticket_discount = best_ticket["discount"]
                final_price = int(price * (1 - ticket_discount))
            else:
                final_price = price
            
            if user.coins < final_price:
                return f"金币不足！附魔需要 {final_price} 金币，你只有 {user.coins} 金币"

            if use_ticket:
                if not user.remove_enchant_ticket(best_ticket["ticket_id"], 1):
                    return "附魔券扣除失败"

            user.remove_coins(final_price)
            
            # 执行附魔
            available = get_available_skills()
            prefix_skills = prefix.get("skills", {})
            # 安全技能：排除前缀自带的技能，防止低值附魔覆盖高值前缀技能
            safe_available = [s for s in available if s not in prefix_skills]
            
            # 新技能基础值在 10%~30% 之间随机
            new_skill_val = round(random.uniform(0.10, 0.30), 2)
            
            # 如果槽位已满，随机替换一个已有技能；否则随机新增一个
            if len(current_skills) >= max_slots:
                # 槽位已满，随机替换
                skill_to_replace = random.choice(list(current_skills.keys()))
                candidates = [s for s in safe_available if s != skill_to_replace]
                if not candidates:
                    # 回退：所有安全技能都被占，允许替换为任意非自身技能
                    candidates = [s for s in available if s != skill_to_replace]
                new_skill = random.choice(candidates)
                current_skills[new_skill] = new_skill_val
                del current_skills[skill_to_replace]
                result_msg = f"🎲 槽位已满，替换 {ROD_SKILL_DESCRIPTIONS.get(skill_to_replace, skill_to_replace)} → {ROD_SKILL_DESCRIPTIONS.get(new_skill, new_skill)}"
            else:
                # 新增技能：优先选前缀没有的安全技能
                remaining = [s for s in safe_available if s not in current_skills]
                if remaining:
                    new_skill = random.choice(remaining)
                else:
                    # 回退：所有安全技能都已附魔，允许获得前缀技能（但可能低值覆盖）
                    fallback = [s for s in available if s not in current_skills]
                    new_skill = random.choice(fallback if fallback else available)
                current_skills[new_skill] = new_skill_val
                result_msg = f"🎲 获得新技能 {ROD_SKILL_DESCRIPTIONS.get(new_skill, new_skill)}"
            
            new_enchant_count = rod.get("enchant_count", 0) + 1
            user.update_rod_skills(rod["instance_id"], new_enchant_count, current_skills)

            # 成就检查
            new_achievements = user.check_achievements()

            await self.storage.save_user(user)

            rod_name = format_rod_name(rod)
            ticket_msg = f"（使用{best_ticket['ticket_id']}，省{int(ticket_discount*100)}%）" if use_ticket else ""
            result = f"✨ 附魔成功！{ticket_msg}\n🎣 {rod_name}\n{result_msg}+{int(new_skill_val*100)}%\n📈 累计附魔 {new_enchant_count} 次"
            for ach in new_achievements:
                result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
            return result
    
    async def cmd_enchant_upgrade(self, event, arg1: str = "", arg2: str = "") -> str:
        """附魔升级命令 - 升级指定技能。自动识别参数: 纯数字为钓竿编号，其他为技能名"""
        user_id = event.get_sender_id()
        
        # 解析参数：纯数字是钓竿编号，其他是技能名
        rod_index = 0
        skill_name = ""
        for a in [arg1, arg2]:
            if not a:
                continue
            sa = str(a)
            # 第一个数字参数解析为钓竿编号，其余作为技能名
            if rod_index == 0 and sa.isdigit():
                rod_index = int(sa)
            elif not skill_name:
                skill_name = sa
        
        # 将中文技能名映射到ID
        skill_name_map = {
            "迅捷": "swift", "swift": "swift",
            "幸运": "lucky", "lucky": "lucky",
            "丰收": "harvest", "harvest": "harvest",
            "寻宝": "treasure", "treasure": "treasure",
            "潮汐": "tide", "tide": "tide",
            "神慧": "exp_boost", "exp_boost": "exp_boost",
            "远航": "voyage", "voyage": "voyage",
            "经验修补": "mending", "mending": "mending",
        }
        skill_id = skill_name_map.get(skill_name.lower(), skill_name.lower())
        if not skill_id:
            return "请指定要升级的技能名，如: /附魔升级 迅捷\n可选: 迅捷/幸运/丰收/寻宝/潮汐/神慧/远航/经验修补"
        
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            rods = user.get_owned_rods()
            # rod_index=0 或未提供时，使用当前装备钓竿
            if rod_index < 1 or rod_index > len(rods):
                current = user.current_rod
                found = False
                for i, r in enumerate(rods, 1):
                    if r.get("instance_id") == current.get("instance_id"):
                        rod_index = i
                        found = True
                        break
                if not found:
                    return f"钓竿编号无效，你有 {len(rods)} 根钓竿"
            
            rod = dict(rods[rod_index - 1])
            # 合并：前缀默认技能 + 附魔技能覆盖，支持升级自带技能
            prefix = get_rod_prefix(rod.get("prefix_id", ""))
            effective_skills = dict(prefix.get("skills", {}))
            effective_skills.update(rod.get("skills", {}) or {})
            
            if skill_id not in effective_skills:
                return f"该钓竿没有 {ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)} 技能，请先附魔"
            
            current_val = effective_skills[skill_id]
            # 自带技能允许突破 50% 上限，最高可升至 100%
            max_skill_val = max(ENCHANT_CONFIG["max_skill_value"], 1.0)
            if current_val >= max_skill_val:
                return f"{ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)} 已达到最高等级（{int(max_skill_val*100)}%）"
            
            # 计算升级价格
            price = calc_upgrade_price(rod)
            if user.coins < price:
                return f"金币不足！升级需要 {price} 金币，你只有 {user.coins} 金币"
            
            user.remove_coins(price)
            new_val = round(min(current_val + ENCHANT_CONFIG["upgrade_increment"], max_skill_val), 2)
            # 只更新被升级的技能到 rod["skills"]，保留原有附魔技能
            new_skills = dict(rod.get("skills", {}) or {})
            new_skills[skill_id] = new_val
            new_enchant_count = rod.get("enchant_count", 0) + 1
            user.update_rod_skills(rod["instance_id"], new_enchant_count, new_skills)

            # 成就检查
            new_achievements = user.check_achievements()

            await self.storage.save_user(user)

            rod_name = format_rod_name(rod)
            result = f"⬆️ 升级成功！\n🎣 {rod_name}\n{ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)}: {int(current_val*100)}% → {int(new_val*100)}%\n💰 花费: {price} 金币\n📈 累计附魔 {new_enchant_count} 次"
            for ach in new_achievements:
                result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
            return result

    async def cmd_directed_enchant(self, event, skill_name: str = "", tier_str: str = "") -> str:
        """定向附魔命令 - 使用背包中的定向附魔券为当前装备钓竿添加/升级技能"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)

            # 解析技能名
            skill_id = SKILL_NAME_MAP.get(skill_name.lower(), skill_name.lower())
            if skill_id not in get_available_skills():
                return f"❌ 未知技能: {skill_name}\n可选: 迅捷/幸运/丰收/寻宝/潮汐/神慧/远航/经验修补"

            # 解析档位
            tier_values = {"5": 0.05, "10": 0.10, "15": 0.15}
            target_value = None
            if tier_str:
                target_value = tier_values.get(tier_str)
                if target_value is None:
                    return "❌ 档位必须是 5、10 或 15"

            # 查找背包中的定向附魔券
            skill_label = ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)
            ticket_found = None
            ticket_item_id = None

            for item in user.get("items", []):
                parsed = parse_directed_enchant_id(item.get("id", ""))
                if not parsed:
                    continue
                t_skill, t_value = parsed
                if t_skill != skill_id:
                    continue
                if target_value is not None and t_value != target_value:
                    continue
                # 匹配成功，取最高档位
                if ticket_found is None or t_value > ticket_found[1]:
                    ticket_found = (t_skill, t_value)
                    ticket_item_id = item["id"]

            if not ticket_found:
                if target_value:
                    return f"❌ 背包中没有 {skill_label}+{int(target_value*100)}% 的定向附魔券"
                else:
                    return f"❌ 背包中没有 {skill_label} 的定向附魔券"

            skill_id_found, ticket_value = ticket_found

            # 获取当前装备钓竿
            rod = user.current_rod
            prefix = get_rod_prefix(rod["prefix_id"])
            max_slots = prefix.get("max_slots", 0)
            rod_skills = dict(rod.get("skills", {}) or {})

            # 合并前缀自带技能与附魔技能，用于计算当前有效值
            effective_skills = dict(prefix.get("skills", {}))
            effective_skills.update(rod_skills)

            # 检查安全技能槽（只统计附魔技能）
            if len(rod_skills) >= max_slots and skill_id not in rod_skills:
                return "❌ 安全技能槽已满，无法使用定向附魔券\n💡 请先通过 /附魔 腾出槽位，或升级已有技能"

            # 检查当前技能值上限
            current_val = effective_skills.get(skill_id, 0)
            if current_val >= 1.0:
                return f"❌ {skill_label} 已达到最高等级（100%）"

            # 新技能值 = 当前值 + 券面值，最高不超过 100%
            new_val = round(min(current_val + ticket_value, 1.0), 2)

            # 扣除券
            if not user.remove_item(ticket_item_id, 1):
                return "❌ 定向附魔券扣除失败"

            # 应用技能到附魔技能槽
            new_skills = dict(rod_skills)
            new_skills[skill_id] = new_val
            new_enchant_count = rod.get("enchant_count", 0) + 1
            user.update_rod_skills(rod["instance_id"], new_enchant_count, new_skills)

            # 成就检查
            new_achievements = user.check_achievements()

            await self.storage.save_user(user)

            rod_name = format_rod_name(rod)
            if current_val == 0:
                action_msg = f"获得新技能 {skill_label}+{int(new_val*100)}%"
            else:
                action_msg = f"升级 {skill_label} {int(current_val*100)}% +{int(ticket_value*100)}% → {int(new_val*100)}%"
            if new_val >= 1.0:
                action_msg += "（已达上限）"
            result = f"✨ 定向附魔成功！\n🎣 {rod_name}\n🎯 {action_msg}\n📈 累计附魔 {new_enchant_count} 次"

            for ach in new_achievements:
                result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"

            return result


    async def cmd_greedy_toggle(self, event, rod_index: int = 0) -> str:
        """在「贪婪的」与「无尽贪婪的」钓竿前缀之间切换。rod_index=0 时默认切换当前装备钓竿"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            rods = user.get_owned_rods()
            if rod_index < 1 or rod_index > len(rods):
                current = user.current_rod
                found = False
                for i, r in enumerate(rods, 1):
                    if r.get("instance_id") == current.get("instance_id"):
                        rod_index = i
                        found = True
                        break
                if not found:
                    return f"钓竿编号无效，你有 {len(rods)} 根钓竿"
            
            rod = dict(rods[rod_index - 1])
            current_prefix_id = rod.get("prefix_id", "")
            
            toggle_map = {
                "rod_pref_12": "rod_pref_19",
                "rod_pref_19": "rod_pref_12",
            }
            if current_prefix_id not in toggle_map:
                rod_name = format_rod_name(rod)
                return f"❌ {rod_name} 不是贪婪/无尽贪婪钓竿，无法切换"
            
            new_prefix_id = toggle_map[current_prefix_id]
            old_name = format_rod_name(rod)
            
            # 切换费用
            toggle_cost = 1000
            if user.coins < toggle_cost:
                return f"❌ 切换需要 {toggle_cost} 金币，你只有 {user.coins} 金币"
            
            if not user.remove_coins(toggle_cost):
                return "❌ 金币扣除失败"
            
            if not user.update_rod_prefix(rod["instance_id"], new_prefix_id):
                user.add_coins(toggle_cost)  # 回滚
                return "❌ 切换失败，请稍后再试"
            
            await self.storage.save_user(user)
            
            new_rod = dict(rod)
            new_rod["prefix_id"] = new_prefix_id
            new_name = format_rod_name(new_rod)
            
            return f"✅ 切换成功！\n🎣 {old_name} → {new_name}\n💰 消耗 {toggle_cost} 金币"
