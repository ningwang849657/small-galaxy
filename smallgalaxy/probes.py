#!/usr/bin/env python3
"""每个平台取"系统空闲时间"和"前台窗口标题"的方式都不一样，全部关在这个文件里。

这一层之上（summary.py / dashboard.py / 整个界面）只认两个数字：空闲了多少秒、
前台窗口标题是什么，所以换平台不需要改任何统计或渲染代码。

窗口标题只用于把 bilibili / YouTube 这类时间单拆成"娱乐"，取不到就返回空串，
统计照常进行——所以拿不到标题的平台（Wayland）功能会降级，但不会不能用。
"""
import ctypes
import os
import platform
import re
import shutil
import subprocess
import sys

TITLE_MAX_LEN = 120
_RUN = {"capture_output": True, "text": True, "timeout": 5}


def _run(args):
    """跑一个外部命令，任何失败都返回 None，让调用方走降级路径。"""
    try:
        result = subprocess.run(args, check=True, **_RUN)
    except (subprocess.SubprocessError, OSError):
        return None
    return result.stdout


def _gdbus(dest, path, method):
    """调一次会话总线上的方法，返回返回值里的整数。

    gdbus 打印成 "(uint64 12345,)"：必须取收尾括号前面的那个数，
    直接找第一串数字会命中类型名里的 64 / 32。
    """
    if shutil.which("gdbus") is None:
        return None
    out = _run(["gdbus", "call", "--session", "--dest", dest, "--object-path", path, "--method", method])
    if out is None:
        return None
    found = re.search(r"(\d+)\s*,?\s*\)\s*$", out.strip())
    return int(found.group(1)) if found else None


class Probe:
    """一个平台后端。`available()` 为真才会被选中。"""

    key = ""
    label = ""
    title_support = True

    def available(self) -> bool:
        raise NotImplementedError

    def idle_seconds(self):
        """返回自上次真实输入以来的秒数；取不到返回 None（本次采样会被跳过）。"""
        raise NotImplementedError

    def window_title(self) -> str:
        return ""

    @property
    def note(self) -> str:
        return "" if self.title_support else "该平台无法读取窗口标题，娱乐时间不会被单独区分。"


class _XScreenSaverInfo(ctypes.Structure):
    _fields_ = [("window", ctypes.c_ulong), ("state", ctypes.c_int), ("kind", ctypes.c_int),
                ("til_or_since", ctypes.c_ulong), ("idle", ctypes.c_ulong), ("event_mask", ctypes.c_ulong)]


