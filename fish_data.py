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
    # ========== 软体/甲壳/虾蟹类新增 ==========
    # 常见类 (common) - 价格 3~20，权重 25~40
    {"id": "fish_020", "name": "河虾", "rarity": "common", "base_price": 6, "weight": 35},
    {"id": "fish_021", "name": "小螃蟹", "rarity": "common", "base_price": 10, "weight": 25},
    {"id": "fish_022", "name": "河蚌", "rarity": "common", "base_price": 4, "weight": 40},
    {"id": "fish_023", "name": "小章鱼", "rarity": "common", "base_price": 18, "weight": 15},
    # 稀有类 (rare) - 价格 40~90，权重 3~7
    {"id": "fish_024", "name": "章鱼", "rarity": "rare", "base_price": 55, "weight": 4},
    {"id": "fish_025", "name": "鱿鱼", "rarity": "rare", "base_price": 45, "weight": 5},
    {"id": "fish_026", "name": "皮皮虾", "rarity": "rare", "base_price": 65, "weight": 4},
    {"id": "fish_027", "name": "大闸蟹", "rarity": "rare", "base_price": 85, "weight": 6},
    {"id": "fish_028", "name": "海星", "rarity": "rare", "base_price": 40, "weight": 7},
    {"id": "fish_029", "name": "墨鱼", "rarity": "rare", "base_price": 75, "weight": 3},
    # 传说类 (legendary) - 价格 300~500，权重 0.2~0.6
    {"id": "fish_030", "name": "澳洲龙虾", "rarity": "legendary", "base_price": 400, "weight": 0.4},
    {"id": "fish_031", "name": "帝王蟹", "rarity": "legendary", "base_price": 350, "weight": 0.6},
    {"id": "fish_032", "name": "大王乌贼", "rarity": "legendary", "base_price": 450, "weight": 0.2},
    {"id": "fish_033", "name": "蓝龙虾", "rarity": "legendary", "base_price": 480, "weight": 0.3},
    # 神话类 (mythic) - 价格 1200~3500，权重 0.03~0.15
    {"id": "fish_034", "name": "巨型章鱼", "rarity": "mythic", "base_price": 1500, "weight": 0.1,
     "desc": "触手长达数十米的深海怪物，能轻易缠绕整艘渔船"},
    {"id": "fish_035", "name": "深海巨蟹", "rarity": "mythic", "base_price": 2200, "weight": 0.07,
     "desc": "生活在海底火山口的庞然大物，甲壳如钢铁般坚硬"},
    {"id": "fish_036", "name": "北海巨妖", "rarity": "mythic", "base_price": 3200, "weight": 0.03,
     "desc": "北欧神话中的克拉肯，沉睡时会被误认为是一座小岛"},
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
    # 诅咒专属前缀
    {"id": "pref_015", "name": "被诅咒的", "rarity": "rare", "price_multiplier": 5.0, "weight": 0},
]

# 钓竿基础类型
ROD_BASES = [
    {"id": "rod_001", "name": "木制钓竿", "quality": "common", "exp_multiplier": 1.0, "rarity_bonus": 0},
    {"id": "rod_002", "name": "竹制钓竿", "quality": "excellent", "exp_multiplier": 1.2, "rarity_bonus": 0.05},
    {"id": "rod_003", "name": "碳纤维钓竿", "quality": "rare", "exp_multiplier": 1.5, "rarity_bonus": 0.10},
    {"id": "rod_004", "name": "金色钓竿", "quality": "legendary", "exp_multiplier": 2.0, "rarity_bonus": 0.20},
    {"id": "rod_005", "name": "神级钓竿", "quality": "mythic", "exp_multiplier": 3.0, "rarity_bonus": 0.35},
    # 特种钓竿（不能带前缀）
    {"id": "rod_006", "name": "金币钓竿", "quality": "legendary", "exp_multiplier": 2.5, "rarity_bonus": 0.25, "no_prefix": True},
    {"id": "rod_007", "name": "胡萝卜钓竿", "quality": "epic", "exp_multiplier": 1.8, "rarity_bonus": 0.15, "no_prefix": True},
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
    # 新增特殊前缀
    {"id": "rod_pref_12", "name": "贪婪的", "multiplier": 2.0, "max_slots": 5, "min_level": 5,
     "skills": {"greedy": 1.0}},
    {"id": "rod_pref_19", "name": "无尽贪婪的", "multiplier": 2.5, "max_slots": 6, "min_level": 7,
     "skills": {"endless_greedy": 1.0}},
    {"id": "rod_pref_13", "name": "诅咒的", "multiplier": 0.8, "max_slots": 6, "min_level": 5,
     "skills": {"cursed": 1.0}},
    {"id": "rod_pref_14", "name": "迅捷的", "multiplier": 1.5, "max_slots": 3, "min_level": 4,
     "skills": {"swift": 0.60, "tide": 0.50, "fail_chance": 0.15}},
    {"id": "rod_pref_15", "name": "学徒的", "multiplier": 0.9, "max_slots": 2, "min_level": 3,
     "skills": {"exp_boost": 0.80, "coin_reduce": 0.50}},
    {"id": "rod_pref_16", "name": "幸运方块的", "multiplier": 1.8, "max_slots": 99, "min_level": 6,
     "skills": {"lucky_block": 1.0}},
    # 傲慢前缀：仅限金色/神级钓竿；睥睨过滤低稀有度鱼，自负要求鱼饵品质 >= rare
    {"id": "rod_pref_17", "name": "傲慢的", "multiplier": 2.2, "max_slots": 5, "min_level": 6,
     "skills": {"arrogant": 1.0}},
    # 嫉妒前缀：攀比之力，等级差距带来稀有度加成
    {"id": "rod_pref_18", "name": "嫉妒的", "multiplier": 2.0, "max_slots": 5, "min_level": 5,
     "skills": {"jealous": 1.0}},
]

