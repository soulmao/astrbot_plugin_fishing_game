"""装备管理命令模块"""
from .commands_base import CommandBase
from .utils import (
    format_rod_name, format_rod_skills, format_bait_name,
    calc_enchant_price, get_available_skills, can_apply_rod_prefix,
)
from .fish_data import get_rod_prefix
from .storage import StorageManager


class EquipmentCommands(CommandBase):
    """装备管理命令处理器"""

    def _get_enchant_warning(self, rod: dict) -> str:
        """检测钓竿下次附魔是否会触发回退，返回警告文本（空字符串表示无警告）"""
        prefix = get_rod_prefix(rod.get("prefix_id", ""))
        max_slots = prefix.get("max_slots", 0)
        if max_slots <= 0:
            return ""
        
        current_skills = rod.get("skills", {}) or {}
        available = get_available_skills()
        prefix_skills = prefix.get("skills", {})
        safe_available = [s for s in available if s not in prefix_skills]
        
        # 判断下次附魔是否处于"安全状态"
        # 安全 = 槽位未满 且 还有安全技能（前缀没有的）可以获得
        has_safe_slot = len(current_skills) < max_slots and any(s not in current_skills for s in safe_available)
        
        if not has_safe_slot:
            if len(current_skills) >= max_slots:
                return "❗槽位已满，继续附魔将随机替换已有技能"
            else:
                return "❗安全技能已耗尽，继续附魔将低值覆盖前缀自带技能"
        return ""
    
    async def cmd_myrods(self, event) -> str:
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            result = "[钓鱼] 我的钓竿\n\n"
            current = user.current_rod
            
            for i, rod in enumerate(user.get_owned_rods(), 1):
                rod_name = format_rod_name(rod)
                skill_text = format_rod_skills(rod["prefix_id"], rod.get("skills"))
                enchant_text = f" [附魔{rod.get('enchant_count', 0)}次]" if rod.get('enchant_count', 0) > 0 else ""
                # 显示附魔/升级费用
                prefix_info = get_rod_prefix(rod["prefix_id"])
                max_slots = prefix_info.get("max_slots", 0)
                cost_hint = ""
                if max_slots > 0:
                    price = calc_enchant_price(rod)
                    cost_hint = f" [+附魔/升级](需{price}金币)"
                warning = self._get_enchant_warning(rod)
                warning_text = f" {warning}" if warning else ""
                is_current = (rod.get("instance_id") == current.get("instance_id"))
                marker = " [当前]" if is_current else ""
                result += f"{i}. {rod_name}{skill_text}{enchant_text}{cost_hint}{warning_text}{marker}\n"
            
            if not user.get_owned_rods():
                result += "(无)\n"
            
            result += "\n提示: 使用 /装备钓竿 [编号] 切换"
            return result
    
    async def cmd_equip_rod(self, event, index: int) -> str:
        """装备钓竿"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)

            if user.is_greedy_active():
                return "💰 你有挂起的贪婪状态，无法更换钓竿。请先 /收杆 或 /贪婪 处理完毕。"

            rods = user.get_owned_rods()
            if index < 1 or index > len(rods):
                return f"编号无效，你有 {len(rods)} 根钓竿"
            
            rod = rods[index - 1]
            if not can_apply_rod_prefix(rod["base_id"], rod["prefix_id"]):
                rod_name = format_rod_name(rod)
                return f"❌ 无法装备 {rod_name}：该前缀与钓竿不兼容"
            if user.equip_rod(rod["instance_id"]):
                await self.storage.save_user(user)
                rod_name = format_rod_name(rod)
                return f"✅ 已装备: {rod_name}"
            return "装备失败"

    async def cmd_mybaits(self, event) -> str:
        """我的鱼饵 - 查看所有鱼饵"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            result = "[钓鱼] 我的鱼饵\n\n"
            current = user.current_bait
            
            for i, bait in enumerate(user.get_baits(), 1):
                bait_name = format_bait_name(bait)
                is_current = (bait["base_id"] == current["base_id"] and bait["prefix_id"] == current["prefix_id"])
                marker = " [当前]" if is_current else ""
                result += f"{i}. {bait_name} x{bait.get('count', 0)}{marker}\n"
            
            if not user.get_baits():
                result += "(无)\n"
            
            result += "\n提示: 使用 /装备鱼饵 [编号] 切换"
            return result

    async def cmd_equip_bait(self, event, index: int) -> str:
        """装备鱼饵"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            
            baits = user.get_baits()
            if index < 1 or index > len(baits):
                return f"编号无效，你有 {len(baits)} 种鱼饵"
            
            bait = baits[index - 1]
            if bait.get("count", 0) <= 0:
                return f"该鱼饵数量为0，无法装备"
            
            if user.equip_bait(bait["base_id"], bait["prefix_id"]):
                await self.storage.save_user(user)
                bait_name = format_bait_name(bait)
                return f"✅ 已装备: {bait_name}"
            return "装备失败"
