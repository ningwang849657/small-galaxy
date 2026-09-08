"""Rendering regressions; fixtures never touch the real activity logs."""
import datetime
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dashboard


class DashboardTests(unittest.TestCase):
    def test_missing_day(self):
        with patch.object(dashboard, 'load_records', return_value=[]):
            day = dashboard.build_day_payload(datetime.date(2026, 9, 8), 300)
        self.assertFalse(day['has_data'])
        self.assertEqual(day['segments'], [])
        self.assertEqual(day['active_seconds'], 0)

    def test_self_contained_and_safe(self):
        html = dashboard.render_html({'days': [], 'probe': '</script><script>alert(1)</script>'})
        self.assertNotIn('</script><script>alert(1)', html)
        self.assertIn('\\u003c/script>', html)
        self.assertIn('ONE DAY AT A TIME', html)
        self.assertNotIn('http-equiv="refresh"', html)
        self.assertNotIn('<script src=', html)
        self.assertNotIn('__DASHBOARD_DATA__', html)
        # 装饰画和头像都必须随页面一起生成，页面加载时不能再去取任何外部资源。
        self.assertIn('buildRainforest', html)
        self.assertNotIn('src="http', html)
        self.assertNotIn('url(http', html)

    def test_avatar_is_inlined(self):
        html = dashboard.render_html({'days': []})
        self.assertNotIn('__AVATAR_SRC__', html)
        self.assertNotIn('__GITHUB_USER__', html)
        self.assertIn(dashboard.GITHUB_USER, html)
        self.assertIn('data:image/jpeg;base64,', dashboard.avatar_data_uri())

    def test_avatar_missing_file_is_not_fatal(self):
        with patch.object(dashboard, 'AVATAR_PATH', Path('/nonexistent/avatar.jpg')):
            self.assertEqual(dashboard.avatar_data_uri(), '')
            self.assertNotIn('__AVATAR_SRC__', dashboard.render_html({'days': []}))


class ThemeContrastTests(unittest.TestCase):
    """Every page theme must stay readable; a new palette cannot quietly drop below WCAG AA."""

    CSS = (Path(__file__).resolve().parents[1] / 'dashboard.css').read_text(encoding='utf-8')
    LIGHT = ('light', 'warm', 'linen', 'mist', 'sky', 'dusk', 'blush')
    DARK = ('dark', 'ink', 'midnight', 'night', 'cocoa', 'wine')

    @staticmethod
    def _normalise(value: str) -> str:
        digits = value.lstrip('#')
        if len(digits) == 3:
            digits = ''.join(char * 2 for char in digits)
        return digits.lower()

    @classmethod
    def _block(cls, selector: str) -> dict:
        found = re.search(re.escape(selector) + r'\s*\{([^}]*)\}', cls.CSS)
        if not found:
            return {}
        pairs = re.findall(r'(--[a-z0-9-]+)\s*:\s*(#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))\b', found.group(1))
        return {name: cls._normalise(value) for name, value in pairs}

    @staticmethod
    def _relative_luminance(colour: str) -> float:
        channels = [int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    @classmethod
    def _contrast(cls, foreground: str, background: str) -> float:
        first, second = cls._relative_luminance(foreground), cls._relative_luminance(background)
        return (max(first, second) + 0.05) / (min(first, second) + 0.05)

    def test_every_theme_meets_wcag_aa(self):
        base, dark = self._block(':root'), self._block(':root[data-dark]')
        self.assertTrue(base and dark, 'theme variable blocks not found')
        for theme in self.LIGHT + self.DARK:
            own = {} if theme == 'light' else self._block(f':root[data-theme="{theme}"]')
            self.assertTrue(theme == 'light' or own, f'{theme} defines no colours')
            colours = {**base, **(dark if theme in self.DARK else {}), **own}
            surface, page = colours['--surface'], colours['--page']
            with self.subTest(theme=theme):
                # Body text aims at AAA; secondary and tertiary text must still clear AA.
                self.assertGreaterEqual(self._contrast(colours['--ink'], surface), 7.0)
                self.assertGreaterEqual(self._contrast(colours['--ink'], page), 7.0)
                self.assertGreaterEqual(self._contrast(colours['--ink-2'], surface), 4.5)
                self.assertGreaterEqual(self._contrast(colours['--ink-3'], surface), 4.5)

    def test_theme_list_matches_the_stylesheet(self):
        declared = set(re.findall(r':root\[data-theme="([a-z]+)"\]', self.CSS))
        listed = set(self.LIGHT + self.DARK)
        self.assertEqual(declared | {'light'}, listed, 'CSS themes and the tested list drifted apart')
        script = (Path(__file__).resolve().parents[1] / 'dashboard-personalization.js').read_text(encoding='utf-8')
        for theme in listed:
            self.assertIn(f"['{theme}'", script, f'{theme} is not offered in the settings menu')


if __name__ == '__main__':
    unittest.main()
