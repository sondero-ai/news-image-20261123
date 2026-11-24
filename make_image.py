#!/usr/bin/env python3
"""Draw entry.png: Monday 23 November 2026's world news on one page.

Python 3 + Pillow. No randomness, no clock, no network: running this twice
writes byte-identical PNGs. The page is 1024x1024 RGB.
"""

from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

W = H = 1024
MARGIN = 22
CONTENT = 980
COL_W = 318
GUTTER = 13
COL_X = (MARGIN, MARGIN + COL_W + GUTTER, MARGIN + 2 * (COL_W + GUTTER))

# ---------------------------------------------------------------- palette

PAPER = (245, 240, 230)
CARD = (251, 247, 238)
INK = (22, 24, 29)
MUTED = (84, 87, 94)
BODY = (78, 81, 88)
RED = (179, 38, 30)
NAVY = (22, 33, 58)
GOLD = (216, 162, 63)
TEAL = (44, 127, 121)
RULE = (207, 198, 182)
BLUSH = (243, 228, 222)
CREAM = (245, 240, 230)

# illustration colours
I_GOLD = (216, 162, 63)
I_RED = (200, 64, 47)
I_TEAL = (62, 156, 147)
I_SLATE = (138, 147, 166)
I_CREAM = (245, 240, 230)
MAP_DOT = (180, 169, 148)
MAP_FILL = (232, 223, 204)

CREAM_80 = (200, 199, 196)
BAND_DOT = (35, 45, 68)

# ---------------------------------------------------------------- fonts

FONT_DIRS = (
    "C:/Windows/Fonts",
    "/usr/share/fonts/truetype/msttcorefonts",
    "/Library/Fonts",
)

FONT_FILES = {
    "georgia_bold": ("georgiab.ttf", "Georgia Bold.ttf"),
    "ui": ("segoeui.ttf", "DejaVuSans.ttf"),
    "ui_bold": ("segoeuib.ttf", "DejaVuSans-Bold.ttf"),
    "ui_semibold": ("seguisb.ttf", "DejaVuSans-Bold.ttf"),
    "ui_light": ("segoeuisl.ttf", "DejaVuSans.ttf"),
}

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    key = (name, size)
    hit = _font_cache.get(key)
    if hit is not None:
        return hit
    for directory in FONT_DIRS:
        for filename in FONT_FILES[name]:
            path = os.path.join(directory, filename)
            if os.path.exists(path):
                loaded = ImageFont.truetype(path, size)
                _font_cache[key] = loaded
                return loaded
    raise RuntimeError(f"no font file found for {name}")


def cap_height(f: ImageFont.FreeTypeFont) -> int:
    box = f.getbbox("H")
    return box[3] - box[1]


# ---------------------------------------------------------------- type helpers


def text_w(d: ImageDraw.ImageDraw, s: str, f: ImageFont.FreeTypeFont) -> float:
    return d.textlength(s, font=f)


def put_l(d, x, top, s, f, fill):
    """Left-aligned, capitals starting at `top`."""
    d.text((x, top + cap_height(f)), s, font=f, fill=fill, anchor="ls")


def put_c(d, cx, top, s, f, fill):
    d.text((cx, top + cap_height(f)), s, font=f, fill=fill, anchor="ms")


def put_r(d, x, top, s, f, fill):
    d.text((x, top + cap_height(f)), s, font=f, fill=fill, anchor="rs")


def tracked_w(d, s, f, tracking):
    if not s:
        return 0.0
    return sum(text_w(d, ch, f) for ch in s) + tracking * (len(s) - 1)


def tracked(d, x, top, s, f, fill, tracking, align="left"):
    """Letter-spaced capitals, baseline derived from the capitals' top."""
    baseline = top + cap_height(f)
    width = tracked_w(d, s, f, tracking)
    if align == "right":
        x -= width
    elif align == "center":
        x -= width / 2.0
    for ch in s:
        d.text((x, baseline), ch, font=f, fill=fill, anchor="ls")
        x += text_w(d, ch, f) + tracking
    return width


def wrap_text(d, s: str, f, max_width: float) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in s.split():
        trial = word if not line else f"{line} {word}"
        if text_w(d, trial, f) <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def wrap_balanced(d, s: str, f, max_width: float, max_lines: int) -> list[str]:
    """Break a sentence into at most max_lines lines with even line lengths.

    A shortest-path over word ranges, costed by squared slack, so headlines do
    not leave an orphan word and paragraphs do not end on a widow.
    """
    words = s.split()
    n = len(words)
    if n == 0:
        return []
    widths = [[0.0] * n for _ in range(n)]
    for i in range(n):
        line = ""
        for j in range(i, n):
            line = words[j] if not line else f"{line} {words[j]}"
            widths[i][j] = text_w(d, line, f)

    inf = float("inf")
    cost = [[inf] * n for _ in range(max_lines + 1)]
    back = [[-1] * n for _ in range(max_lines + 1)]
    for k in range(1, max_lines + 1):
        for j in range(n):
            for i in range(j + 1):
                width = widths[i][j]
                if width > max_width:
                    continue
                if i == 0:
                    prev = 0.0 if k == 1 else inf
                else:
                    prev = cost[k - 1][i - 1] if k > 1 else inf
                if prev == inf:
                    continue
                slack = max_width - width
                total = prev + slack * slack
                if total < cost[k][j]:
                    cost[k][j] = total
                    back[k][j] = i
    best_k = min(range(1, max_lines + 1), key=lambda k: cost[k][n - 1])
    assert cost[best_k][n - 1] < inf, f"cannot set {s!r} in {max_lines} lines"
    lines: list[str] = []
    k, j = best_k, n - 1
    while j >= 0:
        i = back[k][j]
        assert i >= 0
        lines.append(" ".join(words[i:j + 1]))
        j = i - 1
        k -= 1
    return list(reversed(lines))


