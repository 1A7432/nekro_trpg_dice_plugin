"""
TRPG Core Modules

This package contains the core functionality modules for the TRPG system.
"""

from .dice_engine import DiceParser, DiceRoller, DiceResult
from .character_manager import CharacterManager, CharacterSheet, CharacterTemplate
from .prompt_injection import register_prompt_injections

__all__ = [
    "DiceParser",
    "DiceRoller",
    "DiceResult",
    "CharacterManager",
    "CharacterSheet",
    "CharacterTemplate",
    "register_prompt_injections"
]


def __getattr__(name: str):
    if name in {"VectorDatabaseManager", "DocumentProcessor"}:
        from .document_manager import DocumentProcessor, VectorDatabaseManager
        return {"VectorDatabaseManager": VectorDatabaseManager, "DocumentProcessor": DocumentProcessor}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
