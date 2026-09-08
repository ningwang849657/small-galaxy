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


class X11Probe(Probe):
    """Linux + X11：xprintidle 取空闲，xprop 取前台窗口标题。"""

    key, label = "x11", "Linux / X11"

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


# X11 排在 Wayland 之前：XWayland 会话下 xprop 仍然能读到窗口标题，功能更全。
ALL_PROBES = (X11Probe, GnomeWaylandProbe, ScreenSaverProbe, WindowsProbe, MacProbe)


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
        return "检测到 X11 会话，但没有找到 xprintidle。请先安装：sudo apt install xprintidle"
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
