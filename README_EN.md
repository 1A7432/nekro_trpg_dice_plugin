# TRPG Dice Plugin for Nekro Agent

A complete TRPG dice system plugin supporting multiple TRPG rulesets and complex expressions, providing comprehensive tooling for tabletop RPG sessions. Features an integrated AI game master that can automatically serve as Keeper (KP) or Dungeon Master (DM), delivering professional hosting services including roleplay, plot advancement, and rule adjudication.

## 🎯 Key Features

### 🎲 Dice System

- **Standard dice support**: d4, d6, d8, d10, d12, d20, d100, and more
- **Complex expressions**: Compound expressions like 3d6+2, (2d6+6)x5
- **Advantage/disadvantage**: D&D 5E-style advantage/disadvantage mechanics
- **Multi-system support**: Major TRPG systems including COC7, DND5E, and WOD

### 📋 Character Sheet Management

- **Multi-system templates**: Official COC7 and DND5E templates
- **Auto-generation**: One-click generation of rule-compliant character attributes
- **Skill aliases**: Bilingual (Chinese/English) skill name interop
- **Data persistence**: Built on the Nekro Agent official storage API

### 📊 Session Report System

- **Auto-recording**: Automatically logs all dice rolls, skill checks, and actions
- **Intelligent startup**: Begins recording automatically on the first in-game operation, no manual command needed
- **Session memory**: Auto-loads the previous session report and injects it into AI context for narrative continuity
- **Player ratings**: Automatically calculates a 5-star rating for each player character (PC)
- **Statistical reports**: Detailed game statistics
- **Markdown documents**: Auto-generates formatted session report documents

### 📚 Intelligent Document System

- **Multi-format support**: TXT, PDF, DOCX document parsing
- **Vectorized storage**: Semantic-based intelligent search
- **Document Q&A**: AI-driven content question-answering system
- **Category management**: Module, rules, story, and background categorization

### ⚡ Plugin Activation Scheduling

- **Smart sleep**: The plugin supports NekroAgent's activation scheduling, automatically sleeping outside of TRPG sessions to reduce context overhead
- **AI auto-wake**: When conversation involves TRPG topics, dice rolls, skill checks, etc., the AI automatically activates the plugin for its full capabilities
- **Persistent vs. dormant**: TRPG-related prompt injection only takes effect when activated, preserving context efficiency

### 🤖 AI Game Master — Your Intelligent KP/DM

**Let AI become your most professional game master!**

- **🎭 Intelligent narrative hosting**: The AI automatically serves as Keeper (KP) or Dungeon Master (DM), advancing the plot and creating a captivating story experience
- **👥 Roleplay**: The AI portrays NPCs, providing vivid character interaction; each NPC has a unique personality and dialogue style
- **🌟 Environmental descriptions**: Auto-generates detailed scene descriptions and atmosphere building, immersing players in the world
- **⚖️ Rule arbitration**: Conducts intelligent adjudication and interpretation based on TRPG rulesets, ensuring fair gameplay
- **✍️ Story creation**: Assists in crafting and expanding TRPG storylines, offering creative inspiration and plot suggestions
- **🎪 Improvisation**: Dynamically adjusts the plot direction based on player actions, flexibly handling unexpected situations
- **🎲 Multi-system support**: Professional hosting for major TRPG systems like COC and DND5E, with system-specific rules knowledge
- **🎨 Immersive experience**: Creates a professional, engaging TRPG atmosphere that elevates the overall game experience

#### 🧠 Intelligent Prompt Injection System

**The plugin uses intelligent prompt injection technology to automatically equip the AI with professional TRPG hosting capabilities:**

- **📋 Character status awareness**: Automatically reads player character sheets so the AI knows each character's attributes, skills, and current status
- **📚 Document knowledge base**: Auto-injects uploaded module documents, rulebooks, and background settings, giving the AI rich world-building knowledge
- **🎯 Skill check intelligence**: Based on character skill values and system rules, the AI can autonomously make reasonable check judgments
- **🌍 Scene context**: Uses current game state, location, time, and other information so the AI provides contextually appropriate descriptions and reactions
- **🎪 Dynamic persona**: Based on module content and character interaction history, the AI maintains consistent NPC personas and narrative coherence
- **⚙️ System rules**: Auto-injects the core rules of the active TRPG system, ensuring the AI runs the game according to correct rules
- **🔄 Real-time updates**: Character status changes, new document uploads, etc. are reflected in the AI's knowledge base in real time
- **📜 Session memory**: Auto-loads the previous session report so the AI can coherently continue the story

