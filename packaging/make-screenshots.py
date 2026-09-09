"""Regenerate the README screenshots.

    python3 packaging/make-screenshots.py        # 需要 Chrome

必须用合成数据，绝不能用真实日志——截图会连同到岗时间和工时一起公开。
这里有一道自检：截图前先读页面上的到岗时间，对不上合成值就直接中止。
它是必要的，因为 /data 每次请求都从真实日志重建统计，只在渲染那几行打补丁
挡不住浏览器几秒后自己把真数据拉回来（这个坑真的踩过一次，差点推上 GitHub）。
"""
import base64, datetime, json, random, subprocess, sys, tempfile, threading, time
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import build_opener, ProxyHandler
import websocket
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from smallgalaxy import dashboard, dashboard_server

OUT = Path(__file__).resolve().parents[1] / 'docs' / 'screenshots'
OUT.mkdir(parents=True, exist_ok=True)
INTERVAL = 60


def fake_records(date):
    """A plausible lab day: arrive, focus blocks, a lunch gap, a little bilibili, leave."""
    rng = random.Random(date.toordinal())
    if date.weekday() == 5 and rng.random() < .7:
        return []                                    # most Saturdays away
    plan = [(9, rng.randint(0, 25), 'active', 95 + rng.randint(0, 40)),
            (11, rng.randint(0, 20), 'idle', 25 + rng.randint(0, 20)),
            (11, 50, 'active', 60 + rng.randint(0, 30)),
            (13, rng.randint(0, 15), 'idle', 55 + rng.randint(0, 25)),
            (14, rng.randint(0, 20), 'active', 110 + rng.randint(0, 50)),
            (16, rng.randint(10, 40), 'fun', 20 + rng.randint(0, 25)),
            (17, rng.randint(0, 20), 'active', 70 + rng.randint(0, 60))]
    rows, idle = [], 0.0
    for hour, minute, kind, span in plan:
        t = datetime.datetime.combine(date, datetime.time(hour % 24, minute))
        title = 'bilibili 番剧' if kind == 'fun' else 'PyCharm — routefuse'
        for _ in range(span):
            idle = idle + INTERVAL if kind == 'idle' else 0.0
            rows.append((t, idle, '' if kind == 'idle' else title))
            t += datetime.timedelta(seconds=INTERVAL)
    return rows


