"""
TRPG 战报生成模块

提供跑团结束时的自动战报生成和玩家评分功能。
"""

import time
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class SessionRecord:
    """跑团记录类"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.start_time = time.time()
        self.end_time = None
        
        # 记录各类事件
        self.dice_rolls = []  # 掷骰记录
        self.skill_checks = []  # 技能检定记录
        self.combat_rounds = []  # 战斗轮次记录
        self.key_events = []  # 关键事件
        self.npc_interactions = []  # NPC交互
        self.player_actions = {}  # 玩家行动记录 {user_id: actions}
        
        # 玩家统计
        self.player_stats = {}  # {user_id: {char_name, total_rolls, success_count, critical_success, ...}}
    
    def add_dice_roll(self, user_id: str, char_name: str, expression: str, result: int, is_critical: bool = False):
        """添加掷骰记录"""
        self.dice_rolls.append({
            "user_id": user_id,
            "char_name": char_name,
            "expression": expression,
            "result": result,
            "is_critical": is_critical,
            "timestamp": time.time()
        })
        
        # 更新玩家统计
        if user_id not in self.player_stats:
            self.player_stats[user_id] = {
                "char_name": char_name,
                "total_rolls": 0,
                "critical_success": 0,
                "critical_failure": 0
            }
        
        self.player_stats[user_id]["total_rolls"] += 1
        if is_critical:
            self.player_stats[user_id]["critical_success"] += 1
    
    def add_skill_check(self, user_id: str, char_name: str, skill: str, target: int, roll: int, success_level: str):
        """添加技能检定记录"""
        self.skill_checks.append({
            "user_id": user_id,
            "char_name": char_name,
            "skill": skill,
            "target": target,
            "roll": roll,
            "success_level": success_level,
            "timestamp": time.time()
        })
        
        # 更新玩家统计
        if user_id not in self.player_stats:
            self.player_stats[user_id] = {
                "char_name": char_name,
                "total_checks": 0,
                "successful_checks": 0
            }
        
        stats = self.player_stats[user_id]
        stats["total_checks"] = stats.get("total_checks", 0) + 1
        if "成功" in success_level:
            stats["successful_checks"] = stats.get("successful_checks", 0) + 1
    
    def add_key_event(self, description: str, event_type: str = "general"):
        """添加关键事件"""
        self.key_events.append({
            "description": description,
            "event_type": event_type,
            "timestamp": time.time()
        })
    
    def add_player_action(self, user_id: str, char_name: str, action: str):
        """添加玩家行动"""
        if user_id not in self.player_actions:
            self.player_actions[user_id] = []
        
        self.player_actions[user_id].append({
            "char_name": char_name,
            "action": action,
            "timestamp": time.time()
        })
        
        # 更新统计
        if user_id not in self.player_stats:
            self.player_stats[user_id] = {"char_name": char_name}
        
        self.player_stats[user_id]["action_count"] = len(self.player_actions[user_id])
    
    def end_session(self):
        """结束跑团记录"""
        self.end_time = time.time()
    
    def get_duration_minutes(self) -> int:
        """获取跑团时长（分钟）"""
        end = self.end_time or time.time()
        return int((end - self.start_time) / 60)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "dice_rolls": self.dice_rolls,
            "skill_checks": self.skill_checks,
            "combat_rounds": self.combat_rounds,
            "key_events": self.key_events,
            "npc_interactions": self.npc_interactions,
            "player_actions": self.player_actions,
            "player_stats": self.player_stats
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SessionRecord':
        """从字典创建记录"""
        record = cls(data["session_id"])
        record.start_time = data["start_time"]
        record.end_time = data.get("end_time")
        record.dice_rolls = data.get("dice_rolls", [])
        record.skill_checks = data.get("skill_checks", [])
        record.combat_rounds = data.get("combat_rounds", [])
        record.key_events = data.get("key_events", [])
        record.npc_interactions = data.get("npc_interactions", [])
        record.player_actions = data.get("player_actions", {})
        record.player_stats = data.get("player_stats", {})
        return record


class BattleReportGenerator:
    """战报生成器"""
    
    def __init__(self, store):
        self.store = store
    
    async def get_latest_history(self, chat_key: str) -> Optional[SessionRecord]:
        """获取最近的历史记录"""
        try:
            # 尝试获取最近的历史会话
            # 存储键格式: session_history.{chat_key}.{session_id}
            # 我们需要获取最新的一个
            latest_key = f"session_history.{chat_key}.latest"
            data = await self.store.get(store_key=latest_key)
            if data:
                return SessionRecord.from_dict(json.loads(data))
        except Exception:
            pass
        
        return None
    
    async def start_session(self, chat_key: str, session_name: Optional[str] = None, auto_start: bool = False) -> str:
        """开始记录跑团
        
        Args:
            chat_key: 聊天会话标识
            session_name: 可选的会话名称
            auto_start: 是否为自动启动（用于区分手动和自动启动）
        """
        session_id = f"session_{int(time.time())}"
        
        if not session_name:
            session_name = f"跑团-{datetime.now().strftime('%Y%m%d-%H%M')}"
        
        record = SessionRecord(session_id)
        
        # 保存记录
        store_key = f"session_record.{chat_key}.current"
        await self.store.set(
            store_key=store_key,
            value=json.dumps(record.to_dict(), ensure_ascii=False)
        )
        
        # 保存会话名称
        name_key = f"session_name.{chat_key}.current"
        await self.store.set(store_key=name_key, value=session_name)
        
        return session_id
    
    async def get_current_session(self, chat_key: str) -> Optional[SessionRecord]:
        """获取当前跑团记录"""
        store_key = f"session_record.{chat_key}.current"
        
        try:
            data = await self.store.get(store_key=store_key)
            if data:
                return SessionRecord.from_dict(json.loads(data))
        except Exception:
            pass
        
        return None
    
    async def save_session(self, chat_key: str, record: SessionRecord):
        """保存跑团记录"""
        store_key = f"session_record.{chat_key}.current"
        await self.store.set(
            store_key=store_key,
            value=json.dumps(record.to_dict(), ensure_ascii=False)
        )
    
    async def end_session(self, chat_key: str) -> Optional[SessionRecord]:
        """结束跑团记录"""
        record = await self.get_current_session(chat_key)
        if record:
            record.end_session()
            
            # 获取会话名称
            name_key = f"session_name.{chat_key}.current"
            session_name = await self.store.get(store_key=name_key)
            
            # 保存到历史（同时保存到具体ID和latest）
            history_key = f"session_history.{chat_key}.{record.session_id}"
            latest_key = f"session_history.{chat_key}.latest"
            latest_name_key = f"session_name.{chat_key}.latest"
            record_json = json.dumps(record.to_dict(), ensure_ascii=False)
            
            await self.store.set(store_key=history_key, value=record_json)
            await self.store.set(store_key=latest_key, value=record_json)
            
            # 同时保存会话名称到latest
            if session_name:
                await self.store.set(store_key=latest_name_key, value=session_name)
            
            # 清除当前记录
            current_key = f"session_record.{chat_key}.current"
            await self.store.delete(store_key=current_key)
            await self.store.delete(store_key=name_key)
            
            return record
        
        return None
    
    def calculate_player_score(self, user_id: str, record: SessionRecord) -> Tuple[int, str]:
        """
        计算玩家评分
        
        返回: (分数, 评价)
        """
        if user_id not in record.player_stats:
            return 0, "未参与"
        
        stats = record.player_stats[user_id]
        score = 60  # 基础分
        
        # 根据投骰次数评分（参与度）
        total_rolls = stats.get("total_rolls", 0)
        if total_rolls > 0:
            score += min(total_rolls * 2, 15)  # 最多15分
        
        # 根据技能检定成功率评分
        total_checks = stats.get("total_checks", 0)
        successful_checks = stats.get("successful_checks", 0)
        if total_checks > 0:
            success_rate = successful_checks / total_checks
            score += int(success_rate * 15)  # 最多15分
        
        # 根据行动次数评分（角色扮演）
        action_count = stats.get("action_count", 0)
        score += min(action_count * 1, 10)  # 最多10分
        
        # 大成功次数加分
        critical_success = stats.get("critical_success", 0)
        score += critical_success * 2
        
        # 限制分数范围
        score = max(0, min(100, score))
        
        # 评价等级
        if score >= 90:
            rating = "⭐⭐⭐⭐⭐ 传奇表现"
        elif score >= 80:
            rating = "⭐⭐⭐⭐ 优秀表现"
        elif score >= 70:
            rating = "⭐⭐⭐ 良好表现"
        elif score >= 60:
            rating = "⭐⭐ 合格表现"
        else:
            rating = "⭐ 需要努力"
        
        return score, rating
    
    def generate_report_text(self, record: SessionRecord, session_name: str) -> str:
        """生成战报文本"""
        lines = []
        
        # 标题和基本信息
        lines.append("=" * 50)
        lines.append(f"📊 TRPG 跑团战报")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"🎮 会话名称: {session_name}")
        lines.append(f"⏰ 开始时间: {datetime.fromtimestamp(record.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        if record.end_time:
            lines.append(f"⏰ 结束时间: {datetime.fromtimestamp(record.end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"⏱️ 游戏时长: {record.get_duration_minutes()} 分钟")
        lines.append("")
        
        # 玩家评分
        lines.append("=" * 50)
        lines.append("👥 玩家评分")
        lines.append("=" * 50)
        lines.append("")
        
        for user_id, stats in record.player_stats.items():
            char_name = stats.get("char_name", "未知角色")
            score, rating = self.calculate_player_score(user_id, record)
            
            lines.append(f"🎭 {char_name}")
            lines.append(f"   总分: {score}/100 - {rating}")
            lines.append(f"   投骰次数: {stats.get('total_rolls', 0)}")
            lines.append(f"   技能检定: {stats.get('successful_checks', 0)}/{stats.get('total_checks', 0)} 成功")
            lines.append(f"   行动次数: {stats.get('action_count', 0)}")
            lines.append(f"   大成功: {stats.get('critical_success', 0)} 次")
            lines.append("")
        
        # 游戏统计
        lines.append("=" * 50)
        lines.append("📈 游戏统计")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"🎲 总投骰次数: {len(record.dice_rolls)}")
        lines.append(f"🎯 技能检定次数: {len(record.skill_checks)}")
        lines.append(f"⚔️ 战斗轮次: {len(record.combat_rounds)}")
        lines.append(f"📝 关键事件: {len(record.key_events)}")
        lines.append("")
        
        # 关键事件回顾
        if record.key_events:
            lines.append("=" * 50)
            lines.append("🔑 关键事件回顾")
            lines.append("=" * 50)
            lines.append("")
            
            for i, event in enumerate(record.key_events[-10:], 1):  # 只显示最后10个
                timestamp = datetime.fromtimestamp(event["timestamp"]).strftime('%H:%M:%S')
                lines.append(f"{i}. [{timestamp}] {event['description']}")
            lines.append("")
        
        # 精彩时刻（大成功/大失败）
        critical_moments = [
            roll for roll in record.dice_rolls 
            if roll.get("is_critical")
        ]
        
        if critical_moments:
            lines.append("=" * 50)
            lines.append("✨ 精彩时刻")
            lines.append("=" * 50)
            lines.append("")
            
            for moment in critical_moments[-5:]:  # 只显示最后5个
                char_name = moment["char_name"]
                expression = moment["expression"]
                result = moment["result"]
                lines.append(f"🎲 {char_name} 投出 {expression} = {result} (大成功!)")
            lines.append("")
        
        lines.append("=" * 50)
        lines.append("感谢各位玩家的参与！期待下次冒险！")
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def generate_markdown_report(self, record: SessionRecord, session_name: str) -> str:
        """生成Markdown格式战报"""
        lines = []
        
        # 标题
        lines.append(f"# 📊 TRPG 跑团战报")
        lines.append("")
        lines.append(f"## 🎮 会话信息")
        lines.append("")
        lines.append(f"- **会话名称**: {session_name}")
        lines.append(f"- **开始时间**: {datetime.fromtimestamp(record.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        if record.end_time:
            lines.append(f"- **结束时间**: {datetime.fromtimestamp(record.end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **游戏时长**: {record.get_duration_minutes()} 分钟")
        lines.append("")
        
        # 玩家评分
        lines.append("## 👥 玩家评分")
        lines.append("")
        
        for user_id, stats in record.player_stats.items():
            char_name = stats.get("char_name", "未知角色")
            score, rating = self.calculate_player_score(user_id, record)
            
            lines.append(f"### 🎭 {char_name}")
            lines.append("")
            lines.append(f"**总分**: {score}/100 - {rating}")
            lines.append("")
            lines.append("| 统计项 | 数值 |")
            lines.append("|--------|------|")
            lines.append(f"| 投骰次数 | {stats.get('total_rolls', 0)} |")
            lines.append(f"| 技能检定成功率 | {stats.get('successful_checks', 0)}/{stats.get('total_checks', 0)} |")
            lines.append(f"| 行动次数 | {stats.get('action_count', 0)} |")
            lines.append(f"| 大成功次数 | {stats.get('critical_success', 0)} |")
            lines.append("")
        
        # 游戏统计
        lines.append("## 📈 游戏统计")
        lines.append("")
        lines.append("| 项目 | 次数 |")
        lines.append("|------|------|")
        lines.append(f"| 🎲 总投骰次数 | {len(record.dice_rolls)} |")
        lines.append(f"| 🎯 技能检定次数 | {len(record.skill_checks)} |")
        lines.append(f"| ⚔️ 战斗轮次 | {len(record.combat_rounds)} |")
        lines.append(f"| 📝 关键事件 | {len(record.key_events)} |")
        lines.append("")
        
        # 关键事件
        if record.key_events:
            lines.append("## 🔑 关键事件回顾")
            lines.append("")
            
            for i, event in enumerate(record.key_events[-10:], 1):
                timestamp = datetime.fromtimestamp(event["timestamp"]).strftime('%H:%M:%S')
                lines.append(f"{i}. **[{timestamp}]** {event['description']}")
            lines.append("")
        
        # 精彩时刻
        critical_moments = [
            roll for roll in record.dice_rolls 
            if roll.get("is_critical")
        ]
        
        if critical_moments:
            lines.append("## ✨ 精彩时刻")
            lines.append("")
            
            for moment in critical_moments[-5:]:
                char_name = moment["char_name"]
                expression = moment["expression"]
                result = moment["result"]
                timestamp = datetime.fromtimestamp(moment["timestamp"]).strftime('%H:%M:%S')
                lines.append(f"- **[{timestamp}]** 🎲 {char_name} 投出 `{expression}` = **{result}** (大成功!)")
            lines.append("")
        
        # 结尾
        lines.append("---")
        lines.append("")
        lines.append("*感谢各位玩家的参与！期待下次冒险！*")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate_summary_for_prompt(self, record: SessionRecord, session_name: str) -> str:
        """生成用于提示词注入的简洁战报摘要"""
        lines = []
        
        lines.append(f"# 📜 上次跑团记录")
        lines.append("")
        lines.append(f"**会话名称**: {session_name}")
        lines.append(f"**时间**: {datetime.fromtimestamp(record.start_time).strftime('%Y-%m-%d')}")
        
        if record.end_time:
            lines.append(f"**时长**: {record.get_duration_minutes()}分钟")
        lines.append("")
        
        # 参与玩家
        if record.player_stats:
            lines.append("## 参与玩家")
            for user_id, stats in record.player_stats.items():
                char_name = stats.get("char_name", "未知角色")
                score, rating = self.calculate_player_score(user_id, record)
                lines.append(f"- {char_name}: {score}分 ({rating})")
            lines.append("")
        
        # 关键事件总结
        if record.key_events:
            lines.append("## 主要事件")
            # 只显示最后5个关键事件
            for event in record.key_events[-5:]:
                lines.append(f"- {event['description']}")
            lines.append("")
        
        # 游戎进度提示
        lines.append("## 游戏进度")
        lines.append(f"总投骰: {len(record.dice_rolls)}次 | 技能检定: {len(record.skill_checks)}次")
        
        if record.combat_rounds:
            lines.append(f"战斗轮次: {len(record.combat_rounds)}")
        
        lines.append("")
        lines.append("💡 *以上是上次跑团的简要回顾，请基于此继续推进剧情*")
        
        return "\n".join(lines)


    async def ensure_session_started(self, chat_key: str) -> bool:
        """
        确保有活跃的会话记录，如果没有则自动启动
        
        Returns:
            bool: True 如果自动启动了新会话，False 如果已有会话
        """
        current_session = await self.generator.get_current_session(chat_key)
        if not current_session:
            # 自动启动新会话
            await self.generator.start_session(chat_key, auto_start=True)
            return True
        return False
    
    async def start_session(self, chat_key: str, session_name: str = None) -> str:
        """开始记录跑团"""
        return await self.generator.start_session(chat_key, session_name)
    
    async def add_dice_roll(self, chat_key: str, user_id: str, char_name: str, 
                           expression: str, result: int, is_critical: bool = False):
        """记录掷骰"""
        record = await self.generator.get_current_session(chat_key)
        if record:
            record.add_dice_roll(user_id, char_name, expression, result, is_critical)
            await self.generator.save_session(chat_key, record)
    
    async def add_skill_check(self, chat_key: str, user_id: str, char_name: str,
                             skill: str, target: int, roll: int, success_level: str):
        """记录技能检定"""
        record = await self.generator.get_current_session(chat_key)
        if record:
            record.add_skill_check(user_id, char_name, skill, target, roll, success_level)
            await self.generator.save_session(chat_key, record)
    
    async def add_key_event(self, chat_key: str, description: str, event_type: str = "general"):
        """记录关键事件"""
        record = await self.generator.get_current_session(chat_key)
        if record:
            record.add_key_event(description, event_type)
            await self.generator.save_session(chat_key, record)
    
    async def add_player_action(self, chat_key: str, user_id: str, char_name: str, action: str):
        """记录玩家行动"""
        record = await self.generator.get_current_session(chat_key)
        if record:
            record.add_player_action(user_id, char_name, action)
            await self.generator.save_session(chat_key, record)
    
    async def generate_battle_report(self, chat_key: str) -> Tuple[str, str, str]:
        """
        生成并结束战报
        
        返回: (纯文本战报, Markdown战报, 会话名称)
        """
        record = await self.generator.end_session(chat_key)
        if not record:
            return None, None, None
        
        # 获取会话名称
        name_key = f"session_name.{chat_key}.current"
        session_name = await self.store.get(store_key=name_key)
        if not session_name:
            session_name = f"跑团-{datetime.fromtimestamp(record.start_time).strftime('%Y%m%d-%H%M')}"
        
        # 生成战报
        text_report = self.generator.generate_report_text(record, session_name)
        markdown_report = self.generator.generate_markdown_report(record, session_name)
        
        return text_report, markdown_report, session_name
    
    async def get_last_session_summary(self, chat_key: str) -> Optional[str]:
        """
        获取上次跑团的简要总结，用于提示词注入
        
        Returns:
            简要的战报摘要文本，或None
        """
        # 获取最近的历史记录
        latest_record = await self.generator.get_latest_history(chat_key)
        if not latest_record:
            return None
        
        # 获取会话名称
        name_key = f"session_name.{chat_key}.latest"
        session_name = await self.store.get(store_key=name_key)
        if not session_name:
            session_name = f"跑团-{datetime.fromtimestamp(latest_record.start_time).strftime('%Y%m%d-%H%M')}"
        
        # 生成摘要
        summary = self.generator.generate_summary_for_prompt(latest_record, session_name)
        return summary
