"""商店与拍卖行的结构化图片视图。"""

import html
import math
import time

from .fish_data import (
    ROD_SKILL_DESCRIPTIONS,
    get_bait_by_id,
    get_bait_prefix,
    get_effective_rod_skills,
    get_fish_by_id,
    get_prefix_by_id,
    get_rod_by_id,
    get_rod_prefix,
)
from .utils import get_item_name_for_auction, get_shop_slot_count


MARKER_SKILLS = {
    "arrogant", "greedy", "endless_greedy", "cursed", "lucky_block", "jealous",
}
TYPE_META = {
    "rod": ("钓竿", "🎣"),
    "bait": ("鱼饵", "🪤"),
    "fish": ("渔获", "🐠"),
    "ticket": ("附魔券", "🎫"),
    "item": ("道具", "🧰"),
    "refresh_token": ("道具", "🔄"),
    "directed_enchant": ("附魔券", "🎯"),
}


def _safe(value) -> str:
    """转义进入 HTML 的动态文本。"""
    return html.escape(str(value), quote=True)


def _number(value) -> str:
    return f"{int(value):,}"


def _remaining_text(seconds: int) -> str:
    """把剩余秒数压缩为适合卡片的中文时间。"""
    seconds = max(0, int(seconds))
    if seconds <= 0:
        return "即将结束"
    days, remain = divmod(seconds, 86400)
    hours, remain = divmod(remain, 3600)
    minutes = remain // 60
    if days:
        return f"{days}天{hours}小时"
    if hours:
        return f"{hours}小时{minutes}分"
    return f"{max(1, minutes)}分钟"


def _build_skills(base_id: str, prefix_id: str, skills=None) -> list:
    result = []
    for skill_id, value in get_effective_rod_skills(base_id, prefix_id, skills).items():
        label = ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)
        value_text = "特殊效果" if skill_id in MARKER_SKILLS else f"{int(round(float(value) * 100))}%"
        result.append({"name": _safe(label), "value": _safe(value_text)})
    return result


def _shop_item_name(item: dict) -> str:
    item_type = item.get("type", "")
    if item_type == "rod":
        base = get_rod_by_id(item.get("base_id", "")) or {}
        if base.get("no_prefix"):
            return base.get("name", "未知钓竿")
        prefix = get_rod_prefix(item.get("prefix_id", ""))
        return f"{prefix.get('name', '')}{base.get('name', '未知钓竿')}"
    if item_type == "bait":
        base = get_bait_by_id(item.get("base_id", "")) or {}
        prefix = get_bait_prefix(item.get("prefix_id", ""))
        return f"{prefix.get('name', '')}{base.get('name', '未知鱼饵')}"
    if item_type == "directed_enchant":
        return item.get("name", "定向附魔券").replace("[", " · ").replace("]", "")
    if item_type == "refresh_token":
        return "刷新券"
    return item.get("name", item_type or "未知商品")


def build_shop_view(user, sender_name: str) -> dict:
    """构建当前玩家商店的图片数据。"""
    items = []
    for index, item in enumerate(user.get("current_shop", []), 1):
        item_type = item.get("type", "")
        type_name, icon = TYPE_META.get(item_type, ("商品", "📦"))
        quantity = max(1, int(item.get("quantity", 1)))
        price = max(0, int(item.get("price", 0)))
        items.append({
            "index": index,
            "name": _safe(_shop_item_name(item)),
            "type": _safe(item_type or "other"),
            "type_name": _safe(type_name),
            "icon": icon,
            "quantity": _number(quantity) if quantity > 1 else "",
            "price": _number(price),
            "affordable": int(user.coins) >= price,
            "skills": _build_skills(
                item.get("base_id", ""), item.get("prefix_id", ""), {}
            ) if item_type == "rod" else [],
        })

    refresh_remaining = max(0, int(user.shop_refresh_cd - time.time()))
    return {
        "user_name": _safe(sender_name or "垂钓者"),
        "coins": _number(user.coins),
        "shop_level": int(user.shop_level),
        "slot_count": get_shop_slot_count(user.shop_level),
        "refresh_status": "可立即刷新" if refresh_remaining <= 0 else _remaining_text(refresh_remaining),
        "items": items,
    }


