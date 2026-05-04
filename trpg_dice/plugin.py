"""
TRPG Dice Plugin - Main Plugin File

Complete TRPG dice system with character management, document storage, and AI-powered game mastering.
"""

import random
import re
import time
from typing import Dict, List, Optional, Tuple, Union
import json
import hashlib
from datetime import datetime
import uuid
import asyncio

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from pydantic import BaseModel, Field

from nekro_agent.adapters.onebot_v11.matchers.command import (
    finish_with,
    on_command,
)
from nekro_agent.api import message
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx

# 导入核心模块
from .core.dice_engine import DiceParser, DiceRoller, DiceResult, config as dice_config
from .core.character_manager import CharacterManager, CharacterSheet, CharacterTemplate
from .core.document_manager import VectorDatabaseManager, DocumentProcessor
from .core.prompt_injection import register_prompt_injections
from .core.battle_report import BattleReportManager

# 创建插件实例
plugin = NekroPlugin(
    name="TRPG骰子系统",
    module_name="trpg_dice",
    description="完整的TRPG骰子系统，支持多种规则和复杂表达式",
    version="2.0.0",
    author="Dirac",
    url="https://github.com/nekro-agent/trpg-dice-plugin",
    support_adapter=["onebot_v11", "discord"],
)


@plugin.mount_config()
class TRPGDiceConfig(ConfigBase):
    """TRPG骰子配置"""
    
    MAX_DICE_COUNT: int = Field(
        default=100,
        title="单次最大骰子数量",
        description="单次掷骰允许的最大骰子数量",
    )
    MAX_DICE_SIDES: int = Field(
        default=1000,
        title="骰子最大面数",
        description="骰子允许的最大面数",
    )
    DEFAULT_DICE_TYPE: int = Field(
        default=20,
        title="默认骰子类型",
        description="默认的骰子面数",
    )
    ENABLE_CRITICAL_EFFECTS: bool = Field(
        default=True,
        title="启用大成功大失败",
        description="是否启用大成功和大失败判定",
    )
    ENABLE_VECTOR_DB: bool = Field(
        default=True,
        title="启用向量数据库",
        description="是否启用文档向量化存储功能",
    )
    CHUNK_SIZE: int = Field(
        default=1000,
        title="文档分块大小",
        description="文档分块时每块的字符数",
    )
    CHUNK_OVERLAP: int = Field(
        default=200,
        title="分块重叠大小",
        description="文档分块时重叠的字符数",
    )
    MAX_SEARCH_RESULTS: int = Field(
        default=5,
        title="最大搜索结果数",
        description="向量检索时返回的最大结果数量",
    )


# 获取配置和存储
config = plugin.get_config(TRPGDiceConfig)
store = plugin.store

# 更新骰子引擎配置
dice_config.MAX_DICE_COUNT = config.MAX_DICE_COUNT
dice_config.MAX_DICE_SIDES = config.MAX_DICE_SIDES
dice_config.DEFAULT_DICE_TYPE = config.DEFAULT_DICE_TYPE
dice_config.ENABLE_CRITICAL_EFFECTS = config.ENABLE_CRITICAL_EFFECTS

# 初始化管理器
character_manager = CharacterManager(store)
vector_db = VectorDatabaseManager(
    collection_name=plugin.get_vector_collection_name("trpg_documents"),
    logger=plugin.logger
)
battle_report_manager = BattleReportManager(store)

# 注册提示词注入
register_prompt_injections(plugin, character_manager, vector_db, store, config, battle_report_manager)


# ============ 角色卡管理沙盒方法 ============

@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "create_character", "创建新角色卡")
async def create_character(
    _ctx: AgentCtx,
    name: str,
    system: str = "coc7",
    auto_generate: bool = True
) -> str:
    """
    创建新的TRPG角色卡

    Args:
        name: 角色名称
        system: 游戏系统 (coc7/dnd5e)
        auto_generate: 是否自动按规则生成属性值

    Returns:
        创建结果信息
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    system_map = {"coc7": "coc7", "dnd5e": "dnd5e", "CoC": "coc7", "DnD5e": "dnd5e"}
    template_key = system_map.get(system, "coc7")
    system_name = "CoC" if template_key == "coc7" else "DnD5e"

    try:
        if auto_generate:
            character = character_manager.generate_character(template_key, name)
            character.system = system_name
        else:
            character = CharacterSheet(name=name, system=system_name)

        await character_manager.save_character(user_id, chat_key, character)

        # 构建返回信息
        if system_name == "CoC":
            attrs = character.attributes
            response = (
                f"✅ 角色卡 \"{name}\" 创建成功！\n"
                f"🎮 系统: COC7\n"
                f"📊 属性: "
                f"STR:{attrs.get('STR', '?')} "
                f"CON:{attrs.get('CON', '?')} "
                f"DEX:{attrs.get('DEX', '?')} "
                f"INT:{attrs.get('INT', '?')} "
                f"POW:{attrs.get('POW', '?')} "
                f"APP:{attrs.get('APP', '?')} "
                f"SIZ:{attrs.get('SIZ', '?')} "
                f"EDU:{attrs.get('EDU', '?')} "
                f"LUC:{attrs.get('LUC', '?')}\n"
                f"❤️ HP:{attrs.get('HP', '?')}/{attrs.get('HPMAX', '?')} "
                f"🧠 SAN:{attrs.get('SAN', '?')}/{attrs.get('SANMAX', '?')} "
                f"✨ MP:{attrs.get('MP', '?')}/{attrs.get('MPMAX', '?')}\n"
            )
        else:
            attrs = character.attributes
            response = (
                f"✅ 角色卡 \"{name}\" 创建成功！\n"
                f"🎮 系统: DND5E\n"
                f"📊 属性: "
                f"STR:{attrs.get('STR', '?')} "
                f"DEX:{attrs.get('DEX', '?')} "
                f"CON:{attrs.get('CON', '?')} "
                f"INT:{attrs.get('INT', '?')} "
                f"WIS:{attrs.get('WIS', '?')} "
                f"CHA:{attrs.get('CHA', '?')}\n"
            )
        return response
    except Exception as e:
        return f"❌ 创建角色失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_character_sheet", "获取当前角色卡信息")
async def get_character_sheet(_ctx: AgentCtx) -> str:
    """
    获取当前用户的角色卡详细信息

    Returns:
        角色卡信息文本
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        character = await character_manager.get_character(user_id, chat_key)
        if not character or character.name == "default":
            return "❌ 当前没有角色卡，请先使用 create_character 创建角色"

        response = f"📋 角色卡: {character.name}\n"
        response += f"🎮 系统: {character.system}\n"

        if character.system == "CoC":
            attrs = character.attributes
            response += "\n📊 基础属性:\n"
            for attr in ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU", "LUC"]:
                if attr in attrs:
                    response += f"  {attr}: {attrs[attr]}\n"

            response += "\n❤️ 状态:\n"
            response += f"  HP: {attrs.get('HP', '?')}/{attrs.get('HPMAX', '?')}\n"
            response += f"  SAN: {attrs.get('SAN', '?')}/{attrs.get('SANMAX', '?')}\n"
            response += f"  MP: {attrs.get('MP', '?')}/{attrs.get('MPMAX', '?')}\n"

            if character.occupation:
                response += f"\n💼 职业: {character.occupation}\n"
            if character.age:
                response += f"🎂 年龄: {character.age}\n"
        else:
            attrs = character.attributes
            response += "\n📊 属性:\n"
            for k, v in attrs.items():
                response += f"  {k}: {v}\n"

        if character.skills:
            response += "\n🔧 技能:\n"
            # 按技能值排序显示
            sorted_skills = sorted(character.skills.items(), key=lambda x: x[1], reverse=True)
            for skill, value in sorted_skills:
                response += f"  {skill}: {value}\n"

        if character.equipment:
            response += f"\n🎒 装备: {', '.join(character.equipment)}\n"
        if character.background:
            response += f"\n📖 背景: {character.background}\n"
        if character.notes:
            response += f"\n📝 备注: {character.notes}\n"

        return response
    except Exception as e:
        return f"❌ 获取角色卡失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "update_character_skill", "更新角色技能值")
async def update_character_skill(_ctx: AgentCtx, skill_name: str, value: int) -> str:
    """
    更新角色某项技能的数值

    Args:
        skill_name: 技能名称（支持中英文别名，如'侦查'或'spot hidden'）
        value: 新的技能值

    Returns:
        更新结果
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        character = await character_manager.get_character(user_id, chat_key)
        if not character or character.name == "default":
            return "❌ 当前没有角色卡，请先使用 create_character 创建角色"

        # 尝试通过别名查找标准技能名
        standard_name = character_manager.find_skill_by_alias(character, skill_name)
        target_skill = standard_name if standard_name else skill_name

        old_value = character.skills.get(target_skill, "未设定")
        character.skills[target_skill] = value
        character.last_updated = time.time()

        await character_manager.save_character(user_id, chat_key, character)

        return f"✅ 已更新 {character.name} 的 {target_skill}: {old_value} → {value}"
    except Exception as e:
        return f"❌ 更新技能失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "update_character_attribute", "更新角色属性值")
async def update_character_attribute(_ctx: AgentCtx, attribute: str, value: int) -> str:
    """
    更新角色某项属性的数值

    Args:
        attribute: 属性名称（如STR、DEX、POW等）
        value: 新的属性值

    Returns:
        更新结果
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        character = await character_manager.get_character(user_id, chat_key)
        if not character or character.name == "default":
            return "❌ 当前没有角色卡，请先使用 create_character 创建角色"

        old_value = character.attributes.get(attribute, "未设定")
        character.attributes[attribute] = value
        character.last_updated = time.time()

        # COC系统：如果改了POW/CON/SIZ，自动重算衍生属性
        if character.system == "CoC":
            if attribute == "POW":
                character.attributes["SANMAX"] = value
                character.attributes["SAN"] = value
                character.attributes["MPMAX"] = value // 5
                character.attributes["MP"] = value // 5
            elif attribute in ["CON", "SIZ"]:
                con = character.attributes.get("CON", 50)
                siz = character.attributes.get("SIZ", 50)
                character.attributes["HPMAX"] = (con + siz) // 10
                character.attributes["HP"] = (con + siz) // 10

        await character_manager.save_character(user_id, chat_key, character)

        return f"✅ 已更新 {character.name} 的 {attribute}: {old_value} → {value}"
    except Exception as e:
        return f"❌ 更新属性失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "roll_dice", "投掷骰子")
