import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from .urls import normalize, origin, candidate, filename

VERSION = '0.5.0-mac-preview'

def launch_browser(p):
    try:
        return p.chromium.launch(channel='chrome', headless=True)
    except Exception as exc:
        raise RuntimeError('Google Chromeを起動できませんでした。Chromeをインストールして再度お試しください。\n' + str(exc)) from exc

def new_folder(base, url):
    base = Path(base).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    stem = filename('https://local/' + origin(url)[1]) + '_' + datetime.now().strftime('%Y-%m-%d_%H%M%S')
    for i in range(10000):
        path = base / (stem if i == 0 else f'{stem}_{i}')
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue
    raise RuntimeError('保存フォルダを作成できませんでした。')

def prepare(page, cancel):
    page.wait_for_timeout(300)
    started = time.monotonic()
    y = 0
    while time.monotonic() - started < 15 and not cancel.is_set():
        height = page.evaluate('document.documentElement.scrollHeight')
        if y >= min(height, 60000):
            break
        y += 700
        page.evaluate('(y) => window.scrollTo(0,y)', y)
        page.wait_for_timeout(70)
    page.evaluate('''() => Promise.race([Promise.all([document.fonts.ready, ...Array.from(document.images).map(i => i.complete ? Promise.resolve() : new Promise(r => {i.addEventListener('load',r,{once:true});i.addEventListener('error',r,{once:true})}))]),new Promise(r=>setTimeout(r,1200))])''')
    page.evaluate('window.scrollTo(0,0)')
    page.wait_for_timeout(150)

def run_capture(url, modes, limit, base, emit, cancel):
    if not modes or any(m not in ('PC', 'Mobile') for m in modes) or not 1 <= limit <= 10:
        raise ValueError('表示モードとページ数（1〜10）を確認してください。')
    url = normalize(url)
    allowed = origin(url)
    folder = new_folder(base, url)
    for mode in modes:
        (folder / mode).mkdir()
    emit({'type':'folder', 'path':str(folder)})
    log = {'version':VERSION, 'input_url':url, 'browser':'installed Google Chrome', 'pages':[], 'cancelled':False}
    pending = deque([url]); adopted = {url}; visited = set(); images = 0
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            browser = launch_browser(p)
        except Exception as exc:
            log['startup_error'] = str(exc)
            (folder / 'capture-log.json').write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
            raise
        contexts = {}
        try:
            for mode in modes:
                opts = {'viewport':{'width':1440,'height':900}, 'device_scale_factor':1}
                if mode == 'Mobile':
                    opts = dict(p.devices['iPhone 13'])
                    opts.update(viewport={'width':390,'height':844},device_scale_factor=1,default_browser_type='chromium')
                    opts.pop('default_browser_type',None)
                ctx = browser.new_context(**opts, accept_downloads=False)
                def guard(route):
                    req = route.request
                    try:
                        blocked = req.is_navigation_request() and req.frame == req.frame.page.main_frame and origin(req.url) != allowed
                    except ValueError:
                        blocked = req.is_navigation_request()
                    route.abort() if blocked else route.continue_()
                ctx.route('**/*', guard)
                contexts[mode] = ctx
            while pending and not cancel.is_set():
                current = pending.popleft()
                if current in visited:
                    continue
                index = len(log['pages']) + 1
                emit({'type':'progress','processed':len(log['pages']),'detected':len(adopted),'url':current})
                row = {'url':current, 'files':{}, 'errors':{}}
                links = []; final = None
                for mode, ctx in contexts.items():
                    if cancel.is_set(): break
                    page = ctx.new_page()
                    try:
                        response = page.goto(current, wait_until='domcontentloaded', timeout=30000)
                        if response and response.status >= 400:
                            raise RuntimeError(f'HTTP {response.status}')
                        actual = normalize(page.url)
                        if origin(actual) != allowed:
                            raise RuntimeError('別サイトへの移動を検出しました。')
                        if actual in visited:
                            row['duplicate_of'] = actual
                            break
                        final = actual
                        prepare(page, cancel)
                        if cancel.is_set(): break
                        links.extend(page.locator('a[href]').evaluate_all('(els)=>els.map(a=>a.href)'))
                        rel = f'{mode}/{index:02d}_{filename(actual)}.png'
                        page.screenshot(path=str(folder / rel), full_page=True, timeout=20000, animations='disabled')
                        row['files'][mode] = rel
                        images += 1
                    except Exception as exc:
                        row['errors'][mode] = str(exc)
                    finally:
                        page.close()
                visited.add(current)
                if final: visited.add(final)
                log['pages'].append(row)
                for href in links:
                    u = candidate(final or current, href, allowed)
                    if u and u not in adopted and u not in visited and len(adopted) < limit:
                        adopted.add(u); pending.append(u)
                log['cancelled'] = cancel.is_set()
                (folder / 'capture-log.json').write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
                emit({'type':'progress','processed':len(log['pages']),'detected':len(adopted),'images':images})
        finally:
            browser.close()
            log['cancelled'] = cancel.is_set()
            (folder / 'capture-log.json').write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
    failures = sum(bool(row['errors']) for row in log['pages'])
    emit({'type':'done','images':images,'failures':failures,'cancelled':cancel.is_set()})
    return folder, log
