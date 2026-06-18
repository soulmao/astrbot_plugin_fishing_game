"""模糊命令文本规范化测试。"""

import importlib.util
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "fishing_game_fuzzy_utils", PROJECT_ROOT / "fuzzy_utils.py"
)
FUZZY_UTILS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(FUZZY_UTILS)


class _Event:
    def __init__(self, **flags):
        for name, value in flags.items():
            setattr(self, name, value)


class FuzzyCommandTextTests(unittest.TestCase):
    def test_half_width_slash(self):
        self.assertEqual(FUZZY_UTILS.extract_fuzzy_content(_Event(), "/钓一下"), "钓一下")

    def test_full_width_slash(self):
        self.assertEqual(FUZZY_UTILS.extract_fuzzy_content(_Event(), "／查看背包"), "查看背包")

    def test_framework_stripped_prefix_for_wake_event(self):
        event = _Event(is_at_or_wake_command=True)
        self.assertEqual(FUZZY_UTILS.extract_fuzzy_content(event, "钓一下"), "钓一下")

    def test_callable_wake_flag(self):
        event = _Event(is_wake=lambda: True)
        self.assertEqual(FUZZY_UTILS.extract_fuzzy_content(event, "查看背包"), "查看背包")

    def test_plain_chat_is_ignored(self):
        self.assertEqual(FUZZY_UTILS.extract_fuzzy_content(_Event(), "今天去钓鱼吗"), "")

    def test_spaced_phrase_gets_joined_candidate(self):
        candidates = FUZZY_UTILS.build_fuzzy_candidates("我的 鱼竿")
        self.assertEqual(candidates[0], ("我的", ["鱼竿"]))
        self.assertEqual(candidates[1], ("我的鱼竿", []))


if __name__ == "__main__":
    unittest.main()
