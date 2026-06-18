"""钓鱼游戏 LLM 工具模块（FunctionTool 方式）

通过 FunctionTool + @dataclass 方式注册工具到 AstrBot，
确保工具执行结果能正确作为 function result 回传给 LLM，
支持多步 tool calling（如先查背包再赠送）。
"""
from typing import Any
from pydantic import Field
from pydantic.dataclasses import dataclass

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool
from astrbot.core.astr_agent_context import AstrAgentContext


@dataclass
class FishingHelpTool(FunctionTool[AstrAgentContext]):
    """查看钓鱼游戏帮助"""
    name: str = "fishing_help"
    description: str = (
        "查看钓鱼游戏的玩法说明、所有可用命令和操作指南。"
        "当用户询问怎么玩、有什么命令、游戏规则时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_help")


@dataclass
class FishingFishTool(FunctionTool[AstrAgentContext]):
    """执行钓鱼操作"""
    name: str = "fishing_fish"
    description: str = (
        "执行钓鱼操作。普通钓竿每轮消耗 1 个鱼饵；"
        "金币钓竿消耗当前金币 10%（至少 100）；胡萝卜钓竿不消耗鱼饵。"
        "装备贪婪/无尽贪婪钓竿时，钓鱼不会直接结算，而是进入挂起状态生成【贪欲结晶】，"
        "之后用户需要发送 /收杆 结算或 /贪婪 继续赌一把。"
        "如果用户说想钓鱼、去钓鱼，调用此工具。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_fish")


@dataclass
class FishingShopTool(FunctionTool[AstrAgentContext]):
    """查看钓鱼商店"""
    name: str = "fishing_shop"
    description: str = (
        "查看钓鱼商店中当前可购买的钓竿和鱼饵列表。"
        "当用户说要看商店、买东西、有什么装备时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_shop")


@dataclass
class FishingBagTool(FunctionTool[AstrAgentContext]):
    """查看玩家背包"""
    name: str = "fishing_bag"
    description: str = (
        "查看玩家的完整背包信息，包括：所有拥有的钓竿（带编号1/2/3，附魔状态）、"
        "渔获（每条鱼旁有ID如 fish_003）、鱼饵（每个鱼饵旁有ID如 bait_001）、金币、等级等。"
        "当用户要看背包、有什么物品、想出售/赠送物品时，必须先调用此工具获取物品编号和ID。"
        "钓竿通过编号（如1/2/3）引用，渔获和鱼饵通过ID引用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_bag")


@dataclass
class FishingSellTool(FunctionTool[AstrAgentContext]):
    """出售渔获"""
    name: str = "fishing_sell"
    description: str = (
        "出售渔获获取金币。可以指定鱼的ID出售指定种类，或填入'all'/'全部'出售所有渔获。"
        "鱼的ID可以通过 fishing_bag 查看（如 fish_003）。"
        "当用户说卖鱼、出售渔获时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "fish_id_or_all": {
                "type": "string",
                "description": "鱼的ID（如 fish_001）或 'all'/'全部' 表示全部出售，默认为 all"
            }
        },
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        fish_id_or_all = kwargs.get("fish_id_or_all", "all")
        return await self.plugin._cmd_with_scramble(event, "cmd_sell", fish_id_or_all)


@dataclass
class FishingLevelTool(FunctionTool[AstrAgentContext]):
    """查看玩家等级"""
    name: str = "fishing_level"
    description: str = (
        "查看玩家当前的等级信息和经验进度。"
        "当用户问等级、经验、升级时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_level")


@dataclass
class FishingCdTool(FunctionTool[AstrAgentContext]):
    """查看冷却时间"""
    name: str = "fishing_cd"
    description: str = (
        "查看钓鱼和商店刷新的冷却时间剩余。"
        "当用户问冷却时间、还有多久能钓鱼时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_cd")


@dataclass
class FishingBuyTool(FunctionTool[AstrAgentContext]):
    """从商店购买物品"""
    name: str = "fishing_buy"
    description: str = (
        "从商店购买物品，需要先调用 fishing_shop 查看商店获取商品编号。"
        "当用户说购买、买东西时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "item_id": {
                "type": "string",
                "description": "商品编号（如 '1', '2'），对应商店列表中的编号"
            },
            "quantity": {
                "type": "number",
                "description": "购买数量，默认为1"
            }
        },
        "required": ["item_id"]
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        item_id = kwargs.get("item_id", "")
        quantity = int(kwargs.get("quantity", 1))
        try:
            index = int(item_id)
            return await self.plugin._cmd_with_scramble(event, "cmd_buy", index, quantity)
        except ValueError:
            return "无效的商品编号，请输入数字"


