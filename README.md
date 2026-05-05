# TRPG Dice Plugin for Nekro Agent

完整的TRPG骰子系统插件，支持多种TRPG规则和复杂表达式，为跑团提供全面的工具支持。集成AI智能主持人功能，可自动担任KP/DM角色，提供角色扮演、剧情推进、规则判定等专业主持服务。

## 🎯 主要功能

### 🎲 骰子系统

- **标准骰子支持**: d4, d6, d8, d10, d12, d20, d100等
- **复杂表达式**: 3d6+2, (2d6+6)x5等复合表达式
- **优势劣势**: D&D 5E风格的优势/劣势机制
- **多系统支持**: COC7、DND5E、WOD等主流TRPG系统

### 📋 角色卡管理

- **多系统模板**: 官方COC7、DND5E模板
- **自动生成**: 一键生成符合规则的角色属性
- **技能别名**: 支持中英文技能名互通
- **数据持久化**: 基于Nekro Agent官方存储API

### 📊 战报系统

- **自动记录**: 自动记录所有投骰、检定和行动
- **智能启动**: 第一次游戏操作时自动开始记录，无需手动命令
- **历史记忆**: 自动加载上次跑团战报，通过提示词注入给AI，实现剧情连续性
- **玩家评分**: 每位PC自动计算5星级评分
- **统计报表**: 详细的游戏统计数据
- **Markdown文档**: 自动生成格式化战报文档

### 📚 智能文档系统

- **多格式支持**: TXT、PDF、DOCX文档解析
- **向量化存储**: 基于语义的智能搜索
- **文档问答**: AI驱动的内容问答系统
- **分类管理**: 模组、规则、故事、背景分类

### ⚡ 插件激活调度

- **智能休眠**: 插件支持 NekroAgent 激活调度机制，非跑团场景下自动休眠，减少上下文占用
- **AI自主唤醒**: 当对话涉及跑团、掷骰、检定等内容时，AI 自动激活插件获取完整能力
- **常驻与休眠**: 跑团相关提示词注入仅在激活状态下生效，保障上下文效率

### 🤖 AI游戏主持 - 您的智能KP/DM

**让AI成为您最专业的游戏主持人！**

- **🎭 智能剧情主持**: AI自动担任KP/DM角色，推进剧情发展，创造引人入胜的故事体验
- **👥 角色扮演**: AI扮演NPC角色，提供生动的角色互动体验，每个NPC都有独特的个性和对话风格
- **🌟 环境描述**: 自动生成详细的场景描述和氛围营造，让玩家身临其境
- **⚖️ 规则仲裁**: 根据TRPG规则系统进行智能判定和解释，确保游戏公平性
- **✍️ 故事创作**: 协助创作和扩展TRPG故事情节，提供创意灵感和剧情建议
- **🎪 即兴应变**: 根据玩家行动动态调整剧情走向，灵活应对各种意外情况
- **🎲 多系统支持**: 支持COC、DND5E等主流TRPG系统的专业主持，熟悉各系统规则
- **🎨 沉浸式体验**: 营造专业、引人入胜的跑团氛围，提升整体游戏体验

#### 🧠 智能提示词注入系统

**插件通过智能提示词注入技术，让AI自动获得专业的TRPG主持能力：**

- **📋 角色状态感知**: 自动读取玩家角色卡信息，AI能准确了解每个角色的属性、技能和状态
- **📚 文档知识库**: 自动注入已上传的模组文档、规则书、背景设定，AI具备丰富的世界观知识
- **🎯 技能检定智能**: 基于角色技能值和系统规则，AI能自动进行合理的检定判断
- **🌍 场景上下文**: 根据当前游戏状态、位置、时间等信息，AI提供符合情境的描述和反应
- **🎪 动态人设**: 根据模组内容和角色互动历史，AI能保持一致的NPC人设和剧情连贯性
- **⚙️ 系统规则**: 自动注入对应TRPG系统的核心规则，确保AI按正确规则进行游戏主持
- **🔄 实时更新**: 角色状态变化、新文档上传等都会实时更新AI的知识库
- **📜 历史记忆**: 自动加载上次跑团的战报记录，让AI能够连贯地继续剧情

**提示词注入的工作原理：**

1. **角色信息注入**: 每次对话时自动包含玩家角色的当前状态
2. **文档检索注入**: 根据对话内容智能检索相关文档片段
3. **规则系统注入**: 根据当前使用的TRPG系统注入对应规则
4. **历史上下文**: 保持游戏会话的连续性和一致性
5. **战报记忆**: 自动加载上次跑团的简要总结，让AI了解剧情进展

**配置示例：**

```python
# 启用/禁用不同类型的提示词注入
ENABLE_CHARACTER_INJECTION = True   # 角色信息注入
ENABLE_DOCUMENT_INJECTION = True    # 文档知识注入  
ENABLE_SYSTEM_RULES_INJECTION = True # 系统规则注入
ENABLE_CONTEXT_INJECTION = True     # 上下文注入
```

**使用示例：**

