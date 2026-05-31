"""钓鱼游戏数据定义"""

# 鱼类后缀（真实存在的鱼 + 神话鱼类）
FISH_TYPES = [
    # 常见鱼类 (common)
    {"id": "fish_001", "name": "小杂鱼", "rarity": "common", "base_price": 5, "weight": 40},
    {"id": "fish_002", "name": "鲫鱼", "rarity": "common", "base_price": 8, "weight": 30},
    {"id": "fish_003", "name": "鲤鱼", "rarity": "common", "base_price": 15, "weight": 20},
    {"id": "fish_004", "name": "草鱼", "rarity": "common", "base_price": 20, "weight": 15},
    {"id": "fish_005", "name": "鲢鱼", "rarity": "common", "base_price": 25, "weight": 10},
    {"id": "fish_006", "name": "鳙鱼", "rarity": "common", "base_price": 30, "weight": 8},
    {"id": "fish_013", "name": "罗非鱼", "rarity": "common", "base_price": 12, "weight": 22},   # 新增常见鱼
    {"id": "fish_014", "name": "黑鱼", "rarity": "common", "base_price": 35, "weight": 11},     # 新增常见鱼
    # 稀有鱼类 (rare)
    {"id": "fish_007", "name": "鲈鱼", "rarity": "rare", "base_price": 50, "weight": 5},
    {"id": "fish_008", "name": "鳜鱼", "rarity": "rare", "base_price": 60, "weight": 4},
    {"id": "fish_009", "name": "鳟鱼", "rarity": "rare", "base_price": 70, "weight": 3},
    {"id": "fish_010", "name": "金鱼", "rarity": "rare", "base_price": 100, "weight": 2},
    # 传说鱼类 (legendary)
    {"id": "fish_011", "name": "龙鱼", "rarity": "legendary", "base_price": 300, "weight": 0.5},
    {"id": "fish_012", "name": "锦鲤", "rarity": "legendary", "base_price": 500, "weight": 0.3},
    # 神话鱼类 (mythic) - 需要高级钓竿和高等级才能钓到
    {"id": "fish_015", "name": "美人鱼", "rarity": "mythic", "base_price": 1200, "weight": 0.15},
    {"id": "fish_016", "name": "鲲", "rarity": "mythic", "base_price": 2000, "weight": 0.10,
     "desc": "北冥之鲲，不知其几千里也"},
    {"id": "fish_017", "name": "蛟龙", "rarity": "mythic", "base_price": 1800, "weight": 0.12},
    {"id": "fish_018", "name": "利维坦", "rarity": "mythic", "base_price": 3000, "weight": 0.05,
     "desc": "深海中的巨兽，圣经中记载的海怪"},
    {"id": "fish_019", "name": "九尾龟", "rarity": "mythic", "base_price": 2500, "weight": 0.08},
]

# 鱼名前缀
FISH_PREFIXES = [
    {"id": "pref_001", "name": "普通的", "rarity": "common", "price_multiplier": 1.0, "weight": 35},
    {"id": "pref_002", "name": "健康的", "rarity": "common", "price_multiplier": 1.3, "weight": 25},
    {"id": "pref_003", "name": "肥美的", "rarity": "common", "price_multiplier": 1.5, "weight": 15},
    {"id": "pref_004", "name": "银色的", "rarity": "rare", "price_multiplier": 2.0, "weight": 8, "min_level": 3},
    {"id": "pref_005", "name": "红色的", "rarity": "rare", "price_multiplier": 2.2, "weight": 6, "min_level": 3},
    {"id": "pref_006", "name": "蓝色的", "rarity": "rare", "price_multiplier": 2.5, "weight": 4, "min_level": 4},
    {"id": "pref_007", "name": "金色的", "rarity": "legendary", "price_multiplier": 5.0, "weight": 1.5, "min_level": 5},
    {"id": "pref_008", "name": "濒死的", "rarity": "rare", "price_multiplier": 0.5, "weight": 3},
    {"id": "pref_009", "name": "奄奄一息的", "rarity": "rare", "price_multiplier": 0.3, "weight": 1.5},
    {"id": "pref_010", "name": "传奇的", "rarity": "legendary", "price_multiplier": 10.0, "weight": 0.2, "min_level": 5, "requires_gold_rod": True},
    {"id": "pref_011", "name": "神灵的", "rarity": "legendary", "price_multiplier": 15.0, "weight": 0.05, "min_level": 7, "requires_divine_rod": True},
    # 神话级前缀
    {"id": "pref_012", "name": "远古的", "rarity": "mythic", "price_multiplier": 20.0, "weight": 0.03, "min_level": 6, "requires_gold_rod": True},
    {"id": "pref_013", "name": "神话的", "rarity": "mythic", "price_multiplier": 30.0, "weight": 0.01, "min_level": 7, "requires_divine_rod": True},
    # 古龙收藏系列前缀
    {"id": "pref_014", "name": "古龙收藏的", "rarity": "legendary", "price_multiplier": 18.0, "weight": 0.06, "min_level": 6, "requires_gold_rod": True},
]

