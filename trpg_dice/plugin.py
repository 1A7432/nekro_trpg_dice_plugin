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
battle_report_manager = BattleReportManager(store)

# 注册提示词注入
register_prompt_injections(plugin, character_manager, vector_db, store, config, battle_report_manager)


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
        response = f"🎲 掷骰结果已私发给你"
        
        # 发送结果到私聊
        try:
            await message.send_private(event.user_id, f"🎲 {result.format_result()}")
        except Exception:
            response = f"🎲 {result.format_result(show_details=False)}"
        
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
    """技能检定"""
    skill_input = args.extract_plain_text().strip()
    if not skill_input:
        await finish_with(matcher, "请输入技能名称，如: ra 侦察")
        return
    
    try:
        chat_key = str(getattr(event, "group_id", None) or event.user_id)
        
        # 确保有活跃的战报会话
        await battle_report_manager.ensure_session_started(chat_key)
        
        # 获取角色卡
        character = await character_manager.get_character(str(event.user_id), chat_key)
        
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
                       f"🎯 掀出 {result['roll']} (目标值: {skill_value})\n"
                       f"✨ 结果: {result['level']}")
            
            # 记录到战报系统
            try:
                await battle_report_manager.add_skill_check(
                    chat_key,
                    str(event.user_id),
                    character.name,
                    skill_name,
                    skill_value,
                    result['roll'],
                    result['level']
                )
            except Exception:
                pass
        else:
            # 其他系统使用基础投骰
            result = DiceRoller.roll_expression("d20")
            response = f"🎲 {character.name} 进行 {skill_name} 检定: {result.format_result()}"
        
        await finish_with(matcher, response)
        return
    except Exception as e:
        # 检查是否是FinishedException，如果是则让它正常传播
        if "FinishedException" in str(type(e)):
            raise  # 重新抛出FinishedException
        else:
            await finish_with(matcher, f"❌ 检定失败: {str(e)}")
        return


# ============ 角色卡管理命令 ============

@on_command("st", priority=5, block=True).handle()
async def handle_character_sheet(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """角色卡管理"""
    command = args.extract_plain_text().strip()
    
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
            # 检查是否是FinishedException，如果是则让它正常传播
            if "FinishedException" in str(type(get_error)):
                raise  # 重新抛出FinishedException
            else:
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
            # 检查是否是FinishedException，如果是则让它正常传播
            if "FinishedException" in str(type(save_error)):
                raise  # 重新抛出FinishedException
            else:
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
            documents = await vector_db.list_documents(str(event.user_id), str(getattr(event, "group_id", None) or event.user_id))
            
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
            user_id=str(event.user_id),
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
    help_text = """🎲 TRPG骰子系统 v1.0.0

🎯 基础指令:
• r <表达式> - 投骰 (如: r 3d6+2)
• ra <技能> - 技能检定
• me <动作> - 角色动作
• st - 角色卡管理

📚 文档系统:
• 直接上传文件 - 支持PDF/DOCX/TXT文件自动处理
• doc - 查看文档帮助
• ask <问题> - 基于上传文档的智能问答

📄 战报系统:
• session start [名称] - 开始记录跑团
• session end - 结束并生成战报
• session event <描述> - 记录关键事件

🍀 实用功能:
• jrrp - 今日人品
• help - 显示帮助

💡 新特性: 直接上传模组PDF文件，系统会自动解析并支持智能问答！
详细说明请使用各命令的帮助功能！"""
    
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
            
            # 发送文本战报
            await finish_with(matcher, text_report)
            
            # 保存Markdown文档到存储
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"battle_report_{timestamp}.md"
            
            # 将Markdown内容保存到存储
            report_key = f"battle_report.{chat_key}.{timestamp}"
            await store.set(store_key=report_key, value=markdown_report)
            
            # 发送Markdown文档提示
            await message.send(
                f"\n📄 Markdown战报已生成: {filename}\n\n请告诉AI获取Markdown战报文档"
            )
            
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
