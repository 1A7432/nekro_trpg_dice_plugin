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

### 📚 智能文档系统

- **多格式支持**: TXT、PDF、DOCX文档解析
- **向量化存储**: 基于语义的智能搜索
- **文档问答**: AI驱动的内容问答系统
- **分类管理**: 模组、规则、故事、背景分类

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
# 在插件配置中调整
MAX_DICE_COUNT = 100        # 最大骰子数量
MAX_DICE_SIDES = 1000       # 最大骰子面数
ENABLE_VECTOR_DB = True     # 启用文档功能
CHUNK_SIZE = 1000          # 文档分块大小
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
├── __init__.py           # 插件入口
├── plugin.py             # 主插件文件
├── core/                 # 核心模块
│   ├── dice_engine.py    # 骰子引擎
│   ├── character_manager.py  # 角色管理
│   ├── document_manager.py   # 文档管理
│   └── prompt_injection.py   # 提示词注入
├── templates/            # 角色模板
├── docs/                 # 文档
└── examples/             # 示例
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
