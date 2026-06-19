"""钓鱼与贪婪结算结果的结构化图片视图。"""

import html
import re

from .fish_data import FISH_PREFIXES, FISH_TYPES


FISH_NAME_META = {
    f"{prefix['name']}{fish['name']}": {
        "rarity": fish.get("rarity", "common"),
        "ancient": prefix.get("id") == "pref_014",
    }
    for fish in FISH_TYPES
    for prefix in FISH_PREFIXES
}
PIG_NOISES = ("呼噜", "哼哼", "哼", "🐷", "🐽")


def _safe(value) -> str:
    return html.escape(str(value), quote=True)


def _number(value) -> str:
    try:
        return f"{int(str(value).replace(',', '')):,}"
    except (TypeError, ValueError):
        return _safe(value)


def _clean_pig_noise(text: str) -> str:
    """移除胡萝卜钓竿插入的随机猪叫，恢复可解析的结果文本。"""
    cleaned = text or ""
    for noise in PIG_NOISES:
        cleaned = cleaned.replace(noise, "")
    return cleaned


def _find_fish_name(text: str):
    """从一行文本中匹配最长的完整鱼名。"""
    matches = [name for name in FISH_NAME_META if name in text]
    if not matches:
        return None
    name = max(matches, key=len)
    return name, FISH_NAME_META[name]


def _first_number(pattern: str, text: str, default=""):
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else default


def _build_normal_fishing(lines: list, text: str) -> dict:
    fishes = []
    pending_fish = None
    notices = []
    events = []
    aggregate_value = 0

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        aggregate = re.search(r"常见鱼\s*[x×](\d+)\s*\(合计\s*([\d,]+)\s*金币", stripped)
        if aggregate:
            fishes.append({
                "name": "常见渔获合计",
                "count": _number(aggregate.group(1)),
                "price": _number(aggregate.group(2)),
                "rarity": "common",
                "ancient": False,
                "aggregate": True,
            })
            aggregate_value += int(aggregate.group(2).replace(",", ""))
            continue

        fish_match = _find_fish_name(stripped)
        if fish_match:
            name, meta = fish_match
            price_match = re.search(r"💰\s*([\d,]+)", stripped)
            item = {
                "name": _safe(name), "count": "1", "price": "",
                "rarity": meta["rarity"], "ancient": meta["ancient"], "aggregate": False,
            }
            if price_match:
                item["price"] = _number(price_match.group(1))
                aggregate_value += int(price_match.group(1).replace(",", ""))
            fishes.append(item)
            pending_fish = item
            continue

        price_line = re.search(r"售价[:：]\s*([\d,]+)\s*金币", stripped)
        if price_line and pending_fish and not pending_fish["price"]:
            pending_fish["price"] = _number(price_line.group(1))
            aggregate_value += int(price_line.group(1).replace(",", ""))
            pending_fish = None
            continue

        if index > 0 and lines[index - 1].strip().startswith("🎣 钓鱼成功"):
            events.extend(part.strip() for part in re.findall(r"(?:✨|🌾|🌊|🧭|💢)[^✨🌾🌊🧭💢]+", stripped))
        elif stripped.startswith(("🎫", "🎁", "🎲", "👻", "🎉", "🏅", "📖", "🔧")):
            notices.append(_safe(stripped.replace("[", "").replace("]", "")))

    exp = _first_number(r"📈\s*经验\s*\+([\d,]+)", text)
    cooldown = _first_number(r"⏰\s*冷却\s*([^\n]+)", text)
    total_count = _first_number(r"🐟\s*累计钓鱼\s*([\d,]+)\s*次", text)
    return {
        "kind": "success", "title": "钓鱼成功", "subtitle": "本次垂钓收获",
        "fishes": fishes[:30], "hidden_fishes": max(0, len(fishes) - 30),
        "events": [_safe(item) for item in events], "notices": notices,
        "stats": [
            {"label": "本次价值", "value": f"{_number(aggregate_value)} 金币"},
            {"label": "获得经验", "value": f"+{_number(exp)}" if exp else "—"},
            {"label": "冷却", "value": _safe(cooldown or "—")},
            {"label": "累计钓鱼", "value": f"{_number(total_count)} 次" if total_count else "—"},
        ],
        "raw_lines": [],
    }


