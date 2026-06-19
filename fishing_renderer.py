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
        is_cooldown = not is_failure and "冷却" in first_line
        cooldown_text = first_line
        if is_cooldown:
            cooldown_text = re.sub(r"^钓鱼冷却中\s*[，,:：]?\s*", "", first_line).strip()
        view = {
            "kind": "failure" if is_failure else "warning",
            "title": "垂钓失败" if is_failure else ("钓鱼冷却中" if is_cooldown else "暂时无法垂钓"),
            "subtitle": _safe(cooldown_text or first_line), "events": [], "fishes": [], "hidden_fishes": 0,
            "notices": [], "stats": [],
            "raw_lines": [_safe(line.strip()) for line in lines[1:] if line.strip()],
        }
    view["user_name"] = _safe(sender_name or "垂钓者")
    return view


FISHING_IMAGE_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; background: transparent; }
    body {
      padding: 28px;
      font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      color: #17212b;
      background: radial-gradient(circle at 86% 8%, rgba(123,211,255,.32), transparent 31%),
                  linear-gradient(145deg, #d9f3ff 0%, #eefaff 48%, #fff 100%);
    }
    body.success { width: 1320px; }
    body.greedy, body.cashout { width: 960px; }
    body.failure, body.warning { width: 760px; }
    .sheet { overflow: hidden; border: 1px solid #a8d9ef; border-radius: 20px;
      background: rgba(255,255,255,.96); box-shadow: 0 12px 32px rgba(46,122,158,.16); }
    body.greedy .sheet, body.cashout .sheet { border-color: #d0bbf7; box-shadow: 0 12px 32px rgba(91,45,181,.14); }
    body.failure .sheet { border-color: #eeb8c1; box-shadow: 0 12px 32px rgba(155,30,52,.14); }
    body.warning .sheet { border-color: #f0d9a8; box-shadow: 0 12px 32px rgba(168,115,0,.12); }
    .header { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px;
      padding: 24px 32px 20px; border-bottom: 1px solid #c7e7f6;
      background: linear-gradient(100deg, #caedff 0%, #eaf8ff 55%, #fff 100%); }
    body.greedy .header, body.cashout .header { border-bottom-color: #dcc9ff; background: linear-gradient(100deg, #e6d8ff 0%, #f3edff 55%, #fff 100%); }
    body.failure .header { border-bottom-color: #f3c1c9; background: linear-gradient(100deg, #ffd4db 0%, #ffeff1 55%, #fff 100%); }
    body.warning .header { border-bottom-color: #f5deb3; background: linear-gradient(100deg, #ffecc2 0%, #fff8e8 55%, #fff 100%); }
    body.warning .header { align-items: flex-start; padding: 28px 32px 30px; border-bottom: 0; }
    .title { font-size: 40px; line-height: 1.15; font-weight: 900; color: #102a38;
      letter-spacing: .5px; text-shadow: 0 2px 0 rgba(255,255,255,.9); }
    body.greedy .title, body.cashout .title { color: #5b2db5; }
    body.failure .title { color: #9b1e34; }
    body.warning .title { color: #7a5200; }
    .subtitle { margin-top: 7px; color: #54798b; font-size: 18px; font-weight: 700; }
    body.greedy .subtitle, body.cashout .subtitle { color: #7c5ab8; }
    body.failure .subtitle { color: #b05a6a; }
    body.warning .subtitle { margin-top: 13px; color: #9c7a3c; font-size: 40px; line-height: 1.15; font-weight: 900; }
    .user { color: #176b98; font-weight: 900; font-size: 20px; }
    body.greedy .user, body.cashout .user { color: #6b4fc0; }
    body.failure .user { color: #9b4052; }
    body.warning .user { color: #9a7b3c; }
    .body { padding: 22px 28px 28px; }
    .event-list { display: flex; flex-wrap: wrap; gap: 9px; margin-bottom: 16px; }
    .event { padding: 7px 13px; border-radius: 999px; background: #e7f6ff;
      color: #176a98; font-size: 16px; font-weight: 900; }
    .stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .stat { padding: 14px 16px; min-height: 82px; border: 1px solid #c7e2ee;
      border-radius: 14px; background: linear-gradient(145deg, #fff, #f2faff); }
    .stat-label { color: #617d8b; font-size: 15px; font-weight: 700; }
    .stat-value { margin-top: 4px; color: #153746; font-size: 27px; line-height: 1.1; font-weight: 900; }
    .fish-title { margin: 22px 0 11px; font-size: 24px; font-weight: 900; color: #153746; }
    .fish-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .fish-grid.dense { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .fish { min-width: 0; min-height: 76px; padding: 13px 16px; border: 1px solid #cce4ef;
      border-radius: 13px; background: linear-gradient(145deg, #fff, #f7fcff); }
    .fish-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      font-size: 18px; line-height: 1.25; font-weight: 900; }
    .fish-meta { display: flex; justify-content: space-between; gap: 10px; margin-top: 7px;
      color: #617c8a; font-size: 15px; font-weight: 700; }
    .fish-grid.featured .fish { min-height: 90px; padding: 16px 19px; }
    .fish-grid.featured .fish-name { font-size: 22px; }
    .fish-grid.featured .fish-meta { font-size: 17px; }
    .rarity-common { color: #26343b; }
    .rarity-rare { color: #1478c9; }
    .rarity-legendary { color: #d52f45; }
    .rarity-mythic { color: #8438b5; }
    .ancient { color: #a76d00; }
    .notice-list { display: flex; flex-direction: column; gap: 9px; margin-top: 16px; }
    .notice, .action, .more { padding: 11px 14px; border-radius: 11px; background: #edf8fd;
      color: #496979; font-size: 16px; font-weight: 800; }
    .action { padding: 15px 18px; background: #f0e9ff; color: #5b2db5;
      font-size: 19px; text-align: center; font-weight: 900; }
    body.greedy .stats, body.cashout .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    body.greedy .stat, body.cashout .stat { min-height: 94px; border-color: #dfd1f7;
      background: linear-gradient(145deg, #fff, #f7f2ff); }
    body.greedy .stat-value, body.cashout .stat-value { color: #5b2db5; font-size: 31px; }
    body.greedy .notice-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    body.greedy .fish-grid { grid-template-columns: 1fr; }
    .status-box { padding: 28px; text-align: center; color: #5d8193; font-size: 16px; }
  </style>
</head>
<body class="{{ kind }}">
  <article class="sheet">
    <header class="header">
      <div>
        <div class="title">{% if kind == 'success' %}🎣{% elif kind in ('greedy','cashout') %}🧿{% elif kind == 'failure' %}💥{% else %}⏳{% endif %} {{ title }}</div>
        <div class="subtitle">{{ subtitle }}</div>
      </div>
      {% if kind != 'warning' %}<div class="user">{{ user_name }}</div>{% endif %}
    </header>
    {% if kind != 'warning' %}
    <main class="body">
      {% if events %}<div class="event-list">{% for event in events %}<span class="event">{{ event }}</span>{% endfor %}</div>{% endif %}
      {% if stats %}<section class="stats">{% for stat in stats %}<article class="stat"><div class="stat-label">{{ stat.label }}</div><div class="stat-value">{{ stat.value }}</div></article>{% endfor %}</section>{% endif %}
      {% if fishes %}<div class="fish-title">🐠 本次渔获</div><section class="fish-grid{% if fishes|length <= 4 %} featured{% elif fishes|length >= 9 %} dense{% endif %}">{% for fish in fishes %}<article class="fish"><div class="fish-name rarity-{{ fish.rarity }}{% if fish.ancient %} ancient{% endif %}">{{ fish.name }}</div><div class="fish-meta"><span>× {{ fish.count }}</span><span>{% if fish.price %}{{ fish.price }} 金币{% endif %}</span></div></article>{% endfor %}</section>{% if hidden_fishes %}<div class="more">还有 {{ hidden_fishes }} 条稀有渔获未展示</div>{% endif %}{% endif %}
      {% if notices %}<section class="notice-list">{% for notice in notices %}<div class="notice">{{ notice }}</div>{% endfor %}</section>{% endif %}
      {% if raw_lines %}<section class="notice-list">{% for line in raw_lines %}<div class="{% if kind == 'greedy' %}action{% else %}notice{% endif %}">{{ line }}</div>{% endfor %}</section>{% endif %}
      {% if not stats and not fishes and not raw_lines %}<div class="status-box">{{ subtitle }}</div>{% endif %}
    </main>
    {% endif %}
  </article>
</body>
</html>
"""
