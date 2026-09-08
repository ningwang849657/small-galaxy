#!/usr/bin/env python3
"""后台守护进程：每隔固定时间采样一次系统空闲秒数，写入按天分文件的 CSV 日志。"""
import csv
import datetime
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard import regenerate_dashboard_html
from probes import detect_probe, unsupported_message
from summary import FUN_KEYWORDS_PATH

LOG_DIR = Path.home() / ".lab_tracker" / "logs"
LOCK_PATH = Path.home() / ".lab_tracker" / "lab_tracker.lock"
SAMPLE_INTERVAL_SECONDS = 60
DASHBOARD_REFRESH_EVERY_N_SAMPLES = 5  # 每 5 次采样（5 分钟）后台重新生成一次仪表盘
CSV_HEADER = ["timestamp", "idle_seconds", "window_title"]


def lock_exclusively(lock_file) -> None:
    """给已打开的锁文件加一把非阻塞独占锁。POSIX 用 flock，Windows 用 msvcrt。
    两者都由内核在进程退出时自动释放，不会留下需要手动清理的"僵尸锁"。
    """
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)


def acquire_single_instance_lock():
    """保证同一时间只有一个采样进程在写日志，避免手动测试和后台服务同时跑导致数据错乱。"""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_file = LOCK_PATH.open("w")
    try:
        lock_exclusively(lock_file)
    except OSError:
        print(
            "已经有一个 lab_tracker.py 在运行了（可能是后台服务，也可能是另一个手动启动的实例），"
            "本次启动直接退出，避免两边同时写日志。",
            file=sys.stderr,
        )
        sys.exit(1)
    return lock_file  # 调用方需要持有这个引用，不能被垃圾回收，否则锁会被释放


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
    # 先确认这台机器上有能用的采样后端，再去抢锁：装不上就明确报错退出，
    # 而不是让服务"起来了但数字永远是 0"，那种失败最难排查。
    probe = detect_probe()
    if probe is None:
        raise SystemExit(unsupported_message())
    print(f"采样后端: {probe.label}", file=sys.stderr)
    if probe.note:
        print(f"注意: {probe.note}", file=sys.stderr)

    _lock_file = acquire_single_instance_lock()
    migrate_today_log_schema()
    seed_fun_keywords_file()
    consecutive_failures = 0
    sample_count = 0
    while True:
        now = datetime.datetime.now()
        idle = probe.idle_seconds()
        if idle is None:
            consecutive_failures += 1
            # 第一次失败立刻提示，之后每小时（60 次采样）提示一次，避免日志刷屏
            if consecutive_failures == 1 or consecutive_failures % 60 == 0:
                print(
                    f"[{now.isoformat(timespec='seconds')}] 警告: {probe.label} 后端暂时取不到空闲时间，"
                    "已跳过本次采样",
                    file=sys.stderr,
                )
        else:
            consecutive_failures = 0
            append_record(now, idle, probe.window_title())

        sample_count += 1
        if sample_count % DASHBOARD_REFRESH_EVERY_N_SAMPLES == 0:
            try:
                regenerate_dashboard_html()
            except Exception as exc:  # 仪表盘渲染的任何问题都不能影响采样主循环
                print(f"[{now.isoformat(timespec='seconds')}] 警告: 仪表盘生成失败: {exc}", file=sys.stderr)

        time.sleep(SAMPLE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
