"""钓鱼与贪婪结算结果的结构化图片视图。"""

import html
import re

from .fish_data import (
    FISH_PREFIXES, FISH_TYPES, RESEARCH_WEIGHT_MULTIPLIERS, RESEARCH_PITY_STEP,
)


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


def _build_research_progress(text: str, research_state: dict = None) -> dict:
    """组合命令文本与持久化状态，生成紧凑研究进度条数据。"""
    state = dict(research_state or {})
    completed = re.search(r"研究完成[^“]*“([^”]+)”", text)
    if completed:
        return {
            "active": False, "completed": True, "target": _safe(completed.group(1)),
            "remaining": 0, "total": int(state.get("total", 0) or 0), "percent": 100,
        }

    progress = re.search(r"研究推进[：:]?“([^”]+)”剩余\s*(\d+)\s*次", text)
    if progress:
        state.setdefault("target_name", progress.group(1))
        state["remaining"] = int(progress.group(2))
    if not state:
        return {}

    total = max(1, int(state.get("total", 1)))
    remaining = min(total, max(0, int(state.get("remaining", total))))
    completed_attempts = total - remaining
    rarity = state.get("target_rarity", "common")
    multiplier = RESEARCH_WEIGHT_MULTIPLIERS.get(rarity, 4.0) + completed_attempts * RESEARCH_PITY_STEP
    return {
        "active": True, "completed": False,
        "target": _safe(state.get("target_name", "未知目标")),
        "target_type": (
            "图鉴组合" if state.get("target_type") == "combo"
            else ("鱼名前缀" if state.get("target_type") == "prefix" else "鱼种")
        ),
        "remaining": remaining, "total": total,
        "cost": _number(state.get("cost", 0) or 0),
        "remaining_targets": max(0, int(state.get("remaining_targets", 1))),
        "multiplier": f"{multiplier:g} 倍",
        "percent": round(completed_attempts / total * 100),
    }


def build_research_view(user, command_result: str, sender_name: str) -> dict:
    """构建海洋研究专属紧凑卡片。"""
    text = command_result or ""
    research = _build_research_progress(text, user.get_research())
    cancelled = "已取消" in text
    failed = text.startswith("❌")
    if research.get("active"):
        title = "海洋研究"
        equipment_line = next(
            (line.strip() for line in text.splitlines() if "当前装备" in line), ""
        )
        subtitle = equipment_line or "未命中时研究倍率递增，进度归零时触发保底"
    elif cancelled:
        title, subtitle = "研究已取消", "已消耗经验不会返还"
    elif failed:
        title, subtitle = "暂时无法研究", re.sub(r"^[❌\s]+", "", text.splitlines()[0])
    else:
        title, subtitle = "海洋研究", "当前没有进行中的研究"
    return {
        "kind": "active" if research.get("active") else ("warning" if failed else "idle"),
        "title": title, "subtitle": _safe(subtitle), "user_name": _safe(sender_name or "研究员"),
        "research": research, "available_exp": _number(user.get_spendable_exp()),
        "message": _safe(next((line for line in text.splitlines() if line.strip()), "")),
    }


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


