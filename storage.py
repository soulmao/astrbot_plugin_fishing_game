"""用户数据存储模块"""
import time
from typing import Optional, Dict, Any
from .fish_data import (
    LEVELS, ROD_BASES, ROD_PREFIXES, BAIT_BASES, BAIT_PREFIXES,
    calc_rod_value, calc_bait_value, calc_fish_value,
    get_rod_prefix, get_prefix_by_id, get_fish_by_id, get_bait_by_id,
    ENCHANT_CONFIG, ENCHANT_TICKETS,
)
import random
import uuid
import asyncio

class UserData:
    """玩家数据模型"""
    def __init__(self, user_id: str, data: Optional[Dict] = None):
        self.user_id = user_id
        if data:
            self._data = data
            self._migrate_data()
        else:
            self._data = self._default_data()
    
    def _migrate_data(self):
        """兼容老版本数据迁移"""
        # 钓竿数据补充 enchant_count、skills 和 instance_id
        for rod in self._data.get("owned_rods", []):
            if "enchant_count" not in rod:
                rod["enchant_count"] = 0
            if "skills" not in rod:
                rod["skills"] = {}
            if "instance_id" not in rod:
                rod["instance_id"] = f"inst_{uuid.uuid4().hex[:16]}"
        # 同步 current_rod 的 instance_id
        current = self._data.get("current_rod", {})
        if current:
            if "enchant_count" not in current:
                current["enchant_count"] = 0
            if "skills" not in current:
                current["skills"] = {}
            if "instance_id" not in current:
                # 从 owned_rods 中找匹配的 instance_id
                for rod in self._data.get("owned_rods", []):
                    if rod.get("base_id") == current.get("base_id") and rod.get("prefix_id") == current.get("prefix_id"):
                        current["instance_id"] = rod["instance_id"]
                        break
                if "instance_id" not in current:
                    current["instance_id"] = f"inst_{uuid.uuid4().hex[:16]}"
        # 附魔券
        if "enchant_tickets" not in self._data:
            self._data["enchant_tickets"] = []
    
    def _default_data(self) -> Dict:
        """默认玩家数据"""
        initial_rod_id = f"inst_{uuid.uuid4().hex[:16]}"
        return {
            "user_id": self.user_id,
            "coins": 100,
            "exp": 0,
            "level": 1,
            # 初始钓竿: 普通的木制钓竿
            "owned_rods": [{"base_id": "rod_001", "prefix_id": "rod_pref_03", "instance_id": initial_rod_id, "enchant_count": 0, "skills": {}}],
            "current_rod": {"base_id": "rod_001", "prefix_id": "rod_pref_03", "instance_id": initial_rod_id, "enchant_count": 0, "skills": {}},
            # 初始鱼饵: 普通的蚯蚓 x10
            "baits": [{"base_id": "bait_001", "prefix_id": "bait_pref_02", "count": 10}],
            # 当前使用的鱼饵（默认第一个）
            "current_bait": {"base_id": "bait_001", "prefix_id": "bait_pref_02"},
            # 渔获
            "fish_inventory": [],
            # 冷却
            "fish_cooldown": 0,
            "shop_refresh_cd": 0,
            # 赠送
            "daily_give_count": 0,
            "daily_give_reset": "",
            # 统计
            "total_fish_count": 0,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
            # 图鉴
            "collection": {},
            # 附魔券
            "enchant_tickets": [],
            # 道具（刷新券等特殊物品）
            "items": [],
        }
    
    def to_dict(self) -> Dict:
        self._data["updated_at"] = int(time.time())
        return self._data
    
    # 金币
    @property
    def coins(self) -> int:
        return self._data.get("coins", 0)
    
    def add_coins(self, amount: int):
        self._data["coins"] = self.coins + amount
    
    def remove_coins(self, amount: int) -> bool:
        if self.coins >= amount:
            self._data["coins"] -= amount
            return True
        return False
    
    # 经验
    @property
    def exp(self) -> int:
        return self._data.get("exp", 0)
    
    def add_exp(self, amount: int) -> tuple[bool, int]:
        """增加经验，返回(是否升级, 升级后等级)"""
        self._data["exp"] = self.exp + amount
        old_level = self.level
        new_level = self._calc_level()
        if new_level > old_level:
            self._data["level"] = new_level
            return True, new_level
        return False, self.level
    
    def _calc_level(self) -> int:
        """根据经验计算等级"""
        exp = self._data.get("exp", 0)
        level = 1
        for lvl in LEVELS:
            if exp >= lvl["exp_required"]:
                level = lvl["level"]
        return level
    
    @property
    def level(self) -> int:
        return self._data.get("level", 1)
    
    # 鱼饵
    def get_bait_count(self, base_id: str, prefix_id: str) -> int:
        for bait in self._data.get("baits", []):
            if bait["base_id"] == base_id and bait["prefix_id"] == prefix_id:
                return bait.get("count", 0)
        return 0
    
    def get_total_bait_count(self) -> int:
        """获取所有鱼饵总数"""
        return sum(b.get("count", 0) for b in self._data.get("baits", []))
    
    def add_bait(self, base_id: str, prefix_id: str, count: int = 1):
        for bait in self._data.get("baits", []):
            if bait["base_id"] == base_id and bait["prefix_id"] == prefix_id:
                bait["count"] = bait.get("count", 0) + count
                return
        self._data.setdefault("baits", []).append({"base_id": base_id, "prefix_id": prefix_id, "count": count})
    
    def remove_bait(self, base_id: str, prefix_id: str, count: int = 1) -> bool:
        for bait in self._data.get("baits", []):
            if bait["base_id"] == base_id and bait["prefix_id"] == prefix_id:
                if bait.get("count", 0) >= count:
                    bait["count"] -= count
                    if bait["count"] <= 0:
                        self._data["baits"].remove(bait)
                        # 如果移除的是当前装备的鱼饵，自动重置为默认值
                        current = self.current_bait
                        if current.get("base_id") == base_id and current.get("prefix_id") == prefix_id:
                            self._reset_current_bait()
                    return True
        return False
    
    def _reset_current_bait(self):
        """将当前鱼饵重置为默认或第一个可用的"""
        for bait in self._data.get("baits", []):
            if bait.get("count", 0) > 0:
                self._data["current_bait"] = {"base_id": bait["base_id"], "prefix_id": bait["prefix_id"]}
                return
        self._data["current_bait"] = {"base_id": "bait_001", "prefix_id": "bait_pref_02"}
    
    def get_baits(self) -> list:
        """获取所有鱼饵列表（副本）"""
        return list(self._data.get("baits", []))
    
    # 渔获
    def add_fish(self, fish_id: str, prefix_id: str, count: int = 1):
        for fish in self._data.get("fish_inventory", []):
            if fish["fish_id"] == fish_id and fish["prefix_id"] == prefix_id:
                fish["count"] = fish.get("count", 0) + count
                return
        self._data.setdefault("fish_inventory", []).append({
            "fish_id": fish_id,
            "prefix_id": prefix_id,
            "count": count,
            "obtained_at": int(time.time())
        })
    
    def remove_fish(self, fish_id: str, prefix_id: str, count: int = 1) -> bool:
        for fish in self._data.get("fish_inventory", []):
            if fish["fish_id"] == fish_id and fish["prefix_id"] == prefix_id:
                if fish.get("count", 0) >= count:
                    fish["count"] -= count
                    if fish["count"] <= 0:
                        self._data["fish_inventory"].remove(fish)
                    return True
        return False
    
    def get_fish_count(self, fish_id: str, prefix_id: str) -> int:
        for fish in self._data.get("fish_inventory", []):
            if fish["fish_id"] == fish_id and fish["prefix_id"] == prefix_id:
                return fish.get("count", 0)
        return 0
    
    def get_fish_inventory(self) -> list:
        """获取渔获列表（副本）"""
        return list(self._data.get("fish_inventory", []))
    
    # 钓竿
    def add_rod(self, base_id: str, prefix_id: str, skills: dict = None, enchant_count: int = 0, instance_id: str = None) -> str:
        """添加钓竿，返回 instance_id"""
        if instance_id is None:
            instance_id = f"inst_{uuid.uuid4().hex[:16]}"
        rod = {
            "base_id": base_id,
            "prefix_id": prefix_id,
            "instance_id": instance_id,
            "enchant_count": enchant_count,
            "skills": skills if skills else {},
        }
        self._data.setdefault("owned_rods", []).append(rod)
        return instance_id
    
    def has_rod(self, base_id: str, prefix_id: str) -> bool:
        """检查是否拥有某 base_id+prefix_id 组合的钓竿（用于商店购买等）"""
        for rod in self._data.get("owned_rods", []):
            if rod.get("base_id") == base_id and rod.get("prefix_id") == prefix_id:
                return True
        return False
    
    def has_rod_instance(self, instance_id: str) -> bool:
        """检查是否拥有某 instance_id 的钓竿"""
        for rod in self._data.get("owned_rods", []):
            if rod.get("instance_id") == instance_id:
                return True
        return False
    
    @property
    def current_rod(self) -> Dict:
        return self._data.get("current_rod", {"base_id": "rod_001", "prefix_id": "rod_pref_03", "instance_id": "", "enchant_count": 0, "skills": {}})
    
    def equip_rod(self, instance_id: str) -> bool:
        """通过 instance_id 装备钓竿"""
        for rod in self._data.get("owned_rods", []):
            if rod.get("instance_id") == instance_id:
                self._data["current_rod"] = {
                    "base_id": rod["base_id"],
                    "prefix_id": rod["prefix_id"],
                    "instance_id": rod["instance_id"],
                    "enchant_count": rod.get("enchant_count", 0),
                    "skills": dict(rod.get("skills", {})),
                }
                return True
        return False
    
    def get_owned_rods(self) -> list:
        """获取拥有的钓竿列表（副本）"""
        return list(self._data.get("owned_rods", []))
    
    def get_rod_by_index(self, index: int) -> Optional[dict]:
        """通过编号(1-based)获取钓竿"""
        rods = self._data.get("owned_rods", [])
        if 1 <= index <= len(rods):
            return dict(rods[index - 1])
        return None
    
    def get_rod_by_instance_id(self, instance_id: str) -> Optional[dict]:
        """通过 instance_id 获取钓竿"""
        for rod in self._data.get("owned_rods", []):
            if rod.get("instance_id") == instance_id:
                return dict(rod)
        return None
    
    def remove_rod(self, instance_id: str) -> Optional[dict]:
        """通过 instance_id 移除钓竿，返回被移除的钓竿数据（用于赠送/拍卖转移）"""
        for rod in self._data.get("owned_rods", []):
            if rod.get("instance_id") == instance_id:
                self._data["owned_rods"].remove(rod)
                # 如果移除的是当前装备的钓竿，重置
                current = self._data.get("current_rod", {})
                if current.get("instance_id") == instance_id:
                    self._reset_current_rod()
                return dict(rod)
        return None
    
    def _reset_current_rod(self):
        """重置当前钓竿为第一个可用"""
        rods = self._data.get("owned_rods", [])
        if rods:
            self._data["current_rod"] = {
                "base_id": rods[0]["base_id"],
                "prefix_id": rods[0]["prefix_id"],
                "instance_id": rods[0]["instance_id"],
                "enchant_count": rods[0].get("enchant_count", 0),
                "skills": dict(rods[0].get("skills", {})),
            }
        else:
            self._data["current_rod"] = {"base_id": "rod_001", "prefix_id": "rod_pref_03", "instance_id": f"inst_{uuid.uuid4().hex[:16]}", "enchant_count": 0, "skills": {}}
    
    def update_rod_skills(self, instance_id: str, enchant_count: int, skills: dict) -> bool:
        """通过 instance_id 更新钓竿的技能和附魔次数"""
        for rod in self._data.get("owned_rods", []):
            if rod.get("instance_id") == instance_id:
                rod["enchant_count"] = enchant_count
                rod["skills"] = dict(skills)
                # 同步更新当前装备
                current = self._data.get("current_rod", {})
                if current.get("instance_id") == instance_id:
                    current["enchant_count"] = enchant_count
                    current["skills"] = dict(skills)
                return True
        return False
    
    # 鱼饵选择
    @property
    def current_bait(self) -> Dict:
        return self._data.get("current_bait", {"base_id": "bait_001", "prefix_id": "bait_pref_02"})
    
    def has_bait_type(self, base_id: str, prefix_id: str) -> bool:
        """检查是否有某种鱼饵"""
        for bait in self._data.get("baits", []):
            if bait["base_id"] == base_id and bait["prefix_id"] == prefix_id and bait.get("count", 0) > 0:
                return True
        return False
    
    def equip_bait(self, base_id: str, prefix_id: str) -> bool:
        """装备鱼饵"""
        if self.has_bait_type(base_id, prefix_id):
            self._data["current_bait"] = {"base_id": base_id, "prefix_id": prefix_id}
            return True
        return False
    
    # 冷却
    @property
    def fish_cooldown(self) -> int:
        return self._data.get("fish_cooldown", 0)
    
    def is_fishing_ready(self) -> bool:
        return time.time() >= self.fish_cooldown
    
    def set_fishing_cooldown(self, seconds: int):
        self._data["fish_cooldown"] = int(time.time()) + seconds
    
    def get_fishing_cd_remaining(self) -> int:
        remaining = self.fish_cooldown - int(time.time())
        return max(0, remaining)
    
    @property
    def shop_refresh_cd(self) -> int:
        return self._data.get("shop_refresh_cd", 0)
    
    def is_shop_refresh_ready(self) -> bool:
        return time.time() >= self.shop_refresh_cd
    
    def set_shop_refresh_cd(self, seconds: int):
        self._data["shop_refresh_cd"] = int(time.time()) + seconds
    
    # 赠送
    def check_and_reset_daily_give(self):
        """检查并重置每日赠送次数，返回当前次数"""
        today = time.strftime("%Y-%m-%d")
        reset_date = self._data.get("daily_give_reset", "")
        if reset_date != today:
            self._data["daily_give_count"] = 0
            self._data["daily_give_reset"] = today
        return self._data.get("daily_give_count", 0)
    
    @property
    def daily_give_count(self) -> int:
        """获取今日已赠送次数（只读，不自动重置）"""
        today = time.strftime("%Y-%m-%d")
        reset_date = self._data.get("daily_give_reset", "")
        if reset_date != today:
            return 0
        return self._data.get("daily_give_count", 0)
    
    def add_give(self):
        current = self.check_and_reset_daily_give()
        self._data["daily_give_count"] = current + 1
    
    # 统计
    @property
    def total_fish_count(self) -> int:
        return self._data.get("total_fish_count", 0)
    
    def increment_fish_count(self):
        self._data["total_fish_count"] = self._data.get("total_fish_count", 0) + 1
    
    # 通用属性访问
    def get(self, key: str, default=None):
        return self._data.get(key, default)
    
    def set(self, key: str, value):
        self._data[key] = value
    
    # 图鉴系统
    def add_to_collection(self, fish_id: str, prefix_id: str):
        """记录钓到的鱼到图鉴"""
        key = f"{fish_id}#{prefix_id}"
        collection = self._data.setdefault("collection", {})
        if key not in collection:
            collection[key] = {"count": 0, "first_at": int(time.time())}
        collection[key]["count"] += 1
    
    def get_collection(self) -> dict:
        """获取图鉴数据"""
        return dict(self._data.get("collection", {}))
    
    def is_collected(self, fish_id: str, prefix_id: str) -> bool:
        """检查某条鱼是否已收集"""
        key = f"{fish_id}#{prefix_id}"
        return key in self._data.get("collection", {})
    
    def get_collection_count(self) -> int:
        """获取已收集的种类数量"""
        return len(self._data.get("collection", {}))
    
    # 附魔券系统
    def add_enchant_ticket(self, ticket_id: str, count: int = 1):
        for ticket in self._data.get("enchant_tickets", []):
            if ticket.get("ticket_id") == ticket_id:
                ticket["count"] = ticket.get("count", 0) + count
                return
        self._data.setdefault("enchant_tickets", []).append({"ticket_id": ticket_id, "count": count})
    
    def remove_enchant_ticket(self, ticket_id: str, count: int = 1) -> bool:
        for ticket in self._data.get("enchant_tickets", []):
            if ticket.get("ticket_id") == ticket_id:
                if ticket.get("count", 0) >= count:
                    ticket["count"] -= count
                    if ticket["count"] <= 0:
                        self._data["enchant_tickets"].remove(ticket)
                    return True
        return False
    
    def get_enchant_ticket_count(self, ticket_id: str) -> int:
        for ticket in self._data.get("enchant_tickets", []):
            if ticket.get("ticket_id") == ticket_id:
                return ticket.get("count", 0)
        return 0
    
    def get_best_enchant_ticket(self) -> Optional[dict]:
        """获取最佳附魔券（折扣最大的）"""
        best = None
        for ticket in self._data.get("enchant_tickets", []):
            ticket_info = None
            for t in ENCHANT_TICKETS:
                if t["id"] == ticket.get("ticket_id"):
                    ticket_info = t
                    break
            if ticket_info and ticket.get("count", 0) > 0:
                if best is None or ticket_info["discount"] > best["discount"]:
                    best = {"ticket_id": ticket["ticket_id"], "count": ticket["count"], "discount": ticket_info["discount"]}
        return best
    
    # 库存价值计算
    def get_total_inventory_value(self) -> int:
        """计算库存总价值（钓竿 + 鱼饵 + 渔获 + 道具）"""
        total = 0
        # 钓竿价值
        for rod in self._data.get("owned_rods", []):
            total += calc_rod_value(
                rod.get("base_id", ""),
                rod.get("prefix_id", ""),
                rod.get("skills")
            )
        # 鱼饵价值
        for bait in self._data.get("baits", []):
            total += calc_bait_value(
                bait.get("base_id", ""),
                bait.get("prefix_id", ""),
                bait.get("count", 0)
            )
        # 渔获价值
        for fish in self._data.get("fish_inventory", []):
            total += calc_fish_value(
                fish.get("fish_id", ""),
                fish.get("prefix_id", ""),
                fish.get("count", 0)
            )
        # 道具价值（刷新券按商店价，附魔券按固定值）
        for item in self._data.get("items", []):
            if item.get("id") == "refresh_token":
                total += 30 * item.get("count", 0)
        for ticket in self._data.get("enchant_tickets", []):
            total += 50 * ticket.get("count", 0)
        return total
    
    # 道具系统（刷新券等特殊物品）
    def add_item(self, item_id: str, count: int = 1):
        """添加道具"""
        for item in self._data.get("items", []):
            if item.get("id") == item_id:
                item["count"] = item.get("count", 0) + count
                return
        self._data.setdefault("items", []).append({"id": item_id, "count": count})
    
    def remove_item(self, item_id: str, count: int = 1) -> bool:
        """移除道具，返回是否成功"""
        for item in self._data.get("items", []):
            if item.get("id") == item_id:
                if item.get("count", 0) >= count:
                    item["count"] -= count
                    if item["count"] <= 0:
                        self._data["items"].remove(item)
                    return True
        return False
    
    def get_item_count(self, item_id: str) -> int:
        """获取道具数量"""
        for item in self._data.get("items", []):
            if item.get("id") == item_id:
                return item.get("count", 0)
        return 0