```
me 我仔细观察房间里的每个角落      # AI会详细描述房间环境
me 我尝试说服守门的卫兵           # AI会扮演卫兵进行对话和判定
me 我使用侦察技能寻找线索         # AI会根据COC规则进行检定并描述结果
kp 接下来会发生什么？             # AI会推进剧情发展
```

## 🚀 快速开始

### 安装要求

基础功能：

- Python 3.8+
- Nekro Agent
- nonebot2

可选依赖（完整功能）：

```bash
pip install PyPDF2        # PDF文档支持
pip install python-docx   # Word文档支持
```

### 嵌入模型配置（文档检索功能必需）

本插件的文档上传/检索功能依赖 Nekro Agent 的 `text-embedding` 模型组配置。请确保：

| 要求 | 说明 |
|---|---|
| **模型支持维度** | ≥1536 维（推荐），或 ≥1024 维（最低） |
| **最大输入长度** | ≥8192 Token（推荐），≥4000 Token（最低） |
| **支持的模型示例** | 阿里 `text-embedding-v4` / `text-embedding-v3`、OpenAI `text-embedding-3-small` / `text-embedding-3-large` |

**⚠️ 已知不兼容的模型**：
- `text-embedding-v1` / `text-embedding-v2`（最大仅 2048 Token，无法处理 4000 字符分块）
- 纯聊天模型（如 GPT-4、Qwen-Max 等，不具备向量嵌入能力）

**配置位置**：Nekro Agent WebUI → 系统设置 → 模型组配置 → `text-embedding` 模型组 → 确保模型名称和 Base URL 指向正确的嵌入模型服务。

### 模组初始化模型配置（全文分析必需）

本插件上传模组后会自动调用 LLM 对模组**全文**进行结构化分析（提取场景、NPC、线索、时间线等）。**强烈推荐使用 DeepSeek V4**：

| 要求 | 说明 |
|---|---|
| **上下文窗口** | ≥1M Token（推荐 DeepSeek V4），≥128K Token（最低，仅支持小型模组） |
| **输出长度** | ≥32K Token（推荐 DeepSeek V4），≥8K Token（最低） |
| **推荐模型** | **DeepSeek V4 Pro / V4 Flash**（1M 上下文，384K 最大输出，性价比极高） |

**DeepSeek V4 配置示例**：
- 模型组名称：`deepseek-v4`
- Chat 模型：`deepseek-v4-pro` 或 `deepseek-v4-flash`
- Base URL：`https://api.deepseek.com`
- API Key：你的 DeepSeek API Key

**⚠️ 不兼容的模型**：
- 仅支持 4K/8K/32K 上下文的旧模型（无法塞下完整模组文本）
- 输出长度限制低于 8K 的模型（结构化模组数据通常需要 16K-32K 输出）

**配置位置**：
1. Nekro Agent WebUI → 系统设置 → 模型组配置 → 创建 `deepseek-v4` 模型组
2. 插件配置 → `MODULE_INIT_MODEL_GROUP` → 选择 `deepseek-v4`
3. 插件配置 → `MODULE_INIT_MAX_INPUT_TOKENS` → 默认 80 万字符（适配 1M 上下文）
4. 插件配置 → `MODULE_INIT_MAX_OUTPUT_TOKENS` → 默认 32K（充分利用 DeepSeek V4 的 384K 输出能力）

### 模组知识池系统（全文分析）

上传 module/story 类型文档后，插件会自动调用 LLM 对模组**全文**进行结构化分析，提取场景、NPC、线索、威胁、时间线、幕后真相等。分片(chunk)仅用于向量检索，初始化时合并全文分析。

**AI KP 查询工具**：

| 工具 | 用途 |
|------|------|
| `get_module_summary()` | 开局前获取全局概要：summary/background/truths/timeline/威胁清单/场景清单/NPC清单 |
| `list_module_elements("scenes")` | 列出模组元素名称清单：scenes/npcs/clues/threats/timeline |
| `get_module_element_detail("scenes", "场景名")` | 获取单个场景/NPC/线索/威胁的完整详情（不截断） |
| `query_knowledge_pool("关键词", "keeper")` | 关键词搜索模组知识池 |

**AI KP 工作流**：
1. 开局前 `get_module_summary()` 建立全局认知
2. `list_module_elements("scenes")` 查看场景/NPC/威胁清单
3. 玩家行动到哪，`get_module_element_detail` 查对应详情
4. 发现线索后 `unlock_for_player("clues", "线索名")` 记录到玩家知识池
5. 遇战斗先查 `threats` 的 stats/san_loss/attacks，确认数值后再要求掷骰

**AI KP 自由笔记**（记录即兴创作和世界状态变更）：

| 工具 | 用途 |
|------|------|
| `kp_note("add", "world_changes", "描述")` | 记录世界变更（门被炸开、NPC死亡等） |
| `kp_note("add", "npc_status", "描述")` | 记录NPC状态更新 |
| `kp_note("add", "improvised_scenes", "描述")` | 记录即兴创作的新场景 |
| `kp_note("list", "world_changes", "")` | 查看某分类的全部笔记 |

