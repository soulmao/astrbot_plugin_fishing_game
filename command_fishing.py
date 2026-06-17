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
)
from .storage import StorageManager
import random
import time


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
            
            # 低等级+傲慢保护：提前检查，避免消耗鱼饵后空池
            if arrogant_val > 0 and user.level < 5:
                return "👑 傲慢的钓竿需要至少 5 级才能锁定传说品质鱼类。请提升等级后再试！"
            
            # 检查资源
            selected_bait = None
            if is_gold_rod:
                # 金币钓竿：消耗当前金币10%
                gold_cost = int(user.coins * 0.10)
                if user.coins < 100:
                    return "金币不足100，无法使用金币钓竿！"
                user.remove_coins(gold_cost)
            elif not is_carrot_rod:
                # 普通钓竿：检查鱼饵
                if user.get_total_bait_count() <= 0:
                    return "你没有鱼饵了，请先在商店购买或接受赠送！"
                selected_bait = user.current_bait
                bait_count = user.get_bait_count(selected_bait["base_id"], selected_bait["prefix_id"])
                # 贪婪/无尽贪婪模式消耗更多鱼饵，需确保数量充足
                if endless_greedy_val > 0:
                    min_bait_needed = 3
                elif greedy_val > 0:
                    min_bait_needed = 2
                else:
                    min_bait_needed = 1
                if bait_count < min_bait_needed:
                    selected_bait = None
                    for bait in user.get_baits():
                        if bait.get("count", 0) >= min_bait_needed:
                            selected_bait = bait
                            break
                    if not selected_bait:
                        if min_bait_needed > 1:
                            return f"鱼饵不足，{'无尽贪婪' if endless_greedy_val > 0 else '贪婪'}钓竿需要至少 {min_bait_needed} 个鱼饵！"
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
            
            # 贪婪模式：旧贪婪 / 无尽贪婪
            greedy_mode = ""
            if endless_greedy_val > 0:
                greedy_mode = "endless"
            elif greedy_val > 0:
                greedy_mode = "normal"
            
            greedy_multiplier = 1
            greedy_bonus_gold = 0
            greedy_bait_cost = 1
            greedy_cd_penalty = 0.0
            greedy_rarity_bonus = 0.0
            greedy_price_bonus = 0.0
            endless_backlash_chance = 0.0
            
            if greedy_mode == "normal":
                greedy_multiplier = random.randint(2, 5)
                # 贪婪馈赠：额外奖励一笔金币
                greedy_bonus_gold = random.randint(greedy_multiplier * 40, greedy_multiplier * 100)
                greedy_bait_cost = 2
                greedy_cd_penalty = 0.10
                greedy_rarity_bonus = 0.35
            elif greedy_mode == "endless":
                greedy_multiplier = random.randint(3, 7)
                greedy_bait_cost = 3
                greedy_cd_penalty = 0.25
                greedy_rarity_bonus = 0.50
                greedy_price_bonus = 0.20
                endless_backlash_chance = 0.20
            
            # 基础钓鱼次数（含双倍）
            base_count = 2 if lucky_events["double_fish"] else 1
            total_base_count = base_count * greedy_multiplier
            
            # 贪婪模式下每次钓鱼消耗更多鱼饵，否则1个
            bait_cost = greedy_bait_cost if greedy_mode else 1
            
            # 消耗资源（鱼饵）
            if not is_gold_rod and not is_carrot_rod and not lucky_events["free_bait"]:
                if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], bait_cost):
                    return "鱼饵消耗失败，请检查背包！"
            
            # 无尽贪婪：反噬判定（消耗鱼饵后，有概率一无所获并进入完整冷却）
            if greedy_mode == "endless" and random.random() < endless_backlash_chance:
                user.set_fishing_cooldown(self.star.fishing_cooldown)
                new_achievements = user.check_achievements()
                await self.storage.save_user(user)
                result = f"♾️ 无尽贪婪反噬！贪婪吞噬了一切，本次没有渔获...\n⏰ 冷却 {format_time(self.star.fishing_cooldown)}"
                for ach in new_achievements:
                    result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                return result
            
            fish_results = []
            total_exp = 0
            bait_shortage = False  # 是否因鱼饵不足提前中断
            
            # 执行基础钓鱼（含贪婪多倍）
            for i in range(total_base_count):
                # 贪婪额外次数消耗鱼饵（金币钓竿/胡萝卜钓竿除外）
                if i >= base_count and not is_gold_rod and not is_carrot_rod and not lucky_events["free_bait"]:
                    if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], bait_cost):
                        bait_shortage = True
                        break
                
                result = self._do_fish_once(user, rod, selected_bait, jealous_bonus=jealous_bonus)
                if result is None:
                    # 保存此前已获得的渔获/消耗，避免数据丢失
                    await self.storage.save_user(user)
                    return "👑 当前等级过低，傲慢的钓竿无法锁定任何传说/神话鱼类，请提升等级后再试！"
                fish_results.append(result)
                user.add_fish(result["fish_id"], result["prefix_id"], 1)
                user.add_to_collection(result["fish_id"], result["prefix_id"])
                user.increment_fish_count()
                user.add_rarity_count(result["rarity"])
                total_exp += result["exp"]
            
            # 贪婪馈赠金币在钓鱼成功后发放
            if greedy_bonus_gold > 0:
                user.add_coins(greedy_bonus_gold)

            # 丰收：概率额外钓到 unit_catch 条鱼（享受贪婪倍率）
            harvest_triggered = random.random() < harvest_val
            unit_catch = greedy_multiplier * base_count
            if harvest_triggered:
                for _ in range(unit_catch):
                    if not (is_gold_rod or is_carrot_rod or lucky_events["free_bait"]):
                        if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], bait_cost):
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
                                if not user.remove_bait(selected_bait["base_id"], selected_bait["prefix_id"], bait_cost):
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

            # 嫉妒的：见不得人好（钓到传说/神话鱼时概率额外消耗）
            jealous_gold_cost = 0
            jealous_exp_penalty = 0
            if jealous_val > 0:
                for r in all_results:
                    if r["rarity"] in ("legendary", "mythic") and random.random() < 0.25:
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
            if greedy_mode:
                effective_cooldown = int(effective_cooldown * (1 + greedy_cd_penalty))  # 贪婪延长冷却
            
            # 嫉妒的：妒火中烧（概率延长 30% 冷却）
            jealous_cd_penalty = False
            if jealous_val > 0 and random.random() < 0.20:
                effective_cooldown = int(effective_cooldown * 1.30)
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
                if random.random() < 0.10:
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
                if random.random() < 0.5:
                    # 添加新技能
                    current_skills = dict(rod.get("skills", {}))
                    available_skills = [s for s in get_available_skills() if s not in current_skills and s not in rod_prefix.get("skills", {})]
                    if available_skills:
                        new_skill = random.choice(available_skills)
                        new_val = round(random.uniform(0.10, 0.20), 2)
                        current_skills[new_skill] = new_val
                        user.update_rod_skills(rod["instance_id"], rod.get("enchant_count", 0), current_skills)
                        lucky_block_msgs.append(f"🎲 幸运方块！获得 {ROD_SKILL_DESCRIPTIONS.get(new_skill, new_skill)}+{int(new_val*100)}%")
                else:
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
            if greedy_mode == "normal":
                event_msgs.append(f"💰 贪婪触发！{greedy_multiplier}倍钓鱼")
            elif greedy_mode == "endless":
                event_msgs.append(f"♾️ 无尽贪婪触发！{greedy_multiplier}倍钓鱼")
                if bait_shortage:
                    event_msgs.append(f"⚠️ 已触发 {greedy_multiplier} 倍，因鱼饵不足实际钓到 {len(fish_results)} 条")
            if voyage_triggered:
                event_msgs.append(f"🧭 远航触发！额外{voyage_count}次")
            if greedy_bonus_gold > 0:
                event_msgs.append(f"💵 贪婪馈赠 +{greedy_bonus_gold} 金币")
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
                if greedy_mode == "normal":
                    cd_line += f" 💰+10%"
                elif greedy_mode == "endless":
                    cd_line += f" ♾️+25%"
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

    def _do_fish_once(self, user, rod, selected_bait=None, jealous_bonus: float = 0.0) -> dict:
        """执行一次钓鱼随机计算，返回结果字典；若无可选池则返回None
        selected_bait=None 时表示使用金币钓竿（不消耗鱼饵，按金币加成品质）
        jealous_bonus: 嫉妒前缀的额外稀有度加成
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
            rod_rarity_bonus += 0.50
        elif effective_skills.get("greedy"):
            rod_rarity_bonus += 0.35
        
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
            # 傲慢的钓竿睥睨：过滤常见/稀有鱼
            if rod_prefix.get("skills", {}).get("arrogant") and fish["rarity"] in ("common", "rare"):
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
        if rod_prefix.get("skills", {}).get("cursed") and random.random() < 0.10:
            cursed_prefix = get_prefix_by_id("pref_015")
            if cursed_prefix:
                selected_prefix = cursed_prefix
        
        price = int(selected_fish["base_price"] * selected_prefix["price_multiplier"])
        # 无尽贪婪：钓到的鱼价值提升 20%
        if effective_skills.get("endless_greedy"):
            price = int(price * 1.20)
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
        """计算嫉妒前缀的攀比之力：每有一个等级更高的玩家，稀有度权重 +5%，最高 +50%
        使用 StorageManager 中的等级分布缓存，避免每次钓鱼全量扫描用户。
        """
        try:
            higher_count = await self.storage.get_higher_level_count(user.level)
            return min(higher_count * 0.05, 0.50)
        except Exception:
            return 0.0