async def roll_dice(_ctx: AgentCtx, expression: str) -> str:
    """
    投掷骰子并返回结果

    Args:
        expression: 骰子表达式，如 '1d100', '3d6+2', '2d6*5'

    Returns:
        掷骰结果
    """
    try:
        result = DiceRoller.roll_expression(expression)
        response = f"🎲 {result.format_result()}"

        if result.is_critical_success():
            response += " ✨ 大成功!"
        elif result.is_critical_failure():
            response += " 💥 大失败!"

        return response
    except ValueError as e:
        return f"❌ 骰子表达式错误: {str(e)}"
    except Exception as e:
        return f"❌ 掷骰失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "skill_check", "角色技能检定")
async def skill_check(_ctx: AgentCtx, skill_name: str, bonus: int = 0, penalty: int = 0, dc: int = None, proficient: bool = False) -> str:
    """
    对当前角色进行技能检定

    Args:
        skill_name: 技能名称（支持中英文别名）
        bonus: 奖励骰/优势次数（COC:奖励骰数量，DND:优势次数）
        penalty: 惩罚骰/劣势次数（COC:惩罚骰数量，DND:劣势次数）
        dc: 困难等级（仅DND5E，默认15）
        proficient: 是否熟练（仅DND5E）

    Returns:
        检定结果
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        character = await character_manager.get_character(user_id, chat_key)
        if not character or character.name == "default":
            return "❌ 当前没有角色卡，请先使用 create_character 创建角色"

        # 查找技能
        standard_name = character_manager.find_skill_by_alias(character, skill_name)
        target_skill = standard_name if standard_name else skill_name

        if character.system == "CoC":
            skill_value = character.skills.get(target_skill, 0)
            # 使用修复后的COC7奖励骰逻辑
            result = DiceRoller.roll_coc_check_with_bonus(skill_value, bonus, penalty)

            success = result["success"]
            emoji = "✨" if success else "❌"

            response = (
                f"🎲 {character.name} 进行 {target_skill} 检定\n"
                f"🎯 目标值: {skill_value}"
            )
            if bonus > 0:
                response += f" + {bonus}奖励骰"
            elif penalty > 0:
                response += f" - {penalty}惩罚骰"
            response += f"\n🎲 原始掷出: {result['roll']}"

            if bonus > 0 or penalty > 0:
                bp_label = "奖励骰" if bonus > 0 else "惩罚骰"
                response += f"\n📌 {bp_label}十位: {result['extra_tens']} → 最终十位: {result['final_tens']}"

            response += f"\n🎲 最终结果: {result['final_roll']}\n{emoji} 结果: {result['level']}"

            return response
        else:
            # DND5E 完整检定: d20 + 属性修正 + 熟练加值 vs DC
            modifier = character_manager.get_dnd_skill_modifier(character, target_skill, proficient)
            target_dc = dc if dc is not None else 15

            # 处理优势/劣势
            net_advantage = bonus - penalty
            if net_advantage > 0:
                result = DiceRoller.roll_advantage("1d20", is_check=True)
                adv_label = f"优势x{net_advantage}"
            elif net_advantage < 0:
                result = DiceRoller.roll_disadvantage("1d20", is_check=True)
                adv_label = f"劣势x{abs(net_advantage)}"
            else:
                result = DiceRoller.roll_expression("1d20", is_check=True)
                adv_label = ""

            total = result.total + modifier

            if result.is_critical_success():
                level = "大成功"
                success = True
            elif result.is_critical_failure():
                level = "大失败"
                success = False
            else:
                success = total >= target_dc
                level = "成功" if success else "失败"

            emoji = "✨" if success else "❌"
            prof_label = "(熟练)" if proficient else ""
            response = (
                f"🎲 {character.name} 进行 {target_skill} 检定 {prof_label}\n"
            )
            if adv_label:
                response += f"🎭 {adv_label}\n"
            response += (
                f"🎯 掷出: {result.total} + 加值{modifier} = {total} vs DC {target_dc}\n"
                f"{emoji} 结果: {level}"
            )
            return response

    except Exception as e:
        return f"❌ 检定失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "list_characters", "列出所有角色卡")
async def list_characters(_ctx: AgentCtx) -> str:
    """列出用户的所有角色卡"""
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        characters = await character_manager.list_characters(user_id, chat_key)
        if not characters:
            return "📄 当前没有角色卡，使用 create_character 创建新角色"

        response = "📋 角色卡列表:\n"
        for i, char in enumerate(characters, 1):
            response += f"{i}. {char['name']} ({char['system']})\n"
        return response
    except Exception as e:
        return f"❌ 获取角色列表失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "delete_character", "删除角色卡")
async def delete_character(_ctx: AgentCtx, name: str) -> str:
    """删除指定角色卡"""
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        success = await character_manager.delete_character(user_id, chat_key, name)
        if success:
            return f"✅ 角色卡 \"{name}\" 已删除"
        else:
            return f"❌ 删除角色卡 \"{name}\" 失败"
    except Exception as e:
        return f"❌ 删除失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "switch_character", "切换当前角色卡")
async def switch_character(_ctx: AgentCtx, name: str) -> str:
    """切换到指定角色卡"""
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        character = await character_manager.get_character(user_id, chat_key, name)
        if character.name == "default" and name != "default":
            return f"❌ 未找到角色卡 \"{name}\""
        await character_manager.set_active_character(user_id, chat_key, name)
        return f"✅ 已切换到角色卡: {character.name} ({character.system})"
    except Exception as e:
        return f"❌ 切换失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "sanity_check", "理智检定")
async def sanity_check(_ctx: AgentCtx, success_loss: str, failure_loss: str) -> str:
    """
    进行COC7理智检定(SAN Check)

    Args:
        success_loss: 成功时的理智损失表达式，如 "1", "1d4"
        failure_loss: 失败时的理智损失表达式，如 "1d6", "1d100"

    Returns:
        检定结果和更新后的SAN值
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        character = await character_manager.get_character(user_id, chat_key)
        if not character or character.name == "default":
            return "❌ 当前没有角色卡，请先使用 create_character 创建角色"

        if character.system != "CoC":
            return "❌ 理智检定仅支持COC7系统"

        san_value = character.attributes.get("SAN", 50)
        result = DiceRoller.roll_coc_check(san_value)

        # 计算理智损失
        if result["success"]:
            loss_expr = success_loss
            loss_result = DiceRoller.roll_expression(loss_expr)
            loss = loss_result.total
        else:
            loss_expr = failure_loss
            loss_result = DiceRoller.roll_expression(loss_expr)
            loss = loss_result.total

        # 大失败时损失所有SAN
        if result["level"] == "大失败":
            loss = san_value

        new_san = max(0, san_value - loss)
        character.attributes["SAN"] = new_san
        await character_manager.save_character(user_id, chat_key, character)

        emoji = "😰" if result["success"] else "🤯"
        return (
            f"{emoji} {character.name} 理智检定\n"
            f"🎯 当前SAN: {san_value}  掷出: {result['roll']}\n"
            f"📊 结果: {result['level']}\n"
            f"💔 理智损失: {loss} (骰子: {loss_expr}={loss_result.format_result()})\n"
            f"🧠 剩余SAN: {new_san}/{character.attributes.get('SANMAX', 99)}"
        )
    except Exception as e:
        return f"❌ 理智检定失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "skill_growth", "技能成长检定")
async def skill_growth(_ctx: AgentCtx, skill_name: str) -> str:
    """
    进行COC7技能成长检定(EN)

    Args:
        skill_name: 技能名称

    Returns:
        成长结果
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        character = await character_manager.get_character(user_id, chat_key)
        if not character or character.name == "default":
            return "❌ 当前没有角色卡"

        standard_name = character_manager.find_skill_by_alias(character, skill_name)
        target_skill = standard_name if standard_name else skill_name
        skill_value = character.skills.get(target_skill, 0)

        if skill_value >= 100:
            return f"📈 {target_skill} 已满值({skill_value})，无需成长"

        # 成长检定：1d100 > 当前技能值则成长
        roll = random.randint(1, 100)
        if roll > skill_value:
            # 成长1d10
            growth = random.randint(1, 10)
            old_value = skill_value
            new_value = min(100, skill_value + growth)
            character.skills[target_skill] = new_value
            await character_manager.save_character(user_id, chat_key, character)
            return (
                f"📈 {character.name} 的 {target_skill} 成长检定\n"
                f"🎲 掷出: {roll} > {old_value} → 成功!\n"
                f"✨ {target_skill}: {old_value} → {new_value} (+{new_value - old_value})"
            )
        else:
            return (
                f"📈 {character.name} 的 {target_skill} 成长检定\n"
                f"🎲 掷出: {roll} ≤ {skill_value} → 未成长"
            )
    except Exception as e:
        return f"❌ 成长检定失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "opposed_check", "对抗检定")
async def opposed_check(_ctx: AgentCtx, skill1: str, skill2: str, skill1_value: int = None, skill2_value: int = None) -> str:
    """
    COC7对抗检定

    Args:
        skill1: 主动方技能名
        skill2: 被动方技能名
        skill1_value: 主动方技能值（如未提供则从角色卡读取）
        skill2_value: 被动方技能值（如未提供则从角色卡读取）

    Returns:
        对抗结果
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        character = await character_manager.get_character(user_id, chat_key)
        if not character or character.name == "default":
            return "❌ 当前没有角色卡"

        # 获取技能值
        if skill1_value is None:
            s1 = character_manager.get_skill_value(character, skill1)
        else:
            s1 = skill1_value

        if skill2_value is None:
            s2 = character.skills.get(skill2, 50)
        else:
            s2 = skill2_value

        r1 = random.randint(1, 100)
        r2 = random.randint(1, 100)

        def get_level(roll, value):
            if roll == 1: return 5, "大成功"
            if roll <= value // 5: return 4, "极难成功"
            if roll <= value // 2: return 3, "困难成功"
            if roll <= value: return 2, "成功"
            if roll == 100 or (roll >= 96 and value < 50): return 0, "大失败"
            return 1, "失败"

        lv1, name1 = get_level(r1, s1)
        lv2, name2 = get_level(r2, s2)

        # 判定胜负
        if lv1 > lv2:
            winner = f"主动方 ({skill1})"
        elif lv2 > lv1:
            winner = f"被动方 ({skill2})"
        else:
            # 平手：技能值高者胜
            if s1 > s2:
                winner = f"主动方 ({skill1}) - 技能值高"
            elif s2 > s1:
                winner = f"被动方 ({skill2}) - 技能值高"
            else:
                winner = "平局"

        return (
            f"⚔️ 对抗检定: {skill1} vs {skill2}\n"
            f"🎯 主动方: {skill1}={s1} 掷出{r1} → {name1}\n"
            f"🎯 被动方: {skill2}={s2} 掷出{r2} → {name2}\n"
            f"🏆 结果: {winner}"
        )
    except Exception as e:
        return f"❌ 对抗检定失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "hp_manager", "生命值管理")
