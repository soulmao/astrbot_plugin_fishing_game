"""用户数据存储模块"""
import time
from typing import Optional, Dict, Any
from .fish_data import LEVELS, ROD_BASES, ROD_PREFIXES, BAIT_BASES, BAIT_PREFIXES

class UserData:
    """玩家数据模型"""
    def __init__(self, user_id: str, data: Optional[Dict] = None):
        self.user_id = user_id
        if data:
            self._data = data
        else:
            self._data = self._default_data()
    
    def _default_data(self) -> Dict:
        """默认玩家数据"""
        return {
            "user_id": self.user_id,
            "coins": 100,
            "exp": 0,
            "level": 1,
            # 初始钓竿: 普通的木制钓竿
            "owned_rods": [{"base_id": "rod_001", "prefix_id": "rod_pref_03"}],
            "current_rod": {"base_id": "rod_001", "prefix_id": "rod_pref_03"},
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
    def add_rod(self, base_id: str, prefix_id: str):
        rod = {"base_id": base_id, "prefix_id": prefix_id}
        if rod not in self._data.get("owned_rods", []):
            self._data.setdefault("owned_rods", []).append(rod)
    
    def has_rod(self, base_id: str, prefix_id: str) -> bool:
        return {"base_id": base_id, "prefix_id": prefix_id} in self._data.get("owned_rods", [])
    
    @property
    def current_rod(self) -> Dict:
        return self._data.get("current_rod", {"base_id": "rod_001", "prefix_id": "rod_pref_03"})
    
    def equip_rod(self, base_id: str, prefix_id: str) -> bool:
        if self.has_rod(base_id, prefix_id):
            self._data["current_rod"] = {"base_id": base_id, "prefix_id": prefix_id}
            return True
        return False
    
    def get_owned_rods(self) -> list:
        """获取拥有的钓竿列表（副本）"""
        return list(self._data.get("owned_rods", []))
    
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
        """获取排行榜"""
        key = "fishing_leaderboard"
        leaderboard = await self.get_kv_data(key) or {}
        # 按钓鱼次数排序，返回前10
        sorted_users = sorted(leaderboard.items(), key=lambda x: x[1].get("count", 0) if isinstance(x[1], dict) else x[1], reverse=True)[:10]
        return [(uid, data.get("count", 0) if isinstance(data, dict) else data, data.get("name", "未知") if isinstance(data, dict) else "未知", data.get("level", 1) if isinstance(data, dict) else 1) for uid, data in sorted_users]
