"""Rendering regressions; fixtures never touch the real activity logs."""
import datetime
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


if __name__ == '__main__':
    unittest.main()