# 傲慢前缀可附加的基础钓竿白名单
ARROGANT_COMPATIBLE_BASES = {"rod_004", "rod_005"}

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
    {"level": 5, "name": "专家渔夫", "exp_required": 1200},
    {"level": 6, "name": "大师渔夫", "exp_required": 3000},
    {"level": 7, "name": "传说渔夫", "exp_required": 8000},
    {"level": 8, "name": "神话渔夫", "exp_required": 20000},
    {"level": 9, "name": "海王", "exp_required": 50000},
    {"level": 10, "name": "深渊行者", "exp_required": 120000},
    {"level": 11, "name": "远古钓者", "exp_required": 300000},
    {"level": 12, "name": "钓鱼之神", "exp_required": 800000},
]

# 商店商品定义（用于随机生成）
SHOP_ITEMS = {
    "rods": [
        {"base_id": "rod_001", "price": 0, "min_level": 1},     # 木制钓竿
        {"base_id": "rod_002", "price": 200, "min_level": 2},   # 竹制钓竿
        {"base_id": "rod_003", "price": 500, "min_level": 4},   # 碳纤维钓竿
        {"base_id": "rod_004", "price": 2000, "min_level": 6},  # 金色钓竿
        {"base_id": "rod_005", "price": 5000, "min_level": 7},  # 神级钓竿
        {"base_id": "rod_006", "price": 3000, "min_level": 6},  # 金币钓竿
        {"base_id": "rod_007", "price": 1500, "min_level": 5},  # 胡萝卜钓竿
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

# 定向附魔券配置
DIRECTED_ENCHANT_CONFIG = {
    "base_prices": {0.05: 500, 0.10: 1000, 0.15: 1500},
    "exp_factor_divisor": 10000,     # 价格 = base * (1 + exp / divisor)
}

# 商店升级配置
SHOP_UPGRADE_CONFIG = {
    "base_price": 500,
    "max_level": 12,
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
    if not prefix_id:
        # 特种钓竿（金币钓竿、胡萝卜钓竿）不带前缀
        return {"id": "", "name": "", "multiplier": 1.0, "max_slots": 0, "skills": {}}
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
    # 叠加：前缀默认技能 + 附魔技能覆盖同名键
    effective_skills = dict(prefix.get("skills", {}))
    if skills is not None:
        effective_skills.update(skills)
    for val in effective_skills.values():
        multiplier *= (1 + val)
    return int(shop_price * multiplier)


def scramble_text(text: str, intensity: float) -> str:
    """文字打乱：intensity 0~1，随机替换为unicode符号，最多替换30%字符"""
    import random
    if not text or intensity <= 0:
        return text
    chars = list(text)
    # 可替换的 Unicode 符号池（字母、符号、颜文字组件等）
    unicode_pool = (
        "?"
    )
    max_replace = max(1, int(len(chars) * 0.75))  # 最多替换75%
    actual_replace = max(1, int(max_replace * min(intensity, 1.0)))
    indices = random.sample(range(len(chars)), min(actual_replace, len(chars)))
    for idx in indices:
        if chars[idx].strip():  # 不替换空白字符，保持可读性
            chars[idx] = random.choice(unicode_pool)
    return "".join(chars)


def add_pig_noise(text: str, chance: float = 0.3) -> str:
    """胡萝卜钓竿：在文本中随机位置插入哼/🐷等符号"""
    import random
    if not text:
        return text
    noises = ["哼", "🐷", "呼噜", "🐽", "哼哼"]
    chars = list(text)
    insert_count = max(1, int(len(chars) * chance * 0.1))
    for _ in range(insert_count):
        pos = random.randint(0, len(chars))
        noise = random.choice(noises)
        chars.insert(pos, noise)
    return "".join(chars)


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
    "voyage": "🧭远航",
    "mending": "🔧经验修补",
    "greedy": "💰贪婪",
    "cursed": "👻诅咒",
    "fail_chance": "💥失误",
    "coin_reduce": "📉清贫",
    "lucky_block": "🎲幸运方块",
    "arrogant": "👑傲慢",
    "jealous": "💢嫉妒",
    "endless_greedy": "♾️无尽贪婪",
}

# 成就定义
# category 说明:
#   fish_count      -> total_fish_count >= target
#   rare_count      -> rarity_catch_count["rare"] >= target
#   legendary_count -> rarity_catch_count["legendary"] >= target
#   mythic_count    -> rarity_catch_count["mythic"] >= target
#   coins           -> coins >= target
#   level           -> level >= target
#   collection      -> collection 数量 >= target
#   enchant_count   -> 所有钓竿 enchant_count 之和 >= target
#   checkin_days    -> consecutive_checkin_days >= target
ACHIEVEMENTS = [
    # 累计钓鱼
    {"id": "first_fish", "name": "初出茅庐", "category": "fish_count", "target": 1, "reward_coins": 20, "reward_exp": 10},
    {"id": "novice_angler", "name": "新手渔夫", "category": "fish_count", "target": 10, "reward_coins": 50, "reward_exp": 30},
    {"id": "experienced_angler", "name": "资深渔夫", "category": "fish_count", "target": 100, "reward_coins": 200, "reward_exp": 100},
    {"id": "master_angler", "name": "钓鱼大师", "category": "fish_count", "target": 500, "reward_coins": 1000, "reward_exp": 500},
    {"id": "legend_angler", "name": "钓鱼传说", "category": "fish_count", "target": 1000, "reward_coins": 5000, "reward_exp": 2000},
    {"id": "fish_god", "name": "万竿之王", "category": "fish_count", "target": 2000, "reward_coins": 15000, "reward_exp": 5000},
    {"id": "eternal_angler", "name": "永恒钓者", "category": "fish_count", "target": 5000, "reward_coins": 50000, "reward_exp": 20000},

    # 稀有度捕获
    {"id": "first_rare", "name": "稀有发现", "category": "rare_count", "target": 1, "reward_coins": 100, "reward_exp": 50},
    {"id": "rare_collector", "name": "稀有收藏家", "category": "rare_count", "target": 50, "reward_coins": 500, "reward_exp": 200},
    {"id": "rare_hoarder", "name": "稀有囤积者", "category": "rare_count", "target": 200, "reward_coins": 2000, "reward_exp": 800},
    {"id": "rare_emperor", "name": "稀有帝王", "category": "rare_count", "target": 500, "reward_coins": 8000, "reward_exp": 3000},

    {"id": "first_legendary", "name": "传说诞生", "category": "legendary_count", "target": 1, "reward_coins": 500, "reward_exp": 200},
    {"id": "legendary_collector", "name": "传说收藏家", "category": "legendary_count", "target": 20, "reward_coins": 2000, "reward_exp": 800},
    {"id": "legendary_hunter", "name": "传说猎手", "category": "legendary_count", "target": 50, "reward_coins": 8000, "reward_exp": 3000},
    {"id": "legendary_lord", "name": "传说领主", "category": "legendary_count", "target": 100, "reward_coins": 25000, "reward_exp": 10000},

    {"id": "first_mythic", "name": "神话降临", "category": "mythic_count", "target": 1, "reward_coins": 2000, "reward_exp": 1000},
    {"id": "mythic_hunter", "name": "神话猎人", "category": "mythic_count", "target": 10, "reward_coins": 10000, "reward_exp": 5000},
    {"id": "mythic_collector", "name": "神话收藏家", "category": "mythic_count", "target": 25, "reward_coins": 30000, "reward_exp": 15000},
    {"id": "mythic_god", "name": "神话之主", "category": "mythic_count", "target": 50, "reward_coins": 100000, "reward_exp": 50000},

    # 金币积累
    {"id": "rich", "name": "小有余财", "category": "coins", "target": 1000, "reward_coins": 100, "reward_exp": 50},
    {"id": "wealthy", "name": "富可敌国", "category": "coins", "target": 10000, "reward_coins": 1000, "reward_exp": 500},
    {"id": "millionaire", "name": "百万富翁", "category": "coins", "target": 50000, "reward_coins": 5000, "reward_exp": 2000},
    {"id": "gold_magnate", "name": "金币大亨", "category": "coins", "target": 100000, "reward_coins": 10000, "reward_exp": 5000},
    {"id": "treasure_king", "name": "寻宝之王", "category": "coins", "target": 500000, "reward_coins": 50000, "reward_exp": 20000},
    {"id": "coin_god", "name": "财富之神", "category": "coins", "target": 1000000, "reward_coins": 100000, "reward_exp": 50000},

    # 等级
    {"id": "level_3", "name": "入门渔夫", "category": "level", "target": 3, "reward_coins": 100, "reward_exp": 50},
    {"id": "level_5", "name": "专家渔夫", "category": "level", "target": 5, "reward_coins": 500, "reward_exp": 200},
    {"id": "level_7", "name": "传说渔夫", "category": "level", "target": 7, "reward_coins": 2000, "reward_exp": 1000},
    {"id": "level_9", "name": "海王", "category": "level", "target": 9, "reward_coins": 10000, "reward_exp": 5000},
    {"id": "level_11", "name": "远古钓者", "category": "level", "target": 11, "reward_coins": 50000, "reward_exp": 20000},
    {"id": "level_12", "name": "钓鱼之神", "category": "level", "target": 12, "reward_coins": 200000, "reward_exp": 100000},

    # 图鉴
    {"id": "collector_10", "name": "初识图鉴", "desc": "点亮 10 个图鉴条目（含不同前缀）", "category": "collection", "target": 10, "reward_coins": 100, "reward_exp": 50},
    {"id": "collector_50", "name": "图鉴达人", "desc": "点亮 50 个图鉴条目（含不同前缀）", "category": "collection", "target": 50, "reward_coins": 500, "reward_exp": 200},
    {"id": "collector_100", "name": "图鉴大师", "desc": "点亮 100 个图鉴条目（含不同前缀）", "category": "collection", "target": 100, "reward_coins": 2000, "reward_exp": 1000},
    {"id": "collector_200", "name": "图鉴宗师", "desc": "点亮 200 个图鉴条目（含不同前缀）", "category": "collection", "target": 200, "reward_coins": 10000, "reward_exp": 5000},
    {"id": "collector_500", "name": "图鉴全通", "desc": "点亮 500 个图鉴条目（含不同前缀）", "category": "collection", "target": 500, "reward_coins": 50000, "reward_exp": 20000},

    # 附魔
    {"id": "first_enchant", "name": "初识附魔", "category": "enchant_count", "target": 1, "reward_coins": 100, "reward_exp": 50},
    {"id": "enchanter_10", "name": "附魔学徒", "category": "enchant_count", "target": 10, "reward_coins": 500, "reward_exp": 200},
    {"id": "enchanter_50", "name": "附魔大师", "category": "enchant_count", "target": 50, "reward_coins": 5000, "reward_exp": 2000},
    {"id": "enchanter_100", "name": "附魔之神", "category": "enchant_count", "target": 100, "reward_coins": 20000, "reward_exp": 10000},

    # 连续签到
    {"id": "daily_3", "name": "持之以恒", "category": "checkin_days", "target": 3, "reward_coins": 200, "reward_exp": 100},
    {"id": "daily_7", "name": "风雨无阻", "category": "checkin_days", "target": 7, "reward_coins": 1000, "reward_exp": 500},
    {"id": "daily_14", "name": "坚持不懈", "category": "checkin_days", "target": 14, "reward_coins": 3000, "reward_exp": 1500},
    {"id": "daily_30", "name": "签到王者", "category": "checkin_days", "target": 30, "reward_coins": 10000, "reward_exp": 5000},
]
