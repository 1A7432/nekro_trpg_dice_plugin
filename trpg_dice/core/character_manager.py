"""
TRPG 角色管理模块

提供完整的角色卡管理功能，包括多系统模板支持、角色生成、技能管理等。
"""

import time
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime


class CharacterSheet:
    """完整的角色卡片类"""
    
    def __init__(self, name: str = "未命名角色", system: str = "CoC"):
        self.name = name
        self.system = system  # CoC, DnD5e, WoD 等
        
        # 基础属性 (使用官方COC7标准)
        if system == "CoC":
            self.attributes = {
                "STR": 50, "CON": 50, "SIZ": 50, "DEX": 50,
                "APP": 50, "INT": 50, "POW": 50, "EDU": 50, "LUC": 50,
                # 衍生属性
                "SAN": 50, "SANMAX": 50, "HP": 10, "HPMAX": 10,
                "MP": 10, "MPMAX": 10, "IDEA": 50, "KNOW": 50,
                # 加值属性
                "SANMAXADD": 0, "HPMAXADD": 0, "MPMAXADD": 0
            }
            self.secondary_attributes = {}  # 不再使用，属性统一到attributes
            self.skills = {
                "会计": 5, "人类学": 1, "估价": 5, "考古学": 1, "取悦": 15,
                "攀爬": 20, "计算机使用": 5, "信用": 0, "克苏鲁神话": 0,
                "乔装": 5, "闪避": 25, "汽车驾驶": 20, "电气维修": 10,
                "电子学": 1, "话术": 5, "急救": 30, "历史": 5,
                "恐吓": 15, "跳跃": 20, "母语": 50, "法律": 5,
                "图书馆": 20, "聆听": 20, "锁匠": 1, "机械维修": 10,
                "医学": 1, "博物": 10, "导航": 10, "神秘学": 5,
                "操作重型机械": 1, "说服": 10, "精神分析": 1, "心理学": 10,
                "骑乘": 5, "妙手": 10, "侦查": 25, "潜行": 20,
                "游泳": 20, "投掷": 20, "追踪": 10, "驯兽": 5,
                "潜水": 1, "爆破": 1, "读唇": 1, "催眠": 1,
                "炮术": 1, "手枪": 20, "步霰": 25, "斗殴": 20
            }
            self.occupation = ""
            self.age = 25
            
        elif system == "DnD5e":
            self.attributes = {
                "力量": 10, "敏捷": 10, "体质": 10,
                "智力": 10, "感知": 10, "魅力": 10
            }
            self.secondary_attributes = {
                "生命值": 8, "护甲等级": 10, "先攻修正": 0, "速度": 30,
                "熟练加值": 2, "被动感知": 10
            }
            self.skills = {}
            self.character_class = ""
            self.race = ""
            self.level = 1
            
        self.equipment = []
        self.background = ""
        self.notes = ""
        self.created_time = time.time()
        self.last_updated = time.time()
    
    def get_modifier(self, attribute: str) -> int:
        """获取属性修正值"""
        if self.system == "DnD5e":
            value = self.attributes.get(attribute, 10)
            return (value - 10) // 2
        elif self.system == "CoC":
            # CoC使用直接的属性值进行检定
            return self.attributes.get(attribute, 50)
        return 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "system": self.system,
            "attributes": self.attributes,
            "secondary_attributes": getattr(self, 'secondary_attributes', {}),
            "skills": self.skills,
            "equipment": getattr(self, 'equipment', []),
            "background": getattr(self, 'background', ""),
            "notes": getattr(self, 'notes', ""),
            "occupation": getattr(self, 'occupation', ""),
            "age": getattr(self, 'age', 25),
            "character_class": getattr(self, 'character_class', ""),
            "race": getattr(self, 'race', ""),
            "level": getattr(self, 'level', 1),
            "created_time": self.created_time,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CharacterSheet':
        """从字典创建角色"""
        character = cls(data.get("name", ""), data.get("system", "CoC"))
        character.attributes = data.get("attributes", {})
        character.secondary_attributes = data.get("secondary_attributes", {})
        character.skills = data.get("skills", {})
        character.equipment = data.get("equipment", [])
        character.background = data.get("background", "")
        character.notes = data.get("notes", "")
        character.occupation = data.get("occupation", "")
        character.age = data.get("age", 25)
        character.character_class = data.get("character_class", "")
        character.race = data.get("race", "")
        character.level = data.get("level", 1)
        character.created_time = data.get("created_time", time.time())
        character.last_updated = data.get("last_updated", time.time())
        return character


