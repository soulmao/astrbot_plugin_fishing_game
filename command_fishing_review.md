# command_fishing.py 深度审查报告

## 审查范围
- 文件：`/mnt/agents/output/refactored/command_fishing.py`
- 依赖文件：`utils.py`、`fish_data.py`、`commands_base.py`、`models.py`
- 审查重点：异步一致性、参数传递、边界条件、并发安全、逻辑完整性

---

## 发现的问题（含严重等级）

### 🔴 严重 (Critical) — 3个

#### C1. 丰收技能中 `_do_fish_once` 返回 None 时静默跳过（与基础循环处理不一致）
**位置**：第152-159行
```python
if harvest_triggered:
    if is_gold_rod or is_carrot_rod or user.remove_bait(...):
        result = self._do_fish_once(user, rod, selected_bait)
        if result:   # ← 仅当 result 为真值时才处理
            fish_results.append(result)
            ...
```
**问题描述**：基础钓鱼循环中（第140-142行），`_do_fish_once` 返回 None 时会 `return "钓鱼出现异常，请联系管理员"`。但丰收技能触发时，如果 `_do_fish_once` 返回 None，代码只是静默跳过，不返回任何错误消息，用户感知不到问题。

**修复建议**：统一处理方式，丰收中 `_do_fish_once` 返回 None 时也应返回异常消息：
```python
result = self._do_fish_once(user, rod, selected_bait)
if result is None:
    return "钓鱼出现异常，请联系管理员"
```

---

#### C2. 远航技能中 `_do_fish_once` 返回 None 时静默跳过（同上）
**位置**：第174-180行
```python
for _ in range(voyage_count):
    ...
    result = self._do_fish_once(user, rod, selected_bait)
    if result:   # ← 同上问题
        voyage_results.append(result)
        ...
```
**问题描述**：与 C1 相同，远航循环中 `_do_fish_once` 返回 None 时静默跳过。

**修复建议**：同上，添加 `if result is None: return "钓鱼出现异常，请联系管理员"`。

---

#### C3. 远航显示消息使用目标次数而非实际执行次数
**位置**：第166-169行、第308行
```python
voyage_count = min(total_exp // 20, 50)   # ← 目标次数
...
event_msgs.append(f"🧭 远航触发！额外{voyage_count}次")   # ← 显示目标次数
```
**问题描述**：`voyage_count` 是根据经验值计算的目标次数，而非实际成功执行的次数。当鱼饵不足时（第172行 `break`），实际执行次数可能远小于目标次数。用户会看到"额外50次"但实际只钓了2次。

**修复建议**：使用实际执行次数（`len(voyage_results)`）显示：
```python
actual_voyage_count = len(voyage_results)
event_msgs.append(f"🧭 远航触发！额外{actual_voyage_count}次")
```

---

### 🟡 中等 (Medium) — 1个

#### M1. 金币钓竿死代码检查
**位置**：第49-53行
```python
gold_cost = int(user.coins * 0.10)
if user.coins < 100:
    return "金币不足100，无法使用金币钓竿！"
if gold_cost < 1:   # ← 死代码
    return "金币不足，无法使用金币钓竿！"
```
**问题描述**：第50行的 `user.coins < 100` 已经确保执行到第52行时 `coins >= 100`，因此 `gold_cost = int(coins * 0.10) >= 10`，永远不会 `< 1`。第52-53行代码永远不会执行，属于死代码。

**修复建议**：删除第52-53行，或改为检查 `user.remove_coins(gold_cost)` 的返回值：
```python
gold_cost = int(user.coins * 0.10)
if user.coins < 100:
    return "金币不足100，无法使用金币钓竿！"
if not user.remove_coins(gold_cost):
    return "金币扣除失败！"
```

---

### 🟢 低等 (Low) — 3个

#### L1. `get_available_skills()` 技能池不完整（可能影响幸运方块逻辑）
**位置**：`utils.py` 第100-102行；`command_fishing.py` 第267行

`get_available_skills()` 只返回8种技能：`["swift", "lucky", "harvest", "treasure", "tide", "exp_boost", "voyage", "mending"]`

