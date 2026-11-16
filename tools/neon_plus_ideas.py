"""Neon "Plus" ideas for the title screen's corner: each drawn as glass tubes (glow, tube, hot core), laid over
art/title_plus/title_screen.png, all on one sheet. Writes art/title_plus/ideas/ (sheet + each sign as a PNG).

    /opt/homebrew/bin/python3 tools/neon_plus_ideas.py
"""
import math, os, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TITLE = os.path.join(ROOT, "art", "title_plus", "title_screen.png")
OLD = os.path.join(ROOT, "art", "title_plus", "plus_neon_pink_lit.png")
OUT = os.path.join(ROOT, "art", "title_plus", "ideas")
SPOT = (256, 118)                # the sign's centre on the 320 x 224 screen (the old sign's middle)


def arc(cx, cy, rx, ry, a0, a1, n=24):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


# capitals, height H: polylines (a neon sign bends one tube where it can)
def caps(H):
    W = 0.62 * H
    P = [[(0, H), (0, 0), (W * 0.45, 0)] + arc(W * 0.45, H * 0.27, W * 0.55, H * 0.27, -90, 90)[1:] + [(0, H * 0.54)]]
    L = [[(0, 0), (0, H), (W * 0.85, H)]]
    U = [[(0, 0), (0, H * 0.62)] + arc(W / 2, H * 0.62, W / 2, H * 0.38, 180, 0) + [(W, 0)]]
    S = [arc(W / 2, H / 4, W / 2, H / 4, -20, -270, 30) + arc(W / 2, 3 * H / 4, W / 2, H / 4, -90, 160, 30)]
    return [(P, W), (L, W * 0.85), (U, W), (S, W)]


# rounded lowercase: x-height X, ascender up to 0, descender below
def lower(H):
    X, top = H * 0.6, H * 0.4
    W = 0.55 * H
    p = [[(0, top), (0, H + H * 0.35)], arc(W / 2, top + X / 2, W / 2, X / 2, 0, 360, 32)]
    l = [[(0, 0), (0, H - 2)] + arc(2, H - 2, 2, 2, 180, 90, 6)]
    u = [[(0, top), (0, H - X * 0.4)] + arc(W / 2, H - X * 0.4, W / 2, X * 0.4, 180, 0) + [(W, top), (W, H)]]
    s = [arc(W / 2, top + X / 4, W / 2, X / 4, -20, -270, 24) + arc(W / 2, top + 3 * X / 4, W / 2, X / 4, -90, 160, 24)]
    return [(p, W), (l, 4), (u, W), (s, W)]


def lay_out(glyphs, gap, slant=0.0):
    out, x = [], 0
    for strokes, w in glyphs:
        out += [[(px + x, py) for px, py in s] for s in strokes]
        x += w + gap
    return out


def transform(strokes, slant=0.0, turn=0.0, scale=1.0):
    pts = [p for s in strokes for p in s]
    cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    c, s_ = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    def f(p):
        x, y = (p[0] - cx) * scale, (p[1] - cy) * scale
        x -= slant * y
        return (x * c - y * s_, x * s_ + y * c)
    return [[f(p) for p in s] for s in strokes]


