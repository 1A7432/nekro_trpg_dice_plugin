"""
模组初始化引擎

后台调用 LLM 分析每个 chunk，生成结构化 Catalog 和知识池。
不受 AI 沙盒迭代限制，上传模组后自动完成。
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from nekro_agent.api.core import config as core_config
from nekro_agent.services.agent.openai import gen_openai_chat_response, OpenAIResponse
from nekro_agent.api import core


class ModuleInitializer:
    """模组初始化器 - 后台 LLM 驱动分析"""

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
        """执行初始化核心逻辑"""
        chunks = await self.vector_db.list_all_chunks(chat_key, limit=1000)
        if not chunks:
            self.logger.info(f"[ModuleInit] {chat_key} 没有文档需要初始化")
            return

        self.logger.info(f"[ModuleInit] {chat_key} 开始分析 {len(chunks)} 个 chunk")

        # 并发分析，控制并发数
        semaphore = asyncio.Semaphore(self.config.MODULE_INIT_MAX_CONCURRENT)

        async def analyze_with_limit(chunk):
            async with semaphore:
                return await self._analyze_chunk(chunk)

        results = await asyncio.gather(*[analyze_with_limit(c) for c in chunks])

        # 构建 Catalog
        catalog = []
        for chunk, analysis in zip(chunks, results):
            catalog.append({
                "chunk_id": str(chunk.get("id", "")),
                "doc_name": chunk.get("filename", "未知文档"),
                "chunk_index": chunk.get("chunk_index", 0),
                "type": analysis.get("type", "unknown"),
                "risk_level": analysis.get("risk_level", "unknown"),
                "summary": analysis.get("summary", ""),
                "keywords": analysis.get("keywords", []),
                "spoiler_tags": analysis.get("spoiler_tags", []),
                "requires": analysis.get("requires", []),
                "unlocks": analysis.get("unlocks", []),
                "preview": chunk.get("text", "")[:200],
                "status": "processed",
            })

        # 生成知识池
        keeper_pool, player_pool = self._build_knowledge_pools(catalog)

        # 持久化存储
        await self.store.set(
            user_key="",
            store_key=f"module_catalog.{chat_key}",
            value=json.dumps(catalog, ensure_ascii=False),
        )
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

        self.logger.info(
            f"[ModuleInit] {chat_key} 完成: {len(catalog)} chunks, "
            f"keeper={len(keeper_pool.get('scenes', [])) + len(keeper_pool.get('npcs', []))} items, "
            f"player={len(player_pool.get('scenes', [])) + len(player_pool.get('npcs', []))} items"
        )

    async def _analyze_chunk(self, chunk: Dict) -> Dict:
        """调用 LLM 分析单个 chunk，失败时回退到启发式分析"""
        text = chunk.get("text", "")

        # 截断到配置的最大字符数（粗略按 1 token ≈ 1.5 中文字符估算）
        max_chars = int(self.config.MODULE_INIT_MAX_CHUNK_TOKENS * 1.5)
        truncated_text = text[:max_chars]

        prompt = f"""分析以下TRPG模组文本片段，输出 JSON：

要求：
- type: 类型（scene/npc/clue/rule/background/other）。场景描述→scene，人物介绍→npc，线索信息→clue，规则条文→rule，世界观/历史→background，其他→other
- title: 提取该片段的核心主题名称。场景→场景名（如"废弃医院大厅"）；NPC→人物名（如"凯尔·莫里斯"）；线索→线索标题（如"涂鸦墙上的信息"）；其他→用摘要前10字
- risk_level: 敏感度（keeper_only/player_visible/mixed）。包含守秘人提示/幕后真相/NPC秘密/怪物数据/未来线索→keeper_only；纯场景外观/玩家可直接感知的→player_visible；混合→mixed
- summary: 100字以内的内容摘要，只概括核心内容，不含剧透
- keywords: 关键词列表（3-8个，必须包含场景名/NPC名/关键物品名等可检索词）
- spoiler_tags: 剧透标签列表（该片段中包含的不可透露给玩家的信息标签）
- requires: 触发该片段内容的前置条件列表（如果有）
- unlocks: 该片段可能解锁的后续内容列表（如果有）

文本：
{truncated_text}

