"""游戏结果图片渲染和贪婪侵蚀效果测试。"""

import importlib.util
import os
import random
import sys
import types
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_NAME = "astrbot_plugin_fishing_game"

if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [PROJECT_ROOT]
    sys.modules[PACKAGE_NAME] = package


def _load_module(module_name: str, file_name: str):
    path = os.path.join(PROJECT_ROOT, file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


if f"{PACKAGE_NAME}.fish_data" not in sys.modules:
    _load_module(f"{PACKAGE_NAME}.fish_data", "fish_data.py")
renderer = _load_module(f"{PACKAGE_NAME}.result_renderer", "result_renderer.py")


class ResultRendererTests(unittest.TestCase):
    """语义着色与 HTML 安全测试。"""

    def test_fish_rarity_colors_use_real_data(self):
        content = renderer.render_result_html(
            "普通的鲫鱼、银色的鲈鱼、金色的龙鱼、神话的北海巨妖"
        )
        self.assertIn('fish-name rarity-common">鲫鱼', content)
        self.assertIn('fish-name rarity-rare">鲈鱼', content)
        self.assertIn('fish-name rarity-legendary">龙鱼', content)
        self.assertIn('fish-name rarity-mythic">北海巨妖', content)

    def test_longest_fish_name_wins(self):
        content = renderer.render_result_html("钓到了巨型章鱼")
        self.assertEqual(content.count('class="fish-name'), 1)
        self.assertIn('rarity-mythic">巨型章鱼', content)

    def test_ancient_collection_has_unique_style(self):
        content = renderer.render_result_html("古龙收藏的龙鱼")
        self.assertIn("rarity-legendary ancient", content)

    def test_user_text_is_html_escaped(self):
        content = renderer.render_result_html("<script>alert('x')</script>")
        self.assertNotIn("<script>", content)
        self.assertIn("&lt;script&gt;", content)

    def test_basic_markdown_is_rendered(self):
        content = renderer.render_result_html("## **本次渔获**\n- 稀有鲈鱼")
        self.assertIn('class="heading heading-2"', content)
        self.assertIn("<strong>本次渔获</strong>", content)
        self.assertIn('class="bullet"', content)

    def test_black_blocks_keep_their_own_image_style(self):
        content = renderer.render_result_html("贪婪■侵蚀")
        self.assertIn('<span class="obscured">■</span>', content)


class GreedyObscurityTests(unittest.TestCase):
    """无尽贪婪应产生黑色方块，不再制造问号乱码。"""

    def test_zero_intensity_keeps_text(self):
        self.assertEqual(renderer.obscure_text("钓鱼成功", 0), "钓鱼成功")

    def test_obscurity_uses_black_blocks_and_preserves_layout(self):
        source = "钓鱼成功！\n获得 100 金币"
        result = renderer.obscure_text(source, 1.0, random.Random(7))
        self.assertIn("■", result)
        self.assertNotIn("?", result)
        self.assertEqual(result.count("\n"), source.count("\n"))
        self.assertEqual(result.count(" "), source.count(" "))
        self.assertEqual(len(result), len(source))

    def test_intensity_is_capped(self):
        source = "一二三四五六七八九十"
        result = renderer.obscure_text(source, 99, random.Random(1))
        self.assertEqual(result.count("■"), 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
