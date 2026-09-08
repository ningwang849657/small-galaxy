#!/usr/bin/env python3
"""读取 lab_tracker.py 生成的空闲时间日志，汇总某一天或最近 7 天的科研时间报告。"""
import argparse
import csv
import datetime
from pathlib import Path

LOG_DIR = Path.home() / ".lab_tracker" / "logs"
DEFAULT_THRESHOLD_SECONDS = 300

# 娱乐时间识别：前台窗口标题里含这些关键词的时间，从"有效科研"里单拆成"娱乐"。
# 用户可以在 ~/.lab_tracker/fun_keywords.txt 里自定义（每行一个，# 开头是注释）。
FUN_KEYWORDS_PATH = Path.home() / ".lab_tracker" / "fun_keywords.txt"
DEFAULT_FUN_KEYWORDS = ["bilibili", "哔哩哔哩", "youtube"]
# 相邻两次采样间隔理论上是 60 秒；给娱乐分钟归因设一个上限，
# 防止守护进程中断很久之后的一条娱乐采样把整段空窗都算成娱乐。
FUN_INTERVAL_CAP_SECONDS = 180


def load_fun_keywords():
    if FUN_KEYWORDS_PATH.exists():
        keywords = []
        for line in FUN_KEYWORDS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                keywords.append(line.lower())
        if keywords:
            return keywords
    return [k.lower() for k in DEFAULT_FUN_KEYWORDS]


def is_fun_title(title: str, keywords) -> bool:
    t = (title or "").lower()
    return any(k in t for k in keywords)


def load_records(date: datetime.date):
    path = LOG_DIR / f"{date.isoformat()}.csv"
    if not path.exists():
        return []
    records = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            try:
                ts = datetime.datetime.fromisoformat(row["timestamp"])
                idle = float(row["idle_seconds"])
            except (KeyError, ValueError, TypeError):
                continue  # 跳过写入过程中可能出现的损坏行
            records.append((ts, idle, row.get("window_title") or ""))
    return records


def build_day_segments(records, threshold: float):
    """核心统计逻辑，返回按时间顺序首尾相连、覆盖 [到达, 离开] 的分段列表：
    [{"start": datetime, "end": datetime, "kind": "active"|"fun"|"idle"}, ...]
    "fun" 表示人在电脑前、但前台窗口是娱乐网站（bilibili/YouTube 等）的时间。
    没有检测到当天真实操作时返回空列表。

    每条采样记录 (ts, idle) 都隐含了一个更有信息量的事实：
    最近一次真实操作发生在 `ts - idle` 这个时刻。把这个"真实操作时间"
    反推出来（而不是直接相信采样记录本身的时间戳），有两个好处：

    1. 到达/离开时间不再受"电脑整天/整夜开着但人已经不在"影响——
       比如昨晚忘记关机，今天日志文件的第一行可能是 00:00:xx，但那一刻
       的空闲秒数已经累积了一整夜，反推出的"最近操作时间"其实还是昨天，
       会被排除在"今天"之外，直到反推出的时间真正落在今天为止，这才是
       用户实际到达的那一刻。离开时间同理：哪怕电脑一直开到半夜，只要
       之后没有任何操作，反推出的时间也不会晚于用户最后一次真正碰键盘/
       鼠标的时刻。
    2. "有效科研时间"改成对相邻两次真实操作时间的间隔做判定：间隔在阈值
       以内的部分算作专注间隙的宽限期（哪怕中途完全没碰电脑），超出阈值
       的部分才算中断。这比"逐个采样点二选一"更精确，采样噪声会自然抵消
       （因为 ts 和 idle 都基于同一个墙钟时间，两者相减时噪声互相抵消）。
    """
    if not records:
        return []

    activity = [ts - datetime.timedelta(seconds=idle) for ts, idle, _ in records]
    today_activity = sorted(
        la for la, (ts, _, _) in zip(activity, records) if la.date() == ts.date()
    )
    if not today_activity:
        return []

    raw = []
    for prev, curr in zip(today_activity, today_activity[1:]):
        gap = (curr - prev).total_seconds()
        if gap <= threshold:
            raw.append((prev, curr, "active"))
        else:
            grace_end = prev + datetime.timedelta(seconds=threshold)
            raw.append((prev, grace_end, "active"))
            raw.append((grace_end, curr, "idle"))

    if not raw:
        # 当天只有一次真实操作，到达 == 离开，没有可跨越的区间
        only = today_activity[0]
        return [{"start": only, "end": only, "kind": "active"}]

    segments = []
    for start, end, kind in raw:
        if segments and segments[-1]["kind"] == kind and segments[-1]["end"] == start:
            segments[-1]["end"] = end
        else:
            segments.append({"start": start, "end": end, "kind": kind})

    return _overlay_fun(segments, _collect_fun_intervals(records, threshold))


def _collect_fun_intervals(records, threshold: float):
    """找出"人在电脑前、前台窗口是娱乐网站"的时间区间（已合并、按时间排序）。
    每条娱乐采样认领它与上一条采样之间的区间（上限 FUN_INTERVAL_CAP_SECONDS）。
    idle <= threshold 的限制：挂机播放视频超过阈值的部分交给底层算法记为中断。
    """
    keywords = load_fun_keywords()
    intervals = []
    prev_ts = None
    for ts, idle, title in records:
        if prev_ts is not None and idle <= threshold and is_fun_title(title, keywords):
            start = max(prev_ts, ts - datetime.timedelta(seconds=FUN_INTERVAL_CAP_SECONDS))
            if start < ts:
                if intervals and start <= intervals[-1][1]:
                    intervals[-1] = (intervals[-1][0], max(intervals[-1][1], ts))
                else:
                    intervals.append((start, ts))
        prev_ts = ts
    return intervals