@dataclass
class FishingGiveTool(FunctionTool[AstrAgentContext]):
    """赠送物品给其他用户"""
    name: str = "fishing_give"
    description: str = (
        "赠送金币、渔获、鱼饵或钓竿给其他用户。每日限10次。"
        "注意：如果item_type是fish、bait或rod，item_id必须填写，否则会报错。"
        "先通过fishing_bag查看物品的ID（如fish_003代表鲤鱼，bait_001代表蚯蚓），"
        "钓竿通过fishing_myrods查看编号。"
        "然后将该ID传入item_id参数。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "target_user": {
                "type": "string",
                "description": "目标用户的ID"
            },
            "item_type": {
                "type": "string",
                "description": "物品类型，可选值: coins(金币), fish(渔获), bait(鱼饵), rod(钓竿)"
            },
            "item_id": {
                "type": "string",
                "description": "物品ID（赠送金币时不需要），渔获ID如fish_003，鱼饵ID如bait_001，钓竿填写编号如1"
            },
            "quantity": {
                "type": "number",
                "description": "赠送数量，默认为1"
            }
        },
        "required": ["target_user", "item_type"]
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        target_user = kwargs.get("target_user", "")
        item_type = kwargs.get("item_type", "")
        item_id = kwargs.get("item_id", "")
        quantity = int(kwargs.get("quantity", 1))
        return await self.plugin._cmd_with_scramble(
            event, "cmd_give", target_user, item_type, item_id, quantity
        )


@dataclass
class FishingRankTool(FunctionTool[AstrAgentContext]):
    """查看排行榜"""
    name: str = "fishing_rank"
    description: str = (
        "查看钓鱼次数排行榜，显示玩家的钓鱼排名。"
        "当用户问排行榜、排名时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_rank")


@dataclass
class FishingMyRodsTool(FunctionTool[AstrAgentContext]):
    """查看玩家拥有的钓竿"""
    name: str = "fishing_myrods"
    description: str = (
        "查看玩家拥有的所有钓竿列表。"
        "当用户问有什么钓竿、我的钓竿时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_myrods")


@dataclass
class FishingEquipTool(FunctionTool[AstrAgentContext]):
    """切换装备钓竿"""
    name: str = "fishing_equip"
    description: str = (
        "切换装备指定的钓竿。当用户说换钓竿、装备某个钓竿时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "index": {
                "type": "number",
                "description": "钓竿编号（从1开始）"
            }
        },
        "required": ["index"]
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        index = int(kwargs.get("index", 1))
        return await self.plugin._cmd_with_scramble(event, "cmd_equip_rod", index)


@dataclass
class FishingMyBaitsTool(FunctionTool[AstrAgentContext]):
    """查看玩家拥有的鱼饵"""
    name: str = "fishing_mybaits"
    description: str = (
        "查看玩家拥有的所有鱼饵列表。当用户问有什么鱼饵、我的鱼饵时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_mybaits")


@dataclass
class FishingEquipBaitTool(FunctionTool[AstrAgentContext]):
    """切换装备鱼饵"""
    name: str = "fishing_equip_bait"
    description: str = (
        "切换装备指定的鱼饵。钓鱼时会优先消耗已装备的鱼饵。"
        "当用户说换鱼饵、装备某个鱼饵时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "index": {
                "type": "number",
                "description": "鱼饵编号（从1开始）"
            }
        },
        "required": ["index"]
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        index = int(kwargs.get("index", 1))
        return await self.plugin._cmd_with_scramble(event, "cmd_equip_bait", index)


@dataclass
class FishingShopRefreshTool(FunctionTool[AstrAgentContext]):
    """手动刷新商店"""
    name: str = "fishing_shop_refresh"
    description: str = (
        "手动刷新商店商品，消耗50金币或使用刷新券。"
        "当用户说刷新商店、换一批商品时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_shop_refresh")