def _build_greedy(text: str) -> dict:
    if "收杆成功" in text:
        return {
            "kind": "cashout", "title": "贪婪收杆成功", "subtitle": "贪欲结晶已经兑现",
            "events": [], "fishes": [], "hidden_fishes": 0, "notices": [],
            "stats": [
                {"label": "结算层数", "value": _number(_first_number(r"结算层数[:：]\s*(\d+)", text, "0"))},
                {"label": "获得金币", "value": "+" + _number(_first_number(r"💰\s*\+([\d,]+)", text, "0"))},
                {"label": "获得经验", "value": "+" + _number(_first_number(r"📈\s*\+([\d,]+)", text, "0"))},
                {"label": "冷却", "value": _safe(_first_number(r"⏰\s*冷却\s*([^\n]+)", text, "无"))},
            ],
            "raw_lines": [],
        }

    if re.search(r"第\s*\d+\s*层贪婪成功", text):
        fish_match = _find_fish_name(text)
        fishes = []
        if fish_match:
            name, meta = fish_match
            fishes.append({
                "name": _safe(name), "count": "1",
                "price": _number(_first_number(r"额外钓上:[^\n]*💰([\d,]+)", text)),
                "rarity": meta["rarity"], "ancient": meta["ancient"], "aggregate": False,
            })
        return {
            "kind": "greedy", "title": "贪婪挑战成功", "subtitle": "结晶仍在继续膨胀",
            "events": [], "fishes": fishes, "hidden_fishes": 0, "notices": [],
            "stats": [
                {"label": "当前层数", "value": _number(_first_number(r"第\s*(\d+)\s*层", text, "0"))},
                {"label": "结晶价值", "value": _number(_first_number(r"膨胀至\s*([\d,]+)\s*金币", text, "0")) + " 金币"},
                {"label": "累计经验", "value": _number(_first_number(r"当前累计经验[:：]\s*([\d,]+)", text, "0"))},
                {"label": "下次断线", "value": _number(_first_number(r"下次断线概率[:：]\s*(\d+)%", text, "0")) + "%"},
            ],
            "raw_lines": ["/收杆 立即结算", "/贪婪 继续挑战"],
        }

    return {
        "kind": "greedy", "title": "贪欲结晶形成", "subtitle": "选择收杆，或继续赌一层",
        "events": [], "fishes": [], "hidden_fishes": 0, "notices": [],
        "stats": [
            {"label": "聚合渔获", "value": _number(_first_number(r"将\s*([\d,]+)\s*条渔获", text, "0")) + " 条"},
            {"label": "结晶价值", "value": _number(_first_number(r"结晶基础价值[:：]\s*([\d,]+)", text, "0")) + " 金币"},
            {"label": "结晶经验", "value": _number(_first_number(r"结晶基础经验[:：]\s*([\d,]+)", text, "0"))},
        ],
        "raw_lines": ["/收杆 立即结算", "/贪婪 继续挑战"],
    }


def build_fishing_result_view(command_result: str, sender_name: str) -> dict:
    """把稳定的钓鱼命令结果转换为专用结算页数据。"""
    text = _clean_pig_noise(command_result)
    lines = text.splitlines()
    if "🎣 钓鱼成功" in text and "结晶基础价值" not in text:
        view = _build_normal_fishing(lines, text)
    elif any(marker in text for marker in ("结晶基础价值", "层贪婪成功", "收杆成功")):
        view = _build_greedy(text)
    else:
        first_line = next((line.strip() for line in lines if line.strip()), "本次没有产生结果")
        is_failure = any(marker in text for marker in ("失败", "断线", "没有渔获"))
        view = {
            "kind": "failure" if is_failure else "warning",
            "title": "垂钓失败" if is_failure else "暂时无法垂钓",
            "subtitle": _safe(first_line), "events": [], "fishes": [], "hidden_fishes": 0,
            "notices": [], "stats": [],
            "raw_lines": [_safe(line.strip()) for line in lines[1:] if line.strip()],
        }
    view["user_name"] = _safe(sender_name or "垂钓者")
    return view


