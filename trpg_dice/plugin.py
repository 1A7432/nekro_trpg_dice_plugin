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

# 创建插件实例
plugin = NekroPlugin(
    name="TRPG骰子系统",
    module_name="trpg_dice",
    description="完整的TRPG骰子系统，支持多种规则和复杂表达式",
    version="1.0.0",
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
    collection_name=plugin.get_vector_collection_name("trpg_documents")
)

# 注册提示词注入
register_prompt_injections(plugin, character_manager, vector_db, store, config)


# ============ 骰子相关命令 ============

@on_command("r", priority=5, block=True).handle()
async def handle_dice_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """基础掷骰指令"""
    expression = args.extract_plain_text().strip()
    if not expression:
        await finish_with(matcher, "请输入骰子表达式，如: r 3d6+2")
    
    try:
        result = DiceRoller.roll_expression(expression)
        response = f"🎲 {result.format_result()}"
        
        # 添加特殊效果提示
        if result.is_critical_success():
            response += " ✨ 大成功!"
        elif result.is_critical_failure():
            response += " 💥 大失败!"
        
        await finish_with(matcher, response)
    except ValueError as e:
        await finish_with(matcher, f"❌ {str(e)}")


@on_command("rh", aliases={"rhide"}, priority=5, block=True).handle()
async def handle_hidden_roll(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """隐藏掷骰指令"""
    expression = args.extract_plain_text().strip()
    if not expression:
        await finish_with(matcher, "请输入骰子表达式，如: rh 3d6+2")
    
    try:
        result = DiceRoller.roll_expression(expression)
        response = f"🎲 掷骰结果已私发给你"
        
        # 发送结果到私聊
        try:
            await message.send_private(event.user_id, f"🎲 {result.format_result()}")
        except Exception:
            response = f"🎲 {result.format_result(show_details=False)}"
        
        await finish_with(matcher, response)
    except ValueError as e:
        await finish_with(matcher, f"❌ {str(e)}")


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


@on_command("me", priority=5, block=True).handle()
async def handle_character_action(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """角色动作描述"""
    action = args.extract_plain_text().strip()
    if not action:
        await finish_with(matcher, "请描述你的角色动作，如: me 仔细观察房间")
    
    # 获取角色信息
    try:
        character = await character_manager.get_character(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id))
        char_name = character.name if character else "你"
        
        response = f"🎭 {char_name} {action}"
        await finish_with(matcher, response)
    except Exception:
        await finish_with(matcher, f"🎭 你 {action}")


@on_command("ra", priority=5, block=True).handle()
async def handle_skill_check(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """技能检定"""
    skill_input = args.extract_plain_text().strip()
    if not skill_input:
        await finish_with(matcher, "请输入技能名称，如: ra 侦察")
    
    try:
        # 获取角色卡
        character = await character_manager.get_character(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id))
        
        # 查找技能
        skill_name = character_manager.find_skill_by_alias(character, skill_input)
        if not skill_name:
            skill_name = skill_input
        
        # 获取技能值
        skill_value = character.skills.get(skill_name, 50)
        
        # 执行CoC检定
        if character.system == "CoC":
            result = DiceRoller.roll_coc_check(skill_value)
            response = (f"🎲 {character.name} 进行 {skill_name} 检定:\n"
                       f"🎯 掷出 {result['roll']} (目标值: {skill_value})\n"
                       f"✨ 结果: {result['level']}")
        else:
            # 其他系统使用基础掷骰
            result = DiceRoller.roll_expression("d20")
            response = f"🎲 {character.name} 进行 {skill_name} 检定: {result.format_result()}"
        
        await finish_with(matcher, response)
    except Exception as e:
        await finish_with(matcher, f"❌ 检定失败: {str(e)}")


# ============ 角色卡管理命令 ============

@on_command("st", priority=5, block=True).handle()
async def handle_character_sheet(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """角色卡管理"""
    command = args.extract_plain_text().strip()
    
    try:
        if not command or command == "show":
            # 显示角色卡
            try:
                character = await character_manager.get_character(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id))
                
                response = f"📋 角色卡: {character.name}\n"
                response += f"🎮 系统: {character.system}\n"
                
                if character.system == "CoC":
                    # COC7属性显示
                    attrs = ["STR", "CON", "DEX", "INT", "SAN", "HP"]
                    attr_strs = []
                    for attr in attrs:
                        if attr in character.attributes:
                            attr_strs.append(f"{attr}:{character.attributes[attr]}")
                    response += f"📊 属性: {' '.join(attr_strs)}\n"
                    
                    # 显示部分技能
                    if character.skills:
                        skill_list = list(character.skills.items())[:5]
                        skill_strs = [f"{k}:{v}" for k, v in skill_list]
                        response += f"🔧 技能: {' '.join(skill_strs)}..."
                
                await finish_with(matcher, response)
            except Exception as get_error:
                await finish_with(matcher, f"❌ 获取角色卡失败: {str(get_error)}")
            return
            
        elif command.startswith("new "):
            # 创建新角色
            char_name = command[4:].strip()
            if not char_name:
                await finish_with(matcher, "请指定角色名称")
                return
            
            # 清理角色名中的特殊字符
            import re
            char_name = re.sub(r'[<>\[\]{}]', '', char_name).strip()
            
            if not char_name:
                await finish_with(matcher, "角色名称不能为空或只包含特殊字符")
                return
            
            try:
                character = CharacterSheet(name=char_name)
                await character_manager.save_character(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id), character)
                await finish_with(matcher, f"✅ 已创建角色: {char_name}")
            except Exception as save_error:
                await finish_with(matcher, f"❌ 保存角色失败: {str(save_error)}")
            return
            
        elif command.startswith("temp "):
            # 切换模板
            template_name = command[5:].strip().lower()
            
            if template_name not in ["coc7", "dnd5e"]:
                await finish_with(matcher, "❌ 支持的模板: coc7, dnd5e")
                return
            
            character = await character_manager.get_character(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id))
            character.system = "CoC" if template_name == "coc7" else "DnD5e"
            
            await character_manager.save_character(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id), character)
            await finish_with(matcher, f"✅ 已切换到 {template_name} 模板")
            return
            
        elif command == "init":
            # 自动生成角色属性
            character = await character_manager.get_character(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id))
            
            # 使用模板生成
            template_name = "coc7" if character.system == "CoC" else "dnd5e"
            new_character = character_manager.generate_character(template_name, character.name)
            
            await character_manager.save_character(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id), new_character)
            await finish_with(matcher, f"✅ 已自动生成角色属性: {new_character.name}")
            return
            
        else:
            await finish_with(matcher, "用法: st [show/new <名称>/temp <模板>/init]")
            return
            
    except Exception as e:
        await finish_with(matcher, f"❌ 未知错误: {str(e)}")


