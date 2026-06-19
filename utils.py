"""钓鱼游戏工具函数模块"""
import random
from typing import Optional, List
from .fish_data import (
    FISH_TYPES, FISH_PREFIXES, ROD_BASES, ROD_PREFIXES,
    BAIT_BASES, BAIT_PREFIXES, LEVELS, SHOP_ITEMS,
    get_fish_by_id, get_prefix_by_id, get_rod_by_id, get_bait_by_id,
    get_level_info, get_next_level_exp, ROD_SKILL_DESCRIPTIONS,
    ENCHANT_TICKETS, ENCHANT_CONFIG,
    DIRECTED_ENCHANT_CONFIG, SHOP_UPGRADE_CONFIG,
    calc_rod_value, calc_bait_value, calc_fish_value,
    get_rod_prefix, get_bait_prefix, get_effective_rod_skills,
    ARROGANT_COMPATIBLE_BASES, SPECIAL_PREFIX_BALANCE,
)
from .models import UserData


def format_time(seconds: int) -> str:
    """格式化时间"""
    if seconds <= 0:
        return "好了"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分")
    if secs > 0:
        parts.append(f"{secs}秒")
    if not parts:
        return "好了"
    return "".join(parts)


def format_rod_name(rod: dict, with_value: bool = False) -> str:
    """格式化钓竿名称"""
    base = get_rod_by_id(rod["base_id"])
    prefix = get_rod_prefix(rod["prefix_id"])
    name = "木制钓竿"
    if base:
        name = base["name"]
        if prefix:
            name = f"{prefix['name']}{name}"
    if with_value:
        value = calc_rod_value(
            rod.get("base_id", ""), rod.get("prefix_id", ""), rod.get("skills")
        )
        return f"{name}(价值{value}金币)"
    return name


def format_rod_skills(prefix_id: str, rod_skills: dict = None, base_id: str = "") -> str:
    """格式化原生、前缀和实例词条，实例词条覆盖同名默认值。"""
    effective_skills = get_effective_rod_skills(base_id, prefix_id, rod_skills)
    if not effective_skills:
        return ""
    parts = []
    # 标记型技能（无具体百分比，只显示标签）
    marker_skills = {"arrogant", "greedy", "endless_greedy", "cursed", "lucky_block", "jealous"}
    for sid, val in effective_skills.items():
        label = ROD_SKILL_DESCRIPTIONS.get(sid, sid)
        if sid in marker_skills:
            parts.append(f"{label}")
        elif sid in ("lucky", "exp_boost", "voyage", "mending"):
            parts.append(f"{label}+{int(val*100)}%")
        else:
            parts.append(f"{label}{int(val*100)}%")
    return " [" + " | ".join(parts) + "]"


def can_apply_rod_prefix(base_id: str, prefix_id: str) -> bool:
    """检查某前缀是否可以附加到某基础钓竿上
    
    特种钓竿（no_prefix）不允许任何前缀；
    傲慢前缀仅限金色/神级钓竿。
    """
    rod_base = get_rod_by_id(base_id)
    prefix = get_rod_prefix(prefix_id)
    if not rod_base or not prefix:
        return False
    # 特种钓竿（金币钓竿、胡萝卜钓竿）禁止任何前缀
    if rod_base.get("no_prefix"):
        return prefix_id == ""
    # 傲慢前缀白名单校验
    if prefix.get("skills", {}).get("arrogant"):
        return base_id in ARROGANT_COMPATIBLE_BASES
    return True


def format_bait_name(bait: dict) -> str:
    """格式化鱼饵名称"""
    base = get_bait_by_id(bait["base_id"])
    prefix = get_bait_prefix(bait["prefix_id"])
    if base and prefix:
        return f"{prefix['name']}{base['name']}"
    return "普通的蚯蚓"


def calc_enchant_price(rod: dict) -> int:
    """计算附魔价格 = 鱼竿价值 × 30% × 2^enchant_count（倍增）
    诅咒前缀享受折扣，但仍需承担可感知的养成成本。"""
    value = calc_rod_value(
        rod.get("base_id", ""), rod.get("prefix_id", ""), rod.get("skills")
    )
    enchant_count = rod.get("enchant_count", 0)
    base = int(value * ENCHANT_CONFIG["base_price_percent"])
    price = int(base * (2 ** enchant_count))
    # 诅咒前缀打折
    prefix = get_rod_prefix(rod.get("prefix_id", ""))
    if prefix.get("skills", {}).get("cursed"):
        price = int(price * SPECIAL_PREFIX_BALANCE["cursed"]["enchant_price_multiplier"])
    return max(1, price)


