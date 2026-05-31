# 🎣 AstrBot 钓鱼游戏插件

> 基于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 框架的群聊钓鱼游戏插件，支持钓鱼、背包、商店、装备、赠送、排行榜、图鉴等完整经济系统。

[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.9.2-blue)](https://github.com/AstrBotDevs/AstrBot)
[![Version](https://img.shields.io/badge/version-1.0.0-green)]()
[![License](https://img.shields.io/badge/license-MIT-orange)]()

---

## 📋 目录

- [功能特性](#-功能特性)
- [安装方式](#-安装方式)
- [配置说明](#-配置说明)
- [游戏玩法](#-游戏玩法)
- [命令列表](#-命令列表)
- [LLM 工具支持](#-llm-工具支持)
- [数据体系](#-数据体系)
- [项目结构](#-项目结构)
- [技术实现](#-技术实现)
- [依赖](#-依赖)

---

## ✨ 功能特性

| 系统 | 说明 |
|------|------|
| 🎣 **钓鱼系统** | 随机鱼种 × 随机前缀组合，4 种稀有度（常见/稀有/传说/神话），共 18 种鱼类 + 14 种前缀 |
| 💰 **经济系统** | 金币获取、卖鱼变现、商店购买，完整的经济闭环 |
| 🔧 **钓竿系统** | 5 种基础钓竿（木/竹/碳纤维/金色/神级）+ 11 种前缀，组合出 55 种钓竿 |
| 🔱 **技能词条** | 高品质钓竿自带 6 种技能：⚡迅捷、🍀幸运、🌾丰收、💎寻宝、🌊潮汐、✨神慧 |
| 🪤 **鱼饵系统** | 4 种基础鱼饵 + 9 种前缀，影响经验加成和品质加成 |
| 📊 **等级系统** | 7 个等级（新手→传说渔夫），升级解锁更强装备和更高稀有度鱼类 |
| 🏪 **商店系统** | 随机刷新 6 件商品，支持刷新券和金币刷新（冷却 1 小时） |
| 🎁 **赠送系统** | 跨用户赠送金币/渔获/鱼饵，每日限 10 次，含防死锁和事务回滚 |
| 🏆 **排行榜** | 钓鱼次数排名，展示前 10 名及个人排名 |
| 📖 **图鉴系统** | 追踪已收集的鱼类 × 前缀组合，按稀有度分类统计 |
| 🤖 **LLM 集成** | 16 个 FunctionTool，支持自然语言多步工具调用 |
| ⏰ **每日刷新** | 每天 0 点自动重置所有用户的赠送次数 |

---

## 📦 安装方式

### 方式一：AstrBot 插件市场（推荐）

在 AstrBot 面板的插件市场中搜索 `fishing_game` 并安装。

### 方式二：手动安装

```bash
# 进入 AstrBot 插件目录
cd AstrBot/plugins

# 克隆本仓库
git clone https://github.com/soulmao/astrbot_plugin_fishing_game.git

# 重启 AstrBot 或通过面板加载插件
```

---

## ⚙️ 配置说明

在 AstrBot 面板的插件配置中可设置以下参数：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `fishing_cooldown` | `int` | `14400` | 每次钓鱼后的冷却时间（秒），默认 4 小时 |
| `shop_refresh_cooldown` | `int` | `3600` | 手动刷新商店的冷却时间（秒），默认 1 小时 |

---

## 🎮 游戏玩法

### 新手上路

新玩家初始获得：
- 💰 **100 金币**
- 🎣 **普通的木制钓竿** ×1
- 🪤 **普通的蚯蚓** ×10

### 核心循环

```
钓鱼 → 获得渔获 → 卖鱼赚金币 → 商店购买装备 → 钓更高品质的鱼 → 升级
```

### 钓鱼机制

每次钓鱼消耗 1 个鱼饵，随机获得：
- **鱼种**（18 种）+ **前缀**（14 种）组合命名（如 "金色的龙鱼"）
- 售价 = 鱼种基础价 × 前缀价格倍率
- 经验 = 10 × 钓竿倍率 × 鱼饵倍率
- 高品质钓竿可提升稀有鱼权重

**稀有度与等级限制：**

| 稀有度 | 解锁等级 | 钓竿要求 | 示例 |
|--------|----------|----------|------|
| 🔹 常见 | Lv.1+ | 无 | 小杂鱼、鲫鱼、鲤鱼、草鱼 |
| 🔷 稀有 | Lv.2+ | 无 | 鲈鱼、鳜鱼、鳟鱼、金鱼 |
| ⭐ 传说 | Lv.5+ | 无 | 龙鱼、锦鲤 |
| 🌟 神话 | Lv.6+ | 金色钓竿以上 | 美人鱼、鲲、蛟龙、利维坦 |

### 钓竿技能词条

高品质前缀自带技能词条，数值随前缀品质提升：

| 技能 | 图标 | 效果 |
|------|------|------|
| 迅捷 | ⚡ | 减少钓鱼冷却时间 |
| 幸运 | 🍀 | 提升幸运事件触发概率（双倍钓鱼、免费鱼饵、额外奖励） |
| 丰收 | 🌾 | 概率额外钓到一条鱼 |
| 寻宝 | 💎 | 概率获得额外金币 |
| 潮汐 | 🌊 | 概率本次钓鱼无需冷却 |
| 神慧 | ✨ | 获得额外经验加成 |

### 幸运事件

钓鱼时有概率触发以下幸运事件（受"幸运"技能加成）：

- ✨ **双倍钓鱼** — 一次钓两条鱼
- ✨ **不消耗鱼饵** — 本次钓鱼免费
- 🎁 **幸运奖励** — 随机获得鱼饵
- 🎁 **超级幸运** — 随机获得钓竿

### 古龙收藏系列 🐉

稀有收藏级系列，仅高级玩家可获得：

- **古龙收藏钓竿**：极高幸运与全技能加成
- **古龙收藏鱼类**：售价远超普通传说鱼（额外 20% 收藏家溢价）
- **古龙收藏鱼饵**：大幅加成随机事件触发率

### 等级体系

| 等级 | 称号 | 所需经验 | 解锁 |
|------|------|----------|------|
| Lv.1 | 新手渔夫 | 0 | 基础钓竿和鱼饵 |
| Lv.2 | 入门渔夫 | 100 | 稀有鱼类、竹制钓竿、新鲜鱼饵 |
| Lv.3 | 熟练渔夫 | 300 | 银色/红色前缀、刷新券 |
| Lv.4 | 老练渔夫 | 600 | 精美前缀、香料饵 |
| Lv.5 | 专家渔夫 | 1,000 | 传说鱼类、金色前缀 |
| Lv.6 | 大师渔夫 | 2,000 | 神话鱼类、金色钓竿、传说饵 |
| Lv.7 | 传说渔夫 | 5,000 | 神灵前缀、神级钓竿、古龙收藏系列 |

---

## 📋 命令列表

### 核心命令

| 命令 | 别名 | 参数 | 说明 |
|------|------|------|------|
| `/钓鱼` | `/fish` | — | 消耗 1 个鱼饵钓鱼，有冷却时间 |
| `/背包` | `/bag` | — | 查看金币、经验、渔获、鱼饵、钓竿等信息 |
| `/卖鱼` | `/sell` | `[ID\|全部]` | 出售指定渔获或全部渔获，获得金币和经验 |
| `/商店` | `/shop` | — | 查看当前可购买的钓竿和鱼饵（随机 6 件） |
| `/购买` | `/buy` | `<编号> [数量]` | 从商店购买物品 |
| `/刷新商店` | `/shop_refresh` | — | 手动刷新商店（消耗 50 金币或刷新券，冷却 1 小时） |

### 装备命令

| 命令 | 别名 | 参数 | 说明 |
|------|------|------|------|
| `/我的钓竿` | `/myrods` | — | 查看拥有的所有钓竿 |
| `/装备钓竿` | `/equip` | `<编号>` | 切换当前使用的钓竿 |
| `/我的鱼饵` | `/mybaits` | — | 查看拥有的所有鱼饵 |
| `/装备鱼饵` | `/equip_bait` | `<编号>` | 切换当前使用的鱼饵 |

### 信息命令

| 命令 | 别名 | 参数 | 说明 |
|------|------|------|------|
| `/等级` | `/level` | — | 查看当前等级和经验进度 |
| `/冷却` | `/cd` | — | 查看钓鱼和商店刷新冷却状态 |
| `/排行榜` | `/rank` | — | 查看钓鱼次数排行榜 |
| `/图鉴` | `/collection` | — | 查看已收集的鱼类图鉴进度 |
| `/帮助` | `/help` | — | 查看完整帮助信息 |

### 社交命令

| 命令 | 别名 | 参数 | 说明 |
|------|------|------|------|
| `/赠送` | `/give` | `<@用户> <类型> [ID] [数量]` | 赠送金币/渔获/鱼饵给其他用户，每日限 10 次 |

**赠送示例：**
- `/赠送 @好友 coins 100` — 赠送 100 金币
- `/赠送 @好友 fish fish_003 2` — 赠送 2 条鲤鱼
- `/赠送 @好友 bait bait_001 5` — 赠送 5 条蚯蚓

---

## 🤖 LLM 工具支持

插件注册了 16 个 **FunctionTool**，支持通过自然语言与钓鱼游戏交互，且支持多步工具调用。

| 工具名 | 函数名 | 描述 |
|--------|--------|------|
| 钓鱼帮助 | `fishing_help` | 查看游戏帮助 |
| 钓鱼 | `fishing_fish` | 执行钓鱼操作 |
| 商店 | `fishing_shop` | 查看商店商品 |
| 背包 | `fishing_bag` | 查看背包信息（含物品 ID） |
| 卖鱼 | `fishing_sell` | 出售渔获换金币 |
| 等级 | `fishing_level` | 查看等级进度 |
| 冷却 | `fishing_cd` | 查看冷却状态 |
| 购买 | `fishing_buy` | 从商店购买物品 |
| 赠送 | `fishing_give` | 赠送物品给其他用户 |
| 排行榜 | `fishing_rank` | 查看排行榜 |
| 我的钓竿 | `fishing_myrods` | 查看拥有的钓竿 |
| 装备钓竿 | `fishing_equip` | 切换装备钓竿 |
| 我的鱼饵 | `fishing_mybaits` | 查看拥有的鱼饵 |
| 装备鱼饵 | `fishing_equip_bait` | 切换装备鱼饵 |
| 刷新商店 | `fishing_shop_refresh` | 手动刷新商店 |
| 图鉴 | `fishing_collection` | 查看图鉴收集进度 |

> 💡 用户可以直接用自然语言操作，如 "帮我钓一次鱼"、"看看我的背包有什么"、"卖掉所有的鱼" 等。

---

## 📊 数据体系

### 鱼类（18 种）

- **常见**（8 种）：小杂鱼、鲫鱼、鲤鱼、草鱼、鲢鱼、鳙鱼、罗非鱼、黑鱼
- **稀有**（4 种）：鲈鱼、鳜鱼、鳟鱼、金鱼
- **传说**（2 种）：龙鱼、锦鲤
- **神话**（5 种）：美人鱼、鲲、蛟龙、利维坦、九尾龟

### 钓竿（5 种基础 × 11 种前缀 = 55 种组合）

| 基础钓竿 | 品质 | 经验倍率 | 稀有度加成 |
|----------|------|----------|------------|
| 木制钓竿 | 普通 | ×1.0 | 0% |
| 竹制钓竿 | 精良 | ×1.2 | +5% |
| 碳纤维钓竿 | 稀有 | ×1.5 | +10% |
| 金色钓竿 | 传说 | ×2.0 | +20% |
| 神级钓竿 | 神话 | ×3.0 | +35% |

### 鱼饵（4 种基础 × 9 种前缀 = 36 种组合）

| 基础鱼饵 | 品质 | 经验倍率 | 品质加成 |
|----------|------|----------|----------|
| 蚯蚓 | 普通 | ×1.0 | 0% |
| 饵料 | 精良 | ×1.3 | +5% |
| 香料饵 | 稀有 | ×1.5 | +10% |
| 传说饵 | 传说 | ×2.0 | +20% |

---

## 📁 项目结构

```
astrbot_plugin_fishing_game/
├── __init__.py          # Python 包标识
├── main.py              # 插件入口，注册命令和 LLM 工具，调度每日刷新
├── commands.py          # 命令处理器，所有业务逻辑（钓鱼、背包、商店、赠送等）
├── fish_data.py         # 数据定义（鱼类、前缀、钓竿、鱼饵、等级、商店商品配置）
├── storage.py           # 用户数据模型（UserData）和存储管理器（StorageManager）
├── llm_tools.py         # 16 个 LLM FunctionTool 定义
├── _conf_schema.json    # 插件配置 Schema
├── metadata.yaml        # AstrBot 插件元数据
└── plugin.json          # 插件基本信息
```

| 文件 | 行数 | 职责 |
|------|------|------|
| `main.py` | 225 | 插件生命周期、命令路由、LLM 工具注册、每日定时任务 |
| `commands.py` | 1154 | 核心业务逻辑，涵盖 18 个命令的完整实现 |
| `fish_data.py` | 189 | 所有游戏数据的静态定义和辅助查询函数 |
| `storage.py` | 385 | UserData 模型（属性/方法）+ StorageManager（K-V 持久化） |
| `llm_tools.py` | 392 | 16 个 FunctionTool 的 dataclass 定义 |

---

## 🔧 技术实现

### 整体架构

```
┌─────────────────────────────────────────────┐
│                   main.py                    │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │ 命令路由层   │  │ LLM FunctionTool 注册 │  │
│  │ @filter      │  │ 16 个工具函数        │  │
│  └──────┬───────┘  └──────────┬───────────┘  │
│         │                     │              │
│  ┌──────▼─────────────────────▼──────────┐   │
│  │        commands.py                     │   │
│  │  FishingGameCommands（业务逻辑层）     │   │
│  │  ┌──────────────────────────────────┐  │   │
│  │  │  asyncio.Lock 用户级并发控制     │  │   │
│  │  │  _get_user_lock(user_id)         │  │   │
│  │  └──────────────────────────────────┘  │   │
│  └──────────────┬────────────────────────┘   │
│                 │                            │
│  ┌──────────────▼────────────────────────┐   │
│  │         storage.py                     │   │
│  │  ┌────────────┐  ┌──────────────────┐ │   │
│  │  │  UserData  │  │ StorageManager    │ │   │
│  │  │  数据模型  │  │ AstrBot KV 持久化 │ │   │
│  │  └────────────┘  └──────────────────┘ │   │
│  └──────────────┬────────────────────────┘   │
│                 │                            │
│  ┌──────────────▼────────────────────────┐   │
│  │         fish_data.py                   │   │
│  │  静态数据定义 + 辅助查询函数           │   │
│  └───────────────────────────────────────┘   │
│                                              │
│  ⏰ asyncio.create_task(_daily_refresh)      │
│     每日 0 点自动重置赠送次数                 │
└─────────────────────────────────────────────┘
```

### 数据模型（`UserData`）

`UserData` 是玩家数据的核心模型，完全基于 `dict` 存储，提供属性访问器和方法封装：

```python
class UserData:
    _data = {
        "user_id": str,         # 用户唯一标识
        "coins": 100,           # 金币
        "exp": 0,               # 经验值
        "level": 1,             # 等级（1-7）
        "owned_rods": [...],    # 拥有的钓竿列表 [{base_id, prefix_id}]
        "current_rod": {...},   # 当前装备的钓竿
        "baits": [...],         # 鱼饵列表 [{base_id, prefix_id, count}]
        "current_bait": {...},  # 当前装备的鱼饵
        "fish_inventory": [...],# 渔获背包 [{fish_id, prefix_id, count}]
        "fish_cooldown": 0,     # 钓鱼冷却时间戳
        "shop_refresh_cd": 0,   # 商店刷新冷却时间戳
        "daily_give_count": 0,  # 今日已赠送次数
        "daily_give_reset": "", # 赠送次数重置日期
        "total_fish_count": 0,  # 累计钓鱼次数（排行榜用）
        "collection": {},       # 图鉴 {fish_id#prefix_id: {count, first_at}}
        "items": [],            # 道具列表 [{id, count}]（如刷新券）
    }
```

**设计要点：**
- 使用 **属性装饰器**（`@property`）为常用字段提供类型化的 getter
- 渔获/鱼饵/钓竿均按 **基础类型 + 前缀** 组合存储，支持灵活扩展
- 冷却使用 **Unix 时间戳** 而非倒计时数值，避免离线期间的计时偏差
- 等级通过 `_calc_level()` 方法从经验值**动态计算**，数据一致性更强

### 持久化存储（`StorageManager`）

基于 AstrBot 框架的 **K-V 存储** 实现数据持久化：

```python
class StorageManager:
    async def get_user(user_id) -> UserData  # 读取用户数据，不存在则自动创建
    async def save_user(user)                # 保存用户数据到 KV Store
    async def user_exists(user_id) -> bool   # 检查用户是否存在
```

**存储策略：**
- **单用户数据**：Key 格式 `fishing_user_{user_id}`，value 为完整的 JSON 字典
- **全局用户列表**：Key `fishing_all_user_ids`，记录所有已注册用户 ID，用于每日刷新遍历
- **排行榜**：Key `fishing_leaderboard`，存储 `{user_id: {count, name, level}}` 字典，每次钓鱼后增量更新
- **懒初始化**：用户首次操作时才创建数据，避免预加载开销
- **老用户兼容**：`get_user()` 自动将已存在但未注册到全局列表的老用户补录

### 并发控制

每个用户独立持有 `asyncio.Lock`，确保同一用户的多个请求**串行执行**：

```python
class FishingGameCommands:
    user_locks: dict[str, asyncio.Lock] = {}

    def _get_user_lock(self, user_id) -> asyncio.Lock:
        # 按需创建锁，每个用户一把锁
        ...

    async def cmd_fish(self, event):
        async with self._get_user_lock(user_id):  # 同一用户排队执行
            user = await self.storage.get_user(user_id)
            # ... 业务逻辑 ...
            await self.storage.save_user(user)
```

**赠送场景的死锁防护：**
```python
# 按 user_id 字母序排序加锁，防止 A→B 和 B→A 同时操作产生死锁
first_id, second_id = sorted([sender_id, receiver_id])
async with lock(first_id):
    async with lock(second_id):
        # ... 赠送逻辑 ...
```

**事务回滚：** 赠送操作采用 try/except 回滚机制——先扣发送方 → 保存 → 如果接收方保存失败则自动撤销发送方数据。

### 钓鱼随机算法

采用**加权随机选择**（Weighted Random Selection），实现多层级抽奖：

```python
def _do_fish_once(user, rod, bait):
    # 1. 构建鱼种候选池（按等级和钓竿过滤 + 稀有度加权）
    fish_pool = []
    for fish in FISH_TYPES:
        if 满足等级和钓竿要求:
            weight = fish["weight"] * (1 + rod稀有度加成 + bait品质加成)
            fish_pool.append((fish, weight))
    
    # 2. 加权随机选择鱼种
    selected_fish = random.choices(fish_pool, weights=[...], k=1)[0]
    
    # 3. 构建前缀候选池（按等级和钓竿过滤）
    prefix_pool = [prefix for prefix in PREFIXES if 满足条件]
    
    # 4. 加权随机选择前缀
    selected_prefix = random.choices(prefix_pool, weights=[...], k=1)[0]
    
    # 5. 计算最终售价和经验
    price = fish.base_price × prefix.price_multiplier
    exp = 10 × rod.exp_multiplier × bait.exp_multiplier
```

**关键设计：**
- 稀有度加成（`rarity_bonus`）仅作用于**稀有及以上**鱼类，不影响常见鱼的权重
- 古龙收藏前缀（`pref_014`）在卖鱼时额外享受 **1.2 倍收藏家溢价**
- 神话鱼（美人鱼、鲲等）需要**金色钓竿以上**且等级 **Lv.6+** 才能入池

### 技能系统

钓竿前缀的 `skills` 字段为字典，Key 对应技能枚举，Value 为 0-1 的加成系数：

```python
# 示例：传说的钓竿前缀
"skills": {
    "swift": 0.50,      # 冷却减少 50%
    "lucky": 0.20,      # 幸运事件 +20%
    "harvest": 0.25,    # 丰收概率 25%
    "treasure": 0.20,   # 寻宝概率 20%
    "tide": 0.05,       # 潮汐概率 5%
    "exp_boost": 0.30,  # 经验加成 30%
}
```

**技能效果叠加逻辑：**
- 鱼饵的 `event_bonus`（仅古龙收藏鱼饵有）与钓竿 `lucky` 技能**叠加**触发幸运事件
- 上限限制：幸运事件触发率上限 **50%**，鱼饵/钓竿奖励上限 **15%**

### 赠送事务两阶段提交

赠送系统实现了完整的**两阶段提交回滚**机制：

```
Phase 1: PREPARE
  ├── 参数校验（目标用户、物品类型、数量限制）
  ├── 检查赠送次数（自动处理日期重置）
  └── 锁定双方的 asyncio.Lock

Phase 2: COMMIT (with auto-rollback)
  ├── 扣减发送方物品/金币
  ├── 保存发送方数据 ✅
  │   └── 失败 → 回滚发送方
  ├── 增加接收方物品/金币
  ├── 保存接收方数据 ✅
  │   └── 失败 → 回滚发送方 + 恢复赠送次数
  └── 返回结果
```

### LLM FunctionTool 集成

16 个 FunctionTool 基于 **Pydantic dataclass** 定义，每个工具包含：
- `name`：全局唯一的函数名
- `description`：自然语言描述，LLM 据此判断何时调用
- `parameters`：JSON Schema 格式的参数定义
- `call()`：实际执行逻辑，委托给 `FishingGameCommands`

```python
@dataclass
class FishingSellTool(FunctionTool[AstrAgentContext]):
    name = "fishing_sell"
    description = "出售渔获获取金币..."
    parameters = {
        "type": "object",
        "properties": {
            "fish_id_or_all": {"type": "string", "description": "鱼的ID或'all'"}
        }
    }

    async def call(self, context, **kwargs):
        event = context.context.event
        return await self.plugin.commands.cmd_sell(event, kwargs["fish_id_or_all"])
```

注册到 AstrBot 后，这些工具支持**多步 tool calling**——LLM 可先调用 `fishing_bag` 查看背包，再根据返回的鱼 ID 调用 `fishing_sell` 出售。

### 每日自动刷新

采用 **asyncio.Task** 实现常驻后台定时任务：

```python
async def _daily_refresh_loop():
    while True:
        sleep_seconds = 距离下个凌晨的秒数
        await asyncio.sleep(sleep_seconds)
        
        # 遍历所有已注册用户
        for uid in await storage.get_all_user_ids():
            user = await storage.get_user(uid)
            user.check_and_reset_daily_give()  # 内部通过日期字符串判断是否跨天
            await storage.save_user(user)
        
        await asyncio.sleep(60)  # 避免同一秒重复触发
```

**容错设计：**
- 单个用户重置失败不影响其他用户
- 任务被取消（`CancelledError`）时正确退出
- 任何异常后等待 5 分钟重试
- 插件卸载时通过 `terminate()` 取消任务

---

## 📌 依赖

- **AstrBot** >= 4.9.2
- Python 3.9+
- pydantic

---

## 📄 License

MIT License

## 🔗 仓库

[https://github.com/soulmao/astrbot_plugin_fishing_game](https://github.com/soulmao/astrbot_plugin_fishing_game)