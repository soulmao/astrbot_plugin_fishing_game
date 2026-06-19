<!-- From: d:\workspace\astrbot_plugin_fishing_game\AGENTS.md -->
# AGENTS.md — AstrBot 钓鱼游戏插件

> 本文件面向 AI 编码助手。假设读者对项目一无所知，请优先阅读本文件后再修改代码。

---

## 1. 项目概述

**AstrBot 钓鱼游戏插件**（`fishing_game`）是一个基于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 框架的群聊娱乐插件，提供完整的钓鱼经济系统。玩家在群聊中通过命令钓鱼、卖鱼、购买装备、赠送好友、拍卖物品、附魔钓竿、收集图鉴、解锁成就等。

- **插件名**: `fishing_game`
- **显示名称**: 钓鱼游戏
- **版本**: `V4.6.1`（`metadata.yaml`、`plugin.json`、`main.py` 中 `@register` 已统一）
- **作者**: AstrBot
- **依赖框架**: AstrBot >= 4.9.2
- **运行环境**: Python 3.9+
- **额外依赖**: `pydantic`（用于 LLM FunctionTool 的 dataclass 定义）

### 核心游戏循环

```
钓鱼 → 获得渔获 → 卖鱼赚金币 → 商店购买装备 → 钓更高品质的鱼 → 升级
```

### 关键元数据文件

| 文件 | 用途 |
|------|------|
| `metadata.yaml` | AstrBot 插件市场元数据（名称、版本、作者、兼容版本） |
| `plugin.json` | 插件基本信息 |
| `_conf_schema.json` | AstrBot 面板配置 Schema，支持 `fishing_cooldown`、`shop_refresh_cooldown`、拍卖行相关参数、模糊匹配阈值、管理员 UID 等 |

### 项目特点

- 命令式交互：所有命令通过 `main.py` 中 `@filter.command` 装饰器注册。
- LLM 集成：注册了 25 个 FunctionTool，支持自然语言多步 tool calling。
- 数据持久化：基于 AstrBot 的 K-V 存储（`star.get_kv_data` / `star.put_kv_data`）。
- 并发安全：每个用户独立 `asyncio.Lock`，赠送与拍卖购买场景按 user_id 排序加锁防止死锁。
- 定时任务：每日 0 点重置用户赠送次数，每小时检查拍卖行过期物品。
- 模糊命令入口：通过 `@filter.regex(r"^/(.+)$", priority=1)` 兜底识别 `/钓一下`、`/查看背包` 等口语化变体。
- 特殊文本效果：装备"无尽贪婪的"前缀钓竿时，返回文本会随金币增加受到黑色方块侵蚀；装备"胡萝卜钓竿"时文本会随机插入猪叫声。
- 游戏结果图片：精确命令、模糊命令和调用过本插件 FunctionTool 的最终 LLM 回复都会图片化，失败时回退文本。
- 背包图片：使用专用结构化模板，包含经验进度条、钓竿技能卡片，以及按库存总价值降序、最多六十种的标签式渔获展示。
- 市场图片：商店使用三列商品卡，拍卖行使用两列交易卡；列表和搜索结果保留价格、卖家、剩余时间与操作编号。
- 收藏图片：“我的鱼饵”完整展示效果与当前装备，图鉴展示稀有度进度和最近点亮，成就按类别完整展示全部目标。
- 钓鱼图片：普通钓鱼、贪婪挑战、收杆结算及失败状态使用专用结构化模板。

---

## 2. 技术栈与运行架构

### 2.1 技术栈

- **语言**: Python 3.9+
- **框架**: AstrBot >= 4.9.2（插件继承 `astrbot.api.star.Star`）
- **依赖库**:
  - `pydantic`（`Field`、`pydantic.dataclasses.dataclass`）
  - `astrbot` 相关 API（`filter`, `AstrMessageEvent`, `Context`, `Star`, `register`, `logger`）
  - 标准库：`asyncio`, `time`, `random`, `uuid`, `datetime`, `typing`, `difflib`

### 2.2 运行方式

本项目不是独立运行的应用，而是作为 AstrBot 插件加载：

