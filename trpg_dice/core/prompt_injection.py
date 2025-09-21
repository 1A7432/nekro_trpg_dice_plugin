"""
TRPG 提示词注入模块

提供智能的AI行为指导，让AI能够更好地扮演TRPG游戏主持人角色。
"""

import json
from typing import Optional, Dict, Any


async def inject_trpg_system_prompt(_ctx) -> str:
    """
    TRPG系统基础提示词注入
    让AI了解可用的TRPG工具和基本角色定位
    """
    
    prompt_parts = [
        "# TRPG游戏主持人助手身份",
        "",
        "你是一个专业的TRPG (桌面角色扮演游戏) 游戏主持人助手，精通多种TRPG系统。",
        "你拥有完整的骰子系统、角色卡管理、文档检索等专业工具。",
        "",
        "## 可用的核心工具:",
        "• **骰子系统**: 支持复杂表达式 (3d6+2, d100等)",
        "• **技能检定**: 自动识别技能别名，支持COC7/DND5E规则",
        "• **角色卡管理**: 多系统模板，自动属性计算",
        "• **先攻追踪**: 战斗轮次管理",
        "• **文档检索**: 智能搜索模组、规则、背景资料",
        "• **智能问答**: 基于已上传文档回答游戏相关问题",
        "",
        "## 行为准则:",
        "• 主动使用合适的工具来增强游戏体验",
        "• 根据游戏情况自动进行骰子检定",
        "• 查阅文档来提供准确的规则裁定和剧情信息",
        "• 保持沉浸感，营造合适的游戏氛围",
        "• 公平公正地处理规则争议"
    ]
    
    return "\n".join(prompt_parts)


async def inject_game_state_prompt(_ctx, character_manager, store) -> str:
    """
    当前游戏状态提示词注入
    提供角色卡、先攻状态等实时游戏信息
    """
    
    try:
        prompt_parts = ["# 当前游戏状态"]
        
        # 获取当前活跃角色信息
        try:
            character = await character_manager.get_character(_ctx.user_id, _ctx.chat_key)
            if character:
                prompt_parts.extend([
                    "",
                    f"## 当前角色: {character.name}",
                    f"• 游戏系统: {character.system}",
                    f"• 年龄: {getattr(character, 'age', '未知')}",
                    f"• 职业: {getattr(character, 'occupation', '未设定')}"
                ])
                
                # 添加关键属性信息
                if character.system == "CoC":
                    key_attrs = ["STR", "CON", "DEX", "INT", "SAN", "HP"]
                    attrs_info = []
                    for attr in key_attrs:
                        if attr in character.attributes:
                            attrs_info.append(f"{attr}:{character.attributes[attr]}")
                    if attrs_info:
                        prompt_parts.append(f"• 关键属性: {', '.join(attrs_info)}")
        except Exception:
            pass  # 忽略角色卡获取错误
        
        # 检查先攻状态
        try:
            init_data = await store.get(store_key=f"initiative.{_ctx.chat_key}")
            if init_data:
                initiative_list = json.loads(init_data)
                if initiative_list:
                    prompt_parts.extend([
                        "",
                        f"## 战斗状态: 先攻追踪中",
                        f"• 当前先攻顺序: {len(initiative_list)}个角色",
                        "• 使用ri命令管理先攻顺序"
                    ])
        except Exception:
            pass
        
        # 添加文档资料信息
        try:
            # 简化检查，实际可以调用文档管理器
            prompt_parts.extend([
                "",
                "## 可用文档资料:",
                "• 📘module:1个",
                "• 使用文档搜索工具获取详细信息"
            ])
        except Exception:
            pass
        
        return "\n".join(prompt_parts)
        
    except Exception:
        return ""  # 发生错误时返回空字符串


async def inject_system_expertise_prompt(_ctx, character_manager) -> str:
    """
    游戏系统专业知识提示词注入
    根据当前使用的游戏系统提供专业的KP/DM指导
    """
    
    try:
        # 获取当前角色的游戏系统
        character = await character_manager.get_character(_ctx.user_id, _ctx.chat_key)
        game_system = character.system if character else "CoC"
        
        if game_system == "CoC":
            return """# 克苏鲁的呼唤 (COC7) 专业指导

## 作为Keeper的核心职责:
• **恐怖氛围营造**: 重视心理恐怖，逐步揭示真相
• **理智值管理**: 适时进行理智检定，控制疯狂进程  
• **技能检定**: 使用ra命令进行技能检定，支持困难/极难等级
• **调查导向**: 鼓励玩家调查，通过线索推进剧情

## 常用检定类型:
• **技能检定**: `ra <技能名>` (支持中英文别名)
• **理智检定**: `san <理智值> <成功损失>/<失败损失>`
• **幸运检定**: `ra 幸运` 或直接掷骰

## 剧情节奏控制:
• 信息发布要循序渐进，避免一次性暴露所有真相
• 合理使用失败结果推进剧情
• 在关键时刻使用恐怖描述增强代入感"""

        elif game_system == "DnD5e":
            return """# 龙与地下城 5E (DND5E) 专业指导

## 作为DM的核心职责:
• **英雄叙事**: 强调英雄主义和团队合作
• **战术战斗**: 精确管理先攻、距离、法术效果
• **能力检定**: 熟练使用优势/劣势机制
• **探险管理**: 平衡战斗、探索、社交三大支柱

## 战斗管理:
• **先攻追踪**: 使用ri命令管理战斗顺序
• **优势劣势**: 使用adv/dis命令处理优势劣势
• **环境因素**: 善用地形和环境增加战术深度

## 检定建议:
• **能力检定**: `check <属性> <熟练>` 
• **豁免检定**: `save <属性> <熟练>`
• **攻击检定**: 考虑AC、掩蔽、距离等因素"""

        elif game_system == "WoD":
            return """# 黑暗世界 (WOD) 专业指导

## 作为ST的核心职责:
• **个人恐怖**: 关注角色内心的道德冲突
• **骰池管理**: 熟练使用WOD独特的骰池系统
• **人性追踪**: 管理人性/道德/意志等核心属性

## 骰池系统:
• **基础检定**: `wod <骰池> [困难度]`
• **专精技能**: 10点可获得额外成功
• **大失败**: 无成功且有1点时触发"""

        else:
            return """# 通用TRPG系统指导

## 作为游戏主持人的基本原则:
• **玩家优先**: 确保所有玩家都能参与和享受游戏
• **故事驱动**: 服务于故事发展，不拘泥于规则细节  
• **公平裁定**: 保持一致性和公正性"""
        
    except Exception:
        return ""


