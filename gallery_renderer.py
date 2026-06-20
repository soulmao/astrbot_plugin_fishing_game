"""鱼饵、图鉴与成就页面的结构化图片视图。"""

import html
from datetime import datetime

from .fish_data import (
    ACHIEVEMENTS,
    BAIT_PREFIXES,
    FISH_PREFIXES,
    FISH_TYPES,
    get_bait_by_id,
    get_bait_prefix,
    get_fish_by_id,
    get_prefix_by_id,
    calc_fish_value,
    RESEARCH_CONFIG,
)


RARITY_META = {
    "mythic": ("神话", "🌟"),
    "legendary": ("传说", "⭐"),
    "rare": ("稀有", "🔷"),
    "common": ("常见", "🔹"),
}
CATEGORY_META = {
    "fish_count": ("垂钓生涯", "🎣"),
    "rare_count": ("稀有收藏", "🔷"),
    "legendary_count": ("传说猎手", "⭐"),
    "mythic_count": ("神话追寻", "🌟"),
    "coins": ("财富积累", "💰"),
    "level": ("等级成长", "🏷️"),
    "collection": ("图鉴收集", "📖"),
    "enchant_count": ("附魔之路", "✨"),
    "checkin_days": ("连续签到", "🔥"),
}
CATEGORY_ORDER = list(CATEGORY_META)


def _safe(value) -> str:
    """转义所有可能进入 HTML 的动态文本。"""
    return html.escape(str(value), quote=True)


def _number(value) -> str:
    return f"{int(value):,}"


def _date_text(timestamp: int) -> str:
    """兼容损坏或超出平台范围的旧时间戳。"""
    if timestamp <= 0:
        return "时间未知"
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return "时间未知"


def _achievement_progress(user, achievement: dict) -> tuple:
    category = achievement.get("category")
    target = max(0, int(achievement.get("target", 0)))
    rarity_counts = user.rarity_catch_count
    values = {
        "fish_count": user.total_fish_count,
        "rare_count": rarity_counts.get("rare", 0),
        "legendary_count": rarity_counts.get("legendary", 0),
        "mythic_count": rarity_counts.get("mythic", 0),
        "coins": user.coins,
        "level": user.level,
        "collection": user.get_collection_count(),
        "enchant_count": user.get_total_enchant_count(),
        "checkin_days": user.consecutive_checkin_days,
    }
    return max(0, int(values.get(category, 0))), target


def _achievement_description(achievement: dict) -> str:
    if achievement.get("desc"):
        return achievement["desc"]
    target = _number(achievement.get("target", 0))
    descriptions = {
        "fish_count": f"累计完成 {target} 次钓鱼",
        "rare_count": f"累计捕获 {target} 次稀有渔获",
        "legendary_count": f"累计捕获 {target} 次传说渔获",
        "mythic_count": f"累计捕获 {target} 次神话渔获",
        "coins": f"持有金币达到 {target}",
        "level": f"玩家等级达到 Lv.{target}",
        "collection": f"点亮 {target} 个图鉴条目",
        "enchant_count": f"累计完成 {target} 次附魔",
        "checkin_days": f"连续签到达到 {target} 天",
    }
    return descriptions.get(achievement.get("category"), achievement.get("name", "成就目标"))


def build_baits_view(user, sender_name: str) -> dict:
    """构建“我的鱼饵”完整卡片列表。"""
    current = user.current_bait
    items = []
    for index, bait in enumerate(user.get_baits(), 1):
        base = get_bait_by_id(bait.get("base_id", ""))
        prefix = get_bait_prefix(bait.get("prefix_id", ""))
        if not base or not prefix:
            continue
        is_current = (
            bait.get("base_id") == current.get("base_id")
            and bait.get("prefix_id") == current.get("prefix_id")
        )
        exp_multiplier = float(base.get("exp_multiplier", 1)) * float(prefix.get("multiplier", 1))
        quality_bonus = float(base.get("quality_bonus", 0)) * float(prefix.get("multiplier", 1))
        effects = [
            {"name": "经验", "value": f"×{exp_multiplier:.2f}"},
            {"name": "稀有加成", "value": f"+{int(round(quality_bonus * 100))}%"},
        ]
        event_bonus = float(prefix.get("event_bonus", 0))
        if event_bonus > 0:
            effects.append({"name": "奇遇", "value": f"+{int(round(event_bonus * 100))}%"})
        items.append({
            "index": index,
            "name": _safe(f"{prefix['name']}{base['name']}"),
            "count": _number(max(0, int(bait.get("count", 0)))),
            "quality": _safe(base.get("quality", "common")),
            "current": is_current,
            "effects": effects,
        })
    items.sort(key=lambda item: not item["current"])
    return {
        "user_name": _safe(sender_name or "垂钓者"),
        "total_types": len(items),
        "total_count": _number(sum(max(0, int(bait.get("count", 0))) for bait in user.get_baits())),
        "items": items,
    }