async def hp_manager(_ctx: AgentCtx, action: str, value: int = 0) -> str:
    """
    管理角色生命值

    Args:
        action: 操作类型 (show/add/sub/set)
        value: 数值

    Returns:
        当前HP状态
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key

    try:
        character = await character_manager.get_character(user_id, chat_key)
        if not character or character.name == "default":
            return "❌ 当前没有角色卡"

        if character.system == "CoC":
            hp = character.attributes.get("HP", 10)
            hp_max = character.attributes.get("HPMAX", 10)
        else:
            hp = character.secondary_attributes.get("生命值", 10)
            hp_max = hp

        if action == "show":
            pass
        elif action == "add":
            hp = min(hp_max, hp + value)
        elif action == "sub":
            hp = max(0, hp - value)
        elif action == "set":
            hp = max(0, min(hp_max, value))
        else:
            return f"❌ 未知操作: {action}，支持: show/add/sub/set"

        if character.system == "CoC":
            character.attributes["HP"] = hp
        else:
            character.secondary_attributes["生命值"] = hp

        await character_manager.save_character(user_id, chat_key, character)

        ratio = hp / hp_max if hp_max > 0 else 1
        if ratio >= 0.75:
            status = "🟢 健康"
        elif ratio >= 0.5:
            status = "🟡 轻伤"
        elif ratio >= 0.25:
            status = "🟠 重伤"
        elif hp > 0:
            status = "🔴 濒死"
        else:
            status = "💀 死亡"

        return f"❤️ {character.name} HP: {hp}/{hp_max} {status}"
    except Exception as e:
        return f"❌ HP管理失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "initiative_tracker", "先攻管理")
async def initiative_tracker(_ctx: AgentCtx, action: str, name: str = None, initiative: int = None) -> str:
    """
    先攻追踪管理

    Args:
        action: 操作 (add/list/clear/next)
        name: 角色名
        initiative: 先攻值

    Returns:
        先攻列表
    """
    user_id = getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))
    chat_key = _ctx.chat_key
    store_key = f"initiative.{chat_key}"

    try:
        init_data = await store.get(user_key=user_id, store_key=store_key)
        if init_data:
            init_list = json.loads(init_data)
        else:
            init_list = []

        if action == "add":
            if name is None:
                # 使用当前角色卡
                character = await character_manager.get_character(user_id, chat_key)
                name = character.name
                if initiative is None:
                    if character.system == "DnD5e":
                        init_mod = character.secondary_attributes.get("先攻修正", 0)
                        result = DiceRoller.roll_expression("1d20")
                        initiative = result.total + init_mod
                    else:
                        result = DiceRoller.roll_expression("1d100")
                        initiative = result.total

            init_list.append({"name": name, "init": initiative})
            init_list.sort(key=lambda x: x["init"], reverse=True)
            await store.set(user_key=user_id, store_key=store_key, value=json.dumps(init_list))
            return f"✅ 已添加 {name} 的先攻: {initiative}"

        elif action == "list":
            if not init_list:
                return "📋 先攻列表为空"
            response = "⚔️ 先攻顺序:\n"
            for i, entry in enumerate(init_list, 1):
                response += f"{i}. {entry['name']}: {entry['init']}\n"
            return response

        elif action == "clear":
            await store.set(user_key=user_id, store_key=store_key, value="[]")
            return "✅ 先攻列表已清空"

        elif action == "next":
            if not init_list:
                return "📋 先攻列表为空"
            current = init_list.pop(0)
            init_list.append(current)
            await store.set(user_key=user_id, store_key=store_key, value=json.dumps(init_list))
            return f"➡️ 当前回合: {current['name']}"

        else:
            return f"❌ 未知操作: {action}"
    except Exception as e:
        return f"❌ 先攻管理失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "wod_check", "黑暗世界骰池检定")
async def wod_check(_ctx: AgentCtx, pool_size: int, difficulty: int = 6) -> str:
    """
    进行WoD骰池检定

    Args:
        pool_size: 骰池大小
        difficulty: 困难度（默认6）

    Returns:
        检定结果
    """
    try:
        result = DiceRoller.roll_wod_pool(pool_size, difficulty)
        rolls_str = ", ".join(map(str, result["rolls"]))

        if result["botch"]:
            level = "💀 大失败"
        elif result["successes"] == 0:
            level = "❌ 失败"
        elif result["successes"] == 1:
            level = "✨ 成功"
        else:
            level = f"✨ {result['successes']}成功"

        return (
            f"🎲 WoD骰池检定: {pool_size}d10 (困难度{difficulty})\n"
            f"🎲 结果: [{rolls_str}]\n"
            f"📊 成功数: {result['successes']}\n"
            f"{level}"
        )
    except Exception as e:
        return f"❌ 骰池检定失败: {str(e)}"


# ============ 文档上传沙盒方法 ============

@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "upload_document", "上传并处理文档文件")
async def upload_document(_ctx: AgentCtx, file_path: str, doc_type: str = "module", custom_filename: Optional[str] = None) -> str:
    """
    处理用户上传的文档文件
    
    Args:
        file_path: AI提供的沙盒文件路径
        doc_type: 文档类型 (module/rule/story/background)
        custom_filename: 可选的自定义文件名
    
    Returns:
        处理结果信息
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"
    
    if doc_type not in ["module", "rule", "story", "background"]:
        return "❌ 文档类型必须是: module/rule/story/background"
    
    try:
        # 获取宿主机真实路径
        host_path = _ctx.fs.get_file(file_path)
        
        if not host_path.exists():
            return "❌ 指定的文件不存在"
        
        # 确定文件名
        if custom_filename:
            filename = custom_filename
        else:
            filename = host_path.stem  # 不包含扩展名的文件名
        
        # 读取文件内容并转换为文本
        with open(host_path, 'rb') as f:
            file_content = f.read()
        
        # 根据文件扩展名提取文本
        original_filename = host_path.name
        try:
            text_content = vector_db.document_processor.extract_text_by_extension(
                original_filename, file_content
            )
        except ValueError as e:
            return f"❌ 文件处理失败: {str(e)}"
        
        if not text_content.strip():
            return "❌ 文件内容为空或无法提取文本"
        
        # 生成文档ID并存储到向量数据库
        document_id = str(uuid.uuid4())
        chat_key = _ctx.chat_key

        chunk_count = await vector_db.store_document(
            document_id=document_id,
            filename=filename,
            text_content=text_content,
            chat_key=chat_key,
            document_type=doc_type
        )
        
        # 返回成功信息
        doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}[doc_type]
        result = f"✅ {doc_emoji} 文档 \"{filename}\" 上传成功！\n📊 已分割为 {chunk_count} 个片段\n📄 提取了 {len(text_content)} 个字符的文本内容"

        # 确保总是有返回值，不会为空
        if not result:
            result = f"✅ 文档上传完成（{filename}）"

        return result

    except Exception as e:
        error_msg = f"❌ 文档上传失败: {str(e)}"
        return error_msg


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "delete_document", "删除指定的文档")
async def delete_document(_ctx: AgentCtx, filename: str) -> str:
    """
    删除指定的文档
    
    Args:
        filename: 要删除的文档名称
    
    Returns:
        删除结果信息
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"
    
    try:
        chat_key = _ctx.chat_key

        # 查找该文档
        documents = await vector_db.list_documents(chat_key)
        target_doc = None

        for doc in documents:
            if doc["filename"] == filename:
                target_doc = doc
                break

        if not target_doc:
            return f"❌ 未找到名为 \"{filename}\" 的文档"

        # 删除文档
        success = await vector_db.delete_document(
            target_doc["document_id"], chat_key
        )
        
        if success:
            doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}.get(target_doc["document_type"], "📄")
            return f"✅ {doc_emoji} 文档 \"{filename}\" 已删除"
        else:
            return f"❌ 删除文档 \"{filename}\" 失败"
            
    except Exception as e:
        return f"❌ 删除文档失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "list_my_documents", "列出我的所有文档")
async def list_my_documents(_ctx: AgentCtx, doc_type: Optional[str] = None) -> str:
    """
    列出用户的所有文档
    
    Args:
        doc_type: 可选的文档类型过滤
    
    Returns:
        文档列表信息
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"
    
    try:
        chat_key = _ctx.chat_key

        documents = await vector_db.list_documents(chat_key, doc_type)
        
        if not documents:
            filter_text = f"类型为 {doc_type} 的" if doc_type else ""
            return f"📄 暂无{filter_text}已上传的文档"
        
        response = "📚 已上传的文档:\n"
        for i, doc in enumerate(documents, 1):
            doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}.get(doc["document_type"], "📄")
            response += f"{i}. {doc_emoji} {doc['filename']} ({doc['document_type']})\n"
            response += f"   预览: {doc['preview']}\n"

        # 确保总是有返回值，不会为空
        if not response:
            response = "📚 文档列表获取完成"

        return response

    except Exception as e:
        error_msg = f"❌ 获取文档列表失败: {str(e)}"
        return error_msg


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "search_documents", "搜索文档内容")
async def search_documents(_ctx: AgentCtx, query: str, doc_type: Optional[str] = None, limit: int = 5) -> str:
    """
    搜索文档内容
    
    Args:
        query: 搜索查询
        doc_type: 可选的文档类型过滤
        limit: 返回结果数量限制
    
    Returns:
        搜索结果信息
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"
    
    if not query.strip():
        return "❌ 请输入搜索关键词"
    
    try:
        chat_key = _ctx.chat_key

        results = await vector_db.search_documents(
            query=query,
            chat_key=chat_key,
            document_type=doc_type,
            limit=limit
        )
        
        if not results:
            return "🔍 未找到相关内容"
        
        response = f"🔍 搜索 \"{query}\" 的结果:\n"
        for i, result in enumerate(results, 1):
            response += f"{i}. {result['filename']} (相似度: {int(result['score']*100)}%)\n"
            response += f"   {result['text'][:100]}...\n\n"

        # 确保总是有返回值，不会为空
        if not response:
            response = "🔍 搜索完成，但未找到相关内容"

        return response

    except Exception as e:
        error_msg = f"❌ 搜索失败: {str(e)}"
        return error_msg


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "answer_document_question", "基于文档回答问题")
async def answer_document_question(_ctx: AgentCtx, question: str) -> str:
    """
    基于上传的文档回答问题
    
    Args:
        question: 用户的问题
    
    Returns:
        基于文档的回答
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"
    
    if not question.strip():
        return "❌ 请输入你的问题"
    
    try:
        chat_key = _ctx.chat_key

        # 获取相关文档上下文
        context = await vector_db.get_document_context(question, chat_key)
        
        if not context:
            return "❌ 没有找到相关的文档内容来回答这个问题"
        
        # 这里可以集成AI来生成更好的回答
        # 目前先返回相关的文档片段
        return f"🤖 基于文档的相关内容:\n{context}\n\n💡 以上是从您上传的文档中找到的相关信息"
        
    except Exception as e:
        return f"❌ 问答失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_supported_file_types", "获取支持的文件类型")