class X11CtypesProbe(Probe):
    """Linux + X11，直接用 ctypes 调 Xlib —— 不需要装 xprintidle / xprop。

    libX11 和 libXss 在任何跑 X11 的机器上都必然存在（X 客户端全靠它们），
    所以这条路让 Linux 也变成"下载即用"，不用先 apt install。
    """

    key, label = "x11-ctypes", "Linux / X11"
    _ANY_PROPERTY_TYPE = 0

    def __init__(self):
        self._display = None
        self._x11 = self._xss = None

    def _open(self):
        """打开并缓存一个 X 连接；失败返回 None（比如没有 DISPLAY）。"""
        if self._display is not None:
            return self._display
        try:
            self._x11 = ctypes.CDLL("libX11.so.6")
            self._xss = ctypes.CDLL("libXss.so.1")
        except OSError:
            return None
        self._x11.XOpenDisplay.restype = ctypes.c_void_p
        self._x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self._x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self._x11.XInternAtom.restype = ctypes.c_ulong
        self._x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self._x11.XGetWindowProperty.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_long, ctypes.c_long, ctypes.c_int,
            ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte))]
        self._x11.XFree.argtypes = [ctypes.c_void_p]
        self._xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(_XScreenSaverInfo)
        self._xss.XScreenSaverQueryInfo.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_XScreenSaverInfo)]
        display = self._x11.XOpenDisplay(None)
        if not display:
            return None
        self._display = ctypes.c_void_p(display)
        return self._display

    def available(self) -> bool:
        return self.idle_seconds() is not None

    def idle_seconds(self):
        display = self._open()
        if display is None:
            return None
        try:
            info = self._xss.XScreenSaverAllocInfo()
            if not info:
                return None
            try:
                root = self._x11.XDefaultRootWindow(display)
                if not self._xss.XScreenSaverQueryInfo(display, root, info):
                    return None
                return info.contents.idle / 1000
            finally:
                self._x11.XFree(info)
        except (OSError, AttributeError):
            return None

    def _property(self, window, atom_name, expected=None):
        """读一个窗口属性，返回 (bytes, 实际类型 atom)；读不到返回 (None, 0)。"""
        atom = self._x11.XInternAtom(self._display, atom_name, False)
        if not atom:
            return None, 0
        actual_type = ctypes.c_ulong()
        actual_format = ctypes.c_int()
        count = ctypes.c_ulong()
        remaining = ctypes.c_ulong()
        data = ctypes.POINTER(ctypes.c_ubyte)()
        status = self._x11.XGetWindowProperty(
            self._display, window, atom, 0, 1024, False,
            expected if expected is not None else self._ANY_PROPERTY_TYPE,
            ctypes.byref(actual_type), ctypes.byref(actual_format),
            ctypes.byref(count), ctypes.byref(remaining), ctypes.byref(data))
        if status != 0 or not data:
            return None, 0
        try:
            # Xlib 的坑：format 32 的属性在 64 位机上每项占一个 C long（8 字节），
            # 不是 4 字节。按 4 字节读会错位。
            width = ctypes.sizeof(ctypes.c_ulong) if actual_format.value == 32 else max(1, actual_format.value // 8)
            raw = bytes(bytearray(data[i] for i in range(count.value * width)))
            return raw, actual_type.value
        finally:
            self._x11.XFree(data)

    def window_title(self) -> str:
        display = self._open()
        if display is None:
            return ""
        try:
            root = self._x11.XDefaultRootWindow(display)
            raw, _ = self._property(root, b"_NET_ACTIVE_WINDOW")
            if not raw or len(raw) < 4:
                return ""
            window = int.from_bytes(raw[:ctypes.sizeof(ctypes.c_ulong)], sys.byteorder)
            if not window:
                return ""
            # _NET_WM_NAME 是 UTF-8，现代窗口管理器都设；WM_NAME 是 latin-1 的老退路。
            for name, encoding in ((b"_NET_WM_NAME", "utf-8"), (b"WM_NAME", "latin-1")):
                title, _ = self._property(window, name)
                if title:
                    return title.split(b"\x00")[0].decode(encoding, "replace")[:TITLE_MAX_LEN]
            return ""
        except (OSError, AttributeError, ValueError):
            return ""


class X11Probe(Probe):
    """Linux + X11 的退路：ctypes 那条走不通时，用 xprintidle / xprop 命令行工具。"""

    key, label = "x11", "Linux / X11 (xprintidle)"

    def available(self) -> bool:
        return bool(os.environ.get("DISPLAY")) and shutil.which("xprintidle") is not None

    def idle_seconds(self):
        out = _run(["xprintidle"])
        try:
            return int(out.strip()) / 1000
        except (AttributeError, ValueError):
            return None

    def window_title(self) -> str:
        if shutil.which("xprop") is None:
            return ""
        out = _run(["xprop", "-root", "_NET_ACTIVE_WINDOW"])
        if not out:
            return ""
        found = re.search(r"window id # (0x[0-9a-fA-F]+)", out)
        if not found or found.group(1) == "0x0":
            return ""
        detail = _run(["xprop", "-id", found.group(1), "_NET_WM_NAME", "WM_NAME"])
        if not detail:
            return ""
        for pattern in (r'_NET_WM_NAME\(UTF8_STRING\) = "(.*)"',
                        r'WM_NAME\((?:STRING|COMPOUND_TEXT)\) = "(.*)"'):
            match = re.search(pattern, detail)
            if match:
                return match.group(1)[:TITLE_MAX_LEN]
        return ""


class GnomeWaylandProbe(Probe):
    """GNOME Wayland：Mutter 的 IdleMonitor 走 D-Bus，返回毫秒。

    Wayland 故意不让普通程序读别的窗口的标题（这是安全设计，不是缺陷），
    GNOME 41 起 Shell.Eval 也已禁用，所以这里拿不到标题。
    """

    key, label, title_support = "gnome-wayland", "Linux / Wayland (GNOME)", False

    def available(self) -> bool:
        return self.idle_seconds() is not None

    def idle_seconds(self):
        value = _gdbus("org.gnome.Mutter.IdleMonitor",
                       "/org/gnome/Mutter/IdleMonitor/Core",
                       "org.gnome.Mutter.IdleMonitor.GetIdletime")
        return None if value is None else value / 1000


class ScreenSaverProbe(Probe):
    """KDE 等实现了 org.freedesktop.ScreenSaver 的桌面，返回秒。"""

    key, label, title_support = "freedesktop", "Linux / Wayland (freedesktop)", False

    def available(self) -> bool:
        return self.idle_seconds() is not None

    def idle_seconds(self):
        value = _gdbus("org.freedesktop.ScreenSaver",
                       "/org/freedesktop/ScreenSaver",
                       "org.freedesktop.ScreenSaver.GetSessionIdleTime")
        return None if value is None else float(value)


class WindowsProbe(Probe):
    """Windows：user32.GetLastInputInfo + GetForegroundWindow，纯 ctypes，无需装任何东西。"""

    key, label = "windows", "Windows"

    def available(self) -> bool:
        return os.name == "nt"

    def idle_seconds(self):
        try:
            user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32

            class LastInput(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

            info = LastInput()
            info.cbSize = ctypes.sizeof(info)
            if not user32.GetLastInputInfo(ctypes.byref(info)):
                return None
            # GetTickCount 是 32 位、约 49.7 天回绕；和 dwTime 同域相减再取模才不会算出负数。
            elapsed = (kernel32.GetTickCount() - info.dwTime) % (2 ** 32)
            return elapsed / 1000
        except (AttributeError, OSError):
            return None

    def window_title(self) -> str:
        try:
            user32 = ctypes.windll.user32
            handle = user32.GetForegroundWindow()
            if not handle:
                return ""
            length = user32.GetWindowTextLengthW(handle)
            if length <= 0:
                return ""
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(handle, buffer, length + 1)
            return buffer.value[:TITLE_MAX_LEN]
        except (AttributeError, OSError):
            return ""


class MacProbe(Probe):
    """macOS：ioreg 读 HIDIdleTime（纳秒）；标题优先用辅助功能，退回前台程序名。"""

    key, label = "macos", "macOS"
    # 取窗口标题要"辅助功能"授权；没授权时只拿得到程序名（Safari / Google Chrome），
    # 足以区分是不是浏览器，但认不出具体在看哪个网站。
    TITLE_SCRIPT = (
        'tell application "System Events"\n'
        ' set frontApp to first application process whose frontmost is true\n'
        ' try\n'
        '  return value of attribute "AXTitle" of window 1 of frontApp\n'
        ' on error\n'
        '  return name of frontApp\n'
        ' end try\n'
        'end tell'
    )

    def available(self) -> bool:
        return platform.system() == "Darwin" and self.idle_seconds() is not None

    def idle_seconds(self):
        out = _run(["ioreg", "-c", "IOHIDSystem", "-d", "1", "-w", "0"])
        if not out:
            return None
        found = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out)
        return int(found.group(1)) / 1_000_000_000 if found else None

    def window_title(self) -> str:
        out = _run(["osascript", "-e", self.TITLE_SCRIPT])
        return out.strip()[:TITLE_MAX_LEN] if out else ""


# 顺序即优先级：
#   1. ctypes 调 Xlib —— 零外部依赖，所以排最前；
#   2. xprintidle —— 上一条在某些老环境下失败时的退路；
#   3. Wayland 后端排在 X11 之后，因为 XWayland 会话下 X11 仍能读到窗口标题，功能更全。
ALL_PROBES = (X11CtypesProbe, X11Probe, GnomeWaylandProbe, ScreenSaverProbe, WindowsProbe, MacProbe)


def detect_probe():
    """挑一个当前系统上能用的后端；都不行返回 None。"""
    for factory in ALL_PROBES:
        probe = factory()
        try:
            if probe.available():
                return probe
        except Exception:                      # 探测本身绝不能让守护进程起不来
            continue
    return None


def unsupported_message() -> str:
    system = platform.system()
    session = os.environ.get("XDG_SESSION_TYPE", "")
    if system == "Linux" and session == "x11":
        return ("检测到 X11 会话，但连 libX11 / libXss 都加载不了，这很不寻常。"
                "退一步可以试试：sudo apt install xprintidle x11-utils")
    if system == "Linux":
        return ("没能取到系统空闲时间。Wayland 会话需要 GNOME 的 Mutter 或实现了 "
                "org.freedesktop.ScreenSaver 的桌面，并且要装 gdbus（glib2 自带）。")
    return f"当前系统（{system or '未知'}）暂时没有可用的采样后端。"


if __name__ == "__main__":
    chosen = detect_probe()
    if chosen is None:
        raise SystemExit(unsupported_message())
    print(f"后端: {chosen.label}")
    print(f"空闲: {chosen.idle_seconds():.1f} 秒")
    print(f"标题: {chosen.window_title()!r}")
    if chosen.note:
        print(f"注意: {chosen.note}")
