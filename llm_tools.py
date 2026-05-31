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
        return await self.plugin.commands.cmd_help(event)


@dataclass
class FishingFishTool(FunctionTool[AstrAgentContext]):
    """执行钓鱼操作"""
    name: str = "fishing_fish"
    description: str = (
        "执行钓鱼操作，消耗1个鱼饵获得随机鱼类。需要先确保用户有鱼饵。"
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
        return await self.plugin.commands.cmd_fish(event)


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
        return await self.plugin.commands.cmd_shop(event)


@dataclass
class FishingBagTool(FunctionTool[AstrAgentContext]):
    """查看玩家背包"""
    name: str = "fishing_bag"
    description: str = (
        "查看玩家的背包信息，包括金币、经验、等级、渔获（每条鱼旁有ID如 fish_003）、"
        "鱼饵（每个鱼饵旁有ID如 bait_001）、当前钓竿等。"
        "通过背包可以获取需要赠送或出售的鱼的ID。"
        "当用户要看背包、有什么鱼、财产时调用。"
    )
    parameters: dict = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    plugin: Any = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        event = context.context.event
        return await self.plugin.commands.cmd_bag(event)


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
        return await self.plugin.commands.cmd_sell(event, fish_id_or_all)


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
        return await self.plugin.commands.cmd_level(event)


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
        return await self.plugin.commands.cmd_cd(event)


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
            return await self.plugin.commands.cmd_buy(event, index, quantity)
        except ValueError:
            return "无效的商品编号，请输入数字"


@dataclass
class FishingGiveTool(FunctionTool[AstrAgentContext]):
    """赠送物品给其他用户"""
    name: str = "fishing_give"
    description: str = (
        "赠送金币、渔获或鱼饵给其他用户。每日限10次。"
        "注意：如果item_type是fish或bait，item_id必须填写，否则会报错。"
        "先通过fishing_bag查看物品的ID（如fish_003代表鲤鱼，bait_001代表蚯蚓），"
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
                "description": "物品类型，可选值: coins(金币), fish(渔获), bait(鱼饵)"
            },
            "item_id": {
                "type": "string",
                "description": "物品ID（赠送金币时不需要），渔获ID如fish_003，鱼饵ID如bait_001"
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
        return await self.plugin.commands.cmd_give(
            event, target_user, item_type, item_id, quantity
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
        return await self.plugin.commands.cmd_rank(event)


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
        return await self.plugin.commands.cmd_myrods(event)


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
        return await self.plugin.commands.cmd_equip_rod(event, index)


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
        return await self.plugin.commands.cmd_mybaits(event)


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
        return await self.plugin.commands.cmd_equip_bait(event, index)


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
        return await self.plugin.commands.cmd_shop_refresh(event)


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
        return await self.plugin.commands.cmd_collection(event)