class StorageManager:
    """存储管理器"""
    def __init__(self, star):
        self.star = star
        self._auction_lock = asyncio.Lock()

    async def get_kv_data(self, key, default=None):
        return await self.star.get_kv_data(key, default)
    
    async def put_kv_data(self, key, value):
        await self.star.put_kv_data(key, value)
    
    async def get_user(self, user_id: str) -> UserData:
        """获取用户数据，不存在则创建"""
        key = f"fishing_user_{user_id}"
        data = await self.get_kv_data(key)
        if data is None:
            user = UserData(user_id)
            await self.save_user(user)
            await self._register_user_id(user_id)
            return user
        # 兼容旧版本：已存在的老用户可能未注册到全局列表，自动补录
        await self._register_user_id(user_id)
        return UserData(user_id, data)
    
    async def user_exists(self, user_id: str) -> bool:
        """检查用户是否已存在"""
        key = f"fishing_user_{user_id}"
        data = await self.get_kv_data(key)
        return data is not None
    
    async def save_user(self, user: UserData):
        """保存用户数据"""
        key = f"fishing_user_{user.user_id}"
        await self.put_kv_data(key, user.to_dict())
    
    async def _register_user_id(self, user_id: str):
        """将用户ID注册到全局列表"""
        key = "fishing_all_user_ids"
        all_ids = await self.get_kv_data(key) or []
        if user_id not in all_ids:
            all_ids.append(user_id)
            await self.put_kv_data(key, all_ids)
    
    async def get_all_user_ids(self) -> list:
        """获取所有已注册用户ID"""
        return await self.get_kv_data("fishing_all_user_ids") or []
    
    async def add_user_to_leaderboard(self, user_id: str, total_fish: int, user_name: str = "", level: int = 1):
        """更新排行榜数据"""
        key = "fishing_leaderboard"
        leaderboard = await self.get_kv_data(key) or {}
        leaderboard[user_id] = {"count": total_fish, "name": user_name, "level": level}
        await self.put_kv_data(key, leaderboard)
    
    async def get_leaderboard(self) -> list:
        """获取排行榜（实时计算 inventory_value + exp），返回全部用于准确排名"""
        all_ids = await self.get_all_user_ids()
        # 从旧排行榜缓存中尝试获取用户名（兼容已有数据）
        old_lb = await self.get_kv_data("fishing_leaderboard") or {}
        scores = []
        for uid in all_ids:
            try:
                user = await self.get_user(uid)
                score = user.get_total_inventory_value() + user.exp
                name = ""
                if isinstance(old_lb.get(uid), dict):
                    name = old_lb[uid].get("name", "")
                scores.append((uid, score, name))
            except Exception:
                continue
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
    
    # ===== 拍卖行 =====
    async def list_auction_item(self, seller_id: str, seller_name: str, item: dict) -> dict:
        """物品上架，返回 listing 信息"""
        async with self._auction_lock:
            listings = await self.get_kv_data("fishing_auctions") or []
            listing_id = f"auc_{int(time.time() * 1000)}_{len(listings)}"
            expires_at = int(time.time()) + getattr(self.star, 'auction_duration_hours', 24) * 3600
            listing = {
                "id": listing_id,
                "seller_id": seller_id,
                "seller_name": seller_name,
                "type": item["type"],  # rod, bait, fish, ticket
                "base_id": item.get("base_id", ""),
                "prefix_id": item.get("prefix_id", ""),
                "item_data": item,  # 完整物品数据
                "price": item["price"],
                "expires_at": expires_at,
                "created_at": int(time.time()),
            }
            listings.append(listing)
            await self.put_kv_data("fishing_auctions", listings)
            return listing
    
    async def cancel_auction_listing(self, listing_id: str, seller_id: str) -> Optional[dict]:
        """取消上架，返回 listing 数据（用于退还物品）"""
        async with self._auction_lock:
            listings = await self.get_kv_data("fishing_auctions") or []
            for i, lst in enumerate(listings):
                if lst["id"] == listing_id and lst["seller_id"] == seller_id:
                    listing = listings.pop(i)
                    await self.put_kv_data("fishing_auctions", listings)
                    return listing
            return None
    
    async def buy_auction_item(self, listing_id: str, buyer_id: str) -> Optional[dict]:
        """购买拍卖物品，返回 listing 数据（用于转移物品）"""
        async with self._auction_lock:
            listings = await self.get_kv_data("fishing_auctions") or []
            for i, lst in enumerate(listings):
                if lst["id"] == listing_id:
                    if lst["seller_id"] == buyer_id:
                        return None  # 不能买自己的
                    listing = listings.pop(i)
                    await self.put_kv_data("fishing_auctions", listings)
                    return listing
            return None
    
    async def search_auctions(self, keyword: str = "", page: int = 1, page_size: int = 10) -> tuple:
        """搜索拍卖行，返回 (listings, total)"""
        listings = await self.get_kv_data("fishing_auctions") or []
        now = int(time.time())
        # 过滤过期
        listings = [lst for lst in listings if lst["expires_at"] > now]
        # 搜索
        if keyword:
            kw = keyword.lower()
            filtered = []
            for lst in listings:
                item = lst.get("item_data", {})
                name = item.get("name", "").lower()
                type_name = lst["type"].lower()
                if kw in name or kw in type_name:
                    filtered.append(lst)
            listings = filtered
        # 分页
        total = len(listings)
        start = (page - 1) * page_size
        end = start + page_size
        return listings[start:end], total
    
    async def get_expired_listings(self) -> list:
        """获取所有已过期的上架物品"""
        listings = await self.get_kv_data("fishing_auctions") or []
        now = int(time.time())
        expired = [lst for lst in listings if lst["expires_at"] <= now]
        return expired
    
    async def remove_expired_listings(self, listing_ids: list) -> bool:
        """移除指定过期的上架记录"""
        async with self._auction_lock:
            listings = await self.get_kv_data("fishing_auctions") or []
            new_listings = [lst for lst in listings if lst["id"] not in listing_ids]
            await self.put_kv_data("fishing_auctions", new_listings)
            return True