def _overlay_fun(segments, fun_intervals):
    """把娱乐区间叠加到基础分段上：只切分 "active" 段（娱乐 ∩ 中断仍算中断）。"""
    if not fun_intervals:
        return segments
    out = []
    for seg in segments:
        if seg["kind"] != "active":
            out.append(seg)
            continue
        cur, end = seg["start"], seg["end"]
        for fs, fe in fun_intervals:
            s, e = max(fs, cur), min(fe, end)
            if s >= e:
                continue
            if cur < s:
                out.append({"start": cur, "end": s, "kind": "active"})
            out.append({"start": s, "end": e, "kind": "fun"})
            cur = e
        if cur < end:
            out.append({"start": cur, "end": end, "kind": "active"})
        elif cur == end and seg["start"] == end:
            out.append(seg)  # 保留零长度的单次操作段
    merged = []
    for seg in out:
        if merged and merged[-1]["kind"] == seg["kind"] and merged[-1]["end"] == seg["start"]:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(dict(seg))
    return merged


def compute_stats(records, threshold: float):
    """在 build_day_segments 之上聚合出到达/离开/总在场/有效/摸鱼等汇总数字。"""
    if not records:
        return None

    segments = build_day_segments(records, threshold)
    if not segments:
        return {
            "no_real_activity": True,
            "sample_count": len(records),
        }

    arrival = segments[0]["start"]
    departure = segments[-1]["end"]
    total_presence = (departure - arrival).total_seconds()
    active_seconds = sum(
        (s["end"] - s["start"]).total_seconds() for s in segments if s["kind"] == "active"
    )
    fun_seconds = sum(
        (s["end"] - s["start"]).total_seconds() for s in segments if s["kind"] == "fun"
    )

    return {
        "arrival": arrival,
        "departure": departure,
        "total_presence": total_presence,
        "active_seconds": active_seconds,
        "fun_seconds": fun_seconds,
        "idle_seconds": total_presence - active_seconds - fun_seconds,
        "sample_count": len(records),
    }


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    return f"{hours}小时{minutes}分钟"


def build_day_report(date: datetime.date, threshold: float):
    """返回 (报告文本, stats字典或None)。文本部分同时供 CLI 和 GUI 复用。"""
    weekday_name = "周" + "一二三四五六日"[date.weekday()]
    stats = compute_stats(load_records(date), threshold)
    lines = [f"=== {date.isoformat()} ({weekday_name}) ==="]
    if stats is None:
        lines.append("  当天没有记录（可能未到实验室，或守护进程未运行）")
    elif stats.get("no_real_activity"):
        lines.append("  当天有采样记录，但没有检测到任何真实操作（电脑可能一直开着，但你没有来）")
    else:
        lines += [
            f"  到达时间: {stats['arrival'].strftime('%H:%M:%S')}",
            f"  离开时间: {stats['departure'].strftime('%H:%M:%S')}",
            f"  总在场时长: {format_duration(stats['total_presence'])}",
            f"  有效科研时间: {format_duration(stats['active_seconds'])}",
            f"  娱乐时长(bilibili等): {format_duration(stats['fun_seconds'])}",
            f"  摸鱼/中断时长: {format_duration(stats['idle_seconds'])}",
            f"  采样点数: {stats['sample_count']}",
        ]
    return "\n".join(lines), stats


def build_week_report(end_date: datetime.date, threshold: float) -> str:
    lines = [f"########## 最近 7 天周报（截至 {end_date.isoformat()}）##########", ""]
    total_presence = 0.0
    total_active = 0.0
    total_fun = 0.0
    days_with_data = 0
    for offset in range(6, -1, -1):
        text, stats = build_day_report(end_date - datetime.timedelta(days=offset), threshold)
        lines += [text, ""]
        if stats is not None and not stats.get("no_real_activity"):
            total_presence += stats["total_presence"]
            total_active += stats["active_seconds"]
            total_fun += stats["fun_seconds"]
            days_with_data += 1
    lines.append("========== 本周汇总 ==========")
    lines.append(f"  有记录天数: {days_with_data} 天")
    lines.append(f"  总在场时长: {format_duration(total_presence)}")
    lines.append(f"  总有效科研时间: {format_duration(total_active)}")
    lines.append(f"  总娱乐时长: {format_duration(total_fun)}")
    if days_with_data:
        lines.append(f"  日均有效科研时间: {format_duration(total_active / days_with_data)}")
    return "\n".join(lines)


def print_day_report(date: datetime.date, threshold: float):
    text, stats = build_day_report(date, threshold)
    print(text + "\n")
    return stats


def print_week_report(end_date: datetime.date, threshold: float) -> None:
    print(build_week_report(end_date, threshold))


def parse_args():
    parser = argparse.ArgumentParser(description="实验室科研时间统计报告")
    parser.add_argument("--date", type=str, default=None, help="查看指定日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--week", action="store_true", help="以 --date 为截止日，汇总最近 7 天生成周报")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD_SECONDS,
        help=f"判定“有效科研时间”的空闲阈值（秒），默认 {DEFAULT_THRESHOLD_SECONDS}",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    target_date = datetime.date.fromisoformat(args.date) if args.date else datetime.date.today()
    if args.week:
        print_week_report(target_date, args.threshold)
    else:
        print_day_report(target_date, args.threshold)


if __name__ == "__main__":
    main()
