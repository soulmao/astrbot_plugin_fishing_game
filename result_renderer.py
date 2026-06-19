"""LLM 游戏结果的语义着色与图片模板。"""

import html
import random
from typing import List, Optional, Tuple

from .fish_data import FISH_PREFIXES, FISH_TYPES


RARITY_LABELS = {
    "常见": "common",
    "稀有": "rare",
    "传说": "legendary",
    "神话": "mythic",
}


def is_t2i_service_error(error) -> bool:
    """判断异常是否来自 AstrBot 外部 T2I 端点不可用。"""
    message = str(error).lower()
    markers = (
        "all endpoints failed",
        "text2img failed",
        "t2i.network_strategy",
        "http 502",
        "http 503",
        "http 504",
    )
    return any(marker in message for marker in markers)


def obscure_text(text: str, intensity: float, rng=None) -> str:
    """用黑色方块侵蚀文字，保留空白与换行以维持版面结构。"""
    if not text or intensity <= 0:
        return text

    random_source = rng or random
    chars = list(text)
    candidates = [index for index, char in enumerate(chars) if not char.isspace()]
    if not candidates:
        return text

    ratio = min(max(float(intensity), 0.0), 1.0) * 0.75
    replace_count = max(1, int(len(candidates) * ratio))
    for index in random_source.sample(candidates, min(replace_count, len(candidates))):
        chars[index] = "■"
    return "".join(chars)


def _build_fish_entities() -> List[Tuple[str, Optional[dict], dict]]:
    """生成完整鱼名和裸鱼名，按长度降序以避免子串误匹配。"""
    entities = []
    for fish in FISH_TYPES:
        for prefix in FISH_PREFIXES:
            entities.append((f"{prefix['name']}{fish['name']}", prefix, fish))
        entities.append((fish["name"], None, fish))
    return sorted(entities, key=lambda item: len(item[0]), reverse=True)


FISH_ENTITIES = _build_fish_entities()


def _render_fish(prefix: Optional[dict], fish: dict) -> str:
    """分别渲染鱼名前缀和鱼种稀有度。"""
    parts = []
    if prefix:
        prefix_class = prefix.get("rarity", "common")
        ancient_class = " ancient" if prefix.get("id") == "pref_014" else ""
        parts.append(
            f'<span class="fish-prefix rarity-{prefix_class}{ancient_class}">'
            f'{html.escape(prefix["name"])}</span>'
        )
    fish_class = fish.get("rarity", "common")
    parts.append(
        f'<span class="fish-name rarity-{fish_class}">{html.escape(fish["name"])}</span>'
    )
    return "".join(parts)


def _match_fish(text: str, position: int):
    """在指定位置匹配最长鱼名。"""
    for name, prefix, fish in FISH_ENTITIES:
        if text.startswith(name, position):
            return name, prefix, fish
    return None


def _render_inline(text: str, allow_bold: bool = True) -> str:
    """安全渲染少量 Markdown，并为已知鱼名和稀有度标签着色。"""
    parts = []
    index = 0
    while index < len(text):
        if allow_bold and text.startswith("**", index):
            end = text.find("**", index + 2)
            if end != -1:
                parts.append(f"<strong>{_render_inline(text[index + 2:end], False)}</strong>")
                index = end + 2
                continue

        if text[index] == "`":
            end = text.find("`", index + 1)
            if end != -1:
                parts.append(f"<code>{html.escape(text[index + 1:end])}</code>")
                index = end + 1
                continue

        if text[index] == "■":
            parts.append('<span class="obscured">■</span>')
            index += 1
            continue

        fish_match = _match_fish(text, index)
        if fish_match:
            name, prefix, fish = fish_match
            parts.append(_render_fish(prefix, fish))
            index += len(name)
            continue

        rarity_match = next(
            ((label, rarity) for label, rarity in RARITY_LABELS.items()
             if text.startswith(label, index)),
            None,
        )
        if rarity_match:
            label, rarity = rarity_match
            parts.append(
                f'<span class="rarity-label rarity-{rarity}">{html.escape(label)}</span>'
            )
            index += len(label)
            continue

        parts.append(html.escape(text[index]))
        index += 1
    return "".join(parts)


