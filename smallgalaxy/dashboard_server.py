"""Loopback-only, read-only dashboard server; never serves raw logs or arbitrary paths."""
import json
import datetime
import math
import re
import subprocess
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from . import dashboard

PORT = 8766
URL = f"http://127.0.0.1:{PORT}"
PAGE = Path.home() / '.lab_tracker' / 'dashboard.html'
IDENTITY = b'small-galaxy-dashboard-v1'
# 你自己的音频文件放这里，页面就能直接点播，不依赖任何在线平台。
MUSIC_DIR = Path.home() / '.lab_tracker' / 'music'
AUDIO_TYPES = {'.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.ogg': 'audio/ogg',
               '.oga': 'audio/ogg', '.opus': 'audio/ogg', '.wav': 'audio/wav',
               '.flac': 'audio/flac', '.aac': 'audio/aac'}


def live_dashboard_data() -> dict:
    """The saved HTML is a fallback export, never the source of today's statistics.

    Retain export options and a *recent* first-start hint, but rebuild dates, log
    totals and recording status on every request, including when sampling stopped.
    """
    snapshot = {}
    try:
        match = re.search(r'^let DATA = (.+);$', PAGE.read_text(encoding='utf-8'), re.M)
        if match:
            value = json.loads(match[1])
            if isinstance(value, dict):
                snapshot = value
    except (OSError, ValueError):
        pass  # A missing or incomplete export must not prevent a live dashboard.
    threshold = snapshot.get('threshold_seconds', dashboard.DEFAULT_THRESHOLD_SECONDS)
    if not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or threshold <= 0:
        threshold = dashboard.DEFAULT_THRESHOLD_SECONDS
    days = snapshot.get('days')
    window_days = len(days) if isinstance(days, list) and 1 <= len(days) <= 366 else dashboard.WINDOW_DAYS
    started = False
    if snapshot.get('daemon_started'):
        try:
            age = (datetime.datetime.now() - datetime.datetime.fromisoformat(snapshot['generated_at'])).total_seconds()
            started = 0 <= age < dashboard.STALE_AFTER_SECONDS
        except (KeyError, TypeError, ValueError):
            pass
    return dashboard.build_dashboard_data(threshold, window_days, daemon_started=started)


def live_dashboard_html() -> bytes:
    return dashboard.render_html(live_dashboard_data()).encode('utf-8')


def list_music() -> list:
    """按名字列出音乐目录里的音频文件；只看这一层，不递归，不跟随符号链接出去。"""
    try:
        entries = sorted(MUSIC_DIR.iterdir(), key=lambda item: item.name.lower())
    except OSError:
        return []
    tracks = []
    for entry in entries:
        if entry.suffix.lower() not in AUDIO_TYPES:
            continue
        try:
            if not entry.is_file() or entry.resolve().parent != MUSIC_DIR.resolve():
                continue
            tracks.append({'name': entry.name, 'size': entry.stat().st_size})
        except OSError:
            continue
    return tracks


def resolve_track(name: str) -> Path:
    """把请求里的文件名解析成音乐目录下的真实文件，越界一律拒绝。"""
    if not name or '/' in name or '\\' in name or name in ('.', '..'):
        raise ValueError('bad track name')
    target = MUSIC_DIR / name
    if target.suffix.lower() not in AUDIO_TYPES:
        raise ValueError('unsupported type')
    resolved = target.resolve()
    if resolved.parent != MUSIC_DIR.resolve() or not resolved.is_file():
        raise ValueError('outside the music directory')
    return resolved


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
            self.send_error(403)
            return
        path = self.path.split('?', 1)[0]
        try:
            if path == '/health':
                body, mime = IDENTITY, 'text/plain'
            elif path in ('/', '/dashboard.html'):
                body, mime = live_dashboard_html(), 'text/html; charset=utf-8'
            elif path == '/data':
                body = json.dumps(live_dashboard_data(), ensure_ascii=False).encode('utf-8')
                mime = 'application/json; charset=utf-8'
            elif path == '/music':
                body = json.dumps(list_music(), ensure_ascii=False).encode()
                mime = 'application/json; charset=utf-8'
            elif path.startswith('/music/'):
                try:
                    track = resolve_track(urllib.parse.unquote(path[len('/music/'):]))
                except ValueError:
                    self.send_error(404)
                    return
                body, mime = track.read_bytes(), AUDIO_TYPES[track.suffix.lower()]
            else:
                self.send_error(404)
                return
        except (OSError, ValueError):
            self.send_error(503, 'Dashboard is being generated; please retry')
            return
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def _server_command():
    """怎么把自己作为后台服务再启动一次。

    源码和 pip 安装都能用 `python -m smallgalaxy.dashboard_server`；
    PyInstaller 打出来的包里没有 Python 解释器可调，改成用自身可执行文件加一个开关。
    """
    if getattr(sys, "frozen", False):
        return [sys.executable, "--serve"]
    return [sys.executable, "-m", "smallgalaxy.dashboard_server"]


def ensure_server():
    opener = build_opener(ProxyHandler({}))

    def ready():
        try:
            with opener.open(URL + '/health', timeout=.5) as response:
                return response.read(100) == IDENTITY
        except (OSError, URLError):
            return False

    if ready():
        return URL
    process = subprocess.Popen(_server_command(),
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(30):
        if ready():
            return URL
        if process.poll() is not None:
            break
        time.sleep(.1)
    raise RuntimeError(f'小银河本地页面服务无法启动，请检查端口 {PORT} 是否已被占用。')


def serve_forever():
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()


if __name__ == '__main__':
    serve_forever()
