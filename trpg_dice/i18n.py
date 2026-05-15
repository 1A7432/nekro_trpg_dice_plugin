"""
TRPG Dice Plugin - Internationalization (i18n) module

Phase 1: Minimal closed-loop i18n with Python stdlib gettext.
- Default language: zh_CN (identity translation)
- Runtime: zero external dependencies (stdlib gettext only)
- Build-time: Babel (pybabel) for extraction
"""

import gettext
import json
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_DEFAULT_LANGUAGE: str = "zh_CN"
_FALLBACK_LANGUAGE: str = "zh_CN"

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------
_current_language: str = _DEFAULT_LANGUAGE
_translation: Optional[gettext.NullTranslations] = None


def _locale_dir() -> str:
    """Return the absolute path to the locale directory."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")


def _install_translation(lang: str) -> gettext.NullTranslations:
    """Load and return a gettext translation for *lang*.

    Falls back to NullTranslations (returns msgid unchanged) when the
    .mo file is missing or unreadable.
    """
    localedir = _locale_dir()
    try:
        t = gettext.translation(
            domain="trpg_dice",
            localedir=localedir,
            languages=[lang],
            fallback=False,
        )
    except (FileNotFoundError, OSError, UnicodeError, Exception):
        # Broad catch: any unexpected issue loading translations should
        # not crash the application. Gracefully fall back to identity.
        t = gettext.NullTranslations()
    return t


def set_language(lang: str) -> None:
    """Switch the active UI language.

    Args:
        lang: BCP-47 / POSIX style language tag, e.g. "zh_CN", "en_US".
    """
    global _current_language, _translation
    _current_language = lang
    _translation = _install_translation(lang)


def get_current_language() -> str:
    """Return the currently active language code."""
    return _current_language


def _(message: str) -> str:
    """Translate *message* using the currently active translation.

    The module is safe to import anywhere; translation is loaded lazily
    on the first call to _().

    If no translation is loaded or the message is missing, the original
    msgid is returned unchanged (graceful fallback).

    Usage with named placeholders (REQUIRED):
        _("角色 {name} 创建成功").format(name=name)

    Do NOT use f-strings inside _():
        WRONG: _(f"角色 {name} 创建成功")
    """
    if _translation is None:
        # Lazy init on first call so the module is safe to import anywhere.
        set_language(_current_language)
    assert _translation is not None
    return _translation.gettext(message)


SKILL_DISPLAY_NAMES: dict[str, dict[str, str]] = {
    # ---- COC7 skills ----
    "会计": {"zh_CN": "会计", "en_US": "Accounting"},
    "人类学": {"zh_CN": "人类学", "en_US": "Anthropology"},
    "估价": {"zh_CN": "估价", "en_US": "Appraise"},
    "考古学": {"zh_CN": "考古学", "en_US": "Archaeology"},
    "取悦": {"zh_CN": "取悦", "en_US": "Charm"},
    "攀爬": {"zh_CN": "攀爬", "en_US": "Climb"},
    "计算机使用": {"zh_CN": "计算机使用", "en_US": "Computer Use"},
    "信用": {"zh_CN": "信用", "en_US": "Credit Rating"},
    "克苏鲁神话": {"zh_CN": "克苏鲁神话", "en_US": "Cthulhu Mythos"},
    "乔装": {"zh_CN": "乔装", "en_US": "Disguise"},
    "闪避": {"zh_CN": "闪避", "en_US": "Dodge"},
    "汽车驾驶": {"zh_CN": "汽车驾驶", "en_US": "Drive Auto"},
    "电气维修": {"zh_CN": "电气维修", "en_US": "Electrical Repair"},
    "电子学": {"zh_CN": "电子学", "en_US": "Electronics"},
    "话术": {"zh_CN": "话术", "en_US": "Fast Talk"},
    "急救": {"zh_CN": "急救", "en_US": "First Aid"},
    "历史": {"zh_CN": "历史", "en_US": "History"},
    "恐吓": {"zh_CN": "恐吓", "en_US": "Intimidate"},
    "跳跃": {"zh_CN": "跳跃", "en_US": "Jump"},
    "母语": {"zh_CN": "母语", "en_US": "Own Language"},
    "法律": {"zh_CN": "法律", "en_US": "Law"},
    "图书馆": {"zh_CN": "图书馆", "en_US": "Library Use"},
    "聆听": {"zh_CN": "聆听", "en_US": "Listen"},
    "锁匠": {"zh_CN": "锁匠", "en_US": "Locksmith"},
    "机械维修": {"zh_CN": "机械维修", "en_US": "Mechanical Repair"},
    "医学": {"zh_CN": "医学", "en_US": "Medicine"},
    "博物": {"zh_CN": "博物", "en_US": "Natural World"},
    "导航": {"zh_CN": "导航", "en_US": "Navigate"},
    "神秘学": {"zh_CN": "神秘学", "en_US": "Occult"},
    "操作重型机械": {"zh_CN": "操作重型机械", "en_US": "Operate Heavy Machinery"},
    "说服": {"zh_CN": "说服", "en_US": "Persuade"},
    "精神分析": {"zh_CN": "精神分析", "en_US": "Psychoanalysis"},
    "心理学": {"zh_CN": "心理学", "en_US": "Psychology"},
    "骑乘": {"zh_CN": "骑乘", "en_US": "Ride"},
    "妙手": {"zh_CN": "妙手", "en_US": "Sleight of Hand"},
    "侦查": {"zh_CN": "侦查", "en_US": "Spot Hidden"},
    "潜行": {"zh_CN": "潜行", "en_US": "Stealth"},
    "游泳": {"zh_CN": "游泳", "en_US": "Swim"},
    "投掷": {"zh_CN": "投掷", "en_US": "Throw"},
    "追踪": {"zh_CN": "追踪", "en_US": "Track"},
    "驯兽": {"zh_CN": "驯兽", "en_US": "Animal Handling"},
    "潜水": {"zh_CN": "潜水", "en_US": "Diving"},
    "爆破": {"zh_CN": "爆破", "en_US": "Demolitions"},
    "读唇": {"zh_CN": "读唇", "en_US": "Read Lips"},
    "催眠": {"zh_CN": "催眠", "en_US": "Hypnosis"},
    "炮术": {"zh_CN": "炮术", "en_US": "Artillery"},
    "手枪": {"zh_CN": "手枪", "en_US": "Handgun"},
    "步霰": {"zh_CN": "步霰", "en_US": "Rifle / Shotgun"},
    "斗殴": {"zh_CN": "斗殴", "en_US": "Fighting (Brawl)"},
    # ---- DND5E skills ----
    "运动": {"zh_CN": "运动", "en_US": "Athletics"},
    "体操": {"zh_CN": "体操", "en_US": "Acrobatics"},
    "巧手": {"zh_CN": "巧手", "en_US": "Sleight of Hand"},
    "隐匿": {"zh_CN": "隐匿", "en_US": "Stealth"},
    "调查": {"zh_CN": "调查", "en_US": "Investigation"},
    "奥秘": {"zh_CN": "奥秘", "en_US": "Arcana"},
    "历史": {"zh_CN": "历史", "en_US": "History"},
    "自然": {"zh_CN": "自然", "en_US": "Nature"},
    "宗教": {"zh_CN": "宗教", "en_US": "Religion"},
    "察觉": {"zh_CN": "察觉", "en_US": "Perception"},
    "洞悉": {"zh_CN": "洞悉", "en_US": "Insight"},
    "驯兽": {"zh_CN": "驯兽", "en_US": "Animal Handling"},
    "医药": {"zh_CN": "医药", "en_US": "Medicine"},
    "生存": {"zh_CN": "生存", "en_US": "Survival"},
    "游说": {"zh_CN": "游说", "en_US": "Persuasion"},
    "欺瞒": {"zh_CN": "欺瞒", "en_US": "Deception"},
    "威吓": {"zh_CN": "威吓", "en_US": "Intimidation"},
    "表演": {"zh_CN": "表演", "en_US": "Performance"},
}

ATTRIBUTE_DISPLAY_NAMES: dict[str, dict[str, str]] = {
    # ---- Shared core attributes ----
    "STR": {"zh_CN": "STR", "en_US": "Strength"},
    "CON": {"zh_CN": "CON", "en_US": "Constitution"},
    "DEX": {"zh_CN": "DEX", "en_US": "Dexterity"},
    "INT": {"zh_CN": "INT", "en_US": "Intelligence"},
    "WIS": {"zh_CN": "WIS", "en_US": "Wisdom"},
    "CHA": {"zh_CN": "CHA", "en_US": "Charisma"},
    # ---- Chinese ability names (DND5E alias support) ----
    "力量": {"zh_CN": "力量", "en_US": "Strength"},
    "体质": {"zh_CN": "体质", "en_US": "Constitution"},
    "敏捷": {"zh_CN": "敏捷", "en_US": "Dexterity"},
    "智力": {"zh_CN": "智力", "en_US": "Intelligence"},
    "感知": {"zh_CN": "感知", "en_US": "Wisdom"},
    "魅力": {"zh_CN": "魅力", "en_US": "Charisma"},
    # ---- COC7 specific ----
    "SIZ": {"zh_CN": "SIZ", "en_US": "Size"},
    "APP": {"zh_CN": "APP", "en_US": "Appearance"},
    "POW": {"zh_CN": "POW", "en_US": "Power"},
    "EDU": {"zh_CN": "EDU", "en_US": "Education"},
    "LUC": {"zh_CN": "LUC", "en_US": "Luck"},
    # ---- COC7 derived ----
    "SAN": {"zh_CN": "SAN", "en_US": "Sanity"},
    "SANMAX": {"zh_CN": "SANMAX", "en_US": "Sanity Max"},
    "HP": {"zh_CN": "HP", "en_US": "Hit Points"},
    "HPMAX": {"zh_CN": "HPMAX", "en_US": "HP Max"},
    "MP": {"zh_CN": "MP", "en_US": "Magic Points"},
    "MPMAX": {"zh_CN": "MPMAX", "en_US": "MP Max"},
    "IDEA": {"zh_CN": "IDEA", "en_US": "Idea"},
    "KNOW": {"zh_CN": "KNOW", "en_US": "Knowledge"},
    "SANMAXADD": {"zh_CN": "SANMAXADD", "en_US": "Sanity Max Bonus"},
    "HPMAXADD": {"zh_CN": "HPMAXADD", "en_US": "HP Max Bonus"},
    "MPMAXADD": {"zh_CN": "MPMAXADD", "en_US": "MP Max Bonus"},
    # ---- DND5E derived / secondary ----
    "速度": {"zh_CN": "速度", "en_US": "Speed"},
    "先攻": {"zh_CN": "先攻", "en_US": "Initiative"},
    "先攻修正": {"zh_CN": "先攻修正", "en_US": "Initiative Modifier"},
    "载重": {"zh_CN": "载重", "en_US": "Carrying Capacity"},
    "负重": {"zh_CN": "负重", "en_US": "Encumbrance"},
    "护甲等级": {"zh_CN": "护甲等级", "en_US": "Armor Class"},
    "生命值": {"zh_CN": "生命值", "en_US": "Hit Points"},
    "熟练加值": {"zh_CN": "熟练加值", "en_US": "Proficiency Bonus"},
    "被动感知": {"zh_CN": "被动感知", "en_US": "Passive Perception"},
}


def t_skill_name(key: str, lang: Optional[str] = None) -> str:
    """Return the localized display name for a skill.

    Falls back to the raw *key* if no mapping exists.
    """
    target_lang = lang or _current_language
    mapping = SKILL_DISPLAY_NAMES.get(key, {})
    return mapping.get(target_lang, key)


def t_attribute_name(key: str, lang: Optional[str] = None) -> str:
    """Return the localized display name for an attribute.

    Falls back to the raw *key* if no mapping exists.
    """
    target_lang = lang or _current_language
    mapping = ATTRIBUTE_DISPLAY_NAMES.get(key, {})
    return mapping.get(target_lang, key)


_PROMPT_CACHE: dict[str, dict[str, str]] = {}


def _load_prompts(lang: str) -> dict[str, str]:
    if lang not in _PROMPT_CACHE:
        path = os.path.join(os.path.dirname(__file__), "locales", f"prompts.{lang}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _PROMPT_CACHE[lang] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _PROMPT_CACHE[lang] = {}
    return _PROMPT_CACHE[lang]


def t_prompt(key: str, lang: Optional[str] = None) -> str:
    target_lang = lang or _current_language
    prompts = _load_prompts(target_lang)
    text = prompts.get(key)
    if text:
        return text
    if target_lang != "zh_CN":
        prompts = _load_prompts("zh_CN")
        text = prompts.get(key)
        if text:
            return text
    return key


# ---------------------------------------------------------------------------
# Module is safe to import anywhere; _() triggers lazy init on first call.
# ---------------------------------------------------------------------------