def calc_upgrade_price(rod: dict) -> int:
    """计算升级价格 = 鱼竿价值 × 30% × 2^enchant_count（与附魔同价）"""
    return calc_enchant_price(rod)


def get_available_skills() -> list:
    """获取所有可附魔的技能ID列表（失误/清贫为前缀专属，不加入附魔池）"""
    return ["swift", "lucky", "harvest", "treasure", "tide", "exp_boost", "voyage", "mending"]


SKILL_NAME_MAP = {
    "迅捷": "swift", "swift": "swift",
    "幸运": "lucky", "lucky": "lucky",
    "丰收": "harvest", "harvest": "harvest",
    "寻宝": "treasure", "treasure": "treasure",
    "潮汐": "tide", "tide": "tide",
    "神慧": "exp_boost", "exp_boost": "exp_boost",
    "远航": "voyage", "voyage": "voyage",
    "经验修补": "mending", "mending": "mending",
}

def parse_directed_enchant_id(item_id: str) -> tuple:
    """解析定向附魔券ID，返回 (skill_id, value) 或 None"""
    prefix = "directed_enchant_"
    if not item_id.startswith(prefix):
        return None
    rest = item_id[len(prefix):]
    parts = rest.rsplit("_", 1)
    if len(parts) != 2:
        return None
    skill_id, value_str = parts
    try:
        value = int(value_str) / 100
        return (skill_id, value)
    except ValueError:
        return None

def calc_directed_enchant_price(skill_id: str, value: float, user_exp: int) -> int:
    """计算定向附魔券价格 = 基础价 × (1 + 经验 / 系数)"""
    base = DIRECTED_ENCHANT_CONFIG["base_prices"].get(value, 100)
    factor = 1 + user_exp / DIRECTED_ENCHANT_CONFIG["exp_factor_divisor"]
    return int(base * factor)

def calc_shop_upgrade_price(shop_level: int) -> int:
    """计算商店升级价格 = 基础价 × 2^等级"""
    return int(SHOP_UPGRADE_CONFIG["base_price"] * (2 ** shop_level))

def get_shop_slot_count(shop_level: int) -> int:
    """计算商店展示条数 = 6 + 等级 × 2"""
    return 6 + shop_level * 2


def render_shop_text(items: list) -> str:
    """将商品列表渲染为商店文本（纯渲染，无IO/无锁）"""
    # 特殊物品的名称映射（不需要 base_id/prefix_id 的物品）
    SPECIAL_NAMES = {
        "refresh_token": "🔄 刷新券",
        "directed_enchant": "🎯 定向附魔券",
    }
    result = """🏪 钓鱼商店

"""
    for i, item in enumerate(items, 1):
        item_type = item["type"]
        if item_type == "rod":
            base = get_rod_by_id(item["base_id"])
            prefix = get_rod_prefix(item["prefix_id"])
            name = f"{prefix['name']}{base['name']}"
        elif item_type == "directed_enchant":
            name = item["name"]
        elif item_type in SPECIAL_NAMES:
            # 特殊物品（如刷新券）：使用映射名称，不访问 base_id
            name = SPECIAL_NAMES[item_type]
        else:
            base = get_bait_by_id(item["base_id"])
            prefix = get_bait_prefix(item["prefix_id"])
            name = f"{prefix['name']}{base['name']}"

        result += f"{i}. [{item_type}] {name}"
        if "quantity" in item:
            result += f" x{item['quantity']}"
        result += f" - {item['price']} 金币\n"

    result += "\n💡 使用 /购买 [编号] [数量] 购买"
    return result


