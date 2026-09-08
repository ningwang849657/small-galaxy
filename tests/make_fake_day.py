#!/usr/bin/env python3
"""生成模拟的空闲时间日志，用于验证 summary.py 的计算逻辑，不依赖 xprintidle。

用法: python3 tests/make_fake_day.py
会在 ~/.lab_tracker/logs/ 下写入：
  2099-01-01 ~ 2099-01-07   一周的"正常"数据（用于验证周报），2099-01-04 故意留空模拟当天没到实验室
  2099-01-08                模拟"下班后忘记关机，电脑一直采样到快午夜"，验证离开时间不会被之后的空闲拖晚
  2099-01-09                模拟"昨晚忘记关机，今天一早电脑还带着隔夜的空闲"，验证到达时间不会被误判成 00:00 前后
使用明显不会和真实数据冲突的未来日期（2099年），可放心多次重复运行。
"""
import csv
import datetime
from pathlib import Path

LOG_DIR = Path.home() / ".lab_tracker" / "logs"
INTERVAL = 60  # 需与 lab_tracker.py 的采样间隔一致


def segment(start: datetime.datetime, end: datetime.datetime, pattern: str, start_idle: float = 0.0, title: str = ""):
    """按 INTERVAL 秒生成 [start, end) 之间的采样点。
    pattern == "active": 空闲秒数恒为 0（模拟持续操作电脑）。
    pattern == "away":   空闲秒数从 start_idle 开始每个采样点递增 INTERVAL 秒
                         （模拟停止操作、离开工位；start_idle 可以是 0，
                         也可以是一个很大的数，模拟"已经空闲了一整晚"）。
    title: 模拟采样时的前台窗口标题（用于测试娱乐时间识别）。
    """
    rows = []
    t = start
    idle = start_idle
    while t < end:
        idle = 0.0 if pattern == "active" else idle + INTERVAL
        rows.append((t, idle, title))
        t += datetime.timedelta(seconds=INTERVAL)
    return rows


def build_day(date: datetime.date, day_plan):
    rows = []
    for entry in day_plan:
        start_t, end_t, pattern, *rest = entry
        start_idle = rest[0] if rest else 0.0
        title = rest[1] if len(rest) > 1 else ""
        start_dt = datetime.datetime.combine(date, start_t)
        end_dt = datetime.datetime.combine(date, end_t)
        rows.extend(segment(start_dt, end_dt, pattern, start_idle, title))
    return rows


def write_day(date: datetime.date, rows) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{date.isoformat()}.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "idle_seconds", "window_title"])
        for ts, idle, title in rows:
            writer.writerow([ts.isoformat(timespec="seconds"), f"{idle:.1f}", title])
    print(f"写入 {path} ({len(rows)} 条记录)")


def main() -> None:
    t = datetime.time

    # 典型一天：9:00-17:00，中午 12:00-13:30 午休/开会，15:00-15:10 短暂离开
    typical_day = [
        (t(9, 0), t(12, 0), "active"),
        (t(12, 0), t(13, 30), "away"),
        (t(13, 30), t(15, 0), "active"),
        (t(15, 0), t(15, 10), "away"),
        (t(15, 10), t(17, 0), "active"),
        (t(17, 0), t(17, 0, 1), "active"),  # 补一个采样点，作为当天的"离开时间"
    ]
    for day_num in range(1, 8):
        date = datetime.date(2099, 1, day_num)
        if day_num == 4:
            print(f"跳过 {date.isoformat()}（模拟当天未到实验室，不生成数据）")
            continue
        write_day(date, build_day(date, typical_day))

    # 2099-01-08：正常工作到 17:00，之后忘记关机，电脑一直采样到 23:59
    # 用于验证：离开时间应该停在最后一次真实操作（17:00），不会被之后的空闲拖到快午夜
    forgot_to_shutdown = [
        (t(9, 0), t(12, 0), "active"),
        (t(12, 0), t(13, 30), "away"),
        (t(13, 30), t(17, 0), "active"),
        (t(17, 0), t(23, 59), "away"),
    ]
    write_day(datetime.date(2099, 1, 8), build_day(datetime.date(2099, 1, 8), forgot_to_shutdown))

    # 2099-01-09：昨晚就忘记关机，今天凌晨到早上 9:15 之前电脑一直带着隔夜空闲，
    # 9:15 才真正有人开始操作。用于验证：到达时间应该是 9:15，而不是 00:00 前后。
    overnight_carryover = [
        (t(0, 0), t(9, 15), "away", 40000.0),  # 40000 秒 ≈ 11 小时的隔夜空闲
        (t(9, 15), t(17, 0), "active"),
    ]
    write_day(datetime.date(2099, 1, 9), build_day(datetime.date(2099, 1, 9), overnight_carryover))

    # 2099-01-10：全天在电脑前，但中午 12:00-12:30 前台窗口是 bilibili（一直在滚动/点击，
    # 空闲秒数为 0）。用于验证：这 30 分钟应被单独归为"娱乐"，而不是有效科研时间。
    fun_day = [
        (t(9, 0), t(12, 0), "active", 0.0, "chapter3.tex - Overleaf - Google Chrome"),
        (t(12, 0), t(12, 30), "active", 0.0, "【放松一下】搞笑合集_哔哩哔哩_bilibili - Google Chrome"),
        (t(12, 30), t(17, 0), "active", 0.0, "chapter3.tex - Overleaf - Google Chrome"),
        (t(17, 0), t(17, 0, 1), "active", 0.0, "chapter3.tex - Overleaf - Google Chrome"),
    ]
    write_day(datetime.date(2099, 1, 10), build_day(datetime.date(2099, 1, 10), fun_day))


if __name__ == "__main__":
    main()
