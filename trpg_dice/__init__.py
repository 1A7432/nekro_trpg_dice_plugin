"""
TRPG Dice Plugin for Nekro Agent

A comprehensive TRPG dice system supporting multiple game systems,
character management, document storage, and AI-powered game mastering.

Author: Dirac
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "Dirac"
__description__ = "Comprehensive TRPG dice and game management system"

__all__ = ["plugin"]


def __getattr__(name: str):
    if name == "plugin":
        from .plugin import plugin
        return plugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
