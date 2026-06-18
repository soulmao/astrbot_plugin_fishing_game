"""用户数据模型模块"""
import time
import uuid
from typing import Optional, Dict, Any, List
from .fish_data import (
    LEVELS, ROD_BASES, ROD_PREFIXES, BAIT_BASES, BAIT_PREFIXES,
    calc_rod_value, calc_bait_value, calc_fish_value,
    get_rod_prefix, get_prefix_by_id, get_fish_by_id, get_bait_by_id,
    ENCHANT_CONFIG, ENCHANT_TICKETS, ACHIEVEMENTS,
    DIRECTED_ENCHANT_CONFIG, SHOP_UPGRADE_CONFIG,
)


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
        # 每日签到/成就迁移
        if "rarity_catch_count" not in self._data:
            self._data["rarity_catch_count"] = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
        if "last_fish_date" not in self._data:
            self._data["last_fish_date"] = ""
        if "consecutive_checkin_days" not in self._data:
            self._data["consecutive_checkin_days"] = 0
        if "achievements" not in self._data:
            self._data["achievements"] = []
        # 商店等级
        if "shop_level" not in self._data:
            self._data["shop_level"] = 0
        # 贪婪状态机
        if "greedy_state" not in self._data:
            self._data["greedy_state"] = None

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
            # 稀有度捕获统计
            "rarity_catch_count": {"common": 0, "rare": 0, "legendary": 0, "mythic": 0},
            # 每日签到
            "last_fish_date": "",
            "consecutive_checkin_days": 0,
            # 成就
            "achievements": [],
            # 商店等级
            "shop_level": 0,
            # 贪婪状态机（挂起状态）
            "greedy_state": None,
        }

    def to_dict(self) -> Dict:
        self._data["updated_at"] = int(time.time())
        return self._data

    # 金币
    @property
    def coins(self) -> int:
        return self._data.get("coins", 0)

    def add_coins(self, amount: int):
        if amount < 0:
            return False
        self._data["coins"] = self.coins + amount
        return True

    def remove_coins(self, amount: int) -> bool:
        if amount <= 0:
            return False
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

    def update_rod_prefix(self, instance_id: str, prefix_id: str) -> bool:
        """通过 instance_id 更新钓竿前缀（用于贪婪/无尽贪婪切换），同步更新当前装备"""
        for rod in self._data.get("owned_rods", []):
            if rod.get("instance_id") == instance_id:
                rod["prefix_id"] = prefix_id
                current = self._data.get("current_rod", {})
                if current.get("instance_id") == instance_id:
                    current["prefix_id"] = prefix_id
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

    # 稀有度统计
    @property
    def rarity_catch_count(self) -> dict:
        return self._data.setdefault("rarity_catch_count", {"common": 0, "rare": 0, "legendary": 0, "mythic": 0})

    def add_rarity_count(self, rarity: str, count: int = 1):
        counts = self.rarity_catch_count
        counts[rarity] = counts.get(rarity, 0) + count

    # 每日签到
    @property
    def last_fish_date(self) -> str:
        return self._data.get("last_fish_date", "")

    @property
    def consecutive_checkin_days(self) -> int:
        return self._data.get("consecutive_checkin_days", 0)

    def update_checkin(self, today: str) -> int:
        """更新签到日期并返回当前连续天数"""
        last = self.last_fish_date
        if not last:
            streak = 1
        else:
            try:
                from datetime import datetime, timedelta
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                if last == yesterday:
                    streak = self.consecutive_checkin_days + 1
                else:
                    streak = 1
            except Exception:
                streak = 1
        self._data["last_fish_date"] = today
        self._data["consecutive_checkin_days"] = streak
        return streak

    # 成就系统
    @property
    def achievements(self) -> list:
        return self._data.setdefault("achievements", [])

    def get_total_enchant_count(self) -> int:
        total = sum(r.get("enchant_count", 0) for r in self._data.get("owned_rods", []))
        current = self._data.get("current_rod", {})
        current_id = current.get("instance_id")
        if current_id and not any(r.get("instance_id") == current_id for r in self._data.get("owned_rods", [])):
            total += current.get("enchant_count", 0)
        return total

    def _achievement_condition(self, ach: dict) -> bool:
        """根据 category + target 判断单个成就是否达成"""
        cat = ach.get("category")
        target = ach.get("target", 0)
        rc = self.rarity_catch_count
        if cat == "fish_count":
            return self.total_fish_count >= target
        if cat == "rare_count":
            return rc.get("rare", 0) >= target
        if cat == "legendary_count":
            return rc.get("legendary", 0) >= target
        if cat == "mythic_count":
            return rc.get("mythic", 0) >= target
        if cat == "coins":
            return self.coins >= target
        if cat == "level":
            return self.level >= target
        if cat == "collection":
            return self.get_collection_count() >= target
        if cat == "enchant_count":
            return self.get_total_enchant_count() >= target
        if cat == "checkin_days":
            return self.consecutive_checkin_days >= target
        return False

    def check_achievements(self) -> list:
        """检查并解锁成就，返回本次新解锁的成就列表（已发放奖励）"""
        completed = set(self.achievements)
        new_unlocks = []
        for ach in ACHIEVEMENTS:
            if ach["id"] in completed:
                continue
            if self._achievement_condition(ach):
                completed.add(ach["id"])
                self.add_coins(ach.get("reward_coins", 0))
                self.add_exp(ach.get("reward_exp", 0))
                new_unlocks.append(ach)
        self._data["achievements"] = list(completed)
        return new_unlocks

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

    # 商店等级
    @property
    def shop_level(self) -> int:
        return self._data.get("shop_level", 0)

    @shop_level.setter
    def shop_level(self, value: int):
        self._data["shop_level"] = value

    # 贪婪状态机
    @property
    def greedy_state(self) -> Optional[Dict]:
        return self._data.get("greedy_state")

    def is_greedy_active(self) -> bool:
        state = self._data.get("greedy_state")
        return bool(state and state.get("active"))

    def start_greedy(self, rod_instance_id: str, rod_prefix_id: str, initial_bait: Dict,
                     chip: Dict, bait_cost_total: int) -> None:
        """启动一次贪婪挂起状态"""
        self._data["greedy_state"] = {
            "active": True,
            "stack": 1,
            "rod_instance_id": rod_instance_id,
            "rod_prefix_id": rod_prefix_id,
            "initial_bait": dict(initial_bait),
            "bait_cost_total": bait_cost_total,
            "chip": dict(chip),
        }

    def update_greedy_chip(self, chip: Dict, bait_cost_delta: int = 0, stack_delta: int = 1) -> bool:
        """更新贪婪结晶，层数默认 +1"""
        state = self._data.get("greedy_state")
        if not state or not state.get("active"):
            return False
        state["chip"] = dict(chip)
        state["stack"] = state.get("stack", 1) + stack_delta
        state["bait_cost_total"] = state.get("bait_cost_total", 0) + bait_cost_delta
        return True

    def clear_greedy(self) -> Optional[Dict]:
        """清空贪婪状态，返回被清空的旧状态"""
        old = self._data.get("greedy_state")
        self._data["greedy_state"] = None
        return old

    # 获取定向附魔券列表
    def get_directed_enchant_tickets(self) -> list:
        """返回 [(skill_id, value, count), ...] 的定向附魔券列表"""
        from .utils import parse_directed_enchant_id
        result = []
        for item in self._data.get("items", []):
            parsed = parse_directed_enchant_id(item.get("id", ""))
            if parsed:
                skill_id, value = parsed
                result.append((skill_id, value, item.get("count", 0)))
        return result
