"""
TRPG 骰子引擎模块

提供完整的骰子表达式解析和投掷功能，支持复杂的TRPG骰子表达式。
"""

import random
import re
import time
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class DiceConfig:
    """骰子配置"""
    MAX_DICE_COUNT: int = 100
    MAX_DICE_SIDES: int = 1000
    DEFAULT_DICE_TYPE: int = 20
    ENABLE_CRITICAL_EFFECTS: bool = True


# 默认配置实例
config = DiceConfig()


class DiceResult:
    """骰子结果类"""
    
    def __init__(self, expression: str, rolls: List[int], modifier: int = 0, 
                 dice_count: int = 1, dice_sides: int = 20):
        self.expression = expression
        self.rolls = rolls
        self.modifier = modifier
        self.dice_count = dice_count
        self.dice_sides = dice_sides
        self.total = sum(rolls) + modifier
        self.timestamp = time.time()
    
    def format_result(self, show_details: bool = True) -> str:
        """格式化骰子结果"""
        if not show_details:
            return f"结果: {self.total}"
        
        if len(self.rolls) == 1:
            roll_str = f"[{self.rolls[0]}]"
        else:
            roll_str = f"[{', '.join(map(str, self.rolls))}]"
        
        if self.modifier != 0:
            modifier_str = f"{'+' if self.modifier > 0 else ''}{self.modifier}"
            return f"{self.expression} = {roll_str}{modifier_str} = {self.total}"
        else:
            return f"{self.expression} = {roll_str} = {self.total}"
    
    def is_critical_success(self) -> bool:
        """判断是否大成功"""
        if not config.ENABLE_CRITICAL_EFFECTS:
            return False
        return any(roll == self.dice_sides for roll in self.rolls)
    
    def is_critical_failure(self) -> bool:
        """判断是否大失败"""
        if not config.ENABLE_CRITICAL_EFFECTS:
            return False
        return any(roll == 1 for roll in self.rolls)


