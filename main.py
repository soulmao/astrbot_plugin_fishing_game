"""AstrBot 钓鱼游戏插件"""
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from .storage import StorageManager
from .command_equipment import EquipmentCommands
from .command_fishing import FishingCommands
from .command_info import InfoCommands
from .command_economy import EconomyCommands
from .command_social import SocialCommands
from .command_auction import AuctionCommands
from .command_enchant import EnchantCommands
from .command_achievements import AchievementCommands
from .command_admin import AdminCommands
from .fish_data import get_rod_prefix
from .result_renderer import (
    RESULT_IMAGE_TEMPLATE, is_t2i_service_error, obscure_text, render_result_html,
)
from .backpack_renderer import (
    BACKPACK_IMAGE_TEMPLATE, RODS_IMAGE_TEMPLATE,
    build_backpack_view, build_rods_view,
)
from .market_renderer import (
    AUCTION_IMAGE_TEMPLATE, SHOP_IMAGE_TEMPLATE,
    build_auction_view, build_shop_view,
)
from .gallery_renderer import (
    ACHIEVEMENTS_IMAGE_TEMPLATE, BAITS_IMAGE_TEMPLATE, COLLECTION_IMAGE_TEMPLATE,
    build_achievements_view, build_baits_view, build_collection_view,
)
from .fishing_renderer import FISHING_IMAGE_TEMPLATE, build_fishing_result_view
from .llm_tools import (
    FishingHelpTool, FishingFishTool, FishingShopTool,
    FishingBagTool, FishingSellTool, FishingLevelTool,
    FishingCdTool, FishingBuyTool, FishingGiveTool,
    FishingRankTool, FishingMyRodsTool, FishingEquipTool,
    FishingMyBaitsTool, FishingEquipBaitTool, FishingShopRefreshTool,
    FishingCollectionTool, FishingAchievementsTool,
    FishingAuctionTool, FishingEnchantTool, FishingEnchantUpgradeTool,
    FishingDirectedEnchantTool, FishingUpgradeShopTool, FishingGreedyToggleTool,
    FishingGreedyContinueTool, FishingGreedyCashoutTool,
)
import time
import asyncio
import difflib
import html
from .fuzzy_utils import extract_fuzzy_content, build_fuzzy_candidates