def paragraph(d, x, top, lines, f, fill, pitch, align="left"):
    y = top + cap_height(f)
    for line in lines:
        if align == "left":
            d.text((x, y), line, font=f, fill=fill, anchor="ls")
        else:
            d.text((x, y), line, font=f, fill=fill, anchor="ms")
        y += pitch


def rect(d, x, y, w, h, fill):
    d.rectangle((x, y, x + w - 1, y + h - 1), fill=fill)


# ---------------------------------------------------------------- shape helpers

def rr(d, x0, y0, x1, y1, radius, fill=None, outline=None, width=1):
    radius = max(0, min(radius, (x1 - x0) / 2, (y1 - y0) / 2))
    d.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=fill, outline=outline, width=width)


def ell(d, x0, y0, x1, y1, fill=None, outline=None, width=1):
    d.ellipse((x0, y0, x1, y1), fill=fill, outline=outline, width=width)


def rotate(points, degrees):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return [(x * c - y * s, x * s + y * c) for x, y in points]


def icon_poly(d, cx, cy, u, points, fill=None, outline=None, width=1):
    d.polygon([(cx + x * u, cy + y * u) for x, y in points], fill=fill, outline=outline, width=width)


def icon_line(d, cx, cy, u, points, fill, width=2, joint="curve"):
    d.line([(cx + x * u, cy + y * u) for x, y in points], fill=fill, width=width, joint=joint)


def icon_rect(d, cx, cy, u, x0, y0, x1, y1, fill=None, outline=None, width=1):
    d.rectangle((cx + x0 * u, cy + y0 * u, cx + x1 * u, cy + y1 * u), fill=fill, outline=outline, width=width)


def icon_ell(d, cx, cy, u, x0, y0, x1, y1, fill=None, outline=None, width=1):
    d.ellipse((cx + x0 * u, cy + y0 * u, cx + x1 * u, cy + y1 * u), fill=fill, outline=outline, width=width)


def icon_rr(d, cx, cy, u, x0, y0, x1, y1, radius, fill=None, outline=None, width=1):
    rr(d, cx + x0 * u, cy + y0 * u, cx + x1 * u, cy + y1 * u, radius * u, fill=fill, outline=outline, width=width)


# ---------------------------------------------------------------- icons
# Each icon lives in a 100-unit-tall box scaled by u = band_height / 100, so the
# same drawing serves the tall lead cards and the shorter ones.


def icon_chip(d, cx, cy, h):
    """Microchip with gold pins and a cream return arrow."""
    u = h / 100.0
    ox = -24
    for i in (-1, 0, 1):
        yy = i * 13
        icon_rect(d, cx, cy, u, ox - 36, yy - 3, ox - 24, yy + 3, fill=I_GOLD)
        icon_rect(d, cx, cy, u, ox + 24, yy - 3, ox + 36, yy + 3, fill=I_GOLD)
        xx = ox + i * 13
        icon_rect(d, cx, cy, u, xx - 3, -36, xx + 3, -24, fill=I_GOLD)
        icon_rect(d, cx, cy, u, xx - 3, 24, xx + 3, 36, fill=I_GOLD)
    icon_rr(d, cx, cy, u, ox - 24, -24, ox + 24, 24, 3, fill=I_CREAM)
    icon_rect(d, cx, cy, u, ox - 12, -12, ox + 12, 12, fill=NAVY)
    icon_rect(d, cx, cy, u, ox - 5, -5, ox + 5, 5, fill=I_GOLD)
    # return arrow: a U-turn on the right
    ax = 50
    icon_line(d, cx, cy, u, [(ax - 19, 24), (ax - 19, 2)], I_CREAM, 2)
    d.arc((cx + (ax - 19) * u, cy - 18 * u, cx + (ax + 19) * u, cy + 22 * u),
          180, 360, fill=I_CREAM, width=2)
    icon_line(d, cx, cy, u, [(ax + 19, 2), (ax + 19, 10)], I_CREAM, 2)
    icon_poly(d, cx, cy, u, [(ax + 12, 8), (ax + 19, 22), (ax + 26, 8)], fill=I_CREAM)


