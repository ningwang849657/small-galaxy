#!/usr/bin/env python3
"""后台守护进程：每隔固定时间采样一次系统空闲秒数，写入按天分文件的 CSV 日志。"""
import csv
import datetime
import fcntl
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard import regenerate_dashboard_html
from summary import FUN_KEYWORDS_PATH

LOG_DIR = Path.home() / ".lab_tracker" / "logs"
LOCK_PATH = Path.home() / ".lab_tracker" / "lab_tracker.lock"
SAMPLE_INTERVAL_SECONDS = 60
DASHBOARD_REFRESH_EVERY_N_SAMPLES = 5  # 每 5 次采样（5 分钟）后台重新生成一次仪表盘
CSV_HEADER = ["timestamp", "idle_seconds", "window_title"]
TITLE_MAX_LEN = 120  # 窗口标题截断长度，够识别网站名，避免日志无限膨胀


def acquire_single_instance_lock():
    """保证同一时间只有一个采样进程在写日志，避免手动测试和 systemd 服务同时跑导致数据错乱。
    用 flock 而不是 PID 文件：进程崩溃或被 kill 时内核会自动释放锁，不会留下需要手动清理的"僵尸锁"。
    """
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_file = LOCK_PATH.open("w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(
            "已经有一个 lab_tracker.py 在运行了（可能是 systemd 服务，也可能是另一个手动启动的实例），"
            "本次启动直接退出，避免两边同时写日志。",
            file=sys.stderr,
        )
        sys.exit(1)
    return lock_file  # 调用方需要持有这个引用，不能被垃圾回收，否则锁会被释放


def get_idle_seconds():
    """调用 xprintidle 获取空闲毫秒数并转换为秒。命令不存在或调用失败时返回 None。"""
    if shutil.which("xprintidle") is None:
        return None
    try:
        result = subprocess.run(
            ["xprintidle"], capture_output=True, text=True, timeout=5, check=True
        )
        return int(result.stdout.strip()) / 1000
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def get_active_window_title() -> str:
    """取当前前台窗口的标题（用于识别娱乐网站）。取不到时返回空字符串，不影响采样。"""
    if shutil.which("xprop") is None:
        return ""
    try:
        out = subprocess.run(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout
        m = re.search(r"window id # (0x[0-9a-fA-F]+)", out)
        if not m or m.group(1) == "0x0":
            return ""
        out2 = subprocess.run(
            ["xprop", "-id", m.group(1), "_NET_WM_NAME", "WM_NAME"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout
        for pattern in (r'_NET_WM_NAME\(UTF8_STRING\) = "(.*)"', r'WM_NAME\((?:STRING|COMPOUND_TEXT)\) = "(.*)"'):
            m2 = re.search(pattern, out2)
            if m2:
                return m2.group(1)[:TITLE_MAX_LEN]
        return ""
    except (subprocess.SubprocessError, OSError):
        return ""


def migrate_today_log_schema() -> None:
    """启动时把今天已存在的老格式日志（两列）原地升级为三列，补空标题。
    只处理今天的文件：历史文件读取端天然兼容（缺列按空标题处理），不需要动。
    """
    path = LOG_DIR / f"{datetime.date.today().isoformat()}.csv"
    if not path.exists():
        return
    with path.open(newline="") as f:
        rows = list(csv.reader(f))
    if not rows or "window_title" in rows[0]:
        return
    rows[0] = CSV_HEADER
    for row in rows[1:]:
        while len(row) < len(CSV_HEADER):
            row.append("")
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as f:
        csv.writer(f).writerows(rows)
    tmp.replace(path)


def seed_fun_keywords_file() -> None:
    """首次运行时生成默认的娱乐关键词文件，方便用户直接编辑自定义。"""
    if FUN_KEYWORDS_PATH.exists():
        return
    FUN_KEYWORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FUN_KEYWORDS_PATH.write_text(
        "# 娱乐网站关键词：每行一个，忽略大小写，前台窗口标题里含有它就把这段时间计为娱乐\n"
        "# 以 # 开头的行是注释；改完保存，下次生成报告/仪表盘时生效，不用重启服务\n"
        "bilibili\n"
        "哔哩哔哩\n"
        "youtube\n",
        encoding="utf-8",
    )


def append_record(timestamp: datetime.datetime, idle_seconds: float, window_title: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{timestamp.date().isoformat()}.csv"
    is_new_file = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(CSV_HEADER)
        writer.writerow([timestamp.isoformat(timespec="seconds"), f"{idle_seconds:.1f}", window_title])


def main() -> None:
    _lock_file = acquire_single_instance_lock()
    migrate_today_log_schema()
    seed_fun_keywords_file()
    consecutive_failures = 0
    sample_count = 0
    while True:
        now = datetime.datetime.now()
        idle = get_idle_seconds()
        if idle is None:
            consecutive_failures += 1
            # 第一次失败立刻提示，之后每小时（60 次采样）提示一次，避免日志刷屏
            if consecutive_failures == 1 or consecutive_failures % 60 == 0:
                print(
                    f"[{now.isoformat(timespec='seconds')}] 警告: 无法获取空闲时间，"
                    "已跳过本次采样（请检查 xprintidle 是否已安装，以及 DISPLAY 是否可用）",
                    file=sys.stderr,
                )
        else:
            consecutive_failures = 0
            append_record(now, idle, get_active_window_title())

        sample_count += 1
        if sample_count % DASHBOARD_REFRESH_EVERY_N_SAMPLES == 0:
            try:
                regenerate_dashboard_html()
            except Exception as exc:  # 仪表盘渲染的任何问题都不能影响采样主循环
                print(f"[{now.isoformat(timespec='seconds')}] 警告: 仪表盘生成失败: {exc}", file=sys.stderr)

        time.sleep(SAMPLE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
