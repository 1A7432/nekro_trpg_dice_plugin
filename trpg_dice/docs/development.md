# TRPG Dice Plugin 二次开发指南

本文档为希望基于本插件进行二次开发或贡献代码的开发者提供详细指导。

## 📁 项目结构

```
trpg_dice/
├── __init__.py              # 插件入口，定义导出内容
├── plugin.py                # 主插件文件，命令处理和插件配置
├── core/                    # 核心功能模块
│   ├── __init__.py          # 核心模块导出
│   ├── dice_engine.py       # 骰子解析和投掷引擎
│   ├── character_manager.py # 角色卡管理系统
│   ├── document_manager.py  # 文档存储和检索系统
│   └── prompt_injection.py  # AI提示词注入系统
├── templates/               # 角色生成模板
│   ├── coc7_template.json   # COC7官方模板
│   └── dnd5e_template.json  # DND5E官方模板
├── docs/                    # 文档目录
│   ├── trpg_dice_help.md    # 用户使用手册
│   ├── trpg_prompt_examples.md  # 提示词注入示例
│   └── development.md       # 本开发文档
└── examples/                # 示例代码（预留）
```

## 🔧 核心模块详解

### 1. 骰子引擎 (dice_engine.py)

#### 核心类说明

**DiceParser**: 骰子表达式解析器
```python
@staticmethod
def parse_expression(expression: str) -> Tuple[int, int, int, int, int]:
    """
    解析骰子表达式
    返回: (数量, 面数, 修正值, 乘数, 保留数量)
    
    支持的表达式格式:
    - d20, 3d6, 2d10+5 (基础格式)
    - 4d6k3 (保留最高3个)
    - 3d6x5, (2d6+6)x5 (乘法)
    """
```

**DiceRoller**: 骰子投掷器
```python
@staticmethod
def roll_dice(dice_count: int, dice_sides: int, keep_count: int = 0) -> List[int]:
    """
    投掷骰子并可选择保留最高的N个
    keep_count=0表示保留全部
    """
```

#### 扩展新骰子语法

要添加新的骰子表达式语法，需要修改 `DiceParser.parse_expression()`:

```python
# 在parse_expression方法中添加新的解析逻辑
if 'new_syntax' in expression:
    # 解析新语法的逻辑
    pass
```

**示例：添加"取最低值"语法 (4d6l1)**

```python
# 在parse_expression中的k语法后添加
if 'l' in expression and 'k' not in expression:
    l_parts = expression.split('l')
    if len(l_parts) == 2:
        dice_part = l_parts[0].strip()
        drop_count = int(l_parts[1].strip())
        
        # 解析逻辑...
        return dice_count, dice_sides, modifier, 1, -drop_count  # 负数表示丢弃
```

### 2. 角色管理系统 (character_manager.py)

#### 核心类说明

**CharacterSheet**: 角色卡数据模型
```python
class CharacterSheet:
    def __init__(self, name: str = "未命名角色", system: str = "CoC"):
        self.name = name
        self.system = system
        self.attributes = {}      # 基础属性
        self.skills = {}          # 技能
        self.equipment = []       # 装备
        # ... 其他属性
```

**CharacterTemplate**: 角色模板系统
```python
class CharacterTemplate:
    def __init__(self, name: str, system: str):
        self.attributes = {}      # 属性定义和生成规则
        self.skills = {}          # 技能初始值
        self.mapping = {}         # 衍生属性计算公式
        self.synonyms = {}        # 技能别名映射
```

#### 添加新的TRPG系统

1. **创建新模板**:
```python
@classmethod
def get_new_system_template(cls) -> 'CharacterTemplate':
    template = cls("新系统标准", "NewSystem")
    template.main_dice = "1d100"  # 或其他主要骰子
    
    # 定义属性生成规则
    template.attributes = {
        "属性1": {"dice": "3d6"},
        "属性2": 50,  # 固定值
    }
    
    # 定义衍生属性计算
    template.mapping = {
        "衍生属性": "{属性1}*2",
    }
    
    # 定义技能别名
    template.synonyms = {
        "技能1": ["skill1", "技能一"],
    }
    
    return template
```

2. **在CharacterManager中注册**:
```python
def __init__(self, store):
    self.templates = {
        "coc7": CharacterTemplate.get_coc7_template(),
        "dnd5e": CharacterTemplate.get_dnd5e_template(),
        "new_system": CharacterTemplate.get_new_system_template(),  # 新系统
    }
```

### 3. 文档管理系统 (document_manager.py)

#### 核心类说明