**AI KP 时间管理**：

| 工具 | 用途 |
|------|------|
| `game_clock("show")` | 查看当前游戏时间和日程 |
| `game_clock("set", "1926年3月15日 14:00")` | 设定游戏时间 |
| `game_clock("advance", "+2小时")` | 推进游戏时间 |
| `game_clock("add_event", "调查员抵达精神病院")` | 添加日程事件 |

**角色状态跟踪**：

| 工具 | 用途 |
|------|------|
| `update_character_status('["中毒(每回合1HP)", "恐惧(SAN-10)"]')` | 更新角色状态效果，每次对话自动注入AI上下文 |

### 基础使用

#### 掷骰子

```
r 3d6+2          # 基础掷骰
ra 侦察          # 技能检定
adv d20          # 优势掷骰
me 仔细观察房间   # 角色动作
```

#### 角色卡管理

```
st               # 显示角色卡
st new 我的调查员 # 创建新角色
st temp coc7     # 切换COC7模板
st init          # 自动生成属性
```

#### 文档管理

```
doc_text module 深海古城 [模组内容...]  # 上传文档
doc search 深海古城的NPC              # 搜索内容
ask 这个模组的主要剧情是什么           # 智能问答
```

#### 战报系统

```
# 自动模式 - 直接开始游戏！
r 3d6+2                       # 第一次投骰自动开始记录
ra 侦察                       # 自动记录
me 仔细观察房间              # 自动记录

# 手动模式 - 可选，如需自定义会话名称
session start 深海古城探险      # 手动指定名称开始
session event 发现神秘地下入口  # 记录关键事件
session end                      # 生成战报
```

## 📖 详细文档

- [用户手册](trpg_dice/docs/trpg_dice_help.md) - 完整功能说明
- [提示词系统](trpg_dice/docs/trpg_prompt_examples.md) - AI行为配置
- [开发文档](trpg_dice/docs/development.md) - 二次开发指南

## 🎮 支持的TRPG系统

### 克苏鲁的呼唤 (COC7)

- 完整的技能检定系统
- 理智值管理
- 官方角色生成规则
- 中英文技能别名支持

### 龙与地下城 5E (DND5E)

- 优势劣势机制
- 六大属性系统
- 战斗先攻管理
- 标准角色生成

### 黑暗世界 (WOD)

- 骰池检定系统
- 专精规则支持
- 大失败判定

### 其他系统

- 通用骰子系统
- 可扩展架构
- 自定义模板支持

## 🛠️ 配置选项

```python
# 骰子系统
MAX_DICE_COUNT = 100        # 最大骰子数量
MAX_DICE_SIDES = 1000       # 最大骰子面数

# 文档与向量检索
ENABLE_VECTOR_DB = True     # 启用文档功能
CHUNK_SIZE = 4000           # 文档分块大小（字符）
CHUNK_OVERLAP = 800         # 分块重叠大小
MAX_SEARCH_RESULTS = 15     # 向量检索最大结果数

# 模组全文分析（需要 1M 上下文模型）
MODULE_INIT_MODEL_GROUP = "default"        # 分析模组的 LLM 模型组（推荐 deepseek-v4）
MODULE_INIT_MAX_INPUT_TOKENS = 800000      # 最大输入字符数（适配 1M 上下文）
MODULE_INIT_MAX_OUTPUT_TOKENS = 32768      # 最大输出 token（结构化数据需要 4K-32K）
MODULE_INIT_AUTO_START = True              # 上传模组后自动初始化

# 插件激活调度（由系统管理）
allow_sleep = True          # 允许插件休眠
sleep_brief = "TRPG跑团系统，涉及掷骰/检定/角色卡时激活"
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境设置

```bash
git clone <repo-url>
cd nekro-trpg-plugin
pip install -r requirements.txt
```

### 代码结构

```
trpg_dice/
├── __init__.py              # 插件入口
├── plugin.py                # 主插件文件（36个沙盒方法）
├── core/                    # 核心模块
│   ├── dice_engine.py       # 骰子引擎
│   ├── character_manager.py # 角色管理
│   ├── document_manager.py  # 文档管理（向量存储）
│   ├── module_initializer.py # 模组全文分析引擎
│   ├── battle_report.py     # 战报系统
│   └── prompt_injection.py  # 提示词注入（自动注入角色状态/游戏时间/世界变更）
├── templates/               # 角色模板
├── docs/                    # 文档
└── examples/                # 示例
```

## 📄 许可证

MIT License

## 🙏 致谢

- [OlivOS-Team/OlivOS](https://github.com/OlivOS-Team/OlivOS) - 参考的骰子系统
- [OlivaDice](https://wiki.dice.center/User/Manual) - 功能设计参考
- Nekro Agent Team - 提供优秀的插件框架

## 📞 支持

- [Issues](../../issues) - 报告问题
- [Discussions](../../discussions) - 讨论交流
- [Wiki](../../wiki) - 详细文档

---

**Enjoy your TRPG adventures! 🎲✨**
