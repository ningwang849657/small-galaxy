#!/usr/bin/env python3
"""生成自包含仪表盘，通过本机页面服务打开，支持个性化与可选音乐。"""
import base64
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

from . import asset_dir
from .summary import DEFAULT_THRESHOLD_SECONDS, build_day_segments, load_records

DATA_DIR = Path.home() / ".lab_tracker"
DASHBOARD_PATH = DATA_DIR / "dashboard.html"
WINDOW_DAYS = 14
STALE_AFTER_SECONDS = 180
# 头像内嵌为 data URI，页面打开时不会向 github.com 发请求；换头像后重新下载这个文件即可。
GITHUB_USER = "ningwang849657"
AVATAR_PATH = asset_dir() / "icons" / "github-avatar.jpg"


def check_daemon_status() -> str:
    """按"最近一条采样有多新"判断是否在记录。

    原来问的是 systemctl，但 macOS 用 launchd、Windows 用计划任务，都没有这个命令；
    而且"服务单元已加载"和"数据真的在进来"并不等价——后者才是用户关心的事。
    """
    newest = None
    today = datetime.date.today()
    for date in (today, today - datetime.timedelta(days=1)):
        records = load_records(date)
        if records:
            newest = max(newest or records[-1][0], records[-1][0])
    if newest is None:
        return "unknown"
    behind = (datetime.datetime.now() - newest).total_seconds()
    # 采样间隔 60 秒，留三倍余量：偶尔一次卡顿不该显示成"未在记录"。
    return "active" if behind <= STALE_AFTER_SECONDS else "inactive"


def daemon_command():
    """怎么把采样守护进程作为独立后台进程启动。

    AppImage 要特别处理：AppRun 是把系统 python3 加上 PYTHONPATH 跑起来的，
    而 AppImage 的挂载点在它自己的进程退出时就会被卸载。所以不能从这里直接
    起一个 python 子进程——父进程一退出，挂载没了，守护进程就读不到资源文件。
    必须重新起一个独立的 AppImage 进程，让它自己持有挂载。
    """
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        return [appimage, "--daemon"]
    if getattr(sys, "frozen", False):
        return [sys.executable, "--daemon"]
    return [sys.executable, "-m", "smallgalaxy.lab_tracker"]


def daemon_hint() -> str:
    """页面上要显示给用户的那条"手动启动"命令，按安装方式给对的写法。"""
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        return f"./{Path(appimage).name} --daemon"
    if shutil.which("small-galaxy-daemon"):
        return "small-galaxy-daemon"
    return "python3 -m smallgalaxy.lab_tracker"


def ensure_daemon() -> bool:
    """打开仪表盘时顺手把后台采样拉起来，返回是否真的起了一个新进程。

    不需要先判断有没有在跑：守护进程自带单实例文件锁，重复启动的那个会立刻退出。
    设 SMALL_GALAXY_NO_DAEMON=1 可以关掉这个行为。
    """
    if os.environ.get("SMALL_GALAXY_NO_DAEMON"):
        return False
    if check_daemon_status() == "active":
        return False
    quiet = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    # 脱离当前终端/浏览器进程，否则关掉它们会顺手杀死采样进程。
    if os.name == "nt":
        quiet["creationflags"] = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
    else:
        quiet["start_new_session"] = True
    # 子进程是全新的解释器，不会继承 sys.path。从源码目录直接跑时它找不到
    # smallgalaxy 包，会立刻 ModuleNotFoundError 退出——把包的位置显式传下去。
    env = os.environ.copy()
    package_root = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [package_root, env.get("PYTHONPATH")]))
    try:
        subprocess.Popen(daemon_command(), env=env, **quiet)
        return True
    except OSError:
        return False


def _seconds_since_midnight(dt: datetime.datetime) -> float:
    midnight = datetime.datetime.combine(dt.date(), datetime.time())
    return (dt - midnight).total_seconds()


def build_day_payload(date: datetime.date, threshold: float) -> dict:
    records = load_records(date)
    segments = build_day_segments(records, threshold)
    weekday_name = "周" + "一二三四五六日"[date.weekday()]
    payload = {
        "date": date.isoformat(),
        "weekday": weekday_name,
        "is_weekend": date.weekday() >= 5,
        "has_data": bool(records),
        "no_real_activity": bool(records) and not segments,
        "sample_count": len(records),
    }
    if not segments:
        payload.update(
            arrival=None,
            departure=None,
            total_presence_seconds=0,
            active_seconds=0,
            fun_seconds=0,
            idle_seconds=0,
            segments=[],
        )
        return payload

    arrival = segments[0]["start"]
    departure = segments[-1]["end"]
    active_seconds = sum(
        (s["end"] - s["start"]).total_seconds() for s in segments if s["kind"] == "active"
    )
    fun_seconds = sum(
        (s["end"] - s["start"]).total_seconds() for s in segments if s["kind"] == "fun"
    )
    total_presence = (departure - arrival).total_seconds()
    payload.update(
        arrival=arrival.strftime("%H:%M"),
        departure=departure.strftime("%H:%M"),
        total_presence_seconds=total_presence,
        active_seconds=active_seconds,
        fun_seconds=fun_seconds,
        idle_seconds=total_presence - active_seconds - fun_seconds,
        segments=[
            {
                "start_sec": _seconds_since_midnight(s["start"]),
                "end_sec": _seconds_since_midnight(s["end"]),
                "kind": s["kind"],
            }
            for s in segments
        ],
    )
    return payload


def build_dashboard_data(threshold: float = DEFAULT_THRESHOLD_SECONDS, window_days: int = WINDOW_DAYS,
                         daemon_started: bool = False) -> dict:
    today = datetime.date.today()
    days = [
        build_day_payload(today - datetime.timedelta(days=offset), threshold)
        for offset in range(window_days - 1, -1, -1)
    ]
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "threshold_seconds": threshold,
        "daemon_status": check_daemon_status(),
        # 首次打开时页面要能说清楚"现在该做什么"，这两项就是给它的。
        "daemon_started": daemon_started,
        "start_hint": daemon_hint(),
        "days": days,
    }