1. 将仓库克隆到 AstrBot 的 `plugins/` 目录：
   ```bash
   cd AstrBot/plugins
   git clone https://github.com/soulmao/astrbot_plugin_fishing_game.git
   ```
2. 重启 AstrBot 或通过 AstrBot 管理面板加载插件。
3. 在 AstrBot 面板配置插件参数（冷却时间、拍卖行参数、模糊匹配阈值、管理员 UID 等）。

### 2.3 架构分层

```
┌─────────────────────────────────────────────┐
│ 表现层 (main.py)                             │
│  - FishingGamePlugin（Star 子类）            │
│  - @filter.command 命令注册与统一路由        │
│  - LLM FunctionTool 注册（25 个）            │
│  - 定时任务调度（每日刷新、拍卖行过期检查）  │
│  - LLM 彩色结果图 / 贪婪方块 / 胡萝卜猪叫声  │
│  - 模糊命令入口（@filter.regex 兜底）        │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│ 命令层 (command_*.py)                        │
│  继承 CommandBase，按功能域拆分：            │
│  - command_fishing.py      钓鱼核心          │
│  - command_equipment.py    装备管理          │
│  - command_economy.py      经济/商店         │
│  - command_social.py       赠送/社交         │
│  - command_auction.py      拍卖行            │
│  - command_enchant.py      附魔/升级         │
│  - command_achievements.py 成就系统          │
│  - command_info.py         信息查询/帮助     │
│  - command_admin.py        管理员命令        │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│ 服务层                                        │
│  - storage.py    StorageManager（K-V 持久化）│
│  - utils.py      纯工具函数                  │
│  - commands_base.py CommandBase 基类         │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│ 模型层 (models.py)                           │
│  - UserData 玩家数据模型                      │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│ 数据层 (fish_data.py)                        │
│  - 鱼类/前缀/钓竿/鱼饵/等级/成就等静态配置   │
│  - 查询函数与价值计算公式                    │
└─────────────────────────────────────────────┘
```

### 2.4 关键运行流程

1. **插件加载**: AstrBot 调用 `FishingGamePlugin.__init__()`，初始化配置、StorageManager、各命令模块、命令映射 `_cmd_map`、注册 LLM 工具、启动定时任务。
2. **命令触发**: 用户发送 `/钓鱼` 等命令，AstrBot 路由到 `main.py` 中对应方法，再通过 `_route_cmd()` 分派到具体命令模块的方法。
3. **业务处理**: 命令模块通过 `StorageManager` 读写 `UserData`，处理完后返回字符串结果。
4. **LLM 调用**: LLM 通过 FunctionTool 调用 `_cmd_with_scramble()`，同样路由到 `_cmd_map` 中对应方法。
5. **模糊入口**: 用户输入 `/钓一下` 等非精确命令时，`cmd_fuzzy_entry()` 使用 `difflib.get_close_matches` 匹配关键词库，命中后调用 `_route_cmd()` 并阻止事件继续传播。
6. **插件卸载**: `terminate()` 取消定时任务。

---

## 3. 代码组织与模块说明

### 3.1 文件清单与职责

| 文件 | 行数（约） | 职责 |
|------|-----------|------|
| `__init__.py` | 4 | Python 包入口，导出 `FishingGamePlugin` |
| `main.py` | 604 | 插件生命周期、命令路由、LLM 工具注册、定时任务、模糊命令入口 |
| `commands_base.py` | 18 | `CommandBase` 基类，提供用户级锁 |
| `command_fishing.py` | 548 | 钓鱼核心（随机算法、技能特效、幸运事件、签到） |
| `command_equipment.py` | 124 | 钓竿/鱼饵的查看与装备切换 |
| `command_economy.py` | 239 | 卖鱼、商店、购买、刷新商店、商店升级 |
| `command_social.py` | 226 | 赠送金币/渔获/鱼饵/钓竿，含事务回滚 |
| `command_auction.py` | 558 | 拍卖行浏览/搜索/上架/出售/取消/购买（支持钓竿/鱼饵/渔获/附魔券/道具券） |
| `command_enchant.py` | 285 | 随机附魔、技能升级、定向附魔 |
| `command_achievements.py` | 57 | 成就列表与进度查询 |
| `command_info.py` | 420 | 帮助、背包、等级、图鉴、冷却、排行榜 |
| `command_admin.py` | 492 | 管理员查看/加金币/设经验/加钓竿/全服发放/日志审计 |
| `fish_data.py` | 456 | 所有静态游戏数据与查询/计算函数 |
| `models.py` | 648 | `UserData` 数据模型（属性访问器、业务方法、数据迁移） |
| `storage.py` | 170 | `StorageManager` K-V 持久化、排行榜、拍卖行数据 |
| `utils.py` | 346 | 格式化、价值计算、商店生成、加权随机等纯工具函数 |
| `llm_tools.py` | 660 | 25 个 FunctionTool 的 dataclass 定义 |
| `fish_data_admin.html` | - | 独立 HTML 数据管理台（静态文件，未在代码中引用） |
| `_conf_schema.json` | 44 | 插件配置 Schema |
| `metadata.yaml` | 6 | AstrBot 插件元数据 |
| `plugin.json` | 6 | 插件基本信息 |

