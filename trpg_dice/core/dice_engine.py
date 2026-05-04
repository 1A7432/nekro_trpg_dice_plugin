"""
TRPG 骰子引擎模块

提供完整的骰子表达式解析和投掷功能，支持复杂的TRPG骰子表达式。
修复了减法bug、奖励骰逻辑，并新增爆炸骰、Fate骰、多次掷骰等功能。
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
                 dice_count: int = 1, dice_sides: int = 20, is_check: bool = False):
        self.expression = expression
        self.rolls = rolls
        self.modifier = modifier
        self.dice_count = dice_count
        self.dice_sides = dice_sides
        self.total = sum(rolls) + modifier
        self.timestamp = time.time()
        self.is_check = is_check  # 是否是检定（单骰）

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
        """判断是否大成功 - 只在单骰检定时生效"""
        if not config.ENABLE_CRITICAL_EFFECTS:
            return False
        if not self.is_check or self.dice_count != 1:
            return False
        return any(roll == self.dice_sides for roll in self.rolls)

    def is_critical_failure(self) -> bool:
        """判断是否大失败 - 只在单骰检定时生效"""
        if not config.ENABLE_CRITICAL_EFFECTS:
            return False
        if not self.is_check or self.dice_count != 1:
            return False
        return any(roll == 1 for roll in self.rolls)


class DiceParser:
    """骰子表达式解析器"""

    @staticmethod
    def parse_expression(expression: str) -> Tuple[int, int, int, int, int]:
        """解析骰子表达式，返回(数量, 面数, 修正值, 乘数, 保留数量)"""
        expression = expression.lower().strip()

        # 处理带乘法的表达式，如 3d6x5, (2d6+6)x5, 3d6*5
        if (('x' in expression or '*' in expression) and 'k' not in expression and 'kh' not in expression and 'kl' not in expression):
            # 找到第一个 x 或 *（不在括号内）
            mul_pos = -1
            mul_char = ''
            depth = 0
            for i, ch in enumerate(expression):
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                elif depth == 0 and ch in 'x*':
                    mul_pos = i
                    mul_char = ch
                    break

            if mul_pos > 0:
                dice_part = expression[:mul_pos].strip()
                multiplier = int(expression[mul_pos + 1:].strip())

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
    def parse_multiple_dice(expression: str) -> List[Tuple[int, int, int, int, int, int]]:
        """
        解析多个骰子表达式，如 3d6+2d4+5
        返回(数量, 面数, 修正值, 乘数, 保留数量, 符号)
        符号: 1=正, -1=负
        """
        expression = expression.replace(" ", "").lower()

        # 分割表达式
        parts = re.split(r'(?=[+-])', expression)
        if not parts or (len(parts) == 1 and not parts[0]):
            raise ValueError("空的骰子表达式")

        # 处理开头没有符号的情况
        if parts[0] == '':
            parts = parts[1:]
        elif parts[0].startswith('+') or parts[0].startswith('-'):
            pass
        else:
            parts[0] = '+' + parts[0]

        results = []

        for part in parts:
            if not part:
                continue
            sign = -1 if part.startswith('-') else 1
            content = part[1:] if part.startswith('+') or part.startswith('-') else part
            if not content:
                continue

            dice_count, dice_sides, modifier, multiplier, keep_count = DiceParser.parse_expression(content)

            # 负号直接通过 sign 传递，不要在解析阶段处理
            results.append((dice_count, dice_sides, modifier, multiplier, keep_count, sign))

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
    def roll_expression(expression: str, is_check: bool = False) -> DiceResult:
        """投掷骰子表达式"""
        try:
            dice_parts = DiceParser.parse_multiple_dice(expression)
        except ValueError as e:
            raise ValueError(f"表达式解析失败: {e}")

        all_rolls = []
        total_modifier = 0
        main_dice_count = 0
        main_dice_sides = config.DEFAULT_DICE_TYPE

        for dice_count, dice_sides, modifier, multiplier, keep_count, sign in dice_parts:
            if dice_count > 0:
                rolls = DiceRoller.roll_dice(dice_count, dice_sides, keep_count)
                # 应用乘数
                if multiplier != 1:
                    rolls = [roll * multiplier for roll in rolls]
                # 应用符号
                if sign == -1:
                    rolls = [-r for r in rolls]
                all_rolls.extend(rolls)
                # 记录主要骰子信息（第一组有实际骰子的）
                if main_dice_count == 0:
                    main_dice_count = dice_count
                    main_dice_sides = dice_sides

            # 修正值也需要应用乘数和符号
            total_modifier += sign * modifier * multiplier

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
            dice_sides=main_dice_sides,
            is_check=is_check
        )

    @staticmethod
    def roll_advantage(expression: str, is_check: bool = False) -> DiceResult:
        """优势掷骰（取较高值）"""
        result1 = DiceRoller.roll_expression(expression, is_check=is_check)
        result2 = DiceRoller.roll_expression(expression, is_check=is_check)

        if result1.total >= result2.total:
            return result1
        else:
            return result2

    @staticmethod
    def roll_disadvantage(expression: str, is_check: bool = False) -> DiceResult:
        """劣势掷骰（取较低值）"""
        result1 = DiceRoller.roll_expression(expression, is_check=is_check)
        result2 = DiceRoller.roll_expression(expression, is_check=is_check)

        if result1.total <= result2.total:
            return result1
        else:
            return result2

    @staticmethod
    def roll_coc_check(skill_value: int) -> dict:
        """CoC技能检定（基础版，无奖惩骰）"""
        roll = random.randint(1, 100)

        # 判定成功等级
        if roll == 1:
            level = "大成功"
        elif roll == 100 or (roll >= 96 and skill_value < 50):
            level = "大失败"
        elif roll <= skill_value // 5:
            level = "极难成功"
        elif roll <= skill_value // 2:
            level = "困难成功"
        elif roll <= skill_value:
            level = "成功"
        else:
            level = "失败"

        success = level not in ["失败", "大失败"]

        return {
            "roll": roll,
            "skill_value": skill_value,
            "level": level,
            "success": success
        }

    @staticmethod
    def roll_coc_check_with_bonus(skill_value: int, bonus: int = 0, penalty: int = 0) -> dict:
        """
        CoC技能检定，支持奖励/惩罚骰

        COC7规则：
        - d100由个位(0-9)和十位(0-9)组成，00+0=100
        - 奖励骰：额外掷N个十位骰，取最小替换原十位
        - 惩罚骰：额外掷N个十位骰，取最大替换原十位
        """
        # 投d100
        roll = random.randint(1, 100)
        ones = roll % 10  # 个位
        tens = (roll // 10) % 10  # 十位（roll=100时tens=0）

        # 净奖惩骰数量
        net_bonus = bonus - penalty

        extra_tens = []
        if net_bonus != 0:
            # 额外投 |net_bonus| 个十位骰
            extra_tens = [random.randint(0, 9) for _ in range(abs(net_bonus))]

        if net_bonus > 0:
            # 奖励骰：取所有十位中的最小值
            all_tens = [tens] + extra_tens
            final_tens = min(all_tens)
        elif net_bonus < 0:
            # 惩罚骰：取所有十位中的最大值
            all_tens = [tens] + extra_tens
            final_tens = max(all_tens)
        else:
            final_tens = tens

        # 计算最终结果
        if final_tens == 0 and ones == 0:
            final_roll = 100
        else:
            final_roll = final_tens * 10 + ones

        # 判定成功等级
        if final_roll == 1:
            level = "大成功"
        elif final_roll == 100 or (final_roll >= 96 and skill_value < 50):
            level = "大失败"
        elif final_roll <= skill_value // 5:
            level = "极难成功"
        elif final_roll <= skill_value // 2:
            level = "困难成功"
        elif final_roll <= skill_value:
            level = "成功"
        else:
            level = "失败"

        success = level not in ["失败", "大失败"]

        return {
            "roll": roll,
            "final_roll": final_roll,
            "skill_value": skill_value,
            "level": level,
            "success": success,
            "bonus": bonus,
            "penalty": penalty,
            "tens": tens,
            "ones": ones,
            "extra_tens": extra_tens,
            "final_tens": final_tens,
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

    @staticmethod
    def roll_explode(expression: str, max_explosions: int = 10) -> DiceResult:
        """
        爆炸骰：掷出最大值时继续掷骰
        支持格式如 d10, 2d6 等
        """
        try:
            dice_parts = DiceParser.parse_multiple_dice(expression)
        except ValueError as e:
            raise ValueError(f"表达式解析失败: {e}")

        all_rolls = []
        total_modifier = 0
        main_dice_count = 0
        main_dice_sides = config.DEFAULT_DICE_TYPE

        for dice_count, dice_sides, modifier, multiplier, keep_count, sign in dice_parts:
            if dice_count > 0 and dice_sides > 0:
                rolls = []
                explosion_count = 0
                current_count = dice_count

                while current_count > 0 and explosion_count < max_explosions:
                    new_rolls = DiceRoller.roll_dice(current_count, dice_sides)
                    rolls.extend(new_rolls)
                    explosion_count += current_count

                    # 统计需要爆炸的骰子
                    explosions = sum(1 for r in new_rolls if r == dice_sides)
                    current_count = explosions

                # 应用乘数和符号
                if multiplier != 1:
                    rolls = [roll * multiplier for roll in rolls]
                if sign == -1:
                    rolls = [-r for r in rolls]
                all_rolls.extend(rolls)

                if main_dice_count == 0:
                    main_dice_count = dice_count
                    main_dice_sides = dice_sides

            total_modifier += sign * modifier * multiplier

        if not all_rolls:
            all_rolls = [0]
            main_dice_count = 0
            main_dice_sides = 0

        return DiceResult(
            expression=f"{expression}(爆炸)",
            rolls=all_rolls,
            modifier=total_modifier,
            dice_count=main_dice_count,
            dice_sides=main_dice_sides
        )

    @staticmethod
    def roll_fate(dice_count: int = 4, modifier: int = 0) -> DiceResult:
        """
        Fate/命运骰：结果为 -1, 0, +1
        """
        if dice_count <= 0:
            dice_count = 4

        rolls = []
        for _ in range(dice_count):
            # Fate骰：-, 空白, + 各1/3概率
            r = random.randint(1, 3)
            if r == 1:
                rolls.append(-1)
            elif r == 2:
                rolls.append(0)
            else:
                rolls.append(1)

        total = sum(rolls) + modifier

        result = DiceResult(
            expression=f"{dice_count}df{'+' + str(modifier) if modifier > 0 else str(modifier) if modifier < 0 else ''}",
            rolls=rolls,
            modifier=modifier,
            dice_count=dice_count,
            dice_sides=3
        )
        result.total = total
        return result

    @staticmethod
    def roll_repeat(expression: str, times: int) -> List[DiceResult]:
        """多次投掷同一表达式"""
        if times <= 0 or times > 20:
            raise ValueError("重复次数必须在1-20之间")

        results = []
        for _ in range(times):
            results.append(DiceRoller.roll_expression(expression))
        return results