**DocumentProcessor**: 文档处理器
```python
class DocumentProcessor:
    @staticmethod
    def extract_text_by_extension(filename: str, file_content: bytes) -> str:
        """根据文件扩展名提取文本"""
```

**VectorDatabaseManager**: 向量数据库管理
```python
class VectorDatabaseManager:
    async def store_document(self, document_id: str, filename: str, 
                           text_content: str, user_id: str, chat_key: str, 
                           document_type: str = "module") -> int:
        """存储文档到向量数据库"""
```

#### 添加新文档类型支持

1. **扩展文档处理器**:
```python
@staticmethod
def extract_text_from_new_format(file_content: bytes) -> str:
    """处理新格式文档"""
    # 实现新格式的解析逻辑
    pass

# 在extract_text_by_extension中添加
elif extension == 'newext':
    return DocumentProcessor.extract_text_from_new_format(file_content)
```

2. **添加新文档分类**:
```python
# 在plugin.py的doc命令中添加新类型
if doc_type not in ["module", "rule", "story", "background", "new_type"]:
    await message.finish("❌ 文档类型必须是: module/rule/story/background/new_type")
```

### 4. 提示词注入系统 (prompt_injection.py)

#### 核心功能

提示词注入让AI能够智能地使用插件功能，提供专业的TRPG体验。

```python
def register_prompt_injections(plugin, character_manager, vector_db, store, config):
    """注册所有提示词注入方法"""
    
    @plugin.mount_prompt_inject_method(
        name="custom_prompt",
        description="自定义提示词注入"
    )
    async def custom_inject(_ctx) -> str:
        # 自定义提示词逻辑
        return "自定义提示词内容"
```

#### 添加新的提示词注入

```python
async def inject_custom_behavior(_ctx, additional_context) -> str:
    """自定义AI行为提示词"""
    
    prompt_parts = [
        "# 自定义功能说明",
        "",
        "你现在具有以下额外能力:",
        "• 自定义功能1",
        "• 自定义功能2",
    ]
    
    # 可以根据上下文动态生成内容
    if additional_context:
        prompt_parts.extend([
            "",
            f"当前上下文: {additional_context}"
        ])
    
    return "\n".join(prompt_parts)
```

## 🎮 添加新命令

### 1. 基础命令添加

在 `plugin.py` 中添加新的命令处理器:

```python
@on_command("new_cmd", aliases={"新命令"}, priority=5, block=True).handle()
async def handle_new_command(event: MessageEvent, args: Message = CommandArg()):
    """新命令处理器"""
    user_input = args.extract_plain_text().strip()
    
    try:
        # 命令逻辑处理
        result = process_new_command(user_input)
        await message.finish(f"✅ {result}")
    except Exception as e:
        await message.finish(f"❌ 命令执行失败: {str(e)}")
```

### 2. 复杂命令示例

```python
@on_command("batch_roll", aliases={"批量掷骰"}, priority=5, block=True).handle()
async def handle_batch_roll(event: MessageEvent, args: Message = CommandArg()):
    """批量掷骰命令示例"""
    args_text = args.extract_plain_text().strip()
    
    if not args_text:
        await message.finish("用法: batch_roll <次数> <表达式>\n例如: batch_roll 5 3d6")
    
    parts = args_text.split(' ', 1)
    if len(parts) != 2:
        await message.finish("❌ 参数格式错误")
    
    try:
        count = int(parts[0])
        expression = parts[1]
        
        if count > 10:  # 限制批量掷骰次数
            await message.finish("❌ 批量掷骰次数不能超过10次")
        
        results = []
        for i in range(count):
            result = DiceRoller.roll_expression(expression)
            results.append(f"{i+1}. {result.format_result()}")
        
        response = f"🎲 批量掷骰 {expression} x{count}:\n"
        response += "\n".join(results)
        
        # 计算统计信息
        totals = [DiceRoller.roll_expression(expression).total for _ in range(count)]
        avg = sum(totals) / len(totals)
        response += f"\n📊 平均值: {avg:.1f}, 最高: {max(totals)}, 最低: {min(totals)}"
        
        await message.finish(response)
        
    except ValueError as e:
        await message.finish(f"❌ 参数错误: {str(e)}")
    except Exception as e:
        await message.finish(f"❌ 执行失败: {str(e)}")
```

## 🔧 配置和扩展

### 1. 插件配置扩展

在 `plugin.py` 的 `TRPGDiceConfig` 类中添加新配置项:

