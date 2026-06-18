"""模糊命令入口的文本规范化工具。"""

from typing import List, Tuple


def _read_event_flag(event, name: str) -> bool:
    """安全读取 AstrBot 不同版本中的布尔事件标记。"""
    value = getattr(event, name, False)
    if callable(value):
        try:
            value = value()
        except TypeError:
            return False
    return value is True


def is_wake_command_event(event) -> bool:
    """判断事件是否已被 AstrBot 标记为唤醒或命令消息。"""
    return any(
        _read_event_flag(event, name)
        for name in ("is_at_or_wake_command", "is_wake", "is_wake_command")
    )


def extract_fuzzy_content(event, text: str) -> str:
    """提取模糊命令正文，兼容半角/全角斜杠及框架剥离前缀的情况。

    无显式斜杠时，仅接受 AstrBot 已标记为唤醒/命令的事件，避免误吞普通聊天。
    """
    normalized = (text or "").strip()
    if not normalized:
        return ""
    if normalized[0] in ("/", "／"):
        return normalized[1:].strip()
    if is_wake_command_event(event):
        return normalized
    return ""


def build_fuzzy_candidates(content: str) -> List[Tuple[str, list]]:
    """构建匹配候选；先保留参数，再尝试合并口语化空格。"""
    parts = content.split()
    if not parts:
        return []
    candidates = [(parts[0].lower(), parts[1:])]
    if len(parts) > 1:
        joined = "".join(parts).lower()
        if joined != parts[0].lower():
            candidates.append((joined, []))
    return candidates