def cdp_session(page_path, width, height, body):
    with patch.object(dashboard_server, 'PAGE', page_path):
        server = ThreadingHTTPServer(('127.0.0.1', 0), dashboard_server.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory(prefix='shots-profile-') as prof:
            proc = subprocess.Popen(['google-chrome', '--headless', '--no-sandbox', '--disable-gpu', '--mute-audio',
                                     '--user-data-dir=' + prof, '--remote-debugging-port=0',
                                     f'--window-size={width},{height}', 'about:blank'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            sock = None
            try:
                portfile = Path(prof) / 'DevToolsActivePort'
                deadline = time.monotonic() + 30
                while not portfile.exists() and time.monotonic() < deadline:
                    time.sleep(.1)
                port = int(portfile.read_text().splitlines()[0])
                opener = build_opener(ProxyHandler({}))
                with opener.open(f'http://127.0.0.1:{port}/json/list') as r:
                    target = next(t for t in json.load(r) if t['type'] == 'page')
                sock = websocket.create_connection(target['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
                state = {'id': 0}

                def cdp(method, params=None):
                    state['id'] += 1
                    sock.send(json.dumps({'id': state['id'], 'method': method, 'params': params or {}}))
                    while True:
                        msg = json.loads(sock.recv())
                        if msg.get('id') == state['id']:
                            return msg

                def js(expr):
                    return cdp('Runtime.evaluate', {'expression': f'(()=>{{{expr}}})()', 'returnByValue': True}) \
                        ['result']['result'].get('value')

                def shot(name, selector=None, pad=16, scale=1):
                    clip = None
                    if selector:
                        r = json.loads(js(f"const r=document.querySelector('{selector}').getBoundingClientRect();"
                                          f"return JSON.stringify({{x:r.x+scrollX,y:r.y+scrollY,w:r.width,h:r.height}});"))
                        clip = {'x': max(0, r['x'] - pad), 'y': max(0, r['y'] - pad),
                                'width': r['w'] + pad * 2, 'height': r['h'] + pad * 2, 'scale': scale}
                    args = {'format': 'png'}
                    if clip:
                        args['clip'] = clip
                    data = cdp('Page.captureScreenshot', args)['result']['data']
                    path = OUT / name
                    path.write_bytes(base64.b64decode(data))
                    return path

                cdp('Emulation.setDeviceMetricsOverride',
                    {'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': width < 500})
                cdp('Page.navigate', {'url': f'http://127.0.0.1:{server.server_port}/'})
                time.sleep(4)
                body(js, shot)
            finally:
                if sock:
                    sock.close()
                proc.terminate(); proc.wait(timeout=10)
        server.shutdown(); server.server_close()


def shrink(path, width):
    im = Image.open(path).convert('RGB')
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(path, optimize=True)
    return path.stat().st_size


# 补丁必须罩住整个会话，不能只罩渲染：/data 现在每次请求都从真实日志重建统计，
# 页面载入几秒后就会把真实作息拉回来，截图里就成了本人的到岗时间。
PATCH = patch.object(dashboard, 'load_records', fake_records)
PATCH.start()
data = dashboard.build_dashboard_data()
html = dashboard.render_html(data)
EXPECTED_ARRIVAL = data['days'][-1]['arrival']

with tempfile.TemporaryDirectory(prefix='readme-shots-') as tmp:
    page = Path(tmp) / 'dashboard.html'
    page.write_text(html, encoding='utf-8')

    def desktop(js, shot):
        js("window.scrollTo(0,0); document.getElementById('hero-title').style.animation='none';")
        time.sleep(1.2)
        # 自检：页面上的数字必须是合成的。真实数据一旦泄进来就立刻停，别把它截进图里。
        live = js("return TODAY.arrival")
        assert live == EXPECTED_ARRIVAL, f'真实数据泄漏进页面: {live} != {EXPECTED_ARRIVAL}'
        print('  数据自检通过（合成到达时间', live, '）')
        shot('dashboard.png')                                   # full first screen

        # Weather phases, hero only. IIFE per eval so a top-level const cannot clash.
        for name, phase in (('rain-1-drizzle', .02), ('rain-2-downpour', .35), ('rain-3-sunny', .86)):
            js(f"window.applyWeatherSettings('cycle',96); clearInterval(weatherTimer);"
               f"const w=weatherAt({phase}); paintWeather(w.rain,w.sun); window.scrollTo(0,0);")
            time.sleep(1.0)
            shot(f'{name}.png', '.hero', pad=0)
        js("window.applyWeatherSettings('cycle',96);")

        # Every page theme, cropped to the three time cards.
        js("preferences.showDecor=false; applyAppearance();"
           "document.querySelector('.kpi-row').scrollIntoView({block:'start'}); window.scrollBy(0,-20);")
        time.sleep(1)
        for theme in THEMES:
            js(f"preferences.theme='{theme}'; applyAppearance();")
            time.sleep(.55)
            shot(f'_theme-{theme}.png', '.kpi-row', pad=10)
        js("preferences.theme='light'; applyAppearance();")
        for focus in FOCUS:
            js(f"preferences.focusStyle='{focus}'; applyAppearance();")
            time.sleep(.55)
            shot(f'_focus-{focus}.png', '.focus-card', pad=10)
        js("preferences.focusStyle='night'; preferences.showDecor=true; applyAppearance();")

        js("openSettings(); document.getElementById('setting-brand')?.focus();")
        time.sleep(1)
        shot('settings.png', 'dialog', pad=0)
        js("dialog.close();")

    THEMES = ['light', 'warm', 'linen', 'mist', 'sky', 'dusk', 'blush',
              'dark', 'ink', 'midnight', 'night', 'cocoa', 'wine']
    FOCUS = ['night', 'forest', 'ocean', 'plum', 'clay', 'ember', 'paper']
    cdp_session(page, 1440, 1000, desktop)

    def mobile(js, shot):
        js("window.scrollTo(0,0); document.getElementById('hero-title').style.animation='none';")
        time.sleep(1.2)
        shot('mobile.png')

    cdp_session(page, 414, 900, mobile)

PATCH.stop()
print('raw shots written to', OUT)