只输出 JSON，不要其他内容。"""

        try:
            model_group = core_config.get_model_group_info(self.config.MODULE_INIT_MODEL_GROUP)
            if not model_group:
                self.logger.warning(
                    f"[ModuleInit] 找不到模型组 {self.config.MODULE_INIT_MODEL_GROUP}，使用回退分析"
                )
                return self._fallback_analysis(text)

            response: OpenAIResponse = await gen_openai_chat_response(
                model=model_group.CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                api_key=model_group.API_KEY,
                base_url=model_group.BASE_URL,
                max_tokens=800,
                temperature=0.3,
            )

            content = response.response_content.strip()
            # 去掉可能的 markdown 代码块标记
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

            result = json.loads(content)

            # 确保必要字段存在
            for field in ["type", "risk_level", "summary", "keywords", "spoiler_tags", "requires", "unlocks"]:
                if field not in result:
                    result[field] = [] if field in ["keywords", "spoiler_tags", "requires", "unlocks"] else "unknown"

            return result

        except Exception as e:
            self.logger.warning(f"[ModuleInit] LLM 分析失败: {e}，使用回退分析")
            return self._fallback_analysis(text)

    def _fallback_analysis(self, text: str) -> Dict:
        """LLM 调用失败时的启发式回退分析"""
        risk = "mixed"
        if any(k in text for k in ["守秘人", "KP", "幕后", "真相是", "秘密", "剧透", "不可描述"]):
            risk = "keeper_only"
        elif any(k in text for k in ["场景", "房间", "地点", "外观", "描述", "看到", "听到", "闻到"]):
            risk = "player_visible"

        type_guess = "other"
        text_lower = text.lower()
        # 优先判断 NPC（人名通常在文本中明确出现）
        if any(k in text for k in ["NPC", "人物介绍", "角色卡", "调查员", "守秘人信息"]):
            type_guess = "npc"
        elif any(k in text for k in ["线索", "发现", "证据", "物品", "文件", "日记", "笔记", "密码"]):
            type_guess = "clue"
        elif any(k in text for k in ["场景", "房间", "地点", "区域", "地图", "建筑", "内部", "外部"]):
            type_guess = "scene"
        elif any(k in text for k in ["规则", "检定", "技能", "属性", "成功", "失败", "掷骰", "惩罚骰", "奖励骰"]):
            type_guess = "rule"
        elif any(k in text for k in ["背景", "世界观", "历史", "设定", "年代", "时代"]):
            type_guess = "background"

        summary = text[:100] + "..." if len(text) > 100 else text
        summary = summary.replace("\n", " ")

        # 尝试从文本中提取标题：第一个句号前的内容，或前15字
        title = summary[:20] + "..." if len(summary) > 20 else summary

        return {
            "type": type_guess,
            "title": title,
            "risk_level": risk,
            "summary": summary,
            "keywords": [],
            "spoiler_tags": [],
            "requires": [],
            "unlocks": [],
        }

    def _build_knowledge_pools(self, catalog: List[Dict]) -> tuple:
        """基于 Catalog 构建守秘人知识池和玩家知识池"""
        keeper_pool: Dict[str, List] = {
            "scenes": [],
            "npcs": [],
            "clues": [],
            "truths": [],
            "future_events": [],
            "monster_stats": [],
        }
        player_pool: Dict[str, List] = {
            "scenes": [],
            "npcs": [],
            "world_info": [],
            "known_clues": [],
        }

        for entry in catalog:
            # title 优先用 LLM 提取的，否则从 summary 取前15字，绝不用文件名
            title = entry.get("title", "")
            if not title or title == entry.get("doc_name", ""):
                summary = entry.get("summary", "")
                title = summary[:18] + "..." if len(summary) > 18 else summary
            if not title:
                title = f"片段#{entry.get('chunk_index', 0)}"

            item = {
                "id": entry["chunk_id"],
                "title": title,
                "summary": entry["summary"],
                "keywords": entry["keywords"],
            }

            if entry["type"] == "scene":
                if entry["risk_level"] == "keeper_only":
                    keeper_pool["scenes"].append({**item, "spoiler_tags": entry.get("spoiler_tags", [])})
                else:
                    player_pool["scenes"].append(item)
            elif entry["type"] == "npc":
                if entry["risk_level"] == "keeper_only":
                    keeper_pool["npcs"].append({**item, "spoiler_tags": entry.get("spoiler_tags", [])})
                else:
                    player_pool["npcs"].append(item)
            elif entry["type"] == "clue":
                if entry["risk_level"] == "keeper_only":
                    keeper_pool["clues"].append({**item, "spoiler_tags": entry.get("spoiler_tags", [])})
                else:
                    player_pool["known_clues"].append(item)
            elif entry["type"] == "rule":
                player_pool["world_info"].append(item)
            elif entry["type"] == "background":
                player_pool["world_info"].append(item)
            else:
                # other / unknown 类型：基于 risk_level 和 keywords 二次分配
                if entry.get("risk_level") == "keeper_only":
                    keeper_pool["scenes"].append({**item, "spoiler_tags": entry.get("spoiler_tags", [])})
                else:
                    player_pool["world_info"].append(item)

            # 有 spoiler_tags 的归入守秘人真相池
            if entry.get("spoiler_tags"):
                keeper_pool["truths"].append({
                    "id": entry["chunk_id"],
                    "title": title,
                    "tags": entry["spoiler_tags"],
                    "summary": entry["summary"],
                })

        return keeper_pool, player_pool