缺失：`fail_chance`、`coin_reduce`、`lucky_block`、`greedy`、`cursed`

**问题描述**：幸运方块添加新技能时（第267行），只能从上述8种中选择。如果设计意图是13种技能都可以通过幸运方块获得，则存在遗漏。反之如果是设计意图（特殊前缀专属技能不应通过幸运方块获得），则不是问题。

**修复建议**：确认设计意图。如果应该包含全部技能，修改为返回完整列表。

---

#### L2. 金币钓竿迅捷失败时金币已扣除
**位置**：第54行 vs 第86-90行
```python
user.remove_coins(gold_cost)      # 第54行：先扣除金币
...
if fail_chance_val > 0 and random.random() < fail_chance_val:   # 第86行：后判定失败
    ...
    return f"💥 钓鱼失败！..."
```
**问题描述**：使用金币钓竿时，金币在迅捷失败判定之前已被扣除。如果迅捷触发失败，用户损失了金币但什么都没钓到。需要确认这是否为原始设计意图。

**修复建议**：如果原始逻辑是"先扣费再钓鱼"（类似入场费），则保持现状并添加注释说明；如果原始逻辑是"成功后扣费"，将金币扣除移至迅捷失败判定之后。

---

#### L3. 经验显示条件逻辑可简化
**位置**：第346-350行
```python
if exp_boost_val > 0 and not coin_reduce_val:
    exp_line += f"（含神慧+{int(exp_boost_val*100)}%）"
elif coin_reduce_val > 0:
    exp_line += f"（含学徒加成+{int(exp_boost_val*100)}%）"
```
**问题描述**：当 `coin_reduce_val > 0` 时显示"学徒加成"，但显示的经验加成百分比是 `exp_boost_val` 而非 `coin_reduce_val`。在现有数据中 `exp_boost` 和 `coin_reduce` 总是一起出现（学徒前缀），但如果未来有只带 `coin_reduce` 不带 `exp_boost` 的情况，会显示 `+0%`。

**修复建议**：确认是否为预期行为，或改为显示综合加成信息。

---

## 参数传递验证结果

| 函数 | 调用位置 | 参数匹配 | 结果 |
|------|---------|---------|------|
| `format_time(seconds: int)` | 第33行、第358行 | 传入 int ✅ | ✅ 正确 |
| `get_rod_prefix(prefix_id: str)` | 第36行、第404行 | 传入 rod["prefix_id"] ✅ | ✅ 正确 |
| `get_bait_prefix(prefix_id: str)` | 第95行、第411行 | 传入 bait prefix_id，且在非空保护块内 ✅ | ✅ 正确 |
| `scramble_text(text: str, intensity: float)` | 第258行 | 传入 str, 0.8 ✅ | ✅ 正确 |
| `add_pig_noise(text: str, chance=0.3)` | 第395行 | 传入 str，使用默认 chance ✅ | ✅ 正确 |
| `weighted_random_choice(items: list)` | 第242行 | 传入 ENCHANT_TICKETS ✅ | ✅ 正确 |
| `get_available_skills()` | 第267行 | 无参调用 ✅ | ✅ 正确 |

**参数传递结论：全部正确，未发现参数不匹配问题。**

---

## 边界条件验证结果

| 场景 | 位置 | 验证结果 |
|------|------|---------|
| 无鱼饵（总数=0） | 第57-58行 | ✅ 返回提示 |
| 当前鱼饵耗尽自动切换 | 第60-68行 | ✅ 遍历切换，无可用则返回 |
| 金币钓竿 coins<100 | 第50-51行 | ✅ 返回错误 |
| 金币钓竿 coins>=100 | 第49、54行 | ✅ 正常扣费 |
| 胡萝卜钓竿（不消耗鱼饵） | 第55、122、136行 | ✅ 多处判断保护 |
| 贪婪前缀金币不足降级 | 第112-115行 | ✅ 降级为普通模式 |
| 贪婪多倍鱼饵消耗 | 第119、122、136行 | ✅ 首次+额外次数均处理 |
| free_bait 事件跳过消耗 | 第122行 | ✅ 条件判断正确 |
| 远航金币/胡萝卜钓竿不消耗鱼饵 | 第171行 | ✅ 条件判断正确 |
| 远航鱼饵不足 break | 第172-173行 | ⚠️ 见 C3 |
| 潮汐触发不设置冷却 | 第208-210行 | ✅ 逻辑正确 |
| 迅捷失败设置半冷却 | 第87-88行 | ✅ 并保存用户数据 |
| 诅咒前缀丢失技能 | 第248-260行 | ✅ 过滤 cursed 自身 |
| 幸运方块添加/消除技能 | 第263-282行 | ✅ 两种分支处理 |
| 经验修补转化金币 | 第196-199行 | ✅ 先转化再加经验 |
| 学徒前缀经验/金币调整 | 第185-192、235行 | ✅ 两种组合情况处理 |