**How prompt injection works:**

1. **Character info injection**: Automatically includes each player character's current status in every conversation turn
2. **Document retrieval injection**: Intelligently retrieves relevant document excerpts based on conversation content
3. **Ruleset injection**: Injects the corresponding rules based on the currently active TRPG system
4. **Historical context**: Maintains session continuity and consistency
5. **Session report memory**: Auto-loads a brief summary of the previous session so the AI understands story progress

**Configuration example:**

```python
# Enable/disable different types of prompt injection
ENABLE_CHARACTER_INJECTION = True   # Character info injection
ENABLE_DOCUMENT_INJECTION = True    # Document knowledge injection  
ENABLE_SYSTEM_RULES_INJECTION = True # System rules injection
ENABLE_CONTEXT_INJECTION = True     # Context injection
```

**Usage examples:**

```
me 我仔细观察房间里的每个角落      # AI will describe the room environment in detail
me 我尝试说服守门的卫兵           # AI will roleplay the guard and make rulings
me 我使用侦察技能寻找线索         # AI will perform a COC skill check and describe the result
kp 接下来会发生什么？             # AI will advance the plot
```

## 🚀 Quick Start

### Requirements

Basic features:

- Python 3.8+
- Nekro Agent
- nonebot2

Optional dependencies (full feature set):

```bash
pip install PyPDF2        # PDF document support
pip install python-docx   # Word document support
```

### Embedding Model Configuration (Required for Document Retrieval)

The document upload/retrieval features depend on Nekro Agent's `text-embedding` model group configuration. Please ensure:

| Requirement | Details |
|---|---|
| **Supported dimensions** | ≥1536 dimensions (recommended), or ≥1024 dimensions (minimum) |
| **Max input length** | ≥8192 tokens (recommended), ≥4000 tokens (minimum) |
| **Supported model examples** | Alibaba `text-embedding-v4` / `text-embedding-v3`, OpenAI `text-embedding-3-small` / `text-embedding-3-large` |

**⚠️ Known incompatible models**:
- `text-embedding-v1` / `text-embedding-v2` (max 2048 tokens, cannot handle 4000-character chunks)
- Chat-only models (e.g., GPT-4, Qwen-Max, which lack vector embedding capability)

**Configuration path**: Nekro Agent WebUI → System Settings → Model Group Config → `text-embedding` model group → Ensure model name and Base URL point to a correct embedding model service.

### Module Initialization Model Configuration (Required for Full-Text Analysis)

After uploading a module, the plugin automatically invokes an LLM to perform **full-text** structural analysis (extracting scenes, NPCs, clues, timelines, etc.). **DeepSeek V4 is strongly recommended**:

| Requirement | Details |
|---|---|
| **Context window** | ≥1M tokens (DeepSeek V4 recommended), ≥128K tokens (minimum, small modules only) |
| **Output length** | ≥32K tokens (DeepSeek V4 recommended), ≥8K tokens (minimum) |
| **Recommended model** | **DeepSeek V4 Pro / V4 Flash** (1M context, 384K max output, excellent cost/performance) |

**DeepSeek V4 configuration example**:
- Model group name: `deepseek-v4`
- Chat model: `deepseek-v4-pro` or `deepseek-v4-flash`
- Base URL: `https://api.deepseek.com`
- API Key: Your DeepSeek API Key

**⚠️ Incompatible models**:
- Legacy models with only 4K/8K/32K context (cannot fit the full module text)
- Models with output limits below 8K (structured module data typically requires 16K-32K output)

