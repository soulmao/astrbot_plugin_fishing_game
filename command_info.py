"""信息查询命令模块"""
import random
import time
import math

from .commands_base import CommandBase
from .utils import (
    format_rod_name, format_rod_skills, format_time, format_bait_name,
    parse_directed_enchant_id,
)
from .fish_data import (
    FISH_TYPES, FISH_PREFIXES, get_fish_by_id, get_prefix_by_id,
    get_level_info, get_next_level_exp, get_bait_prefix, get_bait_by_id,
    ENCHANT_TICKETS, ROD_SKILL_DESCRIPTIONS, calc_fish_value,
    RESEARCH_CONFIG,
)
from .storage import StorageManager


class InfoCommands(CommandBase):
    """信息查询命令处理器"""

    async def cmd_help(self, event) -> str:
        """帮助命令"""
        fishing_cd = format_time(self.star.fishing_cooldown)
        return f"""🎣 钓鱼游戏帮助 · V4.7.0

📋 **命令列表：**

🎯 `/钓鱼` 或 `/fish`
  普通钓竿每轮消耗1个鱼饵；装备贪婪/无尽贪婪钓竿时进入挂起状态，不会直接结算
  贪婪钓竿的附魔词条仅在首次激活时生效，后续继续不会重复触发
  冷却 {fishing_cd}

💰 `/收杆` 或 `/greedy_cashout`
  结算当前贪婪挂起状态，将【贪欲结晶】兑换为金币与经验

🎲 `/贪婪` 或 `/greedy_continue`
  继续当前的贪婪挂起状态，以结晶为饵再次抛竿（可能暴富，可能断线爆仓）

📦 `/背包` 或 `/bag`
  查看渔获、鱼饵、金币、钓竿等信息

💰 `/卖鱼 [ID/全部]` 或 `/sell [ID/全部]`
  出售渔获获取金币（贪婪挂起期间被锁定，无法使用）

📊 `/等级` 或 `/level`
  查看当前等级和经验进度，最高 Lv.15「深海主宰」

📖 `/图鉴` 或 `/collection`
  查看 46 种鱼 × 15 种前缀的收集进度，以及当前可研究的 5 个最高价值鱼种

🔬 `/研究 [品级/鱼名/前缀名/鱼名+前缀]` 或 `/research [目标]`
  品级/鱼名研究鱼种，前缀名研究前缀；同时指定鱼名和前缀可锁定图鉴组合
  未命中时研究倍率逐次提高，最后一次主动垂钓保底
  不带目标查看进度；`/研究 取消` 可取消当前研究（经验不返还）

⏰ `/冷却` 或 `/cd`
  查看钓鱼和商店刷新的冷却状态

🏪 `/商店` 或 `/shop`
  查看可购买的钓竿和鱼饵（随机刷新6件）

🛒 `/购买 [编号] [数量]` 或 `/buy [编号] [数量]`
  从商店购买物品

🔄 `/刷新商店` 或 `/shop_refresh`
  手动刷新商店，消耗50金币或刷新券
  冷却 1 小时

🎣 `/我的钓竿` 或 `/myrods`
  查看所有拥有的钓竿

🔧 `/装备钓竿 [编号]` 或 `/equip [编号]`
  切换当前使用的钓竿（贪婪挂起期间被锁定，无法使用）

🪤 `/我的鱼饵` 或 `/mybaits`
  查看所有拥有的鱼饵

🔧 `/装备鱼饵 [编号]` 或 `/equip_bait [编号]`
  切换当前使用的鱼饵，钓鱼时优先消耗该鱼饵

🏆 `/排行榜` 或 `/rank`
  查看综合价值排行榜（库存价值 + 经验）

🎁 `/赠送 @用户 类型 ID [数量]` 或 `/give @用户 类型 ID [数量]`
  赠送金币/渔获/鱼饵/钓竿给其他用户
  类型: coins(金币), fish(渔获), bait(鱼饵), rod(钓竿)

🏪 `/拍卖` 或 `/auction`
  拍卖行：浏览/搜索/上架/出售/取消/购买物品
  /拍卖 列表 [页码] | /拍卖 搜索 <关键词>
  /拍卖 上架 <类型> <编号/ID> [价格] | /拍卖 出售 <类型> <编号/ID>
  /拍卖 取消 <编号> | /拍卖 购买 <编号>
  类型: rod(钓竿), bait(鱼饵), fish(渔获), ticket(附魔券), item(道具券)

✨ `/附魔 <钓竿编号>` 或 `/enchant <钓竿编号>`
  为钓竿随机附魔技能，消耗金币或附魔券

⬆️ `/附魔升级 <钓竿编号> <技能名>` 或 `/enchant_upgrade <编号> <技能>`
  升级指定钓竿的指定技能，消耗金币

🎯 `/定向附魔 [技能名] [档位]` 或 `/directed_enchant [技能名] [档位]`
  使用背包中的定向附魔券为当前装备钓竿添加/升级技能
  在当前技能百分比基础上累加，最高 100%；档位 5/10/15（对应+5%/+10%/+15%），不指定时自动使用最高档位

♾️ `/切换贪婪 [钓竿编号]` 或 `/greedy_toggle [编号]`
  在「贪婪的」与「无尽贪婪的」钓竿前缀之间切换，默认切换当前装备钓竿，消耗 1000 金币

🏪 `/升级商店` 或 `/upgrade_shop`
  消耗金币提升商店等级，增加商店展示条数（每次+2条，最高12级）

🏅 `/成就` 或 `/achievements`
  查看成就列表与解锁进度

————————————————

🐟 **游戏玩法：**
• 初始获得 100 金币、木制钓竿、10条蚯蚓
• 钓鱼获得渔获 → 卖鱼赚金币 → 购买更好的钓竿和鱼饵
• 鱼池共 46 种鱼；稀有鱼自然权重约 21.55%，传说鱼约 1.39%
• 更好的钓竿/鱼饵 = 更高稀有度、更多高价值前缀 + 更多经验
• 多余经验可用于海洋研究：品级/鱼名研究鱼种，前缀名研究前缀，鱼名+前缀锁定组合
• 等级上限为 Lv.15；升级可解锁装备，并积累不会导致掉级的安全研究经验
• 高品质钓竿前缀自带词条技能（迅捷、幸运、丰收等）
• 钓竿可附魔和升级技能，每次附魔价格倍增
• 每日可赠送 10 次给好友
• 拍卖行可买卖物品，保留24小时

🏅 **成就系统：**
• 完成各类目标（累计钓鱼、捕获稀有鱼、金币、等级、图鉴、附魔、连续签到等）自动解锁成就
• 每次解锁成就会获得金币和经验奖励
• 成就在钓鱼、卖鱼、附魔、拍卖、赠送等操作后自动检查并提示

🔥 **每日签到：**
• 每日首次成功钓鱼时自动签到
• 连续签到天数越高，奖励越丰厚（金币、经验、随机鱼饵）
• 断签后连续天数会重置

🔱 **钓竿词条技能：**
高品质钓竿前缀自带技能：
• ⚡迅捷 - 减少钓鱼冷却时间
• 🍀幸运 - 提升幸运事件触发概率
• 🌾丰收 - 概率获得额外渔获
• 💎寻宝 - 概率获得额外金币
• 🌊潮汐 - 概率本次钓鱼无需冷却
• ✨神慧 - 获得额外经验加成
• 🧭远航 - 概率触发额外钓鱼（每次额外钓鱼增加约 7.5% 基础冷却）
• 🔧经验修补 - 部分经验转化为金币

👻 **特殊前缀钓竿：**
神秘的词缀，拥有独特机制：
• 💰 贪婪的 - 【全部或一无所有】：钓上鱼后形成【贪欲结晶】，首层即享 1.2 倍收益。附魔词条只在首次激活时生效，后续 /贪婪 不会重复触发。可 /收杆 结算，或继续提高倍率；断线会清空结晶，修理费为当前金币的 2%，但不超过结晶价值的 10%。初始消耗 2 个鱼饵，结算后冷却延长 15%。
• ♾️ 无尽贪婪的 - 更高风险、高收益的贪婪版本：首层享 1.4 倍收益，附魔词条同样只在首次激活时生效；后续成长更快，但断线率更高，金币越多时返回文字受到的黑色方块侵蚀越强。初始消耗 3 个鱼饵，结算后冷却延长 30%。可用 `/切换贪婪` 切换，消耗 1000 金币
• 👻 诅咒的 - 附魔和升级仅需正常价格的 35%，但每次钓鱼有 8% 概率丢失一个附魔词条
• ⚡ 迅捷的 - 冷却缩短 45%，20% 概率免冷却，但有 18% 概率失误
• 📚 学徒的 - 经验收益显著提高，但寻宝金币收益降低 35%
• 🎲 幸运方块的 - 更偏向获得随机技能，最多保留 6 个；满槽后可能强化已有词条，单条最高 25%
• 👑 傲慢的 - 仅限金色/神级钓竿，保底稀有品质并提高传说/神话机会；必须使用珍稀（香料饵）及以上鱼饵
• 💢 嫉妒的 - 每有一名等级更高的玩家，分级稀有度加成 +8%（最高 +64%）；传说与神话获得更强提升，副作用与额外冷却的触发率均为 15%

🔧 **特种钓竿：**
无法附加前缀的独特钓竿，不消耗鱼饵：
• 🥕 胡萝卜钓竿 - 自带远航技能，触发额外钓鱼；所有返回文本中随机插入猪叫声
• 💰 金币钓竿 - 不消耗鱼饵，每次固定消耗 10 金币，自带 80% 寻宝；金币越多，钓到高品质鱼的概率越高（最多+50%稀有度）
• ⬛ 无尽贪婪 - 金币越多，返回文字受到的黑色方块侵蚀越强；不再产生问号乱码

🐉 **古龙收藏系列：**
稀有词缀，仅高级玩家可获得：
• 🎣 古龙收藏钓竿 - 极高幸运与全技能加成
• 🐟 古龙收藏鱼类 - 售价远超普通传说鱼
• 🪤 古龙收藏鱼饵 - 大幅加成随机事件触发率

💡 **模糊命令支持**：
• 支持常见口语化变体，例如 `/钓一下`、`/查看背包`、`/我的鱼竿`
• 相似度阈值可在 AstrBot 面板中调整

🛠️ **管理员命令**（仅配置的 UID 可用）：
• `/管理 查看 <@用户/UID>` `/管理 加金币 <@用户/UID> <数量>`
• `/管理 设经验 <@用户/UID> <数量>` `/管理 加钓竿 <UID> <base_id> [前缀] [词条数值 ...] [附魔次数]`
• `/管理 加券 <@用户/UID> <券ID> [数量]`
• `/管理 全服发金币 <数量>` `/管理 统计` `/管理 日志`
• `/管理 物品ID [类别] [关键词] [页码]` `/管理 清空日志`
• 物品ID 类别支持：鱼、钓竿、鱼饵、券、词条、前缀；也可直接输入中文名或 ID
• 加钓竿示例：`/管理 加钓竿 523969851 rod_002 rod_pref_11 迅捷45% 幸运25% 7`
• 完整列表请使用 `/管理 帮助`"""

    @staticmethod
    def _research_fish_unlocked(user, fish: dict) -> bool:
        """检查鱼种是否能由当前等级和钓竿获得。"""
        rod_id = user.current_rod.get("base_id", "")
        min_levels = {"common": 1, "rare": 2, "legendary": 5, "mythic": 6}
        if user.level < min_levels.get(fish.get("rarity"), 1):
            return False
        return fish.get("rarity") != "mythic" or rod_id in ("rod_004", "rod_005")

    @staticmethod
    def _research_prefix_unlocked(user, prefix: dict) -> bool:
        """检查鱼名前缀是否能由当前等级和钓竿获得。"""
        rod_id = user.current_rod.get("base_id", "")
        if user.level < int(prefix.get("min_level", 1)):
            return False
        if prefix.get("requires_gold_rod") and rod_id not in ("rod_004", "rod_005"):
            return False
        if prefix.get("requires_divine_rod") and rod_id != "rod_005":
            return False
        if prefix.get("id") == "pref_015" and user.current_rod.get("prefix_id") != "rod_pref_13":
            return False
        return True

    @classmethod
    def _match_research_targets(cls, user, query: str) -> tuple:
        """解析自然目标，返回研究类型、当前可达候选和其中未点亮候选。"""
        normalized = "".join(str(query or "").strip().lower().split())
        rarity_aliases = {
            "常见": "common", "常见鱼": "common", "common": "common",
            "稀有": "rare", "稀有鱼": "rare", "rare": "rare",
            "传说": "legendary", "传说鱼": "legendary", "legendary": "legendary",
            "神话": "mythic", "神话鱼": "mythic", "mythic": "mythic",
        }
        rarity = rarity_aliases.get(normalized)
        fish_match = next((
            fish for fish in FISH_TYPES
            if fish["id"].lower() in normalized or fish["name"].lower() in normalized
        ), None)
        prefix_match = next((
            prefix for prefix in FISH_PREFIXES
            if prefix["id"].lower() in normalized
            or prefix["name"].lower() in normalized
            or (
                fish_match
                and prefix["name"].lower().rstrip("的") in normalized
            )
            or (
                not rarity
                and normalized == prefix["name"].lower().rstrip("的")
            )
        ), None)
        collection = user.get_collection()
        collected_fish = {key.split("#", 1)[0] for key in collection if "#" in key}
        collected_prefixes = {key.split("#", 1)[1] for key in collection if "#" in key}

        # 同时指定鱼和前缀（含“龙鱼 金色”及 ID 组合）才进入精确组合研究。
        if fish_match and prefix_match:
            candidates = [(fish_match, prefix_match, f"{prefix_match['name']}{fish_match['name']}")]
            candidates = [item for item in candidates if cls._research_fish_unlocked(user, item[0])
                          and cls._research_prefix_unlocked(user, item[1])]
            unseen = [item for item in candidates if f"{item[0]['id']}#{item[1]['id']}" not in collection]
            return "combo", candidates, unseen

        if prefix_match:
            available = [prefix_match] if cls._research_prefix_unlocked(user, prefix_match) else []
            return "prefix", available, [p for p in available if p["id"] not in collected_prefixes]

        if fish_match:
            available = [fish_match] if cls._research_fish_unlocked(user, fish_match) else []
            return "fish", available, [f for f in available if f["id"] not in collected_fish]

        if rarity:
            available = [fish for fish in FISH_TYPES
                         if fish.get("rarity") == rarity and cls._research_fish_unlocked(user, fish)]
            return "fish", available, [f for f in available if f["id"] not in collected_fish]
        return "", [], []

    @staticmethod
    def _research_combo_cost(fish: dict, prefix: dict) -> tuple:
        """组合费用按自然稀缺度在基础费用的 0.75～1.5 倍间浮动。"""
        fish_cfg = RESEARCH_CONFIG["fish"][fish["rarity"]]
        prefix_cfg = RESEARCH_CONFIG["prefix"][prefix["rarity"]]
        max_fish_weight = max(float(item.get("weight", 0)) for item in FISH_TYPES)
        max_prefix_weight = max(float(item.get("weight", 0)) for item in FISH_PREFIXES)
        inverse = (
            max_fish_weight / max(0.001, float(fish.get("weight", 0)))
            * max_prefix_weight / max(0.001, float(prefix.get("weight", 0)))
        )
        scarcity_factor = min(1.5, max(0.75, 0.75 + math.log10(inverse) * 0.15))
        cost = int(round(max(fish_cfg["cost"], prefix_cfg["cost"]) * scarcity_factor / 100)) * 100
        return max(100, cost), max(
            fish_cfg["attempts"], prefix_cfg["attempts"]
        )

    @staticmethod
    def _research_single_cost(target_type: str, target: dict) -> tuple:
        config = RESEARCH_CONFIG[target_type][target["rarity"]]
        return config["cost"], config["attempts"]

    @staticmethod
    def _select_preferred_target(target_type: str, candidates: list, collection: dict):
        """宽范围研究优先高价值目标，并优先完全未点亮的前缀。"""
        if target_type == "fish":
            score = lambda fish: float(fish.get("base_price", 0))
        elif target_type == "prefix":
            score = lambda prefix: float(prefix.get("price_multiplier", 0))
        else:
            collected_prefixes = {key.split("#", 1)[1] for key in collection if "#" in key}
            score = lambda item: (
                calc_fish_value(item[0]["id"], item[1]["id"], 1)
                * (1.25 if item[1]["id"] not in collected_prefixes else 1.0)
            )
        best_score = max(score(item) for item in candidates)
        return random.choice([item for item in candidates if score(item) == best_score])

    @classmethod
    def _research_availability(cls, user, state: dict) -> tuple:
        """返回当前装备是否可完成研究，以及不可达时的明确需求。"""
        fish = get_fish_by_id(state.get("fish_id") or state.get("target_id", ""))
        prefix = get_prefix_by_id(state.get("prefix_id") or state.get("target_id", ""))
        if state.get("target_type") in ("fish", "combo") and fish:
            if not cls._research_fish_unlocked(user, fish):
                return False, "需要金色或神级钓竿，并达到该鱼种等级要求"
        if state.get("target_type") in ("prefix", "combo") and prefix:
            if not cls._research_prefix_unlocked(user, prefix):
                if prefix.get("id") == "pref_015":
                    return False, "需要装备诅咒前缀钓竿"
                if prefix.get("requires_divine_rod"):
                    return False, "需要神级钓竿"
                if prefix.get("requires_gold_rod"):
                    return False, "需要金色或神级钓竿"
                return False, f"需要达到 Lv.{prefix.get('min_level', 1)}"
        return True, "当前装备可达成"

    async def cmd_research(self, event, target: str = "") -> str:
        """海洋研究：消费安全经验，定向提高未收集图鉴目标的出现率。"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            action = str(target or "").strip()
            active = user.get_research()

            if action.lower() in ("取消", "cancel", "停止", "stop"):
                if not active:
                    return "🔬 当前没有进行中的海洋研究。"
                old = user.clear_research()
                await self.storage.save_user(user)
                return f"🔬 已取消对“{old['target_name']}”的研究，已消耗经验不返还。"

            if not action or action.lower() in ("状态", "status", "进度"):
                spendable = user.get_spendable_exp()
                if not active:
                    return (
                        "🔬 当前没有进行中的海洋研究。\n"
                        f"📈 可用经验：{spendable:,}\n"
                        "研究品级或鱼名可补鱼种，研究前缀名可补前缀；同时输入鱼名和前缀可锁定组合。"
                    )
                reachable, requirement = self._research_availability(user, active)
                reach_text = "✅ 当前装备可达成" if reachable else f"⏸️ 当前装备不可达成：{requirement}"
                return (
                    f"🔬 正在研究：{active['target_name']}\n"
                    f"🎯 剩余保底：{active['remaining']}/{active['total']} 次主动垂钓\n"
                    f"📚 匹配范围剩余：{active.get('remaining_targets', 1)} 个未点亮目标\n"
                    f"{reach_text}\n"
                    f"📈 可用经验：{spendable:,}\n"
                    "提示：额外渔获不会重复消耗研究次数。"
                )

            if active:
                return (
                    f"❌ 当前正在研究“{active['target_name']}”，剩余 {active['remaining']} 次。\n"
                    "请先使用 /研究 取消。"
                )

            target_type, available, unseen = self._match_research_targets(user, action)
            if not available:
                return (
                    "❌ 没有匹配到当前可研究的目标。\n"
                    "可以输入：传说、神话、龙鱼、神话的、龙鱼 金色，或 fish_011#pref_013。"
                )
            if not unseen:
                labels = {"fish": "鱼种", "prefix": "前缀", "combo": "组合"}
                return f"✅ “{action}”对应的{labels[target_type]}已经点亮。"

            spendable = user.get_spendable_exp()
            affordable = []
            for candidate in unseen:
                if target_type == "combo":
                    cost, attempts = self._research_combo_cost(candidate[0], candidate[1])
                else:
                    cost, attempts = self._research_single_cost(target_type, candidate)
                if cost <= spendable:
                    affordable.append((candidate, cost, attempts))
            if not affordable:
                costs = [
                    self._research_combo_cost(item[0], item[1])[0]
                    if target_type == "combo" else self._research_single_cost(target_type, item)[0]
                    for item in unseen
                ]
                min_cost = min(costs)
                return (
                    f"❌ 可安全消费的经验不足，至少需要 {min_cost:,}，当前仅 {spendable:,}。\n"
                    "研究不会消耗当前等级门槛以内的经验，因此不会导致降级。"
                )

            chosen = self._select_preferred_target(
                target_type, [item[0] for item in affordable], user.get_collection()
            )
            cost, attempts = next(
                (item_cost, item_attempts) for item, item_cost, item_attempts in affordable
                if item == chosen
            )
            if not user.spend_exp(cost):
                return "❌ 研究经验扣除失败，请重新查询当前经验。"
            if target_type == "combo":
                fish, prefix, target_name = chosen
                target_rarity = max(
                    (fish["rarity"], prefix["rarity"]),
                    key=lambda rarity: ("common", "rare", "legendary", "mythic").index(rarity),
                )
                user.start_research_combo(
                    fish["id"], prefix["id"], target_name, action, cost, attempts,
                    target_rarity, len(unseen),
                )
            else:
                target_name = chosen["name"]
                user.start_research(
                    target_type, chosen["id"], target_name, cost, attempts,
                    action, chosen["rarity"], len(unseen),
                )
            await self.storage.save_user(user)
            type_name = {"fish": "鱼种", "prefix": "前缀", "combo": "图鉴组合"}[target_type]
            return (
                f"🔬 已从“{action}”中选定未点亮{type_name}：{target_name}\n"
                f"📈 消耗经验：{cost:,}（等级保持 Lv.{user.level}）\n"
                f"🎯 接下来 {attempts} 次主动垂钓获得递增研究加成，最后一次保底。"
            )
    
    async def cmd_bag(self, event) -> str:
        """背包命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            # 基础信息
            level_info = get_level_info(user.level)
            next_exp = get_next_level_exp(user.level)
            
            result = f"""📦 背包信息

👤 {event.get_sender_name()}
🏷️ {level_info['name']} (Lv.{user.level})
💰 金币: {user.coins}
📈 经验: {user.exp}{'' if next_exp is None else f' / {next_exp}'}
🐟 累计钓鱼: {user.total_fish_count} 次

🎣 拥有的钓竿:"""
            
            current = user.current_rod
            for i, rod in enumerate(user.get_owned_rods(), 1):
                rod_name = format_rod_name(rod)
                skill_text = format_rod_skills(
                    rod["prefix_id"], rod.get("skills"), rod.get("base_id", "")
                )
                enchant_text = f" [附魔{rod.get('enchant_count', 0)}次]" if rod.get('enchant_count', 0) > 0 else ""
                is_current = (rod.get("instance_id") == current.get("instance_id"))
                marker = " [当前装备]" if is_current else ""
                result += f"\n  {i}. {rod_name}{skill_text}{enchant_text}{marker}"
            
            if not user.get_owned_rods():
                result += "\n  (无)"
            
            result += "\n\n🪤 鱼饵:"
            for bait in user.get_baits():
                bait_base = get_bait_by_id(bait["base_id"])
                bait_prefix = get_bait_prefix(bait["prefix_id"])
                if bait_base and bait_prefix:
                    result += f"\n  • {bait_prefix['name']}{bait_base['name']} x{bait['count']}"
            
            if not user.get_baits():
                result += "\n  (无)"
            
            total_fish_value = sum(
                calc_fish_value(f["fish_id"], f["prefix_id"], f["count"])
                for f in user.get_fish_inventory()
            )
            result += f"\n\n🐠 渔获[总价值：{total_fish_value}金币]:"
            for fish in user.get_fish_inventory():
                fish_info = get_fish_by_id(fish["fish_id"])
                prefix = get_prefix_by_id(fish["prefix_id"])
                if fish_info and prefix:
                    result += f"\n  • [{fish['fish_id']}] {prefix['name']}{fish_info['name']} x{fish['count']}"
            
            if not user.get_fish_inventory():
                result += "\n  (无)"
            
            # 添加道具信息
            result += "\n\n🎫 附魔券:"
            tickets = user._data.get("enchant_tickets", [])
            if tickets:
                for ticket in tickets:
                    ticket_info = None
                    for t in ENCHANT_TICKETS:
                        if t["id"] == ticket.get("ticket_id"):
                            ticket_info = t
                            break
                    name = ticket_info["name"] if ticket_info else ticket.get("ticket_id", "未知")
                    result += f"\n  • {name} x{ticket.get('count', 0)}"
            else:
                result += "\n  (无)"

            result += "\n\n🧰 道具:"
            items = user._data.get("items", [])
            ITEM_NAMES = {"refresh_token": "🔄 刷新券"}
            if items:
                for item in items:
                    item_id = item.get("id", "")
                    parsed = parse_directed_enchant_id(item_id)
                    if parsed:
                        skill_id, value = parsed
                        name = f"🎯 定向附魔券[{ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)}+{int(value*100)}%]"
                    else:
                        name = ITEM_NAMES.get(item_id, item_id)
                    result += f"\n  • {name} x{item.get('count', 0)}"
            else:
                result += "\n  (无)"

            # 签到与成就摘要
            streak = user.consecutive_checkin_days
            if streak > 0:
                result += f"\n\n🔥 连续签到: {streak} 天"
            ach_count = len(user.achievements)
            result += f"\n🏅 已解锁成就: {ach_count} 个"

            # 添加冷却倒计时
            fishing_cd = user.get_fishing_cd_remaining()
            cd_text = "好了" if fishing_cd <= 0 else format_time(fishing_cd)
            result += f"\n⏰ 钓鱼冷却: {cd_text}"

            return result
    
    async def cmd_level(self, event) -> str:
        """等级命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            level_info = get_level_info(user.level)
            next_exp = get_next_level_exp(user.level)
            
            result = f"""📊 等级信息