def build_collection_view(user, sender_name: str, recent_limit: int = 12) -> dict:
    """构建图鉴总览和最近点亮条目。"""
    collection = user.get_collection()
    total_collectible = len(FISH_TYPES) * len(FISH_PREFIXES)
    collected_count = len(collection)
    overall_percent = collected_count / total_collectible * 100 if total_collectible else 0

    totals = {rarity: 0 for rarity in RARITY_META}
    counts = {rarity: 0 for rarity in RARITY_META}
    for fish in FISH_TYPES:
        totals.setdefault(fish.get("rarity", "common"), 0)
        totals[fish.get("rarity", "common")] += len(FISH_PREFIXES)

    valid_entries = []
    for key, info in collection.items():
        parts = key.split("#", 1)
        if len(parts) != 2:
            continue
        fish = get_fish_by_id(parts[0])
        prefix = get_prefix_by_id(parts[1])
        if not fish or not prefix:
            continue
        rarity = fish.get("rarity", "common")
        counts[rarity] = counts.get(rarity, 0) + 1
        first_at = max(0, int(info.get("first_at", 0)))
        valid_entries.append({
            "name": _safe(f"{prefix['name']}{fish['name']}"),
            "rarity": _safe(rarity),
            "ancient": prefix.get("id") == "pref_014",
            "count": _number(max(1, int(info.get("count", 1)))),
            "first_at": first_at,
            "date": _date_text(first_at),
        })

    rarity_stats = []
    for rarity in ("mythic", "legendary", "rare", "common"):
        count = counts.get(rarity, 0)
        total = totals.get(rarity, 0)
        name, icon = RARITY_META[rarity]
        rarity_stats.append({
            "rarity": rarity,
            "name": name,
            "icon": icon,
            "count": count,
            "total": total,
            "percent": round(count / total * 100, 2) if total else 0,
        })

    valid_entries.sort(key=lambda item: item["first_at"], reverse=True)
    for item in valid_entries:
        item.pop("first_at", None)

    collected_fish = {key.split("#", 1)[0] for key in collection if "#" in key}
    rod_id = user.current_rod.get("base_id", "")
    available_prefixes = []
    for prefix in FISH_PREFIXES:
        if user.level < int(prefix.get("min_level", 1)):
            continue
        if prefix.get("requires_gold_rod") and rod_id not in ("rod_004", "rod_005"):
            continue
        if prefix.get("requires_divine_rod") and rod_id != "rod_005":
            continue
        if prefix.get("id") == "pref_015" and user.current_rod.get("prefix_id") != "rod_pref_13":
            continue
        available_prefixes.append(prefix)
    researchable = []
    min_levels = {"common": 1, "rare": 2, "legendary": 5, "mythic": 6}
    spendable = user.get_spendable_exp()
    for fish in FISH_TYPES:
        rarity = fish.get("rarity", "common")
        cost = RESEARCH_CONFIG["fish"][rarity]["cost"]
        if fish["id"] in collected_fish or user.level < min_levels.get(rarity, 1) or cost > spendable:
            continue
        if rarity == "mythic" and rod_id not in ("rod_004", "rod_005"):
            continue
        best_value = max(
            (calc_fish_value(fish["id"], prefix["id"], 1) for prefix in available_prefixes),
            default=int(fish.get("base_price", 0)),
        )
        researchable.append({
            "name": _safe(fish["name"]), "rarity": rarity,
            "value": _number(best_value), "cost": _number(cost),
        })
    researchable.sort(key=lambda item: int(item["value"].replace(",", "")), reverse=True)
    return {
        "user_name": _safe(sender_name or "垂钓者"),
        "collected": collected_count,
        "total": total_collectible,
        "percent": round(overall_percent, 2),
        "rarities": rarity_stats,
        "recent": valid_entries[:max(0, int(recent_limit))],
        "researchable": researchable[:5],
    }


