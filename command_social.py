"""社交系统命令模块"""
from .commands_base import CommandBase
from .utils import format_rod_name, extract_target_user_id
from .fish_data import (
    get_fish_by_id, get_bait_by_id, GIVE_LIMITS,
)
from .storage import StorageManager


class SocialCommands(CommandBase):
    """社交系统命令处理器"""

    async def cmd_give(self, event, target_user: str, item_type: str, item_id: str = "", quantity: int = 1) -> str:
        """赠送命令"""
        
        sender_id = event.get_sender_id()
        receiver_id = extract_target_user_id(target_user)
        
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
                
                # 验证：赠送渔获/鱼饵/钓竿时必须提供ID
                if item_type in ("fish", "bait", "rod") and not item_id:
                    return "请指定要赠送的物品ID或编号，先使用 /背包 或 /我的钓竿 查看，如 /赠送 @用户 fish fish_003 2"
                
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
                        receiver_new_achievements = receiver.check_achievements()
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

                    result = f"✅ 已赠送 {quantity} 金币给 {target_user}（+{exp_gained} 经验）"
                    for ach in receiver_new_achievements:
                        result += f"\n\n🏅 对方解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                    return result
                
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
                        receiver_new_achievements = receiver.check_achievements()
                        await self.storage.save_user(receiver)
                    except Exception as e:
                        try:
                            sender.add_fish(item_id, actual_prefix_id, quantity)
                            sender._data["daily_give_count"] = max(0, sender._data.get("daily_give_count", 1) - 1)
                            await self.storage.save_user(sender)
                        except Exception:
                            pass
                        return f"赠送失败：目标用户数据保存异常（{e}），已尝试回滚"

                    result = f"✅ 已赠送渔获 x{quantity} 给 {target_user}（+{exp_gained} 经验）"
                    for ach in receiver_new_achievements:
                        result += f"\n\n🏅 对方解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                    return result
                
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
                        receiver_new_achievements = receiver.check_achievements()
                        await self.storage.save_user(receiver)
                    except Exception as e:
                        try:
                            sender.add_bait(item_id, actual_prefix_id, quantity)
                            sender._data["daily_give_count"] = max(0, sender._data.get("daily_give_count", 1) - 1)
                            await self.storage.save_user(sender)
                        except Exception:
                            pass
                        return f"赠送失败：目标用户数据保存异常（{e}），已尝试回滚"

                    result = f"✅ 已赠送鱼饵 x{quantity} 给 {target_user}（+{exp_gained} 经验）"
                    for ach in receiver_new_achievements:
                        result += f"\n\n🏅 对方解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                    return result
                
                # 处理钓竿赠送
                if item_type == "rod":
                    try:
                        rod_index = int(item_id)
                    except ValueError:
                        return "钓竿编号必须是数字，请使用 /我的钓竿 查看编号"
                    
                    rods = sender.get_owned_rods()
                    if rod_index < 1 or rod_index > len(rods):
                        return f"钓竿编号无效，你有 {len(rods)} 根钓竿。提示：出售/上架后编号会重新排序，请先重新查询背包或我的钓竿获取最新编号。"
                    
                    rod = rods[rod_index - 1]
                    
                    # 不能赠送当前装备的钓竿
                    current = sender.current_rod
                    if rod.get("instance_id") == current.get("instance_id"):
                        return "不能赠送当前装备的钓竿，请先切换到其他钓竿"
                    
                    if not sender.remove_rod(rod["instance_id"]):
                        return "钓竿移除失败"
                    sender.add_give()
                    
                    try:
                        await self.storage.save_user(sender)
                    except Exception as e:
                        sender.add_rod(rod["base_id"], rod["prefix_id"], rod.get("skills"), rod.get("enchant_count", 0), rod["instance_id"])
                        return f"赠送失败：无法保存你的数据（{e}）"
                    
                    try:
                        receiver.add_rod(rod["base_id"], rod["prefix_id"], rod.get("skills"), rod.get("enchant_count", 0), rod["instance_id"])
                        receiver.add_exp(exp_gained)
                        receiver_new_achievements = receiver.check_achievements()
                        await self.storage.save_user(receiver)
                    except Exception as e:
                        try:
                            sender.add_rod(rod["base_id"], rod["prefix_id"], rod.get("skills"), rod.get("enchant_count", 0), rod["instance_id"])
                            sender._data["daily_give_count"] = max(0, sender._data.get("daily_give_count", 1) - 1)
                            await self.storage.save_user(sender)
                        except Exception:
                            pass
                        return f"赠送失败：目标用户数据保存异常（{e}），已尝试回滚"

                    rod_name = format_rod_name(rod)
                    result = f"✅ 已赠送钓竿 [{rod_name}] 给 {target_user}（+{exp_gained} 经验）"
                    for ach in receiver_new_achievements:
                        result += f"\n\n🏅 对方解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                    return result
                
                return "无效的物品类型"