def avatar_data_uri() -> str:
    """本地头像文件转 data URI；文件缺失时返回空串，页面会跳过头像不报错。"""
    try:
        return "data:image/jpeg;base64," + base64.b64encode(AVATAR_PATH.read_bytes()).decode("ascii")
    except OSError:
        return ""


def render_html(data: dict) -> str:
    assets = asset_dir()
    html = _TEMPLATE.replace("__DASHBOARD_DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))
    html = html.replace('<meta http-equiv="refresh" content="60">', '')
    html = html.replace("摸鱼 / 中断", "空闲 / 中断").replace("中断 / 摸鱼", "空闲 / 中断")
    # base64 与用户名都只含 JS 字符串安全字符，直接替换不会破坏字面量。
    html = html.replace("__AVATAR_SRC__", avatar_data_uri()).replace("__GITHUB_USER__", GITHUB_USER)
    html = html.replace("</head>", "<style>" + (assets / "dashboard.css").read_text(encoding="utf-8") + "</style></head>")
    scripts = "".join("<script>" + (assets / name).read_text(encoding="utf-8") + "</script>"
                      for name in ("dashboard-enhancements.js", "dashboard-decor.js",
                                   "dashboard-personalization.js", "dashboard-scenes.js"))
    for token, filename in (
        ('__RAINFOREST_ART__', 'rainforest-canyon.webp'),
        ('__DEER_ART__', 'forest-deer.webp'),
        ('__WOLF_ART__', 'white-wolf.webp'),
        ('__NIGHT_ART__', 'night-walker.webp'),
    ):
        try:
            source = 'data:image/webp;base64,' + base64.b64encode((assets / 'art' / filename).read_bytes()).decode('ascii')
        except OSError:
            source = ''  # The vector layer still works in a minimal install.
        scripts = scripts.replace(token, source)
    return html.replace("</body>", scripts + "</body>")


def regenerate_dashboard_html(threshold: float = DEFAULT_THRESHOLD_SECONDS,
                              daemon_started: bool = False) -> Path:
    data = build_dashboard_data(threshold, daemon_started=daemon_started)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Readers always see a complete generation, even during the five-minute update.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=DATA_DIR,
                                     prefix="dashboard-", suffix=".tmp", delete=False) as output:
        output.write(render_html(data))
        temporary = Path(output.name)
    temporary.replace(DASHBOARD_PATH)
    return DASHBOARD_PATH


