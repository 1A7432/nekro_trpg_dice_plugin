"""
模组初始化引擎 v2

全文分析模式：将模组完整文本一次性交给 LLM，输出结构化数据。
要求 LLM 支持 1M 上下文（≈ 50-80 万中文字符），一般 COC 模组 2-10 万字完全可塞下。
分片(chunk)仅保留用于向量检索，初始化时合并全文分析。
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from nekro_agent.api.core import config as core_config
from nekro_agent.services.agent.openai import gen_openai_chat_response, OpenAIResponse
from nekro_agent.api import core

from ..i18n import t_prompt


class ModuleInitializer:
    """模组初始化器 - 后台 LLM 全文驱动分析"""

    def __init__(self, store, vector_db, plugin_config):
        self.store = store
        self.vector_db = vector_db
        self.config = plugin_config
        self.logger = core.logger

    async def initialize(self, chat_key: str):
        """启动模组初始化（如果已在处理中则跳过）"""
        status_key = f"module_init_status.{chat_key}"

        current_status = await self.store.get(user_key="", store_key=status_key)
        if current_status == "processing":
            self.logger.info(f"[ModuleInit] {chat_key} 已有初始化任务在进行中，跳过")
            return

        await self.store.set(user_key="", store_key=status_key, value="processing")

        try:
            await self._do_initialize(chat_key)
            await self.store.set(user_key="", store_key=status_key, value="ready")
            self.logger.info(f"[ModuleInit] {chat_key} 模组初始化完成")
        except Exception as e:
            self.logger.error(f"[ModuleInit] {chat_key} 初始化失败: {e}")
            await self.store.set(user_key="", store_key=status_key, value=f"failed:{str(e)}")

    async def _do_initialize(self, chat_key: str):
        """执行初始化核心逻辑 - 全文分析模式"""
        chunks = await self.vector_db.list_all_chunks(chat_key, limit=1000)
        if not chunks:
            self.logger.info(f"[ModuleInit] {chat_key} 没有文档需要初始化")
            return

        # 按文档和 chunk_index 排序，确保文本顺序正确
        chunks.sort(key=lambda c: (c.get("filename", ""), c.get("chunk_index", 0)))
        full_text = "\n\n".join(c["text"] for c in chunks)
        doc_name = chunks[0].get("filename", "未知模组")

        self.logger.info(
            f"[ModuleInit] {chat_key} 开始全文分析: 文档={doc_name}, "
            f"chunks={len(chunks)}, 总字数={len(full_text)}"
        )

        # 调用 LLM 进行全文结构化分析
        analysis = await self._analyze_full_text(full_text, doc_name)

        # 存储完整 catalog（结构化数据）
        await self.store.set(
            user_key="",
            store_key=f"module_catalog.{chat_key}",
            value=json.dumps(analysis, ensure_ascii=False),
        )

        # 构建知识池
        keeper_pool, player_pool = self._build_knowledge_pools(analysis)

        await self.store.set(
            user_key="",
            store_key=f"module_keeper_pool.{chat_key}",
            value=json.dumps(keeper_pool, ensure_ascii=False),
        )
        await self.store.set(
            user_key="",
            store_key=f"module_player_pool.{chat_key}",
            value=json.dumps(player_pool, ensure_ascii=False),
        )

        # 将开局已知事实写入 confirmed_facts
        opening_facts = analysis.get("opening_facts", [])
        if opening_facts:
            try:
                notes_key = f"kp_notes.{chat_key}"
                notes_data = await self.store.get(user_key="", store_key=notes_key)
                notes = json.loads(notes_data) if notes_data else {}
                notes.setdefault("confirmed_facts", [])
                for fact in opening_facts:
                    notes["confirmed_facts"].append({"time": "开局", "content": fact})
                await self.store.set(user_key="", store_key=notes_key, value=json.dumps(notes, ensure_ascii=False))
            except Exception:
                pass

        self.logger.info(
            f"[ModuleInit] {chat_key} 完成: scenes={len(analysis.get('scenes', []))}, "
            f"npcs={len(analysis.get('npcs', []))}, clues={len(analysis.get('clues', []))}, "
            f"truths={len(analysis.get('truths', []))}"
        )

    async def _analyze_full_text(self, full_text: str, doc_name: str) -> Dict:
        """调用 LLM 对模组全文进行结构化分析"""
        # 粗略按 1 token ≈ 1 中文字符估算，保留部分余量给 prompt 自身
        max_chars = getattr(self.config, "MODULE_INIT_MAX_INPUT_TOKENS", 500000)
        truncated_text = full_text[:max_chars]

        if len(truncated_text) < len(full_text):
            self.logger.warning(
                f"[ModuleInit] 文本过长已截断: {len(full_text)} -> {len(truncated_text)} 字符"
            )

        prompt = t_prompt("prompt.module.analysis").format(
            doc_name=doc_name,
            truncated_text=truncated_text,
        )

        try:
            model_group = core_config.get_model_group_info(self.config.MODULE_INIT_MODEL_GROUP)
            if not model_group:
                self.logger.warning(f"[ModuleInit] 找不到模型组，使用回退分析")
                return self._fallback_full_analysis(full_text)

            max_output = getattr(self.config, "MODULE_INIT_MAX_OUTPUT_TOKENS", 8192)
            response: OpenAIResponse = await gen_openai_chat_response(
                model=model_group.CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                api_key=model_group.API_KEY,
                base_url=model_group.BASE_URL,
                max_tokens=max_output,
                temperature=0.3,
            )

            content = response.response_content.strip()
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

            result = json.loads(content)

            # 确保必要字段存在
            for field in ["scenes", "npcs", "clues", "timeline", "background", "threats", "truths", "opening_facts", "summary"]:
                if field not in result:
                    result[field] = [] if field in ["scenes", "npcs", "clues", "timeline", "threats", "truths", "opening_facts"] else ""

            return result

        except Exception as e:
            self.logger.warning(f"[ModuleInit] LLM 全文分析失败: {e}，使用回退分析")
            return self._fallback_full_analysis(full_text)

    def _fallback_full_analysis(self, text: str) -> Dict:
        """LLM 调用失败时的全文回退分析"""
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
        scenes = []
        for i, para in enumerate(paragraphs[:20]):
            scenes.append({
                "name": f"场景{i+1}",
                "focus": "探索",
                "description": para[:200],
                "keeper_notes": "",
                "npcs_present": [],
                "clues": [],
            })

        return {
            "scenes": scenes,
            "npcs": [],
            "clues": [],
            "timeline": [],
            "background": text[:500] if len(text) > 500 else text,
            "threats": [],
            "truths": [],
            "summary": text[:100] if len(text) > 100 else text,
        }

    def _build_knowledge_pools(self, analysis: Dict) -> tuple:
        """基于结构化分析结果构建守秘人知识池和玩家知识池"""
        keeper_pool = {
            "scenes": [],
            "npcs": [],
            "clues": [],
            "truths": [],
            "timeline": [],
            "background": analysis.get("background", ""),
            "summary": analysis.get("summary", ""),
        }
        player_pool = {
            "scenes": [],
            "npcs": [],
            "clues": [],
            "background": analysis.get("background", ""),
            "summary": analysis.get("summary", ""),
        }

        # scenes: keeper 含 keeper_notes，player 只含 description
        for scene in analysis.get("scenes", []):
            keeper_pool["scenes"].append(scene)
            player_pool["scenes"].append({
                "name": scene.get("name", ""),
                "focus": scene.get("focus", "探索"),
                "description": scene.get("description", ""),
                "npcs_present": scene.get("npcs_present", []),
                "clues": [
                    {"name": c.get("name", ""), "description": c.get("description", ""), "discovery_method": c.get("discovery_method", "")}
                    for c in scene.get("clues", [])
                ],
            })

        # npcs: keeper 含 secret，player 只含 description
        for npc in analysis.get("npcs", []):
            keeper_pool["npcs"].append(npc)
            player_pool["npcs"].append({
                "name": npc.get("name", ""),
                "description": npc.get("description", ""),
                "role": npc.get("role", ""),
            })

        # clues: keeper 含全部，player 初始为空（跑团中逐步解锁）
        keeper_pool["clues"] = analysis.get("clues", [])

        # threats: 只给 keeper（战斗数据不可告知玩家）
        keeper_pool["threats"] = analysis.get("threats", [])

        # timeline, truths: 只给 keeper
        keeper_pool["timeline"] = analysis.get("timeline", [])
        keeper_pool["truths"] = analysis.get("truths", [])

        return keeper_pool, player_pool