```python
@plugin.mount_config()
class TRPGDiceConfig(ConfigBase):
    # 现有配置...
    
    # 新增配置
    ENABLE_BATCH_ROLLS: bool = Field(
        default=True,
        title="启用批量掷骰",
        description="是否允许批量掷骰功能",
    )
    MAX_BATCH_COUNT: int = Field(
        default=10,
        title="最大批量数量",
        description="单次批量掷骰的最大次数",
    )
    CUSTOM_FEATURE_ENABLED: bool = Field(
        default=False,
        title="启用自定义功能",
        description="是否启用实验性自定义功能",
    )
```

### 2. 存储系统扩展

使用官方存储API添加新的数据类型:

```python
async def save_custom_data(user_id: str, chat_key: str, data: dict):
    """保存自定义数据"""
    store_key = f"custom_data.{chat_key}"
    await store.set(
        user_key=user_id, 
        store_key=store_key, 
        value=json.dumps(data, ensure_ascii=False)
    )

async def get_custom_data(user_id: str, chat_key: str) -> dict:
    """获取自定义数据"""
    store_key = f"custom_data.{chat_key}"
    try:
        data = await store.get(user_key=user_id, store_key=store_key)
        return json.loads(data) if data else {}
    except Exception:
        return {}
```

## 🧪 测试和调试

### 1. 单元测试

创建测试文件 `tests/test_dice_engine.py`:

```python
import unittest
from trpg_dice.core.dice_engine import DiceParser, DiceRoller

class TestDiceEngine(unittest.TestCase):
    
    def test_4d6k3_parsing(self):
        """测试4d6k3表达式解析"""
        result = DiceParser.parse_expression("4d6k3")
        self.assertEqual(result, (4, 6, 0, 1, 3))
    
    def test_basic_dice_rolling(self):
        """测试基础掷骰功能"""
        result = DiceRoller.roll_expression("d20")
        self.assertTrue(1 <= result.total <= 20)
    
    def test_complex_expression(self):
        """测试复杂表达式"""
        result = DiceRoller.roll_expression("3d6+2")
        self.assertTrue(5 <= result.total <= 20)  # 3-18 + 2

if __name__ == '__main__':
    unittest.main()
```

### 2. 调试技巧

在开发过程中，可以添加调试日志:

```python
import logging

# 在plugin.py开头添加
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 在关键位置添加日志
@on_command("debug_cmd")
async def debug_command(event: MessageEvent, args: Message = CommandArg()):
    logger.debug(f"Debug command called with args: {args}")
    
    try:
        result = some_complex_operation()
        logger.info(f"Operation successful: {result}")
        await message.finish(f"✅ 调试结果: {result}")
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        await message.finish(f"❌ 调试失败: {str(e)}")
```

## 📦 打包和发布

### 1. 版本管理

更新 `__init__.py` 中的版本信息:

```python
__version__ = "1.1.0"  # 遵循语义化版本
```

### 2. 依赖管理

更新 `requirements.txt`:

```txt
# 添加新依赖
new-dependency>=1.0.0
```

### 3. 文档更新

确保更新以下文档:
- `README.md`: 新功能说明
- `trpg_dice_help.md`: 用户手册更新
- `CHANGELOG.md`: 版本变更记录

## 🤝 贡献指南

### 1. 代码规范

- 使用中文注释和文档字符串
- 遵循PEP 8代码风格
- 类和函数命名使用英文，变量可使用中文拼音
- 错误消息使用中文，便于用户理解

### 2. Git工作流

```bash
# 1. Fork项目并克隆
git clone your-fork-url
cd nekro-trpg-plugin

# 2. 创建功能分支
git checkout -b feature/new-feature

# 3. 开发和测试
# ... 开发代码 ...

# 4. 提交更改
git add .
git commit -m "feat: 新功能描述"

# 5. 推送并创建PR
git push origin feature/new-feature
```

### 3. Pull Request规范

- 标题简洁明确，使用中文
- 详细描述更改内容和原因
- 包含必要的测试
- 更新相关文档

## ⚠️ 注意事项

### 1. 性能考虑

- 大量掷骰时注意内存使用
- 向量数据库查询要设置合理的限制
- 避免在命令处理中进行耗时操作

### 2. 安全考虑

- 验证用户输入，防止注入攻击
- 限制骰子数量和面数，避免资源滥用
- 敏感配置信息不要硬编码

### 3. 兼容性

- 新功能要向下兼容
- 考虑不同聊天平台的适配
- 测试各种边界情况

## 📞 获取帮助

- **Issues**: 报告Bug或请求新功能
- **Discussions**: 技术讨论和使用问题
- **Wiki**: 查看详细文档和示例

---

希望这份开发指南能帮助你更好地理解和扩展TRPG Dice Plugin！🎲✨