# 钓竿基础类型
ROD_BASES = [
    {"id": "rod_001", "name": "木制钓竿", "quality": "common", "exp_multiplier": 1.0, "rarity_bonus": 0},
    {"id": "rod_002", "name": "竹制钓竿", "quality": "excellent", "exp_multiplier": 1.2, "rarity_bonus": 0.05},
    {"id": "rod_003", "name": "碳纤维钓竿", "quality": "rare", "exp_multiplier": 1.5, "rarity_bonus": 0.10},
    {"id": "rod_004", "name": "金色钓竿", "quality": "legendary", "exp_multiplier": 2.0, "rarity_bonus": 0.20},
    {"id": "rod_005", "name": "神级钓竿", "quality": "mythic", "exp_multiplier": 3.0, "rarity_bonus": 0.35},
]

# 钓竿前缀
ROD_PREFIXES = [
    {"id": "rod_pref_01", "name": "破旧的",  "multiplier": 0.5, "max_slots": 0},
    {"id": "rod_pref_02", "name": "老化的",  "multiplier": 0.7, "max_slots": 1},
    {"id": "rod_pref_03", "name": "普通的",  "multiplier": 1.0, "max_slots": 1},
    {"id": "rod_pref_04", "name": "耐用的",  "multiplier": 1.2, "max_slots": 2, "min_level": 2},
    {"id": "rod_pref_05", "name": "精良的",  "multiplier": 1.5, "max_slots": 2, "min_level": 2},
    {"id": "rod_pref_06", "name": "结实的",  "multiplier": 1.8, "max_slots": 3, "min_level": 3,
     "skills": {"swift": 0.10}},
    {"id": "rod_pref_07", "name": "精致的",  "multiplier": 2.0, "max_slots": 4, "min_level": 4,
     "skills": {"swift": 0.20, "lucky": 0.05}},
    {"id": "rod_pref_08", "name": "华丽的",  "multiplier": 2.5, "max_slots": 5, "min_level": 5,
     "skills": {"swift": 0.30, "lucky": 0.08, "harvest": 0.10}},
    {"id": "rod_pref_09", "name": "史诗的",  "multiplier": 3.0, "max_slots": 6, "min_level": 6,
     "skills": {"swift": 0.40, "lucky": 0.12, "harvest": 0.15, "treasure": 0.12}},
    {"id": "rod_pref_10", "name": "传说的",  "multiplier": 5.0, "max_slots": 8, "min_level": 7,
     "skills": {"swift": 0.50, "lucky": 0.20, "harvest": 0.25, "treasure": 0.20, "tide": 0.05, "exp_boost": 0.30}},
    # 古龙收藏系列钓竿前缀
    {"id": "rod_pref_11", "name": "古龙收藏的", "multiplier": 4.0, "max_slots": 10, "min_level": 7,
     "skills": {"swift": 0.35, "lucky": 0.25, "harvest": 0.20, "treasure": 0.25, "tide": 0.08, "exp_boost": 0.40}},
]

# 鱼饵基础类型
BAIT_BASES = [
    {"id": "bait_001", "name": "蚯蚓", "quality": "common", "exp_multiplier": 1.0, "quality_bonus": 0},
    {"id": "bait_002", "name": "饵料", "quality": "excellent", "exp_multiplier": 1.3, "quality_bonus": 0.05},
    {"id": "bait_003", "name": "香料饵", "quality": "rare", "exp_multiplier": 1.5, "quality_bonus": 0.10},
    {"id": "bait_004", "name": "传说饵", "quality": "legendary", "exp_multiplier": 2.0, "quality_bonus": 0.20},
]

