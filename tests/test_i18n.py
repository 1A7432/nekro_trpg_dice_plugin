"""
Tests for the i18n infrastructure.

Verifies:
- Default language is zh_CN
- Chinese output matches original msgid
- English output after switching language
- Missing translation graceful fallback
- set_language / get_current_language API
- t_prompt stub
"""

import os
import sys
import unittest

# Ensure the package root is on sys.path so "from trpg_dice.i18n import ..." works.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from trpg_dice.i18n import _, set_language, get_current_language, t_prompt


class I18nTests(unittest.TestCase):
    """Phase 1 i18n closed-loop tests."""

    def tearDown(self):
        """Reset to default language after every test."""
        set_language("zh_CN")

    # ------------------------------------------------------------------
    # Default language
    # ------------------------------------------------------------------

    def test_default_language_is_zh_cn(self):
        """Default language must be zh_CN for existing users."""
        self.assertEqual(get_current_language(), "zh_CN")

    def test_zh_cn_output_matches_original(self):
        """zh_CN is an identity translation: msgstr == msgid."""
        msg = _("✅ 知识池已增量更新")
        self.assertEqual(msg, "✅ 知识池已增量更新")

    def test_zh_cn_with_named_placeholder(self):
        """Named placeholders work identically under zh_CN."""
        msg = _('✅ 已启动模组知识池初始化（{count} 个分片），后台处理中...').format(count=42)
        self.assertEqual(msg, "✅ 已启动模组知识池初始化（42 个分片），后台处理中...")

    # ------------------------------------------------------------------
    # English switch
    # ------------------------------------------------------------------

    def test_switch_to_en_us(self):
        """Switching to en_US must change get_current_language."""
        set_language("en_US")
        self.assertEqual(get_current_language(), "en_US")

    def test_en_us_translated_output(self):
        """English translations must be returned when language is en_US."""
        set_language("en_US")
        msg = _("✅ 知识池已增量更新")
        self.assertEqual(msg, "✅ Knowledge pool updated incrementally.")

    def test_en_us_with_named_placeholder(self):
        """Named placeholders must work after switching to English."""
        set_language("en_US")
        msg = _('✅ 已启动模组知识池初始化（{count} 个分片），后台处理中...').format(count=7)
        self.assertEqual(
            msg,
            "✅ Module knowledge pool initialization started (7 chunks), processing in background...",
        )

    # ------------------------------------------------------------------
    # Missing-translation fallback
    # ------------------------------------------------------------------

    def test_missing_translation_falls_back_to_msgid(self):
        """If a msgid is absent from the .mo, _() must return the original string."""
        set_language("en_US")
        # This string is intentionally NOT in any .po file.
        unknown = _("这是一个没有翻译的测试字符串")
        self.assertEqual(unknown, "这是一个没有翻译的测试字符串")

    def test_unsupported_language_falls_back_to_msgid(self):
        """Switching to a language with no .mo must silently fall back."""
        set_language("ja_JP")
        msg = _("✅ 知识池已增量更新")
        # No ja_JP .mo exists, so gettext returns msgid unchanged.
        self.assertEqual(msg, "✅ 知识池已增量更新")

    # ------------------------------------------------------------------
    # API surface
    # ------------------------------------------------------------------

    def test_set_language_changes_current(self):
        """set_language must update the internal current-language state."""
        set_language("en_US")
        self.assertEqual(get_current_language(), "en_US")
        set_language("zh_CN")
        self.assertEqual(get_current_language(), "zh_CN")

    def test_t_prompt_stub_returns_key(self):
        """t_prompt is a Phase 3 stub and must return the key unchanged."""
        self.assertEqual(t_prompt("some_key"), "some_key")
        self.assertEqual(t_prompt("another_key", lang="en_US"), "another_key")

    def test_placeholder_consistency(self):
        """Placeholder names in msgstr must match msgid (or msgstr is empty)."""
        import re

        locale_dir = os.path.join(os.path.dirname(__file__), "..", "trpg_dice", "locale")
        placeholder_pattern = re.compile(r'\{(\w+)\}')

        def extract_strings(po_path):
            with open(po_path, "r", encoding="utf-8") as f:
                content = f.read()
            msgid_pattern = re.compile(r'msgid\s+((?:"[^"]*"\s*)+)')
            msgstr_pattern = re.compile(r'msgstr\s+((?:"[^"]*"\s*)+)')
            msgids = msgid_pattern.findall(content)
            msgstrs = msgstr_pattern.findall(content)

            def clean(s):
                return ''.join(re.findall(r'"([^"]*)"', s))

            return [clean(m) for m in msgids], [clean(m) for m in msgstrs]

        for lang in ["zh_CN", "en_US"]:
            po_path = os.path.join(locale_dir, lang, "LC_MESSAGES", "trpg_dice.po")
            msgids, msgstrs = extract_strings(po_path)
            for msgid, msgstr in zip(msgids, msgstrs):
                if not msgid:
                    continue
                if not msgstr:
                    continue
                msgid_ph = set(placeholder_pattern.findall(msgid))
                msgstr_ph = set(placeholder_pattern.findall(msgstr))
                self.assertEqual(
                    msgid_ph,
                    msgstr_ph,
                    f"{lang}: Placeholder mismatch for msgid {msgid!r}",
                )


if __name__ == "__main__":
    unittest.main()