def generate_shop_items(user: UserData) -> list:
    """根据用户等级和已拥有物品生成商店商品"""
    level = user.level
    items = []

    # 钓竿
    for rod in SHOP_ITEMS["rods"]:
        if rod["min_level"] <= level:
            base = get_rod_by_id(rod["base_id"])
            if base and base.get("no_prefix"):
                # 特种钓竿（金币钓竿、胡萝卜钓竿）不带前缀
                price = rod["price"]
                if price > 0:
                    items.append({
                        "type": "rod",
                        "base_id": rod["base_id"],
                        "prefix_id": "",
                        "price": int(price)
                    })
            else:
                for prefix in ROD_PREFIXES:
                    if "min_level" not in prefix or prefix["min_level"] <= level:
                        # 傲慢前缀只能出现在金色/神级钓竿上
                        if not can_apply_rod_prefix(rod["base_id"], prefix["id"]):
                            continue
                        price = rod["price"] * prefix["multiplier"]
                        if price > 0:  # 0价格为赠品
                            items.append({
                                "type": "rod",
                                "base_id": rod["base_id"],
                                "prefix_id": prefix["id"],
                                "price": int(price)
                            })

    # 鱼饵
    for bait in SHOP_ITEMS["baits"]:
        if bait["min_level"] <= level:
            for prefix in BAIT_PREFIXES:
                if "min_level" not in prefix or prefix["min_level"] <= level:
                    base = get_bait_by_id(bait["base_id"])
                    price = bait["price"] * prefix["multiplier"]
                    items.append({
                        "type": "bait",
                        "base_id": bait["base_id"],
                        "prefix_id": prefix["id"],
                        "quantity": bait["quantity"],
                        "price": int(price)
                    })

    # 刷新券
    for special in SHOP_ITEMS.get("special", []):
        if special["min_level"] <= level:
            items.append({
                "type": special["id"],
                "price": special["price"]
            })

    # 定向附魔券（每次刷新最多出现 2 个）
    available_skills = get_available_skills()
    if available_skills:
        de_count = min(2, len(available_skills))
        for _ in range(de_count):
            skill_id = random.choice(available_skills)
            value = random.choice(list(DIRECTED_ENCHANT_CONFIG["base_prices"].keys()))
            price = calc_directed_enchant_price(skill_id, value, user.exp)
            name = f"定向附魔券[{ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)}+{int(value*100)}%]"
            items.append({
                "type": "directed_enchant",
                "skill_id": skill_id,
                "value": value,
                "price": price,
                "name": name,
            })

    # 动态条数
    slot_count = get_shop_slot_count(user.shop_level)
    if len(items) > slot_count:
        items = random.sample(items, slot_count)

    return items


def get_item_name_for_auction(item_data: dict) -> str:
    """获取拍卖物品显示名称"""
    item_type = item_data.get("type", "")
    if item_type == "rod":
        return format_rod_name(item_data)
    elif item_type == "bait":
        base = get_bait_by_id(item_data.get("base_id", ""))
        prefix = get_bait_prefix(item_data.get("prefix_id", ""))
        if base and prefix:
            return f"{prefix['name']}{base['name']}"
        return "未知鱼饵"
    elif item_type == "fish":
        fish = get_fish_by_id(item_data.get("fish_id", ""))
        prefix = get_prefix_by_id(item_data.get("prefix_id", ""))
        if fish and prefix:
            return f"{prefix['name']}{fish['name']}"
        return "未知鱼类"
    elif item_type == "ticket":
        for t in ENCHANT_TICKETS:
            if t["id"] == item_data.get("ticket_id", ""):
                return t["name"]
        return "未知附魔券"
    elif item_type == "item":
        item_id = item_data.get("item_id", "")
        if item_id == "refresh_token":
            return "🔄 刷新券"
        parsed = parse_directed_enchant_id(item_id)
        if parsed:
            skill_id, value = parsed
            return f"🎯 定向附魔券[{ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)}+{int(value*100)}%]"
        return item_id or "未知道具"
    return "未知物品"


def calc_item_value(item_id: str, count: int = 1) -> int:
    """计算道具类物品默认价值（用于拍卖行定价和直接出售）"""
    if item_id == "refresh_token":
        return 30 * count
    parsed = parse_directed_enchant_id(item_id)
    if parsed:
        skill_id, value = parsed
        base_price = DIRECTED_ENCHANT_CONFIG["base_prices"].get(value, 0)
        return base_price * count
    return 0


def weighted_random_choice(items: list, key: str = "weight") -> dict:
    """按权重随机选择一项"""
    weights = [item.get(key, 0) for item in items]
    total = sum(weights)
    if total <= 0:
        return random.choice(items)
    r = random.uniform(0, total)
    cumulative = 0
    for item in items:
        cumulative += item.get(key, 0)
        if r <= cumulative:
            return item
    return items[-1]


def extract_target_user_id(raw: str) -> Optional[str]:
    """从命令参数中提取目标用户ID"""
    if not raw:
        return None
    cleaned = raw.lstrip("@").strip()
    if not cleaned:
        return None
    return cleaned


__all__ = [
    "format_time",
    "format_rod_name",
    "format_rod_skills",
    "format_bait_name",
    "calc_enchant_price",
    "calc_upgrade_price",
    "get_available_skills",
    "render_shop_text",
    "generate_shop_items",
    "get_item_name_for_auction",
    "weighted_random_choice",
    "extract_target_user_id",
]