@dataclass
class FishingAchievementsTool(FunctionTool[AstrAgentContext]):
    """查看玩家成就"""
    name: str = "fishing_achievements"
    description: str = (
        "查看玩家当前已解锁的成就列表和所有成就的进度。"
        "当用户问成就、有什么成就、完成了哪些成就时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_achievements")


@dataclass
class FishingCollectionTool(FunctionTool[AstrAgentContext]):
    """查看钓鱼图鉴"""
    name: str = "fishing_collection"
    description: str = (
        "查看玩家已收集的鱼类图鉴进度，按稀有度分类显示收集情况。"
        "当用户说图鉴、收藏、收集进度时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_collection")


@dataclass
class FishingAuctionTool(FunctionTool[AstrAgentContext]):
    """拍卖行操作"""
    name: str = "fishing_auction"
    description: str = (
        "拍卖行操作工具。重要区分：'直接出售'(sell)是立刻把物品卖给系统换金币，价格固定为物品价值的30%，即时到账；"
        "'上架'(listing)是把物品挂到拍卖行等其他玩家购买，可以自定价格（默认价值的30%，可上下浮动30%），但需要等待别人买。"
        "当用户说'卖掉'、'直接出售'、'换成金币'时用action=sell；"
        "当用户说'上架'、'挂到拍卖行'、'放出去卖'时用action=listing。"
        "action=list浏览列表，action=search搜索关键词，action=buy购买，action=cancel取消自己的上架。"
        "支持物品类型：rod(钓竿，用编号)、bait(鱼饵，用编号或base_id)、fish(渔获，用fish_id)、"
        "ticket(附魔券，用ticket_id)、item(道具券，用道具ID如refresh_token或directed_enchant_swift_10)。"
        "【重要】出售/上架钓竿后，背包中的钓竿编号会重新排序。如果要连续操作多根钓竿，"
        "每次操作后请根据返回结果中的最新编号继续，或先调用fishing_bag重新查询。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型: list(列表), search(搜索), listing(上架), sell(出售), buy(购买), cancel(取消)"
            },
            "keyword_or_id": {
                "type": "string",
                "description": "搜索关键词、上架/购买/取消的编号或ID。action=list时可不传。item类型需填道具ID，如refresh_token、directed_enchant_swift_10"
            },
            "item_type": {
                "type": "string",
                "description": "物品类型: rod(钓竿), bait(鱼饵), fish(渔获), ticket(附魔券), item(道具券)。上架/出售时需要"
            },
            "price": {
                "type": "number",
                "description": "上架价格（可选，不传则使用默认价格）"
            }
        },
        "required": ["action"]
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        action = kwargs.get("action", "list")
        keyword_or_id = kwargs.get("keyword_or_id", "")
        item_type = kwargs.get("item_type", "")
        price = kwargs.get("price")
        
        args = []
        if action == "search":
            args.append(keyword_or_id)
        elif action in ("listing", "sell"):
            if item_type:
                args.append(item_type)
            if keyword_or_id:
                args.append(keyword_or_id)
            if price is not None:
                args.append(str(price))
        elif action in ("buy", "cancel"):
            if keyword_or_id:
                args.append(keyword_or_id)
        
        return await self.plugin._cmd_with_scramble(event, "cmd_auction", action, *args)


@dataclass
class FishingEnchantTool(FunctionTool[AstrAgentContext]):
    """钓竿附魔"""
    name: str = "fishing_enchant"
    description: str = (
        "为指定编号的钓竿随机附魔技能，消耗金币或普通附魔券（不是定向附魔券）。"
        "当用户说普通附魔、随机附魔、给钓竿加技能但未指定具体技能和定向券时调用。"
        "如果用户提到'定向附魔券'或'定向技能券'，请改用 fishing_directed_enchant。"
        "rod_index 可以通过 fishing_myrods 查看。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "rod_index": {
                "type": "number",
                "description": "钓竿编号（从1开始）"
            }
        },
        "required": ["rod_index"]
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        rod_index = int(kwargs.get("rod_index", 1))
        return await self.plugin._cmd_with_scramble(event, "cmd_enchant", rod_index)