def build_achievements_view(user, sender_name: str) -> dict:
    """构建按目标类别分组的完整成就页面。"""
    completed = set(user.achievements)
    groups = []
    for category in CATEGORY_ORDER:
        name, icon = CATEGORY_META[category]
        items = []
        for achievement in ACHIEVEMENTS:
            if achievement.get("category") != category:
                continue
            current, target = _achievement_progress(user, achievement)
            done = achievement.get("id") in completed
            percent = 100.0 if done else min(100.0, current / target * 100) if target else 0.0
            items.append({
                "name": _safe(achievement.get("name", "未命名成就")),
                "description": _safe(_achievement_description(achievement)),
                "done": done,
                "current": _number(min(current, target) if target else current),
                "target": _number(target),
                "percent": round(percent, 2),
                "reward_coins": _number(achievement.get("reward_coins", 0)),
                "reward_exp": _number(achievement.get("reward_exp", 0)),
            })
        if items:
            groups.append({
                "name": name,
                "icon": icon,
                "completed": sum(1 for item in items if item["done"]),
                "total": len(items),
                "items": items,
            })

    completed_count = sum(1 for achievement in ACHIEVEMENTS if achievement["id"] in completed)
    total = len(ACHIEVEMENTS)
    return {
        "user_name": _safe(sender_name or "垂钓者"),
        "completed": completed_count,
        "total": total,
        "percent": round(completed_count / total * 100, 2) if total else 0,
        "groups": groups,
    }


BAITS_IMAGE_TEMPLATE = r"""
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent}body{width:1200px;padding:24px;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#17212b;background:radial-gradient(circle at 86% 8%,rgba(123,211,255,.32),transparent 31%),linear-gradient(145deg,#d9f3ff 0%,#eefaff 48%,#fff 100%)}
.sheet{overflow:hidden;border:1px solid #a8d9ef;border-radius:20px;background:rgba(255,255,255,.96);box-shadow:0 12px 32px rgba(46,122,158,.16)}
.header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:18px 26px 15px;border-bottom:1px solid #c7e7f6;background:linear-gradient(100deg,#caedff 0%,#eaf8ff 55%,#fff 100%)}
.title{font-size:28px;font-weight:900;color:#102a38}.subtitle{margin-top:5px;color:#54798b;font-size:13px}.summary{text-align:right;color:#176b98;font-size:15px;font-weight:900}
.body{padding:16px 22px 20px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.card{min-width:0;padding:11px;border:1px solid #c9e4f1;border-radius:12px;background:linear-gradient(145deg,#f5fbfe,#fff);box-shadow:0 4px 12px rgba(41,128,169,.07)}
.card.current{border:2px solid #258be3;background:linear-gradient(145deg,#e2f5ff,#fff);box-shadow:0 0 0 3px rgba(37,139,227,.10)}
.head{display:flex;align-items:center;justify-content:space-between;gap:9px}.index{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:26px;border-radius:8px;background:#dff2fc;color:#126c9e;font-weight:900;font-size:12px}
.badges{display:flex;gap:5px}.count{padding:2px 7px;border-radius:999px;background:#eef7fb;color:#436878;font-size:11px;font-weight:800}.current-badge{padding:2px 7px;border-radius:999px;background:#258be3;color:#fff;font-size:11px;font-weight:800}
.name{margin-top:7px;font-size:15px;font-weight:900;color:#153746}.effects{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}.effect{padding:4px 7px;border:1px solid #c6e2ef;border-radius:7px;background:#f8fcfe;color:#456674;font-size:11px;font-weight:700}
.effect b{margin-left:3px;color:#1374b7}.empty{grid-column:1/-1;padding:36px;text-align:center;border:1px dashed #bddce9;border-radius:13px;color:#78909c;background:#f8fcfe}
.hint{margin-top:14px;padding:9px 11px;border-radius:10px;background:#edf8fd;color:#496979;text-align:center;font-size:12px}
</style></head><body><article class="sheet"><header class="header"><div><div class="title">🪤 我的鱼饵</div><div class="subtitle">{{ user_name }} 的鱼饵收藏</div></div><div class="summary">{{ total_types }} 种 · 共 {{ total_count }} 份</div></header><main class="body"><section class="grid">{% for bait in items %}<article class="card{% if bait.current %} current{% endif %}"><div class="head"><span class="index">{{ bait.index }}</span><span class="badges"><span class="count">× {{ bait.count }}</span>{% if bait.current %}<span class="current-badge">当前装备</span>{% endif %}</span></div><div class="name">{{ bait.name }}</div><div class="effects">{% for effect in bait.effects %}<span class="effect">{{ effect.name }} <b>{{ effect.value }}</b></span>{% endfor %}</div></article>{% else %}<div class="empty">还没有鱼饵，可前往商店购买</div>{% endfor %}</section><div class="hint">使用 /装备鱼饵 编号 切换当前鱼饵</div></main></article></body></html>
"""


