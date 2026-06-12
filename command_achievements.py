"""成就系统命令模块"""
from .commands_base import CommandBase
from .fish_data import ACHIEVEMENTS
from .storage import StorageManager


def _get_achievement_progress(user, ach: dict) -> tuple:
    """返回 (当前进度, 目标值)，用于成就列表展示"""
    cat = ach.get("category")
    target = ach.get("target", 0)
    rc = user.rarity_catch_count
    if cat == "fish_count":
        return user.total_fish_count, target
    if cat == "rare_count":
        return rc.get("rare", 0), target
    if cat == "legendary_count":
        return rc.get("legendary", 0), target
    if cat == "mythic_count":
        return rc.get("mythic", 0), target
    if cat == "coins":
        return user.coins, target
    if cat == "level":
        return user.level, target
    if cat == "collection":
        return user.get_collection_count(), target
    if cat == "enchant_count":
        return user.get_total_enchant_count(), target
    if cat == "checkin_days":
        return user.consecutive_checkin_days, target
    return 0, target


class AchievementCommands(CommandBase):
    """成就系统命令处理器"""

    async def cmd_achievements(self, event) -> str:
        """成就命令 - 查看成就列表与进度"""
        user_id = event.get_sender_id()
        async with self._get_user_lock(user_id):
            user = await self.storage.get_user(user_id)
            completed = set(user.achievements)
            total = len(ACHIEVEMENTS)
            completed_count = len(completed)

            lines = [f"🏅 成就系统 ({completed_count}/{total})", ""]
            for ach in ACHIEVEMENTS:
                is_done = ach["id"] in completed
                status = "✅" if is_done else "⬜"
                cur, goal = _get_achievement_progress(user, ach)
                progress_text = ""
                if not is_done and goal > 1:
                    progress_text = f" ({min(cur, goal)}/{goal})"
                lines.append(f"{status} {ach['name']} - {ach.get('desc', ach['name'])}{progress_text}")
                if is_done and (ach.get("reward_coins") or ach.get("reward_exp")):
                    lines.append(f"     奖励: 💰{ach.get('reward_coins', 0)} 📈{ach.get('reward_exp', 0)}")

            return "\n".join(lines)
