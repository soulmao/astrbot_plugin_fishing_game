"""管理员命令模块"""
import time
from typing import Optional

from .commands_base import CommandBase
from .utils import extract_target_user_id, format_rod_name, format_bait_name
from .fish_data import (
    get_rod_by_id, get_rod_prefix, get_bait_by_id, get_bait_prefix,
    get_prefix_by_id, get_fish_by_id, calc_fish_value,
    FISH_TYPES, FISH_PREFIXES, ROD_BASES, ROD_PREFIXES,
    BAIT_BASES, BAIT_PREFIXES,
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
• 加钓竿 <@用户/UID> <钓竿base_id> [前缀id] - 给玩家添加钓竿
• 删钓竿 <@用户/UID> <instance_id> - 删除玩家指定钓竿
• 清冷却 <@用户/UID> - 清空玩家钓鱼和商店冷却
• 全服发金币 <数量> - 给所有注册玩家发放金币
• 全服发鱼饵 <base_id> <prefix_id> <数量> - 给所有注册玩家发放鱼饵
• 统计 - 查看全服统计信息
• 物品ID [类别] [页码] - 查看鱼类/钓竿/鱼饵/前缀 ID 列表
• 日志 [页码] - 查看最近管理员操作日志
• 清空日志 - 清空所有审计日志

⚠️ 管理员 UID 请在 AstrBot 面板的 admin_uids 配置项中设置。"""

    async def cmd_admin(self, event, action: str = "", arg1: str = "", arg2: str = "", arg3: str = "", arg4: str = "") -> str:
        """管理员命令入口"""
        if not self._check_admin(event):
            return "❌ 你没有管理员权限"

        operator = event.get_sender_id()

        action = action.strip()
        if not action:
            return self._admin_help()

        sub_args = [a for a in (arg1, arg2, arg3, arg4) if a]

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
            return "❌ 用法：/管理 加钓竿 <@用户/UID> <钓竿base_id> [前缀id]"

        target_uid = self._parse_target_uid(sub_args[0])
        base_id = sub_args[1]
        prefix_id = sub_args[2] if len(sub_args) > 2 else "rod_pref_03"

        rod_base = get_rod_by_id(base_id)
        if not rod_base:
            return f"❌ 钓竿 base_id {base_id} 不存在"

        # 特种钓竿不带前缀
        if rod_base.get("no_prefix"):
            prefix_id = ""

        async with self._get_user_lock(target_uid):
            if not target_uid or not await self.storage.user_exists(target_uid):
                return f"❌ 用户 {target_uid} 不存在"

            user = await self.storage.get_user(target_uid)
            instance_id = user.add_rod(base_id, prefix_id)
            await self.storage.save_user(user)

        rod_name = format_rod_name({"base_id": base_id, "prefix_id": prefix_id})
        await self._add_admin_log(operator, "加钓竿", target_uid, f"添加 {rod_name} (base={base_id}, prefix={prefix_id}, instance={instance_id})")
        return f"✅ 已为 {target_uid} 添加 {rod_name}\ninstance_id: {instance_id}"

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
        """列出鱼类/钓竿/鱼饵/前缀等物品 ID，方便管理员管理"""
        category = sub_args[0].lower() if sub_args else "全部"
        valid_categories = {"全部", "鱼", "鱼类", "钓竿", "鱼饵", "前缀", "鱼前缀", "钓竿前缀", "鱼饵前缀"}

        if category not in valid_categories:
            return (
                "❌ 未知类别。用法：/管理 物品ID [类别]\n"
                "可选类别：全部、鱼、钓竿、鱼饵、前缀、鱼前缀、钓竿前缀、鱼饵前缀"
            )

        result_parts = []

        def fmt(items, key_id="id", key_name="name"):
            return " | ".join(f"{it[key_id]}({it[key_name]})" for it in items)

        if category in ("全部", "鱼", "鱼类"):
            fish_text = fmt(FISH_TYPES)
            result_parts.append(f"🐟 鱼类 ID：\n{fish_text}")

        if category in ("全部", "钓竿"):
            rod_text = fmt(ROD_BASES)
            result_parts.append(f"🎣 钓竿 ID：\n{rod_text}")

        if category in ("全部", "鱼饵"):
            bait_text = fmt(BAIT_BASES)
            result_parts.append(f"🪤 鱼饵 ID：\n{bait_text}")

        if category in ("全部", "前缀", "鱼前缀"):
            prefix_text = fmt(FISH_PREFIXES)
            result_parts.append(f"🏷️ 鱼前缀 ID：\n{prefix_text}")

        if category in ("全部", "前缀", "钓竿前缀"):
            rod_prefix_text = fmt(ROD_PREFIXES)
            result_parts.append(f"🔧 钓竿前缀 ID：\n{rod_prefix_text}")

        if category in ("全部", "前缀", "鱼饵前缀"):
            bait_prefix_text = fmt(BAIT_PREFIXES)
            result_parts.append(f"🌿 鱼饵前缀 ID：\n{bait_prefix_text}")

        await self._add_admin_log(operator, "物品ID", "", f"查看类别：{category}")
        return "📋 物品 ID 列表\n\n" + "\n\n".join(result_parts)
