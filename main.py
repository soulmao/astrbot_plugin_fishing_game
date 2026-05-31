"""AstrBot 钓鱼游戏插件"""
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .storage import StorageManager
from .commands import FishingGameCommands
from .fish_data import (
    FISH_TYPES, FISH_PREFIXES, ROD_BASES, ROD_PREFIXES,
    BAIT_BASES, BAIT_PREFIXES, LEVELS, SHOP_ITEMS,
    get_fish_by_id, get_prefix_by_id, get_rod_by_id, get_bait_by_id,
    get_level_info, get_next_level_exp, GIVE_LIMITS
)
from .llm_tools import (
    FishingHelpTool, FishingFishTool, FishingShopTool,
    FishingBagTool, FishingSellTool, FishingLevelTool,
    FishingCdTool, FishingBuyTool, FishingGiveTool,
    FishingRankTool, FishingMyRodsTool, FishingEquipTool,
    FishingMyBaitsTool, FishingEquipBaitTool, FishingShopRefreshTool,
    FishingCollectionTool
)
import random
import time
import asyncio


@register("fishing_game", "AstrBot", "钓鱼游戏插件 - 群聊娱乐插件，支持钓鱼、背包、商店、赠送等完整经济系统", "1.0.0")
class FishingGamePlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.context = context
        self.config = config or {}
        
        # 读取冷却时间配置（秒）
        self.fishing_cooldown = self.config.get("fishing_cooldown", 4 * 3600)
        self.shop_refresh_cooldown = self.config.get("shop_refresh_cooldown", 1 * 3600)
        logger.info(f"钓鱼游戏冷却配置: 钓鱼={self.fishing_cooldown}s, 商店刷新={self.shop_refresh_cooldown}s")
        
        self.storage = StorageManager(self)
        self.commands = FishingGameCommands(self, self.storage)
        
        # 注册 LLM FunctionTool（支持多步 tool calling）
        self._register_llm_tools()
        
        # 每日自动刷新定时任务（每天0点重置）
        self._refresh_task = None
        self._schedule_daily_refresh()
        logger.info("钓鱼游戏插件已加载")
    
    def _register_llm_tools(self):
        """注册 FunctionTool 到 AstrBot，支持结果回传 LLM"""
        tools = [
            FishingHelpTool(plugin=self),
            FishingFishTool(plugin=self),
            FishingShopTool(plugin=self),
            FishingBagTool(plugin=self),
            FishingSellTool(plugin=self),
            FishingLevelTool(plugin=self),
            FishingCdTool(plugin=self),
            FishingBuyTool(plugin=self),
            FishingGiveTool(plugin=self),
            FishingRankTool(plugin=self),
            FishingMyRodsTool(plugin=self),
            FishingEquipTool(plugin=self),
            FishingMyBaitsTool(plugin=self),
            FishingEquipBaitTool(plugin=self),
            FishingShopRefreshTool(plugin=self),
            FishingCollectionTool(plugin=self),
        ]
        self.context.add_llm_tools(*tools)
        logger.info(f"已注册 {len(tools)} 个 Fishing FunctionTool")
    
    def _seconds_until_midnight(self) -> int:
        """计算距离下一个 00:00:00 的秒数"""
        now = time.localtime()
        # 计算当前已过今天的秒数
        elapsed = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec
        return 86400 - elapsed
    
    async def _daily_refresh_loop(self):
        """每日自动刷新所有用户数据 - 异步协程"""
        while True:
            try:
                # 先等到下一个 0 点
                sleep_seconds = self._seconds_until_midnight()
                logger.info(f"每日刷新任务将在 {sleep_seconds} 秒后执行")
                await asyncio.sleep(sleep_seconds)
                
                logger.info("执行每日数据自动刷新")
                try:
                    today = time.strftime("%Y-%m-%d")
                    all_user_ids = await self.storage.get_all_user_ids()
                    reset_count = 0
                    for uid in all_user_ids:
                        try:
                            user = await self.storage.get_user(uid)
                            user.check_and_reset_daily_give()
                            await self.storage.save_user(user)
                            reset_count += 1
                        except Exception as e:
                            logger.error(f"重置用户 {uid} 每日赠送次数失败: {e}")
                    logger.info(f"已重置 {reset_count} 位用户的每日赠送次数")
                except Exception as e:
                    logger.error(f"每日刷新执行失败: {e}")
                
                # 执行完后短暂等待，避免在同一秒内重复触发
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("每日刷新任务已取消")
                break
            except Exception as e:
                logger.error(f"每日刷新任务异常: {e}")
                await asyncio.sleep(300)  # 异常后5分钟重试
    
    def _schedule_daily_refresh(self):
        """启动每日自动刷新异步任务"""
        self._refresh_task = asyncio.create_task(self._daily_refresh_loop())
    
    # ========== 手动命令 ==========
    
    @filter.command("我的钓竿", alias={"myrods"})
    async def cmd_myrods(self, event: AstrMessageEvent):
        '''我的钓竿 - 查看你拥有的所有钓竿'''
        result = await self.commands.cmd_myrods(event)
        yield event.plain_result(result)
    
    @filter.command("装备钓竿", alias={"equip"})
    async def cmd_equip_rod(self, event: AstrMessageEvent, index: int):
        '''装备钓竿 - 切换当前使用的钓竿'''
        result = await self.commands.cmd_equip_rod(event, index)
        yield event.plain_result(result)
    
    @filter.command("我的鱼饵", alias={"mybaits"})
    async def cmd_mybaits(self, event: AstrMessageEvent):
        '''我的鱼饵 - 查看你拥有的所有鱼饵'''
        result = await self.commands.cmd_mybaits(event)
        yield event.plain_result(result)
    
    @filter.command("装备鱼饵", alias={"equip_bait"})
    async def cmd_equip_bait(self, event: AstrMessageEvent, index: int):
        '''装备鱼饵 - 切换当前使用的鱼饵'''
        result = await self.commands.cmd_equip_bait(event, index)
        yield event.plain_result(result)
    
    @filter.command("钓鱼", alias={"fish"})
    async def cmd_fish(self, event: AstrMessageEvent):
        '''钓鱼 - 开始钓鱼，消耗1个鱼饵，获得随机鱼类'''
        result = await self.commands.cmd_fish(event)
        yield event.plain_result(result)
    
    @filter.command("背包", alias={"bag"})
    async def cmd_bag(self, event: AstrMessageEvent):
        '''背包 - 查看你的渔获、鱼饵、金币等信息'''
        result = await self.commands.cmd_bag(event)
        yield event.plain_result(result)
    
    @filter.command("卖鱼", alias={"sell"})
    async def cmd_sell(self, event: AstrMessageEvent, fish_id_or_all: str = "all"):
        '''卖鱼 - 出售渔获获取金币，支持指定鱼ID或"全部"'''
        result = await self.commands.cmd_sell(event, fish_id_or_all)
        yield event.plain_result(result)
    
    @filter.command("等级", alias={"level"})
    async def cmd_level(self, event: AstrMessageEvent):
        '''等级 - 查看当前等级和经验进度'''
        result = await self.commands.cmd_level(event)
        yield event.plain_result(result)
    
    @filter.command("冷却", alias={"cd"})
    async def cmd_cd(self, event: AstrMessageEvent):
        '''冷却 - 查看钓鱼和商店刷新的冷却时间'''
        result = await self.commands.cmd_cd(event)
        yield event.plain_result(result)
    
    @filter.command("商店", alias={"shop"})
    async def cmd_shop(self, event: AstrMessageEvent):
        '''商店 - 查看可购买的钓竿和鱼饵'''
        result = await self.commands.cmd_shop(event)
        yield event.plain_result(result)
    
    @filter.command("购买", alias={"buy"})
    async def cmd_buy(self, event: AstrMessageEvent, index: int, quantity: int = 1):
        '''购买 - 从商店购买物品，用法: /购买 编号 [数量]'''
        result = await self.commands.cmd_buy(event, index, quantity)
        yield event.plain_result(result)
    
    @filter.command("刷新商店", alias={"shop_refresh"})
    async def cmd_shop_refresh(self, event: AstrMessageEvent):
        '''刷新商店 - 手动刷新商店商品，消耗50金币或使用刷新券'''
        result = await self.commands.cmd_shop_refresh(event)
        yield event.plain_result(result)
    
    @filter.command("排行榜", alias={"rank"})
    async def cmd_rank(self, event: AstrMessageEvent):
        '''排行榜 - 查看钓鱼次数排行榜'''
        result = await self.commands.cmd_rank(event)
        yield event.plain_result(result)
    
    @filter.command("帮助", alias={"help"})
    async def cmd_help(self, event: AstrMessageEvent):
        '''帮助 - 查看钓鱼游戏帮助信息'''
        result = await self.commands.cmd_help(event)
        yield event.plain_result(result)
    
    @filter.command("图鉴", alias={"collection"})
    async def cmd_collection(self, event: AstrMessageEvent):
        '''图鉴 - 查看已收集的鱼类图鉴进度'''
        result = await self.commands.cmd_collection(event)
        yield event.plain_result(result)
    
    @filter.command("赠送", alias={"give"})
    async def cmd_give(self, event: AstrMessageEvent, target_user: str, item_type: str, item_id: str = "", quantity: int = 1):
        '''赠送 - 赠送物品给其他用户，用法: /赠送 @用户 物品类型 物品ID [数量]
        物品类型: coins(金币), fish(渔获), bait(鱼饵)'''
        result = await self.commands.cmd_give(event, target_user, item_type, item_id, quantity)
        yield event.plain_result(result)
    
    async def terminate(self):
        '''插件卸载时调用'''
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("钓鱼游戏插件已卸载")
