"""
TRPG 提示词注入模块

提供智能的AI行为指导，让AI能够更好地扮演TRPG游戏主持人角色。
增强版：支持场景感知、角色状态实时注入、战斗状态追踪、文档上下文检索。
"""

import json
from typing import Optional, Dict, Any

from ..i18n import t_prompt


def _get_user_id(_ctx) -> str:
    """获取用户ID"""
    return getattr(_ctx, 'from_user_id', getattr(_ctx, 'from_platform_userid', ''))


def _summarize_knowledge_item(item: Any) -> str:
    """将不同知识池条目格式统一压缩为提示词中的一行摘要。"""
    if not isinstance(item, dict):
        return str(item)

    title = item.get("name") or item.get("title") or item.get("time") or item.get("event") or "条目"
    summary = (
        item.get("summary")
        or item.get("description")
        or item.get("event")
        or item.get("background")
        or item.get("role")
        or item.get("location")
        or ""
    )

    extras = []
    if item.get("focus"):
        extras.append(f"焦点: {item['focus']}")
    if item.get("location") and item.get("location") != title:
        extras.append(f"位置: {item['location']}")
    if item.get("leads_to"):
        extras.append(f"指向: {item['leads_to']}")
    if item.get("san_loss"):
        extras.append(f"SAN损失: {item['san_loss']}")

    detail = str(summary).strip()
    if extras:
        detail = f"{detail} ({'；'.join(extras)})" if detail else "；".join(extras)
    if len(detail) > 180:
        detail = detail[:180] + "..."
    return f"- {title}: {detail}" if detail else f"- {title}"


async def inject_trpg_system_prompt(_ctx) -> str:
    """
    TRPG系统基础提示词注入
    让AI了解可用的TRPG工具和基本角色定位
    """
    return t_prompt("prompt.kp.system_prompt")


