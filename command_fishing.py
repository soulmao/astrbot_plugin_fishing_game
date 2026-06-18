"""钓鱼核心命令模块"""
from .commands_base import CommandBase
from .utils import (
    format_time, format_rod_name, format_rod_skills, format_bait_name,
    calc_enchant_price, weighted_random_choice, get_available_skills,
    can_apply_rod_prefix,
)
from .fish_data import (
    FISH_TYPES, FISH_PREFIXES, ROD_BASES, ROD_PREFIXES,
    BAIT_BASES, BAIT_PREFIXES, LEVELS, SHOP_ITEMS,
    get_fish_by_id, get_prefix_by_id, get_rod_by_id, get_bait_by_id,
    get_level_info, get_next_level_exp, ROD_SKILL_DESCRIPTIONS,
    ENCHANT_TICKETS, ENCHANT_CONFIG,
    calc_rod_value, calc_bait_value, calc_fish_value,
    get_rod_prefix, get_bait_prefix, scramble_text, add_pig_noise,
    SPECIAL_PREFIX_BALANCE, SPECIAL_ROD_BALANCE,
)
from .storage import StorageManager
import random
import time


# 贪婪模式配置：初始钓竿激活消耗、断线概率、售价倍率等
GREEDY_CONFIG = {
    "normal": {
        "name": "贪婪的",
        "initial_bait_cost": 2,
        # 即使首层立刻收杆也应覆盖额外鱼饵与冷却成本，避免玩家被迫继续冒险。
        "initial_reward_multiplier": 1.20,
        "base_break_chance": 0.15,
        "break_increment_per_stack": 0.12,
        "extra_break_per_extra_fish": 0.06,
        "base_rarity_bonus": 0.20,
        "rarity_bonus_per_stack": 0.08,
        # 后续层数适度提高收益，用高断线风险换取更明确的回报。
        "price_multipliers": [1.55, 2.05, 2.65, 3.35, 4.15, 5.05, 6.05, 7.15, 8.35, 9.65],
        "repair_wallet_rate": 0.02,
        "repair_chip_rate": 0.10,
        "break_extra_fish_cap": 3,
        "cd_penalty": 0.15,
    },
    "endless": {
        "name": "无尽贪婪的",
        "initial_bait_cost": 3,
        "initial_reward_multiplier": 1.40,
        "base_break_chance": 0.22,
        "break_increment_per_stack": 0.14,
        "extra_break_per_extra_fish": 0.08,
        "base_rarity_bonus": 0.30,
        "rarity_bonus_per_stack": 0.10,
        "price_multipliers": [1.90, 2.70, 3.70, 4.90, 6.30, 7.90, 9.70, 11.70, 13.90, 16.30],
        "repair_wallet_rate": 0.02,
        "repair_chip_rate": 0.10,
        "break_extra_fish_cap": 3,
        "cd_penalty": 0.30,
    },
}