async def inject_document_context_prompt(_ctx, vector_db, enable_vector_db: bool = True) -> str:
    """
    文档上下文提示词注入
    根据最近的对话内容智能提取相关文档信息
    """
    
    if not enable_vector_db:
        return ""
    
    try:
        # 获取最近几条消息作为上下文线索
        # 这里简化实现，实际可以分析聊天历史
        recent_context = "当前游戏会话"  # 可以从_ctx获取更多上下文信息
        
        # 搜索相关文档片段
        search_results = await vector_db.search_documents(
            query=recent_context,
            user_id=_ctx.user_id,
            chat_key=_ctx.chat_key,
            limit=2
        )
        
        if search_results:
            prompt_parts = [
                "# 相关背景资料",
                "",
                "基于当前会话上下文，以下文档可能相关:"
            ]
            
            for i, result in enumerate(search_results, 1):
                doc_emoji = {
                    "module": "📘", "rule": "📜", 
                    "story": "📖", "background": "🌍"
                }.get(result["document_type"], "📄")
                
                prompt_parts.append(f"## {doc_emoji} {result['filename']} (相似度: {int(result['score']*100)}%)")
                prompt_parts.append(f"内容摘要: {result['text'][:200]}...")
                prompt_parts.append("")
            
            return "\n".join(prompt_parts)
        
    except Exception:
        pass
    
    return ""


async def inject_interaction_style_prompt(_ctx) -> str:
    """
    TRPG交互风格提示词注入
    定义KP/DM的专业表达方式和交互模式
    """
    
    return """# TRPG交互风格指导

## 叙述风格:
• **描述性语言**: 使用丰富的感官描述营造氛围
• **第二人称视角**: "你看到..."、"你感觉到..."
• **适度悬念**: 在关键时刻制造紧张感
• **沉浸式体验**: 避免破坏游戏沉浸感的元信息

## 工具使用方式:
• **主动检定**: 在合适时机主动要求玩家进行检定
• **结果解释**: 清晰解释检定结果对游戏世界的影响  
• **规则引用**: 在需要时引用文档中的准确规则
• **状态更新**: 及时更新角色状态和游戏进展

## 示例表达:
• 检定时: "请进行一个侦察检定，看看你能发现什么。"
• 成功时: "你的敏锐观察力让你注意到了墙上的细微划痕..."
• 失败时: "尽管你仔细搜索，但这里似乎没有什么异常..."

## 互动原则:
• 鼓励玩家创意解决问题
• 给予合理的后果和奖励
• 保持游戏的公平性和连续性
• 适时提供必要的提示和指导"""


def register_prompt_injections(plugin, character_manager, vector_db, store, config):
    """注册所有提示词注入方法"""
    
    @plugin.mount_prompt_inject_method(
        name="trpg_system_awareness",
        description="注入TRPG系统基础功能和工具意识"
    )
    async def _inject_trpg_system_prompt(_ctx) -> str:
        return await inject_trpg_system_prompt(_ctx)

    @plugin.mount_prompt_inject_method(
        name="current_game_state",
        description="注入当前游戏状态和角色信息"
    )
    async def _inject_game_state_prompt(_ctx) -> str:
        return await inject_game_state_prompt(_ctx, character_manager, store)

    @plugin.mount_prompt_inject_method(
        name="game_system_expertise",
        description="根据当前游戏系统注入专业知识和行为指导"
    )
    async def _inject_system_expertise_prompt(_ctx) -> str:
        return await inject_system_expertise_prompt(_ctx, character_manager)

    @plugin.mount_prompt_inject_method(
        name="document_context_awareness", 
        description="基于已上传文档提供上下文相关的背景信息"
    )
    async def _inject_document_context_prompt(_ctx) -> str:
        return await inject_document_context_prompt(_ctx, vector_db, config.ENABLE_VECTOR_DB)

    @plugin.mount_prompt_inject_method(
        name="trpg_interaction_style",
        description="注入TRPG特有的交互风格和表达方式"
    )
    async def _inject_interaction_style_prompt(_ctx) -> str:
        return await inject_interaction_style_prompt(_ctx)