---

## 异步一致性验证

| 检查项 | 结果 |
|--------|------|
| `cmd_fish` 标记为 `async def` | ✅ |
| 内部所有 I/O 操作使用 `await` | ✅ (`storage.get_user`, `storage.save_user`, `storage.add_user_to_leaderboard`) |
| `async with self._get_user_lock()` 正确使用 | ✅ |
| 同步方法（`_do_fish_once`, `_generate_random_bait`, `_generate_random_rod`）未错误使用 `await` | ✅ |
| 早期 `return` 路径已保存数据（迅捷失败分支） | ✅ |
| 早期 `return` 路径未修改数据（冷却/资源不足分支） | ✅ |

---

## 并发安全验证

| 检查项 | 结果 |
|--------|------|
| 用户锁包裹整个 `cmd_fish` 方法体 | ✅ |
| 所有 `user` 数据修改在锁内完成 | ✅ |
| `storage.save_user()` 在锁内调用 | ✅ |
| 排行榜更新在锁内调用 | ✅ |
| 锁通过 `_get_user_lock()` 按需创建 | ✅ |
| 无锁外数据修改 | ✅ |

---

## 逻辑完整性验证

| 检查项 | 结果 |
|--------|------|
| 13种技能全部解析（swift/lucky/harvest/treasure/tide/exp_boost/voyage/mending/greedy/cursed/fail_chance/coin_reduce/lucky_block） | ✅ 第71-83行 |
| 4种幸运事件全部判定（double_fish/free_bait/bonus_bait/bonus_rod） | ✅ 第99-104行 |
| 冷却设置覆盖全部影响因素（迅捷/贪婪/远航/潮汐） | ✅ 第201-210行 |
| 结果汇总包含基础+远航所有渔获 | ✅ 第313行 |
| 稀有度分组包含全部4种（common/rare/legendary/mythic） | ✅ 第314行 |
| 神话鱼描述去重显示 | ✅ 第371-375行 |
| 金币钓竿 `_do_fish_once` 中 coin_bonus 计算 | ✅ 第418行 |
| 诅咒钓竿专属诅咒前缀替换 | ✅ 第460-463行 |
| 胡萝卜钓竿结果插入猪符号 | ✅ 第394-396行 |

---

## 总体评估

### 评分：7.5 / 10

**优点**：
1. 整体架构清晰，拆分后参数传递全部正确
2. 异步/并发处理规范，用户锁使用正确
3. 边界条件覆盖较全面（鱼饵耗尽、金币不足、特种钓竿等）
4. 13种技能和4种幸运事件处理完整
5. 冷却系统考虑了迅捷/贪婪/远航/潮汐全部因素

**需要修复的问题**：
1. **🔴 C1/C2**: 丰收和远航中 `_do_fish_once` 返回 None 的处理与基础循环不一致（应统一返回异常）
2. **🔴 C3**: 远航显示次数使用目标值而非实际值（应使用 `len(voyage_results)`）
3. **🟡 M1**: 删除金币钓竿的死代码检查（或改为检查 `remove_coins` 返回值）

**建议确认的问题**：
1. **L1**: 幸运方块技能池是否需要扩展至全部13种技能
2. **L2**: 金币钓竿迅捷失败时已扣金币是否为设计意图

修复 C1/C2/C3 后即可达到生产可用水平。
