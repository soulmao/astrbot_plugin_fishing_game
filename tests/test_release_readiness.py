"""发布前元数据与配置一致性测试。"""

import json
import os
import re
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name: str) -> str:
    with open(os.path.join(PROJECT_ROOT, name), "r", encoding="utf-8") as file:
        return file.read()


class ReleaseReadinessTests(unittest.TestCase):
    """防止发布时版本号分裂或配置文件损坏。"""

    def test_version_is_consistent_across_release_files(self):
        metadata = _read("metadata.yaml")
        plugin = json.loads(_read("plugin.json"))
        main = _read("main.py")
        readme = _read("README.md")

        metadata_match = re.search(r"^version:\s*(V\d+\.\d+\.\d+)\s*$", metadata, re.MULTILINE)
        register_match = re.search(r"@register\([^\n]+,\s*\"(V\d+\.\d+\.\d+)\"\)", main)
        self.assertIsNotNone(metadata_match)
        self.assertIsNotNone(register_match)

        versions = {
            metadata_match.group(1),
            plugin["version"],
            register_match.group(1),
        }
        self.assertEqual(versions, {"V4.7.0"})
        self.assertIn("version-V4.7.0", readme)
        self.assertIn("### V4.7.0 更新摘要", readme)

    def test_json_release_files_are_valid(self):
        plugin = json.loads(_read("plugin.json"))
        schema = json.loads(_read("_conf_schema.json"))
        self.assertEqual(plugin["name"], "fishing_game")
        self.assertIn("llm_result_image_enabled", schema)
        self.assertIs(schema["llm_result_image_enabled"]["default"], True)

    def test_preview_artifacts_are_ignored(self):
        gitignore = _read(".gitignore")
        self.assertIn("docs/*preview*.html", gitignore)
        self.assertIn("docs/*preview*.png", gitignore)

    def test_docs_match_current_test_and_market_layout(self):
        agents = _read("AGENTS.md")
        readme = _read("README.md")
        help_source = _read("command_info.py")
        self.assertIn("129 个 `unittest` 用例", agents)
        self.assertNotIn("当前项目没有单元测试", agents)
        self.assertIn("`main.py` | 844", agents)
        self.assertIn("商店按四列", readme)
        self.assertIn("拍卖行按三列", readme)
        self.assertIn("钓鱼游戏帮助 · V4.7.0", help_source)
        self.assertIn("最高 Lv.15", help_source)
        self.assertIn("46 种鱼 × 15 种前缀", help_source)

    def test_llm_auction_price_and_greedy_descriptions_are_unambiguous(self):
        tools = _read("llm_tools.py")
        self.assertIn('if action == "listing" and price is not None:', tools)
        self.assertNotIn("贪婪时说调用", tools)


if __name__ == "__main__":
    unittest.main(verbosity=2)
