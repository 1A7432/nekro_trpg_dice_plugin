"""
TRPG Core Modules

This package contains the core functionality modules for the TRPG system.
"""

from .dice_engine import DiceParser, DiceRoller, DiceResult
from .character_manager import CharacterManager, CharacterSheet, CharacterTemplate
from .document_manager import VectorDatabaseManager, DocumentProcessor
from .prompt_injection import register_prompt_injections

__all__ = [
    "DiceParser",
    "DiceRoller",
    "DiceResult",
    "CharacterManager",
    "CharacterSheet",
    "CharacterTemplate",
    "VectorDatabaseManager",
    "DocumentProcessor",
    "register_prompt_injections"
]