def build_fishing_result_view(command_result: str, sender_name: str,
                              research_state: dict = None) -> dict:
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
    view["research"] = _build_research_progress(text, research_state)
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
      padding: 20px;
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
    .header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px;
      padding: 18px 24px 15px; border-bottom: 1px solid #c7e7f6;
      background: linear-gradient(100deg, #caedff 0%, #eaf8ff 55%, #fff 100%); }
    body.greedy .header, body.cashout .header { border-bottom-color: #dcc9ff; background: linear-gradient(100deg, #e6d8ff 0%, #f3edff 55%, #fff 100%); }
    body.failure .header { border-bottom-color: #f3c1c9; background: linear-gradient(100deg, #ffd4db 0%, #ffeff1 55%, #fff 100%); }
    body.warning .header { border-bottom-color: #f5deb3; background: linear-gradient(100deg, #ffecc2 0%, #fff8e8 55%, #fff 100%); }
    body.warning .header { align-items: flex-start; padding: 22px 26px 24px; border-bottom: 0; }
    .title { font-size: 36px; line-height: 1.15; font-weight: 900; color: #102a38;
      letter-spacing: .5px; text-shadow: 0 2px 0 rgba(255,255,255,.9); }
    body.greedy .title, body.cashout .title { color: #5b2db5; }
    body.failure .title { color: #9b1e34; }
    body.warning .title { color: #7a5200; }
    .subtitle { margin-top: 5px; color: #54798b; font-size: 17px; font-weight: 700; }
    body.greedy .subtitle, body.cashout .subtitle { color: #7c5ab8; }
    body.failure .subtitle { color: #b05a6a; }
    body.warning .subtitle { margin-top: 9px; color: #9c7a3c; font-size: 34px; line-height: 1.15; font-weight: 900; }
    .user { color: #176b98; font-weight: 900; font-size: 20px; }
    body.greedy .user, body.cashout .user { color: #6b4fc0; }
    body.failure .user { color: #9b4052; }
    body.warning .user { color: #9a7b3c; }
    .body { padding: 16px 20px 20px; }
    .event-list { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 10px; }
    .event { padding: 6px 11px; border-radius: 999px; background: #e7f6ff;
      color: #176a98; font-size: 15px; font-weight: 900; }
    .stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
    .stat { padding: 10px 13px; min-height: 68px; border: 1px solid #c7e2ee;
      border-radius: 14px; background: linear-gradient(145deg, #fff, #f2faff); }
    .stat-label { color: #617d8b; font-size: 15px; font-weight: 700; }
    .stat-value { margin-top: 3px; color: #153746; font-size: 25px; line-height: 1.1; font-weight: 900; }
    .fish-title { margin: 15px 0 8px; font-size: 22px; font-weight: 900; color: #153746; }
    .fish-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }
    .fish-grid.dense { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .fish { min-width: 0; min-height: 64px; padding: 10px 13px; border: 1px solid #cce4ef;
      border-radius: 13px; background: linear-gradient(145deg, #fff, #f7fcff); }
    .fish-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      font-size: 18px; line-height: 1.25; font-weight: 900; }
    .fish-meta { display: flex; justify-content: space-between; gap: 10px; margin-top: 4px;
      color: #617c8a; font-size: 15px; font-weight: 700; }
    .fish-grid.featured .fish { min-height: 72px; padding: 12px 15px; }
    .fish-grid.featured .fish-name { font-size: 21px; }
    .fish-grid.featured .fish-meta { font-size: 16px; }
    .rarity-common { color: #26343b; }
    .rarity-rare { color: #1478c9; }
    .rarity-legendary { color: #d52f45; }
    .rarity-mythic { color: #8438b5; }
    .ancient { color: #a76d00; }
    .notice-list { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
    .notice, .action, .more { padding: 8px 11px; border-radius: 9px; background: #edf8fd;
      color: #496979; font-size: 15px; font-weight: 800; }
    .action { padding: 10px 13px; background: #f0e9ff; color: #5b2db5;
      font-size: 17px; text-align: center; font-weight: 900; }
    body.greedy .stats, body.cashout .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    body.greedy .stat, body.cashout .stat { min-height: 74px; border-color: #dfd1f7;
      background: linear-gradient(145deg, #fff, #f7f2ff); }
    body.greedy .stat-value, body.cashout .stat-value { color: #5b2db5; font-size: 27px; }
    body.greedy .notice-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    body.greedy .fish-grid { grid-template-columns: 1fr; }
    .research { margin-bottom: 10px; padding: 9px 12px; border: 1px solid #b8dff2;
      border-radius: 11px; background: linear-gradient(100deg, #edf9ff, #f8fcff); }
    .research-head { display: flex; align-items: center; justify-content: space-between; gap: 14px;
      color: #185d82; font-size: 15px; font-weight: 900; }
    .research-track { height: 8px; margin-top: 7px; overflow: hidden; border-radius: 999px; background: #dceef7; }
    .research-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, #39aee8, #6878f4); }
    .research.completed { border-color: #b8dfc3; background: #f1fbf3; }
    .research.completed .research-head { color: #287640; }
    .research.completed .research-fill { background: linear-gradient(90deg, #4cc677, #2ea85d); }
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
    {% if kind != 'warning' or research %}
    <main class="body">
      {% if research %}<section class="research{% if research.completed %} completed{% endif %}"><div class="research-head"><span>🔬 {% if research.completed %}研究完成{% else %}{{ research.target_type }}研究 · {{ research.target }}{% endif %}</span><span>{% if research.completed %}目标已点亮{% else %}{{ research.total - research.remaining }}/{{ research.total }} · 剩余{{ research.remaining }}次{% endif %}</span></div><div class="research-track"><div class="research-fill" style="width: {{ research.percent }}%"></div></div></section>{% endif %}
      {% if events %}<div class="event-list">{% for event in events %}<span class="event">{{ event }}</span>{% endfor %}</div>{% endif %}
      {% if stats %}<section class="stats">{% for stat in stats %}<article class="stat"><div class="stat-label">{{ stat.label }}</div><div class="stat-value">{{ stat.value }}</div></article>{% endfor %}</section>{% endif %}
      {% if fishes %}<div class="fish-title">🐠 本次渔获</div><section class="fish-grid{% if fishes|length <= 4 %} featured{% elif fishes|length >= 9 %} dense{% endif %}">{% for fish in fishes %}<article class="fish"><div class="fish-name rarity-{{ fish.rarity }}{% if fish.ancient %} ancient{% endif %}">{{ fish.name }}</div><div class="fish-meta"><span>× {{ fish.count }}</span><span>{% if fish.price %}{{ fish.price }} 金币{% endif %}</span></div></article>{% endfor %}</section>{% if hidden_fishes %}<div class="more">还有 {{ hidden_fishes }} 条稀有渔获未展示</div>{% endif %}{% endif %}
      {% if notices %}<section class="notice-list">{% for notice in notices %}<div class="notice">{{ notice }}</div>{% endfor %}</section>{% endif %}
      {% if raw_lines %}<section class="notice-list">{% for line in raw_lines %}<div class="{% if kind == 'greedy' %}action{% else %}notice{% endif %}">{{ line }}</div>{% endfor %}</section>{% endif %}
      {% if not stats and not fishes and not raw_lines and not research %}<div class="status-box">{{ subtitle }}</div>{% endif %}
    </main>
    {% endif %}
  </article>
</body>
</html>
"""


RESEARCH_IMAGE_TEMPLATE = r"""
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent}body{width:760px;padding:18px;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#173042;background:linear-gradient(145deg,#d9f3ff,#f7fcff)}
.card{overflow:hidden;border:1px solid #a8d9ef;border-radius:16px;background:rgba(255,255,255,.96);box-shadow:0 8px 22px rgba(46,122,158,.14)}
.head{display:flex;align-items:center;justify-content:space-between;padding:15px 20px 12px;background:linear-gradient(100deg,#caedff,#effaff 70%,#fff);border-bottom:1px solid #c7e7f6}
.title{font-size:27px;font-weight:900}.user{font-size:16px;font-weight:900;color:#19709e}.sub{margin-top:3px;color:#5f8193;font-size:14px;font-weight:700}
.body{padding:13px 20px 16px}.target{display:flex;justify-content:space-between;align-items:end;gap:16px}.name{font-size:22px;font-weight:900;color:#174f70}.remain{font-size:15px;font-weight:900;color:#39728f}
.track{height:10px;margin-top:9px;overflow:hidden;border-radius:999px;background:#dceef7}.fill{height:100%;border-radius:inherit;background:linear-gradient(90deg,#2eb1ec,#6a75f3)}
.meta{display:flex;justify-content:space-between;gap:14px;margin-top:9px;color:#587789;font-size:14px;font-weight:800}.message{padding:9px 11px;border-radius:9px;background:#f1f8fc;color:#587789;font-size:15px;font-weight:800}
body.warning .card{border-color:#efd39a}body.warning .head{background:linear-gradient(100deg,#ffedc9,#fff9ec)}body.warning .title{color:#805700}
</style></head><body class="{{ kind }}"><article class="card"><header class="head"><div><div class="title">🔬 {{ title }}</div><div class="sub">{{ subtitle }}</div></div><div class="user">{{ user_name }}</div></header><main class="body">{% if research.active %}<div class="target"><div class="name">{{ research.target_type }} · {{ research.target }}</div><div class="remain">剩余 {{ research.remaining }} 次保底</div></div><div class="track"><div class="fill" style="width:{{ research.percent }}%"></div></div><div class="meta"><span>研究进度 {{ research.total - research.remaining }}/{{ research.total }}</span><span>当前加成 {{ research.multiplier }}</span><span>范围剩余 {{ research.remaining_targets }}</span><span>可用经验 {{ available_exp }}</span></div>{% else %}<div class="message">{{ message or subtitle }} · 可用经验 {{ available_exp }}</div>{% endif %}</main></article></body></html>
"""