_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>小银河</title>
<style>
  :root {
    --page:        #F6F0E3;
    --surface:     #FDFAF2;
    --surface-2:   #33291B;   /* 提示框：深暖棕，页面上唯一的深色浮层 */
    --border:      rgba(92,72,40,0.15);
    --hairline:    rgba(92,72,40,0.10);
    --ink:         #33291D;
    --ink-2:       #6E6252;
    --ink-3:       #9B8B71;
    --active:      #3B72D9;
    --active-soft: rgba(59,114,217,0.12);
    --fun:         #B44E83;
    --idle:        #CFC3AC;
    --warm:        #A96A1C;
    --good:        #178A45;
    --bad:         #C24138;
    --gridline:    rgba(92,72,40,0.10);
    --baseline:    rgba(92,72,40,0.30);
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body {
    margin: 0;
    min-height: 100vh;
    background:
      radial-gradient(1100px 480px at 50% -160px, #FBE3BE 0%, rgba(251,227,190,0) 62%),
      var(--page);
    color: var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    padding: 30px 34px 40px;
    line-height: 1.45;
  }
  .wrap { max-width: 1000px; margin: 0 auto; position: relative; }

  /* ---------- 头部：星空 + 标题 + 状态 ---------- */
  #starfield {
    position: absolute; top: -30px; left: -34px; right: -34px; height: 190px;
    pointer-events: none; z-index: 0;
  }
  @media (prefers-reduced-motion: no-preference) {
    .twinkle { animation: twinkle 5.5s ease-in-out infinite; }
    @keyframes twinkle { 0%,100% { opacity: 0.10; } 50% { opacity: 0.40; } }
  }
  header {
    position: relative; z-index: 1;
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; margin-bottom: 26px; padding-top: 6px;
  }
  .brand { display: flex; align-items: center; gap: 13px; }
  .brand h1 { font-size: 21px; font-weight: 650; margin: 0; letter-spacing: 0.04em; }
  .brand .tagline { font-size: 12.5px; color: var(--ink-3); margin-top: 2px; letter-spacing: 0.02em; }

  .pill {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 6px 14px; border-radius: 999px;
    font-size: 12.5px; font-weight: 600; letter-spacing: 0.03em;
    border: 1px solid transparent; white-space: nowrap;
  }
  .pill .dot { width: 7px; height: 7px; border-radius: 50%; }
  .pill.on  { color: var(--good); background: rgba(23,138,69,0.09); border-color: rgba(23,138,69,0.28); }
  .pill.on .dot  { background: var(--good); box-shadow: 0 0 7px rgba(23,138,69,0.55); }
  .pill.off { color: var(--bad); background: rgba(194,65,56,0.08); border-color: rgba(194,65,56,0.28); }
  .pill.off .dot { background: var(--bad); }
  .pill.na  { color: var(--ink-3); background: rgba(92,72,40,0.06); border-color: var(--border); }
  .pill.na .dot  { background: var(--ink-3); }

  /* ---------- KPI 行 ---------- */
  .kpi-row {
    position: relative; z-index: 1;
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 18px;
  }
  .tile {
    background: var(--surface);
    border: 1px solid var(--border); border-radius: 14px;
    box-shadow: 0 1px 2px rgba(80,60,20,0.05), 0 6px 18px rgba(80,60,20,0.05);
    padding: 17px 20px 15px;
  }
  .tile .label { font-size: 12.5px; color: var(--ink-2); margin-bottom: 9px; letter-spacing: 0.01em; }
  .tile .value { font-weight: 650; line-height: 1; margin-bottom: 9px; font-size: 30px; }
  .tile .value .u { font-size: 14px; font-weight: 550; color: var(--ink-2); margin: 0 3px 0 2px; }
  .tile .sub { font-size: 12px; color: var(--ink-3); display: flex; align-items: center; gap: 6px; min-height: 30px; flex-wrap: wrap; }
  .delta { font-weight: 650; font-size: 12px; }
  .delta.up { color: var(--good); }
  .delta.down { color: var(--bad); }
  .delta.flat { color: var(--ink-3); font-weight: 500; }
  .spark { display: block; }

  /* ---------- 卡片 ---------- */
  .card {
    background: var(--surface);
    border: 1px solid var(--border); border-radius: 14px;
    box-shadow: 0 1px 2px rgba(80,60,20,0.05), 0 6px 18px rgba(80,60,20,0.05);
    padding: 19px 22px 16px; margin-bottom: 16px;
  }
  .card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 4px; }
  .card-head h2 { font-size: 14px; font-weight: 650; margin: 0; letter-spacing: 0.02em; }
  .card-head .hint { font-size: 12px; color: var(--ink-3); }

  .legend { display: flex; gap: 18px; align-items: center; font-size: 12px; color: var(--ink-2); margin: 8px 0 6px; }
  .legend .key { display: inline-flex; align-items: center; gap: 7px; }
  .legend .sw { width: 13px; height: 8px; border-radius: 2.5px; }
  .legend .sw.a { background: var(--active); }
  .legend .sw.f { background: var(--fun); }
  .legend .sw.i { background: var(--idle); }
  .legend .ln { width: 14px; height: 0; border-top: 2px solid var(--warm); opacity: 0.75; }

  svg.chart { display: block; width: 100%; height: auto; font-family: inherit; }
  .axis-label { fill: var(--ink-3); font-size: 11px; font-variant-numeric: tabular-nums; }
  .gridline { stroke: var(--gridline); stroke-width: 1; }
  .baseline { stroke: var(--baseline); stroke-width: 1; }

  .bar-group { cursor: pointer; outline: none; }
  .band-bg { fill: rgba(92,72,40,0.05); opacity: 0; rx: 8; }
  .bar-group:hover .band-bg { opacity: 1; }
  .bar-group.selected .band-bg { opacity: 1; fill: rgba(169,106,28,0.09); }
  .bar-group:focus-visible .band-bg { opacity: 1; stroke: var(--warm); stroke-width: 1; }
  .bar-a { fill: var(--active); }
  .bar-f { fill: var(--fun); }
  .bar-i { fill: var(--idle); }
  @media (prefers-reduced-motion: no-preference) {
    .bar-a, .bar-f, .bar-i { transition: filter 0.12s ease; }
  }
  .bar-group:hover .bar-a, .bar-group:hover .bar-f, .bar-group:hover .bar-i { filter: brightness(0.92); }
  .date-label { fill: var(--ink-3); font-size: 10.5px; font-variant-numeric: tabular-nums; }
  .date-label.today { fill: var(--warm); font-weight: 650; }
  .date-label.weekend { opacity: 0.62; }
  .bar-group.selected .date-label { fill: var(--ink); }
  .bar-group.selected .date-label.today { fill: var(--warm); }
  .sel-tick { fill: var(--warm); }
  .ref-line { stroke: var(--warm); stroke-width: 1; opacity: 0.55; }
  .ref-label { fill: var(--warm); font-size: 10.5px; opacity: 0.95; font-variant-numeric: tabular-nums; }

  /* 单日时间线 */
  .presence-bg { fill: rgba(92,72,40,0.07); }
  .seg-a { fill: var(--active); }
  .seg-f { fill: var(--fun); }
  .seg-i { fill: var(--idle); }
  .seg-hit { fill: transparent; cursor: pointer; }
  .seg-hit:hover + .seg-visual, .seg-visual.hover { filter: brightness(0.92); }
  .flag-label { fill: var(--ink-2); font-size: 11px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .flag-tick { stroke: var(--warm); stroke-width: 1.5; opacity: 0.85; }
  .minor-tick { stroke: rgba(92,72,40,0.22); stroke-width: 1; }

  #detail-stats { display: flex; flex-wrap: wrap; gap: 8px 30px; margin: 10px 0 14px; }
  #detail-stats .stat .k { display: block; font-size: 11px; color: var(--ink-3); margin-bottom: 2px; letter-spacing: 0.04em; }
  #detail-stats .stat .v { font-size: 15px; font-weight: 650; font-variant-numeric: tabular-nums; }
  .empty-note { font-size: 13px; color: var(--ink-3); padding: 22px 0 16px; text-align: center; }
  .empty-note::before { content: "✦"; color: var(--warm); opacity: 0.6; margin-right: 8px; }

  /* 提示框 */
  .tooltip {
    position: fixed; pointer-events: none; z-index: 20;
    background: var(--surface-2); color: #F7F0E2;
    border: 1px solid rgba(255,255,255,0.10); border-radius: 9px;
    box-shadow: 0 8px 28px rgba(60,42,15,0.35);
    font-size: 12px; line-height: 1.65; padding: 9px 12px;
    transform: translate(-50%, calc(-100% - 12px));
    opacity: 0; transition: opacity 0.1s; white-space: nowrap;
  }
  .tooltip.below { transform: translate(-50%, 14px); }
  .tooltip .tt-head { color: #C9B99C; font-size: 11.5px; margin-bottom: 3px; }
  .tooltip .tt-row { display: flex; align-items: center; gap: 7px; }
  .tooltip .tt-key { width: 10px; height: 3px; border-radius: 1.5px; flex: none; }
  .tooltip .tt-val { font-weight: 700; font-variant-numeric: tabular-nums; }
  .tooltip .tt-lbl { color: #C9B99C; }

  /* 表格 */
  details summary {
    cursor: pointer; font-size: 13px; color: var(--ink-2); user-select: none;
    list-style: none; display: flex; align-items: center; gap: 8px;
  }
  details summary::before { content: "▸"; color: var(--ink-3); transition: transform 0.15s; }
  details[open] summary::before { transform: rotate(90deg); }
  details summary::-webkit-details-marker { display: none; }
  table { width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 12.5px; }
  th, td { padding: 7px 10px; border-bottom: 1px solid var(--hairline); font-variant-numeric: tabular-nums; }
  th { color: var(--ink-3); font-weight: 550; text-align: left; font-size: 11.5px; letter-spacing: 0.04em; }
  td { color: var(--ink-2); }
  td:first-child { color: var(--ink); }
  th.num, td.num { text-align: right; }
  tbody tr:hover { background: rgba(92,72,40,0.045); }
  tr.today-row td:first-child { color: var(--warm); font-weight: 650; }
  tr.dim td { color: var(--ink-3); }

  footer {
    margin-top: 22px; padding-top: 14px; border-top: 1px solid var(--hairline);
    font-size: 12px; color: var(--ink-3); display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  }

  @media (max-width: 860px) {
    body { padding: 22px 18px 32px; }
    .kpi-row { grid-template-columns: 1fr; }
    #starfield { left: -18px; right: -18px; }
  }
</style>
</head>
<body>
<div class="wrap">
  <svg id="starfield" aria-hidden="true"></svg>

  <header>
    <div class="brand">
      <svg width="34" height="34" viewBox="0 0 128 128" aria-hidden="true">
        <defs>
          <linearGradient id="hm-bg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#181030"/><stop offset="100%" stop-color="#050308"/>
          </linearGradient>
          <linearGradient id="hm-b" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#5B8CFF" stop-opacity="0"/><stop offset="50%" stop-color="#8FA8FF" stop-opacity="0.95"/><stop offset="100%" stop-color="#B98CFF" stop-opacity="0"/>
          </linearGradient>
          <linearGradient id="hm-p" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#FF6FA8" stop-opacity="0"/><stop offset="50%" stop-color="#FFA0D2" stop-opacity="0.9"/><stop offset="100%" stop-color="#FFD37A" stop-opacity="0"/>
          </linearGradient>
          <radialGradient id="hm-c" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#FFFDF5"/><stop offset="35%" stop-color="#FFE9B8" stop-opacity="0.95"/><stop offset="100%" stop-color="#FFE9B8" stop-opacity="0"/>
          </radialGradient>
        </defs>
        <rect x="4" y="4" width="120" height="120" rx="30" fill="url(#hm-bg)"/>
        <ellipse cx="64" cy="64" rx="46" ry="15" fill="url(#hm-b)" transform="rotate(-30 64 64)"/>
        <ellipse cx="64" cy="64" rx="37" ry="11" fill="url(#hm-p)" transform="rotate(58 64 64)"/>
        <circle cx="64" cy="64" r="15" fill="url(#hm-c)"/>
        <circle cx="64" cy="64" r="4.2" fill="#FFFDF5"/>
      </svg>
      <div>
        <h1>小银河</h1>
        <div class="tagline">实验室科研时间 · 最近 14 天</div>
      </div>
    </div>
    <span class="pill na" id="status-pill"><span class="dot"></span><span id="status-text">…</span></span>
  </header>

  <div class="kpi-row">
    <div class="tile">
      <div class="label">今日有效科研时间</div>
      <div class="value" id="kpi-today">—</div>
      <div class="sub" id="kpi-today-sub"></div>
    </div>
    <div class="tile">
      <div class="label">近 7 天有效科研时间</div>
      <div class="value" id="kpi-week">—</div>
      <div class="sub" id="kpi-week-sub"></div>
    </div>
    <div class="tile">
      <div class="label">近 14 天日均有效时间</div>
      <div class="value" id="kpi-avg">—</div>
      <div class="sub" id="kpi-avg-sub"></div>
    </div>
  </div>

  <div class="card">
    <div class="card-head">
      <h2>每日时长</h2>
      <span class="hint">点柱子查看那天的明细</span>
    </div>
    <div class="legend">
      <span class="key"><span class="sw a"></span>有效科研</span>
      <span class="key"><span class="sw f"></span>娱乐</span>
      <span class="key"><span class="sw i"></span>摸鱼 / 中断</span>
      <span class="key"><span class="ln"></span>14 天日均</span>
    </div>
    <svg id="bar-chart" class="chart" viewBox="0 0 960 244" role="img" aria-label="最近 14 天每日有效科研时间与中断时长堆叠柱状图"></svg>
  </div>

  <div class="card">
    <div class="card-head">
      <h2 id="detail-title">—</h2>
      <span class="hint">悬停色块看每段起止时间</span>
    </div>
    <div id="detail-stats"></div>
    <svg id="timeline" class="chart" viewBox="0 0 960 92" role="img" aria-label="选中日期的 24 小时专注与中断时间线"></svg>
    <p class="empty-note" id="detail-empty" style="display:none;"></p>
  </div>

  <div class="card">
    <details>
      <summary>数据表格</summary>
      <table id="data-table">
        <thead><tr>
          <th>日期</th><th>到达</th><th>离开</th>
          <th class="num">总在场</th><th class="num">有效科研</th><th class="num">娱乐</th><th class="num">摸鱼 / 中断</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </details>
  </div>

  <footer>
    <span id="meta-line"></span>
    <span id="footer-note">✦ 小银河</span>
  </footer>
</div>

<div class="tooltip" id="tooltip"></div>

<script>
let DATA = __DASHBOARD_DATA__;
const AVATAR_SRC = "__AVATAR_SRC__";
const GITHUB_USER = "__GITHUB_USER__";
const NS = "http://www.w3.org/2000/svg";
let TODAY = DATA.days[DATA.days.length - 1];
let LABELS = {active:'有效科研', idle:'空闲 / 中断', fun:'娱乐', arrival:'到达', departure:'离开', presence:'总在场', manual:false};
const isValid = d => d.has_data && !d.no_real_activity;

/* ---------- 工具 ---------- */
function el(tag, attrs) {
  const node = document.createElementNS(NS, tag);
  for (const k in attrs) node.setAttribute(k, attrs[k]);
  return node;
}
function fmtDur(sec) {
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h > 0 ? h + "小时" + m + "分" : m + "分钟";
}
function setDurParts(node, sec) {
  node.textContent = "";
  if (sec == null) { node.textContent = "—"; return; }
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  const put = (n, u) => {
    node.appendChild(document.createTextNode(String(n)));
    const us = document.createElement("span"); us.className = "u"; us.textContent = u;
    node.appendChild(us);
  };
  if (h > 0) { put(h, "小时"); put(m, "分"); } else { put(m, "分钟"); }
}
function fmtClock(sec) {
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60);
  return String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
}
function shortDate(iso) { const p = iso.split("-"); return p[1] + "/" + p[2]; }
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

/* ---------- 提示框 ---------- */
const tooltip = document.getElementById("tooltip");
function ttRow(colorClass, val, lbl) {
  const row = document.createElement("div"); row.className = "tt-row";
  if (colorClass) {
    const key = document.createElement("span"); key.className = "tt-key";
    key.style.background = colorClass === "a" ? "var(--active)" : colorClass === "f" ? "var(--fun)" : colorClass === "i" ? "var(--idle)" : colorClass;
    row.appendChild(key);
  }
  const v = document.createElement("span"); v.className = "tt-val"; v.textContent = val;
  row.appendChild(v);
  if (lbl) { const l = document.createElement("span"); l.className = "tt-lbl"; l.textContent = lbl; row.appendChild(l); }
  return row;
}
function ttHead(text) {
  const h = document.createElement("div"); h.className = "tt-head"; h.textContent = text; return h;
}
function showTooltip(evt, nodes) {
  tooltip.textContent = "";
  nodes.forEach(n => tooltip.appendChild(n));
  const x = Math.min(Math.max(evt.clientX, 110), window.innerWidth - 110);
  tooltip.classList.toggle("below", evt.clientY < 150);
  tooltip.style.left = x + "px";
  tooltip.style.top = evt.clientY + "px";
  tooltip.style.opacity = 1;
}
function hideTooltip() { tooltip.style.opacity = 0; }

/* ---------- 头部星空（固定种子，自动刷新时星星不会跳动） ---------- */
(function renderStars() {
  const svg = document.getElementById("starfield");
  const rand = mulberry32(20990101);
  const W = 1100, H = 190;
  svg.setAttribute("viewBox", "0 0 " + W + " " + H);
  svg.setAttribute("preserveAspectRatio", "xMidYMin slice");
  // 暖色主题下星点换成琥珀/陶土色的"晨光微尘"，透明度压得很低
  for (let i = 0; i < 44; i++) {
    const x = rand() * W, y = rand() * H * (0.25 + 0.75 * rand());
    const r = rand() < 0.85 ? 0.9 + rand() * 0.8 : 1.7 + rand() * 0.9;
    const tint = rand();
    const fill = tint < 0.30 ? "#C98A3B" : tint < 0.45 ? "#CE8D6B" : "#A98F5F";
    const star = el("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: r.toFixed(2), fill, opacity: (0.08 + rand() * 0.20).toFixed(2) });
    if (rand() < 0.12) {
      star.classList.add("twinkle");
      star.style.animationDelay = (rand() * 5).toFixed(1) + "s";
    }
    svg.appendChild(star);
  }
})();

/* ---------- 状态徽章 & 页脚 ---------- */
function renderStatus() {
  const map = {
    active:   ["on",  "记录中"],
    inactive: ["off", "未在记录"],
    failed:   ["off", "服务出错"],
    unknown:  ["na",  "状态未知"],
  };
  const [cls, text] = map[DATA.daemon_status] || map.unknown;
  const pill = document.getElementById("status-pill");
  pill.className = "pill " + cls;
  document.getElementById("status-text").textContent = text;
  const thresholdMin = Math.round(DATA.threshold_seconds / 60);
  document.getElementById("meta-line").textContent =
    "数据生成于 " + DATA.generated_at.replace("T", " ") + " · 空闲阈值 " + thresholdMin + " 分钟 · 打开图标或后台每 5 分钟自动更新";
}
renderStatus();

/* ---------- KPI ---------- */
function deltaNode(diffSec, contextLabel) {
  const span = document.createElement("span");
  if (diffSec == null) return span;
  if (Math.abs(diffSec) < 300) {
    span.className = "delta flat";
    span.textContent = "≈ 与" + contextLabel + "持平";
  } else {
    const up = diffSec > 0;
    span.className = "delta " + (up ? "up" : "down");
    span.textContent = (up ? "↑ " : "↓ ") + fmtDur(Math.abs(diffSec)) + " · " + (up ? "高于" : "低于") + contextLabel;
  }
  return span;
}
function renderKPIs() {
  const days = DATA.days;
  const valid = days.filter(isValid);
  const avg14 = valid.length ? valid.reduce((s, d) => s + d.active_seconds, 0) / valid.length : null;

  // 今日
  setDurParts(document.getElementById("kpi-today"), isValid(TODAY) ? TODAY.active_seconds : null);
  const subToday = document.getElementById("kpi-today-sub");
  subToday.textContent = "";
  if (isValid(TODAY)) {
    const t = document.createElement("span");
    t.textContent = LABELS.arrival + " " + TODAY.arrival + " · " + (LABELS.manual ? LABELS.departure : '最近活动') + " " + TODAY.departure;
    subToday.appendChild(t);
    const others = valid.filter(d => d !== TODAY);
    if (others.length) {
      const avgOthers = others.reduce((s, d) => s + d.active_seconds, 0) / others.length;
      subToday.appendChild(deltaNode(TODAY.active_seconds - avgOthers, "日均"));
    }
  } else {
    subToday.textContent = TODAY.has_data ? "今天还没有检测到操作" : "今天还没有数据";
  }

  // 近 7 天（与前 7 天比较）
  const last7 = days.slice(7).filter(isValid);
  const prev7 = days.slice(0, 7).filter(isValid);
  const sum7 = last7.reduce((s, d) => s + d.active_seconds, 0);
  setDurParts(document.getElementById("kpi-week"), sum7);
  const subWeek = document.getElementById("kpi-week-sub");
  subWeek.textContent = "";
  const c = document.createElement("span"); c.textContent = last7.length + " / 7 天有记录";
  subWeek.appendChild(c);
  if (prev7.length) {
    subWeek.appendChild(deltaNode(sum7 - prev7.reduce((s, d) => s + d.active_seconds, 0), "前 7 天"));
  }

  // 14 天日均 + 迷你趋势图
  setDurParts(document.getElementById("kpi-avg"), avg14);
  const subAvg = document.getElementById("kpi-avg-sub");
  subAvg.textContent = "";
  const spark = el("svg", { class: "spark", width: 104, height: 30, viewBox: "0 0 104 30" });
  const maxA = Math.max(3600, ...days.map(d => d.active_seconds));
  days.forEach((d, i) => {
    const x = 2 + i * 7.3;
    let h = isValid(d) ? Math.max(2, (d.active_seconds / maxA) * 28) : 2;
    const bar = el("rect", {
      x: x.toFixed(1), y: (30 - h).toFixed(1), width: 4.4, height: h.toFixed(1), rx: 1.4,
      fill: !isValid(d) ? "rgba(92,72,40,0.12)" : (d === TODAY ? "var(--active)" : "#B8A98C"),
    });
    const t = el("title", {});
    t.textContent = d.date + " · " + (isValid(d) ? fmtDur(d.active_seconds) : "无记录");
    bar.appendChild(t);
    spark.appendChild(bar);
  });
  subAvg.appendChild(spark);
}
renderKPIs();

/* ---------- 14 天柱状图 ---------- */
let selectedDate = null;
function topRoundedPath(x, y, w, h, r) {
  r = Math.min(r, w / 2, h);
  return "M" + x + "," + (y + h) +
    " L" + x + "," + (y + r) +
    " Q" + x + "," + y + " " + (x + r) + "," + y +
    " L" + (x + w - r) + "," + y +
    " Q" + (x + w) + "," + y + " " + (x + w) + "," + (y + r) +
    " L" + (x + w) + "," + (y + h) + " Z";
}
function dayTooltipNodes(day) {
  const nodes = [ttHead(day.date + " " + day.weekday + (day === TODAY ? " · 今天" : ""))];
  if (isValid(day)) {
    nodes.push(ttRow("a", fmtDur(day.active_seconds), LABELS.active));
    if (day.fun_seconds > 60) nodes.push(ttRow("f", fmtDur(day.fun_seconds), LABELS.fun));
    if (day.idle_seconds > 60) nodes.push(ttRow("i", fmtDur(day.idle_seconds), LABELS.idle));
    nodes.push(ttRow(null, day.arrival + " – " + day.departure, LABELS.arrival + ' – ' + (day === TODAY && !LABELS.manual ? '最近活动' : LABELS.departure)));
  } else {
    nodes.push(ttRow(null, day.has_data ? "没有检测到真实操作" : "没有记录", ""));
  }
  return nodes;
}
function renderBarChart() {
  const svg = document.getElementById("bar-chart");
  svg.textContent = "";
  const days = DATA.days;
  const W = 960, H = 244, mL = 42, mR = 72, mT = 14, mB = 46;
  const plotW = W - mL - mR, plotH = H - mT - mB, baseY = mT + plotH;

  const maxSec = Math.max((LABELS.manual ? 1 : 8) * 3600, ...days.map(d => d.total_presence_seconds));
  const maxH = LABELS.manual ? Math.ceil(maxSec / 3600) : Math.ceil(maxSec / 7200) * 2;
  const tickStep = LABELS.manual && maxH <= 3 ? .5 : LABELS.manual && maxH <= 8 ? 1 : 2;
  const yOf = sec => baseY - (sec / (maxH * 3600)) * plotH;

  for (let h = 0; h <= maxH; h += tickStep) {
    const y = yOf(h * 3600);
    if (h > 0) svg.appendChild(el("line", { x1: mL, x2: W - mR, y1: y, y2: y, class: "gridline" }));
    const lb = el("text", { x: mL - 9, y: y + 3.5, class: "axis-label", "text-anchor": "end" });
    lb.textContent = h + "h";
    svg.appendChild(lb);
  }
  svg.appendChild(el("line", { x1: mL, x2: W - mR, y1: baseY, y2: baseY, class: "baseline" }));

  const valid = days.filter(isValid);
  const avg = valid.length ? valid.reduce((s, d) => s + d.active_seconds, 0) / valid.length : 0;
  if (avg > 0) {
    const ry = yOf(avg);
    svg.appendChild(el("line", { x1: mL, x2: W - mR + 6, y1: ry, y2: ry, class: "ref-line" }));
    const rl = el("text", { x: W - mR + 12, y: ry + 3.5, class: "ref-label", "text-anchor": "start" });
    rl.textContent = "日均 " + (avg / 3600).toFixed(1) + "h";
    svg.appendChild(rl);
  }

  const band = plotW / days.length;
  const barW = Math.min(26, band * 0.52);
  const GAP = 2;

  days.forEach(day => {
    const cx = mL + band * (days.indexOf(day) + 0.5);
    const g = el("g", { class: "bar-group", tabindex: 0, role: "button", 'data-date':day.date });
    g.setAttribute("aria-label", day.date + " " + day.weekday + " " + (isValid(day) ? "有效" + fmtDur(day.active_seconds) : "无数据"));
    if (day.date === selectedDate) g.classList.add("selected");

    g.appendChild(el("rect", { x: cx - band / 2 + 2, y: mT - 4, width: band - 4, height: plotH + 8, rx: 8, class: "band-bg" }));

    if (isValid(day)) {
      const x = cx - barW / 2;
      if (day.total_presence_seconds < 300) {
        svgStub(g, cx, barW, baseY, "bar-a");
      } else {
        // 自下而上堆叠：有效(蓝) → 娱乐(玫红) → 中断(沙)，层间 2px 间隙，最顶层圆角收头
        const hOf = sec => (sec / (maxH * 3600)) * plotH;
        const layers = [
          { h: hOf(day.active_seconds), cls: "bar-a" },
          { h: hOf(day.fun_seconds), cls: "bar-f" },
          { h: hOf(day.idle_seconds), cls: "bar-i" },
        ].filter(l => l.h > 0.5);
        let yCursor = baseY;
        layers.forEach((layer, li) => {
          if (li > 0) yCursor -= GAP;
          const yTop = yCursor - layer.h;
          if (li === layers.length - 1) {
            g.appendChild(el("path", { d: topRoundedPath(x, yTop, barW, layer.h, 4), class: layer.cls }));
          } else {
            g.appendChild(el("rect", { x, y: yTop, width: barW, height: layer.h, class: layer.cls }));
          }
          yCursor = yTop;
        });
      }
    } else if (day.has_data) {
      svgStub(g, cx, barW, baseY, "bar-i");
    }

    const dl = el("text", { x: cx, y: H - 28, class: dateCls(day), "text-anchor": "middle" });
    dl.textContent = shortDate(day.date);
    const wl = el("text", { x: cx, y: H - 14, class: dateCls(day), "text-anchor": "middle" });
    wl.textContent = day === TODAY ? "今天" : day.weekday;
    g.appendChild(dl); g.appendChild(wl);

    if (day.date === selectedDate) {
      g.appendChild(el("rect", { x: cx - 8, y: H - 7, width: 16, height: 3, rx: 1.5, class: "sel-tick" }));
    }

    g.addEventListener("click", () => selectDay(day.date));
    g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectDay(day.date); } });
    g.addEventListener("pointermove", evt => showTooltip(evt, dayTooltipNodes(day)));
    g.addEventListener("pointerleave", hideTooltip);
    svg.appendChild(g);
  });

  function svgStub(g, cx, barW, baseY, cls) {
    g.appendChild(el("rect", { x: cx - barW / 2, y: baseY - 3, width: barW, height: 3, rx: 1.5, class: cls }));
  }
  function dateCls(day) {
    let c = "date-label";
    if (day === TODAY) c += " today";
    else if (day.is_weekend) c += " weekend";
    return c;
  }
}