COLLECTION_IMAGE_TEMPLATE = r"""
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent}body{width:1200px;padding:24px;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#17212b;background:radial-gradient(circle at 86% 8%,rgba(123,211,255,.32),transparent 31%),linear-gradient(145deg,#d9f3ff 0%,#eefaff 48%,#fff 100%)}
.sheet{overflow:hidden;border:1px solid #a8d9ef;border-radius:20px;background:rgba(255,255,255,.96);box-shadow:0 12px 32px rgba(46,122,158,.16)}
.header{padding:18px 26px 15px;border-bottom:1px solid #c7e7f6;background:linear-gradient(100deg,#caedff 0%,#eaf8ff 55%,#fff 100%)}
.title{font-size:28px;font-weight:900;color:#102a38}.subtitle{margin-top:5px;color:#54798b;font-size:13px}.body{padding:16px 22px 20px}
.overall{padding:11px 13px;border:1px solid #c8e6f4;border-radius:12px;background:#f4fbff}.overall-head{display:flex;justify-content:space-between;gap:20px;margin-bottom:7px}.overall-value{color:#12658b;font-size:15px;font-weight:900}.overall-pct{color:#527487;font-weight:800}
.progress{height:10px;overflow:hidden;border-radius:999px;background:#dceef7}.fill{height:100%;min-width:4px;border-radius:inherit;background:linear-gradient(90deg,#4bb7e8,#2387df)}
.rarities{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:12px}.rarity{padding:10px;border:1px solid #d2e8f2;border-radius:11px;background:#fbfdfe}.rarity-name{font-weight:900}.rarity-count{margin-top:4px;font-size:17px;font-weight:900}.rarity-pct{margin-top:1px;color:#718995;font-size:11px}
.common{color:#26343b}.rare{color:#1478c9}.legendary{color:#d52f45}.mythic{color:#8438b5}.ancient{color:#a76d00}
.section-title{margin:16px 0 8px;font-size:16px;font-weight:900;color:#153746}.recent{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}.item{min-width:0;padding:9px 11px;border:1px solid #d5e8f1;border-radius:10px;background:#fbfdfe}
.research-list{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px}.research-item{padding:9px 11px;border:1px solid #bddff0;border-radius:10px;background:linear-gradient(145deg,#eef9ff,#fff)}.research-meta{display:flex;justify-content:space-between;gap:6px;margin-top:4px;color:#63808e;font-size:10px}
.fish-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:900}.fish-meta{display:flex;justify-content:space-between;gap:8px;margin-top:3px;color:#718894;font-size:11px}
.empty{grid-column:1/-1;padding:36px;text-align:center;border:1px dashed #bddce9;border-radius:13px;color:#78909c;background:#f8fcfe}
</style></head><body><article class="sheet"><header class="header"><div class="title">📖 钓鱼图鉴</div><div class="subtitle">{{ user_name }} 的收藏记录</div></header><main class="body"><section class="overall"><div class="overall-head"><span class="overall-value">已点亮 {{ collected }} / {{ total }}</span><span class="overall-pct">{{ percent }}%</span></div><div class="progress"><div class="fill" style="width:{{ percent }}%"></div></div></section><section class="rarities">{% for rarity in rarities %}<article class="rarity"><div class="rarity-name {{ rarity.rarity }}">{{ rarity.icon }} {{ rarity.name }}</div><div class="rarity-count {{ rarity.rarity }}">{{ rarity.count }} / {{ rarity.total }}</div><div class="rarity-pct">完成 {{ rarity.percent }}%</div></article>{% endfor %}</section><div class="section-title">🔬 当前可研究鱼种 · 按最高价值排序</div><section class="research-list">{% for fish in researchable %}<article class="research-item"><div class="fish-name {{ fish.rarity }}">{{ fish.name }}</div><div class="research-meta"><span>最高 {{ fish.value }} 金币</span><span>需 {{ fish.cost }} 经验</span></div></article>{% else %}<div class="empty">当前经验、等级和装备范围内暂无未点亮鱼种</div>{% endfor %}</section><div class="section-title">📜 最近点亮</div><section class="recent">{% for fish in recent %}<article class="item"><div class="fish-name {{ fish.rarity }}{% if fish.ancient %} ancient{% endif %}">{{ fish.name }}</div><div class="fish-meta"><span>累计捕获 × {{ fish.count }}</span><span>{{ fish.date }}</span></div></article>{% else %}<div class="empty">首次钓到渔获后，收藏记录会在这里亮起</div>{% endfor %}</section></main></article></body></html>
"""