async def inject_game_state_prompt(_ctx, character_manager, store) -> str:
    """
    极简战情面板注入（支持全团多角色）
    每轮对话自动注入当前场景、时间、全团角色状态、NPC、线索、世界变更等核心信息。
    """

    try:
        user_id = _get_user_id(_ctx)
        chat_key = _ctx.chat_key
        lines = ["═══════════════════════════════════════", "【战情面板】", "═══════════════════════════════════════"]

        # ── 场景 & 时间 & 焦点 ──
        scene_name = "未知"
        focus = "探索"
        clock_time = "未设定"

        try:
            clock_data = await store.get(user_key="", store_key=f"game_clock.{chat_key}")
            if clock_data:
                clock = json.loads(clock_data)
                clock_time = clock.get("current_time", "未设定")
        except Exception:
            pass

        try:
            notes_data = await store.get(user_key="", store_key=f"kp_notes.{chat_key}")
            if notes_data:
                notes = json.loads(notes_data)
                scene_name = notes.get("current_scene", "未知")
                focus = notes.get("current_focus", "探索")
        except Exception:
            pass

        lines.extend([
            f"🎬 当前场景: {scene_name}",
            f"⏰ 游戏时间: {clock_time}",
            f"🎯 当前焦点: {focus}",
        ])

        # ── 全团角色状态（从 party_roster 读取） ──
        try:
            roster = await character_manager.get_party_roster(chat_key)
            if roster:
                lines.append("")
                lines.append("👤 调查员状态:")
                for member in roster:
                    name = member.get("name", "?")
                    system = member.get("system", "CoC")
                    if system == "CoC":
                        hp = member.get("HP", "?/?")
                        san = member.get("SAN", "?/?")
                        mp = member.get("MP", "?/?")
                        status_eff = member.get("status_effects", [])
                        eff_str = " | ".join(status_eff) if status_eff else "无"
                        lines.append(f"   • {name} | HP:{hp} SAN:{san} MP:{mp} | {eff_str}")
                    else:
                        hp = member.get("HP", "?")
                        ac = member.get("AC", "?")
                        status_eff = member.get("status_effects", [])
                        eff_str = " | ".join(status_eff) if status_eff else "无"
                        lines.append(f"   • {name} | HP:{hp} AC:{ac} | {eff_str}")
            else:
                # 回退：只显示当前角色
                character = await character_manager.get_character(user_id, chat_key)
                if character and character.name != "default":
                    attrs = character.attributes
                    if character.system == "CoC":
                        hp = f"{attrs.get('HP', '?')}/{attrs.get('HPMAX', '?')}"
                        san = f"{attrs.get('SAN', '?')}/{attrs.get('SANMAX', '?')}"
                        mp = f"{attrs.get('MP', '?')}/{attrs.get('MPMAX', '?')}"
                        lines.append(f"👤 {character.name} | HP:{hp} SAN:{san} MP:{mp}")
                    else:
                        hp = attrs.get("HP", "?")
                        ac = getattr(character, 'secondary_attributes', {}).get("护甲等级", "?")
                        lines.append(f"👤 {character.name} | HP:{hp} AC:{ac}")
        except Exception:
            pass

        # ── 活跃NPC（最近3条） ──
        try:
            notes_data = await store.get(user_key="", store_key=f"kp_notes.{chat_key}")
            if notes_data:
                notes = json.loads(notes_data)
                npc_items = notes.get("npc_status", [])[-3:]
                if npc_items:
                    lines.append("")
                    lines.append("👥 活跃NPC:")
                    for item in npc_items:
                        lines.append(f"   • {item.get('content', '')}")
        except Exception:
            pass

        # ── 调查背景（opening_facts 优先显示） ──
        try:
            notes_data = await store.get(user_key="", store_key=f"kp_notes.{chat_key}")
            if notes_data:
                notes = json.loads(notes_data)
                all_facts = notes.get("confirmed_facts", [])
                opening = [f for f in all_facts if f.get("time") == "开局"]
                if opening:
                    lines.append("")
                    lines.append("📋 调查背景:")
                    for item in opening[-5:]:
                        lines.append(f"   • {item.get('content', '')}")
        except Exception:
            pass

        # ── 已确认事实（最近5条，不含开局） ──
        try:
            notes_data = await store.get(user_key="", store_key=f"kp_notes.{chat_key}")
            if notes_data:
                notes = json.loads(notes_data)
                facts = [f for f in notes.get("confirmed_facts", []) if f.get("time") != "开局"][-5:]
                lines.append("")
                if facts:
                    lines.append("📌 已确认事实:")
                    for item in facts:
                        lines.append(f"   • {item.get('content', '')}")
                else:
                    lines.append("📌 已确认事实: 暂无")
        except Exception:
            pass

        # ── 进行中线索（从 player_pool 读取） ──
        try:
            player_data = await store.get(user_key="", store_key=f"module_player_pool.{chat_key}")
            if player_data:
                player = json.loads(player_data)
                clues = player.get("clues", [])
                if clues:
                    lines.append("")
                    lines.append("🔍 进行中线索:")
                    for c in clues[-5:]:
                        desc = c.get("description", "")[:40]
                        lines.append(f"   • {c.get('name', '?')}: {desc}")
        except Exception:
            pass

        # ── 世界变更（最近3条） ──
        try:
            notes_data = await store.get(user_key="", store_key=f"kp_notes.{chat_key}")
            if notes_data:
                notes = json.loads(notes_data)
                changes = notes.get("world_changes", [])[-3:]
                if changes:
                    lines.append("")
                    lines.append("🌍 世界变更:")
                    for item in changes:
                        lines.append(f"   • {item.get('content', '')}")
        except Exception:
            pass

        # ── 先攻状态（战斗中才显示） ──
        try:
            init_data = await store.get(user_key=user_id, store_key=f"initiative.{chat_key}")
            if init_data:
                initiative_list = json.loads(init_data)
                if initiative_list:
                    lines.append("")
                    lines.append("⚔️ 先攻顺序:")
                    for i, entry in enumerate(initiative_list[:5], 1):
                        marker = " 👈" if i == 1 else ""
                        lines.append(f"   {i}. {entry['name']} ({entry['init']}){marker}")
        except Exception:
            pass

        lines.append("═══════════════════════════════════════")
        return "\n".join(lines)

    except Exception:
        return ""

async def inject_system_expertise_prompt(_ctx, character_manager) -> str:
    """
    游戏系统专业知识提示词注入
    根据当前使用的游戏系统提供专业的KP/DM指导
    """

    try:
        user_id = _get_user_id(_ctx)
        character = await character_manager.get_character(user_id, _ctx.chat_key)
        game_system = character.system if character else "CoC"

        if game_system == "CoC":
            return t_prompt("prompt.kp.expertise.coc")

        elif game_system == "DnD5e":
            return t_prompt("prompt.kp.expertise.dnd5e")

        elif game_system == "WoD":
            return t_prompt("prompt.kp.expertise.wod")

        else:
            return t_prompt("prompt.kp.expertise.generic")

    except Exception:
        return ""