/* ---------- 单日时间线 ---------- */
function renderTimeline(day) {
  const svg = document.getElementById("timeline");
  const empty = document.getElementById("detail-empty");
  svg.textContent = "";
  if (!isValid(day) || !day.segments.length || day.total_presence_seconds < 60) {
    svg.style.display = "none";
    empty.style.display = "block";
    empty.textContent = !day.has_data
      ? "这天没有采样记录 — 可能没到实验室，或守护进程没在运行"
      : (day.no_real_activity || !day.segments.length)
        ? "这天电脑开着，但没有检测到任何键盘鼠标操作"
        : "这天只有一瞬间的操作记录，画不出时间线";
    return;
  }
  svg.style.display = "block";
  empty.style.display = "none";

  const W = 960, mL = 10, mR = 10;
  const stripY = 24, stripH = 30, plotW = W - mL - mR;
  const xOf = sec => mL + (sec / 86400) * plotW;

  // 小时刻度
  for (let h = 0; h <= 24; h++) {
    const x = xOf(h * 3600);
    if (h % 3 === 0) {
      svg.appendChild(el("line", { x1: x, x2: x, y1: stripY + stripH + 3, y2: stripY + stripH + 9, class: "minor-tick" }));
      const lb = el("text", { x, y: stripY + stripH + 24, class: "axis-label", "text-anchor": h === 0 ? "start" : h === 24 ? "end" : "middle" });
      lb.textContent = String(h).padStart(2, "0") + ":00";
      svg.appendChild(lb);
    } else {
      svg.appendChild(el("line", { x1: x, x2: x, y1: stripY + stripH + 3, y2: stripY + stripH + 6, class: "minor-tick", opacity: 0.5 }));
    }
  }

  const x1 = xOf(day.segments[0].start_sec);
  const x2 = xOf(day.segments[day.segments.length - 1].end_sec);

  // 在场时间窗背景 + 圆角裁剪
  const clipId = "tl-clip";
  const defs = el("defs", {});
  const clip = el("clipPath", { id: clipId });
  clip.appendChild(el("rect", { x: x1, y: stripY, width: Math.max(2, x2 - x1), height: stripH, rx: 6 }));
  defs.appendChild(clip);
  svg.appendChild(defs);
  svg.appendChild(el("rect", { x: mL, y: stripY, width: plotW, height: stripH, rx: 6, class: "presence-bg" }));

  const segCls = kind => kind === "active" ? "seg-a" : kind === "fun" ? "seg-f" : "seg-i";
  const gSegs = el("g", { "clip-path": "url(#" + clipId + ")" });
  day.segments.forEach(seg => {
    const sx = xOf(seg.start_sec), ex = xOf(seg.end_sec);
    gSegs.appendChild(el("rect", {
      x: sx, y: stripY, width: Math.max(0.5, ex - sx), height: stripH,
      class: segCls(seg.kind),
    }));
  });
  svg.appendChild(gSegs);

  // 命中层（透明、比色块宽，方便悬停窄段）
  day.segments.forEach(seg => {
    const sx = xOf(seg.start_sec), ex = xOf(seg.end_sec);
    const hitW = Math.max(9, ex - sx);
    const hit = el("rect", { x: sx - (hitW - (ex - sx)) / 2, y: stripY - 4, width: hitW, height: stripH + 8, class: "seg-hit" });
    const kindLabel = seg.kind === "active" ? LABELS.active : seg.kind === "fun" ? LABELS.fun : LABELS.idle;
    const kindKey = seg.kind === "active" ? "a" : seg.kind === "fun" ? "f" : "i";
    hit.addEventListener("pointermove", evt => showTooltip(evt, [
      ttHead(kindLabel),
      ttRow(kindKey, fmtClock(seg.start_sec) + " – " + fmtClock(seg.end_sec), fmtDur(seg.end_sec - seg.start_sec)),
    ]));
    hit.addEventListener("pointerleave", hideTooltip);
    svg.appendChild(hit);
  });

  // 到达 / 离开小旗
  svg.appendChild(el("line", { x1: x1, x2: x1, y1: stripY - 6, y2: stripY + stripH, class: "flag-tick" }));
  svg.appendChild(el("line", { x1: x2, x2: x2, y1: stripY - 6, y2: stripY + stripH, class: "flag-tick" }));
  const near = (x2 - x1) < 130;
  const la = el("text", { x: x1, y: stripY - 11, class: "flag-label", "text-anchor": x1 < 60 ? "start" : "middle" });
  la.textContent = LABELS.arrival + " " + day.arrival;
  const ld = el("text", { x: near ? x2 + 6 : x2, y: stripY - 11, class: "flag-label", "text-anchor": near ? "start" : (x2 > W - 60 ? "end" : "middle") });
  ld.textContent = (day === TODAY && !LABELS.manual ? "最近活动" : LABELS.departure) + ' ' + day.departure;
  svg.appendChild(la); svg.appendChild(ld);
}

