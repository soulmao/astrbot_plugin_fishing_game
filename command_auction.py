"""拍卖行命令模块"""
from .commands_base import CommandBase
from .utils import (
    format_rod_name, format_bait_name, get_item_name_for_auction,
    calc_rod_value, calc_bait_value, calc_fish_value,
)
from .fish_data import (
    get_fish_by_id, get_prefix_by_id, get_bait_by_id, get_rod_prefix, get_bait_prefix,
    ENCHANT_TICKETS,
)
from .storage import StorageManager
import time


class AuctionCommands(CommandBase):
    """拍卖行命令处理器"""

    def _get_latest_rods_summary(self, user) -> str:
        """返回最新的钓竿列表摘要（用于操作后提示LLM编号已变化）"""
        current = user.current_rod
        lines = ["\n📋 当前拥有的钓竿:"]
        for i, rod in enumerate(user.get_owned_rods(), 1):
            name = format_rod_name(rod)
            marker = " [当前]" if rod.get("instance_id") == current.get("instance_id") else ""
            lines.append(f"  {i}. {name}{marker}")
        if not user.get_owned_rods():
            lines.append("  (无)")
        return "\n".join(lines)

    async def cmd_auction(self, event, action: str = "list", arg1: str = "", arg2: str = "", arg3: str = "") -> str:
        """拍卖行命令"""
        user_id = event.get_sender_id()
        action = action.lower()
        args = [a for a in [arg1, arg2, arg3] if a]
        
        if action in ("列表", "list"):
            page = 1
            if args:
                try:
                    page = int(args[0])
                except ValueError:
                    pass
            listings, total = await self.storage.search_auctions("", page, 10)
            total_pages = (total + 9) // 10
            
            result = f"🏪 拍卖行 (第{page}/{max(1, total_pages)}页, 共{total}件)\n\n"
            if not listings:
                result += "暂无在售物品\n"
            else:
                for lst in listings:
                    name = get_item_name_for_auction(lst.get("item_data", {}))
                    result += f"📦 [{lst['id']}] {name}\n"
                    result += f"   售价: {lst['price']} 金币 | 卖家: {lst.get('seller_name', '未知')[:10]}\n"
                    remaining = max(0, lst['expires_at'] - int(time.time()))
                    hours = remaining // 3600
                    mins = (remaining % 3600) // 60
                    result += f"   剩余: {hours}小时{mins}分\n\n"
            result += "\n💡 /拍卖 购买 [编号] | /拍卖 搜索 [关键词]"
            return result
        
        if action in ("搜索", "search"):
            if not args:
                return "请输入搜索关键词，如: /拍卖 搜索 金色"
            keyword = args[0]
            page = 1
            if len(args) > 1:
                try:
                    page = int(args[1])
                except ValueError:
                    pass
            listings, total = await self.storage.search_auctions(keyword, page, 10)
            total_pages = (total + 9) // 10
            
            result = f"🔍 拍卖行搜索 '{keyword}' (第{page}/{max(1, total_pages)}页, 共{total}件)\n\n"
            if not listings:
                result += "未找到匹配物品\n"
            else:
                for lst in listings:
                    name = get_item_name_for_auction(lst.get("item_data", {}))
                    result += f"📦 [{lst['id']}] {name}\n"
                    result += f"   售价: {lst['price']} 金币 | 卖家: {lst.get('seller_name', '未知')[:10]}\n\n"
            return result
        
        if action in ("出售", "sell"):
            if len(args) < 2:
                return "用法: /拍卖 出售 <类型> <编号>\n类型: rod(钓竿), bait(鱼饵), fish(渔获), ticket(附魔券)"
            item_type = args[0].lower()
            item_ref = args[1]
            
            async with self._get_user_lock(user_id):
                user = await self.storage.get_user(user_id)
                
                if item_type == "rod":
                    try:
                        rod_index = int(item_ref)
                    except ValueError:
                        return "钓竿编号必须是数字"
                    rods = user.get_owned_rods()
                    if rod_index < 1 or rod_index > len(rods):
                        return f"钓竿编号无效。提示：出售/上架后编号会重新排序，请先重新查询背包或我的钓竿获取最新编号。"
                    rod = rods[rod_index - 1]
                    current = user.current_rod
                    if rod.get("instance_id") == current.get("instance_id"):
                        return "不能出售当前装备的钓竿"
                    value = calc_rod_value(rod["base_id"], rod["prefix_id"], rod.get("skills"))
                    sell_price = int(value * self.star.auction_default_price_percent)
                    # 诅咒前缀：卖出时扣除金币
                    prefix = get_rod_prefix(rod.get("prefix_id", ""))
                    cursed_penalty = 0
                    if prefix.get("skills", {}).get("cursed"):
                        cursed_penalty = int(sell_price * 0.20)
                        if user.coins < cursed_penalty:
                            return f"诅咒钓竿卖出需要扣除 {cursed_penalty} 金币，你当前金币不足"
                        user.remove_coins(cursed_penalty)
                    if not user.remove_rod(rod["instance_id"]):
                        return "出售失败"
                    user.add_coins(sell_price)

                    new_achievements = user.check_achievements()

                    await self.storage.save_user(user)
                    penalty_msg = f"（诅咒扣除 {cursed_penalty} 金币）" if cursed_penalty > 0 else ""
                    result = f"✅ 已直接出售 {format_rod_name(rod)}，获得 {sell_price} 金币{penalty_msg}" + self._get_latest_rods_summary(user)
                    for ach in new_achievements:
                        result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                    return result
                
                elif item_type == "bait":
                    baits = user.get_baits()
                    try:
                        bait_index = int(item_ref)
                        if bait_index < 1 or bait_index > len(baits):
                            return "鱼饵编号无效"
                        bait = baits[bait_index - 1]
                        actual_prefix_id = bait["prefix_id"]
                        count = bait.get("count", 0)
                        if count <= 0:
                            return "该鱼饵数量为0"
                    except ValueError:
                        # 尝试按 base_id 查找
                        found = False
                        for bait in baits:
                            if bait["base_id"] == item_ref and bait.get("count", 0) > 0:
                                actual_prefix_id = bait["prefix_id"]
                                count = bait["count"]
                                found = True
                                break
                        if not found:
                            return f"未找到该鱼饵"
                    
                    value = calc_bait_value(bait["base_id"], actual_prefix_id, count)
                    sell_price = int(value * self.star.auction_default_price_percent)
                    if not user.remove_bait(bait["base_id"], actual_prefix_id, count):
                        return "出售失败"
                    user.add_coins(sell_price)

                    new_achievements = user.check_achievements()

                    await self.storage.save_user(user)
                    result = f"✅ 已直接出售鱼饵，获得 {sell_price} 金币"
                    for ach in new_achievements:
                        result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                    return result
                
                elif item_type == "fish":
                    fish_inv = user.get_fish_inventory()
                    found = None
                    for fish in fish_inv:
                        if fish["fish_id"] == item_ref:
                            found = fish
                            break
                    if not found:
                        return f"背包中没有 ID 为 {item_ref} 的渔获"
                    
                    value = calc_fish_value(found["fish_id"], found["prefix_id"], found["count"])
                    sell_price = int(value * self.star.auction_default_price_percent)
                    if not user.remove_fish(found["fish_id"], found["prefix_id"], found["count"]):
                        return "出售失败"
                    user.add_coins(sell_price)

                    new_achievements = user.check_achievements()

                    await self.storage.save_user(user)
                    result = f"✅ 已直接出售渔获，获得 {sell_price} 金币"
                    for ach in new_achievements:
                        result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                    return result
                
                elif item_type == "ticket":
                    ticket_id = item_ref
                    count = user.get_enchant_ticket_count(ticket_id)
                    if count <= 0:
                        return "你没有该附魔券"
                    # 附魔券固定价值 50 金币/张
                    value = 50 * count
                    sell_price = int(value * self.star.auction_default_price_percent)
                    if not user.remove_enchant_ticket(ticket_id, count):
                        return "出售失败"
                    user.add_coins(sell_price)

                    new_achievements = user.check_achievements()

                    await self.storage.save_user(user)
                    result = f"✅ 已直接出售附魔券 x{count}，获得 {sell_price} 金币"
                    for ach in new_achievements:
                        result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                    return result
                
                return "无效的物品类型"
        
        if action in ("上架", "listing"):
            if len(args) < 2:
                return "用法: /拍卖 上架 <类型> <编号/ID> [价格]\n类型: rod(钓竿), bait(鱼饵), fish(渔获), ticket(附魔券)"
            item_type = args[0].lower()
            item_ref = args[1]
            custom_price = None
            if len(args) > 2:
                try:
                    custom_price = int(args[2])
                except ValueError:
                    return "价格必须是数字"
            
            async with self._get_user_lock(user_id):
                user = await self.storage.get_user(user_id)
                seller_name = event.get_sender_name() or user_id[:8]
                
                item_data = {"type": item_type}
                
                if item_type == "rod":
                    try:
                        rod_index = int(item_ref)
                    except ValueError:
                        return "钓竿编号必须是数字"
                    rods = user.get_owned_rods()
                    if rod_index < 1 or rod_index > len(rods):
                        return "钓竿编号无效。提示：出售/上架后编号会重新排序，请先重新查询背包或我的钓竿获取最新编号。"
                    rod = rods[rod_index - 1]
                    current = user.current_rod
                    if rod.get("instance_id") == current.get("instance_id"):
                        return "不能上架当前装备的钓竿"
                    
                    value = calc_rod_value(rod["base_id"], rod["prefix_id"], rod.get("skills"))
                    default_price = int(value * self.star.auction_default_price_percent)
                    min_price = int(default_price * (1 - self.star.auction_price_range_percent))
                    max_price = int(default_price * (1 + self.star.auction_price_range_percent))
                    
                    if custom_price is not None:
                        if custom_price < min_price or custom_price > max_price:
                            return f"价格必须在 {min_price} ~ {max_price} 金币之间（默认{default_price}）"
                        price = custom_price
                    else:
                        price = default_price
                    
                    # 诅咒前缀：上架时扣除金币
                    prefix = get_rod_prefix(rod.get("prefix_id", ""))
                    cursed_penalty = 0
                    if prefix.get("skills", {}).get("cursed"):
                        cursed_penalty = int(price * 0.20)
                        if user.coins < cursed_penalty:
                            return f"诅咒钓竿上架需要扣除 {cursed_penalty} 金币，你当前金币不足"
                        user.remove_coins(cursed_penalty)
                    
                    if not user.remove_rod(rod["instance_id"]):
                        return "上架失败"
                    
                    item_data.update({
                        "base_id": rod["base_id"],
                        "prefix_id": rod["prefix_id"],
                        "instance_id": rod["instance_id"],
                        "enchant_count": rod.get("enchant_count", 0),
                        "skills": rod.get("skills", {}),
                        "name": format_rod_name(rod),
                        "price": price,
                    })
                
                elif item_type == "bait":
                    baits = user.get_baits()
                    try:
                        bait_index = int(item_ref)
                        if bait_index < 1 or bait_index > len(baits):
                            return "鱼饵编号无效"
                        bait = baits[bait_index - 1]
                        actual_prefix_id = bait["prefix_id"]
                        count = bait.get("count", 0)
                    except ValueError:
                        found = False
                        for bait in baits:
                            if bait["base_id"] == item_ref and bait.get("count", 0) > 0:
                                actual_prefix_id = bait["prefix_id"]
                                count = bait["count"]
                                found = True
                                break
                        if not found:
                            return "未找到该鱼饵"
                    
                    value = calc_bait_value(bait["base_id"], actual_prefix_id, count)
                    default_price = int(value * self.star.auction_default_price_percent)
                    min_price = int(default_price * (1 - self.star.auction_price_range_percent))
                    max_price = int(default_price * (1 + self.star.auction_price_range_percent))
                    
                    if custom_price is not None:
                        if custom_price < min_price or custom_price > max_price:
                            return f"价格必须在 {min_price} ~ {max_price} 金币之间（默认{default_price}）"
                        price = custom_price
                    else:
                        price = default_price
                    
                    if not user.remove_bait(bait["base_id"], actual_prefix_id, count):
                        return "上架失败"
                    
                    base = get_bait_by_id(bait["base_id"])
                    prefix = get_bait_prefix(actual_prefix_id)
                    name = f"{prefix['name']}{base['name']}" if base and prefix else "未知鱼饵"
                    item_data.update({
                        "base_id": bait["base_id"],
                        "prefix_id": actual_prefix_id,
                        "count": count,
                        "name": name,
                        "price": price,
                    })
                
                elif item_type == "fish":
                    fish_inv = user.get_fish_inventory()
                    found = None
                    for fish in fish_inv:
                        if fish["fish_id"] == item_ref:
                            found = fish
                            break
                    if not found:
                        return f"背包中没有 ID 为 {item_ref} 的渔获"
                    
                    value = calc_fish_value(found["fish_id"], found["prefix_id"], found["count"])
                    default_price = int(value * self.star.auction_default_price_percent)
                    min_price = int(default_price * (1 - self.star.auction_price_range_percent))
                    max_price = int(default_price * (1 + self.star.auction_price_range_percent))
                    
                    if custom_price is not None:
                        if custom_price < min_price or custom_price > max_price:
                            return f"价格必须在 {min_price} ~ {max_price} 金币之间（默认{default_price}）"
                        price = custom_price
                    else:
                        price = default_price
                    
                    if not user.remove_fish(found["fish_id"], found["prefix_id"], found["count"]):
                        return "上架失败"
                    
                    fish_info = get_fish_by_id(found["fish_id"])
                    prefix = get_prefix_by_id(found["prefix_id"])
                    name = f"{prefix['name']}{fish_info['name']}" if fish_info and prefix else "未知鱼类"
                    item_data.update({
                        "fish_id": found["fish_id"],
                        "prefix_id": found["prefix_id"],
                        "count": found["count"],
                        "name": name,
                        "price": price,
                    })
                
                elif item_type == "ticket":
                    ticket_id = item_ref
                    count = user.get_enchant_ticket_count(ticket_id)
                    if count <= 0:
                        return "你没有该附魔券"
                    
                    value = 50 * count
                    default_price = int(value * self.star.auction_default_price_percent)
                    min_price = int(default_price * (1 - self.star.auction_price_range_percent))
                    max_price = int(default_price * (1 + self.star.auction_price_range_percent))
                    
                    if custom_price is not None:
                        if custom_price < min_price or custom_price > max_price:
                            return f"价格必须在 {min_price} ~ {max_price} 金币之间（默认{default_price}）"
                        price = custom_price
                    else:
                        price = default_price
                    
                    if not user.remove_enchant_ticket(ticket_id, count):
                        return "上架失败"
                    
                    ticket_info = None
                    for t in ENCHANT_TICKETS:
                        if t["id"] == ticket_id:
                            ticket_info = t
                            break
                    name = ticket_info["name"] if ticket_info else "未知附魔券"
                    item_data.update({
                        "ticket_id": ticket_id,
                        "count": count,
                        "name": name,
                        "price": price,
                    })
                
                else:
                    return "无效的物品类型"
                
                listing = await self.storage.list_auction_item(user_id, seller_name, item_data)
                await self.storage.save_user(user)
                return f"✅ 上架成功！\n📦 [{listing['id']}] {item_data.get('name', '未知')}\n💰 售价: {price} 金币\n⏰ 保留{self.star.auction_duration_hours}小时" + self._get_latest_rods_summary(user)
        
        if action in ("取消", "cancel"):
            if not args:
                return "用法: /拍卖 取消 <上架编号>"
            listing_id = args[0]
            
            async with self._get_user_lock(user_id):
                user = await self.storage.get_user(user_id)
                listing = await self.storage.cancel_auction_listing(listing_id, user_id)
                if not listing:
                    return "未找到该上架物品或你不是卖家"
                
                # 退还物品
                item_data = listing.get("item_data", {})
                item_type = item_data.get("type", "")
                
                if item_type == "rod":
                    user.add_rod(
                        item_data["base_id"],
                        item_data["prefix_id"],
                        item_data.get("skills", {}),
                        item_data.get("enchant_count", 0),
                        item_data.get("instance_id")
                    )
                elif item_type == "bait":
                    user.add_bait(item_data["base_id"], item_data["prefix_id"], item_data.get("count", 1))
                elif item_type == "fish":
                    user.add_fish(item_data["fish_id"], item_data["prefix_id"], item_data.get("count", 1))
                elif item_type == "ticket":
                    user.add_enchant_ticket(item_data["ticket_id"], item_data.get("count", 1))
                
                await self.storage.save_user(user)
                return f"✅ 已取消上架，{item_data.get('name', '物品')} 已退回" + self._get_latest_rods_summary(user)
        
        if action in ("购买", "buy"):
            if not args:
                return "用法: /拍卖 购买 <上架编号>"
            listing_id = args[0]
            
            #  buyer 和 seller 需要排序加锁
            buyer_id = user_id
            listing = (await self.storage.search_auctions("", 1, 9999))[0]
            target = None
            for lst in listing:
                if lst["id"] == listing_id:
                    target = lst
                    break
            if not target:
                return "未找到该上架物品"
            
            seller_id = target["seller_id"]
            if seller_id == buyer_id:
                return "不能购买自己的物品"
            
            first_id, second_id = sorted([buyer_id, seller_id])
            async with self._get_user_lock(first_id):
                async with self._get_user_lock(second_id):
                    buyer = await self.storage.get_user(buyer_id)
                    seller = await self.storage.get_user(seller_id)
                    
                    price = target["price"]
                    if buyer.coins < price:
                        return f"金币不足！需要 {price} 金币，你只有 {buyer.coins} 金币"
                    
                    # 执行购买（从全局移除）
                    bought = await self.storage.buy_auction_item(listing_id, buyer_id)
                    if not bought:
                        return "购买失败，该物品可能已被买走或过期"
                    
                    # 扣买方金币
                    buyer.remove_coins(price)
                    
                    # 给卖方金币
                    seller.add_coins(price)
                    
                    # 转移物品给买方
                    item_data = bought.get("item_data", {})
                    item_type = item_data.get("type", "")
                    
                    if item_type == "rod":
                        buyer.add_rod(
                            item_data["base_id"],
                            item_data["prefix_id"],
                            item_data.get("skills", {}),
                            item_data.get("enchant_count", 0),
                            item_data.get("instance_id")
                        )
                    elif item_type == "bait":
                        buyer.add_bait(item_data["base_id"], item_data["prefix_id"], item_data.get("count", 1))
                    elif item_type == "fish":
                        buyer.add_fish(item_data["fish_id"], item_data["prefix_id"], item_data.get("count", 1))
                    elif item_type == "ticket":
                        buyer.add_enchant_ticket(item_data["ticket_id"], item_data.get("count", 1))

                    # 成就检查
                    buyer_new_achievements = buyer.check_achievements()
                    seller_new_achievements = seller.check_achievements()

                    await self.storage.save_user(buyer)
                    await self.storage.save_user(seller)
                    result = f"✅ 购买成功！\n📦 {item_data.get('name', '未知物品')}\n💰 花费: {price} 金币\n📦 剩余: {buyer.coins} 金币" + self._get_latest_rods_summary(buyer)
                    for ach in buyer_new_achievements:
                        result += f"\n\n🏅 解锁成就 [{ach['name']}]！\n💰 +{ach.get('reward_coins', 0)} 金币 📈 +{ach.get('reward_exp', 0)} 经验"
                    if seller_new_achievements:
                        result += "\n\n📢 卖家也解锁了成就：" + "、".join([ach['name'] for ach in seller_new_achievements])
                    return result
        
        return "未知操作。用法:\n/拍卖 列表 [页码]\n/拍卖 搜索 <关键词> [页码]\n/拍卖 上架 <类型> <编号> [价格]\n/拍卖 出售 <类型> <编号>\n/拍卖 取消 <上架编号>\n/拍卖 购买 <上架编号>"