# ============ 文档管理命令 ============

@on_command("doc", aliases={"文档", "模组"}, priority=5, block=True).handle()
async def handle_document_help(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """文档系统帮助"""
    if not config.ENABLE_VECTOR_DB:
        await finish_with(matcher, "❌ 文档功能未启用")
    
    command = args.extract_plain_text().strip()
    
    if command == "list":
        # 列出文档
        try:
            documents = await vector_db.list_documents(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id))
            
            if not documents:
                await finish_with(matcher, "📄 暂无已上传的文档")
            
            response = "📚 已上传的文档:\n"
            for i, doc in enumerate(documents, 1):
                doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}.get(doc["document_type"], "📄")
                response += f"{i}. {doc_emoji} {doc['filename']} ({doc['document_type']})\n"
            
            await finish_with(matcher, response)
            
        except Exception as e:
            await finish_with(matcher, f"❌ 获取文档列表失败: {str(e)}")
    
    elif command.startswith("search "):
        # 搜索文档
        query = command[7:].strip()
        if not query:
            await finish_with(matcher, "请输入搜索关键词")
        
        try:
            results = await vector_db.search_documents(
                query=query,
                user_id=str(event.user_id),
                chat_key=str(getattr(event, "group_id", None) or event.user_id),
                limit=config.MAX_SEARCH_RESULTS
            )
            
            if not results:
                await finish_with(matcher, "🔍 未找到相关内容")
            
            response = f"🔍 搜索 \"{query}\" 的结果:\n"
            for i, result in enumerate(results, 1):
                response += f"{i}. {result['filename']} (相似度: {int(result['score']*100)}%)\n"
                response += f"   {result['text'][:100]}...\n"
            
            await finish_with(matcher, response)
            
        except Exception as e:
            await finish_with(matcher, f"❌ 搜索失败: {str(e)}")
    
    else:
        # 显示帮助
        help_text = """📚 文档系统使用说明:

📤 上传文档:
• doc_text <类型> <文档名> <内容>
• 类型: module(模组) / rule(规则) / story(故事) / background(背景)

🔍 搜索管理:
• doc search <关键词> - 搜索文档内容
• doc list - 列出所有文档
• ask <问题> - 智能问答

💡 使用示例:
• doc_text module 深海古城 [模组内容...]
• doc search 深海古城的NPC
• ask 这个模组的主要剧情是什么"""
        
        await finish_with(matcher, help_text)


