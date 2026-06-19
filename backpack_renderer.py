"""背包结果的结构化视图数据与专用图片模板。"""

import html
import re

from .fish_data import (
    ENCHANT_TICKETS,
    LEVELS,
    ROD_SKILL_DESCRIPTIONS,
    calc_fish_value,
    get_bait_by_id,
    get_bait_prefix,
    get_effective_rod_skills,
    get_fish_by_id,
    get_level_info,
    get_next_level_exp,
    get_prefix_by_id,
    get_rod_by_id,
    get_rod_prefix,
)
from .utils import calc_enchant_price, get_available_skills


FISH_DISPLAY_LIMIT = 60
MARKER_SKILLS = {
    "arrogant", "greedy", "endless_greedy", "cursed", "lucky_block", "jealous",
}
RARITY_ORDER = {"mythic": 4, "legendary": 3, "rare": 2, "common": 1}
DIRECTED_ENCHANT_PATTERN = re.compile(r"^directed_enchant_([a-z_]+)_(\d+)$")


def _safe(value) -> str:
    """转义所有可能进入 HTML 的动态文本。"""
    return html.escape(str(value), quote=True)


def _format_number(value: int) -> str:
    return f"{int(value):,}"


def _format_time(seconds: int) -> str:
    """以紧凑中文格式显示冷却。"""
    seconds = max(0, int(seconds))
    if seconds <= 0:
        return "可以钓鱼了"
    hours, remain = divmod(seconds, 3600)
    minutes, secs = divmod(remain, 60)
    parts = []
    if hours:
        parts.append(f"{hours} 小时")
    if minutes:
        parts.append(f"{minutes} 分钟")
    if secs and not hours:
        parts.append(f"{secs} 秒")
    return " ".join(parts)


def _build_exp_progress(user) -> dict:
    """按当前等级区间计算经验进度，避免直接用总经验除以下一级总经验。"""
    level_info = get_level_info(user.level)
    current_required = int(level_info.get("exp_required", 0))
    next_required = get_next_level_exp(user.level)
    if next_required is None:
        return {
            "percent": 100.0,
            "text": f"{_format_number(user.exp)} · 已满级",
            "remaining": "最高等级",
        }

    span = max(1, int(next_required) - current_required)
    gained = max(0, int(user.exp) - current_required)
    percent = min(100.0, gained / span * 100)
    return {
        "percent": round(percent, 2),
        "text": f"{_format_number(user.exp)} / {_format_number(next_required)}",
        "remaining": f"距离升级还差 {_format_number(max(0, int(next_required) - int(user.exp)))} 经验",
    }


def _rod_name(rod: dict) -> str:
    base = get_rod_by_id(rod.get("base_id", ""))
    if not base:
        return "未知钓竿"
    prefix_id = rod.get("prefix_id", "")
    if not prefix_id or base.get("no_prefix"):
        return base["name"]
    prefix = get_rod_prefix(prefix_id)
    return f"{prefix.get('name', '')}{base['name']}"


def _get_enchant_warning(rod: dict) -> str:
    """复用命令层规则生成下一次附魔的风险提示。"""
    prefix = get_rod_prefix(rod.get("prefix_id", ""))
    max_slots = prefix.get("max_slots", 0)
    if max_slots <= 0:
        return ""
    current_skills = rod.get("skills", {}) or {}
    safe_skills = [
        skill for skill in get_available_skills()
        if skill not in (prefix.get("skills", {}) or {})
    ]
    has_safe_slot = (
        len(current_skills) < max_slots
        and any(skill not in current_skills for skill in safe_skills)
    )
    if has_safe_slot:
        return ""
    if len(current_skills) >= max_slots:
        return "槽位已满，继续附魔将随机替换已有技能"
    return "安全技能已耗尽，继续附魔将低值覆盖前缀自带技能"


def _build_rods(user, include_enchant_details: bool = False, sort_current: bool = True) -> list:
    current_id = user.current_rod.get("instance_id", "")
    rods = []
    for index, rod in enumerate(user.get_owned_rods(), 1):
        base = get_rod_by_id(rod.get("base_id", "")) or {}
        prefix = get_rod_prefix(rod.get("prefix_id", ""))
        skills = []
        effective_skills = get_effective_rod_skills(
            rod.get("base_id", ""), rod.get("prefix_id", ""), rod.get("skills")
        )
        for skill_id, value in effective_skills.items():
            label = ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)
            if skill_id in MARKER_SKILLS:
                value_text = "特殊效果"
            else:
                value_text = f"{int(round(float(value) * 100))}%"
            skills.append({"name": _safe(label), "value": _safe(value_text)})

        enchant_count = max(0, int(rod.get("enchant_count", 0)))
        rods.append({
            "index": index,
            "name": _safe(_rod_name(rod)),
            "enhancement": f"+{enchant_count}" if enchant_count else "",
            "current": bool(current_id and rod.get("instance_id") == current_id),
            "quality": _safe(base.get("quality", "common")),
            "skills": skills,
            "enchant_price": (
                _format_number(calc_enchant_price(rod))
                if include_enchant_details and prefix.get("max_slots", 0) > 0
                else ""
            ),
            "warning": _safe(_get_enchant_warning(rod)) if include_enchant_details else "",
        })
    if sort_current:
        rods.sort(key=lambda item: not item["current"])
    return rods