class DiceParser:
    """骰子表达式解析器"""
    
    @staticmethod
    def parse_expression(expression: str) -> Tuple[int, int, int, int, int]:
        """解析骰子表达式，返回(数量, 面数, 修正值, 乘数, 保留数量)"""
        expression = expression.lower().strip()
        
        # 处理带乘法的表达式，如 3d6x5, (2d6+6)x5
        if 'x' in expression and 'k' not in expression:
            parts = expression.split('x')
            if len(parts) == 2:
                dice_part = parts[0].strip()
                multiplier = int(parts[1].strip())
                
                # 处理括号表达式 (2d6+6)x5
                if dice_part.startswith('(') and dice_part.endswith(')'):
                    dice_part = dice_part[1:-1]  # 去掉括号
                
                # 递归解析骰子部分
                dice_count, dice_sides, modifier, _, keep_count = DiceParser.parse_expression(dice_part)
                return dice_count, dice_sides, modifier, multiplier, keep_count
        
        # 处理保留最高的N个骰子，如 4d6k3
        if 'k' in expression:
            k_parts = expression.split('k')
            if len(k_parts) == 2:
                dice_part = k_parts[0].strip()
                keep_count = int(k_parts[1].strip())
                
                # 解析骰子部分
                pattern = r'^(\d*)d(\d+)([+-]\d+)?$'
                match = re.match(pattern, dice_part)
                
                if match:
                    dice_count = int(match.group(1)) if match.group(1) else 1
                    dice_sides = int(match.group(2))
                    modifier = int(match.group(3)) if match.group(3) else 0
                    
                    if keep_count > dice_count:
                        raise ValueError(f"保留数量({keep_count})不能超过骰子数量({dice_count})")
                    
                    return dice_count, dice_sides, modifier, 1, keep_count
        
        # 处理基础表达式 d20, 3d6, 2d10+5 等
        pattern = r'^(\d*)d(\d+)([+-]\d+)?$'
        match = re.match(pattern, expression)
        
        if match:
            dice_count = int(match.group(1)) if match.group(1) else 1
            dice_sides = int(match.group(2))
            modifier = int(match.group(3)) if match.group(3) else 0
            return dice_count, dice_sides, modifier, 1, 0  # 0表示不保留
        
        # 处理纯数字修正 +5, -3 等
        if re.match(r'^[+-]?\d+$', expression):
            return 0, 0, int(expression), 1, 0
        
        # 处理单个数字作为d20
        if re.match(r'^\d+$', expression):
            num = int(expression)
            if num <= config.MAX_DICE_SIDES:
                return 1, num, 0, 1, 0
        
        raise ValueError(f"无法解析的骰子表达式: {expression}")
    
    @staticmethod
    def parse_multiple_dice(expression: str) -> List[Tuple[int, int, int, int, int]]:
        """解析多个骰子表达式，如 3d6+2d4+5"""
        expression = expression.replace(" ", "").lower()
        
        # 分割表达式
        parts = re.split(r'([+-])', expression)
        if not parts:
            raise ValueError("空的骰子表达式")
        
        results = []
        current_sign = 1
        
        for part in parts:
            if part == '+':
                current_sign = 1
            elif part == '-':
                current_sign = -1
            elif part.strip():
                dice_count, dice_sides, modifier, multiplier, keep_count = DiceParser.parse_expression(part)
                
                # 应用符号
                if current_sign == -1:
                    modifier = -modifier
                    if dice_count > 0:
                        # 负数骰子，转换为负修正值
                        modifier -= dice_count * ((dice_sides + 1) // 2)  # 期望值
                        dice_count = 0
                        keep_count = 0
                
                results.append((dice_count, dice_sides, modifier, multiplier, keep_count))
        
        return results


class DiceRoller:
    """骰子投掷器"""
    
    @staticmethod
    def roll_dice(dice_count: int, dice_sides: int, keep_count: int = 0) -> List[int]:
        """投掷指定数量和面数的骰子，可选择保留最高的N个"""
        if dice_count <= 0:
            return []
        
        if dice_count > config.MAX_DICE_COUNT:
            raise ValueError(f"骰子数量不能超过{config.MAX_DICE_COUNT}个")
        
        if dice_sides > config.MAX_DICE_SIDES:
            raise ValueError(f"骰子面数不能超过{config.MAX_DICE_SIDES}")
        
        rolls = [random.randint(1, dice_sides) for _ in range(dice_count)]
        
        # 如果指定了保留数量，则保留最高的N个
        if keep_count > 0 and keep_count < dice_count:
            rolls.sort(reverse=True)  # 降序排列
            rolls = rolls[:keep_count]  # 取前keep_count个
        
        return rolls
    
    @staticmethod
    def roll_expression(expression: str) -> DiceResult:
        """投掷骰子表达式"""
        try:
            dice_parts = DiceParser.parse_multiple_dice(expression)
        except ValueError as e:
            raise ValueError(f"表达式解析失败: {e}")
        
        all_rolls = []
        total_modifier = 0
        main_dice_count = 0
        main_dice_sides = config.DEFAULT_DICE_TYPE
        
        for dice_count, dice_sides, modifier, multiplier, keep_count in dice_parts:
            if dice_count > 0:
                rolls = DiceRoller.roll_dice(dice_count, dice_sides, keep_count)
                # 应用乘数
                if multiplier != 1:
                    rolls = [roll * multiplier for roll in rolls]
                all_rolls.extend(rolls)
                # 记录主要骰子信息（第一组有实际骰子的）
                if main_dice_count == 0:
                    main_dice_count = dice_count
                    main_dice_sides = dice_sides
            
            # 修正值也需要应用乘数
            total_modifier += modifier * multiplier
        
        # 如果没有实际的骰子，只有修正值
        if not all_rolls:
            all_rolls = [0]
            main_dice_count = 0
            main_dice_sides = 0
        
        return DiceResult(
            expression=expression,
            rolls=all_rolls,
            modifier=total_modifier,
            dice_count=main_dice_count,
            dice_sides=main_dice_sides
        )
    
    @staticmethod
    def roll_advantage(expression: str) -> DiceResult:
        """优势掷骰（取较高值）"""
        result1 = DiceRoller.roll_expression(expression)
        result2 = DiceRoller.roll_expression(expression)
        
        if result1.total >= result2.total:
            return result1
        else:
            return result2
    
    @staticmethod
    def roll_disadvantage(expression: str) -> DiceResult:
        """劣势掷骰（取较低值）"""
        result1 = DiceRoller.roll_expression(expression)
        result2 = DiceRoller.roll_expression(expression)
        
        if result1.total <= result2.total:
            return result1
        else:
            return result2
    
    @staticmethod
    def roll_coc_check(skill_value: int) -> dict:
        """CoC技能检定"""
        roll = random.randint(1, 100)
        
        # 判断成功等级
        if roll <= skill_value // 5:  # 极难成功
            level = "极难成功"
        elif roll <= skill_value // 2:  # 困难成功
            level = "困难成功"
        elif roll <= skill_value:  # 常规成功
            level = "成功"
        else:  # 失败
            level = "失败"
        
        # 判断大成功大失败
        if roll == 1:
            level = "大成功"
        elif roll == 100 or (roll >= 96 and skill_value < 50):
            level = "大失败"
        
        return {
            "roll": roll,
            "skill_value": skill_value,
            "level": level,
            "success": level not in ["失败", "大失败"]
        }
    
    @staticmethod
    def roll_wod_pool(pool_size: int, difficulty: int = 6, specialization: bool = False) -> dict:
        """黑暗世界骰池检定"""
        if pool_size <= 0:
            return {"successes": 0, "rolls": [], "botch": True}
        
        rolls = [random.randint(1, 10) for _ in range(pool_size)]
        successes = 0
        ones = 0
        
        for roll in rolls:
            if roll >= difficulty:
                successes += 1
                # 专精：10点再加一个成功
                if specialization and roll == 10:
                    successes += 1
            elif roll == 1:
                ones += 1
        
        # 判断是否大失败（无成功且有1）
        botch = successes == 0 and ones > 0
        
        return {
            "successes": successes,
            "rolls": rolls,
            "botch": botch,
            "difficulty": difficulty,
            "pool_size": pool_size
        }