async def get_supported_file_types(_ctx: AgentCtx) -> str:
    """
    获取支持的文件类型信息
    
    Returns:
        支持的文件类型列表
    """
    return """📄 支持的文件类型:
• TXT - 纯文本文件
• PDF - PDF文档 (需要PyPDF2)
• DOCX - Microsoft Word文档 (需要python-docx)

📚 文档类型:
• module - 📘 游戏模组、剧本内容
• rule - 📜 游戏规则、系统说明  
• story - 📖 背景故事、剧情内容
• background - 🌍 世界观、设定资料

💡 使用方法:
1. 直接上传文件到聊天窗口
2. 告诉我文件类型，我会自动处理
3. 处理完成后可以搜索和询问文档内容"""


# ============ 战报相关沙盒方法 ============

@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "start_session_recording", "开始记录跑团会话")
async def start_session_recording(_ctx: AgentCtx, session_name: Optional[str] = None) -> str:
    """
    开始记录跑团会话，用于后续生成战报
    
    Args:
        session_name: 可选的会话名称
    
    Returns:
        开始记录的确认信息
    """
    try:
        session_id = await battle_report_manager.start_session(_ctx.chat_key, session_name)
        
        if session_name:
            return f"✅ 已开始记录跑团会话: {session_name}"
        else:
            return "✅ 已开始记录跑团会话，结束时将自动生成战报"
    except Exception as e:
        return f"❌ 开始记录失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "add_session_event", "记录跑团关键事件")
async def add_session_event(_ctx: AgentCtx, description: str, event_type: str = "general") -> str:
    """
    记录跑团中的关键事件
    
    Args:
        description: 事件描述
        event_type: 事件类型 (general/combat/story/discovery)
    
    Returns:
        记录结果
    """
    try:
        await battle_report_manager.add_key_event(_ctx.chat_key, description, event_type)
        return f"✅ 已记录关键事件: {description}"
    except Exception as e:
        return f"❌ 记录事件失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "generate_session_report", "生成跑团战报")
async def generate_session_report(_ctx: AgentCtx) -> str:
    """
    结束当前跑团并生成战报
    
    Returns:
        战报内容和Markdown文档
    """
    try:
        text_report, markdown_report, session_name = await battle_report_manager.generate_battle_report(_ctx.chat_key)
        
        if not text_report:
            return "❌ 没有正在进行的跑团会话"
        
        # 将Markdown文档保存到沙监文件系统
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"battle_report_{timestamp}.md"
        
        # 写入沙监文件系统
        sandbox_path = _ctx.fs.get_sandbox_path() / filename
        with open(sandbox_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        # 返回文本战报和文档路径
        response = f"{text_report}\n\n📄 Markdown战报已生成: {filename}"
        
        return response
        
    except Exception as e:
        return f"❌ 生成战报失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_battle_report_markdown", "获取Markdown格式战报")
async def get_battle_report_markdown(_ctx: AgentCtx, timestamp: str) -> str:
    """
    获取之前生成的Markdown战报
    
    Args:
        timestamp: 战报的时间戳
    
    Returns:
        Markdown格式的战报内容
    """
    try:
        report_key = f"battle_report.{_ctx.chat_key}.{timestamp}"
        markdown_report = await store.get(store_key=report_key)
        
        if not markdown_report:
            return "❌ 未找到指定的战报"
        
        return markdown_report
        
    except Exception as e:
        return f"❌ 获取战报失败: {str(e)}"


# ============ 骰子相关命令 ============

@on_command("r", priority=5, block=True).handle()
async def handle_dice_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """基础投骰指令"""
    expression = args.extract_plain_text().strip()
    if not expression:
        await finish_with(matcher, "请输入骰子表达式，如: r 3d6+2")
        return
    
    try:
        result = DiceRoller.roll_expression(expression)
        response = f"🎲 {result.format_result()}"
        
        # 添加特殊效果提示
        is_critical = False
        if result.is_critical_success():
            response += " ✨ 大成功!"
            is_critical = True
        elif result.is_critical_failure():
            response += " 💥 大失败!"
            is_critical = True
        
        # 确保有活跃的战报会话
        chat_key = str(getattr(event, "group_id", None) or event.user_id)
        await battle_report_manager.ensure_session_started(chat_key)
        
        # 记录到战报系统
        try:
            character = await character_manager.get_character(str(event.user_id), chat_key)
            char_name = character.name if character else "未知角色"
            
            await battle_report_manager.add_dice_roll(
                chat_key,
                str(event.user_id),
                char_name,
                expression,
                result.total,
                is_critical
            )
        except Exception:
            pass  # 如果记录失败，不影响正常投骰
        
        await finish_with(matcher, response)
        return
    except ValueError as e:
        await finish_with(matcher, f"❌ {str(e)}")
        return


@on_command("rh", aliases={"rhide"}, priority=5, block=True).handle()
async def handle_hidden_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """隐藏掷骰指令"""
    expression = args.extract_plain_text().strip()
    if not expression:
        await finish_with(matcher, "请输入骰子表达式，如: rh 3d6+2")
        return
    
    try:
        result = DiceRoller.roll_expression(expression)
        # 由于 NekroAgent 的 message API 没有 send_private 函数，
        # 隐藏掷骰直接在群聊中显示简化结果
        response = f"🎲 隐藏掷骰: {result.format_result(show_details=False)}"
        
        await finish_with(matcher, response)
        return
    except ValueError as e:
        await finish_with(matcher, f"❌ {str(e)}")
        return


@on_command("adv", aliases={"advantage"}, priority=5, block=True).handle()
async def handle_advantage_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """优势掷骰"""
    expression = args.extract_plain_text().strip()
    if not expression:
        expression = "d20"
    
    try:
        result = DiceRoller.roll_advantage(expression)
        await finish_with(matcher, f"🎲 优势掷骰: {result.format_result()}")
    except ValueError as e:
        await finish_with(matcher, f"❌ {str(e)}")
        return


@on_command("dis", aliases={"disadvantage"}, priority=5, block=True).handle()
async def handle_disadvantage_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """劣势掷骰"""
    expression = args.extract_plain_text().strip()
    if not expression:
        expression = "d20"
    
    try:
        result = DiceRoller.roll_disadvantage(expression)
        await finish_with(matcher, f"🎲 劣势掷骰: {result.format_result()}")
    except ValueError as e:
        await finish_with(matcher, f"❌ {str(e)}")
        return