@register("fishing_game", "AstrBot", "钓鱼游戏插件 - 群聊娱乐插件，支持钓鱼、背包、商店、赠送等完整经济系统", "V4.6.1")
class FishingGamePlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.context = context
        self.config = config or {}

        # 读取冷却时间配置（秒）
        self.fishing_cooldown = self.config.get("fishing_cooldown", 4 * 3600)
        self.shop_refresh_cooldown = self.config.get("shop_refresh_cooldown", 1 * 3600)
        # 读取拍卖行配置
        self.auction_default_price_percent = self.config.get("auction_default_price_percent", 0.30)
        self.auction_price_range_percent = self.config.get("auction_price_range_percent", 0.30)
        self.auction_duration_hours = self.config.get("auction_duration_hours", 24)
        # 读取模糊匹配配置
        self.fuzzy_match_threshold = self.config.get("fuzzy_match_threshold", 0.6)
        self.fuzzy_match_threshold = max(0.0, min(1.0, float(self.fuzzy_match_threshold)))
        # 将游戏命令与 LLM 工具的最终回复渲染成游戏主题图片。
        self.llm_result_image_enabled = bool(self.config.get("llm_result_image_enabled", True))
        self._pending_image_results = {}
        # 读取管理员 UID 列表
        admin_uids_str = self.config.get("admin_uids", "")
        self.admin_uids = set(uid.strip() for uid in admin_uids_str.split(",") if uid.strip())
        logger.info(f"钓鱼游戏配置: 钓鱼CD={self.fishing_cooldown}s, 商店刷新CD={self.shop_refresh_cooldown}s, "
                    f"拍卖默认价格={self.auction_default_price_percent}, 拍卖浮动={self.auction_price_range_percent}, "
                    f"拍卖保留时长={self.auction_duration_hours}h, 模糊匹配阈值={self.fuzzy_match_threshold}, "
                    f"游戏结果图片={self.llm_result_image_enabled}, "
                    f"管理员数量={len(self.admin_uids)}")

        self.storage = StorageManager(self)

        # 初始化各命令模块
        self.equipment_cmds = EquipmentCommands(self, self.storage)
        self.fishing_cmds = FishingCommands(self, self.storage)
        self.info_cmds = InfoCommands(self, self.storage)
        self.economy_cmds = EconomyCommands(self, self.storage)
        self.social_cmds = SocialCommands(self, self.storage)
        self.auction_cmds = AuctionCommands(self, self.storage)
        self.enchant_cmds = EnchantCommands(self, self.storage)
        self.achievement_cmds = AchievementCommands(self, self.storage)
        self.admin_cmds = AdminCommands(self, self.storage)

        # 命令名 -> (模块实例, 方法名) 映射
        self._cmd_map = self._build_cmd_map()

        # 模糊匹配关键词库与精确命令集合
        self._fuzzy_keywords = self._build_fuzzy_keywords()
        self._exact_commands = self._build_exact_commands()
        self._cmd_arg_types = self._build_cmd_arg_types()

        # 注册 LLM FunctionTool（支持多步 tool calling）
        self._register_llm_tools()

        # 每日自动刷新定时任务（每天0点重置）
        self._refresh_task = None
        self._schedule_daily_refresh()

        # 拍卖行过期检查定时任务（每小时检查）
        self._auction_check_task = None
        self._schedule_auction_check()
        logger.info("钓鱼游戏插件已加载")

    def _build_cmd_map(self) -> dict:
        """构建命令名到模块实例的映射"""
        return {
            # 装备管理
            'cmd_myrods': (self.equipment_cmds, 'cmd_myrods'),
            'cmd_equip_rod': (self.equipment_cmds, 'cmd_equip_rod'),
            'cmd_mybaits': (self.equipment_cmds, 'cmd_mybaits'),
            'cmd_equip_bait': (self.equipment_cmds, 'cmd_equip_bait'),
            # 钓鱼核心
            'cmd_fish': (self.fishing_cmds, 'cmd_fish'),
            # 信息查询
            'cmd_help': (self.info_cmds, 'cmd_help'),
            'cmd_bag': (self.info_cmds, 'cmd_bag'),
            'cmd_level': (self.info_cmds, 'cmd_level'),
            'cmd_collection': (self.info_cmds, 'cmd_collection'),
            'cmd_cd': (self.info_cmds, 'cmd_cd'),
            'cmd_rank': (self.info_cmds, 'cmd_rank'),
            # 经济系统
            'cmd_sell': (self.economy_cmds, 'cmd_sell'),
            'cmd_shop': (self.economy_cmds, 'cmd_shop'),
            'cmd_buy': (self.economy_cmds, 'cmd_buy'),
            'cmd_shop_refresh': (self.economy_cmds, 'cmd_shop_refresh'),
            'cmd_upgrade_shop': (self.economy_cmds, 'cmd_upgrade_shop'),
            # 社交系统
            'cmd_give': (self.social_cmds, 'cmd_give'),
            # 拍卖行
            'cmd_auction': (self.auction_cmds, 'cmd_auction'),
            # 附魔系统
            'cmd_enchant': (self.enchant_cmds, 'cmd_enchant'),
            'cmd_enchant_upgrade': (self.enchant_cmds, 'cmd_enchant_upgrade'),
            'cmd_directed_enchant': (self.enchant_cmds, 'cmd_directed_enchant'),
            'cmd_greedy_toggle': (self.enchant_cmds, 'cmd_greedy_toggle'),
            'cmd_greedy_continue': (self.fishing_cmds, 'cmd_greedy_continue'),
            'cmd_greedy_cashout': (self.fishing_cmds, 'cmd_greedy_cashout'),
            # 成就系统
            'cmd_achievements': (self.achievement_cmds, 'cmd_achievements'),
            # 管理员系统
            'cmd_admin': (self.admin_cmds, 'cmd_admin'),
        }

    def _build_fuzzy_keywords(self) -> dict:
        """构建模糊匹配关键词库：命令键 -> 可识别关键词列表"""
        return {
            'cmd_fish': ['钓鱼', '钓', '垂钓', 'fish', 'fishing', 'diaoyu', '钓一下', '去钓鱼'],
            'cmd_bag': ['背包', '我的背包', '查看背包', 'bag', 'inventory', 'inv', 'beibao'],
            'cmd_sell': ['卖鱼', '出售', 'sell', 'sellfish', '卖', 'maiyu'],
            'cmd_shop': ['商店', '商城', 'shop', 'store', 'market', '买东西'],
            'cmd_buy': ['购买', '买', 'buy', 'purchase'],
            'cmd_level': ['等级', '经验', 'level', 'lvl', 'dengji'],
            'cmd_cd': ['冷却', 'cd', '冷却时间', 'cooldown'],
            'cmd_rank': ['排行榜', '排名', 'rank', 'ranking', 'leaderboard', 'top'],
            'cmd_help': ['帮助', 'help', '命令', 'commands', '菜单', 'menu', 'helpme'],
            'cmd_collection': ['图鉴', '收集', 'collection', 'pokedex', '鱼类图鉴'],
            'cmd_myrods': ['我的钓竿', '我的鱼竿', '鱼竿', '钓竿', 'rods', 'myrods', 'fishingrods'],
            'cmd_equip_rod': ['装备钓竿', '装备鱼竿', '换钓竿', '换鱼竿', 'equip', 'equiprod', 'userod'],
            'cmd_mybaits': ['我的鱼饵', '鱼饵', 'baits', 'mybaits'],
            'cmd_equip_bait': ['装备鱼饵', '换鱼饵', 'equipbait', 'usebait'],
            'cmd_give': ['赠送', '给', 'give', 'donate', 'send'],
            'cmd_auction': ['拍卖', '拍卖行', 'auction', 'auctionhouse', 'ah'],
            'cmd_enchant': ['附魔', '强化', 'enchant', 'ench', '魔改'],
            'cmd_enchant_upgrade': ['附魔升级', '升级附魔', 'enchant_upgrade', 'upgrade_enchant'],
            'cmd_directed_enchant': ['定向附魔', 'directed_enchant', 'target_enchant'],
            'cmd_greedy_toggle': ['切换贪婪', '贪婪切换', 'greedy_toggle', 'toggle_greedy'],
            'cmd_greedy_continue': ['贪婪', '继续贪婪', 'greedy_continue', 'continue_greedy'],
            'cmd_greedy_cashout': ['收杆', '结算贪婪', 'greedy_cashout', 'cashout_greedy'],
            'cmd_achievements': ['成就', 'achievements', 'achievement', 'trophy'],
            'cmd_shop_refresh': ['刷新商店', 'shop_refresh', 'refresh_shop'],
            'cmd_upgrade_shop': ['升级商店', 'upgrade_shop', 'shop_upgrade'],
        }

    def _build_exact_commands(self) -> set:
        """构建所有精确命中的命令名与别名集合，避免模糊入口重复响应"""
        exact = {
            # 装备管理
            '我的钓竿', 'myrods', '我的鱼竿',
            '装备钓竿', 'equip',
            '我的鱼饵', 'mybaits',
            '装备鱼饵', 'equip_bait',
            # 钓鱼核心
            '钓鱼', 'fish',
            # 信息查询
            '背包', 'bag',
            '卖鱼', 'sell',
            '等级', 'level',
            '冷却', 'cd',
            '商店', 'shop',
            '购买', 'buy',
            '刷新商店', 'shop_refresh',
            '升级商店', 'upgrade_shop',
            '排行榜', 'rank',
            '帮助', 'help',
            '图鉴', 'collection',
            # 社交系统
            '赠送', 'give',
            # 拍卖行
            '拍卖', 'auction', '拍卖行',
            # 附魔系统
            '附魔', 'enchant',
            '附魔升级', 'enchant_upgrade',
            '定向附魔', 'directed_enchant',
            '切换贪婪', 'greedy_toggle',
            '贪婪', '继续贪婪', 'greedy_continue',
            '收杆', '结算贪婪', 'greedy_cashout',
            # 成就系统
            '成就', 'achievements',
            # 管理员系统
            '管理', 'admin',
        }
        return exact

    def _build_cmd_arg_types(self) -> dict:
        """构建命令参数类型映射，用于模糊入口手动转换参数"""
        return {
            'cmd_equip_rod': [int],
            'cmd_equip_bait': [int],
            'cmd_buy': [int, int],
            'cmd_sell': [str],
            'cmd_give': [str, str, str, int],
            'cmd_auction': [str, str, str, str],
            'cmd_enchant': [int],
            'cmd_enchant_upgrade': [str, str],
            'cmd_directed_enchant': [str, str],
            'cmd_greedy_toggle': [int],
            'cmd_greedy_continue': [],
            'cmd_greedy_cashout': [],
        }

    def _fuzzy_match_command(self, word: str) -> tuple:
        """对用户输入的命令词进行模糊匹配，返回 (命令键, 相似度)

        当最高相似度达到阈值时返回对应命令键，否则返回 (None, 0.0)。
        """
        if not word:
            return None, 0.0
        all_keywords = []
        for cmd_key, keywords in self._fuzzy_keywords.items():
            for kw in keywords:
                all_keywords.append((kw, cmd_key))
        matches = difflib.get_close_matches(
            word,
            [kw for kw, _ in all_keywords],
            n=1,
            cutoff=self.fuzzy_match_threshold
        )
        if not matches:
            return None, 0.0
        matched_word = matches[0]
        for kw, cmd_key in all_keywords:
            if kw == matched_word:
                # 计算实际相似度
                ratio = difflib.SequenceMatcher(None, word, matched_word).ratio()
                return cmd_key, ratio
        return None, 0.0

    def _convert_fuzzy_args(self, cmd_key: str, raw_args: list) -> list:
        """根据命令参数类型映射，将字符串参数转换为目标类型"""
        arg_types = self._cmd_arg_types.get(cmd_key, [])
        converted = []
        for i, arg in enumerate(raw_args):
            if i < len(arg_types):
                try:
                    converted.append(arg_types[i](arg))
                except (ValueError, TypeError):
                    # 转换失败时保留原始字符串，让业务层自行校验
                    converted.append(arg)
            else:
                converted.append(arg)
        return converted

    @filter.regex(r"^[\s\S]+$", priority=1)
    async def cmd_fuzzy_entry(self, event: AstrMessageEvent):
        '''模糊命令入口 - 识别 /钓一下、／查看背包及已剥离前缀的唤醒命令
        
        正则需要兼容 AstrBot 不同版本对命令前缀的处理；方法内部会过滤普通聊天。
        '''
        try:
            text = event.message_str.strip()
            content = extract_fuzzy_content(event, text)
            if not content:
                return

            first_word = content.split()[0].lower()
            # 精确命令已由 @filter.command 处理，此处静默忽略。
            if first_word in self._exact_commands:
                return

            matched_cmd = None
            ratio = 0.0
            command_word = ""
            raw_args = []
            for candidate, candidate_args in build_fuzzy_candidates(content):
                candidate_cmd, candidate_ratio = self._fuzzy_match_command(candidate)
                if candidate_cmd and candidate_ratio > ratio:
                    command_word = candidate
                    matched_cmd = candidate_cmd
                    ratio = candidate_ratio
                    raw_args = candidate_args
            if not matched_cmd:
                return

            args = self._convert_fuzzy_args(matched_cmd, raw_args)
            logger.info(f"模糊命令匹配: /{command_word} -> {matched_cmd} (相似度 {ratio:.2f}), 参数: {args}")
            async for r in self._route_cmd(event, matched_cmd, *args):
                yield r
            # 命中后阻止事件继续传播，避免触发 LLM 工具
            event.stop_event()
        except Exception as e:
            logger.error(f"模糊命令入口处理失败: {e}")

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
            FishingAchievementsTool(plugin=self),
            FishingAuctionTool(plugin=self),
            FishingEnchantTool(plugin=self),
            FishingEnchantUpgradeTool(plugin=self),
            FishingDirectedEnchantTool(plugin=self),
            FishingUpgradeShopTool(plugin=self),
            FishingGreedyToggleTool(plugin=self),
            FishingGreedyContinueTool(plugin=self),
            FishingGreedyCashoutTool(plugin=self),
        ]
        self.context.add_llm_tools(*tools)
        logger.info(f"已注册 {len(tools)} 个 Fishing FunctionTool")

    def _seconds_until_midnight(self) -> int:
        """计算距离下一个 00:00:00 的秒数"""
        now = time.localtime()
        elapsed = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec
        return 86400 - elapsed

    async def _auction_check_loop(self):
        """拍卖行过期检查 - 每小时执行一次"""
        while True:
            try:
                await asyncio.sleep(3600)
                logger.info("执行拍卖行过期检查")
                try:
                    expired = await self.storage.get_expired_listings()
                    if expired:
                        returned_count = 0
                        for listing in expired:
                            try:
                                seller_id = listing["seller_id"]
                                async with self.storage.get_user_lock(seller_id):
                                    seller = await self.storage.get_user(seller_id)
                                    item_data = listing.get("item_data", {})
                                    item_type = item_data.get("type", "")

                                    if item_type == "rod":
                                        seller.add_rod(
                                            item_data["base_id"],
                                            item_data["prefix_id"],
                                            item_data.get("skills", {}),
                                            item_data.get("enchant_count", 0),
                                            item_data.get("instance_id")
                                        )
                                    elif item_type == "bait":
                                        seller.add_bait(item_data["base_id"], item_data["prefix_id"], item_data.get("count", 1))
                                    elif item_type == "fish":
                                        seller.add_fish(item_data["fish_id"], item_data["prefix_id"], item_data.get("count", 1))
                                    elif item_type == "ticket":
                                        seller.add_enchant_ticket(item_data["ticket_id"], item_data.get("count", 1))
                                    elif item_type == "item":
                                        seller.add_item(item_data["item_id"], item_data.get("count", 1))

                                    notices = seller.get("auction_notices", [])
                                    notices.append(f"你上架的 {item_data.get('name', '物品')} 已过期退回")
                                    seller.set("auction_notices", notices[-10:])

                                    await self.storage.save_user(seller)
                                returned_count += 1
                            except Exception as e:
                                logger.error(f"退还拍卖物品 {listing.get('id')} 失败: {e}")

                        await self.storage.remove_expired_listings([lst["id"] for lst in expired])
                        logger.info(f"已退还 {returned_count} 件过期拍卖物品")
                except Exception as e:
                    logger.error(f"拍卖行过期检查失败: {e}")
            except asyncio.CancelledError:
                logger.info("拍卖行检查任务已取消")
                break
            except Exception as e:
                logger.error(f"拍卖行检查任务异常: {e}")
                await asyncio.sleep(300)

    def _schedule_auction_check(self):
        """启动拍卖行过期检查异步任务"""
        self._auction_check_task = asyncio.create_task(self._auction_check_loop())

    async def _daily_refresh_loop(self):
        """每日自动刷新所有用户数据 - 异步协程"""
        while True:
            try:
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
                            async with self.storage.get_user_lock(uid):
                                user = await self.storage.get_user(uid)
                                user.check_and_reset_daily_give()
                                await self.storage.save_user(user)
                            reset_count += 1
                        except Exception as e:
                            logger.error(f"重置用户 {uid} 每日赠送次数失败: {e}")
                    logger.info(f"已重置 {reset_count} 位用户的每日赠送次数")
                    
                    # 重建嫉妒前缀所需的等级分布缓存
                    await self.storage.update_level_distribution_cache()
                    logger.info("已重建等级分布缓存")
                except Exception as e:
                    logger.error(f"每日刷新执行失败: {e}")

                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("每日刷新任务已取消")
                break
            except Exception as e:
                logger.error(f"每日刷新任务异常: {e}")
                await asyncio.sleep(300)

    def _schedule_daily_refresh(self):
        """启动每日自动刷新异步任务"""
        self._refresh_task = asyncio.create_task(self._daily_refresh_loop())

    async def _get_greedy_obscurity_intensity(self, user_id: str) -> float:
        """获取无尽贪婪的文字侵蚀强度，未触发时返回零。"""
        try:
            user = await self.storage.get_user(user_id)
            rod = user.current_rod
            prefix = get_rod_prefix(rod.get("prefix_id", ""))
            if prefix.get("skills", {}).get("endless_greedy"):
                return min(user.coins / 100000, 1.0)
        except Exception as exc:
            logger.warning(f"读取贪婪文字效果失败: {exc}")
        return 0.0

    async def _apply_greedy_scramble(self, user_id: str, text: str) -> str:
        """如果用户装备无尽贪婪钓竿，用黑色方块侵蚀返回文字。"""
        if not text:
            return text
        intensity = await self._get_greedy_obscurity_intensity(user_id)
        return obscure_text(text, intensity) if intensity > 0 else text

    def _mark_result_for_image(
        self, event, greedy_intensity: float, cmd_name: str = "",
        cmd_args: tuple = (), cmd_kwargs: dict = None, command_result: str = "",
    ) -> None:
        """标记游戏命令事件，等待最终结果进入图片渲染。"""
        now = time.monotonic()
        self._pending_image_results = {
            event_id: state
            for event_id, state in self._pending_image_results.items()
            if now - state["created_at"] < 300
        }
        self._pending_image_results[id(event)] = {
            "created_at": now,
            "greedy_intensity": greedy_intensity,
            "cmd_name": cmd_name,
            "cmd_args": tuple(cmd_args),
            "cmd_kwargs": dict(cmd_kwargs or {}),
            "command_result": command_result,
        }

    async def _cmd_with_scramble(self, event, cmd_name: str, *args, **kwargs):
        """执行 LLM 工具命令；完整结果供模型推理，视觉效果留到最终回复。"""
        if cmd_name not in self._cmd_map:
            return f"[系统错误: 未知命令 {cmd_name}]"
        module, method_name = self._cmd_map[cmd_name]
        cmd_func = getattr(module, method_name)
        result = await cmd_func(event, *args, **kwargs)
        intensity = await self._get_greedy_obscurity_intensity(event.get_sender_id())
        if self.llm_result_image_enabled:
            self._mark_result_for_image(
                event, intensity, cmd_name, args, kwargs, result,
            )
            return result
        return obscure_text(result, intensity) if intensity > 0 else result

    @filter.on_decorating_result()
    async def render_fishing_result(self, event: AstrMessageEvent):
        """把游戏命令或 LLM 工具的纯文本结果替换为彩色图片。"""
        state = self._pending_image_results.pop(id(event), None)
        if not self.llm_result_image_enabled or not state:
            return

        result = event.get_result()
        chain = getattr(result, "chain", None) if result else None
        if not chain:
            return

        plain_parts = [component.text for component in chain if isinstance(component, Comp.Plain)]
        text = "".join(plain_parts).strip()
        if not text:
            return

        intensity = state.get("greedy_intensity", 0.0)
        if intensity > 0:
            text = obscure_text(text, intensity)

        try:
            template = RESULT_IMAGE_TEMPLATE
            template_data = {
                "content_html": render_result_html(text),
                "sender_name": html.escape(event.get_sender_name() or "垂钓者"),
            }
            if state.get("cmd_name") == "cmd_bag":
                user_id = event.get_sender_id()
                async with self.storage.get_user_lock(user_id):
                    user = await self.storage.get_user(user_id)
                    template_data = build_backpack_view(user, event.get_sender_name())
                template = BACKPACK_IMAGE_TEMPLATE
            elif state.get("cmd_name") == "cmd_myrods":
                user_id = event.get_sender_id()
                async with self.storage.get_user_lock(user_id):
                    user = await self.storage.get_user(user_id)
                    template_data = build_rods_view(user, event.get_sender_name())
                template = RODS_IMAGE_TEMPLATE
            elif state.get("cmd_name") in ("cmd_shop", "cmd_shop_refresh"):
                # 刷新失败时保留原始错误结果，避免展示未刷新的货架造成误解。
                refresh_succeeded = state.get("command_result", "").startswith("✅ 商店已刷新")
                if state.get("cmd_name") == "cmd_shop" or refresh_succeeded:
                    user_id = event.get_sender_id()
                    async with self.storage.get_user_lock(user_id):
                        user = await self.storage.get_user(user_id)
                        template_data = build_shop_view(user, event.get_sender_name())
                    template = SHOP_IMAGE_TEMPLATE
            elif state.get("cmd_name") == "cmd_auction":
                cmd_args = state.get("cmd_args", ())
                action = str(cmd_args[0] if cmd_args else "list").lower()
                keyword = ""
                page = 1
                can_render_market = action in ("list", "列表")
                if can_render_market and len(cmd_args) > 1:
                    try:
                        page = max(1, int(cmd_args[1]))
                    except (TypeError, ValueError):
                        page = 1
                if action in ("search", "搜索") and len(cmd_args) > 1 and cmd_args[1]:
                    can_render_market = True
                    keyword = str(cmd_args[1])
                    if len(cmd_args) > 2:
                        try:
                            page = max(1, int(cmd_args[2]))
                        except (TypeError, ValueError):
                            page = 1
                if can_render_market:
                    listings, total = await self.storage.search_auctions(keyword, page, 10)
                    template_data = build_auction_view(
                        listings, total, page, keyword, event.get_sender_id(),
                    )
                    template = AUCTION_IMAGE_TEMPLATE
            elif state.get("cmd_name") in ("cmd_mybaits", "cmd_collection", "cmd_achievements"):
                user_id = event.get_sender_id()
                async with self.storage.get_user_lock(user_id):
                    user = await self.storage.get_user(user_id)
                    if state.get("cmd_name") == "cmd_mybaits":
                        template_data = build_baits_view(user, event.get_sender_name())
                        template = BAITS_IMAGE_TEMPLATE
                    elif state.get("cmd_name") == "cmd_collection":
                        template_data = build_collection_view(user, event.get_sender_name())
                        template = COLLECTION_IMAGE_TEMPLATE
                    else:
                        template_data = build_achievements_view(user, event.get_sender_name())
                        template = ACHIEVEMENTS_IMAGE_TEMPLATE
            elif state.get("cmd_name") in ("cmd_fish", "cmd_greedy_continue", "cmd_greedy_cashout"):
                template_data = build_fishing_result_view(
                    state.get("command_result", text), event.get_sender_name(),
                )
                template = FISHING_IMAGE_TEMPLATE

            image_url = await self.html_render(
                template,
                template_data,
                options={"type": "png", "full_page": True, "animations": "disabled"},
            )
            image_chain = event.image_result(image_url).chain
            new_chain = []
            image_inserted = False
            for component in chain:
                if isinstance(component, Comp.Plain):
                    if not image_inserted:
                        new_chain.extend(image_chain)
                        image_inserted = True
                    continue
                new_chain.append(component)
            result.chain = new_chain
        except Exception as exc:
            # 保留文本消息链；无尽贪婪仍应维持黑方块侵蚀效果。
            if intensity > 0:
                text_inserted = False
                for component in chain:
                    if isinstance(component, Comp.Plain):
                        component.text = text if not text_inserted else ""
                        text_inserted = True
            if is_t2i_service_error(exc):
                logger.warning(f"AstrBot T2I 图片服务暂时不可用，钓鱼结果已回退文本: {exc}")
            else:
                logger.error(f"钓鱼游戏结果图片渲染失败，已回退文本: {exc}")

    # ========== 命令代理 ==========
    # 所有命令通过统一的 _route_cmd 方法分派到对应模块

    async def _route_cmd(self, event: AstrMessageEvent, cmd_key: str, *args, **kwargs):
        """统一命令路由：执行命令，并按配置进入图片或纯文本结果。"""
        module, method_name = self._cmd_map[cmd_key]
        cmd_func = getattr(module, method_name)
        result = await cmd_func(event, *args, **kwargs)
        if self.llm_result_image_enabled and cmd_key != "cmd_admin":
            intensity = await self._get_greedy_obscurity_intensity(event.get_sender_id())
            self._mark_result_for_image(
                event, intensity, cmd_key, args, kwargs, result,
            )
        else:
            result = await self._apply_greedy_scramble(event.get_sender_id(), result)
        yield event.plain_result(result)

    # ---------- 装备管理 ----------

    @filter.command("我的钓竿", alias={"myrods"})
    async def cmd_myrods(self, event: AstrMessageEvent):
        '''我的钓竿 - 查看你拥有的所有钓竿'''
        async for r in self._route_cmd(event, 'cmd_myrods'): yield r

    @filter.command("我的鱼竿")
    async def cmd_myrods_yu(self, event: AstrMessageEvent):
        '''我的鱼竿 - 查看你拥有的所有钓竿（同/我的钓竿）'''
        async for r in self._route_cmd(event, 'cmd_myrods'): yield r

    @filter.command("装备钓竿", alias={"equip"})
    async def cmd_equip_rod(self, event: AstrMessageEvent, index: int):
        '''装备钓竿 - 切换当前使用的钓竿'''
        async for r in self._route_cmd(event, 'cmd_equip_rod', index): yield r

    @filter.command("我的鱼饵", alias={"mybaits"})
    async def cmd_mybaits(self, event: AstrMessageEvent):
        '''我的鱼饵 - 查看你拥有的所有鱼饵'''
        async for r in self._route_cmd(event, 'cmd_mybaits'): yield r

    @filter.command("装备鱼饵", alias={"equip_bait"})
    async def cmd_equip_bait(self, event: AstrMessageEvent, index: int):
        '''装备鱼饵 - 切换当前使用的鱼饵'''
        async for r in self._route_cmd(event, 'cmd_equip_bait', index): yield r

    # ---------- 钓鱼核心 ----------

    @filter.command("钓鱼", alias={"fish"})
    async def cmd_fish(self, event: AstrMessageEvent):
        '''钓鱼 - 开始钓鱼，消耗1个鱼饵，获得随机鱼类'''
        async for r in self._route_cmd(event, 'cmd_fish'): yield r

    # ---------- 信息查询 ----------

    @filter.command("背包", alias={"bag"})
    async def cmd_bag(self, event: AstrMessageEvent):
        '''背包 - 查看你的渔获、鱼饵、金币等信息'''
        async for r in self._route_cmd(event, 'cmd_bag'): yield r

    @filter.command("卖鱼", alias={"sell"})
    async def cmd_sell(self, event: AstrMessageEvent, fish_id_or_all: str = "all"):
        '''卖鱼 - 出售渔获获取金币，支持指定鱼ID或"全部"'''
        async for r in self._route_cmd(event, 'cmd_sell', fish_id_or_all): yield r

    @filter.command("等级", alias={"level"})
    async def cmd_level(self, event: AstrMessageEvent):
        '''等级 - 查看当前等级和经验进度'''
        async for r in self._route_cmd(event, 'cmd_level'): yield r

    @filter.command("冷却", alias={"cd"})
    async def cmd_cd(self, event: AstrMessageEvent):
        '''冷却 - 查看钓鱼和商店刷新的冷却时间'''
        async for r in self._route_cmd(event, 'cmd_cd'): yield r

    @filter.command("商店", alias={"shop"})
    async def cmd_shop(self, event: AstrMessageEvent):
        '''商店 - 查看可购买的钓竿和鱼饵'''
        async for r in self._route_cmd(event, 'cmd_shop'): yield r

    @filter.command("购买", alias={"buy"})
    async def cmd_buy(self, event: AstrMessageEvent, index: int, quantity: int = 1):
        '''购买 - 从商店购买物品，用法: /购买 编号 [数量]'''
        async for r in self._route_cmd(event, 'cmd_buy', index, quantity): yield r

    @filter.command("刷新商店", alias={"shop_refresh"})
    async def cmd_shop_refresh(self, event: AstrMessageEvent):
        '''刷新商店 - 手动刷新商店商品，消耗50金币或使用刷新券'''
        async for r in self._route_cmd(event, 'cmd_shop_refresh'): yield r

    @filter.command("升级商店", alias={"upgrade_shop"})
    async def cmd_upgrade_shop(self, event: AstrMessageEvent):
        '''升级商店 - 增加商店展示的商品条数'''
        async for r in self._route_cmd(event, 'cmd_upgrade_shop'): yield r

    @filter.command("排行榜", alias={"rank"})
    async def cmd_rank(self, event: AstrMessageEvent):
        '''排行榜 - 查看钓鱼次数排行榜'''
        async for r in self._route_cmd(event, 'cmd_rank'): yield r

    @filter.command("帮助", alias={"help"})
    async def cmd_help(self, event: AstrMessageEvent):
        '''帮助 - 查看钓鱼游戏帮助信息'''
        async for r in self._route_cmd(event, 'cmd_help'): yield r

    @filter.command("图鉴", alias={"collection"})
    async def cmd_collection(self, event: AstrMessageEvent):
        '''图鉴 - 查看已收集的鱼类图鉴进度'''
        async for r in self._route_cmd(event, 'cmd_collection'): yield r

    # ---------- 社交系统 ----------

    @filter.command("赠送", alias={"give"})
    async def cmd_give(self, event: AstrMessageEvent, target_user: str, item_type: str, item_id: str = "", quantity: int = 1):
        '''赠送 - 赠送物品给其他用户，用法: /赠送 @用户 物品类型 物品ID [数量]
        物品类型: coins(金币), fish(渔获), bait(鱼饵), rod(钓竿)'''
        async for r in self._route_cmd(event, 'cmd_give', target_user, item_type, item_id, quantity): yield r

    # ---------- 拍卖行 ----------

    @filter.command("拍卖", alias={"auction"})
    async def cmd_auction(self, event: AstrMessageEvent, action: str = "list", arg1: str = "", arg2: str = "", arg3: str = ""):
        '''拍卖行 - 浏览/搜索/上架/出售/取消/购买拍卖物品，默认显示列表
        用法: /拍卖 [操作] [参数1] [参数2] [参数3]
        操作: 列表/搜索/上架/出售/取消/购买'''
        async for r in self._route_cmd(event, 'cmd_auction', action, arg1, arg2, arg3): yield r

    @filter.command("拍卖行")
    async def cmd_auction_hang(self, event: AstrMessageEvent):
        '''拍卖行 - 快速浏览拍卖行列表'''
        async for r in self._route_cmd(event, 'cmd_auction', "list"): yield r

    # ---------- 附魔系统 ----------

    @filter.command("附魔", alias={"enchant"})
    async def cmd_enchant(self, event: AstrMessageEvent, rod_index: int = 0):
        '''附魔 - 为指定编号的钓竿随机附魔技能，消耗金币或附魔券。不传编号则默认附魔当前装备钓竿。'''
        async for r in self._route_cmd(event, 'cmd_enchant', rod_index): yield r

    @filter.command("附魔升级", alias={"enchant_upgrade"})
    async def cmd_enchant_upgrade(self, event: AstrMessageEvent, arg1: str = "", arg2: str = ""):
        '''附魔升级 - 升级指定钓竿的指定技能，消耗金币。用法: /附魔升级 [技能名] [钓竿编号]
        示例: /附魔升级 迅捷    /附魔升级 神慧 2'''
        async for r in self._route_cmd(event, 'cmd_enchant_upgrade', arg1, arg2): yield r

    @filter.command("定向附魔", alias={"directed_enchant"})
    async def cmd_directed_enchant(self, event: AstrMessageEvent, skill_name: str = "", tier_str: str = ""):
        '''定向附魔 - 使用定向附魔券为当前装备钓竿添加/升级指定技能。用法: /定向附魔 [技能名] [档位]
        示例: /定向附魔 远航 10    /定向附魔 迅捷 5'''
        async for r in self._route_cmd(event, 'cmd_directed_enchant', skill_name, tier_str): yield r

    @filter.command("切换贪婪", alias={"greedy_toggle"})
    async def cmd_greedy_toggle(self, event: AstrMessageEvent, rod_index: int = 0):
        '''切换贪婪 - 在「贪婪的」与「无尽贪婪的」钓竿前缀之间切换。不传编号则默认切换当前装备钓竿。
        示例: /切换贪婪    /切换贪婪 2'''
        async for r in self._route_cmd(event, 'cmd_greedy_toggle', rod_index): yield r

    @filter.command("贪婪", alias={"继续贪婪", "greedy_continue"})
    async def cmd_greedy_continue(self, event: AstrMessageEvent):
        '''贪婪 - 继续当前的贪婪挂起状态，用贪欲结晶再次抛竿'''
        async for r in self._route_cmd(event, 'cmd_greedy_continue'): yield r

    @filter.command("收杆", alias={"结算贪婪", "greedy_cashout"})
    async def cmd_greedy_cashout(self, event: AstrMessageEvent):
        '''收杆 - 结算当前贪欲结晶，获得金币与经验'''
        async for r in self._route_cmd(event, 'cmd_greedy_cashout'): yield r

    # ---------- 成就系统 ----------

    @filter.command("成就", alias={"achievements"})
    async def cmd_achievements(self, event: AstrMessageEvent):
        '''成就 - 查看已解锁的成就列表与进度'''
        async for r in self._route_cmd(event, 'cmd_achievements'): yield r

    # ---------- 管理员系统 ----------

    @filter.command("管理", alias={"admin"})
    async def cmd_admin(
        self, event: AstrMessageEvent, action: str = "", arg1: str = "",
        arg2: str = "", arg3: str = "", arg4: str = "", arg5: str = "",
        arg6: str = "", arg7: str = "", arg8: str = "", arg9: str = "",
        arg10: str = "", arg11: str = "", arg12: str = "", arg13: str = "",
        arg14: str = "",
    ):
        '''管理 - 管理员命令入口'''
        async for r in self._route_cmd(
            event, 'cmd_admin', action, arg1, arg2, arg3, arg4, arg5, arg6,
            arg7, arg8, arg9, arg10, arg11, arg12, arg13, arg14,
        ): yield r

    # ---------- 生命周期 ----------

    async def terminate(self):
        '''插件卸载时调用'''
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        if self._auction_check_task:
            self._auction_check_task.cancel()
            try:
                await self._auction_check_task
            except asyncio.CancelledError:
                pass
        logger.info("钓鱼游戏插件已卸载")