def _line_class(text: str) -> str:
    """根据游戏结果行的语义选择辅助颜色。"""
    stripped = text.strip()
    if any(token in stripped for token in ("❌", "⚠", "断线", "失败", "不足")):
        return "danger"
    if stripped.startswith(("💰", "💎", "🎁", "🎫")):
        return "reward"
    if stripped.startswith(("✨", "📈", "🎉")) or "经验" in stripped:
        return "experience"
    if stripped.startswith(("⏰", "🌊")) or "冷却" in stripped:
        return "cooldown"
    if stripped.startswith(("📦", "🎣", "🐟", "🐠", "🪤", "🎫", "🧰")):
        return "section"
    return "normal"


def render_result_html(text: str) -> str:
    """把 LLM 文本转换为可安全嵌入模板的游戏结果 HTML。"""
    rendered_lines = []
    for raw_line in (text or "").splitlines() or [""]:
        stripped = raw_line.strip()
        if not stripped:
            rendered_lines.append('<div class="spacer"></div>')
            continue

        heading_level = 0
        while heading_level < min(3, len(stripped)) and stripped[heading_level] == "#":
            heading_level += 1
        if heading_level and len(stripped) > heading_level and stripped[heading_level].isspace():
            content = stripped[heading_level:].strip()
            rendered_lines.append(
                f'<div class="heading heading-{heading_level}">{_render_inline(content)}</div>'
            )
            continue

        bullet = ""
        content = raw_line
        left_stripped = raw_line.lstrip()
        if left_stripped.startswith(("- ", "* ", "• ")):
            bullet = '<span class="bullet">◆</span>'
            content = left_stripped[2:]
        rendered_lines.append(
            f'<div class="result-line {_line_class(content)}">{bullet}{_render_inline(content)}</div>'
        )
    return "".join(rendered_lines)


RESULT_IMAGE_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; background: transparent; }
    body {
      width: 760px; padding: 24px;
      font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      color: #17212b;
      background:
        radial-gradient(circle at 86% 8%, rgba(123, 211, 255, .32), transparent 31%),
        linear-gradient(145deg, #d9f3ff 0%, #eefaff 48%, #ffffff 100%);
    }
    .card {
      overflow: hidden;
      border: 1px solid #a8d9ef;
      border-radius: 20px;
      background: rgba(255, 255, 255, .94);
      box-shadow: 0 12px 32px rgba(46, 122, 158, .16), inset 0 1px rgba(255,255,255,.8);
    }
    .header {
      padding: 18px 24px 15px;
      border-bottom: 1px solid #c7e7f6;
      background: linear-gradient(90deg, #d9f3ff 0%, rgba(255,255,255,.92) 100%);
    }
    .title { font-size: 26px; font-weight: 800; letter-spacing: 2px; color: #12658b; }
    .subtitle { margin-top: 4px; font-size: 13px; color: #5d8193; letter-spacing: 1px; }
    .content { padding: 18px 24px 22px; font-size: 18px; line-height: 1.55; }
    .result-line { min-height: 28px; white-space: pre-wrap; overflow-wrap: anywhere; }
    .spacer { height: 10px; }
    .heading { margin: 8px 0 5px; font-weight: 800; color: #132b38; }
    .heading-1 { font-size: 26px; } .heading-2 { font-size: 22px; } .heading-3 { font-size: 19px; }
    strong { color: #101820; font-weight: 800; }
    code { padding: 2px 6px; border-radius: 5px; color: #12658b; background: #e2f4fc; }
    .bullet { margin-right: 8px; color: #2587b2; font-size: 12px; vertical-align: 2px; }
    .reward { color: #966300; } .experience { color: #08796f; }
    .cooldown { color: #176a9b; } .danger { color: #c42d43; }
    .section { color: #153746; font-weight: 800; }
    .fish-prefix { padding: 1px 3px; margin-right: 1px; border-radius: 4px; font-weight: 750; }
    .fish-name, .rarity-label { font-weight: 800; }
    .obscured { color: #05090c; }
    .rarity-common { color: #222a30; }
    .rarity-rare { color: #1478c9; text-shadow: 0 0 8px rgba(60, 155, 255, .18); }
    .rarity-legendary { color: #d52f45; text-shadow: 0 0 8px rgba(255, 55, 82, .16); }
    .rarity-mythic { color: #8438b5; text-shadow: 0 0 8px rgba(190, 82, 255, .18); }
    .ancient { color: #a76d00; text-shadow: 0 0 8px rgba(255, 177, 49, .2); }
  </style>
</head>
<body>
  <section class="card">
    <header class="header">
      <div class="title">{{ sender_name }}</div>
      <div class="subtitle">🎣 钓鱼游戏结果</div>
    </header>
    <main class="content">{{ content_html | safe }}</main>
  </section>
</body>
</html>
"""