@on_command("me", priority=5, block=True).handle()
async def handle_character_action(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """角色动作描述"""
    action = args.extract_plain_text().strip()
    if not action:
        await finish_with(matcher, "请描述你的角色动作，如: me 仔细观察房间")
        return
    
    # 获取角色信息
    try:
        chat_key = str(getattr(event, "group_id", None) or event.user_id)
        
        # 确保有活跃的战报会话
        await battle_report_manager.ensure_session_started(chat_key)
        
        character = await character_manager.get_character(str(event.user_id), chat_key)
        char_name = character.name if character else "你"
        
        response = f"🎭 {char_name} {action}"
        
        # 记录到战报系统
        try:
            await battle_report_manager.add_player_action(
                chat_key,
                str(event.user_id),
                char_name,
                action
            )
        except Exception:
            pass
        
        await finish_with(matcher, response)
        return
    except Exception:
        await finish_with(matcher, f"🎭 你 {action}")
        return


@on_command("ra", priority=5, block=True).handle()
async def handle_skill_check(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """技能检定 - 支持奖惩骰"""
    skill_input = args.extract_plain_text().strip()
    if not skill_input:
        await finish_with(matcher, "请输入技能名称，如: ra 侦察")
        return
    
    try:
        chat_key = str(getattr(event, "group_id", None) or event.user_id)
        
        # 确保有活跃的战报会话
        await battle_report_manager.ensure_session_started(chat_key)
        
        # 解析奖惩骰前缀
        bonus = 0
        penalty = 0
        if skill_input.startswith("b") or skill_input.startswith("p"):
            import re
            bp_match = re.match(r'^([bp])(\d*)\s+(.+)$', skill_input)
            if bp_match:
                bp_type = bp_match.group(1)
                bp_count = int(bp_match.group(2)) if bp_match.group(2) else 1
                skill_input = bp_match.group(3)
                if bp_type == "b":
                    bonus = bp_count
                else:
                    penalty = bp_count

        # 解析困难/极难前缀
        difficulty = "normal"
        if skill_input.startswith("困难"):
            difficulty = "hard"
            skill_input = skill_input[2:].strip()
        elif skill_input.startswith("极难"):
            difficulty = "extreme"
            skill_input = skill_input[2:].strip()
        elif skill_input.startswith("极"):
            difficulty = "extreme"
            skill_input = skill_input[1:].strip()
        # 获取角色卡
        character = await character_manager.get_character(str(event.user_id), chat_key)
        
        # 查找技能
        skill_name = character_manager.find_skill_by_alias(character, skill_input)
        if not skill_name:
            skill_name = skill_input
        
        # 获取技能值
        skill_value = character.skills.get(skill_name, 0)
        
        # 应用难度修正
        if difficulty == "hard":
            skill_value = skill_value // 2
        elif difficulty == "extreme":
            skill_value = skill_value // 5
        
        # 执行CoC检定
        if character.system == "CoC":
            result = DiceRoller.roll_coc_check_with_bonus(skill_value, bonus, penalty)
            response = (f"🎲 {character.name} 进行 {skill_name} 检定\n"
                       f"🎯 目标值: {skill_value}")
            if bonus > 0:
                response += f" (+{bonus}奖励骰)"
            elif penalty > 0:
                response += f" (-{penalty}惩罚骰)"
            if difficulty != "normal":
                response += f" [{difficulty}]"
            response += (f"\n🎲 掷出: {result['final_roll']} (原始{result['roll']})\n"
                        f"✨ 结果: {result['level']}")
            
            # 记录到战报系统
            try:
                await battle_report_manager.add_skill_check(
                    chat_key,
                    str(event.user_id),
                    character.name,
                    skill_name,
                    skill_value,
                    result['final_roll'],
                    result['level']
                )
            except Exception:
                pass
        else:
            # DND5E 完整检定
            modifier = character_manager.get_dnd_skill_modifier(character, skill_name)
            result = DiceRoller.roll_expression("1d20", is_check=True)
            total = result.total + modifier
            if result.is_critical_success():
                level = "大成功"
            elif result.is_critical_failure():
                level = "大失败"
            else:
                level = f"{total}"
            response = (f"🎲 {character.name} 进行 {skill_name} 检定\n"
                       f"🎯 掷出: {result.total} + 加值{modifier} = {total}\n"
                       f"✨ 结果: {level}")
        
        await finish_with(matcher, response)
        return
    except Exception as e:
        if "FinishedException" in str(type(e)):
            raise
        else:
            await finish_with(matcher, f"❌ 检定失败: {str(e)}")
        return


# ============ 角色卡管理命令 ============

@on_command("st", priority=5, block=True).handle()
async def handle_character_sheet(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """角色卡管理"""
    command = args.extract_plain_text().strip()
    user_id = str(event.user_id)
    chat_key = str(getattr(event, "group_id", None) or event.user_id)
    
    if not command or command == "show":
        # 显示角色卡
        try:
            character = await character_manager.get_character(user_id, chat_key)
            
            response = f"📋 角色卡: {character.name}\n"
            response += f"🎮 系统: {character.system}\n"
            
            if character.system == "CoC":
                attrs = ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU", "LUC"]
                attr_strs = []
                for attr in attrs:
                    if attr in character.attributes:
                        attr_strs.append(f"{attr}:{character.attributes[attr]}")
                response += f"📊 属性: {' '.join(attr_strs)}\n"
                response += f"❤️ HP:{character.attributes.get('HP', '?')}/{character.attributes.get('HPMAX', '?')} "
                response += f"🧠 SAN:{character.attributes.get('SAN', '?')}/{character.attributes.get('SANMAX', '?')}\n"
                
                if character.skills:
                    sorted_skills = sorted(character.skills.items(), key=lambda x: x[1], reverse=True)
                    skill_strs = [f"{k}:{v}" for k, v in sorted_skills[:10]]
                    response += f"🔧 技能: {' '.join(skill_strs)}"
                    if len(sorted_skills) > 10:
                        response += " ..."
            else:
                for k, v in character.attributes.items():
                    response += f"{k}:{v} "
                response += "\n"
            
            await finish_with(matcher, response)
        except Exception as get_error:
            if "FinishedException" in str(type(get_error)):
                raise
            else:
                await finish_with(matcher, f"❌ 获取角色卡失败: {str(get_error)}")
        return
    
    elif command.startswith("new "):
        char_name = command[4:].strip()
        if not char_name:
            await finish_with(matcher, "请指定角色名称")
            return
        
        import re
        char_name = re.sub(r'[<>\[\]{}]', '', char_name).strip()
        
        if not char_name:
            await finish_with(matcher, "角色名称不能为空或只包含特殊字符")
            return
        
        try:
            character = CharacterSheet(name=char_name)
            await character_manager.save_character(user_id, chat_key, character)
            await finish_with(matcher, f"✅ 已创建角色: {char_name}")
        except Exception as save_error:
            if "FinishedException" in str(type(save_error)):
                raise
            else:
                await finish_with(matcher, f"❌ 保存角色失败: {str(save_error)}")
        return
    
    elif command.startswith("set "):
        char_name = command[4:].strip()
        try:
            character = await character_manager.get_character(user_id, chat_key, char_name)
            if character.name == "default" and char_name != "default":
                await finish_with(matcher, f"❌ 未找到角色卡: {char_name}")
                return
            await character_manager.set_active_character(user_id, chat_key, char_name)
            await finish_with(matcher, f"✅ 已切换到: {character.name}")
        except Exception as e:
            await finish_with(matcher, f"❌ 切换失败: {str(e)}")
        return
    
    elif command == "list":
        try:
            characters = await character_manager.list_characters(user_id, chat_key)
            if not characters:
                await finish_with(matcher, "📄 当前没有角色卡")
                return
            response = "📋 角色卡列表:\n"
            for i, char in enumerate(characters, 1):
                response += f"{i}. {char['name']} ({char['system']})\n"
            await finish_with(matcher, response)
        except Exception as e:
            await finish_with(matcher, f"❌ 获取列表失败: {str(e)}")
        return
    
    elif command == "clr" or command == "clear":
        try:
            character = CharacterSheet(name="default")
            await character_manager.save_character(user_id, chat_key, character)
            await finish_with(matcher, "✅ 角色卡已清空")
        except Exception as e:
            await finish_with(matcher, f"❌ 清空失败: {str(e)}")
        return
    
    elif command.startswith("del "):
        attr_name = command[4:].strip()
        try:
            character = await character_manager.get_character(user_id, chat_key)
            if attr_name in character.skills:
                del character.skills[attr_name]
                await character_manager.save_character(user_id, chat_key, character)
                await finish_with(matcher, f"✅ 已删除技能: {attr_name}")
            elif attr_name in character.attributes:
                del character.attributes[attr_name]
                await character_manager.save_character(user_id, chat_key, character)
                await finish_with(matcher, f"✅ 已删除属性: {attr_name}")
            else:
                await finish_with(matcher, f"❌ 未找到: {attr_name}")
        except Exception as e:
            await finish_with(matcher, f"❌ 删除失败: {str(e)}")
        return
    
    elif command.startswith("temp "):
        template_name = command[5:].strip().lower()
        
        if template_name not in ["coc7", "dnd5e"]:
            await finish_with(matcher, "❌ 支持的模板: coc7, dnd5e")
            return
        
        character = await character_manager.get_character(user_id, chat_key)
        character.system = "CoC" if template_name == "coc7" else "DnD5e"
        
        await character_manager.save_character(user_id, chat_key, character)
        await finish_with(matcher, f"✅ 已切换到 {template_name} 模板")
        return
    
    elif command == "init":
        character = await character_manager.get_character(user_id, chat_key)
        
        template_name = "coc7" if character.system == "CoC" else "dnd5e"
        new_character = character_manager.generate_character(template_name, character.name)
        
        await character_manager.save_character(user_id, chat_key, new_character)
        await finish_with(matcher, f"✅ 已自动生成角色属性: {new_character.name}")
        return
    
    elif "=" in command or " " in command:
        # 尝试解析属性设置，如 "侦查 70" 或 "STR=60"
        try:
            character = await character_manager.get_character(user_id, chat_key)
            parts = command.split()
            
            if len(parts) >= 2:
                # st 侦查 70
                attr_name = parts[0]
                value_str = parts[1]
                
                # 尝试查找别名
                standard_skill = character_manager.find_skill_by_alias(character, attr_name)
                if standard_skill:
                    attr_name = standard_skill
                
                # 处理 + - 操作
                if value_str.startswith("+") or value_str.startswith("-"):
                    current_val = character.skills.get(attr_name, 0) if attr_name in character.skills else character.attributes.get(attr_name, 0)
                    delta = int(value_str)
                    new_val = current_val + delta
                else:
                    new_val = int(value_str)
                
                if attr_name in character.skills or (standard_skill and standard_skill in character.skills):
                    character.skills[attr_name] = new_val
                else:
                    character.attributes[attr_name] = new_val
                    # COC系统：如果改了POW/CON/SIZ，自动重算衍生属性
                    if character.system == "CoC":
                        if attr_name == "POW":
                            character.attributes["SANMAX"] = new_val
                            character.attributes["SAN"] = new_val
                            character.attributes["MPMAX"] = new_val // 5
                            character.attributes["MP"] = new_val // 5
                        elif attr_name in ["CON", "SIZ"]:
                            con = character.attributes.get("CON", 50)
                            siz = character.attributes.get("SIZ", 50)
                            character.attributes["HPMAX"] = (con + siz) // 10
                            character.attributes["HP"] = (con + siz) // 10
                
                await character_manager.save_character(user_id, chat_key, character)
                await finish_with(matcher, f"✅ 已设置 {attr_name} = {new_val}")
                return
        except Exception as e:
            await finish_with(matcher, f"❌ 设置失败: {str(e)}")
            return
            
    else:
        await finish_with(matcher, "用法: st [show/new <名称>/set <名称>/list/clr/del <属性>/temp <模板>/init/<属性> <值>]")
        return


# ============ CoC7 特殊指令 ============

@on_command("sc", priority=5, block=True).handle()
async def handle_sanity_check(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """理智检定"""
    content = args.extract_plain_text().strip()
    if not content:
        await finish_with(matcher, "用法: sc <成功损失>/<失败损失> [当前SAN]")
        return
    
    try:
        user_id = str(event.user_id)
        chat_key = str(getattr(event, "group_id", None) or event.user_id)
        character = await character_manager.get_character(user_id, chat_key)
        
        # 解析损失表达式
        parts = content.split()
        loss_expr = parts[0]
        if "/" not in loss_expr:
            await finish_with(matcher, "用法: sc <成功损失>/<失败损失>")
            return
        
        success_loss_str, failure_loss_str = loss_expr.split("/", 1)
        
        # 获取当前SAN
        if len(parts) >= 2:
            san_value = int(parts[1])
        else:
            san_value = character.attributes.get("SAN", 50)
        
        result = DiceRoller.roll_coc_check(san_value)
        
        if result["success"]:
            loss_result = DiceRoller.roll_expression(success_loss_str)
            loss = loss_result.total
        else:
            loss_result = DiceRoller.roll_expression(failure_loss_str)
            loss = loss_result.total
        
        if result["level"] == "大失败":
            loss = san_value
        
        new_san = max(0, san_value - loss)
        character.attributes["SAN"] = new_san
        await character_manager.save_character(user_id, chat_key, character)
        
        emoji = "😰" if result["success"] else "🤯"
        response = (
            f"{emoji} {character.name} 理智检定\n"
            f"🎯 当前SAN: {san_value} 掷出: {result['roll']}\n"
            f"📊 结果: {result['level']}\n"
            f"💔 理智损失: {loss}\n"
            f"🧠 剩余SAN: {new_san}"
        )
        await finish_with(matcher, response)
    except Exception as e:
        await finish_with(matcher, f"❌ 理智检定失败: {str(e)}")


@on_command("en", priority=5, block=True).handle()
async def handle_skill_growth(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """技能成长检定"""
    skill_input = args.extract_plain_text().strip()
    if not skill_input:
        await finish_with(matcher, "用法: en <技能名>")
        return
    
    try:
        user_id = str(event.user_id)
        chat_key = str(getattr(event, "group_id", None) or event.user_id)
        character = await character_manager.get_character(user_id, chat_key)
        
        skill_name = character_manager.find_skill_by_alias(character, skill_input)
        if not skill_name:
            skill_name = skill_input
        
        skill_value = character.skills.get(skill_name, 0)
        
        if skill_value >= 100:
            await finish_with(matcher, f"📈 {skill_name} 已满值({skill_value})")
            return
        
        roll = random.randint(1, 100)
        if roll > skill_value:
            growth = random.randint(1, 10)
            new_value = min(100, skill_value + growth)
            character.skills[skill_name] = new_value
            await character_manager.save_character(user_id, chat_key, character)
            await finish_with(matcher, 
                f"📈 {character.name} 的 {skill_name} 成长检定\n"
                f"🎲 掷出: {roll} > {skill_value} → 成功!\n"
                f"✨ {skill_name}: {skill_value} → {new_value} (+{new_value - skill_value})")
        else:
            await finish_with(matcher, 
                f"📈 {character.name} 的 {skill_name} 成长检定\n"
                f"🎲 掷出: {roll} ≤ {skill_value} → 未成长")
    except Exception as e:
        await finish_with(matcher, f"❌ 成长检定失败: {str(e)}")


@on_command("ti", priority=5, block=True).handle()
async def handle_temp_madness(matcher: Matcher, event: MessageEvent):
    """临时疯狂症状"""
    symptoms = [
        "失忆：调查员会发现自己只记得最后身处的安全地点，却没有任何来到这里的记忆。",
        "假性残疾：调查员陷入了心理性的失明、失聪或躯体缺失感中。",
        "暴力倾向：调查员陷入了六亲不认的暴力行为中。",
        "偏执：调查员陷入了严重的偏执妄想之中，所有人都想要伤害他。",
        "人际依赖：调查员因为一些原因而将某人当作了支柱。",
        "昏厥：调查员当场昏倒。",
        "逃避行为：调查员会用任何手段试图逃离现场。",
        "歇斯底里：调查员表现出大笑、哭泣、嘶吼、害怕等极端情绪反应。"
    ]
    symptom = random.choice(symptoms)
    await finish_with(matcher, f"🌀 临时疯狂症状:\n{symptom}")


@on_command("li", priority=5, block=True).handle()
async def handle_long_madness(matcher: Matcher, event: MessageEvent):
    """总结疯狂症状"""
    symptoms = [
        "恐惧症：调查员患上了一种恐惧症，如幽闭恐惧症、恐高症等。",
        "躁狂症：调查员患上了一种躁狂症，如盗窃癖、纵火癖等。",
        "幻觉：调查员持续产生幻觉。",
        "偏执：调查员持续处于偏执状态。",
        "解离性障碍：调查员的人格发生分裂或记忆丧失。",
        "强迫症：调查员产生了强迫性的行为模式。",
        "抑郁症：调查员陷入了严重的抑郁状态。",
        "创伤后应激障碍：调查员因恐怖经历而产生持续的心理创伤。"
    ]
    symptom = random.choice(symptoms)
    await finish_with(matcher, f"🌀 总结疯狂症状:\n{symptom}")


@on_command("cocchar", aliases={"coc"}, priority=5, block=True).handle()
async def handle_coc_char_gen(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """生成CoC角色"""
    name = args.extract_plain_text().strip() or "调查员"
    try:
        user_id = str(event.user_id)
        chat_key = str(getattr(event, "group_id", None) or event.user_id)
        character = character_manager.generate_character("coc7", name)
        await character_manager.save_character(user_id, chat_key, character)
        
        attrs = character.attributes
        response = (
            f"✅ CoC7角色 \"{name}\" 生成成功!\n"
            f"📊 STR:{attrs.get('STR')} CON:{attrs.get('CON')} SIZ:{attrs.get('SIZ')} "
            f"DEX:{attrs.get('DEX')} APP:{attrs.get('APP')} INT:{attrs.get('INT')} "
            f"POW:{attrs.get('POW')} EDU:{attrs.get('EDU')} LUC:{attrs.get('LUC')}\n"
            f"❤️ HP:{attrs.get('HP')}/{attrs.get('HPMAX')} "
            f"🧠 SAN:{attrs.get('SAN')}/{attrs.get('SANMAX')} "
            f"✨ MP:{attrs.get('MP')}/{attrs.get('MPMAX')}"
        )
        await finish_with(matcher, response)
    except Exception as e:
        await finish_with(matcher, f"❌ 角色生成失败: {str(e)}")


@on_command("dndchar", aliases={"dnd"}, priority=5, block=True).handle()
async def handle_dnd_char_gen(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """生成DND角色"""
    name = args.extract_plain_text().strip() or "冒险者"
    try:
        user_id = str(event.user_id)
        chat_key = str(getattr(event, "group_id", None) or event.user_id)
        character = character_manager.generate_character("dnd5e", name)
        await character_manager.save_character(user_id, chat_key, character)
        
        attrs = character.attributes
        response = (
            f"✅ DND5E角色 \"{name}\" 生成成功!\n"
            f"📊 STR:{attrs.get('STR')} DEX:{attrs.get('DEX')} CON:{attrs.get('CON')} "
            f"INT:{attrs.get('INT')} WIS:{attrs.get('WIS')} CHA:{attrs.get('CHA')}"
        )
        await finish_with(matcher, response)
    except Exception as e:
        await finish_with(matcher, f"❌ 角色生成失败: {str(e)}")


# ============ 战斗与先攻指令 ============

@on_command("ri", priority=5, block=True).handle()
async def handle_initiative(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """先攻追踪 - 支持优势劣势"""
    command = args.extract_plain_text().strip()
    user_id = str(event.user_id)
    chat_key = str(getattr(event, "group_id", None) or event.user_id)
    store_key = f"initiative.{chat_key}"
    
    try:
        init_data = await store.get(user_key=user_id, store_key=store_key)
        init_list = json.loads(init_data) if init_data else []
        
        # 解析优势劣势
        advantage = False
        disadvantage = False
        clean_command = command
        if "优势" in command:
            advantage = True
            clean_command = command.replace("优势", "").strip()
        elif "劣势" in command:
            disadvantage = True
            clean_command = command.replace("劣势", "").strip()
        
        if clean_command == "list" or clean_command == "":
            if not init_list:
                await finish_with(matcher, "📋 先攻列表为空")
                return
            response = "⚔️ 先攻顺序:\n"
            for i, entry in enumerate(init_list, 1):
                adv_mark = "🎲" if entry.get('advantage') else ""
                dis_mark = "💀" if entry.get('disadvantage') else ""
                response += f"{i}. {entry['name']}: {entry['init']} {adv_mark}{dis_mark}\n"
            await finish_with(matcher, response)
            return
        
        elif clean_command == "clear":
            await store.set(user_key=user_id, store_key=store_key, value="[]")
            await finish_with(matcher, "✅ 先攻列表已清空")
            return
        
        elif clean_command == "next":
            if not init_list:
                await finish_with(matcher, "📋 先攻列表为空")
                return
            current = init_list.pop(0)
            init_list.append(current)
            await store.set(user_key=user_id, store_key=store_key, value=json.dumps(init_list))
            await finish_with(matcher, f"➡️ 当前回合: {current['name']}")
            return
        
        elif clean_command.startswith("+"):
            # 添加角色到先攻
            char_name = clean_command[1:].strip()
            if not char_name:
                char_name = "未知"
            
            character = await character_manager.get_character(user_id, chat_key)
            
            # 掷先攻
            if advantage and not disadvantage:
                result = DiceRoller.roll_advantage("1d20")
                init_val = result.total
            elif disadvantage and not advantage:
                result = DiceRoller.roll_disadvantage("1d20")
                init_val = result.total
            else:
                init_val = random.randint(1, 20)
            
            if character.system == "DnD5e":
                init_mod = character.secondary_attributes.get("先攻修正", 0)
                init_val += init_mod
            
            entry = {"name": char_name, "init": init_val}
            if advantage:
                entry["advantage"] = True
            if disadvantage:
                entry["disadvantage"] = True
            
            init_list.append(entry)
            init_list.sort(key=lambda x: x["init"], reverse=True)
            await store.set(user_key=user_id, store_key=store_key, value=json.dumps(init_list))
            
            adv_text = " (优势)" if advantage else " (劣势)" if disadvantage else ""
            await finish_with(matcher, f"✅ {char_name} 先攻: {init_val}{adv_text}")
            return
        
        else:
            # 默认添加当前角色
            character = await character_manager.get_character(user_id, chat_key)
            
            if advantage and not disadvantage:
                result = DiceRoller.roll_advantage("1d20")
                init_val = result.total
            elif disadvantage and not advantage:
                result = DiceRoller.roll_disadvantage("1d20")
                init_val = result.total
            else:
                init_val = random.randint(1, 20)
            
            if character.system == "DnD5e":
                init_mod = character.secondary_attributes.get("先攻修正", 0)
                init_val += init_mod
            
            entry = {"name": character.name, "init": init_val}
            if advantage:
                entry["advantage"] = True
            if disadvantage:
                entry["disadvantage"] = True
            
            init_list.append(entry)
            init_list.sort(key=lambda x: x["init"], reverse=True)
            await store.set(user_key=user_id, store_key=store_key, value=json.dumps(init_list))
            
            adv_text = " (优势)" if advantage else " (劣势)" if disadvantage else ""
            await finish_with(matcher, f"✅ {character.name} 先攻: {init_val}{adv_text}")
            return
    except Exception as e:
        await finish_with(matcher, f"❌ 先攻管理失败: {str(e)}")


@on_command("hp", priority=5, block=True).handle()
async def handle_hp(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """生命值管理"""
    command = args.extract_plain_text().strip()
    user_id = str(event.user_id)
    chat_key = str(getattr(event, "group_id", None) or event.user_id)
    
    try:
        character = await character_manager.get_character(user_id, chat_key)
        if character.system == "CoC":
            hp = character.attributes.get("HP", 10)
            hp_max = character.attributes.get("HPMAX", 10)
        else:
            hp = character.secondary_attributes.get("生命值", 10)
            hp_max = hp
        
        if not command:
            await finish_with(matcher, f"❤️ {character.name} HP: {hp}/{hp_max}")
            return
        
        if command.startswith("+"):
            delta = int(command[1:])
            hp = min(hp_max, hp + delta)
        elif command.startswith("-"):
            delta = int(command[1:])
            hp = max(0, hp - delta)
        elif "/" in command:
            hp, hp_max = map(int, command.split("/", 1))
        else:
            hp = max(0, min(hp_max, int(command)))
        
        if character.system == "CoC":
            character.attributes["HP"] = hp
            if "/" in command:
                character.attributes["HPMAX"] = hp_max
        else:
            character.secondary_attributes["生命值"] = hp
        
        await character_manager.save_character(user_id, chat_key, character)
        await finish_with(matcher, f"❤️ {character.name} HP: {hp}/{hp_max}")
    except Exception as e:
        await finish_with(matcher, f"❌ HP管理失败: {str(e)}")


# ============ 特殊骰子指令 ============

@on_command("wod", aliases={"w"}, priority=5, block=True).handle()
async def handle_wod_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """WoD骰池"""
    content = args.extract_plain_text().strip()
    if not content:
        await finish_with(matcher, "用法: wod <骰池大小> [困难度]")
        return
    
    try:
        parts = content.split()
        pool_size = int(parts[0])
        difficulty = int(parts[1]) if len(parts) > 1 else 6
        
        result = DiceRoller.roll_wod_pool(pool_size, difficulty)
        rolls_str = ", ".join(map(str, result["rolls"]))
        
        if result["botch"]:
            level = "💀 大失败"
        elif result["successes"] == 0:
            level = "❌ 失败"
        else:
            level = f"✨ {result['successes']}成功"
        
        response = (
            f"🎲 WoD骰池: {pool_size}d10 (困难度{difficulty})\n"
            f"🎲 结果: [{rolls_str}]\n"
            f"📊 成功数: {result['successes']}\n"
            f"{level}"
        )
        await finish_with(matcher, response)
    except Exception as e:
        await finish_with(matcher, f"❌ 骰池检定失败: {str(e)}")


@on_command("fate", aliases={"f"}, priority=5, block=True).handle()
async def handle_fate_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """Fate骰子"""
    content = args.extract_plain_text().strip()
    try:
        modifier = 0
        dice_count = 4
        if content:
            if content.startswith("+") or content.startswith("-") or content.isdigit():
                modifier = int(content)
            else:
                parts = content.split()
                if parts[0].isdigit():
                    dice_count = int(parts[0])
                if len(parts) > 1:
                    modifier = int(parts[1])
        
        result = DiceRoller.roll_fate(dice_count, modifier)
        rolls_str = " ".join(["-" if r == -1 else "0" if r == 0 else "+" for r in result.rolls])
        
        await finish_with(matcher, f"🎲 Fate骰子: [{rolls_str}] = {result.total}")
    except Exception as e:
        await finish_with(matcher, f"❌ Fate骰子失败: {str(e)}")


@on_command("explode", aliases={"ex"}, priority=5, block=True).handle()
async def handle_explode_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """爆炸骰"""
    expression = args.extract_plain_text().strip()
    if not expression:
        await finish_with(matcher, "用法: explode <表达式> (如 explode d10)")
        return
    
    try:
        result = DiceRoller.roll_explode(expression)
        await finish_with(matcher, f"🎲 爆炸骰: {result.format_result()}")
    except Exception as e:
        await finish_with(matcher, f"❌ 爆炸骰失败: {str(e)}")


@on_command("repeat", aliases={"rn"}, priority=5, block=True).handle()
async def handle_repeat_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """多次掷骰"""
    content = args.extract_plain_text().strip()
    if not content:
        await finish_with(matcher, "用法: repeat <次数> <表达式> (如 repeat 3 d6)")
        return
    
    try:
        parts = content.split(maxsplit=1)
        if len(parts) < 2:
            await finish_with(matcher, "用法: repeat <次数> <表达式>")
            return
        
        times = int(parts[0])
        expression = parts[1]
        
        if times <= 0 or times > 20:
            await finish_with(matcher, "次数必须在1-20之间")
            return
        
        results = DiceRoller.roll_repeat(expression, times)
        response = f"🎲 重复掷骰 {times}次 {expression}:\n"
        for i, result in enumerate(results, 1):
            response += f"  第{i}次: {result.format_result()}\n"
        
        await finish_with(matcher, response)
    except Exception as e:
        await finish_with(matcher, f"❌ 重复掷骰失败: {str(e)}")


@on_command("name", priority=5, block=True).handle()
async def handle_random_name(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """随机姓名生成"""
    content = args.extract_plain_text().strip().lower()
    
    # 中文姓氏和名字
    surnames = ["赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈", "褚", "卫", "蒋", "沈", "韩", "杨", "朱", "秦", "尤", "许"]
    names_male = ["伟", "强", "磊", "军", "洋", "勇", "杰", "涛", "超", "明", "辉", "刚", "平", "健", "俊", "峰", "建", "华", "志", "文"]
    names_female = ["芳", "娜", "敏", "静", "丽", "艳", "娟", "霞", "秀", "玲", "婷", "雪", "颖", "梅", "慧", "莹", "兰", "洁", "倩", "燕"]
    
    en_first_male = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
    en_first_female = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen"]
    en_last = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    count = 1
    if " " in content:
        parts = content.split()
        for p in parts:
            if p.isdigit():
                count = min(int(p), 10)
    elif content.isdigit():
        count = min(int(content), 10)
    
    is_en = "en" in content
    is_male = "男" in content or "male" in content
    is_female = "女" in content or "female" in content
    
    results = []
    for _ in range(count):
        if is_en:
            last = random.choice(en_last)
            if is_male:
                first = random.choice(en_first_male)
            elif is_female:
                first = random.choice(en_first_female)
            else:
                first = random.choice(en_first_male + en_first_female)
            results.append(f"{first} {last}")
        else:
            surname = random.choice(surnames)
            if is_male:
                name = random.choice(names_male)
            elif is_female:
                name = random.choice(names_female)
            else:
                name = random.choice(names_male + names_female)
            results.append(f"{surname}{name}")
    
    response = "🎲 随机姓名:\n" + "\n".join(results)
    await finish_with(matcher, response)


@on_command("draw", priority=5, block=True).handle()
async def handle_draw_card(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """抽卡"""
    content = args.extract_plain_text().strip()
    try:
        count = int(content) if content.isdigit() else 1
        count = min(max(count, 1), 10)
    except:
        count = 1
    
    suits = ["♠", "♥", "♦", "♣"]
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    deck = [f"{s}{r}" for s in suits for r in ranks]
    
    drawn = random.sample(deck, min(count, len(deck)))
    response = f"🃏 抽卡结果 ({count}张):\n" + " ".join(drawn)
    await finish_with(matcher, response)


# ============ 文档管理命令 ============

@on_command("doc", aliases={"文档", "模组"}, priority=5, block=True).handle()
async def handle_document_help(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """文档系统帮助"""
    if not config.ENABLE_VECTOR_DB:
        await finish_with(matcher, "❌ 文档功能未启用")
        return
    
    command = args.extract_plain_text().strip()
    
    if command == "list":
        # 列出文档
        try:
            documents = await vector_db.list_documents(str(getattr(event, "group_id", None) or event.user_id))
            
            if not documents:
                await finish_with(matcher, "📄 暂无已上传的文档")
                return
            
            response = "📚 已上传的文档:\n"
            for i, doc in enumerate(documents, 1):
                doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}.get(doc["document_type"], "📄")
                response += f"{i}. {doc_emoji} {doc['filename']} ({doc['document_type']})\n"
            
            await finish_with(matcher, response)
            return
            
        except Exception as e:
            # 检查是否是FinishedException，如果是则让它正常传播
            if "FinishedException" in str(type(e)):
                raise  # 重新抛出FinishedException
            else:
                await finish_with(matcher, f"❌ 获取文档列表失败: {str(e)}")
            return
    
    elif command.startswith("search "):
        # 搜索文档
        query = command[7:].strip()
        if not query:
            await finish_with(matcher, "请输入搜索关键词")
            return
        
        try:
            results = await vector_db.search_documents(
                query=query,
                chat_key=str(getattr(event, "group_id", None) or event.user_id),
                limit=config.MAX_SEARCH_RESULTS
            )
            
            if not results:
                await finish_with(matcher, "🔍 未找到相关内容")
                return
            
            response = f"🔍 搜索 \"{query}\" 的结果:\n"
            for i, result in enumerate(results, 1):
                response += f"{i}. {result['filename']} (相似度: {int(result['score']*100)}%)\n"
                response += f"   {result['text'][:100]}...\n"
            
            await finish_with(matcher, response)
            return
            
        except Exception as e:
            # 检查是否是FinishedException，如果是则让它正常传播
            if "FinishedException" in str(type(e)):
                raise  # 重新抛出FinishedException
            else:
                await finish_with(matcher, f"❌ 搜索失败: {str(e)}")
            return
    
    else:
        # 显示帮助
        help_text = """📚 文档系统使用说明:

📤 上传文档:
🔹 方式一：直接上传文件
• 将PDF、DOCX、TXT文件直接拖拽到聊天窗口
• 告诉我文档类型(module/rule/story/background)，我会自动处理

🔹 方式二：文本输入
• doc_text <类型> <文档名> <内容>
• 类型: module(模组) / rule(规则) / story(故事) / background(背景)

🔍 搜索管理:
• doc search <关键词> - 搜索文档内容
• doc list - 列出所有文档
• ask <问题> - 智能问答

💡 使用示例:
📁 文件上传: "帮我处理这个模组PDF文件"
📝 文本输入: doc_text module 深海古城 [模组内容...]
🔍 搜索: doc search 深海古城的NPC
❓ 问答: ask 这个模组的主要剧情是什么

📄 支持格式: TXT, PDF, DOCX"""
        
        await finish_with(matcher, help_text)
        return


@on_command("doc_text", aliases={"文档文本", "text"}, priority=5, block=True).handle()
async def handle_upload_text_document(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """上传文本文档"""
    if not config.ENABLE_VECTOR_DB:
        await finish_with(matcher, "❌ 文档功能未启用")
        return
    
    content = args.extract_plain_text().strip()
    parts = content.split(' ', 2)
    
    if len(parts) < 3:
        await finish_with(matcher, "用法: doc_text <类型> <文档名> <内容>\n类型: module/rule/story/background")
        return
    
    doc_type = parts[0].lower()
    filename = parts[1]
    text_content = parts[2]
    
    if doc_type not in ["module", "rule", "story", "background"]:
        await finish_with(matcher, "❌ 文档类型必须是: module/rule/story/background")
        return
    
    try:
        document_id = str(uuid.uuid4())
        chunk_count = await vector_db.store_document(
            document_id=document_id,
            filename=filename,
            text_content=text_content,
            chat_key=str(getattr(event, "group_id", None) or event.user_id),
            document_type=doc_type
        )
        
        doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}[doc_type]
        await finish_with(matcher, f"✅ {doc_emoji} 文档 \"{filename}\" 上传成功！\n📊 已分割为 {chunk_count} 个片段")
        return
    except Exception as e:
        # 检查是否是FinishedException，如果是则让它正常传播
        if "FinishedException" in str(type(e)):
            raise  # 重新抛出FinishedException
        else:
            await finish_with(matcher, f"❌ 上传失败: {str(e)}")
        return


@on_command("ask", aliases={"问答", "询问", "qa"}, priority=5, block=True).handle()
async def handle_document_qa(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """智能文档问答"""
    if not config.ENABLE_VECTOR_DB:
        await finish_with(matcher, "❌ 文档功能未启用")
        return
    
    question = args.extract_plain_text().strip()
    if not question:
        await finish_with(matcher, "请输入你的问题")
        return
    
    try:
        answer = await vector_db.answer_question(
            question=question,
            chat_key=str(getattr(event, "group_id", None) or event.user_id)
        )
        
        await finish_with(matcher, f"🤖 AI回答:\n{answer}")
        return
    except Exception as e:
        # 检查是否是FinishedException，如果是则让它正常传播
        if "FinishedException" in str(type(e)):
            raise  # 重新抛出FinishedException
        else:
            await finish_with(matcher, f"❌ 问答失败: {str(e)}")
        return


# ============ 其他实用命令 ============

@on_command("jrrp", priority=5, block=True).handle()
async def handle_daily_luck(matcher: Matcher, event: MessageEvent):
    """今日人品"""
    try:
        luck_value = await character_manager.get_daily_luck(str(event.user_id))
        
        if luck_value >= 90:
            level = "超级欧皇"
        elif luck_value >= 70:
            level = "欧洲人"
        elif luck_value >= 30:
            level = "平民"
        else:
            level = "非洲人"
        
        await finish_with(matcher, f"🍀 今日人品值: {luck_value} ({level})")
    except Exception as e:
        # 检查是否是FinishedException，如果是则让它正常传播
        if "FinishedException" in str(type(e)):
            raise  # 重新抛出FinishedException
        else:
            await finish_with(matcher, f"❌ 获取人品失败: {str(e)}")


@on_command("help", priority=5, block=True).handle()
async def handle_help(matcher: Matcher, event: MessageEvent):
    """帮助信息"""
    help_text = """🎲 TRPG骰子系统 v2.0.0

🎯 基础掷骰:
• r <表达式> - 投骰 (如: r 3d6+2, r (2d6+6)*5)
• rh <表达式> - 隐藏掷骰
• adv [表达式] - 优势掷骰
• dis [表达式] - 劣势掷骰
• rn <次数> <表达式> - 多次掷骰
• ex <表达式> - 爆炸骰
• fate [修正] - Fate骰子
• wod <骰池> [困难度] - WoD骰池

⚔️ 技能检定:
• ra <技能> - 技能检定 (支持b/p奖惩骰前缀)
• ra 困难<技能> - 困难检定
• ra 极难<技能> - 极难检定
• sc <成功损失>/<失败损失> - 理智检定
• en <技能> - 技能成长
• cocchar [名字] - 生成CoC7角色
• dndchar [名字] - 生成DND5E角色

📋 角色卡管理 (.st):
• st - 显示角色卡
• st new <名字> - 创建角色
• st set <名字> - 切换角色
• st list - 列出角色卡
• st <属性> <值> - 设置属性/技能
• st del <属性> - 删除属性
• st clr - 清空角色卡
• st temp coc7/dnd5e - 切换模板
• st init - 自动生成属性

❤️ 状态管理:
• hp - 查看HP
• hp +<值> - 恢复HP
• hp -<值> - 损失HP
• hp <当前>/<最大> - 设置HP

⚔️ 战斗:
• ri - 加入先攻
• ri +<名字> - 添加角色先攻
• ri list - 查看先攻
• ri next - 下一回合
• ri clear - 清空先攻

📚 文档系统:
• 直接上传文件 - 支持PDF/DOCX/TXT
• doc - 文档帮助
• ask <问题> - 智能问答

📄 战报系统:
• session start [名称] - 开始记录跑团
• session end - 结束并生成战报
• session event <描述> - 记录关键事件

🍀 其他:
• me <动作> - 角色动作
• ti - 临时疯狂症状
• li - 总结疯狂症状
• name [参数] - 随机姓名 (如: name 男 3, name en)
• draw [数量] - 抽卡
• jrrp - 今日人品
• help - 显示帮助"""
    
    await finish_with(matcher, help_text)
    return


# ============ 战报管理命令 ============

@on_command("session", aliases={"跑团", "会话"}, priority=5, block=True).handle()
async def handle_session(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """跑团会话管理"""
    command = args.extract_plain_text().strip()
    chat_key = str(getattr(event, "group_id", None) or event.user_id)
    
    if command.startswith("start"):
        # 开始记录
        parts = command.split(maxsplit=1)
        session_name = parts[1] if len(parts) > 1 else None
        
        try:
            session_id = await battle_report_manager.start_session(chat_key, session_name)
            if session_name:
                await finish_with(matcher, f"✅ 已开始记录跑团会话: {session_name}\n\n📝 所有投骰、检定和行动将自动记录\n📄 结束时使用 'session end' 生成战报")
            else:
                await finish_with(matcher, f"✅ 已开始记录跑团会话\n\n📝 所有投骰、检定和行动将自动记录\n📄 结束时使用 'session end' 生成战报")
        except Exception as e:
            await finish_with(matcher, f"❌ 开始记录失败: {str(e)}")
        return
    
    elif command == "end":
        # 结束并生成战报
        try:
            text_report, markdown_report, session_name = await battle_report_manager.generate_battle_report(chat_key)
            
            if not text_report:
                await finish_with(matcher, "❌ 没有正在进行的跑团会话")
                return
            
            # 保存Markdown文档到存储
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"battle_report_{timestamp}.md"
            
            # 将Markdown内容保存到存储
            report_key = f"battle_report.{chat_key}.{timestamp}"
            await store.set(store_key=report_key, value=markdown_report)
            
            # 发送文本战报和Markdown文档提示
            response = text_report + f"\n\n📄 Markdown战报已生成: {filename}\n💡 请告诉AI获取Markdown战报文档"
            await finish_with(matcher, response)
            
        except Exception as e:
            if "FinishedException" in str(type(e)):
                raise
            else:
                await finish_with(matcher, f"❌ 生成战报失败: {str(e)}")
        return
    
    elif command.startswith("event"):
        # 记录关键事件
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            await finish_with(matcher, "请输入事件描述，如: session event 发现了神秘的地下入口")
            return
        
        description = parts[1]
        try:
            await battle_report_manager.add_key_event(chat_key, description)
            await finish_with(matcher, f"✅ 已记录关键事件: {description}")
        except Exception as e:
            await finish_with(matcher, f"❌ 记录事件失败: {str(e)}")
        return
    
    else:
        # 显示帮助
        help_text = """📄 跑团战报系统

🎯 使用方法:
• session start [名称] - 开始记录跑团会话
• session end - 结束并生成战报
• session event <描述> - 记录关键事件

📊 自动记录项:
• 🎲 所有投骰结果
• 🎯 技能检定详情
• 🎭 角色动作 (me命令)

🏆 战报内容:
• 每位PC的详细评分（5星级别）
• 游戏时长和统计数据
• 关键事件回顾
• 精彩时刻（大成功/大失败）

📄 输出格式:
• 聊天窗口显示文本版战报
• 自动生成Markdown文档

💡 示例:
session start 深海古城探险  # 开始记录
session event 发现了神秘的地下入口  # 记录关键事件
session end  # 生成战报"""
        
        await finish_with(matcher, help_text)
        return


# ============ 清理方法 ============

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件资源"""
    pass
