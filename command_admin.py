"""管理员命令模块"""
import time
import re
from typing import Optional

from .commands_base import CommandBase
from .utils import (
    extract_target_user_id, format_rod_name, format_rod_skills, format_bait_name,
    can_apply_rod_prefix, get_available_skills, SKILL_NAME_MAP,
    parse_directed_enchant_id,
)
from .fish_data import (
    get_rod_by_id, get_rod_prefix, get_bait_by_id, get_bait_prefix,
    get_prefix_by_id, get_fish_by_id, calc_fish_value,
    FISH_TYPES, FISH_PREFIXES, ROD_BASES, ROD_PREFIXES,
    BAIT_BASES, BAIT_PREFIXES, ENCHANT_TICKETS, DIRECTED_ENCHANT_CONFIG,
    ROD_SKILL_DESCRIPTIONS,
)
from .storage import StorageManager


class AdminCommands(CommandBase):
    """管理员命令处理器"""

    ADMIN_LOG_KEY = "fishing_admin_logs"
    ADMIN_LOG_MAX = 100

    def _check_admin(self, event) -> bool:
        """检查发送者是否为配置中的管理员"""
        operator = event.get_sender_id()
        return operator in getattr(self.star, "admin_uids", set())

    def _parse_target_uid(self, raw: str) -> Optional[str]:
        """从参数中解析目标用户 UID"""
        if not raw:
            return None
        return extract_target_user_id(raw)

    async def _add_admin_log(self, operator: str, action: str, target: str = "", detail: str = ""):
        """记录管理员操作审计日志，最多保留最近 100 条"""
        logs = await self.storage.get_kv_data(self.ADMIN_LOG_KEY) or []
        logs.append({
            "timestamp": int(time.time()),
            "operator": operator,
            "action": action,
            "target": target,
            "detail": detail,
        })
        if len(logs) > self.ADMIN_LOG_MAX:
            logs = logs[-self.ADMIN_LOG_MAX:]
        await self.storage.put_kv_data(self.ADMIN_LOG_KEY, logs)

    def _admin_help(self) -> str:
        """管理员命令帮助文本"""
        return """🛠️ 管理员命令

用法: /管理 <子命令> [参数]

📋 子命令列表：
• 查看 <@用户/UID> - 查看玩家数据摘要
• 加金币 <@用户/UID> <数量> - 给玩家增加金币
• 减金币 <@用户/UID> <数量> - 减少玩家金币
• 设经验 <@用户/UID> <数量> - 设置玩家经验并自动计算等级
• 加钓竿 <@用户/UID> <base_id> [前缀id] [词条数值 ...] [附魔次数]
  支持“幸运25%”或“幸运 25%”，可连续指定多个词条
• 加券 <@用户/UID> <券ID> [数量] - 添加附魔券、刷新券或定向附魔券
• 删钓竿 <@用户/UID> <instance_id> - 删除玩家指定钓竿
• 清冷却 <@用户/UID> - 清空玩家钓鱼和商店冷却
• 全服发金币 <数量> - 给所有注册玩家发放金币
• 全服发鱼饵 <base_id> <prefix_id> <数量> - 给所有注册玩家发放鱼饵
• 统计 - 查看全服统计信息
• 物品ID [类别] [关键词] [页码] - 按名称或 ID 快速查询
  类别：鱼、钓竿、鱼饵、券、词条、前缀（也可直接输入中文名或 ID）
  示例：物品ID 贪婪；物品ID 钓竿 金币；物品ID 券 swift
• 日志 [页码] - 查看最近管理员操作日志
• 清空日志 - 清空所有审计日志

⚠️ 管理员 UID 请在 AstrBot 面板的 admin_uids 配置项中设置。"""

    async def cmd_admin(
        self, event, action: str = "", arg1: str = "", arg2: str = "",
        arg3: str = "", arg4: str = "", arg5: str = "", arg6: str = "",
        arg7: str = "", arg8: str = "", arg9: str = "", arg10: str = "",
        arg11: str = "", arg12: str = "", arg13: str = "", arg14: str = "",
    ) -> str:
        """管理员命令入口"""
        if not self._check_admin(event):
            return "❌ 你没有管理员权限"

        operator = event.get_sender_id()

        action = action.strip()
        if not action:
            return self._admin_help()

        sub_args = [
            a for a in (
                arg1, arg2, arg3, arg4, arg5, arg6,
                arg7, arg8, arg9, arg10, arg11, arg12, arg13, arg14,
            ) if a
        ]

        if action in ("帮助", "help", "?"):
            return self._admin_help()

        if action == "查看":
            return await self._cmd_admin_view(event, operator, sub_args)
        if action in ("加金币", "add_coins"):
            return await self._cmd_admin_add_coins(event, operator, sub_args)
        if action in ("减金币", "remove_coins"):
            return await self._cmd_admin_remove_coins(event, operator, sub_args)
        if action in ("设经验", "set_exp"):
            return await self._cmd_admin_set_exp(event, operator, sub_args)
        if action in ("加钓竿", "add_rod"):
            return await self._cmd_admin_add_rod(event, operator, sub_args)
        if action in ("加券", "add_ticket"):
            return await self._cmd_admin_add_ticket(event, operator, sub_args)
        if action in ("删钓竿", "remove_rod"):
            return await self._cmd_admin_remove_rod(event, operator, sub_args)
        if action in ("清冷却", "clear_cd"):
            return await self._cmd_admin_clear_cd(event, operator, sub_args)
        if action in ("全服发金币", "global_coins"):
            return await self._cmd_admin_global_coins(event, operator, sub_args)
        if action in ("全服发鱼饵", "global_bait"):
            return await self._cmd_admin_global_bait(event, operator, sub_args)
        if action in ("统计", "stats"):
            return await self._cmd_admin_stats(event, operator)
        if action in ("物品ID", "item_ids", "物品id"):
            return await self._cmd_admin_item_ids(event, operator, sub_args)
        if action in ("日志", "logs"):
            return await self._cmd_admin_logs(event, operator, sub_args)
        if action in ("清空日志", "clear_logs"):
            return await self._cmd_admin_clear_logs(event, operator)

        return f"❌ 未知的管理员子命令：{action}\n\n{self._admin_help()}"

    async def _get_target_user(self, sub_args: tuple, index: int = 0) -> Optional:
        """解析并获取目标用户，失败时返回 None（已在调用处处理错误）"""
        if len(sub_args) <= index:
            return None
        target_uid = self._parse_target_uid(sub_args[index])
        if not target_uid:
            return None
        if not await self.storage.user_exists(target_uid):
            return None
        return await self.storage.get_user(target_uid)

    async def _cmd_admin_view(self, event, operator: str, sub_args: tuple) -> str:
        """查看玩家数据摘要"""
        if len(sub_args) < 1:
            return "❌ 用法：/管理 查看 <@用户/UID>"

        target_uid = self._parse_target_uid(sub_args[0])
        if not target_uid:
            return "❌ 无法识别目标用户，请使用 @用户 或直接输入 UID"

        async with self._get_user_lock(target_uid):
            if not await self.storage.user_exists(target_uid):
                return f"❌ 用户 {target_uid} 不存在或尚未玩过钓鱼游戏"

            user = await self.storage.get_user(target_uid)
            rods = user.get_owned_rods()
            rod_text = "\n".join(
                f"  [{i+1}] {format_rod_name(r)} (instance: {r.get('instance_id', '-')})"
                for i, r in enumerate(rods)
            ) if rods else "  (无)"

            fish_count = sum(f.get("count", 0) for f in user.get_fish_inventory())
            total_value = user.get_total_inventory_value()

            result = f"""👤 玩家数据摘要

UID: {target_uid}
💰 金币: {user.coins}
📈 经验: {user.exp} (Lv.{user.level})
🐟 累计钓鱼: {user.total_fish_count} 次
📦 库存总价值: {total_value} 金币
🪤 鱼饵种类: {len(user.get_baits())}
🐠 渔获数量: {fish_count}

🎣 拥有的钓竿:
{rod_text}"""

        await self._add_admin_log(operator, "查看", target_uid, "查看玩家数据摘要")
        return result

    async def _cmd_admin_add_coins(self, event, operator: str, sub_args: tuple) -> str:
        """给目标玩家增加金币"""
        if len(sub_args) < 2:
            return "❌ 用法：/管理 加金币 <@用户/UID> <数量>"

        target_uid = self._parse_target_uid(sub_args[0])
        try:
            amount = int(sub_args[1])
        except ValueError:
            return "❌ 数量必须是整数"

        if amount <= 0:
            return "❌ 数量必须大于 0"

        async with self._get_user_lock(target_uid):
            if not target_uid or not await self.storage.user_exists(target_uid):
                return f"❌ 用户 {target_uid} 不存在"

            user = await self.storage.get_user(target_uid)
            old_coins = user.coins
            user.add_coins(amount)
            await self.storage.save_user(user)

        await self._add_admin_log(operator, "加金币", target_uid, f"增加 {amount}，修改前 {old_coins} -> 修改后 {user.coins}")
        return f"✅ 已为 {target_uid} 增加 {amount} 金币\n当前金币: {user.coins}"

    async def _cmd_admin_remove_coins(self, event, operator: str, sub_args: tuple) -> str:
        """减少目标玩家金币"""
        if len(sub_args) < 2:
            return "❌ 用法：/管理 减金币 <@用户/UID> <数量>"

        target_uid = self._parse_target_uid(sub_args[0])
        try:
            amount = int(sub_args[1])
        except ValueError:
            return "❌ 数量必须是整数"

        if amount <= 0:
            return "❌ 数量必须大于 0"

        async with self._get_user_lock(target_uid):
            if not target_uid or not await self.storage.user_exists(target_uid):
                return f"❌ 用户 {target_uid} 不存在"

            user = await self.storage.get_user(target_uid)
            old_coins = user.coins
            new_coins = max(0, user.coins - amount)
            user._data["coins"] = new_coins
            await self.storage.save_user(user)

        await self._add_admin_log(operator, "减金币", target_uid, f"减少 {amount}，修改前 {old_coins} -> 修改后 {new_coins}")
        return f"✅ 已为 {target_uid} 减少 {amount} 金币\n当前金币: {new_coins}"

    async def _cmd_admin_set_exp(self, event, operator: str, sub_args: tuple) -> str:
        """设置目标玩家经验并自动计算等级"""
        if len(sub_args) < 2:
            return "❌ 用法：/管理 设经验 <@用户/UID> <数量>"

        target_uid = self._parse_target_uid(sub_args[0])
        try:
            amount = int(sub_args[1])
        except ValueError:
            return "❌ 数量必须是整数"

        if amount < 0:
            return "❌ 经验不能为负数"

        async with self._get_user_lock(target_uid):
            if not target_uid or not await self.storage.user_exists(target_uid):
                return f"❌ 用户 {target_uid} 不存在"

            user = await self.storage.get_user(target_uid)
            old_exp = user.exp
            old_level = user.level
            user._data["exp"] = amount
            new_level = user._calc_level()
            user._data["level"] = new_level
            await self.storage.save_user(user)

        level_text = f"🎉 等级变化：Lv.{old_level} -> Lv.{new_level}" if new_level != old_level else f"等级保持：Lv.{new_level}"
        await self._add_admin_log(operator, "设经验", target_uid, f"设为 {amount}，经验 {old_exp}->{amount}，等级 {old_level}->{new_level}")
        return f"✅ 已设置 {target_uid} 经验为 {amount}\n{level_text}"

    async def _cmd_admin_add_rod(self, event, operator: str, sub_args: tuple) -> str:
        """给目标玩家添加钓竿"""
        if len(sub_args) < 2:
            return "❌ 用法：/管理 加钓竿 <@用户/UID> <base_id> [前缀id] [词条数值 ...] [附魔次数]"

        target_uid = self._parse_target_uid(sub_args[0])
        base_id = sub_args[1]
        prefix_id = sub_args[2] if len(sub_args) > 2 else "rod_pref_03"
        skill_args = list(sub_args[3:])
        enchant_count = 0
        if skill_args and re.fullmatch(r"\d+", skill_args[-1]):
            enchant_count = int(skill_args.pop())

        rod_base = get_rod_by_id(base_id)
        if not rod_base:
            return f"❌ 钓竿 base_id {base_id} 不存在"

        # 特种钓竿不带前缀
        if rod_base.get("no_prefix"):
            prefix_id = ""
        else:
            prefix_info = get_rod_prefix(prefix_id)
            # 校验前缀与基础钓竿兼容性（傲慢前缀白名单等）
            if not prefix_info:
                return f"❌ 钓竿前缀 {prefix_id} 不存在"
            if not can_apply_rod_prefix(base_id, prefix_id):
                return f"❌ 前缀 {prefix_info.get('name', prefix_id)} 不能附加到钓竿 {rod_base.get('name', base_id)} 上"

        skills = {}
        index = 0
        while index < len(skill_args):
            token = skill_args[index].strip()
            compact_match = re.fullmatch(r"(.+?)(-?\d+(?:\.\d+)?%?)", token)
            if compact_match:
                skill_name, skill_value_text = compact_match.groups()
                index += 1
            elif index + 1 < len(skill_args):
                skill_name = token
                skill_value_text = skill_args[index + 1].strip()
                index += 2
            else:
                return f"❌ 词条“{token}”缺少数值，例如：{token}25%"

            skill_id = SKILL_NAME_MAP.get(skill_name.lower(), skill_name.lower())
            if skill_id not in get_available_skills():
                return f"❌ 未知或不可附魔的词条：{skill_name}"
            if skill_id in skills:
                return f"❌ 词条重复：{skill_name}"
            try:
                value_text = skill_value_text.strip()
                skill_value = float(value_text[:-1]) / 100 if value_text.endswith("%") else float(value_text)
                if not value_text.endswith("%") and skill_value > 1:
                    skill_value /= 100
            except ValueError:
                return "❌ 词条数值必须是数字，例如 0.2、20 或 20%"
            if not 0 < skill_value <= 1:
                return "❌ 词条数值必须大于 0 且不超过 100%"
            skills[skill_id] = round(skill_value, 4)

        if not 0 <= enchant_count <= 100:
            return "❌ 附魔次数必须在 0 到 100 之间"
        max_slots = get_rod_prefix(prefix_id).get("max_slots", 0)
        if len(skills) > max_slots:
            return f"❌ 指定了 {len(skills)} 个词条，但该钓竿最多只有 {max_slots} 个附魔槽位"

        async with self._get_user_lock(target_uid):
            if not target_uid or not await self.storage.user_exists(target_uid):
                return f"❌ 用户 {target_uid} 不存在"

            user = await self.storage.get_user(target_uid)
            instance_id = user.add_rod(base_id, prefix_id, skills, enchant_count)
            await self.storage.save_user(user)

        rod_data = {"base_id": base_id, "prefix_id": prefix_id, "skills": skills}
        rod_name = format_rod_name(rod_data)
        skill_text = format_rod_skills(prefix_id, skills)
        detail = f"添加 {rod_name} (base={base_id}, prefix={prefix_id}, skills={skills}, enchant_count={enchant_count}, instance={instance_id})"
        await self._add_admin_log(operator, "加钓竿", target_uid, detail)
        return f"✅ 已为 {target_uid} 添加 {rod_name}{skill_text}\n累计附魔: {enchant_count} 次\ninstance_id: {instance_id}"

    async def _cmd_admin_add_ticket(self, event, operator: str, sub_args: tuple) -> str:
        """给目标玩家添加券类道具。"""
        if len(sub_args) < 2:
            return "❌ 用法：/管理 加券 <@用户/UID> <券ID> [数量]"

        target_uid = self._parse_target_uid(sub_args[0])
        ticket_id = sub_args[1].lower()
        try:
            count = int(sub_args[2]) if len(sub_args) > 2 else 1
        except ValueError:
            return "❌ 数量必须是整数"
        if not 1 <= count <= 10000:
            return "❌ 数量必须在 1 到 10000 之间"

        enchant_ticket = next((item for item in ENCHANT_TICKETS if item["id"] == ticket_id), None)
        directed_ticket = parse_directed_enchant_id(ticket_id)
        if enchant_ticket:
            ticket_name = enchant_ticket["name"]
            ticket_kind = "enchant"
        elif ticket_id == "refresh_token":
            ticket_name = "刷新券"
            ticket_kind = "item"
        elif directed_ticket:
            skill_id, value = directed_ticket
            if skill_id not in get_available_skills() or value not in DIRECTED_ENCHANT_CONFIG["base_prices"]:
                return f"❌ 无效的定向附魔券 ID：{ticket_id}"
            skill_name = ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)
            ticket_name = f"定向附魔券[{skill_name}+{int(value * 100)}%]"
            ticket_kind = "item"
        else:
            return f"❌ 未知的券 ID：{ticket_id}，可用 /管理 物品ID 券 查看"

        async with self._get_user_lock(target_uid):
            if not target_uid or not await self.storage.user_exists(target_uid):
                return f"❌ 用户 {target_uid} 不存在"
            user = await self.storage.get_user(target_uid)
            if ticket_kind == "enchant":
                user.add_enchant_ticket(ticket_id, count)
            else:
                user.add_item(ticket_id, count)
            await self.storage.save_user(user)

        await self._add_admin_log(operator, "加券", target_uid, f"添加 {ticket_name} ({ticket_id}) x{count}")
        return f"✅ 已为 {target_uid} 添加 {ticket_name} x{count}"

    async def _cmd_admin_remove_rod(self, event, operator: str, sub_args: tuple) -> str:
        """删除目标玩家指定钓竿"""
        if len(sub_args) < 2:
            return "❌ 用法：/管理 删钓竿 <@用户/UID> <instance_id>"

        target_uid = self._parse_target_uid(sub_args[0])
        instance_id = sub_args[1]

        async with self._get_user_lock(target_uid):
            if not target_uid or not await self.storage.user_exists(target_uid):
                return f"❌ 用户 {target_uid} 不存在"

            user = await self.storage.get_user(target_uid)
            rod = user.get_rod_by_instance_id(instance_id)
            if not rod:
                return f"❌ 用户 {target_uid} 没有 instance_id 为 {instance_id} 的钓竿"

            rod_name = format_rod_name(rod)
            user.remove_rod(instance_id)
            await self.storage.save_user(user)

        await self._add_admin_log(operator, "删钓竿", target_uid, f"删除 {rod_name} (instance={instance_id})")
        return f"✅ 已删除 {target_uid} 的钓竿 {rod_name}"

    async def _cmd_admin_clear_cd(self, event, operator: str, sub_args: tuple) -> str:
        """清空目标玩家冷却"""
        if len(sub_args) < 1:
            return "❌ 用法：/管理 清冷却 <@用户/UID>"

        target_uid = self._parse_target_uid(sub_args[0])

        async with self._get_user_lock(target_uid):
            if not target_uid or not await self.storage.user_exists(target_uid):
                return f"❌ 用户 {target_uid} 不存在"

            user = await self.storage.get_user(target_uid)
            user._data["fish_cooldown"] = 0
            user._data["shop_refresh_cd"] = 0
            await self.storage.save_user(user)

        await self._add_admin_log(operator, "清冷却", target_uid, "清空钓鱼和商店刷新冷却")
        return f"✅ 已清空 {target_uid} 的钓鱼和商店刷新冷却"

    async def _cmd_admin_global_coins(self, event, operator: str, sub_args: tuple) -> str:
        """全服发放金币"""
        if len(sub_args) < 1:
            return "❌ 用法：/管理 全服发金币 <数量>"

        try:
            amount = int(sub_args[0])
        except ValueError:
            return "❌ 数量必须是整数"

        if amount <= 0:
            return "❌ 数量必须大于 0"

        all_uids = await self.storage.get_all_user_ids()
        count = 0
        for uid in all_uids:
            async with self._get_user_lock(uid):
                user = await self.storage.get_user(uid)
                user.add_coins(amount)
                await self.storage.save_user(user)
            count += 1

        await self._add_admin_log(operator, "全服发金币", "all", f"发放 {amount} 金币，共 {count} 人")
        return f"✅ 已向全服 {count} 名玩家各发放 {amount} 金币"

    async def _cmd_admin_global_bait(self, event, operator: str, sub_args: tuple) -> str:
        """全服发放鱼饵"""
        if len(sub_args) < 3:
            return "❌ 用法：/管理 全服发鱼饵 <base_id> <prefix_id> <数量>"

        base_id, prefix_id, count_str = sub_args[0], sub_args[1], sub_args[2]
        try:
            count = int(count_str)
        except ValueError:
            return "❌ 数量必须是整数"

        if count <= 0:
            return "❌ 数量必须大于 0"

        bait_base = get_bait_by_id(base_id)
        if not bait_base:
            return f"❌ 鱼饵 base_id {base_id} 不存在"

        all_uids = await self.storage.get_all_user_ids()
        success = 0
        for uid in all_uids:
            async with self._get_user_lock(uid):
                user = await self.storage.get_user(uid)
                user.add_bait(base_id, prefix_id, count)
                await self.storage.save_user(user)
            success += 1

        bait_name = format_bait_name({"base_id": base_id, "prefix_id": prefix_id})
        await self._add_admin_log(operator, "全服发鱼饵", "all", f"发放 {bait_name} x{count}，共 {success} 人")
        return f"✅ 已向全服 {success} 名玩家各发放 {bait_name} x{count}"

    async def _cmd_admin_stats(self, event, operator: str) -> str:
        """查看全服统计信息"""
        all_uids = await self.storage.get_all_user_ids()
        total_users = len(all_uids)

        total_coins = 0
        total_value = 0
        total_fish_count = 0
        total_bait_count = 0
        total_rod_count = 0

        for uid in all_uids:
            try:
                user = await self.storage.get_user(uid)
                total_coins += user.coins
                total_value += user.get_total_inventory_value()
                total_fish_count += sum(f.get("count", 0) for f in user.get_fish_inventory())
                total_bait_count += sum(b.get("count", 0) for b in user.get_baits())
                total_rod_count += len(user.get_owned_rods())
            except Exception:
                continue

        await self._add_admin_log(operator, "统计", "all", f"注册玩家 {total_users} 人")
        return f"""📊 全服统计

👥 注册玩家: {total_users} 人
💰 金币总量: {total_coins}
📦 库存总价值: {total_value}
🐠 渔获总量: {total_fish_count}
🪤 鱼饵总量: {total_bait_count}
🎣 钓竿总量: {total_rod_count}"""

    async def _cmd_admin_logs(self, event, operator: str, sub_args: tuple) -> str:
        """查看审计日志"""
        page = 1
        page_size = 10
        if sub_args:
            try:
                page = int(sub_args[0])
            except ValueError:
                return "❌ 页码必须是整数"
        if page < 1:
            page = 1

        logs = await self.storage.get_kv_data(self.ADMIN_LOG_KEY) or []
        total = len(logs)
        if total == 0:
            return "📋 暂无管理员操作日志"

        start = (page - 1) * page_size
        end = start + page_size
        page_logs = logs[start:end]

        lines = []
        for log in reversed(page_logs):
            ts = log.get("timestamp", 0)
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            lines.append(f"[{time_str}] {log.get('operator', '-')} | {log.get('action', '-')} | 目标:{log.get('target', '-')} | {log.get('detail', '')}")

        total_pages = (total + page_size - 1) // page_size
        result = f"📋 管理员操作日志 (第 {page}/{total_pages} 页，共 {total} 条)\n\n"
        result += "\n".join(lines)
        return result

    async def _cmd_admin_clear_logs(self, event, operator: str) -> str:
        """清空审计日志"""
        await self.storage.put_kv_data(self.ADMIN_LOG_KEY, [{
            "timestamp": int(time.time()),
            "operator": operator,
            "action": "清空日志",
            "target": "all",
            "detail": "清空了所有历史审计日志",
        }])
        return "✅ 已清空所有管理员操作日志（保留本条清理记录）"

    async def _cmd_admin_item_ids(self, event, operator: str, sub_args: tuple) -> str:
        """按类别、名称或 ID 查询管理员可用的物品标识。"""
        category_aliases = {
            "全部": "全部", "all": "全部",
            "鱼": "鱼类", "鱼类": "鱼类", "fish": "鱼类",
            "钓竿": "钓竿", "鱼竿": "钓竿", "rod": "钓竿",
            "鱼饵": "鱼饵", "bait": "鱼饵",
            "券": "券", "道具": "券", "ticket": "券", "item": "券",
            "词条": "词条", "技能": "词条", "skill": "词条",
            "前缀": "前缀", "鱼前缀": "鱼前缀",
            "钓竿前缀": "钓竿前缀", "鱼竿前缀": "钓竿前缀",
            "鱼饵前缀": "鱼饵前缀",
        }
        args = [str(arg).strip() for arg in sub_args if str(arg).strip()]
        page = 1
        if args and args[-1].isdigit():
            page = int(args.pop())
        category = "全部"
        if args and args[0].lower() in category_aliases:
            category = category_aliases[args.pop(0).lower()]
        keyword = " ".join(args).lower()

        records = []

        def add_records(record_category: str, items):
            for item in items:
                records.append((record_category, item["id"], item["name"]))

        add_records("鱼类", FISH_TYPES)
        add_records("钓竿", ROD_BASES)
        add_records("鱼饵", BAIT_BASES)
        add_records("鱼前缀", FISH_PREFIXES)
        add_records("钓竿前缀", ROD_PREFIXES)
        add_records("鱼饵前缀", BAIT_PREFIXES)
        add_records("券", ENCHANT_TICKETS)
        records.append(("券", "refresh_token", "刷新券"))

        for skill_id in get_available_skills():
            skill_name = ROD_SKILL_DESCRIPTIONS.get(skill_id, skill_id)
            records.append(("词条", skill_id, skill_name))
            for value in DIRECTED_ENCHANT_CONFIG["base_prices"]:
                item_id = f"directed_enchant_{skill_id}_{int(value * 100)}"
                records.append(("券", item_id, f"定向附魔券[{skill_name}+{int(value * 100)}%]"))

        def category_matches(record_category: str) -> bool:
            if category == "全部":
                return True
            if category == "前缀":
                return record_category.endswith("前缀")
            return record_category == category

        matches = [
            record for record in records
            if category_matches(record[0])
            and (not keyword or keyword in record[1].lower() or keyword in record[2].lower())
        ]
        if not matches:
            query_text = keyword or category
            return (
                f"🔍 没有找到“{query_text}”对应的物品 ID\n"
                "可直接搜索名称或 ID，例如：/管理 物品ID 贪婪"
            )

        page_size = 15
        total_pages = (len(matches) + page_size - 1) // page_size
        if page < 1 or page > total_pages:
            return f"❌ 页码超出范围，有效页码为 1-{total_pages}"
        start = (page - 1) * page_size
        page_records = matches[start:start + page_size]

        title = f"🔍 物品 ID 查询｜{category}"
        if keyword:
            title += f"｜关键词：{keyword}"
        lines = [title, f"第 {page}/{total_pages} 页，共 {len(matches)} 条", ""]
        lines.extend(f"• [{record_category}] {name} → {item_id}" for record_category, item_id, name in page_records)
        if total_pages > 1:
            lines.append(f"\n翻页：/管理 物品ID {category} {keyword} {page + 1 if page < total_pages else 1}".replace("  ", " "))

        await self._add_admin_log(operator, "物品ID", "", f"类别={category}, 关键词={keyword or '-'}, 页码={page}")
        return "\n".join(lines)