def build_auction_view(
    listings: list,
    total: int,
    page: int = 1,
    keyword: str = "",
    viewer_id: str = "",
    now: int = None,
) -> dict:
    """构建一页拍卖行数据，保持与存储层每页十件一致。"""
    current_time = int(time.time()) if now is None else int(now)
    cards = []
    for listing in listings:
        item_data = listing.get("item_data", {}) or {}
        item_type = item_data.get("type", listing.get("type", ""))
        type_name, icon = TYPE_META.get(item_type, ("物品", "📦"))
        quantity = max(1, int(item_data.get("count", 1)))
        fish = get_fish_by_id(item_data.get("fish_id", "")) if item_type == "fish" else None
        fish_prefix = get_prefix_by_id(item_data.get("prefix_id", "")) if fish else None
        cards.append({
            "id": _safe(listing.get("id", "未知编号")),
            "name": _safe(get_item_name_for_auction(item_data)),
            "type": _safe(item_type or "other"),
            "type_name": _safe(type_name),
            "icon": icon,
            "quantity": _number(quantity) if quantity > 1 else "",
            "price": _number(max(0, int(listing.get("price", 0)))),
            "seller": _safe(listing.get("seller_name", "未知卖家")),
            "remaining": _safe(_remaining_text(int(listing.get("expires_at", 0)) - current_time)),
            "own": bool(viewer_id and listing.get("seller_id") == viewer_id),
            "enhancement": (
                f"+{max(0, int(item_data.get('enchant_count', 0)))}"
                if item_type == "rod" and int(item_data.get("enchant_count", 0)) > 0 else ""
            ),
            "skills": _build_skills(
                item_data.get("base_id", ""), item_data.get("prefix_id", ""),
                item_data.get("skills", {}),
            ) if item_type == "rod" else [],
            "rarity": _safe(fish.get("rarity", "common")) if fish else "",
            "ancient": bool(fish_prefix and fish_prefix.get("id") == "pref_014"),
        })

    total_pages = max(1, math.ceil(max(0, int(total)) / 10))
    return {
        "title": "拍卖行搜索" if keyword else "玩家拍卖行",
        "keyword": _safe(keyword),
        "page": max(1, int(page)),
        "total_pages": total_pages,
        "total": max(0, int(total)),
        "listings": cards,
    }