def icon_ship(d, cx, cy, h):
    """Drone boat, listing warship, teal wake."""
    u = h / 100.0
    for yy in (32, 40):
        pts = [(k, yy + (2 if (k // 12) % 2 else -2)) for k in range(-90, 91, 12)]
        icon_line(d, cx, cy, u, pts, I_TEAL, 2)
    sx, sy = cx + 24 * u, cy - 2 * u
    hull = rotate([(-40, -2), (30, -2), (24, 12), (-44, 12)], 12)
    icon_poly(d, sx, sy, u, hull, fill=I_SLATE)
    deck = rotate([(-30, -14), (14, -14), (14, -2), (-30, -2)], 12)
    icon_poly(d, sx, sy, u, deck, fill=I_CREAM)
    tower = rotate([(-12, -28), (4, -28), (4, -14), (-12, -14)], 12)
    icon_poly(d, sx, sy, u, tower, fill=I_SLATE)
    icon_line(d, sx, sy, u, [(18, -14), (18, -30)], I_SLATE, 2)
    icon_poly(d, cx, cy, u, [(-86, 10), (-52, 10), (-58, 20), (-80, 20)], fill=I_CREAM)
    icon_rect(d, cx, cy, u, -76, 2, -64, 10, fill=I_CREAM)
    icon_line(d, cx, cy, u, [(-70, 2), (-70, -12)], I_CREAM, 2)
    icon_line(d, cx, cy, u, [(-70, -12), (-60, -16)], I_CREAM, 2)
    icon_line(d, cx, cy, u, [(-98, 24), (-86, 24)], I_CREAM, 2)


def icon_ballot(d, cx, cy, h):
    """Broken ballot box, red smoke, gold flag."""
    u = h / 100.0
    icon_poly(d, cx, cy, u, [(-44, 0), (26, 0), (22, 34), (-40, 34)], fill=I_CREAM)
    icon_poly(d, cx, cy, u, [(-48, -8), (30, -8), (26, 0), (-44, 0)], fill=I_CREAM)
    icon_rect(d, cx, cy, u, -32, -6, 2, -2, fill=NAVY)
    icon_line(d, cx, cy, u, [(-8, 0), (-2, 9), (-10, 17), (-4, 26), (-8, 34)], NAVY, 2)
    for dx, dy, r in ((-32, -18, 10), (-18, -30, 12), (0, -38, 8)):
        icon_ell(d, cx, cy, u, dx - r, dy - r, dx + r, dy + r, fill=I_RED)
    icon_line(d, cx, cy, u, [(40, 34), (40, -32)], I_GOLD, 2)
    icon_poly(d, cx, cy, u, [(40, -32), (64, -26), (40, -16)], fill=I_GOLD)


def icon_refinery(d, cx, cy, h):
    """Refinery column, sphere tank, flame, drone."""
    u = h / 100.0
    icon_line(d, cx, cy, u, [(-76, 38), (66, 38)], I_CREAM, 2)
    # distillation column
    icon_rr(d, cx, cy, u, -22, -30, -6, 36, 4, fill=I_CREAM)
    for yy in (-18, -4, 10):
        icon_line(d, cx, cy, u, [(-20, yy), (-8, yy)], NAVY, 1)
    # horizontal storage tank
    icon_rr(d, cx, cy, u, -62, 12, -28, 34, 7, fill=I_CREAM)
    icon_line(d, cx, cy, u, [(-56, 23), (-34, 23)], NAVY, 2)
    icon_line(d, cx, cy, u, [(-56, 34), (-56, 38)], I_CREAM, 2)
    icon_line(d, cx, cy, u, [(-34, 34), (-34, 38)], I_CREAM, 2)
    # chimney and flame
    icon_rect(d, cx, cy, u, 8, -26, 18, 36, fill=I_CREAM)
    icon_poly(d, cx, cy, u, [(6, -26), (13, -44), (20, -26), (13, -18)], fill=I_RED)
    # pipes and a valve
    icon_line(d, cx, cy, u, [(-46, 2), (-32, 2), (-32, -10), (-22, -10)], I_CREAM, 2)
    icon_line(d, cx, cy, u, [(-6, 24), (8, 24)], I_CREAM, 2)
    icon_ell(d, cx, cy, u, -38, -14, -34, -10, fill=I_GOLD)
    # smoke
    icon_ell(d, cx, cy, u, -52, -26, -40, -14, fill=I_TEAL)
    icon_ell(d, cx, cy, u, -47, -37, -37, -27, fill=I_TEAL)
    # drone
    icon_rect(d, cx, cy, u, 30, -34, 44, -28, fill=I_GOLD)
    icon_line(d, cx, cy, u, [(24, -37), (36, -37)], I_GOLD, 2)
    icon_line(d, cx, cy, u, [(38, -37), (50, -37)], I_GOLD, 2)


def icon_gavel(d, cx, cy, h):
    """Gold gavel, cream scroll, red Catalan stripes."""
    u = h / 100.0
    icon_rr(d, cx, cy, u, -54, 12, 54, 38, 4, fill=I_CREAM)
    icon_ell(d, cx, cy, u, -64, 12, -48, 38, fill=I_CREAM)
    icon_ell(d, cx, cy, u, 48, 12, 64, 38, fill=I_CREAM)
    icon_line(d, cx, cy, u, [(-40, 19), (40, 19)], NAVY, 1)
    icon_line(d, cx, cy, u, [(-40, 31), (40, 31)], NAVY, 1)
    for i in range(4):
        x = -36 + i * 18
        icon_rect(d, cx, cy, u, x, 15, x + 10, 35, fill=I_RED)
    gx, gy = cx + 6 * u, cy - 20 * u
    head = rotate([(-26, -9), (26, -9), (26, 9), (-26, 9)], -22)
    icon_poly(d, gx, gy, u, head, fill=I_GOLD)
    handle = rotate([(-4, 9), (5, 9), (5, 40), (-4, 40)], -22)
    icon_poly(d, gx, gy, u, handle, fill=I_GOLD)


def icon_mic(d, cx, cy, h):
    """Cream microphone, red lash, gold scales."""
    u = h / 100.0
    icon_rr(d, cx, cy, u, -58, -36, -32, 4, 13, fill=I_CREAM)
    for yy in (-30, -23, -16, -9):
        icon_line(d, cx, cy, u, [(-55, yy), (-35, yy)], NAVY, 2)
    icon_line(d, cx, cy, u, [(-45, 4), (-45, 24)], I_CREAM, 2)
    icon_line(d, cx, cy, u, [(-58, 24), (-32, 24)], I_CREAM, 2)
    for i in range(3):
        icon_line(d, cx, cy, u, [(-18 + i * 9, -32), (-8 + i * 9, -12)], I_RED, 2)
    # scales
    icon_line(d, cx, cy, u, [(48, -26), (48, 26)], I_GOLD, 2)
    icon_line(d, cx, cy, u, [(28, -18), (68, -18)], I_GOLD, 2)
    icon_line(d, cx, cy, u, [(28, -18), (28, -8)], I_GOLD, 1)
    icon_line(d, cx, cy, u, [(68, -18), (68, -8)], I_GOLD, 1)
    icon_poly(d, cx, cy, u, [(20, -8), (36, -8), (28, 2)], fill=I_GOLD)
    icon_poly(d, cx, cy, u, [(60, -8), (76, -8), (68, 2)], fill=I_GOLD)
    icon_line(d, cx, cy, u, [(40, 26), (56, 26)], I_GOLD, 2)


def icon_flag(d, cx, cy, h):
    """Cream flag, gold scales, red warning ring."""
    u = h / 100.0
    ell(d, cx - 60 * u, cy - 38 * u, cx + 60 * u, cy + 38 * u, outline=I_RED, width=2)
    icon_line(d, cx, cy, u, [(-48, -32), (-48, 34)], I_CREAM, 2)
    icon_poly(d, cx, cy, u, [(-48, -32), (-10, -26), (-14, -6), (-48, -12)], fill=I_CREAM)
    icon_line(d, cx, cy, u, [(36, -22), (36, 30)], I_GOLD, 2)
    icon_line(d, cx, cy, u, [(18, -14), (54, -14)], I_GOLD, 2)
    icon_line(d, cx, cy, u, [(18, -14), (18, -4)], I_GOLD, 1)
    icon_line(d, cx, cy, u, [(54, -14), (54, -4)], I_GOLD, 1)
    icon_poly(d, cx, cy, u, [(9, -4), (27, -4), (18, 6)], fill=I_GOLD)
    icon_poly(d, cx, cy, u, [(45, -4), (63, -4), (54, 6)], fill=I_GOLD)
    icon_line(d, cx, cy, u, [(28, 30), (44, 30)], I_GOLD, 2)


def icon_trophy(d, cx, cy, h):
    """Gold trophy, cream football, teal globe."""
    u = h / 100.0
    icon_ell(d, cx, cy, u, -66, -28, -16, 22, fill=I_TEAL)
    icon_ell(d, cx, cy, u, -49, -28, -33, 22, outline=I_CREAM, width=1)
    icon_line(d, cx, cy, u, [(-66, -3), (-16, -3)], I_CREAM, 1)
    icon_line(d, cx, cy, u, [(-41, -28), (-41, 22)], I_CREAM, 1)
    icon_poly(d, cx, cy, u, [(8, -34), (44, -34), (40, -12), (12, -12)], fill=I_GOLD)
    icon_line(d, cx, cy, u, [(8, -34), (0, -24), (8, -14)], I_GOLD, 2)
    icon_line(d, cx, cy, u, [(44, -34), (52, -24), (44, -14)], I_GOLD, 2)
    icon_rect(d, cx, cy, u, 20, -12, 32, -4, fill=I_GOLD)
    icon_rect(d, cx, cy, u, 10, -4, 42, 4, fill=I_GOLD)
    icon_ell(d, cx, cy, u, 10, 14, 42, 40, fill=I_CREAM)
    for dx, dy in ((26, 20), (20, 30), (33, 30), (26, 36)):
        icon_ell(d, cx, cy, u, dx - 2, dy - 2, dx + 2, dy + 2, fill=NAVY)


def icon_school(d, cx, cy, h):
    """Cream school, red warning triangle, gold envelope."""
    u = h / 100.0
    icon_rect(d, cx, cy, u, -70, -6, -18, 34, fill=I_CREAM)
    icon_poly(d, cx, cy, u, [(-76, -6), (-44, -30), (-12, -6)], fill=I_CREAM)
    for wx in (-62, -46, -30):
        icon_rect(d, cx, cy, u, wx, 2, wx + 9, 13, fill=NAVY)
    icon_rect(d, cx, cy, u, -48, 20, -36, 34, fill=NAVY)
    icon_poly(d, cx, cy, u, [(24, -36), (56, 10), (-8, 10)], fill=I_RED)
    icon_rect(d, cx, cy, u, 22, -24, 26, -2, fill=I_CREAM)
    icon_rect(d, cx, cy, u, 22, 2, 26, 6, fill=I_CREAM)
    icon_rect(d, cx, cy, u, 6, 18, 54, 40, fill=I_GOLD)
    icon_line(d, cx, cy, u, [(6, 18), (30, 33), (54, 18)], NAVY, 2)


def icon_truck(d, cx, cy, h):
    """Slate tipper tipping cream stones onto a red minitruck."""
    u = h / 100.0
    icon_rect(d, cx, cy, u, -74, 6, 8, 12, fill=I_SLATE)
    icon_poly(d, cx, cy, u, [(-74, -8), (-50, -8), (-50, 6), (-74, 6)], fill=I_SLATE)
    icon_rect(d, cx, cy, u, -70, -4, -56, 2, fill=I_CREAM)
    icon_poly(d, cx, cy, u, [(-48, 4), (2, -36), (12, -22), (-42, 10)], fill=I_SLATE)
    icon_line(d, cx, cy, u, [(-48, 4), (2, -36)], I_CREAM, 2)
    for wx in (-62, -30, 2):
        icon_ell(d, cx, cy, u, wx - 8, 10, wx + 8, 26, fill=I_SLATE)
        icon_ell(d, cx, cy, u, wx - 3, 15, wx + 3, 21, fill=NAVY)
    for dx, dy, r in ((20, -22, 4), (28, -10, 5), (22, 2, 4), (34, -18, 3)):
        icon_ell(d, cx, cy, u, dx - r, dy - r, dx + r, dy + r, fill=I_CREAM)
    icon_rect(d, cx, cy, u, 38, 18, 72, 30, fill=I_RED)
    icon_rect(d, cx, cy, u, 58, 10, 72, 18, fill=I_RED)
    for wx in (46, 66):
        icon_ell(d, cx, cy, u, wx - 6, 28, wx + 6, 40, fill=I_SLATE)
        icon_ell(d, cx, cy, u, wx - 2, 32, wx + 2, 36, fill=NAVY)


def icon_pin(d, cx, cy, h):
    """Cream map pin, gold handshake, red withdrawal arrow."""
    u = h / 100.0
    icon_ell(d, cx, cy, u, -84, -36, -44, 4, fill=I_CREAM)
    icon_poly(d, cx, cy, u, [(-74, -6), (-54, -6), (-64, 30)], fill=I_CREAM)
    icon_ell(d, cx, cy, u, -72, -26, -56, -10, fill=NAVY)
    icon_line(d, cx, cy, u, [(-30, -16), (-2, -6)], I_GOLD, 5)
    icon_line(d, cx, cy, u, [(38, -20), (4, -6)], I_GOLD, 5)
    icon_rr(d, cx, cy, u, -8, -12, 12, 2, 4, fill=I_GOLD)
    icon_line(d, cx, cy, u, [(18, 28), (54, 28)], I_RED, 2)
    icon_poly(d, cx, cy, u, [(48, 19), (62, 28), (48, 37)], fill=I_RED)


def icon_health(d, cx, cy, h):
    """Cream medical cross, red virus, gold barrier."""
    u = h / 100.0
    icon_rect(d, cx, cy, u, -82, -12, -30, 8, fill=I_CREAM)
    icon_rect(d, cx, cy, u, -64, -34, -48, 30, fill=I_CREAM)
    icon_ell(d, cx, cy, u, -16, -32, 24, 8, fill=I_RED)
    for deg in range(0, 360, 45):
        a = math.radians(deg)
        x0, y0 = 4 + 19 * math.cos(a), -12 + 19 * math.sin(a)
        x1, y1 = 4 + 27 * math.cos(a), -12 + 27 * math.sin(a)
        icon_line(d, cx, cy, u, [(x0, y0), (x1, y1)], I_RED, 1)
        icon_ell(d, cx, cy, u, x1 - 2, y1 - 2, x1 + 2, y1 + 2, fill=I_RED)
    icon_ell(d, cx, cy, u, -4, -20, 2, -14, fill=NAVY)
    icon_ell(d, cx, cy, u, 10, -10, 16, -4, fill=NAVY)
    icon_rect(d, cx, cy, u, 30, 16, 80, 32, fill=I_GOLD)
    for i in range(4):
        x = 40 + i * 12
        icon_line(d, cx, cy, u, [(x, 16), (x - 8, 32)], NAVY, 2)
    icon_line(d, cx, cy, u, [(34, 32), (34, 40)], I_GOLD, 2)
    icon_line(d, cx, cy, u, [(76, 32), (76, 40)], I_GOLD, 2)


# ---------------------------------------------------------------- stories

LEADS = (
    ("01", "Nvidia reinstates Huang as CEO after spy scandal"),
    ("02", "Ukraine sinks Russian warship in Libyan port"),
    ("03", "Bangladesh factions clash; at least 30 hurt"),
)

STATS = (
    ("$1tn", "NVIDIA VALUE ADDED"),
    ("1", "RUSSIAN WARSHIP SUNK"),
    ("74", "LASHES FOR IRANIAN SINGER"),
    ("14", "PKK BASES EVACUATED"),
    ("7", "KILLED IN PAKISTAN CRASH"),
)

CARDS = (
    dict(
        tag="USA · BUSINESS",
        headline="Nvidia reinstates Huang as CEO",
        body="The board brings back Jensen Huang less than two weeks after his resignation over the Alice Huang spy scandal; Democrats vow a probe.",
        icon=icon_chip,
    ),
    dict(
        tag="LIBYA · WAR",
        headline="Ukraine sinks Russian warship in Benghazi",
        body="Zelensky praises an 'exemplary' naval drone operation; Libya's UN mission urges a probe into the port attack.",
        icon=icon_ship,
    ),
    dict(
        tag="BANGLADESH · POLITICS",
        headline="Awami League factions clash; 30 hurt",
        body="Rival factions detonate crude bombs and vandalise shops in Gopalganj; BNP factions clash in Jhenaidah.",
        icon=icon_ballot,
    ),
    dict(
        tag="RUSSIA · WAR",
        headline="Drone attack hits two Russian refineries",
        body="Ukraine strikes the Perm and Novoshakhtinsk refineries in a large-scale attack across western Russia.",
        icon=icon_refinery,
    ),
    dict(
        tag="SPAIN · LAW",
        headline="Puigdemont granted amnesty",
        body="The Supreme Court closes the case against the former Catalan president over the 2017 independence declaration.",
        icon=icon_gavel,
    ),
    dict(
        tag="IRAN · RIGHTS",
        headline="Singer receives 74 lashes for bareheaded concert",
        body="Parastoo Ahmadi is flogged for performing without a hijab, Iran's judiciary says.",
        icon=icon_mic,
    ),
    dict(
        tag="MYANMAR · RIGHTS",
        headline="UK sanctions generals and recognises Rohingya genocide",
        body="Foreign Secretary Ed Miliband targets five military leaders and formally recognises the genocide.",
        icon=icon_flag,
    ),
    dict(
        tag="SPORT · WORLD CUP",
        headline="FIFA names 2031 and 2035 World Cup hosts",
        body="Costa Rica, Jamaica, Mexico and the US host 2031; England, Scotland, Wales and Northern Ireland host 2035.",
        icon=icon_trophy,
    ),
    dict(
        tag="EUROPE · SECURITY",
        headline="Bomb threats close hundreds of schools",
        body="Schools across Denmark and Germany receive emailed threats; police order them to stay open as normal.",
        icon=icon_school,
    ),
    dict(
        tag="PAKISTAN · DISASTER",
        headline="Truck crash kills seven in Punjab",
        body="A truck loaded with stones overturns onto a minitruck, killing seven and injuring two.",
        icon=icon_truck,
    ),
    dict(
        tag="IRAQ · PEACE",
        headline="PKK withdraws from 14 more bases",
        body="Turkish intelligence says the PKK has evacuated 14 additional bases in northern Iraq as disarmament advances.",
        icon=icon_pin,
    ),
    dict(
        tag="DR CONGO · HEALTH",
        headline="Fighting traps Ebola responders in Ituri",
        body="The WHO says heavy fighting in Ituri is blocking responders from reaching patients in the Ebola outbreak.",
        icon=icon_health,
    ),
)

BRIEFS = (
    ("ITALY", "A student dies on a hunger strike over housing at Sapienza University in Rome."),
    ("TAJIKISTAN", "Dushanbe begins withdrawing from the International Criminal Court."),
    ("CANADA", "Quebec's top court suspends the law that made the monarch's oath optional."),
    ("UK", "The GTA VI hacker is sentenced to seven years but walks free on licence."),
    ("FRANCE", "Gisèle Pelicot is suing a publisher over nude photos used in a book campaign."),
    ("JAPAN", "The Tamagotchi digital pet turns 30."),
)

DATE_CHECK = (
    "DATE CHECK · Every story above was reported on Monday 23 November 2026, in a "
    "time zone where it was already the 23rd. Nvidia's board reinstated Huang and the "
    "first market reaction came on the 23rd. Left out as 22 November's news: COP31's "
    "collapse in Antalya. The Benghazi strike and the refinery attack were reported on the 23rd."
)

FOOTER = (
    "Stories from Monday 23 November 2026, each reported or first published that day. "
    "Sources: BBC · Al Jazeera · NYT · SCMP · The Straits Times · Japan Times · CNA · "
    "CNBC · France 24 · Arab News · UN News · DW."
)


# ---------------------------------------------------------------- the map
# A coarse land mask (120 columns x 26 rows) rasterised once from Natural Earth's
# 110m land polygons, projected equirectangularly between 78N and 50S.

LAND_MASK = (
    "000000000000000000011111111111111110111111111111111111000000000001000000000000111110000111111111110000000011010000000000",
    "100001111111111111111111111111111111110001111111111110000000000000111111000001101111111111111111111111111111111111111111",
    "111011111111111111111111111111111011111000111111100011100000000111111111111111111111111111111111111111111111111111111111",
    "000011111111111111111111111110000011111000011100000000000000011111011111111111111111111111111111111111111111111111111111",
    "000000111000000111111111111111111011111110000000000000000111001111111111111111111111111111111111111111111110000011000000",
    "000000000000000001111111111111111111111111000000000000000111111111111111111111111111111111111111111111111111000010000000",
    "000000000000000000111111111111111111111111000000000000000001111111111111111111111111111111111111111111111111000000000000",
    "000000000000000000111111111111111111100000000000000000000111101111111111111111111111111111111111111111110011000000000000",
    "000000000000000000011111111111111110000000000000000000000111111110010111111111111111111111111111111110101110000000000000",
    "000000000000000000000111111111111000000000000000000000001111111111111111111111111111111111111111111110010000000000000000",
    "000000000000000000000011111100001100000000000000000000011111111111111111111111111111111111111111111110000000000000000000",
    "000000000000000000000000111100101110100000000000000000111111111111111111111111110001111111111111111000000000000000000000",
    "000000000000000000000000001111110001100000000000000000111111111111111111111111100000111100011111100010000000000000000000",
    "000000000000000000000000000000111001111100000000000000111111111111111111111110000000011000001111100011000000000000000000",
    "000000000000000000000000000000001111111111100000000000001111111111111111111110000000001000001100001101000000000000000000",
    "000000000000000000000000000000000111111111110000000000000000000111111111111100000000000000001110111110100000000000000000",
    "000000000000000000000000000000000111111111111111000000000000000111111111110000000000000000000111111110111111101000000000",
    "000000000000000000000000000000000111111111111111100000000000000011111111110000000000000000000001110111000011110001000000",
    "000000000000000000000000000000000011111111111111000000000000000011111111110010000000000000000000000000111101000000000000",
    "000000000000000000000000000000000000111111111110000000000000000011111111101110000000000000000000000011111111100000000001",
    "000000000000000000000000000000000000111111111100000000000000000011111111001100000000000000000000001111111111111000000000",
    "000000000000000000000000000000000000111111110000000000000000000001111110000000000000000000000000001111111111111000000000",
    "000000000000000000000000000000000000111111100000000000000000000000111100000000000000000000000000001111111111111000000000",
    "000000000000000000000000000000000001111110000000000000000000000000000000000000000000000000000000000000000011110000000011",
    "000000000000000000000000000000000001111000000000000000000000000000000000000000000000000000000000000000000000110000001110",
    "000000000000000000000000000000000001110000000000000000000000000000000000000000000000000000000000000000000000000000001000",
)

MAP_LON_LEFT, MAP_LON_RIGHT = -180.0, 180.0
MAP_LAT_TOP, MAP_LAT_BOTTOM = 78.0, -50.0

MARKERS = (
    (1, -77.0, 38.5),    # US east coast
    (2, 20.0, 32.0),     # Benghazi
    (3, 88.5, 24.0),     # Bangladesh
    (4, 56.0, 58.0),     # Perm
    (5, -4.0, 40.0),     # Spain
    (6, 56.0, 32.0),     # Iran
    (7, 100.0, 22.0),    # Myanmar
    (8, -102.0, 23.0),   # Mexico
    (9, 10.0, 56.0),     # Denmark
    (10, 74.0, 31.0),    # Punjab
    (11, 40.0, 34.0),    # northern Iraq
    (12, 30.0, 2.0),     # Ituri
)


def marker_xy(x, y, w, h, lon, lat):
    mx = x + (lon - MAP_LON_LEFT) / (MAP_LON_RIGHT - MAP_LON_LEFT) * w
    my = y + (MAP_LAT_TOP - lat) / (MAP_LAT_TOP - MAP_LAT_BOTTOM) * h
    return mx, my


def draw_map(d, x, y, w, h):
    pitch = 4
    rows = len(LAND_MASK)
    cols = len(LAND_MASK[0])
    assert rows * pitch == h and cols * pitch == w
    for r in range(rows):
        for c in range(cols):
            if LAND_MASK[r][c] == "1":
                d.rectangle((x + c * pitch, y + r * pitch,
                             x + c * pitch + 3, y + r * pitch + 3), fill=MAP_FILL)
    for r in range(rows):
        for c in range(cols):
            if LAND_MASK[r][c] == "1":
                d.rectangle((x + c * pitch + 1, y + r * pitch + 1,
                             x + c * pitch + 2, y + r * pitch + 2), fill=MAP_DOT)

    placed = []
    for number, lon, lat in MARKERS:
        mx, my = marker_xy(x, y, w, h, lon, lat)
        cell_c = int((mx - x) // pitch)
        cell_r = int((my - y) // pitch)
        assert LAND_MASK[cell_r][cell_c] == "1", f"map marker {number} falls in the sea"
        for other, ox, oy in placed:
            gap = math.hypot(mx - ox, my - oy)
            assert gap >= 14.0, f"map markers {other} and {number} are {gap:.1f}px apart"
        placed.append((number, mx, my))
        d.ellipse((mx - 7, my - 7, mx + 7, my + 7), fill=PAPER)
        d.ellipse((mx - 6, my - 6, mx + 6, my + 6), fill=RED)
        d.text((mx, my + 3), str(number), font=font("ui_bold", 7), fill=CREAM, anchor="ms")


# ---------------------------------------------------------------- sections


def draw_masthead(d):
    rect(d, 0, 0, W, 150, NAVY)
    tracked(d, MARGIN, 18, "THE WORLD IN ONE DAY", font("ui_bold", 10), CREAM_80, 3)
    tracked(d, MARGIN, 34, "MONDAY", font("ui_bold", 22), GOLD, 5)
    put_l(d, MARGIN, 58, "23 November 2026", font("georgia_bold", 74), CREAM)
    tracked(d, 1002, 112, "12 STORIES · 8 REGIONS · 6 BRIEFS", font("ui_bold", 10),
            CREAM_80, 1, align="right")


def draw_leads(d):
    lead_font = font("georgia_bold", 17)
    for index, (number, headline) in enumerate(LEADS):
        x = COL_X[index]
        rect(d, x, 156, COL_W, 2, RED)
        put_l(d, x, 161, number, font("ui_bold", 9), RED)
        lines = wrap_balanced(d, headline, lead_font, COL_W, 2)
        paragraph(d, x, 173, lines, lead_font, INK, 18)


def draw_stats(d):
    rect(d, MARGIN, 220, CONTENT, 1, RULE)
    rect(d, MARGIN, 273, CONTENT, 1, RULE)
    cell = CONTENT / 5
    for index, (number, label) in enumerate(STATS):
        cx = MARGIN + cell * index + cell / 2
        put_c(d, cx, 227, number, font("georgia_bold", 30), INK)
        tracked(d, cx, 256, label, font("ui_bold", 9), MUTED, 1, align="center")


def draw_band_dots(d, x, y, w, h):
    for yy in range(y + 7, y + h - 3, 16):
        for xx in range(x + 8, x + w - 3, 16):
            d.rectangle((xx, yy, xx + 1, yy + 1), fill=BAND_DOT)


def draw_card(d, index, card, x, y, height, band, head_size, body_size, body_pitch):
    rect(d, x, y, COL_W, height, CARD)
    d.rectangle((x, y, x + COL_W - 1, y + height - 1), outline=RULE)

    # illustration band
    rect(d, x, y, COL_W, band, NAVY)
    draw_band_dots(d, x, y, COL_W, band)
    cy = y + band / 2
    d.ellipse((x + 9, cy - 7, x + 23, cy + 7), fill=RED)
    d.text((x + 16, cy + 3), f"{index + 1:02d}", font=font("ui_bold", 8), fill=CREAM, anchor="ms")
    card["icon"](d, x + COL_W / 2, cy, band)

    # tag bar
    bar_y = y + band
    date = "23 NOV"
    date_font = font("ui_bold", 9)
    date_w = text_w(d, date, date_font)
    bar_w = COL_W - 6 - date_w - 8
    tag_w = text_w(d, card["tag"], font("ui_bold", 9))
    assert tag_w <= bar_w - 12, (card["tag"], tag_w, bar_w)
    rect(d, x, bar_y, bar_w, 14, RED)
    put_l(d, x + 6, bar_y + 3, card["tag"], font("ui_bold", 9), CREAM)
    put_r(d, x + COL_W - 6, bar_y + 3, date, date_font, MUTED)

    # headline
    head_font = font("georgia_bold", head_size)
    head_pitch = head_size + 1
    lines = wrap_balanced(d, card["headline"], head_font, COL_W - 12, 2)
    head_top = bar_y + 14 + 4
    if len(lines) == 1:
        head_top += head_pitch // 2
    paragraph(d, x + 6, head_top, lines, head_font, INK, head_pitch)

    # body: fixed grid position across a row, whatever the headline count
    body_top = bar_y + 14 + 4 + cap_height(head_font) + head_pitch + 6
    body_font = font("ui", body_size)
    body_lines = wrap_balanced(d, card["body"], body_font, COL_W - 12, 3 if body_size == 12 else 2)
    paragraph(d, x + 6, body_top, body_lines, body_font, BODY, body_pitch)

    last_baseline = body_top + cap_height(body_font) + body_pitch * (len(body_lines) - 1)
    assert last_baseline <= y + height - 6, (card["headline"], last_baseline - (y + height))


ROW_SPEC = (
    (284, 168, 52, 21, 12, 15),
    (458, 126, 40, 19, 11, 13),
    (590, 126, 40, 19, 11, 13),
    (722, 126, 40, 19, 11, 13),
)


def draw_cards(d):
    for index, card in enumerate(CARDS):
        row = index // 3
        col = index % 3
        y, height, band, head_size, body_size, body_pitch = ROW_SPEC[row]
        draw_card(d, index, card, COL_X[col], y, height, band, head_size, body_size, body_pitch)


def draw_bottom(d):
    rect(d, MARGIN, 856, 480, 2, NAVY)
    rect(d, 514, 856, 488, 2, NAVY)

    tracked(d, MARGIN, 861, "WHERE IT HAPPENED", font("ui_bold", 9), MUTED, 2)
    tracked(d, 502, 861, "NUMBERS MATCH THE CARDS", font("ui_bold", 7), MUTED, 1, align="right")
    draw_map(d, MARGIN, 870, 480, 104)

    tracked(d, 514, 861, "ALSO ON THE DAY", font("ui_bold", 9), MUTED, 2)
    brief_font = font("ui", 9)
    for index, (place, brief) in enumerate(BRIEFS):
        col = index // 3
        row = index % 3
        x = 514 + col * 252
        y = 870 + row * 35
        tracked(d, x, y, place, font("ui_bold", 8), RED, 1)
        lines = wrap_balanced(d, brief, brief_font, 236, 2)
        paragraph(d, x, y + 11, lines, brief_font, INK, 11)


def draw_date_check(d):
    rect(d, MARGIN, 982, CONTENT, 25, BLUSH)
    rect(d, MARGIN, 982, 3, 25, RED)
    lines = wrap_balanced(d, DATE_CHECK, font("ui", 9), 952, 2)
    for line in lines:
        assert text_w(d, line, font("ui", 9)) <= 952, line
    paragraph(d, MARGIN + 12, 984, lines, font("ui", 9), INK, 11)


def draw_footer(d):
    assert text_w(d, FOOTER, font("ui", 8)) <= CONTENT, "footer too wide"
    put_l(d, MARGIN, 1010, FOOTER, font("ui", 8), MUTED)


# ---------------------------------------------------------------- build


def build():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    draw_masthead(d)
    draw_leads(d)
    draw_stats(d)
    draw_cards(d)
    draw_bottom(d)
    draw_date_check(d)
    draw_footer(d)
    return img


def main():
    img = build()
    target = os.path.join(HERE, "entry.png")
    img.save(target, "PNG", optimize=True)
    img.resize((300, 300), Image.Resampling.LANCZOS).save(
        os.path.join(HERE, "preview-300.png"), "PNG", optimize=True
    )
    print(f"wrote {target} ({os.path.getsize(target)} bytes)")


if __name__ == "__main__":
    main()
