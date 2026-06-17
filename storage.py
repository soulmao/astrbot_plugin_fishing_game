"""用户数据存储模块"""
import time
from typing import Optional, Dict, Any
from .fish_data import (
    calc_rod_value, calc_bait_value, calc_fish_value,
    get_rod_prefix, get_prefix_by_id, get_fish_by_id, get_bait_by_id,
    ENCHANT_CONFIG, ENCHANT_TICKETS,
)
from .models import UserData
import uuid
import asyncio

class StorageManager:
    """存储管理器"""
    def __init__(self, star):
        self.star = star
        self._auction_lock = asyncio.Lock()
        self._level_cache_lock = asyncio.Lock()
        self._level_distribution_cache: Dict[int, int] = {}
        self._level_cache_timestamp = 0

    async def update_level_distribution_cache(self):
        """重建用户等级分布缓存，建议每日刷新时调用"""
        async with self._level_cache_lock:
            all_ids = await self.get_all_user_ids()
            dist: Dict[int, int] = {}
            for uid in all_ids:
                try:
                    user = await self.get_user(uid)
                    dist[user.level] = dist.get(user.level, 0) + 1
                except Exception:
                    continue
            self._level_distribution_cache = dist
            self._level_cache_timestamp = int(time.time())

    async def get_higher_level_count(self, user_level: int) -> int:
        """返回等级严格高于 user_level 的玩家数量；缓存为空时自动重建一次"""
        async with self._level_cache_lock:
            if not self._level_distribution_cache:
                all_ids = await self.get_all_user_ids()
                dist: Dict[int, int] = {}
                for uid in all_ids:
                    try:
                        user = await self.get_user(uid)
                        dist[user.level] = dist.get(user.level, 0) + 1
                    except Exception:
                        continue
                self._level_distribution_cache = dist
                self._level_cache_timestamp = int(time.time())
            return sum(
                count for lvl, count in self._level_distribution_cache.items()
                if lvl > user_level
            )

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