ACHIEVEMENTS_IMAGE_TEMPLATE = r"""
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent}body{width:1560px;padding:24px;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#17212b;background:radial-gradient(circle at 86% 8%,rgba(123,211,255,.32),transparent 31%),linear-gradient(145deg,#d9f3ff 0%,#eefaff 48%,#fff 100%)}
.sheet{overflow:hidden;border:1px solid #a8d9ef;border-radius:20px;background:rgba(255,255,255,.96);box-shadow:0 12px 32px rgba(46,122,158,.16)}
.header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:18px 26px 15px;border-bottom:1px solid #c7e7f6;background:linear-gradient(100deg,#caedff 0%,#eaf8ff 55%,#fff 100%)}
.title{font-size:28px;font-weight:900;color:#102a38}.subtitle{margin-top:5px;color:#54798b;font-size:13px}.summary{text-align:right}.summary strong{display:block;color:#176b98;font-size:20px}.summary span{color:#607d8b;font-size:12px}
.body{padding:16px 22px 20px}.overall{height:10px;overflow:hidden;border-radius:999px;background:#dceef7}.overall-fill{height:100%;min-width:4px;border-radius:inherit;background:linear-gradient(90deg,#4bb7e8,#2387df)}
.group{margin-top:16px}.group-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:7px}.group-title{font-size:16px;font-weight:900;color:#153746}.group-count{color:#698591;font-size:11px;font-weight:800}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}.card{min-width:0;padding:10px 11px;border:1px solid #d5e8f1;border-radius:11px;background:#fbfdfe}.card.done{border-color:#b8dfcf;background:linear-gradient(145deg,#effbf6,#fff)}
.card-head{display:flex;align-items:center;justify-content:space-between;gap:7px}.name{font-size:14px;font-weight:900;color:#183b4b}.done .name{color:#14734e}.status{font-size:11px;font-weight:900;color:#78909c}.done .status{color:#18875c}
.desc{height:28px;margin-top:4px;color:#647f8c;font-size:10px;line-height:1.4;overflow:hidden}
.progress-row{display:flex;align-items:center;gap:6px;margin-top:6px}.mini{flex:1;height:6px;overflow:hidden;border-radius:999px;background:#dceef7}.mini-fill{height:100%;min-width:3px;border-radius:inherit;background:linear-gradient(90deg,#4bb7e8,#2387df)}.numbers{flex:0 0 auto;color:#607d8b;font-size:10px;font-weight:800}
.reward{margin-top:6px;color:#966300;font-size:10px;font-weight:800}
</style></head><body><article class="sheet"><header class="header"><div><div class="title">🏅 成就系统</div><div class="subtitle">{{ user_name }} 的荣誉陈列</div></div><div class="summary"><strong>{{ completed }} / {{ total }}</strong><span>总完成度 {{ percent }}%</span></div></header><main class="body"><div class="overall"><div class="overall-fill" style="width:{{ percent }}%"></div></div>{% for group in groups %}<section class="group"><div class="group-head"><div class="group-title">{{ group.icon }} {{ group.name }}</div><div class="group-count">{{ group.completed }} / {{ group.total }} 已完成</div></div><div class="grid">{% for achievement in group['items'] %}<article class="card{% if achievement.done %} done{% endif %}"><div class="card-head"><span class="name">{{ achievement.name }}</span><span class="status">{% if achievement.done %}已解锁{% else %}进行中{% endif %}</span></div><div class="desc">{{ achievement.description }}</div><div class="progress-row"><div class="mini"><div class="mini-fill" style="width:{{ achievement.percent }}%"></div></div><span class="numbers">{{ achievement.current }} / {{ achievement.target }}</span></div><div class="reward">奖励 💰{{ achievement.reward_coins }}　📈{{ achievement.reward_exp }}</div></article>{% endfor %}</div></section>{% endfor %}</main></article></body></html>
"""