### 3.2 命令命名约定

- 命令方法统一以 `cmd_` 前缀命名（如 `cmd_fish`、`cmd_sell`）。
- `main.py` 中的 `_cmd_map` 字典将命令名映射到 `(模块实例, 方法名)`。
- 中文命令为主，英文为别名（通过 `@filter.command(alias={...})` 注册）。
- 模糊命令入口 `_cmd_map` 与精确命令共享同一套业务方法。

### 3.3 数据存储约定

- 用户数据 Key: `fishing_user_{user_id}`，值为完整 JSON 字典。
- 全局用户列表 Key: `fishing_all_user_ids`。
- 排行榜 Key: `fishing_leaderboard`（旧数据兼容，但实时排行通过遍历所有用户计算）。
- 拍卖行列表 Key: `fishing_auctions`。
- 管理员审计日志 Key: `fishing_admin_logs`。
- 冷却时间使用 Unix 时间戳存储，避免离线计时偏差。

---

## 4. 开发约定与代码风格

### 4.1 语言与注释

- **所有代码注释、文档字符串、错误提示、用户返回文本均使用中文**。
- 模块顶部使用 `"""模块说明"""` 风格文档字符串。
- 类和方法使用 `"""说明"""` 文档字符串。

### 4.2 异步编程

- 所有涉及 I/O 的操作（存储读写、定时任务）均为 `async`/`await`。
- 命令方法通常为 `async def cmd_xxx(self, event, ...) -> str`。
- 用户级并发控制使用 `async with self._get_user_lock(user_id)`。

### 4.3 命令开发模板

新增命令时，按以下模式：

1. 在对应 `command_*.py` 中新增 `async def cmd_xxx(self, event, ...)` 方法。
2. 在 `main.py` 的 `_build_cmd_map()` 中注册命令映射。
3. 在 `main.py` 中新增 `@filter.command("命令名", alias={...})` 装饰的方法，调用 `_route_cmd()`。
4. 如需 LLM 支持，在 `llm_tools.py` 中新增 FunctionTool 子类，并在 `_register_llm_tools()` 中注册。
5. 如需模糊入口支持，在 `_build_fuzzy_keywords()` 和 `_build_exact_commands()` 中添加关键词。
6. 如需带参数类型转换的模糊入口，在 `_build_cmd_arg_types()` 中声明参数类型。
7. 更新 `command_info.py` 的 `cmd_help()` 帮助文本。

### 4.4 数据模型使用

- 通过 `await self.storage.get_user(user_id)` 获取 `UserData`。
- 修改数据后必须调用 `await self.storage.save_user(user)` 持久化。
- 不要在命令方法中直接操作 `_data` 字典，优先使用 `UserData` 提供的方法（如 `add_coins`、`add_exp`、`add_fish`）。
- 钓竿使用 `instance_id` 唯一标识，支持同名不同实例的钓竿。

### 4.5 并发与锁

- 单用户操作：`async with self._get_user_lock(user_id)`。
- 涉及两个用户的操作（赠送、拍卖购买）：按 `sorted([user_id_a, user_id_b])` 顺序加锁，防止死锁。
- 拍卖行全局列表操作在 `StorageManager` 中使用 `self._auction_lock`。