class CharacterTemplate:
    """
    人物卡模板类 - 基于OlivaDice模板系统设计
    
    功能特性：
    - 多游戏系统支持 (COC7, DND5E, FATE等)
    - 自定义骰子规则和技能映射
    - 自动角色生成
    - 技能别名系统
    - 检定规则配置
    """
    
    def __init__(self, name: str, system: str):
        self.name = name
        self.system = system
        self.main_dice = "1d100"  # 默认检定骰子
        
        # 基础属性定义
        self.attributes = {}
        
        # 技能定义和初始值
        self.skills = {}
        
        # 衍生属性计算规则
        self.mapping = {}
        
        # 技能别名 (多个名称指向同一技能)
        self.synonyms = {}
        
        # 检定规则配置
        self.check_rules = {
            "critical_success": [1],      # 大成功判定
            "critical_failure": [100],    # 大失败判定
            "success_levels": {           # 成功等级
                "极难成功": 20,
                "困难成功": 50,
                "普通成功": 100
            }
        }
        
        # 自动生成规则
        self.init_rules = {}
    
    def apply_to_character(self, character: CharacterSheet):
        """将模板应用到角色卡"""
        from .dice_engine import DiceRoller  # 避免循环导入
        
        character.system = self.system
        
        # 应用基础属性
        for attr, value in self.attributes.items():
            if isinstance(value, dict) and "dice" in value:
                # 如果是骰子表达式，进行掷骰
                roll_result = DiceRoller.roll_expression(value["dice"])
                character.attributes[attr] = roll_result.total
            else:
                character.attributes[attr] = value
        
        # 应用技能初始值
        for skill, value in self.skills.items():
            if isinstance(value, dict) and "dice" in value:
                roll_result = DiceRoller.roll_expression(value["dice"])
                character.skills[skill] = roll_result.total
            elif isinstance(value, str) and "{" in value:
                # 处理字符串公式，如 "{EDU}", "({DEX})/2"
                try:
                    calc_formula = value
                    for attr, attr_value in character.attributes.items():
                        calc_formula = calc_formula.replace(f"{{{attr}}}", str(attr_value))
                    result = eval(calc_formula, {"__builtins__": {}})
                    character.skills[skill] = int(result)
                except Exception:
                    character.skills[skill] = value  # 保留原值
            else:
                character.skills[skill] = value
        
        # 计算衍生属性
        self._calculate_mappings(character)
    
    def _calculate_mappings(self, character: CharacterSheet):
        """计算衍生属性值"""
        for target, formula in self.mapping.items():
            try:
                # 替换公式中的属性值
                calc_formula = formula
                for attr, value in character.attributes.items():
                    calc_formula = calc_formula.replace(f"{{{attr}}}", str(value))
                
                # 安全计算公式
                result = eval(calc_formula, {"__builtins__": {}})
                character.attributes[target] = int(result)
            except Exception:
                pass  # 计算失败则跳过
    
    def find_skill_alias(self, skill_name: str) -> Optional[str]:
        """查找技能别名，返回标准技能名"""
        skill_name = skill_name.lower().strip()
        
        # 直接匹配
        for standard_name, aliases in self.synonyms.items():
            if skill_name == standard_name.lower():
                return standard_name
            if skill_name in [alias.lower() for alias in aliases]:
                return standard_name
        
        return None
    
    @classmethod
    def get_coc7_template(cls) -> 'CharacterTemplate':
        """获取标准COC7模板"""
        template = cls("COC7标准", "CoC")
        template.main_dice = "1d100"
        
        # 基础属性生成规则
        template.attributes = {
            "STR": {"dice": "3d6x5"},  # 力量
            "CON": {"dice": "3d6x5"},  # 体质
            "SIZ": {"dice": "(2d6+6)x5"},  # 体型
            "DEX": {"dice": "3d6x5"},  # 敏捷
            "APP": {"dice": "3d6x5"},  # 外貌
            "INT": {"dice": "(2d6+6)x5"},  # 智力
            "POW": {"dice": "3d6x5"},  # 意志
            "EDU": {"dice": "(2d6+6)x5"},  # 教育
            "LUC": {"dice": "3d6x5"}   # 幸运
        }
        
        # 衍生属性计算
        template.mapping = {
            "SANMAX": "{POW}",
            "SAN": "{POW}",
            "HPMAX": "({CON}+{SIZ})/10",
            "HP": "({CON}+{SIZ})/10",
            "MPMAX": "{POW}/5",
            "MP": "{POW}/5",
            "IDEA": "{INT}",
            "KNOW": "{EDU}"
        }
        
        # 技能别名系统
        template.synonyms = {
            "会计": ["accounting", "会计学"],
            "人类学": ["anthropology", "人类学"],
            "估价": ["appraise", "鉴定", "估价"],
            "考古学": ["archaeology", "考古学"],
            "取悦": ["charm", "魅惑", "取悦"],
            "攀爬": ["climb", "攀爬"],
            "计算机使用": ["computer use", "电脑", "计算机"],
            "信用": ["credit rating", "信用评级", "信用"],
            "克苏鲁神话": ["cthulhu mythos", "神话", "克苏鲁"],
            "乔装": ["disguise", "伪装", "乔装"],
            "闪避": ["dodge", "回避", "闪避"],
            "汽车驾驶": ["drive auto", "驾驶", "开车"],
            "电气维修": ["electrical repair", "电器", "电气"],
            "话术": ["fast talk", "快速交谈", "话术"],
            "急救": ["first aid", "医疗", "急救"],
            "历史": ["history", "历史"],
            "恐吓": ["intimidate", "威吓", "恐吓"],
            "跳跃": ["jump", "跳跃"],
            "母语": ["own language", "母语"],
            "法律": ["law", "法学", "法律"],
            "图书馆": ["library use", "图书馆使用", "图书馆"],
            "聆听": ["listen", "倾听", "聆听"],
            "锁匠": ["locksmith", "开锁", "锁匠"],
            "机械维修": ["mechanical repair", "机械", "维修"],
            "医学": ["medicine", "医疗", "医学"],
            "博物": ["natural world", "自然", "博物"],
            "导航": ["navigate", "导航"],
            "神秘学": ["occult", "神秘学"],
            "说服": ["persuade", "劝说", "说服"],
            "心理学": ["psychology", "心理学"],
            "骑乘": ["ride", "骑术", "骑乘"],
            "妙手": ["sleight of hand", "巧手", "妙手"],
            "侦查": ["spot hidden", "发现", "侦查"],
            "潜行": ["stealth", "隐匿", "潜行"],
            "游泳": ["swim", "游泳"],
            "投掷": ["throw", "投掷"],
            "追踪": ["track", "追踪"],
            "斗殴": ["fighting brawl", "格斗", "斗殴"],
            "手枪": ["handgun", "手枪"],
            "步霰": ["rifle/shotgun", "长枪", "步枪"]
        }
        
        return template
    
    @classmethod
    def get_dnd5e_template(cls) -> 'CharacterTemplate':
        """获取标准DND5E模板"""
        template = cls("DND5E标准", "DnD5e")
        template.main_dice = "1d20"
        
        # 六大基础属性 - 使用4d6k3生成
        template.attributes = {
            "STR": {"dice": "4d6k3"},  # 力量
            "DEX": {"dice": "4d6k3"},  # 敏捷
            "CON": {"dice": "4d6k3"},  # 体质
            "INT": {"dice": "4d6k3"},  # 智力
            "WIS": {"dice": "4d6k3"},  # 感知
            "CHA": {"dice": "4d6k3"}   # 魅力
        }
        
        # 衍生属性计算
        template.mapping = {
            "速度": "30",
            "先攻": "({DEX}-10)/2",
            "载重": "{STR}*15",
            "负重": "{STR}*10", 
            "护甲等级": "10+({DEX}-10)/2"
        }
        
        # 技能基础值（基于属性修正值）
        template.skills = {
            # 力量技能
            "运动": "({STR}-10)/2",
            
            # 敏捷技能
            "体操": "({DEX}-10)/2",
            "巧手": "({DEX}-10)/2",
            "隐匿": "({DEX}-10)/2",
            
            # 智力技能
            "调查": "({INT}-10)/2",
            "奥秘": "({INT}-10)/2", 
            "历史": "({INT}-10)/2",
            "自然": "({INT}-10)/2",
            "宗教": "({INT}-10)/2",
            
            # 感知技能
            "察觉": "({WIS}-10)/2",
            "洞悉": "({WIS}-10)/2",
            "驯兽": "({WIS}-10)/2",
            "医药": "({WIS}-10)/2",
            "生存": "({WIS}-10)/2",
            
            # 魅力技能
            "游说": "({CHA}-10)/2",
            "欺瞒": "({CHA}-10)/2",
            "威吓": "({CHA}-10)/2",
            "表演": "({CHA}-10)/2"
        }
        
        # 技能别名系统（中英文支持）
        template.synonyms = {
            # 基础属性
            "STR": ["力量", "STR", "Strength"],
            "DEX": ["敏捷", "DEX", "Dexterity"],
            "CON": ["体质", "CON", "Constitution"],
            "INT": ["智力", "INT", "Intelligence"],
            "WIS": ["感知", "WIS", "Wisdom"],
            "CHA": ["魅力", "CHA", "Charisma"],
            
            # 基础状态
            "先攻": ["先攻", "Initiative"],
            "速度": ["速度", "Speed"],
            "载重": ["载重", "Carrying_Capacity"],
            "负重": ["负重", "Encumbrance"],
            "护甲等级": ["AC", "Armor_Class", "护甲等级"],
            
            # 技能别名
            "运动": ["运动", "Athletics"],
            "体操": ["体操", "Acrobatics"],
            "巧手": ["Sleight_of_Hand", "巧手", "手上功夫"],
            "隐匿": ["Stealth", "隐匿"],
            "奥秘": ["Arcana", "奥秘"],
            "历史": ["History", "历史"],
            "调查": ["Investigation", "调查"],
            "自然": ["Nature", "自然"],
            "宗教": ["Religion", "宗教"],
            "驯兽": ["Animal_Handling", "动物驯养", "驯兽"],
            "洞悉": ["Insight", "洞悉"],
            "医药": ["Medicine", "医药"],
            "察觉": ["Perception", "察觉", "观察"],
            "生存": ["Survival", "生存", "求生"],
            "欺瞒": ["Deception", "欺瞒"],
            "威吓": ["Intimidation", "威吓"],
            "表演": ["Performance", "表演"],
            "游说": ["Persuasion", "游说"],
            
            # 货币
            "金币": ["Gold_Piece", "金币", "GP"],
            "银币": ["Silver_Piece", "银币", "SP"],
            "铜币": ["Copper_Piece", "CP", "铜币"],
            "铂金币": ["Electrum_Piece", "铂金币", "EP"],
            "白金币": ["Platinum_Piece", "白金币", "PP"]
        }
        
        # 检定规则
        template.check_rules = {
            "critical_success": [20],
            "critical_failure": [1],
            "success_levels": {
                "大成功": 20,
                "成功": "target_met",
                "失败": "target_missed", 
                "大失败": 1
            }
        }
        
        return template