FISHING_IMAGE_TEMPLATE = r"""
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent}body{width:1040px;padding:30px;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#17212b;background:radial-gradient(circle at 86% 8%,rgba(123,211,255,.32),transparent 31%),linear-gradient(145deg,#d9f3ff 0%,#eefaff 48%,#fff 100%)}.sheet{overflow:hidden;border:1px solid #a8d9ef;border-radius:24px;background:rgba(255,255,255,.96);box-shadow:0 18px 48px rgba(46,122,158,.18)}.header{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;padding:27px 32px 24px;border-bottom:1px solid #c7e7f6;background:linear-gradient(100deg,#caedff 0%,#eaf8ff 55%,#fff 100%)}.title{font-size:32px;font-weight:900;color:#102a38}.subtitle{margin-top:7px;color:#54798b;font-size:14px}.user{color:#176b98;font-weight:800}.body{padding:25px 32px 32px}.event-list{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}.event{padding:7px 10px;border-radius:999px;background:#e7f6ff;color:#176a98;font-size:13px;font-weight:800}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.stat{padding:13px 14px;border:1px solid #d3e8f2;border-radius:13px;background:#f8fcfe}.stat-label{color:#708894;font-size:12px}.stat-value{margin-top:5px;color:#153746;font-size:18px;font-weight:900}.fish-title{margin:22px 0 10px;font-size:19px;font-weight:900}.fish-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.fish{min-width:0;padding:11px 12px;border:1px solid #d6e9f2;border-radius:11px;background:#fbfdfe}.fish-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px;font-weight:900}.fish-meta{display:flex;justify-content:space-between;gap:8px;margin-top:6px;color:#718894;font-size:12px}.rarity-common{color:#26343b}.rarity-rare{color:#1478c9}.rarity-legendary{color:#d52f45}.rarity-mythic{color:#8438b5}.ancient{color:#a76d00}.more,.notice,.action{margin-top:10px;padding:9px 11px;border-radius:10px;background:#edf8fd;color:#496979;font-size:13px}.notice-list{display:grid;gap:8px;margin-top:18px}.notice{margin:0}.action{background:#f3edff;color:#69439c;font-weight:800}.status-box{padding:22px;border:1px solid #d8e8ef;border-radius:15px;background:#f8fcfe;color:#496979;line-height:1.7}.failure .header{background:linear-gradient(100deg,#ffe8e8,#fff5f5 55%,#fff)}.failure .title{color:#9e3540}.warning .header{background:linear-gradient(100deg,#fff2d7,#fffaf0 55%,#fff)}.greedy .header,.cashout .header{background:linear-gradient(100deg,#e9dcff,#f6f0ff 55%,#fff)}.greedy .title,.cashout .title{color:#57328c}
</style></head><body class="{{ kind }}"><article class="sheet"><header class="header"><div><div class="title">{% if kind == 'success' %}🎣{% elif kind in ('greedy','cashout') %}🧿{% elif kind == 'failure' %}💥{% else %}⏳{% endif %} {{ title }}</div><div class="subtitle">{{ subtitle }}</div></div><div class="user">{{ user_name }}</div></header><main class="body">{% if events %}<div class="event-list">{% for event in events %}<span class="event">{{ event }}</span>{% endfor %}</div>{% endif %}{% if stats %}<section class="stats">{% for stat in stats %}<article class="stat"><div class="stat-label">{{ stat.label }}</div><div class="stat-value">{{ stat.value }}</div></article>{% endfor %}</section>{% endif %}{% if fishes %}<div class="fish-title">🐠 本次渔获</div><section class="fish-grid">{% for fish in fishes %}<article class="fish"><div class="fish-name rarity-{{ fish.rarity }}{% if fish.ancient %} ancient{% endif %}">{{ fish.name }}</div><div class="fish-meta"><span>× {{ fish.count }}</span><span>{% if fish.price %}{{ fish.price }} 金币{% endif %}</span></div></article>{% endfor %}</section>{% if hidden_fishes %}<div class="more">还有 {{ hidden_fishes }} 条稀有渔获未展示</div>{% endif %}{% endif %}{% if notices %}<section class="notice-list">{% for notice in notices %}<div class="notice">{{ notice }}</div>{% endfor %}</section>{% endif %}{% if raw_lines %}<section class="notice-list">{% for line in raw_lines %}<div class="{% if kind == 'greedy' %}action{% else %}notice{% endif %}">{{ line }}</div>{% endfor %}</section>{% endif %}{% if not stats and not fishes and not raw_lines %}<div class="status-box">{{ subtitle }}</div>{% endif %}</main></article></body></html>
"""