SHOP_IMAGE_TEMPLATE = r"""
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent}body{width:1200px;padding:24px;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#17212b;background:radial-gradient(circle at 86% 8%,rgba(123,211,255,.32),transparent 31%),linear-gradient(145deg,#d9f3ff 0%,#eefaff 48%,#fff 100%)}
.sheet{overflow:hidden;border:1px solid #a8d9ef;border-radius:20px;background:rgba(255,255,255,.96);box-shadow:0 12px 32px rgba(46,122,158,.16)}.header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:18px 26px 15px;border-bottom:1px solid #c7e7f6;background:linear-gradient(100deg,#caedff 0%,#eaf8ff 55%,#fff 100%)}
.title{font-size:28px;font-weight:900;color:#102a38}.subtitle{margin-top:5px;color:#54798b;font-size:13px}.wallet{text-align:right}.wallet-label{color:#668391;font-size:12px}.wallet-value{margin-top:2px;color:#9a6600;font-size:22px;font-weight:900}.body{padding:16px 22px 20px}.shop-meta{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}.meta{padding:5px 9px;border-radius:8px;background:#edf8fd;color:#285263;font-weight:700;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.card{position:relative;isolation:isolate;overflow:hidden;min-width:0;padding:11px;border:1px solid rgba(133,190,217,.55);border-radius:12px;background:rgba(235,247,253,.68);-webkit-backdrop-filter:blur(12px) saturate(135%);backdrop-filter:blur(12px) saturate(135%);box-shadow:0 5px 15px rgba(41,128,169,.09),inset 0 1px 0 rgba(255,255,255,.78)}.card:before{content:attr(data-icon);position:absolute;right:-7px;bottom:-19px;z-index:0;font-size:82px;line-height:1;opacity:.11;filter:saturate(1.15);transform:rotate(-8deg);pointer-events:none}.card>*{position:relative;z-index:1}.card.type-rod{border-color:rgba(102,178,222,.58);background:linear-gradient(145deg,rgba(220,243,255,.78),rgba(245,251,255,.62))}.card.type-bait{border-color:rgba(221,183,73,.56);background:linear-gradient(145deg,rgba(255,245,199,.8),rgba(255,252,235,.64))}.card.type-ticket,.card.type-directed_enchant{border-color:rgba(224,131,143,.56);background:linear-gradient(145deg,rgba(255,224,229,.8),rgba(255,247,248,.64))}.card.type-item,.card.type-refresh_token{border-color:rgba(169,139,215,.52);background:linear-gradient(145deg,rgba(238,227,255,.78),rgba(251,247,255,.64))}.card.type-fish{border-color:rgba(93,190,177,.52);background:linear-gradient(145deg,rgba(217,249,242,.78),rgba(246,255,252,.64))}.card.unaffordable{filter:saturate(.55);opacity:.7}
.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:9px}.index{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:26px;border-radius:8px;background:rgba(255,255,255,.62);color:#126c9e;font-weight:900;font-size:12px;box-shadow:inset 0 0 0 1px rgba(103,175,208,.2)}.type{padding:3px 7px;border-radius:999px;background:rgba(255,255,255,.58);color:#496b7a;font-size:10px;font-weight:900;box-shadow:inset 0 0 0 1px rgba(112,158,179,.14)}
.name{margin-top:7px;font-size:14px;line-height:1.35;font-weight:900;color:#153746}.quantity{margin-left:4px;color:#607d8b;font-size:12px}.skills{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}.skill{padding:3px 6px;border:1px solid #c6e2ef;border-radius:6px;background:#f7fcfe;color:#24566d;font-size:10px;font-weight:700}.skill b{margin-left:3px;color:#1374b7}
.price-row{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:9px;padding-top:8px;border-top:1px solid #e0eef4}.price{color:#a66d00;font-size:15px;font-weight:900}.state{color:#7f929b;font-size:10px;font-weight:700}.empty{grid-column:1/-1;padding:36px;text-align:center;border:1px dashed #bddce9;border-radius:13px;color:#78909c;background:#f8fcfe}.hint{margin-top:14px;padding:9px 11px;border-radius:10px;background:#edf8fd;color:#496979;text-align:center;font-size:12px}
</style></head><body><article class="sheet"><header class="header"><div><div class="title">🏪 钓鱼商店</div><div class="subtitle">{{ user_name }} 的专属货架</div></div><div class="wallet"><div class="wallet-label">当前金币</div><div class="wallet-value">💰 {{ coins }}</div></div></header><main class="body"><div class="shop-meta"><span class="meta">商店 Lv.{{ shop_level }}</span><span class="meta">展示位 {{ items|length }} / {{ slot_count }}</span><span class="meta">刷新 {{ refresh_status }}</span></div><section class="grid">{% for item in items %}<article class="card type-{{ item.type }}{% if not item.affordable %} unaffordable{% endif %}" data-icon="{{ item.icon }}"><div class="card-head"><span class="index">{{ item.index }}</span><span class="type">{{ item.type_name }}</span></div><div class="name">{{ item.name }}{% if item.quantity %}<span class="quantity">× {{ item.quantity }}</span>{% endif %}</div>{% if item.skills %}<div class="skills">{% for skill in item.skills %}<span class="skill">{{ skill.name }} <b>{{ skill.value }}</b></span>{% endfor %}</div>{% endif %}<div class="price-row"><span class="price">{{ item.price }} 金币</span><span class="state">{% if item.affordable %}可购买{% else %}金币不足{% endif %}</span></div></article>{% else %}<div class="empty">商店正在补货，请稍后刷新</div>{% endfor %}</section><div class="hint">使用 /购买 编号 数量　·　使用 /刷新商店 更换商品</div></main></article></body></html>
"""