🏷️ {level_info['name']} (Lv.{user.level})
📈 经验: {user.exp}
"""
            
            if next_exp:
                need_exp = next_exp - user.exp
                denom = next_exp - level_info["exp_required"]
                if denom > 0:
                    progress = (user.exp - level_info["exp_required"]) / denom * 100
                    progress = max(0, min(100, progress))
                else:
                    progress = 100.0
                result += f"⬆️ 下一级需要: {need_exp} 经验\n"
                result += f"[{'█' * int(progress/5)}{'░' * (20-int(progress/5))}] {progress:.1f}%"
            else:
                result += "🏆 已达满级！"
            
            return result
    
    async def cmd_collection(self, event) -> str:
        """图鉴命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            collection = user.get_collection()
            
            # 计算总可收集数（所有鱼种 × 所有前缀组合）
            total_collectible = len(FISH_TYPES) * len(FISH_PREFIXES)
            collected_count = len(collection)
            progress_pct = (collected_count / total_collectible * 100) if total_collectible > 0 else 0
            
            result = f"""📖 钓鱼图鉴

已收集: {collected_count} / {total_collectible} ({progress_pct:.1f}%)"""
            
            # 按稀有度分组统计
            rarity_counts = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
            rarity_totals = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
            
            # 先计算各稀有度理论总数
            for fish in FISH_TYPES:
                for prefix in FISH_PREFIXES:
                    rarity_counts.setdefault(fish["rarity"], 0)
                    rarity_totals.setdefault(fish["rarity"], 0)
                    rarity_totals[fish["rarity"]] += 1
            
            # 再统计实际收集数
            rarity_counts = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
            rarity_items = {"common": [], "rare": [], "legendary": [], "mythic": []}
            
            for key, info in collection.items():
                parts = key.split("#", 1)
                if len(parts) != 2:
                    continue
                fish_id, prefix_id = parts
                fish = get_fish_by_id(fish_id)
                prefix = get_prefix_by_id(prefix_id)
                if fish and prefix:
                    rarity = fish["rarity"]
                    fish_name = f"{prefix['name']}{fish['name']}"
                    count = info.get("count", 1)
                    rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
                    rarity_items.setdefault(rarity, []).append(f"{fish_name} x{count}")
            
            # 重新计算理论总数（确保稀有度键存在）
            rarity_totals = {"common": 0, "rare": 0, "legendary": 0, "mythic": 0}
            for fish in FISH_TYPES:
                for prefix in FISH_PREFIXES:
                    rarity_totals[fish["rarity"]] = rarity_totals.get(fish["rarity"], 0) + 1
            
            rarity_names = {"common": "常见", "rare": "稀有", "legendary": "传说", "mythic": "神话"}
            rarity_emojis = {"common": "🔹", "rare": "🔷", "legendary": "⭐", "mythic": "🌟"}
            
            result += "\n\n📊 稀有度统计:"
            for rarity in ["mythic", "legendary", "rare", "common"]:
                cnt = rarity_counts.get(rarity, 0)
                tot = rarity_totals.get(rarity, 0)
                pct = (cnt / tot * 100) if tot > 0 else 0
                result += f"\n{rarity_emojis[rarity]} {rarity_names[rarity]}: {cnt}/{tot} ({pct:.1f}%)"

            collected_fish = {
                key.split("#", 1)[0] for key in collection if "#" in key
            }
            available_prefixes = [
                prefix for prefix in FISH_PREFIXES
                if self._research_prefix_unlocked(user, prefix)
            ]
            researchable = []
            for fish in FISH_TYPES:
                cost, _ = self._research_single_cost("fish", fish)
                if (fish["id"] in collected_fish or cost > user.get_spendable_exp()
                        or not self._research_fish_unlocked(user, fish)):
                    continue
                best_value = max(
                    (calc_fish_value(fish["id"], prefix["id"], 1)
                     for prefix in available_prefixes),
                    default=int(fish.get("base_price", 0)),
                )
                researchable.append((best_value, fish["name"], cost))
            researchable.sort(reverse=True)
            if researchable:
                result += "\n\n🔬 当前可研究鱼种（按最高价值）:"
                for value, fish_name, cost in researchable[:5]:
                    result += f"\n  • {fish_name} · 最高 {value:,} 金币 · 需 {cost:,} 经验"
            
            # 显示最近收集的鱼类（按首次获得时间排序）
            sorted_items = sorted(collection.items(), key=lambda x: x[1].get("first_at", 0), reverse=True)
            if sorted_items:
                result += "\n\n📜 最近收集:"
                for key, info in sorted_items[:10]:
                    parts = key.split("#", 1)
                    if len(parts) != 2:
                        continue
                    fish_id, prefix_id = parts
                    fish = get_fish_by_id(fish_id)
                    prefix = get_prefix_by_id(prefix_id)
                    if fish and prefix:
                        fish_name = f"{prefix['name']}{fish['name']}"
                        rarity_emoji = {"common": "", "rare": "", "legendary": "⭐", "mythic": "🌟"}.get(fish["rarity"], "")
                        result += f"\n  {rarity_emoji}{fish_name}"
            
            return result
    
    async def cmd_cd(self, event) -> str:
        """冷却命令"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            fishing_cd = user.get_fishing_cd_remaining()
            shop_cd = max(0, user.shop_refresh_cd - int(time.time())) if user.shop_refresh_cd > int(time.time()) else 0
            
            result = """⏰ 冷却状态