@dataclass
class FishingEnchantUpgradeTool(FunctionTool[AstrAgentContext]):
    """钓竿附魔升级"""
    name: str = "fishing_enchant_upgrade"
    description: str = (
        "使用金币升级指定钓竿的指定技能，每次固定增加少量百分比。"
        "当用户说用金币升级技能、提升技能等级时调用。"
        "如果用户提到'定向附魔券'或'定向技能券'，请改用 fishing_directed_enchant。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "rod_index": {
                "type": "number",
                "description": "钓竿编号（从1开始）"
            },
            "skill": {
                "type": "string",
                "description": "技能名: swift(迅捷), lucky(幸运), harvest(丰收), treasure(寻宝), tide(潮汐), exp_boost(神慧), voyage(远航), mending(经验修补)"
            }
        },
        "required": ["rod_index", "skill"]
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        rod_index = int(kwargs.get("rod_index", 1))
        skill = kwargs.get("skill", "")
        return await self.plugin._cmd_with_scramble(event, "cmd_enchant_upgrade", rod_index, skill)


@dataclass
class FishingDirectedEnchantTool(FunctionTool[AstrAgentContext]):
    """定向附魔"""
    name: str = "fishing_directed_enchant"
    description: str = (
        "使用背包中的定向附魔券（定向技能券）为当前装备钓竿添加或升级指定技能。"
        "当用户说要用定向附魔券、定向技能券、给钓竿加特定技能、用券升级技能时调用。"
        "效果：在当前技能百分比基础上累加券面百分比（如当前20% + 5%券 = 25%），最高100%。"
        "技能名支持中文: 迅捷/幸运/丰收/寻宝/潮汐/神慧/远航/经验修补"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "技能名，如: 远航、迅捷、幸运等"
            },
            "tier": {
                "type": "string",
                "description": "档位(可选): 5/10/15，不指定则自动使用背包中最高档位的券"
            }
        },
        "required": ["skill"]
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        skill = kwargs.get("skill", "")
        tier = kwargs.get("tier", "")
        return await self.plugin._cmd_with_scramble(event, "cmd_directed_enchant", skill, tier)


@dataclass
class FishingUpgradeShopTool(FunctionTool[AstrAgentContext]):
    """升级商店"""
    name: str = "fishing_upgrade_shop"
    description: str = (
        "升级商店等级，增加商店展示的商品条数。"
        "当用户说要升级商店、增加商店商品数量、扩展商店时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_upgrade_shop")


@dataclass
class FishingGreedyToggleTool(FunctionTool[AstrAgentContext]):
    """切换贪婪/无尽贪婪钓竿前缀"""
    name: str = "fishing_greedy_toggle"
    description: str = (
        "在「贪婪的」与「无尽贪婪的」钓竿前缀之间切换。默认切换当前装备钓竿，"
        "可通过 rod_index 指定背包中的钓竿编号。消耗 1000 金币，只有带有贪婪前缀的钓竿才能切换。"
        "当用户说切换贪婪、变成无尽贪婪、把钓竿改成贪婪模式时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "rod_index": {
                "type": "number",
                "description": "钓竿编号（从1开始），不指定则切换当前装备钓竿"
            }
        },
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        rod_index = int(kwargs.get("rod_index", 0))
        return await self.plugin._cmd_with_scramble(event, "cmd_greedy_toggle", rod_index)


@dataclass
class FishingGreedyContinueTool(FunctionTool[AstrAgentContext]):
    """继续贪婪挂起状态"""
    name: str = "fishing_greedy_continue"
    description: str = (
        "继续当前的贪婪/无尽贪婪挂起状态。用已生成的【贪欲结晶】作为特殊鱼饵再次抛竿，"
        "有概率获得更高倍率的奖励，也有概率断线爆仓（失去所有结晶并扣除 10% 当前金币修理费）。"
        "当用户说继续贪婪、再赌一把、贪婪时说调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_greedy_continue")


@dataclass
class FishingGreedyCashoutTool(FunctionTool[AstrAgentContext]):
    """结算贪婪挂起状态"""
    name: str = "fishing_greedy_cashout"
    description: str = (
        "结算当前贪婪/无尽贪婪挂起状态，将【贪欲结晶】兑换为金币和经验，并进入钓鱼冷却。"
        "当用户说收杆、结算、不赌了、落袋为安时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin._cmd_with_scramble(event, "cmd_greedy_cashout")