AUCTION_IMAGE_TEMPLATE = r"""
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent}body{width:1200px;padding:24px;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#17212b;background:radial-gradient(circle at 86% 8%,rgba(123,211,255,.32),transparent 31%),linear-gradient(145deg,#d9f3ff 0%,#eefaff 48%,#fff 100%)}
.sheet{overflow:hidden;border:1px solid #a8d9ef;border-radius:20px;background:rgba(255,255,255,.96);box-shadow:0 12px 32px rgba(46,122,158,.16)}.header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:18px 26px 15px;border-bottom:1px solid #c7e7f6;background:linear-gradient(100deg,#caedff 0%,#eaf8ff 55%,#fff 100%)}
.title{font-size:28px;font-weight:900;color:#102a38}.subtitle{margin-top:5px;color:#54798b;font-size:13px}.page{text-align:right;color:#176b98;font-size:15px;font-weight:900}.body{padding:16px 22px 20px}.search{display:inline-flex;margin-bottom:12px;padding:5px 9px;border-radius:8px;background:#edf8fd;color:#285263;font-weight:700;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.card{min-width:0;padding:11px;border:1px solid #c9e4f1;border-radius:12px;background:linear-gradient(145deg,#f5fbfe,#fff);box-shadow:0 4px 12px rgba(41,128,169,.07)}.card.own{border:2px solid #55a6df;background:linear-gradient(145deg,#e7f6ff,#fff)}
.card-head{display:flex;align-items:center;justify-content:space-between;gap:9px}.type{padding:3px 7px;border-radius:999px;background:#e8f5fb;color:#2c657d;font-size:10px;font-weight:800}.own-badge{margin-left:5px;color:#1475b8}.enhance{padding:2px 7px;border-radius:999px;background:#1676c2;color:#fff;font-weight:900;font-size:11px}
.name{margin-top:7px;font-size:15px;line-height:1.35;font-weight:900;color:#153746}.quantity{margin-left:4px;color:#607d8b;font-size:12px}.skills{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}.skill{padding:3px 6px;border:1px solid #c6e2ef;border-radius:6px;background:#f7fcfe;color:#24566d;font-size:10px;font-weight:700}.skill b{margin-left:3px;color:#1374b7}
.trade{display:grid;grid-template-columns:1.1fr 1fr 1fr;gap:6px;margin-top:9px;padding-top:8px;border-top:1px solid #e0eef4}.label{display:block;color:#78909c;font-size:10px}.value{display:block;margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#314f5d;font-size:11px;font-weight:800}.price{color:#a66d00;font-size:14px}
.listing-id{margin-top:8px;padding:5px 7px;border-radius:6px;background:#f0f7fa;color:#526f7d;font-family:Consolas,monospace;font-size:10px;word-break:break-all}.rarity-rare{color:#1478c9}.rarity-legendary{color:#d52f45}.rarity-mythic{color:#8438b5}.ancient{color:#a76d00}.empty{grid-column:1/-1;padding:40px;text-align:center;border:1px dashed #bddce9;border-radius:13px;color:#78909c;background:#f8fcfe}.hint{margin-top:14px;padding:9px 11px;border-radius:10px;background:#edf8fd;color:#496979;text-align:center;font-size:12px}
</style></head><body><article class="sheet"><header class="header"><div><div class="title">🏷️ {{ title }}</div><div class="subtitle">共 {{ total }} 件在售物品{% if keyword %} · 搜索“{{ keyword }}”{% endif %}</div></div><div class="page">第 {{ page }} / {{ total_pages }} 页</div></header><main class="body">{% if keyword %}<div class="search">🔍 当前关键词：{{ keyword }}</div>{% endif %}<section class="grid">{% for item in listings %}<article class="card{% if item.own %} own{% endif %}"><div class="card-head"><span class="type">{{ item.icon }} {{ item.type_name }}{% if item.own %}<span class="own-badge">我的上架</span>{% endif %}</span>{% if item.enhancement %}<span class="enhance">{{ item.enhancement }}</span>{% endif %}</div><div class="name rarity-{{ item.rarity }}{% if item.ancient %} ancient{% endif %}">{{ item.name }}{% if item.quantity %}<span class="quantity">× {{ item.quantity }}</span>{% endif %}</div>{% if item.skills %}<div class="skills">{% for skill in item.skills %}<span class="skill">{{ skill.name }} <b>{{ skill.value }}</b></span>{% endfor %}</div>{% endif %}<div class="trade"><div><span class="label">售价</span><span class="value price">{{ item.price }} 金币</span></div><div><span class="label">卖家</span><span class="value">{{ item.seller }}</span></div><div><span class="label">剩余时间</span><span class="value">{{ item.remaining }}</span></div></div><div class="listing-id">编号 {{ item.id }}</div></article>{% else %}<div class="empty">暂时没有符合条件的在售物品</div>{% endfor %}</section><div class="hint">使用 /拍卖 购买 上架编号　·　使用 /拍卖 搜索 关键词</div></main></article></body></html>
"""