class FishingCommands(CommandBase):
    """钓鱼核心命令处理器"""

    async def cmd_fish(self, event) -> str:
        """钓鱼命令 - 支持新前缀/技能/特种钓竿"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)

            # 检查冷却
            if not user.is_fishing_ready():
                remaining = user.get_fishing_cd_remaining()
                return f"钓鱼冷却中，剩余 {format_time(remaining)}"

            # 已有贪婪挂起状态时不允许重新钓鱼
            if user.is_greedy_active():
                return "💰 你已有挂起的贪婪状态！请先发送 /收杆 结算，或 /贪婪 继续赌一把。"

            # 每日签到（体现在第一次钓鱼中）
            today = time.strftime("%Y-%m-%d")
            checkin_msg = ""
            if user.last_fish_date != today:
                streak = user.update_checkin(today)
                reward_coins = min(50 + streak * 10, 200)
                reward_exp = 20 + streak * 5
                b_base, b_prefix, b_cnt, b_name = self._generate_random_bait()
                user.add_bait(b_base, b_prefix, b_cnt)
                user.add_coins(reward_coins)
                leveled_up_checkin, new_level_checkin = user.add_exp(reward_exp)
                checkin_msg = f"🔥 每日签到成功！连续 {streak} 天\n🎁 获得 {reward_coins} 金币、{b_name} x{b_cnt}、{reward_exp} 经验"
                if leveled_up_checkin:
                    level_info = get_level_info(new_level_checkin)
                    checkin_msg += f"\n🎉 升级！现在是 {level_info['name']}！"

            rod = user.current_rod
            rod_prefix = get_rod_prefix(rod["prefix_id"])
            # 叠加：前缀默认技能 + 附魔技能覆盖同名键
            skills = dict(rod_prefix.get("skills", {}))
            skills.update(rod.get("skills", {}) or {})

            # 判定特种钓竿
            is_gold_rod = rod["base_id"] == "rod_006"
            is_carrot_rod = rod["base_id"] == "rod_007"
            
            # 解析技能数值（提前到资源检查前，确保贪婪/无尽贪婪判定可用）
            swift_val = skills.get("swift", 0)
            lucky_val = skills.get("lucky", 0)
            harvest_val = skills.get("harvest", 0)
            treasure_val = skills.get("treasure", 0)
            tide_val = skills.get("tide", 0)
            exp_boost_val = skills.get("exp_boost", 0)
            voyage_val = skills.get("voyage", 0)
            mending_val = skills.get("mending", 0)
            greedy_val = skills.get("greedy", 0)
            endless_greedy_val = skills.get("endless_greedy", 0)
            cursed_val = skills.get("cursed", 0)
            fail_chance_val = skills.get("fail_chance", 0)
            coin_reduce_val = skills.get("coin_reduce", 0)
            lucky_block_val = skills.get("lucky_block", 0)
            arrogant_val = skills.get("arrogant", 0)
            jealous_val = skills.get("jealous", 0)

            # 金币钓竿自带寻宝，固定成本下仍保留鲜明的金币收益定位。
            if is_gold_rod:
                treasure_val = max(
                    treasure_val,
                    SPECIAL_ROD_BALANCE["gold_rod"]["treasure_chance"],
                )
            
            # 判定是否进入贪婪/无尽贪婪模式（无尽贪婪优先）
            greedy_mode = None
            if endless_greedy_val > 0:
                greedy_mode = "endless"
            elif greedy_val > 0:
                greedy_mode = "normal"

            # 低等级+傲慢保护：提前检查，避免消耗鱼饵后空池
            if arrogant_val > 0 and user.level < 5:
                return "👑 傲慢的钓竿需要至少 5 级才能锁定稀有以上渔获。请提升等级后再试！"
            
            # 检查资源
            selected_bait = None
            if is_gold_rod:
                # 金币钓竿改为固定成本，避免资产越多亏损越严重。
                gold_cost = self._calc_gold_rod_cast_cost()
                if user.coins < gold_cost:
                    return f"金币不足{gold_cost}，无法使用金币钓竿！"
                user.remove_coins(gold_cost)
            elif not is_carrot_rod:
                # 普通钓竿：检查鱼饵
                if user.get_total_bait_count() <= 0:
                    return "你没有鱼饵了，请先在商店购买或接受赠送！"
                selected_bait = user.current_bait
                bait_count = user.get_bait_count(selected_bait["base_id"], selected_bait["prefix_id"])
                # 贪婪/无尽贪婪模式需要一次激活鱼饵，其他模式每轮 1 个
                if greedy_mode:
                    min_bait_needed = GREEDY_CONFIG[greedy_mode]["initial_bait_cost"]
                else:
                    min_bait_needed = 1
                if bait_count < min_bait_needed:
                    selected_bait = None
                    for bait in user.get_baits():
                        if bait.get("count", 0) >= min_bait_needed:
                            selected_bait = bait
                            break
                    if not selected_bait:
                        if greedy_mode:
                            return f"鱼饵不足，{GREEDY_CONFIG[greedy_mode]['name']}钓竿需要至少 {min_bait_needed} 个鱼饵激活！"
                        return "你没有鱼饵了！"
            
            # 嫉妒的：攀比之力（等级差距带来稀有度加成）
            jealous_bonus = 0.0
            if jealous_val > 0:
                jealous_bonus = await self._calc_jealous_bonus(user)
            
            # 傲慢的：自负检查（必须搭配稀有及以上鱼饵）
            if arrogant_val > 0 and not is_gold_rod and not is_carrot_rod:
                if selected_bait is None:
                    return "👑 傲慢的钓竿拒绝与劣质鱼饵为伍！必须使用珍稀（香料饵）及以上品质鱼饵，但你当前没有可用鱼饵。"
                bait_base = get_bait_by_id(selected_bait["base_id"])
                bait_quality = bait_base.get("quality", "common") if bait_base else "common"
                quality_order = {"common": 0, "excellent": 1, "rare": 2, "legendary": 3}
                if quality_order.get(bait_quality, 0) < quality_order["rare"]:
                    # 自负：消耗鱼饵、无渔获、进入完整冷却
                    user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], 1)
                    user.set_fishing_cooldown(self.star.fishing_cooldown)
                    await self.storage.save_user(user)
                    return f"👑 傲慢的钓竿拒绝与劣质鱼饵为伍！必须使用珍稀（香料饵）及以上品质鱼饵。\n🐟 本次没有渔获，但已消耗 1 个 {format_bait_name(selected_bait)}。\n⏰ 进入 {format_time(self.star.fishing_cooldown)} 冷却。"
            
            # 迅捷前缀：钓鱼失败判定
            if fail_chance_val > 0 and random.random() < fail_chance_val:
                fail_cd = int(self.star.fishing_cooldown * 0.5)
                user.set_fishing_cooldown(fail_cd)
                new_achievements = user.check_achievements()
                await self.storage.save_user(user)
                result = f"💥 钓鱼失败！钓竿太不稳定了...\n⏰ 冷却 {format_time(fail_cd)}"
                for ach in new_achievements:
                    result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                return result
            
            # 鱼饵事件加成
            bait_event_bonus = 0
            if selected_bait is not None:
                bait_prefix_obj = get_bait_prefix(selected_bait["prefix_id"])
                bait_event_bonus = bait_prefix_obj.get("event_bonus", 0)
            
            # 幸运事件
            lucky_events = {
                "double_fish": random.random() < min(0.10 + lucky_val + bait_event_bonus, 0.50),
                "free_bait": random.random() < min(0.10 + lucky_val + bait_event_bonus, 0.50),
                "bonus_bait": random.random() < min(0.10 + lucky_val + bait_event_bonus, 0.50),
                "bonus_rod": random.random() < min(0.01 + lucky_val * 0.05 + bait_event_bonus * 0.05, 0.15),
            }

            # 基础钓鱼次数（含双倍），贪婪与普通模式共用
            base_count = 2 if lucky_events["double_fish"] else 1

            # 贪婪模式：激活后直接挂起，不进入冷却、不结算金币经验
            if greedy_mode:
                return await self._handle_greedy_start(
                    event, user, rod, selected_bait, greedy_mode,
                    base_count, jealous_bonus, lucky_events,
                    skills, checkin_msg
                )

            # 非贪婪模式：原流程继续
            total_base_count = base_count
            
            # 消耗资源（鱼饵）
            if not is_gold_rod and not is_carrot_rod and not lucky_events["free_bait"]:
                if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], 1):
                    return "鱼饵消耗失败，请检查背包！"
            
            fish_results = []
            total_exp = 0

            # 执行基础钓鱼
            for i in range(total_base_count):
                # 额外次数消耗鱼饵（金币钓竿/胡萝卜钓竿/免饵除外）
                if i >= base_count and not is_gold_rod and not is_carrot_rod and not lucky_events["free_bait"]:
                    if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], 1):
                        break

                result = self._do_fish_once(user, rod, selected_bait, jealous_bonus=jealous_bonus)
                if result is None:
                    await self.storage.save_user(user)
                    return "👑 当前等级过低，傲慢的钓竿无法锁定稀有以上渔获，请提升等级后再试！"
                fish_results.append(result)
                user.add_fish(result["fish_id"], result["prefix_id"], 1)
                user.add_to_collection(result["fish_id"], result["prefix_id"])
                user.increment_fish_count()
                user.add_rarity_count(result["rarity"])
                total_exp += result["exp"]

            # 丰收：概率额外钓到 unit_catch 条鱼
            harvest_triggered = random.random() < harvest_val
            unit_catch = base_count
            if harvest_triggered:
                for _ in range(unit_catch):
                    if not (is_gold_rod or is_carrot_rod or lucky_events["free_bait"]):
                        if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], 1):
                            break
                    result = self._do_fish_once(user, rod, selected_bait, jealous_bonus=jealous_bonus)
                    if result:
                        fish_results.append(result)
                        user.add_fish(result["fish_id"], result["prefix_id"], 1)
                        user.add_to_collection(result["fish_id"], result["prefix_id"])
                        user.increment_fish_count()
                        user.add_rarity_count(result["rarity"])
                        total_exp += result["exp"]

            # 远航技能判定
            voyage_triggered = False
            voyage_extra_cd = 0
            voyage_results = []
            voyage_count = 0
            if voyage_val > 0 and random.random() < voyage_val:
                voyage_count = min(total_exp // 20, 50)
                if voyage_count > 0:
                    voyage_triggered = True
                    # 每次额外钓鱼增加约 7.7% 基础冷却，高风险高回报
                    voyage_extra_cd = voyage_count * (self.star.fishing_cooldown // 13)
                    for _ in range(voyage_count):
                        for _ in range(unit_catch):
                            if not is_gold_rod and not is_carrot_rod and not lucky_events["free_bait"]:
                                if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], 1):
                                    break
                            result = self._do_fish_once(user, rod, selected_bait, jealous_bonus=jealous_bonus)
                            if result:
                                voyage_results.append(result)
                                user.add_fish(result["fish_id"], result["prefix_id"], 1)
                                user.add_to_collection(result["fish_id"], result["prefix_id"])
                                user.increment_fish_count()
                                user.add_rarity_count(result["rarity"])
                                total_exp += result["exp"]
                        else:
                            continue
                        break

            # 汇总当前结果用于嫉妒副作用计算
            all_results = fish_results + voyage_results

            # 贪婪模式下的事件提示（旧代码残留，已在上文提前返回）
            # 非贪婪模式继续原流程
            # 嫉妒的：见不得人好（钓到传说/神话鱼时概率额外消耗）
            jealous_gold_cost = 0
            jealous_exp_penalty = 0
            if jealous_val > 0:
                jealous_cfg = SPECIAL_PREFIX_BALANCE["jealous"]
                for r in all_results:
                    if r["rarity"] in ("legendary", "mythic") and random.random() < jealous_cfg["rare_catch_penalty_chance"]:
                        cost = int(r["price"] * 0.10)
                        if user.remove_coins(cost):
                            jealous_gold_cost += cost
                        else:
                            penalty = max(1, int(total_exp * 0.05))
                            total_exp = max(0, total_exp - penalty)
                            jealous_exp_penalty += penalty

            # 学徒前缀：经验加成，金币收益减少
            apprentice_exp_mult = 1.0
            apprentice_coin_mult = 1.0
            if exp_boost_val > 0 and coin_reduce_val > 0:
                # 学徒前缀同时有 exp_boost 和 coin_reduce
                apprentice_exp_mult = 1.0 + exp_boost_val
                apprentice_coin_mult = 1.0 - coin_reduce_val
            elif exp_boost_val > 0:
                apprentice_exp_mult = 1.0 + exp_boost_val
            
            total_exp = int(total_exp * apprentice_exp_mult)
            
            # 经验修补：按技能值概率触发，触发后将 50% 经验转化为金币
            mending_gold = 0
            if mending_val > 0 and random.random() < mending_val:
                mending_gold = int(total_exp * 0.5)
                total_exp = total_exp - mending_gold
                user.add_coins(mending_gold)
            
            # 设置冷却
            effective_cooldown = int(self.star.fishing_cooldown * (1 - swift_val))
            
            # 嫉妒的：妒火中烧（小概率延长冷却）
            jealous_cd_penalty = False
            jealous_cfg = SPECIAL_PREFIX_BALANCE["jealous"]
            if jealous_val > 0 and random.random() < jealous_cfg["cooldown_penalty_chance"]:
                effective_cooldown = int(effective_cooldown * jealous_cfg["cooldown_multiplier"])
                jealous_cd_penalty = True
            
            if voyage_triggered:
                effective_cooldown += voyage_extra_cd
            
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
            
            # 寻宝（学徒前缀减少金币收益）
            treasure_triggered = random.random() < treasure_val
            if treasure_triggered:
                treasure_gold = random.randint(
                    int(50 + treasure_val * 200),
                    int(150 + treasure_val * 500)
                )
                treasure_gold = int(treasure_gold * apprentice_coin_mult)
                user.add_coins(treasure_gold)
                bonus_msgs.append(f"💎 寻宝发现：获得 {treasure_gold} 金币！")
            
            # 附魔券掉落判定（1% 基础掉落率）
            ticket_dropped = None
            if random.random() < 0.01:
                ticket = weighted_random_choice(ENCHANT_TICKETS)
                user.add_enchant_ticket(ticket["id"], 1)
                ticket_dropped = ticket["name"]
            
            # 诅咒前缀：概率丢失非诅咒词条
            cursed_msgs = []
            if cursed_val > 0:
                if random.random() < SPECIAL_PREFIX_BALANCE["cursed"]["skill_loss_chance"]:
                    current_skills = dict(rod.get("skills", {}) or {})
                    non_cursed = [k for k in current_skills.keys() if k != "cursed"]
                    if non_cursed:
                        removed = random.choice(non_cursed)
                        current_skills.pop(removed)
                        new_enchant_count = max(0, rod.get("enchant_count", 0) - 1)
                        user.update_rod_skills(rod["instance_id"], new_enchant_count, current_skills)
                        curse_msg = f"👻 诅咒生效！{ROD_SKILL_DESCRIPTIONS.get(removed, removed)} 消失了..."
                        cursed_msgs.append(scramble_text(curse_msg, 0.8))
                        cursed_msgs.append("深渊凝视着你")
            
            # 幸运方块：随机添加或消除词条
            lucky_block_msgs = []
            if lucky_block_val > 0:
                lucky_cfg = SPECIAL_PREFIX_BALANCE["lucky_block"]
                lucky_roll = random.random()
                if lucky_roll < lucky_cfg["gain_chance"]:
                    # 添加新技能
                    current_skills = dict(rod.get("skills", {}))
                    available_skills = [s for s in get_available_skills() if s not in current_skills and s not in rod_prefix.get("skills", {})]
                    max_slots = rod_prefix.get("max_slots", 0)
                    if available_skills and len(current_skills) < max_slots:
                        new_skill = random.choice(available_skills)
                        new_val = round(random.uniform(
                            lucky_cfg["new_skill_min"], lucky_cfg["new_skill_max"]
                        ), 2)
                        current_skills[new_skill] = new_val
                        user.update_rod_skills(rod["instance_id"], rod.get("enchant_count", 0), current_skills)
                        lucky_block_msgs.append(f"🎲 幸运方块！获得 {ROD_SKILL_DESCRIPTIONS.get(new_skill, new_skill)}+{int(new_val*100)}%")
                    elif current_skills:
                        # 满槽时不浪费正面结果，随机强化一个已有词条。
                        upgraded = random.choice(list(current_skills.keys()))
                        old_val = current_skills[upgraded]
                        increase = random.uniform(lucky_cfg["upgrade_min"], lucky_cfg["upgrade_max"])
                        new_val = round(min(old_val + increase, lucky_cfg["skill_value_cap"]), 2)
                        current_skills[upgraded] = new_val
                        user.update_rod_skills(rod["instance_id"], rod.get("enchant_count", 0), current_skills)
                        lucky_block_msgs.append(
                            f"🎲 幸运方块！{ROD_SKILL_DESCRIPTIONS.get(upgraded, upgraded)}强化至+{int(new_val*100)}%"
                        )
                elif lucky_roll >= 1 - lucky_cfg["lose_chance"]:
                    # 消除一个非幸运方块词条
                    current_skills = dict(rod.get("skills", {}))
                    removable = [k for k in current_skills.keys() if k != "lucky_block"]
                    if removable:
                        removed = random.choice(removable)
                        current_skills.pop(removed)
                        user.update_rod_skills(rod["instance_id"], rod.get("enchant_count", 0), current_skills)
                        lucky_block_msgs.append(f"🎲 幸运方块！{ROD_SKILL_DESCRIPTIONS.get(removed, removed)} 消失了...")
            
            # 成就检查
            new_achievements = user.check_achievements()

            # 保存
            await self.storage.save_user(user)

            # 更新排行榜
            await self.storage.add_user_to_leaderboard(
                user_id, 
                user.total_fish_count, 
                event.get_sender_name(), 
                user.level
            )
            
            # ===== 构建结果 =====
            event_msgs = []
            if lucky_events["free_bait"]:
                event_msgs.append("✨ 本次钓鱼不消耗鱼饵！")
            if lucky_events["double_fish"]:
                event_msgs.append("✨ 双倍钓鱼！")
            if harvest_triggered:
                event_msgs.append("🌾 丰收触发！")
            if tide_triggered:
                event_msgs.append("🌊 潮汐之力涌动！")
            if voyage_triggered:
                event_msgs.append(f"🧭 远航触发！额外{voyage_count}次")
            if jealous_bonus > 0:
                event_msgs.append(f"💢 嫉妒加成 +{int(jealous_bonus*100)}%")
            if jealous_cd_penalty:
                event_msgs.append("💢 妒火中烧！冷却延长")
            if jealous_gold_cost > 0:
                event_msgs.append(f"💢 见不得人好 -{jealous_gold_cost} 金币")
            elif jealous_exp_penalty > 0:
                event_msgs.append(f"💢 见不得人好 -{jealous_exp_penalty} 经验")
            
            # 汇总渔获（折叠显示）
            rarity_groups = {"common": [], "rare": [], "legendary": [], "mythic": []}
            for r in all_results:
                rarity_groups[r["rarity"]].append(r)

            fish_lines = []
            total_fish_count = len(all_results)

            if total_fish_count > 5:
                # 折叠模式
                common_count = len(rarity_groups["common"])
                if common_count > 0:
                    common_value = sum(r["price"] for r in rarity_groups["common"])
                    fish_lines.append(f"🔹 常见鱼 x{common_count} (合计 {common_value} 金币)")
                for rarity in ["mythic", "legendary", "rare"]:
                    for r in rarity_groups[rarity]:
                        fish_lines.append(f"{r['rarity_emoji']}{r['fish_name']} 💰{r['price']}")
            else:
                for i, r in enumerate(all_results, 1):
                    if len(all_results) > 1:
                        fish_lines.append(f"  [{i}] {r['rarity_emoji']}{r['fish_name']}")
                        fish_lines.append(f"  💰 售价: {r['price']} 金币")
                    else:
                        fish_lines.append(f"{r['rarity_emoji']}{r['fish_name']}")
                        fish_lines.append(f"💰 售价: {r['price']} 金币")
            
            result_lines = []
            if checkin_msg:
                result_lines.append(checkin_msg)
                result_lines.append("")
            result_lines.append("🎣 钓鱼成功！")
            if event_msgs:
                result_lines.append(" ".join(event_msgs))
            result_lines.append("")
            result_lines.extend(fish_lines)
            
            exp_line = f"📈 经验 +{total_exp}"
            if exp_boost_val > 0 and not coin_reduce_val:
                exp_line += f"（含神慧+{int(exp_boost_val*100)}%）"
            elif coin_reduce_val > 0:
                exp_line += f"（含学徒加成+{int(exp_boost_val*100)}%）"
            result_lines.append(exp_line)
            
            if mending_gold > 0:
                result_lines.append(f"🔧 经验修补：{mending_gold} 经验转化为金币")
            
            if tide_triggered:
                result_lines.append("⏰ 冷却: 无需冷却 🌊")
            else:
                cd_line = f"⏰ 冷却 {format_time(effective_cooldown)}"
                if swift_val > 0:
                    cd_line += f" ⚡-{int(swift_val*100)}%"
                if voyage_triggered:
                    cd_line += f" 🧭+{format_time(voyage_extra_cd)}"
                result_lines.append(cd_line)
            result_lines.append(f"🐟 累计钓鱼 {user.total_fish_count} 次")
            
            result = "\n".join(result_lines)
            
            # 神话鱼显示描述
            shown_descs = set()
            for r in all_results:
                if r.get("desc") and r["desc"] not in shown_descs:
                    result += f"\n📖 {r['desc']}"
                    shown_descs.add(r["desc"])
            
            if ticket_dropped:
                result += f"\n\n🎫 额外获得: {ticket_dropped} x1！"
            
            if bonus_msgs:
                result += "\n\n" + "\n".join(bonus_msgs)
            
            if cursed_msgs:
                result += "\n\n" + "\n".join(cursed_msgs)
            
            if lucky_block_msgs:
                result += "\n\n" + "\n".join(lucky_block_msgs)
            
            if leveled_up:
                level_info = get_level_info(new_level)
                result += f"\n\n🎉 升级！现在是 {level_info['name']}！"

            # 成就解锁提示
            for ach in new_achievements:
                result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"

            # 胡萝卜钓竿：插入猪符号
            if is_carrot_rod:
                result = add_pig_noise(result)
            
            return result

    def _do_fish_once(self, user, rod, selected_bait=None, jealous_bonus: float = 0.0,
                      extra_rarity_bonus: float = 0.0, price_multiplier: float = 1.0) -> dict:
        """执行一次钓鱼随机计算，返回结果字典；若无可选池则返回None
        selected_bait=None 时表示使用金币钓竿（不消耗鱼饵，按金币加成品质）
        jealous_bonus: 嫉妒前缀的额外稀有度加成
        extra_rarity_bonus: 贪婪模式每次循环叠加的额外稀有度加成
        price_multiplier: 贪婪模式对鱼售价的倍率加成
        """
        rod_base = get_rod_by_id(rod["base_id"])
        rod_prefix = get_rod_prefix(rod["prefix_id"])
        
        rod_exp_mult = rod_base["exp_multiplier"] * rod_prefix["multiplier"]
        rod_rarity_bonus = rod_base["rarity_bonus"] * rod_prefix["multiplier"]
        
        # 贪婪技能额外提升稀有度权重
        effective_skills = dict(rod_prefix.get("skills", {}) or {})
        if rod.get("skills"):
            effective_skills.update(rod.get("skills", {}))
        if effective_skills.get("endless_greedy"):
            rod_rarity_bonus += GREEDY_CONFIG["endless"]["base_rarity_bonus"]
        elif effective_skills.get("greedy"):
            rod_rarity_bonus += GREEDY_CONFIG["normal"]["base_rarity_bonus"]

        # 贪婪模式循环叠加的额外稀有度
        rod_rarity_bonus += extra_rarity_bonus

        # 嫉妒前缀：攀比之力带来的额外稀有度加成
        rod_rarity_bonus += jealous_bonus
        
        if selected_bait is not None:
            bait_base = get_bait_by_id(selected_bait["base_id"])
            bait_prefix = get_bait_prefix(selected_bait["prefix_id"])
            bait_exp_mult = bait_base["exp_multiplier"] * bait_prefix["multiplier"]
            bait_quality_bonus = bait_base["quality_bonus"] * bait_prefix["multiplier"]
        else:
            # 金币钓竿：无鱼饵加成，按金币增加稀有度权重
            bait_exp_mult = 1.0
            bait_quality_bonus = 0
            coin_bonus = min(user.coins / 20000, 0.50)  # 最多+50%
            rod_rarity_bonus += coin_bonus
        
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
            # 傲慢的钓竿睥睨：保底稀有，但不再直接保底传说，避免收益断层。
            if effective_skills.get("arrogant") and fish["rarity"] == "common":
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
        
        # 诅咒钓竿专属：10% 概率钓到"被诅咒的"鱼
        if effective_skills.get("cursed") and random.random() < SPECIAL_PREFIX_BALANCE["cursed"]["cursed_fish_chance"]:
            cursed_prefix = get_prefix_by_id("pref_015")
            if cursed_prefix:
                selected_prefix = cursed_prefix
        
        price = int(selected_fish["base_price"] * selected_prefix["price_multiplier"])
        # 应用贪婪售价倍率
        price = int(price * price_multiplier)
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

    async def _handle_greedy_start(self, event, user, rod, selected_bait, greedy_mode: str,
                                   base_count: int, jealous_bonus: float,
                                   lucky_events: dict, skills: dict,
                                   checkin_msg: str) -> str:
        """贪婪模式首次钓鱼：所有附魔词条仅在本次激活阶段生效。"""
        cfg = GREEDY_CONFIG[greedy_mode]
        activation_cost = cfg["initial_bait_cost"]
        is_gold_rod = rod["base_id"] == "rod_006"
        is_carrot_rod = rod["base_id"] == "rod_007"
        free_bait = lucky_events.get("free_bait", False)

        # 扣除激活鱼饵
        if not is_gold_rod and not is_carrot_rod and not free_bait:
            if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], activation_cost):
                return "鱼饵消耗失败，请检查背包！"

        fish_results = []

        def catch_once() -> bool:
            """钓取一条鱼并记录到贪欲结晶的原始渔获。"""
            result = self._do_fish_once(user, rod, selected_bait, jealous_bonus=jealous_bonus)
            if result is None:
                return False
            fish_results.append(result)
            user.increment_fish_count()
            user.add_rarity_count(result["rarity"])
            user.add_to_collection(result["fish_id"], result["prefix_id"])
            return True

        for _ in range(base_count):
            if not catch_once():
                await self.storage.save_user(user)
                return "👑 当前等级过低，傲慢的钓竿无法锁定稀有以上渔获，请提升等级后再试！"

        event_msgs = []

        # 丰收只在首次激活时判定一次，额外渔获由激活成本覆盖。
        if random.random() < skills.get("harvest", 0):
            for _ in range(base_count):
                catch_once()
            event_msgs.append("🌾 丰收触发！")

        # 远航只在首次激活时判定，后续贪婪层不再重复触发。
        voyage_extra_cd = 0
        if random.random() < skills.get("voyage", 0):
            current_exp = sum(r["exp"] for r in fish_results)
            voyage_count = min(current_exp // 20, 50)
            if voyage_count > 0:
                voyage_extra_cd = voyage_count * (self.star.fishing_cooldown // 13)
                for _ in range(voyage_count * base_count):
                    catch_once()
                event_msgs.append(f"🧭 远航触发！额外{voyage_count * base_count}次")

        chip = self._build_greedy_chip(fish_results)
        # 首层同样享受收益倍率，确保立即收杆也有合理回报。
        initial_reward_multiplier = cfg["initial_reward_multiplier"]
        chip["total_price"] = int(chip["total_price"] * initial_reward_multiplier)
        chip["total_exp"] = int(chip["total_exp"] * initial_reward_multiplier)

        # 神慧和经验修补仅处理首次形成的结晶，不作用于后续新增渔获。
        exp_boost = skills.get("exp_boost", 0)
        if exp_boost > 0:
            chip["total_exp"] = int(chip["total_exp"] * (1 + exp_boost))
            event_msgs.append(f"🧠 神慧生效！首次经验 +{int(exp_boost * 100)}%")
        if skills.get("mending", 0) > 0 and random.random() < skills["mending"]:
            mending_gold = int(chip["total_exp"] * 0.5)
            chip["total_exp"] -= mending_gold
            chip["total_price"] += mending_gold
            event_msgs.append(f"🔧 经验修补：{mending_gold} 经验转入结晶价值")

        # 寻宝奖励并入结晶，只有成功收杆后才能兑现。
        treasure_val = skills.get("treasure", 0)
        if treasure_val > 0 and random.random() < treasure_val:
            treasure_gold = random.randint(
                int(50 + treasure_val * 200),
                int(150 + treasure_val * 500),
            )
            chip["total_price"] += treasure_gold
            event_msgs.append(f"💎 寻宝发现：结晶价值 +{treasure_gold}")

        # 幸运的额外道具奖励也只在首次激活时判定。
        if lucky_events.get("bonus_bait"):
            bait_base_id, bait_prefix_id, bait_count, bait_name = self._generate_random_bait()
            user.add_bait(bait_base_id, bait_prefix_id, bait_count)
            event_msgs.append(f"🎁 幸运奖励：获得 {bait_name} x{bait_count}！")
        if lucky_events.get("bonus_rod"):
            rod_base_id, rod_prefix_id, rod_name = self._generate_random_rod()
            user.add_rod(rod_base_id, rod_prefix_id)
            event_msgs.append(f"🎁 超级幸运：获得 {rod_name}！")

        tide_triggered = skills.get("tide", 0) > 0 and random.random() < skills["tide"]
        if tide_triggered:
            event_msgs.append("🌊 潮汐触发！本轮贪婪结束后免冷却")

        effects = {
            "swift": skills.get("swift", 0),
            "tide_triggered": tide_triggered,
            "voyage_extra_cd": voyage_extra_cd,
        }
        user.start_greedy(
            rod["instance_id"], rod["prefix_id"],
            selected_bait or {}, chip, activation_cost, effects
        )

        # 成就检查（可能触发首次钓鱼等）
        new_achievements = user.check_achievements()
        await self.storage.save_user(user)
        await self.storage.add_user_to_leaderboard(
            user.user_id,
            user.total_fish_count,
            event.get_sender_name(),
            user.level
        )

        result_lines = []
        if checkin_msg:
            result_lines.append(checkin_msg)
            result_lines.append("")
        result_lines.append("🎣 钓鱼成功！")
        if free_bait:
            event_msgs.append("✨ 本次钓鱼不消耗鱼饵！")
        if base_count > 1:
            event_msgs.append("✨ 双倍钓鱼！")
        if event_msgs:
            result_lines.append(" ".join(event_msgs))
        result_lines.append("")
        result_lines.append(f"💰 {cfg['name']}钓竿发出一阵令人毛骨悚然的咀嚼声...")
        result_lines.append(f"🧿 你将 {chip['fish_count']} 条渔获揉碎融合为【{chip['name']}】")
        result_lines.append(f"💎 结晶基础价值: {chip['total_price']} 金币")
        result_lines.append(f"📈 结晶基础经验: {chip['total_exp']}")
        result_lines.append("")
        result_lines.append("可选操作：")
        result_lines.append("  /收杆 —— 立即结算当前结晶")
        result_lines.append("  /贪婪 —— 以结晶为饵继续赌一把（更高倍率，但可能断线爆仓）")

        result = "\n".join(result_lines)
        for ach in new_achievements:
            result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
        return result

    def _build_greedy_chip(self, fish_results: list) -> dict:
        """将多条渔获聚合为贪欲结晶"""
        total_price = sum(r["price"] for r in fish_results)
        total_exp = sum(r["exp"] for r in fish_results)
        rarity_counts = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
        rarity_order = {"common": 0, "rare": 1, "legendary": 2, "mythic": 3}
        max_rarity = "common"
        details = []
        for r in fish_results:
            rarity_counts[r["rarity"]] = rarity_counts.get(r["rarity"], 0) + 1
            if rarity_order[r["rarity"]] > rarity_order[max_rarity]:
                max_rarity = r["rarity"]
            details.append({
                "fish_name": r["fish_name"],
                "price": r["price"],
                "exp": r["exp"],
                "rarity": r["rarity"],
                "fish_id": r["fish_id"],
                "prefix_id": r["prefix_id"],
            })
        return {
            "name": "贪欲结晶",
            "total_price": total_price,
            "total_exp": total_exp,
            "fish_count": len(fish_results),
            "rarity_counts": rarity_counts,
            "max_rarity": max_rarity,
            "details": details,
        }

    def _get_greedy_total_multiplier(self, stack: int, mode: str) -> float:
        """获取贪婪第 stack 层的累计收益倍率。"""
        if stack <= 1:
            return GREEDY_CONFIG[mode]["initial_reward_multiplier"]
        cfg = GREEDY_CONFIG[mode]
        multipliers = cfg["price_multipliers"]
        idx = stack - 2
        if idx < len(multipliers):
            return multipliers[idx]
        # 超过预定义表后线性外推
        last = multipliers[-1]
        second_last = multipliers[-2]
        step = last - second_last
        return last + (idx - len(multipliers) + 1) * step

    def _get_greedy_extra_rarity_bonus(self, stack: int, mode: str) -> float:
        """获取第 stack 层相比初始的额外稀有度加成"""
        if stack <= 1:
            return 0.0
        cfg = GREEDY_CONFIG[mode]
        return (stack - 1) * cfg["rarity_bonus_per_stack"]

    def _calc_greedy_break_chance(self, stack: int, fish_count: int, mode: str) -> float:
        """计算断线概率，stack 为当前层数（至少 1）"""
        cfg = GREEDY_CONFIG[mode]
        chance = cfg["base_break_chance"] + (stack - 1) * cfg["break_increment_per_stack"]
        counted_fish = min(max(1, fish_count), cfg["break_extra_fish_cap"])
        chance += max(0, counted_fish - 1) * cfg["extra_break_per_extra_fish"]
        return min(chance, 0.95)

    def _calc_greedy_repair_cost(self, coins: int, chip_value: int, mode: str) -> int:
        """计算断线修理费，按钱包比例收取，但不超过结晶价值上限。"""
        cfg = GREEDY_CONFIG[mode]
        wallet_cost = int(max(0, coins) * cfg["repair_wallet_rate"])
        chip_cap = int(max(0, chip_value) * cfg["repair_chip_rate"])
        return min(wallet_cost, chip_cap)

    def _calc_gold_rod_cast_cost(self) -> int:
        """返回金币钓竿每次抛竿的固定金币成本。"""
        return SPECIAL_ROD_BALANCE["gold_rod"]["cast_cost"]

    def _get_greedy_effective_cooldown(self, state: dict, mode: str) -> int:
        """计算贪婪结束冷却，并兑现首次触发的迅捷、潮汐和远航效果。"""
        effects = state.get("effects", {}) or {}
        if effects.get("tide_triggered", False):
            return 0
        swift = min(max(float(effects.get("swift", 0)), 0.0), 1.0)
        base_cooldown = int(
            self.star.fishing_cooldown
            * (1 - swift)
            * (1 + GREEDY_CONFIG[mode]["cd_penalty"])
        )
        return max(0, base_cooldown + int(effects.get("voyage_extra_cd", 0)))

    async def cmd_greedy_continue(self, event) -> str:
        """贪婪继续命令 - 用贪欲结晶再次抛竿，可能断线爆仓或价值暴涨"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            if not user.is_greedy_active():
                return "💰 你没有挂起的贪婪状态，请先 /钓鱼 激活贪婪钓竿。"

            state = user.greedy_state
            mode = "endless" if state["rod_prefix_id"] == "rod_pref_19" else "normal"
            cfg = GREEDY_CONFIG[mode]
            stack = state["stack"]
            chip = state["chip"]

            # 断线判定
            break_chance = self._calc_greedy_break_chance(stack, chip["fish_count"], mode)
            if random.random() < break_chance:
                repair_cost = self._calc_greedy_repair_cost(
                    user.coins, chip.get("total_price", 0), mode
                )
                user.remove_coins(repair_cost)
                user.clear_greedy()
                effective_cooldown = self._get_greedy_effective_cooldown(state, mode)
                user.set_fishing_cooldown(effective_cooldown)
                new_achievements = user.check_achievements()
                await self.storage.save_user(user)
                await self.storage.add_user_to_leaderboard(
                    user_id, user.total_fish_count, event.get_sender_name(), user.level
                )
                result = (
                    f"💥 断线！贪欲结晶在剧烈震颤中崩解为虚无...\n"
                    f"🧿 你失去了挂起中的所有渔获与初始鱼饵\n"
                    f"🔧 修理鱼竿花费: {repair_cost} 金币\n"
                    f"⏰ 冷却 {format_time(effective_cooldown)}"
                )
                for ach in new_achievements:
                    result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                return result

            # 成功：继续钓一条鱼，并整锅按新倍率结算
            current_mult = self._get_greedy_total_multiplier(stack, mode)
            next_stack = stack + 1
            next_mult = self._get_greedy_total_multiplier(next_stack, mode)
            growth_ratio = next_mult / current_mult if current_mult > 0 else next_mult
            extra_rarity = self._get_greedy_extra_rarity_bonus(next_stack, mode)

            rod = user.current_rod
            if rod.get("instance_id") != state["rod_instance_id"]:
                return "❌ 你更换了触发贪婪的钓竿，当前挂起状态已冻结，请 /收杆 结算。"

            selected_bait = state.get("initial_bait") or None
            result = self._do_fish_once(
                user, rod, selected_bait,
                # 所有非贪婪词条只在首次激活时生效，后续层不再获得嫉妒加成。
                jealous_bonus=0.0,
                extra_rarity_bonus=extra_rarity,
                price_multiplier=1.0
            )
            if result is None:
                return "👑 当前等级过低，无法锁定稀有以上渔获。"

            # 整锅复利增长：新鱼加入后再按层数倍率提升
            chip["total_price"] = int((chip["total_price"] + result["price"]) * growth_ratio)
            chip["total_exp"] = int((chip["total_exp"] + result["exp"]) * growth_ratio)
            chip["fish_count"] += 1
            chip["rarity_counts"][result["rarity"]] = chip["rarity_counts"].get(result["rarity"], 0) + 1
            chip["details"].append({
                "fish_name": result["fish_name"],
                "price": result["price"],
                "exp": result["exp"],
                "rarity": result["rarity"],
                "fish_id": result["fish_id"],
                "prefix_id": result["prefix_id"],
            })
            rarity_order = {"common": 0, "rare": 1, "legendary": 2, "mythic": 3}
            if rarity_order[result["rarity"]] > rarity_order[chip["max_rarity"]]:
                chip["max_rarity"] = result["rarity"]

            # 统计与图鉴
            user.increment_fish_count()
            user.add_rarity_count(result["rarity"])
            user.add_to_collection(result["fish_id"], result["prefix_id"])
            user.update_greedy_chip(chip, stack_delta=1)

            new_achievements = user.check_achievements()
            await self.storage.save_user(user)
            await self.storage.add_user_to_leaderboard(
                user_id, user.total_fish_count, event.get_sender_name(), user.level
            )

            result_lines = [
                f"🎣 第 {next_stack} 层贪婪成功！",
                f"🐟 额外钓上: {result['rarity_emoji']}{result['fish_name']} 💰{result['price']}",
                f"🧿 【{chip['name']}】已膨胀至 {chip['total_price']} 金币（{chip['fish_count']} 条渔获聚合）",
                f"📈 当前累计经验: {chip['total_exp']}",
                f"⚠️ 下次断线概率: {int(self._calc_greedy_break_chance(next_stack, chip['fish_count'], mode) * 100)}%",
                "",
                "可选操作：/收杆 结算 或 /贪婪 继续",
            ]
            result_text = "\n".join(result_lines)
            for ach in new_achievements:
                result_text += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
            return result_text

    async def cmd_greedy_cashout(self, event) -> str:
        """贪婪收杆命令 - 结算当前贪欲结晶，获得金币与经验"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            if not user.is_greedy_active():
                return "💰 你没有挂起的贪婪状态，无需收杆。"

            state = user.greedy_state
            mode = "endless" if state["rod_prefix_id"] == "rod_pref_19" else "normal"
            cfg = GREEDY_CONFIG[mode]
            chip = state["chip"]
            stack = state["stack"]

            final_coins = chip["total_price"]
            final_exp = chip["total_exp"]

            user.add_coins(final_coins)
            leveled_up, new_level = user.add_exp(final_exp)
            user.clear_greedy()

            effective_cooldown = self._get_greedy_effective_cooldown(state, mode)
            user.set_fishing_cooldown(effective_cooldown)

            new_achievements = user.check_achievements()
            await self.storage.save_user(user)
            await self.storage.add_user_to_leaderboard(
                user_id, user.total_fish_count, event.get_sender_name(), user.level
            )

            result_lines = [
                "🎣 收杆成功！贪欲结晶稳稳落入你的背包...",
                f"🧿 结算层数: {stack}",
                f"💰 +{final_coins} 金币",
                f"📈 +{final_exp} 经验",
                "⏰ 冷却 无" if effective_cooldown == 0 else f"⏰ 冷却 {format_time(effective_cooldown)}",
            ]
            result = "\n".join(result_lines)
            if leveled_up:
                level_info = get_level_info(new_level)
                result += f"\n\n🎉 升级！现在是 {level_info['name']}！"
            for ach in new_achievements:
                result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
            return result

    def _generate_random_bait(self) -> tuple:
        """随机生成不受等级限制的鱼饵，返回 (base_id, prefix_id, count, name)"""
        base = random.choice(BAIT_BASES)
        prefix = random.choice(BAIT_PREFIXES)
        count = random.randint(1, 3)
        name = f"{prefix['name']}{base['name']}"
        return base["id"], prefix["id"], count, name

    def _generate_random_rod(self) -> tuple:
        """随机生成不受等级限制的钓竿，返回 (base_id, prefix_id, name)"""
        eligible_bases = [b for b in ROD_BASES if not b.get("no_prefix")]
        base = random.choice(eligible_bases)
        # 傲慢前缀等特殊前缀需校验基础钓竿兼容性
        eligible_prefixes = [p for p in ROD_PREFIXES if can_apply_rod_prefix(base["id"], p["id"])]
        if not eligible_prefixes:
            eligible_prefixes = ROD_PREFIXES
        prefix = random.choice(eligible_prefixes)
        name = f"{prefix['name']}{base['name']}"
        return base["id"], prefix["id"], name

    async def _calc_jealous_bonus(self, user) -> float:
        """计算嫉妒前缀的攀比之力：按高等级玩家数量提高稀有度权重。
        使用 StorageManager 中的等级分布缓存，避免每次钓鱼全量扫描用户。
        """
        try:
            higher_count = await self.storage.get_higher_level_count(user.level)
            cfg = SPECIAL_PREFIX_BALANCE["jealous"]
            return min(higher_count * cfg["bonus_per_higher_player"], cfg["max_rarity_bonus"])
        except Exception:
            return 0.0