**Configuration path**:
1. Nekro Agent WebUI → System Settings → Model Group Config → Create `deepseek-v4` model group
2. Plugin config → `MODULE_INIT_MODEL_GROUP` → Select `deepseek-v4`
3. Plugin config → `MODULE_INIT_MAX_INPUT_TOKENS` → Default 800,000 characters (fits 1M context)
4. Plugin config → `MODULE_INIT_MAX_OUTPUT_TOKENS` → Default 32K (leverages DeepSeek V4's 384K output capability)

### Module Knowledge Pool System (Full-Text Analysis)

After uploading a module/story type document, the plugin automatically invokes an LLM to perform **full-text** structural analysis, extracting scenes, NPCs, clues, threats, timelines, and behind-the-scenes truths. Chunks are used only for vector retrieval; initialization merges them for full-text analysis.

**AI Keeper query tools**:

| Tool | Purpose |
|------|---------|
| `get_module_summary()` | Get global overview before starting: summary/background/truths/timeline/threat list/scene list/NPC list |
| `list_module_elements("scenes")` | List module element names: scenes/npcs/clues/threats/timeline |
| `get_module_element_detail("scenes", "Scene Name")` | Get full details (untruncated) for a single scene/NPC/clue/threat |
| `query_knowledge_pool("keyword", "keeper")` | Keyword search within the module knowledge pool |

**AI Keeper workflow**:
1. Before starting, `get_module_summary()` to establish global awareness
2. `list_module_elements("scenes")` to review the scene/NPC/threat roster
3. Wherever players go, `get_module_element_detail` to look up the corresponding details
4. When clues are discovered, `unlock_for_player("clues", "Clue Name")` to record in the player knowledge pool
5. Before combat, first check `threats` for stats/san_loss/attacks, confirm values, then request dice rolls

**AI Keeper freeform notes** (recording improvisation and world state changes):

| Tool | Purpose |
|------|---------|
| `kp_note("add", "world_changes", "description")` | Record world changes (doors blown up, NPC deaths, etc.) |
| `kp_note("add", "npc_status", "description")` | Record NPC status updates |
| `kp_note("add", "improvised_scenes", "description")` | Record newly improvised scenes |
| `kp_note("list", "world_changes", "")` | View all notes in a category |

**AI Keeper time management**:

| Tool | Purpose |
|------|---------|
| `game_clock("show")` | View current game time and schedule |
| `game_clock("set", "1926年3月15日 14:00")` | Set game time |
| `game_clock("advance", "+2小时")` | Advance game time |
| `game_clock("add_event", "调查员抵达精神病院")` | Add a schedule event |

**Character status tracking**:

| Tool | Purpose |
|------|---------|
| `update_character_status('["中毒(每回合1HP)", "恐惧(SAN-10)"]')` | Update character status effects, auto-injected into AI context each turn |

### ⚠️ Command System and AI Context Isolation (Required Reading)

In NekroAgent's architecture, **the command system (`/` commands) and the AI conversation system are two completely isolated channels**. Understanding this is critical to the TRPG experience.

#### Why is this the case?

```
QQ Message → NekroAgent → detect_command("/ra 侦查") → Command handler executes
                                ↓                          ↓
                         Does NOT enter AI context     Output broadcast to WebUI/QQ
```

- Command output is pushed to the frontend in real time via `command_output_broadcaster`, with **no persistence**
- The AI's context only contains messages routed through `push_human_message`
- Therefore **the AI cannot see commands entered by players, nor the command output results**

#### Impact on TRPG sessions

| Method | Does AI see it? | Notes |
|--------|-----------------|-------|
| Player inputs `/ra 侦查` | ❌ Cannot see | AI does not know the player rolled dice or the result |
| AI calls `skill_check` | ✅ Can see | AI called the tool itself, naturally sees the result |
| Player says "我侦查一下" | ✅ Can see | Enters AI context as a natural language message |

#### Recommended play styles

**Style 1: AI rolls on your behalf (smoothest)**
- Player says "I want to search this room"
- AI Keeper automatically calls the `skill_check` tool to roll dice
- AI advances the plot directly based on the result
- Best for: text-based online TRPGs that prioritize a smooth, fluid experience

**Style 2: Player rolls + manually informs AI**
- Player inputs `/ra 侦查` (or `.ra 侦查`, requires changing the command prefix)
- After seeing the result, copy the result and `@AI` or continue the conversation
- Example: `@AI 我刚掷了侦查，结果是51，普通成功` (I just rolled Spot Hidden, result 51, regular success)
- Best for: players who enjoy rolling dice themselves and value the ritual

**Style 3: Hybrid mode**
- Hidden rolls and behind-the-scenes checks handled by the AI
- Critical checks rolled by the player, who then reports the result
- Best for: groups wanting both immersion and engagement

#### Command prefix notes

NekroAgent's default command prefix is `/`, so `.ra 侦查` will not be recognized as a command.

To use the `.` prefix (common in TRPG communities):
- Go to NekroAgent Web UI → Configuration → OneBot V11 Adapter → Command Prefix
- Change `/` to `.`
- Restart the container for the change to take effect

> ⚠️ **Note**: Even after changing to the `.` prefix, command output is still invisible to the AI. This only changes the symbol that triggers commands.

### Basic Usage

#### Rolling Dice

```
r 3d6+2          # Basic dice roll
ra 侦察          # Skill check
adv d20          # Advantage roll
me 仔细观察房间   # Character action
```

#### Character Sheet Management

```
st               # Show character sheet
st new 我的调查员 # Create new character
st temp coc7     # Switch to COC7 template
st init          # Auto-generate attributes
```

#### Document Management

```
doc_text module 深海古城 [module content...]  # Upload document
doc search 深海古城的NPC                      # Search content
ask 这个模组的主要剧情是什么                   # Intelligent Q&A
```

#### Session Report System

```
# Auto mode — just start playing!
r 3d6+2                       # First dice roll auto-starts recording
ra 侦察                       # Auto-recorded
me 仔细观察房间              # Auto-recorded

# Manual mode — optional, for custom session names
session start 深海古城探险      # Manually specify a name to start
session event 发现神秘地下入口  # Record a key event
session end                      # Generate session report
```

## 📖 Detailed Documentation

- [User Manual](trpg_dice/docs/trpg_dice_help.md) — Complete feature guide
- [Prompt System](trpg_dice/docs/trpg_prompt_examples.md) — AI behavior configuration
- [Developer Documentation](trpg_dice/docs/development.md) — Extension and customization guide

## 🎮 Supported TRPG Systems

### Call of Cthulhu 7th Edition (COC7)

- Complete skill check system
- Sanity (SAN) management
- Official character generation rules
- Bilingual (Chinese/English) skill alias support

### Dungeons & Dragons 5E (DND5E)

- Advantage/disadvantage mechanics
- Six-attribute system
- Combat initiative management
- Standard character generation

### World of Darkness (WOD)

- Dice pool check system
- Specialty rules support
- Botch determination

### Other Systems

- Universal dice system
- Extensible architecture
- Custom template support

## 🛠️ Configuration Options

```python
# Dice system
MAX_DICE_COUNT = 100        # Maximum number of dice
MAX_DICE_SIDES = 1000       # Maximum number of dice sides

# Document & vector retrieval
ENABLE_VECTOR_DB = True     # Enable document features
CHUNK_SIZE = 4000           # Document chunk size (characters)
CHUNK_OVERLAP = 800         # Chunk overlap size
MAX_SEARCH_RESULTS = 15     # Max vector search results

# Module full-text analysis (requires 1M context model)
MODULE_INIT_MODEL_GROUP = "default"        # LLM model group for module analysis (recommended: deepseek-v4)
MODULE_INIT_MAX_INPUT_TOKENS = 800000      # Max input characters (fits 1M context)
MODULE_INIT_MAX_OUTPUT_TOKENS = 32768      # Max output tokens (structured data needs 4K-32K)
MODULE_INIT_AUTO_START = True              # Auto-initialize after uploading a module

# Plugin activation scheduling (system-managed)
allow_sleep = True          # Allow plugin to sleep
sleep_brief = "TRPG跑团系统，涉及掷骰/检定/角色卡时激活"
```

## 🤝 Contributing

Issues and pull requests are welcome!

### Development Environment Setup

```bash
git clone <repo-url>
cd nekro-trpg-plugin
pip install -r requirements.txt
```

### Code Structure

```
trpg_dice/
├── __init__.py              # Plugin entry point
├── plugin.py                # Main plugin file (36 sandbox methods)
├── core/                    # Core modules
│   ├── dice_engine.py       # Dice engine
│   ├── character_manager.py # Character management
│   ├── document_manager.py  # Document management (vector storage)
│   ├── module_initializer.py # Module full-text analysis engine
│   ├── battle_report.py     # Session report system
│   └── prompt_injection.py  # Prompt injection (auto-injects character status/game time/world changes)
├── templates/               # Character templates
├── docs/                    # Documentation
└── examples/                # Examples
```

## 📄 License

MIT License

## 🙏 Acknowledgments

- [OlivOS-Team/OlivOS](https://github.com/OlivOS-Team/OlivOS) — Referenced dice system
- [OlivaDice](https://wiki.dice.center/User/Manual) — Feature design reference
- Nekro Agent Team — For the excellent plugin framework

## 📞 Support

- [Issues](../../issues) — Report problems
- [Discussions](../../discussions) — Community discussion
- [Wiki](../../wiki) — Detailed documentation

---

**Enjoy your TRPG adventures! 🎲✨**