def _build_baits(user) -> list:
    current = user.current_bait
    items = []
    for bait in user.get_baits():
        base = get_bait_by_id(bait.get("base_id", ""))
        prefix = get_bait_prefix(bait.get("prefix_id", ""))
        if not base or not prefix:
            continue
        items.append({
            "name": _safe(f"{prefix['name']}{base['name']}"),
            "count": _format_number(bait.get("count", 0)),
            "current": (
                bait.get("base_id") == current.get("base_id")
                and bait.get("prefix_id") == current.get("prefix_id")
            ),
        })
    return items


def _build_fishes(user) -> dict:
    valid_items = []
    total_value = 0
    for entry in user.get_fish_inventory():
        fish = get_fish_by_id(entry.get("fish_id", ""))
        prefix = get_prefix_by_id(entry.get("prefix_id", ""))
        if not fish or not prefix:
            continue
        count = max(0, int(entry.get("count", 0)))
        stack_value = calc_fish_value(fish["id"], prefix["id"], count)
        total_value += stack_value
        valid_items.append({
            "name": _safe(f"{prefix['name']}{fish['name']}"),
            "count": _format_number(count),
            "rarity": _safe(fish.get("rarity", "common")),
            "ancient": prefix.get("id") == "pref_014",
            "sort_value": stack_value,
            "obtained_at": int(entry.get("obtained_at", 0)),
        })

    valid_items.sort(
        key=lambda item: (
            item["sort_value"], RARITY_ORDER.get(item["rarity"], 0), item["obtained_at"]
        ),
        reverse=True,
    )
    visible = valid_items[:FISH_DISPLAY_LIMIT]
    hidden_count = max(0, len(valid_items) - len(visible))
    for item in visible:
        item.pop("obtained_at", None)
        item.pop("sort_value", None)
    return {
        "items": visible,
        "hidden_count": hidden_count,
        "total_value": _format_number(total_value),
        "total_types": len(valid_items),
    }


def _build_tickets(user) -> list:
    ticket_names = {ticket["id"]: ticket["name"] for ticket in ENCHANT_TICKETS}
    result = []
    for ticket in user._data.get("enchant_tickets", []):
        ticket_id = ticket.get("ticket_id", "")
        result.append({
            "name": _safe(ticket_names.get(ticket_id, ticket_id or "未知附魔券")),
            "count": _format_number(ticket.get("count", 0)),
        })
    return result


def _build_items(user) -> list:
    result = []
    for item in user._data.get("items", []):
        item_id = item.get("id", "")
        match = DIRECTED_ENCHANT_PATTERN.fullmatch(item_id)
        if match:
            skill_id, percent = match.groups()
            skill_name = ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)
            name = f"定向附魔券 · {skill_name} +{int(percent)}%"
        elif item_id == "refresh_token":
            name = "🔄 刷新券"
        else:
            name = item_id or "未知道具"
        result.append({"name": _safe(name), "count": _format_number(item.get("count", 0))})
    return result


def build_backpack_view(user, sender_name: str) -> dict:
    """从用户快照构建背包专用视图数据。"""
    level_info = get_level_info(user.level)
    return {
        "user_name": _safe(sender_name or "垂钓者"),
        "level_name": _safe(level_info.get("name", "渔夫")),
        "level": int(user.level),
        "coins": _format_number(user.coins),
        "total_fish_count": _format_number(user.total_fish_count),
        "exp": _build_exp_progress(user),
        "rods": _build_rods(user),
        "baits": _build_baits(user),
        "fishes": _build_fishes(user),
        "tickets": _build_tickets(user),
        "items": _build_items(user),
        "streak": int(user.consecutive_checkin_days),
        "achievement_count": len(user.achievements),
        "cooldown": _safe(_format_time(user.get_fishing_cd_remaining())),
    }