async def inject_document_context_prompt(_ctx, vector_db, store, enable_vector_db: bool = True) -> str:
    """
    文档上下文提示词注入
    优先使用已初始化的模组知识池，如果没有则回退到向量检索
    """

    if not enable_vector_db:
        return ""

    chat_key = _ctx.chat_key

    try:
        # 1. 优先检查知识池状态
        status = await store.get(user_key="", store_key=f"module_init_status.{chat_key}")

        # 知识池已就绪，直接注入结构化知识
        if status == "ready":
            keeper_data = await store.get(user_key="", store_key=f"module_keeper_pool.{chat_key}")
            player_data = await store.get(user_key="", store_key=f"module_player_pool.{chat_key}")

            prompt_parts = [
                "═══════════════════════════════════════",
                t_prompt("prompt.kp.doc.keeper_pool_title"),
                "═══════════════════════════════════════",
                "",
                t_prompt("prompt.kp.doc.keeper_pool_warning_1"),
                t_prompt("prompt.kp.doc.keeper_pool_warning_2"),
                t_prompt("prompt.kp.doc.keeper_pool_warning_3"),
                "",
            ]

            if keeper_data:
                keeper_pool = json.loads(keeper_data)
                prompt_parts.append(t_prompt("prompt.kp.doc.keeper_pool_label"))
                for category, items in keeper_pool.items():
                    if category in ("summary", "background"):
                        if items:
                            text = str(items)
                            if len(text) > 300:
                                text = text[:300] + "..."
                            prompt_parts.append(f"### {category}\n{text}")
                    elif items:
                        prompt_parts.append(f"### {category}")
                        for item in items[:20]:
                            prompt_parts.append(_summarize_knowledge_item(item))
                            if isinstance(item, dict) and item.get('spoiler_tags'):
                                prompt_parts.append(f"  {t_prompt('prompt.kp.doc.spoiler_label')}{', '.join(item['spoiler_tags'])}")
                prompt_parts.append("")

            if player_data:
                player_pool = json.loads(player_data)
                prompt_parts.append(t_prompt("prompt.kp.doc.player_pool_label"))
                for category, items in player_pool.items():
                    if category in ("summary", "background"):
                        if items:
                            text = str(items)
                            if len(text) > 300:
                                text = text[:300] + "..."
                            prompt_parts.append(f"### {category}\n{text}")
                    elif items:
                        prompt_parts.append(f"### {category}")
                        for item in items[:20]:
                            prompt_parts.append(_summarize_knowledge_item(item))
                prompt_parts.append("")

            prompt_parts.append(t_prompt("prompt.kp.doc.catalog_hint"))
            return "\n".join(prompt_parts)

        # 知识池正在初始化中
        if status == "processing":
            return (
                "═══════════════════════════════════════\n"
                + t_prompt("prompt.kp.doc.processing_title") + "\n"
                "═══════════════════════════════════════\n"
                "\n"
                + t_prompt("prompt.kp.doc.processing_message") + "\n"
                + t_prompt("prompt.kp.doc.processing_hint") + "\n"
            )

        # 没有知识池，回退到向量检索
        queries = [
            "模组剧情 设定 背景 世界观",
            "NPC 角色 人物 关系 介绍",
            "线索 事件 任务 目标 流程",
        ]

        seen_ids = set()
        all_results = []

        for query in queries:
            results = await vector_db.search_documents(
                query=query,
                chat_key=chat_key,
                limit=5,
            )
            for r in results:
                doc_id = f"{r['filename']}:{r.get('chunk_index', 0)}"
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_results.append(r)

        if all_results:
            prompt_parts = [
                "═══════════════════════════════════════",
                t_prompt("prompt.kp.doc.vector_title"),
                "═══════════════════════════════════════",
                "",
                t_prompt("prompt.kp.doc.vector_warning_1"),
                t_prompt("prompt.kp.doc.vector_warning_2"),
                t_prompt("prompt.kp.doc.vector_warning_3"),
                t_prompt("prompt.kp.doc.vector_warning_4"),
                "",
                t_prompt("prompt.kp.doc.vector_info_header"),
            ]

            for i, result in enumerate(all_results[:10], 1):
                doc_emoji = {
                    "module": "📘", "rule": "📜",
                    "story": "📖", "background": "🌍"
                }.get(result["document_type"], "📄")

                prompt_parts.append(f"## {doc_emoji} {result['filename']} ({t_prompt('prompt.kp.doc.chunk_label')}{i})")
                text = result["text"]
                if len(text) > 1500:
                    text = text[:1500] + "..."
                prompt_parts.append(text)
                prompt_parts.append("")

            prompt_parts.append("")
            prompt_parts.append("═══════════════════════════════════════")
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_title"))
            prompt_parts.append("═══════════════════════════════════════")
            prompt_parts.append("")
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_intro"))
            prompt_parts.append("")
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_describable"))
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_describable_example"))
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_describable_action"))
            prompt_parts.append("")
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_undescribable"))
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_undescribable_example"))
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_undescribable_action"))
            prompt_parts.append("")
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_rules"))
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_rules_action"))
            prompt_parts.append("")
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_prohibition_title"))
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_prohibition_1"))
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_prohibition_2"))
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_prohibition_3"))
            prompt_parts.append(t_prompt("prompt.kp.doc.digest_prohibition_4"))
            prompt_parts.append("")
            prompt_parts.append(t_prompt("prompt.kp.doc.vector_hint"))

            return "\n".join(prompt_parts)

    except Exception:
        pass

    return ""