# 鱼饵前缀
BAIT_PREFIXES = [
    {"id": "bait_pref_01", "name": "干瘪的", "multiplier": 0.5},
    {"id": "bait_pref_02", "name": "普通的", "multiplier": 1.0},
    {"id": "bait_pref_03", "name": "新鲜的", "multiplier": 1.3, "min_level": 2},
    {"id": "bait_pref_04", "name": "香喷喷的", "multiplier": 1.5, "min_level": 3},
    {"id": "bait_pref_05", "name": "特制的", "multiplier": 1.8, "min_level": 4},
    {"id": "bait_pref_06", "name": "珍稀的", "multiplier": 2.0, "min_level": 5},
    {"id": "bait_pref_07", "name": "诱人的", "multiplier": 2.5, "min_level": 6},
    {"id": "bait_pref_08", "name": "秘制的", "multiplier": 3.0, "min_level": 7},
    # 古龙收藏系列鱼饵前缀
    {"id": "bait_pref_09", "name": "古龙收藏的", "multiplier": 2.8, "min_level": 7, "event_bonus": 0.20},
]

# 等级配置
LEVELS = [
    {"level": 1, "name": "新手渔夫", "exp_required": 0},
    {"level": 2, "name": "入门渔夫", "exp_required": 100},
    {"level": 3, "name": "熟练渔夫", "exp_required": 300},
    {"level": 4, "name": "老练渔夫", "exp_required": 600},
    {"level": 5, "name": "专家渔夫", "exp_required": 1000},
    {"level": 6, "name": "大师渔夫", "exp_required": 2000},
    {"level": 7, "name": "传说渔夫", "exp_required": 5000},
]

# 商店商品定义（用于随机生成）
SHOP_ITEMS = {
    "rods": [
        {"base_id": "rod_001", "price": 0, "min_level": 1},     # 木制钓竿
        {"base_id": "rod_002", "price": 200, "min_level": 2},   # 竹制钓竿
        {"base_id": "rod_003", "price": 500, "min_level": 4},   # 碳纤维钓竿
        {"base_id": "rod_004", "price": 2000, "min_level": 6},  # 金色钓竿
        {"base_id": "rod_005", "price": 5000, "min_level": 7},  # 神级钓竿
    ],
    "baits": [
        {"base_id": "bait_001", "price": 10, "quantity": 5, "min_level": 1},  # 蚯蚓
        {"base_id": "bait_002", "price": 30, "quantity": 3, "min_level": 2},  # 饵料
        {"base_id": "bait_003", "price": 80, "quantity": 2, "min_level": 4},  # 香料饵
        {"base_id": "bait_004", "price": 200, "quantity": 1, "min_level": 6}, # 传说饵
    ],
    "special": [
        {"id": "refresh_token", "name": "刷新券", "price": 30, "quantity": 1, "min_level": 3},
    ]
}

# 附魔券
ENCHANT_TICKETS = [
    {"id": "ench_ticket_001", "name": "普通的附魔券", "quality": "common",   "discount": 0.20, "weight": 0.0100},
    {"id": "ench_ticket_002", "name": "精良的附魔券", "quality": "excellent","discount": 0.40, "weight": 0.0040},
    {"id": "ench_ticket_003", "name": "史诗的附魔券", "quality": "epic",     "discount": 0.50, "weight": 0.0015},
    {"id": "ench_ticket_004", "name": "传说的附魔券", "quality": "legendary","discount": 0.60, "weight": 0.0005},
]

# 赠送限制
GIVE_LIMITS = {
    "daily_limit": 10,
    "max_per_give": 99,
}

# 拍卖行配置
AUCTION_CONFIG = {
    "default_price_percent": 0.30,   # 默认上架价格 = 价值 × 30%
    "price_range_percent": 0.30,     # 价格浮动范围 ±30%
    "listing_duration_hours": 24,    # 拍卖物品保留时长
}

