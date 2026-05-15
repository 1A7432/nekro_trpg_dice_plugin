import json
import unittest

from trpg_dice.core.battle_report import BattleReportManager, SessionRecord
from trpg_dice.core.character_manager import CharacterManager, CharacterSheet
from trpg_dice.core.dice_engine import DiceResult
from trpg_dice.core.game_clock import advance_game_time
from trpg_dice.core.prompt_injection import _summarize_knowledge_item


class FakeStore:
    def __init__(self):
        self.data = {}

    def _key(self, user_key="", store_key=""):
        return user_key or "", store_key

    async def get(self, user_key="", store_key=""):
        return self.data.get(self._key(user_key, store_key))

    async def set(self, user_key="", store_key="", value=None):
        self.data[self._key(user_key, store_key)] = value

    async def delete(self, user_key="", store_key=""):
        self.data.pop(self._key(user_key, store_key), None)


class CoreFixTests(unittest.TestCase):
    def test_dice_result_d20_and_d100_critical_semantics(self):
        self.assertTrue(DiceResult("1d20", [20], dice_sides=20, is_check=True).is_critical_success())
        self.assertTrue(DiceResult("1d20", [1], dice_sides=20, is_check=True).is_critical_failure())

        self.assertTrue(DiceResult("1d100", [1], dice_sides=100, is_check=True).is_critical_success())
        self.assertTrue(DiceResult("1d100", [100], dice_sides=100, is_check=True).is_critical_failure())
        self.assertFalse(DiceResult("1d100", [100], dice_sides=100, is_check=True).is_critical_success())
        self.assertFalse(DiceResult("1d100", [1], dice_sides=100, is_check=True).is_critical_failure())

    def test_session_record_tracks_critical_failure_separately(self):
        record = SessionRecord("session-test")

        record.add_dice_roll("u1", "Alice", "1d20", 20, True, "success")
        record.add_dice_roll("u1", "Alice", "1d20", 1, True, "failure")

        stats = record.player_stats["u1"]
        self.assertEqual(stats["critical_success"], 1)
        self.assertEqual(stats["critical_failure"], 1)

    def test_dnd_skill_modifier_maps_chinese_ability_names(self):
        """Verify Chinese ability names are correctly mapped in get_dnd_skill_modifier."""
        store = FakeStore()
        manager = CharacterManager(store)
        character = CharacterSheet("战士", "DnD5e")
        character.attributes["STR"] = 14  # modifier = +2
        character.attributes["DEX"] = 12  # modifier = +1

        # Standard skill names
        self.assertEqual(manager.get_dnd_skill_modifier(character, "运动"), 2)
        self.assertEqual(manager.get_dnd_skill_modifier(character, "体操"), 1)

        # Chinese ability names used as skill input should map correctly
        self.assertEqual(manager.get_dnd_skill_modifier(character, "力量"), 2)
        self.assertEqual(manager.get_dnd_skill_modifier(character, "敏捷"), 1)

        # Proficiency bonus at level 1 = +2
        self.assertEqual(manager.get_dnd_skill_modifier(character, "运动", proficient=True), 4)
        self.assertEqual(manager.get_dnd_skill_modifier(character, "力量", proficient=True), 4)

    def test_dnd_skill_modifier_unknown_skill_defaults_to_str(self):
        store = FakeStore()
        manager = CharacterManager(store)
        character = CharacterSheet("战士", "DnD5e")
        character.attributes["STR"] = 10  # modifier = 0

        self.assertEqual(manager.get_dnd_skill_modifier(character, "不存在的技能"), 0)


class AsyncCoreFixTests(unittest.IsolatedAsyncioTestCase):
    async def test_battle_report_preserves_custom_session_name_after_end(self):
        store = FakeStore()
        manager = BattleReportManager(store)
        chat_key = "chat-a"

        await manager.start_session(chat_key, "深海古城")
        record = await manager.generator.get_current_session(chat_key)
        self.assertIsNotNone(record)
        assert record is not None
        record.add_key_event("发现入口")
        await manager.generator.save_session(chat_key, record)

        _, _, session_name = await manager.generate_battle_report(chat_key)

        self.assertEqual(session_name, "深海古城")
        self.assertIsNone(await store.get(store_key=f"session_name.{chat_key}.current"))

    async def test_sync_party_roster_preserves_status_effects_without_explicit_update(self):
        store = FakeStore()
        manager = CharacterManager(store)
        character = CharacterSheet("调查员", "CoC")

        await manager.sync_party_roster("chat-a", character, status_effects=["中毒"])
        await manager.sync_party_roster("chat-a", character)

        roster_data = await store.get(user_key="", store_key="party_roster.chat-a")
        self.assertIsNotNone(roster_data)
        assert roster_data is not None
        roster = json.loads(roster_data)
        self.assertEqual(roster["调查员"]["status_effects"], ["中毒"])

    def test_summarize_knowledge_item_supports_initializer_shapes(self):
        scene = {"name": "大厅", "description": "潮湿阴冷", "focus": "探索"}
        timeline = {"time": "午夜", "event": "钟声响起"}
        truth = {"name": "真相", "description": "管家是邪教徒", "revealed_by": "账本"}

        self.assertEqual(_summarize_knowledge_item(scene), "- 大厅: 潮湿阴冷 (焦点: 探索)")
        self.assertEqual(_summarize_knowledge_item(timeline), "- 午夜: 钟声响起")
        self.assertEqual(_summarize_knowledge_item(truth), "- 真相: 管家是邪教徒")

    def test_advance_game_time_parses_chinese_and_english_units_with_fallback(self):
        self.assertEqual(advance_game_time("1926年3月15日 14:00", "+2小时"), ("1926年03月15日 16:00", True))
        self.assertEqual(advance_game_time("1926-03-15 14:00", "+1day"), ("1926年03月16日 14:00", True))
        self.assertEqual(advance_game_time("未设定", "+2小时"), ("未设定 → 推进 +2小时", False))