function renderDetail(day) {
  document.getElementById("detail-title").textContent =
    day.date + " · " + day.weekday + (day === TODAY ? " · 今天" : "");
  const box = document.getElementById("detail-stats");
  box.textContent = "";
  if (isValid(day)) {
    const rows = [
      [LABELS.arrival, day.arrival],
      [day === TODAY && !LABELS.manual ? "最近活动" : LABELS.departure, day.departure],
      [LABELS.presence, fmtDur(day.total_presence_seconds)],
      [LABELS.active, fmtDur(day.active_seconds)],
      [LABELS.fun, fmtDur(day.fun_seconds)],
      [LABELS.idle, fmtDur(day.idle_seconds)],
    ];
    rows.forEach(([k, v]) => {
      const d = document.createElement("div"); d.className = "stat";
      const ks = document.createElement("span"); ks.className = "k"; ks.textContent = k;
      const vs = document.createElement("span"); vs.className = "v"; vs.textContent = v;
      d.appendChild(ks); d.appendChild(vs); box.appendChild(d);
    });
  }
  renderTimeline(day);
}

function selectDay(date) {
  selectedDate = date;
  // A bookmarked/open "today" must follow the calendar, not yesterday's ISO date.
  history.replaceState(null, "", "#" + (date === TODAY.date ? "today" : date));
  renderBarChart();
  renderDetail(DATA.days.find(d => d.date === date));
}

