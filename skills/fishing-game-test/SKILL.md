---
name: fishing-game-test
description: Test and evaluate the AstrBot fishing_game plugin with regression checks and Monte Carlo balance simulations. Use when changing fishing mechanics, rod prefixes, instance enchantments, built-in special-rod skills, bait, rewards, cooldowns, economy values, locks, or admin commands, and when comparing long-term rod收益. Always include base-rod built-in skills, prefix skills, and instance skills in tests.
---

# 钓鱼游戏测试

对 `astrbot_plugin_fishing_game` 执行回归检查与可复现的收益模拟。

## 执行顺序

1. 修改命令、模型、锁或管理功能后，运行全部单元测试与编译检查。
2. 修改钓竿、前缀、词条、鱼饵、冷却或经济数值后，再运行收益模拟。
3. 重要平衡结论至少使用 3 个随机种子，每种钓竿至少模拟 1000 次。

```powershell
python -m unittest discover -s tests -q
python -m compileall -q .
python scripts/run_balance_simulation.py --project . --iterations 1000 --seed 20260618
```

## 词条口径

禁止只读取钓竿实例的 `skills` 字段。所有功能测试和收益模拟必须通过
`get_effective_rod_skills(base_id, prefix_id, rod_skills)` 合并以下三层：

1. 基础钓竿的 `built_in_skills`，例如金币钓竿和胡萝卜钓竿的原生词条。
2. 钓竿前缀的默认 `skills`。
3. 钓竿实例的附魔 `skills`；同名词条由实例值覆盖默认值。

构造钓竿时优先调用 `UserData.add_rod()`。若测试必须手工构造字典，也要用
`get_rod_builtin_skills()` 注入原生词条，并把钓竿放入 `owned_rods`，确保会持久变化的词条真实生效。

## 判读要求

- 使用净价值/小时比较强度，同时报告渔获、金币、经验、冷却和风险成本。
- 学徒同时比较经验；迅捷同时比较单轮与单位时间收益。
- 贪婪报告断线次数；嫉妒按明确的高等级玩家数量模拟。
- 金币钓竿检查最终金币；幸运方块检查运行后的实例词条。
- 输出原生/前缀/实例合并后的词条数量，发现缺失立即停止平衡判读。
- 随机模拟只用于发现风险，不用单一随机种子证明精确收益。