@on_command("doc_text", aliases={"文档文本", "text"}, priority=5, block=True).handle()
async def handle_upload_text_document(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """上传文本文档"""
    if not config.ENABLE_VECTOR_DB:
        await finish_with(matcher, "❌ 文档功能未启用")
    
    content = args.extract_plain_text().strip()
    parts = content.split(' ', 2)
    
    if len(parts) < 3:
        await finish_with(matcher, "用法: doc_text <类型> <文档名> <内容>\n类型: module/rule/story/background")
    
    doc_type = parts[0].lower()
    filename = parts[1]
    text_content = parts[2]
    
    if doc_type not in ["module", "rule", "story", "background"]:
        await finish_with(matcher, "❌ 文档类型必须是: module/rule/story/background")
    
    try:
        document_id = str(uuid.uuid4())
        chunk_count = await vector_db.store_document(
            document_id=document_id,
            filename=filename,
            text_content=text_content,
            user_id=str(event.user_id),
            chat_key=str(getattr(event, "group_id", None) or event.user_id),
            document_type=doc_type
        )
        
        doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}[doc_type]
        await finish_with(matcher, f"✅ {doc_emoji} 文档 \"{filename}\" 上传成功！\n📊 已分割为 {chunk_count} 个片段")
        
    except Exception as e:
        await finish_with(matcher, f"❌ 上传失败: {str(e)}")


@on_command("ask", aliases={"问答", "询问", "qa"}, priority=5, block=True).handle()
async def handle_document_qa(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """智能文档问答"""
    if not config.ENABLE_VECTOR_DB:
        await finish_with(matcher, "❌ 文档功能未启用")
    
    question = args.extract_plain_text().strip()
    if not question:
        await finish_with(matcher, "请输入你的问题")
    
    try:
        answer = await vector_db.answer_question(
            question=question,
            user_id=str(event.user_id),
            chat_key=str(getattr(event, "group_id", None) or event.user_id)
        )
        
        await finish_with(matcher, f"🤖 AI回答:\n{answer}")
        
    except Exception as e:
        await finish_with(matcher, f"❌ 问答失败: {str(e)}")


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
        await finish_with(matcher, f"❌ 获取人品失败: {str(e)}")


@on_command("help", priority=5, block=True).handle()
async def handle_help(matcher: Matcher, event: MessageEvent):
    """帮助信息"""
    help_text = """🎲 TRPG骰子系统 v1.0.0

🎯 基础指令:
• r <表达式> - 掷骰 (如: r 3d6+2)
• ra <技能> - 技能检定
• me <动作> - 角色动作
• st - 角色卡管理

📚 文档系统:
• doc - 查看文档帮助
• ask <问题> - 智能问答

🍀 实用功能:
• jrrp - 今日人品
• help - 显示帮助

详细说明请使用各命令的帮助功能！"""
    
    await finish_with(matcher, help_text)


# ============ 清理方法 ============

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件资源"""
    pass