async def inject_session_history_prompt(_ctx, battle_report_manager) -> str:
    """
    历史战报记忆注入
    注入上次跑团的战报摘要，作为游戏历史记忆
    """
    
    try:
        # 获取上次跑团的简要总结
        summary = await battle_report_manager.get_last_session_summary(_ctx.chat_key)
        
        if summary:
            return summary
        else:
            # 如果没有历史记录，返回空
            return ""
    except Exception:
        return ""


async def inject_interaction_style_prompt(_ctx) -> str:
    """
    TRPG交互风格提示词注入
    定义KP/DM的专业表达方式和交互模式
    """

    return t_prompt("prompt.kp.interaction_style")


def register_prompt_injections(plugin, character_manager, vector_db, store, config, battle_report_manager):
    """注册所有提示词注入方法

    注意: NekroPlugin 每个插件只能有一个 prompt_inject_method，
    多个 mount_prompt_inject_method 会相互覆盖。因此将所有注入内容合并为一个。
    """

    @plugin.mount_prompt_inject_method(
        name="trpg_unified_prompt_inject",
        description="TRPG 统一提示注入：系统功能、游戏状态、专业知识、文档上下文、交互风格、历史记忆"
    )
    async def _inject_trpg_unified_prompt(_ctx) -> str:
        parts = []

        # 1. 上次跑团历史记忆（最高优先级，承接剧情）
        try:
            await battle_report_manager.ensure_session_started(_ctx.chat_key)
            history = await inject_session_history_prompt(_ctx, battle_report_manager)
            if history:
                parts.append(history)
        except Exception:
            pass

        # 2. 当前游戏状态（角色卡、时间、状态、KP笔记）
        try:
            game_state = await inject_game_state_prompt(_ctx, character_manager, store)
            if game_state:
                parts.append(game_state)
        except Exception:
            pass

        # 3. 模组文档上下文（知识池/向量检索）
        try:
            doc_context = await inject_document_context_prompt(_ctx, vector_db, store, config.ENABLE_VECTOR_DB)
            if doc_context:
                parts.append(doc_context)
        except Exception:
            pass

        # 4. 游戏系统专业知识
        try:
            expertise = await inject_system_expertise_prompt(_ctx, character_manager)
            if expertise:
                parts.append(expertise)
        except Exception:
            pass

        # 5. TRPG 系统基础功能和工具意识
        try:
            system_prompt = await inject_trpg_system_prompt(_ctx)
            if system_prompt:
                parts.append(system_prompt)
        except Exception:
            pass

        # 6. 交互风格指导
        try:
            style = await inject_interaction_style_prompt(_ctx)
            if style:
                parts.append(style)
        except Exception:
            pass

        return "\n\n".join(parts)