🎣 钓鱼: """
            if user.is_fishing_ready():
                result += "好了 ✓"
            else:
                result += format_time(fishing_cd)
            
            result += "\n🏪 商店刷新: "
            if user.is_shop_refresh_ready():
                result += "好了 ✓"
            else:
                result += format_time(shop_cd)
            
            return result

    async def cmd_rank(self, event) -> str:
        """排行榜命令（库存价值 + 经验综合排行）"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            leaderboard = await self.storage.get_leaderboard()
            
            if not leaderboard:
                return "🏆 排行榜\n\n暂无数据"
            
            result = "🏆 富豪排行榜（库存价值 + 经验）\n\n"
            for i, data in enumerate(leaderboard[:10], 1):
                uid, score, name = data
                display = f"{name}({uid})" if name else uid
                emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                result += f"{emoji} {display}  综合价值: {score}\n"
            
            # 查找当前用户排名（遍历全部确保准确）
            my_score = user.get_total_inventory_value() + user.exp
            my_rank = 1
            for uid, score, _ in leaderboard:
                if uid == user_id:
                    break
                my_rank += 1
            else:
                my_rank = len(leaderboard) + 1
            
            my_name = event.get_sender_name() or user_id[:10]
            result += f"\n📍 你的排名: 第{my_rank}名 ({my_name} 综合价值: {my_score})"
            
            return result
