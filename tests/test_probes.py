"""Per-platform sampling backends. Only X11 can run on this machine, so the rest
are driven with recorded command output — the parsing is what actually breaks."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from smallgalaxy import probes


class X11Tests(unittest.TestCase):
    def test_idle_milliseconds_become_seconds(self):
        with patch.object(probes, '_run', return_value='12345\n'):
            self.assertAlmostEqual(probes.X11Probe().idle_seconds(), 12.345)

    def test_unreadable_idle_is_none(self):
        for output in (None, '', 'not a number'):
            with patch.object(probes, '_run', return_value=output):
                self.assertIsNone(probes.X11Probe().idle_seconds())

    def test_title_prefers_utf8_name(self):
        replies = ['_NET_ACTIVE_WINDOW(WINDOW): window id # 0x3c00007\n',
                   '_NET_WM_NAME(UTF8_STRING) = "小银河 — 仪表盘"\nWM_NAME(STRING) = "fallback"\n']
        with patch.object(probes.shutil, 'which', return_value='/usr/bin/xprop'), \
             patch.object(probes, '_run', side_effect=replies):
            self.assertEqual(probes.X11Probe().window_title(), '小银河 — 仪表盘')

    def test_title_falls_back_to_wm_name(self):
        replies = ['_NET_ACTIVE_WINDOW(WINDOW): window id # 0x3c00007\n',
                   'WM_NAME(STRING) = "老窗口管理器"\n']
        with patch.object(probes.shutil, 'which', return_value='/usr/bin/xprop'), \
             patch.object(probes, '_run', side_effect=replies):
            self.assertEqual(probes.X11Probe().window_title(), '老窗口管理器')

    def test_no_focused_window_is_empty(self):
        with patch.object(probes.shutil, 'which', return_value='/usr/bin/xprop'), \
             patch.object(probes, '_run', return_value='_NET_ACTIVE_WINDOW(WINDOW): window id # 0x0\n'):
            self.assertEqual(probes.X11Probe().window_title(), '')

    def test_long_titles_are_truncated(self):
        replies = ['window id # 0x1\n', '_NET_WM_NAME(UTF8_STRING) = "' + 'x' * 500 + '"\n']
        with patch.object(probes.shutil, 'which', return_value='/usr/bin/xprop'), \
             patch.object(probes, '_run', side_effect=replies):
            self.assertEqual(len(probes.X11Probe().window_title()), probes.TITLE_MAX_LEN)


class WaylandTests(unittest.TestCase):
    def test_mutter_reports_milliseconds(self):
        with patch.object(probes.shutil, 'which', return_value='/usr/bin/gdbus'), \
             patch.object(probes, '_run', return_value='(uint64 90000,)\n'):
            self.assertAlmostEqual(probes.GnomeWaylandProbe().idle_seconds(), 90.0)

    def test_screensaver_reports_seconds(self):
        with patch.object(probes.shutil, 'which', return_value='/usr/bin/gdbus'), \
             patch.object(probes, '_run', return_value='(uint32 42,)\n'):
            self.assertAlmostEqual(probes.ScreenSaverProbe().idle_seconds(), 42.0)

    def test_missing_gdbus_is_none(self):
        with patch.object(probes.shutil, 'which', return_value=None):
            self.assertIsNone(probes.GnomeWaylandProbe().idle_seconds())

    def test_wayland_backends_declare_no_title_support(self):
        for probe in (probes.GnomeWaylandProbe(), probes.ScreenSaverProbe()):
            self.assertEqual(probe.window_title(), '')
            self.assertFalse(probe.title_support)
            self.assertIn('娱乐', probe.note)


class MacTests(unittest.TestCase):
    IOREG = '  | |   "HIDIdleTime" = 4500000000\n  | |   "EventFlags" = 256\n'

    def test_nanoseconds_become_seconds(self):
        with patch.object(probes, '_run', return_value=self.IOREG):
            self.assertAlmostEqual(probes.MacProbe().idle_seconds(), 4.5)

    def test_missing_key_is_none(self):
        with patch.object(probes, '_run', return_value='no idle key here'):
            self.assertIsNone(probes.MacProbe().idle_seconds())

    def test_title_is_trimmed(self):
        with patch.object(probes, '_run', return_value='  bilibili — Google Chrome  \n'):
            self.assertEqual(probes.MacProbe().window_title(), 'bilibili — Google Chrome')


class WindowsTests(unittest.TestCase):
    """ctypes.windll does not exist off Windows, so stand in a fake user32/kernel32."""

    def _fake_ctypes(self, tick, last_input, title='记事本'):
        fake = types.SimpleNamespace()
        fake.Structure = probes.ctypes.Structure
        fake.c_uint = probes.ctypes.c_uint
        fake.sizeof = probes.ctypes.sizeof
        fake.byref = probes.ctypes.byref
        fake.create_unicode_buffer = probes.ctypes.create_unicode_buffer

        def get_last_input_info(ref):
            ref._obj.dwTime = last_input
            return 1

        def get_window_text(handle, buffer, size):
            buffer.value = title
            return len(title)

        fake.windll = types.SimpleNamespace(
            user32=types.SimpleNamespace(
                GetLastInputInfo=get_last_input_info,
                GetForegroundWindow=lambda: 4242,
                GetWindowTextLengthW=lambda handle: len(title),
                GetWindowTextW=get_window_text),
            kernel32=types.SimpleNamespace(GetTickCount=lambda: tick))
        return fake

    def test_idle_from_tick_difference(self):
        with patch.object(probes, 'ctypes', self._fake_ctypes(tick=50_000, last_input=44_000)):
            self.assertAlmostEqual(probes.WindowsProbe().idle_seconds(), 6.0)

    def test_tick_count_wraparound_stays_positive(self):
        # GetTickCount is 32-bit and wraps roughly every 49.7 days; a naive
        # subtraction would report a hugely negative idle time right after it wraps.
        with patch.object(probes, 'ctypes', self._fake_ctypes(tick=100, last_input=2 ** 32 - 900)):
            self.assertAlmostEqual(probes.WindowsProbe().idle_seconds(), 1.0)

    def test_foreground_window_title(self):
        with patch.object(probes, 'ctypes', self._fake_ctypes(tick=1, last_input=0, title='bilibili')):
            self.assertEqual(probes.WindowsProbe().window_title(), 'bilibili')

    def test_no_windll_is_handled(self):
        bare = types.SimpleNamespace(Structure=probes.ctypes.Structure, c_uint=probes.ctypes.c_uint)
        with patch.object(probes, 'ctypes', bare):
            self.assertIsNone(probes.WindowsProbe().idle_seconds())
            self.assertEqual(probes.WindowsProbe().window_title(), '')


class DetectionTests(unittest.TestCase):
    def test_picks_the_first_available_backend(self):
        class Never(probes.Probe):
            key = 'never'
            def available(self): return False

        class Always(probes.Probe):
            key = 'always'
            def available(self): return True

        with patch.object(probes, 'ALL_PROBES', (Never, Always)):
            self.assertEqual(probes.detect_probe().key, 'always')

    def test_a_probe_that_raises_never_blocks_detection(self):
        class Explodes(probes.Probe):
            def available(self): raise RuntimeError('boom')

        class Fine(probes.Probe):
            key = 'fine'
            def available(self): return True

        with patch.object(probes, 'ALL_PROBES', (Explodes, Fine)):
            self.assertEqual(probes.detect_probe().key, 'fine')

    def test_no_backend_returns_none_with_advice(self):
        with patch.object(probes, 'ALL_PROBES', ()):
            self.assertIsNone(probes.detect_probe())
        self.assertTrue(probes.unsupported_message())

    def test_x11_is_tried_before_wayland(self):
        # Under XWayland both can answer, and X11 is the better one: it still reads titles.
        keys = [factory.key for factory in probes.ALL_PROBES]
        self.assertLess(keys.index('x11-ctypes'), keys.index('gnome-wayland'))
        self.assertLess(keys.index('x11'), keys.index('gnome-wayland'))

    def test_dependency_free_x11_is_preferred_over_xprintidle(self):
        # Whichever comes first decides whether a user has to apt install anything.
        keys = [factory.key for factory in probes.ALL_PROBES]
        self.assertLess(keys.index('x11-ctypes'), keys.index('x11'))

    def test_every_backend_declares_a_label(self):
        for factory in probes.ALL_PROBES:
            self.assertTrue(factory.key and factory.label, factory)


class XlibTests(unittest.TestCase):
    """The ctypes X11 backend is what removes the apt-install step, so it must be
    the one that actually answers on this machine."""

    def test_it_reads_idle_time_here(self):
        probe = probes.X11CtypesProbe()
        if not probe.available():
            self.skipTest('no X11 display')
        idle = probe.idle_seconds()
        self.assertIsInstance(idle, float)
        self.assertGreaterEqual(idle, 0)

    def test_it_is_the_backend_that_gets_picked(self):
        if not probes.X11CtypesProbe().available():
            self.skipTest('no X11 display')
        self.assertEqual(probes.detect_probe().key, 'x11-ctypes')

    def test_no_display_is_handled(self):
        with patch.object(probes.ctypes, 'CDLL', side_effect=OSError('no library')):
            probe = probes.X11CtypesProbe()
            self.assertIsNone(probe.idle_seconds())
            self.assertEqual(probe.window_title(), '')


class PortabilityTests(unittest.TestCase):
    """A platform-only module imported at the top of a file breaks the other platforms
    before a single line runs — fcntl does not exist on Windows, msvcrt does not exist
    anywhere else. Both must stay inside the function that needs them."""

    UNIX_ONLY = {'fcntl', 'termios', 'grp', 'pwd', 'posix'}
    WINDOWS_ONLY = {'msvcrt', 'winreg', '_winapi'}

    def test_no_platform_specific_module_is_imported_at_top_level(self):
        import ast
        root = Path(__file__).resolve().parents[1] / 'smallgalaxy'
        risky = self.UNIX_ONLY | self.WINDOWS_ONLY
        for path in sorted(root.glob('*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                names = ({alias.name.split('.')[0] for alias in node.names}
                         if isinstance(node, ast.Import) else {(node.module or '').split('.')[0]})
                for name in names & risky:
                    self.assertNotEqual(node.col_offset, 0,
                                        f'{path.name}:{node.lineno} imports {name} at module level')


if __name__ == '__main__':
    unittest.main()