def seg_dist(px, py, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def tubes(img, strokes, colours, at, widths=(0.55, 1.35, 2.5), dither=False):
    """Draw tubes onto img (RGB) centred at `at`. colours: (core, tube, glow); widths: their half-widths."""
    core, tube, glow = colours
    segs = [(s[k], s[k + 1]) for s in strokes for k in range(len(s) - 1)]
    pts = [p for s in strokes for p in s]
    x0, x1 = int(min(p[0] for p in pts) - 4), int(max(p[0] for p in pts) + 5)
    y0, y1 = int(min(p[1] for p in pts) - 4), int(max(p[1] for p in pts) + 5)
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = min(seg_dist(x + 0.5 - 0.5, y + 0.5 - 0.5, a, b) for a, b in segs)
            X, Y = x + at[0], y + at[1]
            if not (0 <= X < img.width and 0 <= Y < img.height):
                continue
            if d <= widths[0] and core:
                img.putpixel((X, Y), core)
            elif d <= widths[1]:
                img.putpixel((X, Y), tube)
            elif d <= widths[2] and glow and (not dither or (X + Y) % 2 == 0 or d <= widths[1] + 0.6):
                img.putpixel((X, Y), glow)


def q(c):                        # to the Neo Geo's colours (5 bits a channel, near enough)
    return tuple(v & 0xF8 for v in c)


PINK = q((255, 90, 200)), q((255, 230, 245)), q((110, 0, 70))
CYAN = q((40, 230, 255)), q((230, 255, 255)), q((0, 70, 120))
YELLOW = q((255, 210, 40)), q((255, 255, 210)), q((120, 60, 0))
GREEN = q((60, 255, 90)), q((230, 255, 230)), q((0, 90, 20))
ORANGE = q((255, 120, 30)), q((255, 235, 200)), q((120, 30, 0))
RED = q((255, 40, 40)), q((255, 220, 220)), q((100, 0, 0))
DARK = q((90, 70, 100))          # an unlit tube


def sign(img, strokes, col, centre=SPOT, **kw):
    tube, core, glow = col
    tubes(img, strokes, (core, tube, glow), centre, **kw)


def idea_old(img):
    old = Image.open(OLD).convert("RGBA")
    img.paste(old, (224, 95), old.split()[3])


def idea_caps(img, col=CYAN, turn=-14):
    sign(img, transform(lay_out(caps(16), 5), slant=0.25, turn=turn), col)


def idea_lower(img):
    sign(img, transform(lay_out(lower(19), 4.5), slant=0.2, turn=-12), PINK)


def idea_framed(img):
    letters = transform(lay_out(caps(13), 4), slant=0.0, turn=-10)
    w, h = 56, 26
    box = [arc(0, 0, 1, 1, 0, 1)]   # placeholder replaced below
    r = 5
    frame = (arc(-w / 2 + r, -h / 2 + r, r, r, 180, 270, 6) + arc(w / 2 - r, -h / 2 + r, r, r, 270, 360, 6) +
             arc(w / 2 - r, h / 2 - r, r, r, 0, 90, 6) + arc(-w / 2 + r, h / 2 - r, r, r, 90, 180, 6))
    frame.append(frame[0])
    frame = transform([frame, [(-w / 2, -h / 2), (w / 2, h / 2)]], turn=-10)[:1]
    sign(img, frame, PINK)
    sign(img, letters, YELLOW, widths=(0.5, 1.2, 2.2))


def idea_symbol(img):
    a = 9
    plus = [[(-a, 0), (a, 0)], [(0, -a), (0, a)]]
    sign(img, transform(plus, turn=0), RED, centre=(SPOT[0] - 22, SPOT[1] + 2), widths=(0.9, 2.2, 3.6))
    sign(img, transform(lay_out(caps(12), 4), slant=0.2, turn=-8), ORANGE, centre=(SPOT[0] + 10, SPOT[1] + 2),
         widths=(0.5, 1.2, 2.2))


def idea_flicker(img):
    s = transform(lay_out(caps(16), 5), slant=0.25, turn=-14)
    pts = sorted(range(len(s)), key=lambda k: min(p[0] for p in s[k]))
    lit = [s[k] for k in pts if k != 2]
    sign(img, lit, GREEN)
    tubes(img, [s[2]], (None, DARK, None), SPOT)          # the U's tube: out


def idea_bolt(img):
    sign(img, transform(lay_out(caps(16), 5), slant=0.25, turn=-10), YELLOW, centre=(SPOT[0], SPOT[1] - 4))
    bolt = [[(-24, 0), (-6, -2), (-3, 3), (8, 0), (11, 5), (26, 1)]]
    sign(img, transform(bolt, turn=-10), CYAN, centre=(SPOT[0], SPOT[1] + 12), widths=(0.4, 1.0, 2.0))


def idea_glow(img):
    sign(img, transform(lay_out(lower(19), 4.5), slant=0.3, turn=-16), CYAN, widths=(0.6, 1.4, 3.6), dither=True)


def idea_two(img):
    s = transform(lay_out(caps(16), 5), slant=0.25, turn=-14)
    order = sorted(s, key=lambda st: min(p[0] for p in st))
    for k, st in enumerate(order):
        sign(img, [st], [PINK, CYAN][k % 2])


IDEAS = [
    ("1  the first try (script, pink)", idea_old),
    ("2  tube capitals, cyan", idea_caps),
    ("3  rounded lowercase, pink", idea_lower),
    ("4  sign with a frame tube", idea_framed),
    ("5  big + and small PLUS", idea_symbol),
    ("6  broken tube (the U is out)", idea_flicker),
    ("7  capitals + a lightning tube", idea_bolt),
    ("8  wide soft glow (dithered)", idea_glow),
    ("9  letters in two colours", idea_two),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    base = Image.open(TITLE).convert("RGB")
    crop = (150, 50, 320, 170)
    Z = 3
    cw, ch = (crop[2] - crop[0]) * Z, (crop[3] - crop[1]) * Z
    cols, pad, lab = 3, 12, 26
    rows = (len(IDEAS) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + lab + pad) + pad), (30, 30, 30))
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
    d = ImageDraw.Draw(sheet)
    for k, (name, f) in enumerate(IDEAS):
        img = base.copy()
        f(img)
        img.save(os.path.join(OUT, "idea_%d.png" % (k + 1)))
        part = img.crop(crop).resize((cw, ch), Image.NEAREST)
        x, y = pad + (k % cols) * (cw + pad), pad + (k // cols) * (ch + lab + pad)
        d.text((x, y), name, fill=(240, 240, 240), font=font)
        sheet.paste(part, (x, y + lab))
    out = os.path.join(OUT, "neon_ideas.png")
    sheet.save(out)
    print("wrote", out)
    subprocess.run(["open", "-a", "Safari", out])


if __name__ == "__main__":
    main()