/* ---------- 表格 ---------- */
function renderTable() {
  const tbody = document.querySelector("#data-table tbody");
  tbody.textContent = '';
  DATA.days.slice().reverse().forEach(day => {
    const tr = document.createElement("tr");
    if (day === TODAY) tr.className = "today-row";
    else if (!isValid(day)) tr.className = "dim";
    const cells = isValid(day)
      ? [day.date + " " + day.weekday, day.arrival, day.departure,
         fmtDur(day.total_presence_seconds), fmtDur(day.active_seconds), fmtDur(day.fun_seconds), fmtDur(day.idle_seconds)]
      : [day.date + " " + day.weekday, "—", "—", "—", "—", "—", day.has_data ? "无真实操作" : "无记录"];
    cells.forEach((text, i) => {
      const td = document.createElement("td");
      if (i >= 3) td.className = "num";
      td.textContent = text;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}
renderTable();

/* ---------- 初始化：记住选中日期 ---------- */
(function init() {
  const wanted = decodeURIComponent(location.hash.slice(1));
  const initial = DATA.days.some(d => d.date === wanted) ? wanted : TODAY.date;
  selectDay(initial);
})();
</script>
</body>
</html>
"""


def _notify(title: str, body: str) -> None:
    """双击图标后给一个立刻可见的桌面通知，让人确认"点击生效了"。
    每个平台的通知方式不同，都拿不到就安静跳过，绝不影响主流程。
    """
    if sys.platform == "darwin":
        command = ["osascript", "-e", f'display notification "{body}" with title "{title}"']
    elif shutil.which("notify-send"):
        command = ["notify-send", title, body]
    else:
        return  # Windows 没有免依赖的通知方式，直接跳过
    try:
        subprocess.run(command, timeout=3)
    except (subprocess.SubprocessError, OSError):
        pass


def _open_in_browser(path: Path) -> None:
    """优先用浏览器自己的 --new-window 打开一个新窗口（一般会被窗口管理器带到前台）；
    如果 webbrowser 走 xdg-open 复用了已有窗口的某个后台标签页，双击图标会显得"没反应"。
    """
    from .dashboard_server import ensure_server
    url = ensure_server()
    for browser_cmd in (["google-chrome", "--new-window", url], ["firefox", "--new-window", url]):
        if shutil.which(browser_cmd[0]):
            try:
                subprocess.Popen(browser_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
    webbrowser.open(url)


def main():
    if "--serve" in sys.argv:                      # 冻结打包后进程自己起服务用的开关
        from .dashboard_server import serve_forever
        serve_forever()
        return
    if "--daemon" in sys.argv:                     # AppImage 双击时的后台模式
        from .lab_tracker import main as run_daemon
        run_daemon()
        return
    # 双击图标就该开始工作：没在记录就顺手把采样拉起来，页面再告诉用户发生了什么。
    started = ensure_daemon()
    path = regenerate_dashboard_html(daemon_started=started)
    _open_in_browser(path)
    _notify("小银河", "已开始记录，仪表盘已在浏览器中打开" if started else "仪表盘已在浏览器中打开")


if __name__ == "__main__":
    main()
