# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow"]
# ///
"""Drive a Terminal.app window with a shell in an OrbStack machine and grab Shottr screenshots of it.

    uv run tools/termshot.py open                      # new window, prints its id
    uv run tools/termshot.py calibrate                 # once per window size/font
    uv run tools/termshot.py step OUT.png -c CMD [-c CMD ...] [-b REGEX ...] [-a REGEX ...]
    uv run tools/termshot.py run CMD                   # run without a screenshot
    uv run tools/termshot.py shot OUT.png [-b ...]     # grab as is, e.g. inside vim
    uv run tools/termshot.py esc                       # press Escape in the window

-b (frame) and -a (arrow) take a regex searched in the window text; its first group
(or the whole match) gets marked. Prefix with N: to pick the N-th match, e.g. -b '2:metric \\d+'.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

COLS, ROWS = 112, 20
STATE = Path(__file__).with_name(".termshot.json")
PROMPT = re.compile(r"^\S+@[\w-]+:\S*[#$]\s*$")
PROMPT_START = re.compile(r"^\S+@[\w-]+:\S*[#$](\s|$)")
ARROW = (229, 56, 59)


def osa(*lines: str) -> str:
    args = [a for line in lines for a in ("-e", line)]
    return subprocess.run(
        ["osascript", *args], capture_output=True, text=True, check=True
    ).stdout.rstrip("\n")


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(**kw) -> None:
    STATE.write_text(json.dumps(load_state() | kw, indent=2))


class Term:
    def __init__(self, win: int):
        self.tab = f"tab 1 of window id {win}"
        self.win = win

    @classmethod
    def open(cls, machine: str) -> "Term":
        win = int(
            osa(
                'tell application "Terminal"',
                f'set t to do script "orb -m {machine}"',
                "delay 2",
                f"set number of columns of t to {COLS}",
                f"set number of rows of t to {ROWS}",
                "return id of front window",
                "end tell",
            )
        )
        t = cls(win)
        save_state(win=win)
        t.wait_prompt(60)
        t.run("sudo -i")
        t.run("clear")
        return t

    def lines(self, prop: str = "contents") -> list[str]:
        text = osa(f'tell application "Terminal" to get {prop} of {self.tab}')
        lines = text.split("\n")
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    def prompts(self) -> int:
        return sum(bool(PROMPT_START.match(l)) for l in self.lines("history"))

    def wait_prompt(self, timeout: float = 30, after: int = -1) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.25)
            lines = self.lines()
            if lines and PROMPT.match(lines[-1]) and self.prompts() > after:
                time.sleep(0.2)
                return
        raise TimeoutError("no prompt")

    def send(self, cmd: str) -> None:
        esc = cmd.replace("\\", "\\\\").replace('"', '\\"')
        osa(f'tell application "Terminal" to do script "{esc}" in {self.tab}')

    def run(self, cmd: str, timeout: float = 30, wait: bool = True) -> None:
        before = self.prompts()
        self.send(cmd)
        if cmd == "clear":
            # clear also wipes Terminal's history, so wait for a lone prompt instead
            deadline = time.time() + timeout
            while time.time() < deadline:
                time.sleep(0.2)
                lines = self.lines()
                if len(lines) == 1 and PROMPT.match(lines[0]):
                    return
            raise TimeoutError("screen not cleared")
        if wait:
            self.wait_prompt(timeout, before)
        else:
            time.sleep(0.5)

    def shot(self, out: Path) -> None:
        osa(
            'set the clipboard to ""',
            f'tell application "Terminal" to set index of window id {self.win} to 1',
            'tell application "Terminal" to activate',
        )
        time.sleep(0.6)
        subprocess.run(["open", "-g", "shottr://grab/window/active"], check=True)
        time.sleep(2)
        for _ in range(3):
            osa('tell application "System Events" to key code 53')
            time.sleep(0.8)
            if "PNGf" in osa("clipboard info"):
                break
        else:
            raise RuntimeError("Shottr did not put an image on the clipboard")
        out.parent.mkdir(parents=True, exist_ok=True)
        osa(
            f'set f to open for access POSIX file "{out.resolve()}" with write permission',
            "set eof f to 0",
            "write (the clipboard as «class PNGf») to f",
            "close access f",
        )


def calibrate(t: Term, tmp: Path) -> None:
    """Fill row 0 with full-block glyphs and measure them: gives grid origin and cell size."""
    t.run("clear")
    # read keeps the prompt off the screen until the shot is taken
    bar = f"printf '\\u2588%.0s' $(seq {COLS})"
    t.send(f"clear; {bar}; echo; echo; {bar}; read")
    time.sleep(1)
    t.shot(tmp)
    t.send("")
    img = Image.open(tmp).convert("RGB")
    w, h = img.size
    px = img.load()
    # rows mostly covered by bright block pixels; the window border is bright too but
    # only a pixel or two tall, so keep the tallest contiguous band
    hits = {}
    for y in range(h):
        row = [x for x in range(w) if sum(px[x, y]) > 600]
        if len(row) > w * 0.6:
            hits[y] = (row[0], row[-1])
    bands, cur = [], []
    for y in sorted(hits):
        if cur and y != cur[-1] + 1:
            bands.append(cur)
            cur = []
        cur.append(y)
    if cur:
        bands.append(cur)
    if not bands:
        raise RuntimeError("calibration row not found")
    first, third = sorted(sorted(bands, key=len)[-2:])
    x0, x1 = hits[first[len(first) // 2]]
    ch = (third[0] - first[0]) / 2
    # the glyph is shorter than the line pitch and sits centred in it
    y0 = first[0] - (ch - len(first)) / 2
    cw = (x1 - x0 + 1) / COLS
    save_state(x0=x0, y0=y0, cw=cw, ch=ch, size=[w, h])
    t.run("clear")
    print(f"x0={x0} y0={y0:.1f} cell={cw:.2f}x{ch:.2f}")


def locate(lines: list[str], spec: str) -> tuple[int, int, int]:
    nth, _, pattern = (
        spec.partition(":") if re.match(r"^\d+:", spec) else ("1", "", spec)
    )
    found = []
    for r, line in enumerate(lines):
        for m in re.finditer(pattern, line):
            g = 1 if m.groups() else 0
            found.append((r, m.start(g), m.end(g)))
    if len(found) < int(nth):
        raise ValueError(f"arrow target {spec!r} not found")
    return found[int(nth) - 1]


def draw_box(img: Image.Image, r: int, c0: int, c1: int, s: dict) -> None:
    cw, ch, x0, y0 = s["cw"], s["ch"], s["x0"], s["y0"]
    pad = cw * 0.3
    width = max(3, round(ch * 0.1))
    ImageDraw.Draw(img).rounded_rectangle(
        [x0 + c0 * cw - pad, y0 + r * ch + 1, x0 + c1 * cw + pad, y0 + (r + 1) * ch - 1],
        radius=width * 2,
        outline=ARROW,
        width=width,
    )


def draw_arrow(
    img: Image.Image, lines: list[str], r: int, c0: int, c1: int, s: dict
) -> None:
    cw, ch, x0, y0 = s["cw"], s["ch"], s["x0"], s["y0"]

    def busy(x: float, y: float) -> bool:
        row, col = int((y - y0) // ch), int((x - x0) // cw)
        if row < 0 or row >= ROWS or col < 0 or col >= COLS:
            return True
        line = lines[row] if row < len(lines) else ""
        return col < len(line) and line[col] != " "

    mid = (c0 + c1) / 2
    top, bottom, cy = y0 + r * ch, y0 + (r + 1) * ch, y0 + (r + 0.5) * ch
    # tip just outside the target, tail offset in the given direction (in cells)
    candidates = [
        ((x0 + c1 * cw + cw * 0.4, cy), (8, 0)),
        ((x0 + mid * cw, bottom + 2), (4, 2.2)),
        ((x0 + mid * cw, bottom + 2), (-4, 2.2)),
        ((x0 + mid * cw, top - 2), (4, -2.2)),
        ((x0 + mid * cw, top - 2), (-4, -2.2)),
        ((x0 + c0 * cw - cw * 0.4, cy), (-8, 0)),
    ]

    def cost(tip, off):
        tail = (tip[0] + off[0] * cw, tip[1] + off[1] * ch)
        if busy(*tail) and not (0 <= (tail[1] - y0) / ch < ROWS):
            return 1e9
        pts = [(tip[0] + (tail[0] - tip[0]) * t / 40, tip[1] + (tail[1] - tip[1]) * t / 40) for t in range(4, 41)]
        return sum(busy(*pt) for pt in pts)

    tip, off = min(candidates, key=lambda c: cost(*c))
    tail = (tip[0] + off[0] * cw, tip[1] + off[1] * ch)

    d = ImageDraw.Draw(img)
    width = max(5, round(ch * 0.2))
    head = ch * 0.8
    dx, dy = tip[0] - tail[0], tip[1] - tail[1]
    n = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / n, dy / n
    base = (tip[0] - ux * head, tip[1] - uy * head)
    d.line([tail, base], fill=ARROW, width=width)
    d.ellipse([tail[0] - width / 2, tail[1] - width / 2, tail[0] + width / 2, tail[1] + width / 2], fill=ARROW)
    px, py = -uy * head * 0.55, ux * head * 0.55
    d.polygon([tip, (base[0] + px, base[1] + py), (base[0] - px, base[1] - py)], fill=ARROW)


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open")
    o.add_argument("--machine", default="sum")
    sub.add_parser("calibrate")
    r = sub.add_parser("run")
    r.add_argument("command")
    r.add_argument("--no-wait", action="store_true")
    sh = sub.add_parser("shot")
    sh.add_argument("out", type=Path)
    sh.add_argument("-b", "--box", action="append", default=[])
    sh.add_argument("-a", "--arrow", action="append", default=[])
    sub.add_parser("esc")
    st = sub.add_parser("step")
    st.add_argument("out", type=Path)
    st.add_argument("-c", "--command", action="append", default=[])
    st.add_argument("-b", "--box", action="append", default=[])
    st.add_argument("-a", "--arrow", action="append", default=[])
    st.add_argument(
        "--no-wait-last",
        action="store_true",
        help="last command does not return (e.g. tcpdump)",
    )
    a = p.parse_args()

    if a.cmd == "open":
        print(Term.open(a.machine).win)
        return
    state = load_state()
    t = Term(state["win"])
    if a.cmd == "calibrate":
        calibrate(t, Path(tempfile.gettempdir()) / "termshot-calib.png")
    elif a.cmd == "run":
        t.run(a.command, wait=not a.no_wait)
        print("\n".join(t.lines()))
    elif a.cmd == "esc":
        osa(
            f'tell application "Terminal" to set index of window id {t.win} to 1',
            'tell application "Terminal" to activate',
            "delay 0.3",
            'tell application "System Events" to key code 53',
        )
    else:
        if a.cmd == "step":
            t.run("clear")
            for i, c in enumerate(a.command):
                last = i == len(a.command) - 1
                t.run(c, wait=not (last and a.no_wait_last))
        lines = t.lines()
        t.shot(a.out)
        # contents come unwrapped; marks need on-screen rows
        rows = [l[i : i + COLS] for l in lines for i in range(0, max(len(l), 1), COLS)]
        if a.box or a.arrow:
            img = Image.open(a.out)
            for spec in a.box:
                draw_box(img, *locate(rows, spec), state)
            for spec in a.arrow:
                draw_arrow(img, rows, *locate(rows, spec), state)
            img.save(a.out)
        print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