class CharacterManager:
    """角色管理器"""
    
    def __init__(self, store):
        self.store = store
        self.templates = {
            "coc7": CharacterTemplate.get_coc7_template(),
            "dnd5e": CharacterTemplate.get_dnd5e_template()
        }
    
    async def get_character(self, user_id: str, chat_key: str, char_name: str = "") -> CharacterSheet:
        """获取用户角色卡"""
        # 获取活跃角色名
        if not char_name:
            active_key = f"active_character.{chat_key}"
            try:
                active_name = await self.store.get(user_key=user_id, store_key=active_key)
                char_name = active_name if active_name else "default"
            except Exception:
                char_name = "default"
        
        # 使用user_key作用域存储
        store_key = f"characters.{chat_key}.{char_name}"
        
        try:
            char_data = await self.store.get(user_key=user_id, store_key=store_key)
            if char_data:
                # 使用Pydantic模型解析JSON数据
                data_dict = json.loads(char_data)
                return CharacterSheet.from_dict(data_dict)
        except Exception as e:
            pass
        
        # 返回默认角色卡
        return CharacterSheet(name=char_name)
    
    async def save_character(self, user_id: str, chat_key: str, character: CharacterSheet):
        """保存用户角色卡"""
        character.last_updated = time.time()
        store_key = f"characters.{chat_key}.{character.name}"
        
        # 使用官方推荐的user_key作用域和JSON序列化
        await self.store.set(
            user_key=user_id,
            store_key=store_key,
            value=json.dumps(character.to_dict(), ensure_ascii=False)
        )
        
        # 同时更新活跃角色
        await self.set_active_character(user_id, chat_key, character.name)
    
    async def set_active_character(self, user_id: str, chat_key: str, char_name: str):
        """设置当前激活的角色卡"""
        active_key = f"active_character.{chat_key}"
        await self.store.set(user_key=user_id, store_key=active_key, value=char_name)
    
    async def get_daily_luck(self, user_id: str) -> int:
        """获取今日人品值"""
        today = datetime.now().strftime("%Y-%m-%d")
        store_key = f"daily_luck.{today}"
        
        try:
            luck_data = await self.store.get(user_key=user_id, store_key=store_key)
            if luck_data:
                return int(luck_data)
        except (ValueError, TypeError):
            pass
        
        # 生成新的人品值
        hash_input = f"{user_id}_{today}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        luck_value = (hash_value % 100) + 1  # 1-100
        
        # 使用user_key作用域保存
        await self.store.set(user_key=user_id, store_key=store_key, value=str(luck_value))
        return luck_value
    
    def generate_character(self, template_name: str, char_name: str = "新角色") -> CharacterSheet:
        """使用模板生成角色"""
        if template_name not in self.templates:
            raise ValueError(f"未知的模板: {template_name}")
        
        template = self.templates[template_name]
        character = CharacterSheet(name=char_name, system=template.system)
        template.apply_to_character(character)
        
        return character
    
    def find_skill_by_alias(self, character: CharacterSheet, skill_name: str) -> Optional[str]:
        """通过别名查找技能"""
        # 获取角色对应的模板
        template_name = "coc7" if character.system == "CoC" else "dnd5e"
        if template_name in self.templates:
            template = self.templates[template_name]
            return template.find_skill_alias(skill_name)
        return None