### 4.6 错误处理

- 业务错误直接返回中文提示字符串。
- 存储异常需要尝试回滚（参考 `command_social.py` 的赠送逻辑和 `command_auction.py` 的购买逻辑）。
- 定时任务需要捕获 `asyncio.CancelledError` 以正确退出。

### 4.7 配置读取

配置在 `FishingGamePlugin.__init__()` 中读取并保存到实例属性：

```python
self.fishing_cooldown = self.config.get("fishing_cooldown", 4 * 3600)
self.shop_refresh_cooldown = self.config.get("shop_refresh_cooldown", 1 * 3600)
self.auction_default_price_percent = self.config.get("auction_default_price_percent", 0.30)
self.auction_price_range_percent = self.config.get("auction_price_range_percent", 0.30)
self.auction_duration_hours = self.config.get("auction_duration_hours", 24)
self.fuzzy_match_threshold = self.config.get("fuzzy_match_threshold", 0.6)
self.llm_result_image_enabled = self.config.get("llm_result_image_enabled", True)
admin_uids_str = self.config.get("admin_uids", "")
self.admin_uids = set(uid.strip() for uid in admin_uids_str.split(",") if uid.strip())
```

---

## 5. 构建与测试

### 5.1 构建

本项目无需构建。它是纯 Python 源码插件，由 AstrBot 动态加载。

### 5.2 本地验证

由于没有单元测试，验证方式主要为：

1. **语法检查**:
   ```bash
   python -m py_compile __init__.py main.py commands_base.py command_*.py fish_data.py models.py storage.py utils.py llm_tools.py
   ```

2. **导入检查**（需要在安装了 AstrBot 和 pydantic 的环境中）：
   ```bash
   python -c "from .main import FishingGamePlugin"
   ```

3. **实际运行验证**: 将插件放入 AstrBot 的 `plugins/` 目录，启动 AstrBot，在群聊中测试命令。

### 5.3 测试策略

**当前项目没有单元测试、集成测试或 CI/CD 配置。**

建议新增测试时遵循以下原则：

- 由于项目强依赖 AstrBot 框架，单元测试需要大量 mock `Context`、`AstrMessageEvent`、`Star.get_kv_data`/`put_kv_data` 等接口。
- 优先对纯工具函数（`utils.py`、`fish_data.py` 中的计算函数）进行单元测试，这些函数无外部依赖。
- 对命令逻辑的测试建议使用 pytest + unittest.mock 模拟 event 和 storage。
- 推荐测试目录结构：
  ```
  tests/
  ├── __init__.py
  ├── test_utils.py
  ├── test_fish_data.py
  ├── test_models.py
  └── test_commands.py
  ```

---

## 6. 配置说明

`_conf_schema.json` 中定义的可配置项：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `fishing_cooldown` | int | 14400 | 钓鱼冷却时间（秒），默认 4 小时 |
| `shop_refresh_cooldown` | int | 3600 | 商店手动刷新冷却时间（秒），默认 1 小时 |
| `auction_default_price_percent` | float | 0.30 | 拍卖行默认上架价格占物品价值的比例 |
| `auction_price_range_percent` | float | 0.30 | 拍卖行价格浮动范围 |
| `auction_duration_hours` | int | 24 | 拍卖物品保留时长（小时） |
| `fuzzy_match_threshold` | float | 0.6 | 模糊命令匹配阈值，0-1 之间 |
| `llm_result_image_enabled` | bool | true | 将游戏命令及 LLM 工具结果渲染为彩色图片 |
| `admin_uids` | string | "" | 管理员 UID 列表，英文逗号分隔 |

---

## 7. 安全注意事项

### 7.1 并发安全

- 用户级锁只能保证同一用户的请求串行，不能防止不同用户并发修改共享数据（如拍卖行列表）。拍卖行等全局数据在 `StorageManager` 中使用独立锁。
- 不要在锁内执行耗时操作（如网络请求），避免阻塞其他用户。

### 7.2 数据安全

- 所有用户数据通过 AstrBot 的 K-V 存储持久化，不直接读写文件系统。
- 用户 ID 来自 `event.get_sender_id()`，通常由平台提供，不要信任用户输入的 `@用户` 字符串，需通过 `extract_target_user_id()` 清洗。