def build_rods_view(user, sender_name: str) -> dict:
    """构建“我的钓竿”专用视图，保留装备编号、费用和附魔风险。"""
    return {
        "user_name": _safe(sender_name or "垂钓者"),
        "rods": _build_rods(user, include_enchant_details=True, sort_current=False),
    }


BACKPACK_IMAGE_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; background: transparent; }
    body { width: 1200px; padding: 30px; font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      color: #17212b; background: radial-gradient(circle at 86% 8%, rgba(123,211,255,.32), transparent 31%),
      linear-gradient(145deg, #d9f3ff 0%, #eefaff 48%, #fff 100%); }
    .sheet { overflow: hidden; border: 1px solid #a8d9ef; border-radius: 24px; background: rgba(255,255,255,.95);
      box-shadow: 0 18px 48px rgba(46,122,158,.18); }
    .header { padding: 27px 34px 24px; border-bottom: 1px solid #c7e7f6;
      background: linear-gradient(100deg, #caedff 0%, #eaf8ff 55%, #fff 100%); }
    .user-name { font-size: 34px; line-height: 1.2; font-weight: 900; color: #102a38; letter-spacing: 1px; }
    .user-meta { margin-top: 8px; color: #54798b; font-size: 15px; letter-spacing: 1px; }
    .body { padding: 28px 34px 34px; }
    .summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 18px; }
    .summary-card { padding: 14px 16px; border: 1px solid #d3eaf5; border-radius: 14px; background: #f8fcfe; }
    .summary-label { color: #688391; font-size: 13px; } .summary-value { margin-top: 4px; font-size: 21px; font-weight: 800; color: #17212b; }
    .exp-card { padding: 16px 18px; border: 1px solid #c8e6f4; border-radius: 15px; background: #f4fbff; }
    .exp-head { display: flex; justify-content: space-between; gap: 18px; margin-bottom: 9px; font-size: 14px; color: #527487; }
    .exp-value { color: #12658b; font-weight: 800; }
    .progress { height: 13px; overflow: hidden; border-radius: 999px; background: #dceef7; box-shadow: inset 0 1px 3px rgba(32,91,120,.12); }
    .progress-fill { height: 100%; min-width: 5px; border-radius: inherit; background: linear-gradient(90deg, #4bb7e8, #2387df); }
    .section { margin-top: 26px; } .section-title { margin-bottom: 12px; font-size: 20px; font-weight: 900; color: #153746; }
    .rod-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
    .rod-card { padding: 16px; border: 1px solid #b9deef; border-radius: 16px;
      background: linear-gradient(135deg, #d8f2ff 0%, #f3fbff 62%, #fff 100%); box-shadow: 0 7px 18px rgba(41,128,169,.09); }
    .rod-card.current { grid-column: 1 / -1; border: 2px solid #258be3; box-shadow: 0 0 0 3px rgba(37,139,227,.12), 0 8px 22px rgba(37,139,227,.14); }
    .rod-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .rod-name { min-width: 0; font-size: 19px; font-weight: 900; color: #123348; }
    .rod-badges { display: flex; align-items: center; gap: 7px; flex: 0 0 auto; }
    .enhancement { padding: 3px 9px; border-radius: 999px; background: #1676c2; color: #fff; font-weight: 900; }
    .current-badge { padding: 3px 9px; border-radius: 999px; background: #e0f2ff; color: #146fb8; font-size: 12px; font-weight: 800; }
    .skill-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 13px; }
    .skill { min-width: 82px; padding: 7px 10px; border: 1px solid #b9deef; border-radius: 10px; background: rgba(255,255,255,.84); text-align: center; }
    .skill-name { display: block; color: #275267; font-size: 13px; font-weight: 700; }
    .skill-value { display: block; margin-top: 2px; color: #126fba; font-size: 15px; font-weight: 900; }
    .empty { color: #8296a0; font-size: 14px; }
    .chip-list { display: flex; flex-wrap: wrap; gap: 9px; }
    .chip { padding: 7px 11px; border: 1px solid #d0e8f3; border-radius: 999px; background: #f7fcfe; color: #27434f; }
    .chip-current { border-color: #5ca8df; background: #e5f4ff; color: #146da9; font-weight: 700; }
    .count { margin-left: 5px; color: #637c88; font-weight: 800; }
    .fish-head { display: flex; justify-content: space-between; gap: 16px; align-items: baseline; margin-bottom: 12px; }
    .fish-total { color: #966300; font-size: 14px; font-weight: 800; }
    .fish-chip { border-color: #d8e9f1; background: #fbfdfe; }
    .fish-name { font-weight: 750; }
    .rarity-common { color: #222a30; } .rarity-rare { color: #1478c9; }
    .rarity-legendary { color: #d52f45; } .rarity-mythic { color: #8438b5; }
    .ancient { color: #a76d00; }
    .fish-more { margin-top: 11px; padding: 9px; border-radius: 10px; text-align: center; color: #496979; background: #edf7fb; font-weight: 800; }
    .lower-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
    .status-row { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 24px; padding-top: 19px; border-top: 1px solid #d8ebf4; }
    .status { padding: 7px 11px; border-radius: 10px; background: #edf8fd; color: #285263; }
  </style>
</head>
<body>
  <article class="sheet">
    <header class="header">
      <div class="user-name">{{ user_name }}</div>
      <div class="user-meta">{{ level_name }} · Lv.{{ level }} · 个人背包</div>
    </header>
    <main class="body">
      <section class="summary">
        <div class="summary-card"><div class="summary-label">金币</div><div class="summary-value">💰 {{ coins }}</div></div>
        <div class="summary-card"><div class="summary-label">累计钓鱼</div><div class="summary-value">🐟 {{ total_fish_count }}</div></div>
        <div class="summary-card"><div class="summary-label">成就</div><div class="summary-value">🏅 {{ achievement_count }}</div></div>
      </section>
      <section class="exp-card">
        <div class="exp-head"><span class="exp-value">经验 {{ exp.text }}</span><span>{{ exp.remaining }}</span></div>
        <div class="progress"><div class="progress-fill" style="width: {{ exp.percent }}%"></div></div>
      </section>

      <section class="section">
        <div class="section-title">🎣 我的钓竿</div>
        <div class="rod-grid">
          {% for rod in rods %}
          <article class="rod-card{% if rod.current %} current{% endif %}">
            <div class="rod-head">
              <div class="rod-name">{{ rod.name }}</div>
              <div class="rod-badges">
                {% if rod.enhancement %}<span class="enhancement">{{ rod.enhancement }}</span>{% endif %}
                {% if rod.current %}<span class="current-badge">当前装备</span>{% endif %}
              </div>
            </div>
            {% if rod.skills %}<div class="skill-grid">
              {% for skill in rod.skills %}<div class="skill"><span class="skill-name">{{ skill.name }}</span><span class="skill-value">{{ skill.value }}</span></div>{% endfor %}
            </div>{% else %}<div class="skill-grid"><span class="empty">暂无技能效果</span></div>{% endif %}
          </article>
          {% else %}<span class="empty">还没有钓竿</span>{% endfor %}
        </div>
      </section>

      <section class="section">
        <div class="section-title">🪤 鱼饵</div>
        <div class="chip-list">{% for bait in baits %}<span class="chip{% if bait.current %} chip-current{% endif %}">{{ bait.name }} <span class="count">× {{ bait.count }}</span></span>{% else %}<span class="empty">暂无鱼饵</span>{% endfor %}</div>
      </section>

      <section class="section">
        <div class="fish-head"><div class="section-title" style="margin:0">🐠 渔获 · {{ fishes.total_types }} 种</div><div class="fish-total">总价值 {{ fishes.total_value }} 金币</div></div>
        <div class="chip-list">{% for fish in fishes.items %}<span class="chip fish-chip"><span class="fish-name rarity-{{ fish.rarity }}{% if fish.ancient %} ancient{% endif %}">{{ fish.name }}</span><span class="count">× {{ fish.count }}</span></span>{% else %}<span class="empty">暂无渔获</span>{% endfor %}</div>
        {% if fishes.hidden_count %}<div class="fish-more">还有 {{ fishes.hidden_count }} 条渔获未展示</div>{% endif %}
      </section>

      <div class="lower-grid">
        <section class="section"><div class="section-title">🎫 附魔券</div><div class="chip-list">{% for ticket in tickets %}<span class="chip">{{ ticket.name }} <span class="count">× {{ ticket.count }}</span></span>{% else %}<span class="empty">暂无附魔券</span>{% endfor %}</div></section>
        <section class="section"><div class="section-title">🧰 道具</div><div class="chip-list">{% for item in items %}<span class="chip">{{ item.name }} <span class="count">× {{ item.count }}</span></span>{% else %}<span class="empty">暂无道具</span>{% endfor %}</div></section>
      </div>
      <div class="status-row">
        {% if streak %}<span class="status">🔥 连续签到 {{ streak }} 天</span>{% endif %}
        <span class="status">⏰ {{ cooldown }}</span>
      </div>
    </main>
  </article>
</body>
</html>
"""


RODS_IMAGE_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; background: transparent; }
    body { width: 920px; padding: 30px; font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      color: #17212b; background: radial-gradient(circle at 86% 8%, rgba(123,211,255,.32), transparent 31%),
      linear-gradient(145deg, #d9f3ff 0%, #eefaff 48%, #fff 100%); }
    .sheet { overflow: hidden; border: 1px solid #a8d9ef; border-radius: 24px; background: rgba(255,255,255,.95);
      box-shadow: 0 18px 48px rgba(46,122,158,.18); }
    .header { padding: 27px 34px 24px; border-bottom: 1px solid #c7e7f6;
      background: linear-gradient(100deg, #caedff 0%, #eaf8ff 55%, #fff 100%); }
    .user-name { font-size: 34px; font-weight: 900; color: #102a38; }
    .user-meta { margin-top: 8px; color: #54798b; font-size: 15px; letter-spacing: 1px; }
    .body { padding: 28px 34px 34px; }
    .rod-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 15px; }
    .rod-card { min-width: 0; padding: 17px; border: 1px solid #b9deef; border-radius: 16px;
      background: linear-gradient(135deg, #d8f2ff 0%, #f3fbff 62%, #fff 100%); box-shadow: 0 7px 18px rgba(41,128,169,.09); }
    .rod-card.current { border: 2px solid #258be3; box-shadow: 0 0 0 3px rgba(37,139,227,.12), 0 8px 22px rgba(37,139,227,.14); }
    .rod-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
    .rod-title { min-width: 0; } .rod-index { margin-bottom: 4px; color: #668391; font-size: 12px; font-weight: 800; }
    .rod-name { font-size: 18px; line-height: 1.35; font-weight: 900; color: #123348; }
    .rod-badges { display: flex; align-items: center; gap: 6px; flex: 0 0 auto; }
    .enhancement { padding: 3px 9px; border-radius: 999px; background: #1676c2; color: #fff; font-weight: 900; }
    .current-badge { padding: 3px 9px; border-radius: 999px; background: #e0f2ff; color: #146fb8; font-size: 12px; font-weight: 800; }
    .skill-grid { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 13px; }
    .skill { min-width: 76px; padding: 6px 8px; border: 1px solid #b9deef; border-radius: 9px; background: rgba(255,255,255,.86); text-align: center; }
    .skill-name { display: block; color: #275267; font-size: 12px; font-weight: 700; }
    .skill-value { display: block; margin-top: 2px; color: #126fba; font-size: 14px; font-weight: 900; }
    .empty { margin-top: 13px; color: #8296a0; font-size: 13px; }
    .rod-footer { display: flex; flex-direction: column; gap: 7px; margin-top: 13px; padding-top: 11px; border-top: 1px solid #cce5f1; }
    .price { color: #176a9b; font-size: 13px; font-weight: 800; }
    .warning { padding: 7px 9px; border: 1px solid #f1c5a5; border-radius: 9px; background: #fff7ef; color: #a84a17; font-size: 12px; line-height: 1.45; }
    .hint { margin-top: 22px; padding: 12px 14px; border-radius: 12px; background: #edf8fd; color: #496979; text-align: center; font-size: 14px; }
  </style>
</head>
<body>
  <article class="sheet">
    <header class="header"><div class="user-name">{{ user_name }}</div><div class="user-meta">🎣 我的钓竿 · {{ rods|length }} 根</div></header>
    <main class="body">
      <div class="rod-grid">
        {% for rod in rods %}<article class="rod-card{% if rod.current %} current{% endif %}">
          <div class="rod-head"><div class="rod-title"><div class="rod-index">第 {{ rod.index }} 根</div><div class="rod-name">{{ rod.name }}</div></div>
            <div class="rod-badges">{% if rod.enhancement %}<span class="enhancement">{{ rod.enhancement }}</span>{% endif %}{% if rod.current %}<span class="current-badge">当前装备</span>{% endif %}</div></div>
          {% if rod.skills %}<div class="skill-grid">{% for skill in rod.skills %}<div class="skill"><span class="skill-name">{{ skill.name }}</span><span class="skill-value">{{ skill.value }}</span></div>{% endfor %}</div>{% else %}<div class="empty">暂无技能效果</div>{% endif %}
          {% if rod.enchant_price or rod.warning %}<div class="rod-footer">{% if rod.enchant_price %}<div class="price">✨ 下次附魔或升级 · {{ rod.enchant_price }} 金币</div>{% endif %}{% if rod.warning %}<div class="warning">⚠ {{ rod.warning }}</div>{% endif %}</div>{% endif %}
        </article>{% else %}<div class="empty">还没有钓竿</div>{% endfor %}
      </div>
      <div class="hint">发送「/装备钓竿 编号」即可切换装备</div>
    </main>
  </article>
</body>
</html>
"""
