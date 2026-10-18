# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow", "playwright", "pyobjc-framework-Quartz"]
# ///
"""Drive a separate Chrome window over CDP and screenshot it in the background.

    uv run tools/browsershot.py open [URL]                 # clean profile, fixed size
    uv run tools/browsershot.py shot OUT.png [--url URL] [--js CODE] [-b SEL ...]
    uv run tools/browsershot.py js CODE                    # evaluate in the page, print result

-b takes a Playwright selector (css, text=..., or `css >> nth=1`); its box gets a red frame.
--js/--py run before the shot (--py gets `page`, e.g. to fill a form); --wait gives the
page time after it.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

PORT = 9333
PROFILE = Path(__file__).with_name(".chrome-profile")
WIDTH, HEIGHT = 1280, 800
RED = (229, 56, 59)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def chrome_pid() -> int:
    out = subprocess.run(
        ["pgrep", "-f", f"remote-debugging-port={PORT}"], capture_output=True, text=True
    ).stdout.split()
    # the browser process is the oldest one; helpers carry the flag too
    pids = [int(p) for p in out]
    ppid = {
        p: int(
            subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(p)], capture_output=True, text=True
            ).stdout.strip()
            or 0
        )
        for p in pids
    }
    return next(p for p in pids if ppid[p] not in pids)


def window_id(pid: int) -> int:
    import Quartz

    wins = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, 0)
    cands = [
        w
        for w in wins
        if w["kCGWindowOwnerPID"] == pid
        and w["kCGWindowLayer"] == 0
        and w["kCGWindowBounds"]["Height"] > 200
    ]
    return max(cands, key=lambda w: w["kCGWindowBounds"]["Height"])["kCGWindowNumber"]


def open_browser(url: str) -> None:
    subprocess.Popen(
        [
            CHROME,
            f"--user-data-dir={PROFILE}",
            f"--remote-debugging-port={PORT}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",
            # keep painting while other windows cover it, so background captures are fresh
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            f"--window-size={WIDTH},{HEIGHT}",
            "--window-position=40,40",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    time.sleep(4)
    print(window_id(chrome_pid()))


def page_of(pw):
    browser = pw.chromium.connect_over_cdp(f"http://localhost:{PORT}")
    pages = [
        p for c in browser.contexts for p in c.pages if not p.url.startswith("devtools")
    ]
    return browser, pages[0]


def shot(
    out: Path,
    url: str | None,
    js: str | None,
    py: str | None,
    wait: float,
    boxes: list[str],
) -> None:
    with sync_playwright() as pw:
        browser, page = page_of(pw)
        cdp = page.context.new_cdp_session(page)
        win = cdp.send("Browser.getWindowForTarget")["windowId"]
        cdp.send("Browser.setWindowBounds", {"windowId": win, "bounds": {"windowState": "normal"}})
        cdp.send(
            "Browser.setWindowBounds",
            {"windowId": win, "bounds": {"width": WIDTH, "height": HEIGHT}},
        )
        if url:
            page.goto(url)
            page.wait_for_load_state("networkidle")
        if js:
            print(page.evaluate(js))
        if py:
            exec(py, {"page": page, "time": time})
        time.sleep(wait)
        rects = []
        for sel in boxes:
            loc = page.locator(sel).first
            loc.scroll_into_view_if_needed()
            rects.append(loc.bounding_box())
        if boxes:
            # scrolling may have moved earlier targets: measure again
            rects = [page.locator(sel).first.bounding_box() for sel in boxes]
        inner = page.evaluate("[innerWidth, innerHeight, devicePixelRatio]")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["screencapture", "-x", "-o", "-l", str(window_id(chrome_pid())), str(out)],
        check=True,
    )
    if rects:
        img = Image.open(out)
        _, ih, dpr = inner
        top = img.height - ih * dpr
        d = ImageDraw.Draw(img)
        w = round(3 * dpr)
        for r in rects:
            pad = 4 * dpr
            d.rounded_rectangle(
                [
                    r["x"] * dpr - pad,
                    top + r["y"] * dpr - pad,
                    (r["x"] + r["width"]) * dpr + pad,
                    top + (r["y"] + r["height"]) * dpr + pad,
                ],
                radius=3 * w,
                outline=RED,
                width=w,
            )
        img.save(out)


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open")
    o.add_argument("url", nargs="?", default="about:blank")
    s = sub.add_parser("shot")
    s.add_argument("out", type=Path)
    s.add_argument("--url")
    s.add_argument("--js")
    s.add_argument("--py", help="Playwright code with `page` in scope")
    s.add_argument("--wait", type=float, default=1.0)
    s.add_argument("-b", "--box", action="append", default=[])
    j = sub.add_parser("js")
    j.add_argument("code")
    a = p.parse_args()
    if a.cmd == "open":
        open_browser(a.url)
    elif a.cmd == "shot":
        shot(a.out, a.url, a.js, a.py, a.wait, a.box)
    else:
        with sync_playwright() as pw:
            browser, page = page_of(pw)
            print(json.dumps(page.evaluate(a.code), ensure_ascii=False, default=str))


if __name__ == "__main__":
    sys.exit(main())