### 7.3 事务回滚

- 赠送系统实现了两阶段提交与回滚：先扣减发送方并保存，再给接收方增加并保存。如果接收方保存失败，尝试回滚发送方。
- 拍卖购买也按 buyer/seller 排序加锁，先扣金币再转移物品。
- 修改类似跨用户事务逻辑时，必须保持按 user_id 排序加锁的顺序。

### 7.4 输入校验

- 命令参数（如商品编号、钓竿编号、数量）需要校验边界。
- 金币、经验等数值操作需要确保不会出现负数。
- 管理员命令需要校验操作者 UID 是否在 `admin_uids` 配置中。

### 7.5 定时任务

- `_daily_refresh_loop()` 和 `_auction_check_loop()` 在 `terminate()` 中取消。
- 定时任务异常后会等待 5 分钟重试，避免无限循环崩溃。

### 7.6 管理员审计

- 管理员命令（查看、加金币、设经验、加钓竿、删钓竿、清冷却、全服发放、物品ID、清空日志）会写入 `fishing_admin_logs`。
- 日志最多保留最近 100 条。

---

## 8. 常见修改指南

### 8.1 新增一种鱼

1. 在 `fish_data.py` 的 `FISH_TYPES` 列表中添加新鱼定义。
2. 如果新增前缀，在 `FISH_PREFIXES` 中添加。
3. 更新 `command_info.py` 中的帮助文本（可选）。

### 8.2 新增钓竿技能

1. 在 `fish_data.py` 的 `ROD_SKILL_DESCRIPTIONS` 中添加技能图标和中文名。
2. 在 `utils.py` 的 `get_available_skills()` 中决定是否允许附魔获得。
3. 在 `command_fishing.py` 中实现技能效果。
4. 在 `utils.py` 的 `format_rod_skills()` 中处理数值显示格式。

### 8.3 新增命令

参考第 4.3 节的命令开发模板，同时需要：
- 更新 `command_info.py` 的 `cmd_help()` 帮助文本。
- 如需 LLM 调用，新增 FunctionTool 并在描述中说明触发时机。
- 如需模糊入口，更新 `_build_fuzzy_keywords()`、`_build_exact_commands()` 和 `_build_cmd_arg_types()`。

### 8.4 修改经济数值

- 鱼售价：修改 `fish_data.py` 中 `FISH_PREFIXES` 的 `price_multiplier` 或 `FISH_TYPES` 的 `base_price`。
- 商店价格：修改 `fish_data.py` 中 `SHOP_ITEMS`。
- 附魔价格：修改 `fish_data.py` 中 `ENCHANT_CONFIG` 或在 `utils.py` 的 `calc_enchant_price()` 中调整。
- 商店升级价格：修改 `fish_data.py` 中 `SHOP_UPGRADE_CONFIG`。

### 8.5 修改管理员权限

- 管理员 UID 通过 AstrBot 面板 `admin_uids` 配置项设置，多个 UID 用英文逗号分隔。
- 代码中通过 `AdminCommands._check_admin()` 检查 `event.get_sender_id() in self.star.admin_uids`。

---

## 9. 依赖与外部资源

- **AstrBot**: 必须运行在 AstrBot 框架中。
- **pydantic**: 用于 LLM FunctionTool 的 dataclass 定义。
- **Python 版本**: 3.9 或更高。

没有 `requirements.txt`、`pyproject.toml`、`setup.py` 等包管理文件。依赖通过 AstrBot 环境或用户手动安装。

---

## 10. 注意事项

- 本项目**没有测试套件**，修改后请通过实际运行或至少语法检查验证。
- 本项目**没有 CI/CD 流程**。
- `.gitignore` 已存在，包含 Python、IDE、环境、OS 常见忽略项。
- `fish_data_admin.html` 是独立的静态 HTML 管理台，当前代码中未引用，修改前端数据展示时可以单独维护。
- 不要修改 `__pycache__` 中的文件，那是 Python 编译缓存。
- `main.py` 与 `metadata.yaml`/`plugin.json` 中的版本号不一致，发布前建议统一。