# 附魔配置
ENCHANT_CONFIG = {
    "base_price_percent": 0.30,      # 附魔基础价为鱼竿价值的 30%
    "max_skill_value": 0.50,         # 单技能升级上限 50%
    "upgrade_increment": 0.05,       # 每次升级增加 5%
}

def get_fish_by_id(fish_id: str) -> dict:
    for fish in FISH_TYPES:
        if fish["id"] == fish_id:
            return fish
    return None

def get_prefix_by_id(prefix_id: str) -> dict:
    for prefix in FISH_PREFIXES:
        if prefix["id"] == prefix_id:
            return prefix
    return None

def get_rod_by_id(rod_id: str) -> dict:
    for rod in ROD_BASES:
        if rod["id"] == rod_id:
            return rod
    return None

def get_bait_by_id(bait_id: str) -> dict:
    for bait in BAIT_BASES:
        if bait["id"] == bait_id:
            return bait
    return None

def get_level_info(level: int) -> dict:
    for lvl in LEVELS:
        if lvl["level"] == level:
            return lvl
    return LEVELS[-1]

from typing import Optional

def get_next_level_exp(level: int) -> Optional[int]:
    for lvl in LEVELS:
        if lvl["level"] == level + 1:
            return lvl["exp_required"]
    return None  # 已满级


def get_rod_prefix(prefix_id: str) -> dict:
    for p in ROD_PREFIXES:
        if p["id"] == prefix_id:
            return p
    return ROD_PREFIXES[2]  # 默认"普通的"


def get_bait_prefix(prefix_id: str) -> dict:
    for p in BAIT_PREFIXES:
        if p["id"] == prefix_id:
            return p
    return BAIT_PREFIXES[1]  # 默认"普通的"


def get_rod_shop_price(base_id: str) -> int:
    """从 SHOP_ITEMS 查钓竿基础商店售价"""
    for rod in SHOP_ITEMS.get("rods", []):
        if rod["base_id"] == base_id:
            return rod["price"]
    return 0


def get_bait_shop_price(base_id: str) -> int:
    """从 SHOP_ITEMS 查鱼饵基础商店单价"""
    for bait in SHOP_ITEMS.get("baits", []):
        if bait["base_id"] == base_id:
            return bait["price"]
    return 0


def calc_rod_value(base_id: str, prefix_id: str, skills: dict = None) -> int:
    """计算钓竿价值 = 商店售价 × 前缀倍率 × ∏(1 + skill_value)"""
    rod_shop = get_rod_shop_price(base_id)
    prefix = get_rod_prefix(prefix_id)
    shop_price = int(rod_shop * prefix["multiplier"])
    if shop_price <= 0:
        shop_price = 50  # 保底价值（如木制钓竿商店价0）
    multiplier = 1.0
    # 优先使用传入的 skills，否则使用前缀默认 skills
    effective_skills = skills if skills is not None else prefix.get("skills", {})
    for val in effective_skills.values():
        multiplier *= (1 + val)
    return int(shop_price * multiplier)


def calc_bait_value(base_id: str, prefix_id: str, count: int) -> int:
    """鱼饵价值 = 商店单价 × 前缀倍率 × 数量"""
    bait_shop = get_bait_shop_price(base_id)
    prefix = get_bait_prefix(prefix_id)
    unit_price = int(bait_shop * prefix["multiplier"])
    return unit_price * count


def calc_fish_value(fish_id: str, prefix_id: str, count: int) -> int:
    """鱼类价值 = base_price × price_multiplier × count（与售价一致）"""
    fish = get_fish_by_id(fish_id)
    prefix = get_prefix_by_id(prefix_id)
    if not fish or not prefix:
        return 0
    price = int(fish["base_price"] * prefix["price_multiplier"])
    # 古龙收藏系列鱼额外 20% 收藏家溢价
    if prefix_id == "pref_014":
        price = int(price * 1.2)
    return price * count


# 钓竿技能说明
ROD_SKILL_DESCRIPTIONS = {
    "swift": "⚡迅捷",
    "lucky": "🍀幸运",
    "harvest": "🌾丰收",
    "treasure": "💎寻宝",
    "tide": "🌊潮汐",
    "exp_boost": "✨神慧",
}