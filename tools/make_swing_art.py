"""The swinging bars (the robot-face "eyebrows" on the professional course): every drawing of the bar as a PNG for
patch 150, art/swing_bar/:

    pose_00.png ... pose_10.png      the game's 11 drawings, in swing order (piece words 0x86DA ... 0x8702)
    pose_00_1/2/3.png ...            three in-betweens from each one to the next (1/4, 1/2, 3/4 of the way)

All 128 x 128, the bracket's bolt (the pivot) at the same spot, indexed in the bar's palette (148; colour 0 =
see-through). The in-betweens are the nearer original drawing turned around the bolt. Existing files are kept (so
hand touch-ups survive) - --force rewrites them all, --preview just makes the preview GIF.

    /opt/homebrew/bin/python3 tools/make_swing_art.py [--force] [--preview]
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hackbuild, png_tiles

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "art", "swing_bar")
PIECES = list(range(0x86DA, 0x8703, 4))         # the 11 drawings, in swing order
BANK, ANIMS = 0x0C, (0x54, 0x58)                # the two animations that use them
PAL = [0x0000, 0x4F00, 0x4F00, 0x4F00, 0x1000, 0x1111, 0x1222, 0x5233, 0x5344, 0x5455, 0x1677, 0x1899, 0x59BB,
       0x3BCC, 0x7CEE, 0x6FFF]                  # palette 148: the object's 144 + the lists' offset 4 (read in play)
CANVAS = 128
PIVOT = (-3.0, 2.5)                             # the bolt, from the object's position (x right, y down) - fitted
ORIGIN = (-67, -62)                             # the canvas's top-left, from the object's position
STEPS = [0, -16, -32, -49, -67, -87, -108, -128, -146, -162, -178]   # each drawing's angle (degrees), fitted


rgb = png_tiles.neo_to_rgb                      # a colour word -> (r, g, b)


def palette():
    pal = [rgb(w) for w in PAL]
    pal[0] = (255, 0, 255)
    return pal


def u32(rom, a):
    return int.from_bytes(rom.data[a:a + 4], "big")


def anim(rom, idx):
    """[(duration, flags, boxes, [(piece word, x, y)])] of animation idx of BANK."""
    rec = u32(rom, u32(rom, u32(rom, 0x48000) + BANK) + idx)
    fl, out = rec & 0xFFFFFF, []
    for k in range(rec >> 24):
        a = fl + 4 * k
        dur, flags = rom.data[a], rom.data[a + 1]
        d = fl + int.from_bytes(rom.data[a + 2:a + 4], "big", signed=True)
        boxes = [rom.u16(d + 2 * i) for i in range(bin(flags & 0x1F).count("1"))]
        d += 2 * len(boxes)
        pieces = []
        while True:
            w = rom.u16(d)
            pieces.append((w, int.from_bytes(rom.data[d + 2:d + 3], "big", signed=True),
                           int.from_bytes(rom.data[d + 3:d + 4], "big", signed=True)))
            d += 4
            if w & 0x8000:
                break
        out.append((dur, flags, boxes, pieces))
    return out


def picture(rom, w):
    """A piece's pixels: {(x, y): colour}, x / y from the object's position."""
    e = 0x5100C + (w & 0x7FFC)
    v = u32(rom, e)
    fmt, cols, rows = v >> 29, ((v >> 24) & 31) + 1, ((v >> 20) & 15) + 1
    at = e + (v & 0xFFFFF)
    out = {}
    for k in range(cols * rows):
        if fmt == 1:
            p, t = 0, rom.u16(at + 2 + 2 * k)
        elif fmt == 5:
            p, t = rom.data[at + 3 * k], rom.u16(at + 3 * k + 1)
        else:
            raise SystemExit("piece 0x%X: format %d" % (w, fmt))
        c, r = divmod(k, rows)
        for y, row in enumerate(rom.sprite_tile(t)):
            for x, val in enumerate(row):
                if val:
                    assert p == 0, "piece 0x%X: a palette offset" % w
                    out[(16 * c + x, 16 * r + y)] = val
    return out


def placed(rom):
    """{piece word: its pixels at their place from the object}."""
    where = {}
    for idx in ANIMS:
        for f in anim(rom, idx):
            for w, x, y in f[3]:
                where[w | 0x8000] = (x, -y)
    out = {}
    for w in PIECES:
        dx, dy = where[w]
        out[w] = {(x + dx, y + dy): v for (x, y), v in picture(rom, w).items()}
    return out


def split(drawings):
    """The bracket (the pixels all but two drawings share) and each drawing's wire."""
    from collections import Counter
    cnt = Counter((p, v) for g in drawings.values() for p, v in g.items())
    bracket = {p: v for (p, v), n in cnt.items() if n >= len(drawings) - 2}
    wires = {w: {p: v for p, v in g.items() if bracket.get(p) != v} for w, g in drawings.items()}
    return bracket, wires


def rotate(wire, deg):
    """The wire turned deg degrees around the bolt (4 x 4 samples a pixel, the commonest wins)."""
    px, py = PIVOT
    ca, sa = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    xs = [p[0] for p in wire]; ys = [p[1] for p in wire]
    R = int(max(max(abs(x - px) for x in xs), max(abs(y - py) for y in ys))) + 3
    out = {}
    for Y in range(int(py) - R, int(py) + R):
        for X in range(int(px) - R, int(px) + R):
            votes = {}
            for j in range(4):
                for i in range(4):
                    u, v = X + (i + .5) / 4 - px, Y + (j + .5) / 4 - py
                    q = wire.get((math.floor(ca * u + sa * v + px), math.floor(-sa * u + ca * v + py)))
                    votes[q] = votes.get(q, 0) + 1
            q = max(votes, key=votes.get)
            if q is not None and (votes[q] >= 5 or votes.get(None, 0) < 8):
                out[(X, Y)] = q
    return out


def to_canvas(pix):
    rows = [[0] * CANVAS for _ in range(CANVAS)]
    for (x, y), v in pix.items():
        X, Y = x - ORIGIN[0], y - ORIGIN[1]
        assert 0 <= X < CANVAS and 0 <= Y < CANVAS, "outside the canvas: %d, %d" % (x, y)
        rows[Y][X] = v
    return rows


def names():
    """[(file name, (pose, quarter))] - quarter 0 = the drawing itself."""
    out = []
    for i in range(len(PIECES)):
        out.append(("pose_%02d.png" % i, (i, 0)))
        if i + 1 < len(PIECES):
            out += [("pose_%02d_%d.png" % (i, q), (i, q)) for q in (1, 2, 3)]
    return out


def inbetween(i, j, q):
    """The drawing (pose, quarter) q quarters of the way from drawing i to drawing j (j may be a few drawings away:
    the swing's end wobbles)."""
    p = 4 * i + (j - i) * q
    return (p // 4, p % 4)


def make(force=False):
    _, rom = hackbuild.load_original()
    drawings = placed(rom)
    bracket, wires = split(drawings)
    os.makedirs(OUT, exist_ok=True)
    made = 0
    for name, (i, q) in names():
        path = os.path.join(OUT, name)
        if os.path.exists(path) and not force:
            continue
        if q == 0:
            pix = drawings[PIECES[i]]
        else:
            a, b = PIECES[i], PIECES[i + 1]
            turn = (STEPS[i + 1] - STEPS[i]) * q / 4
            pix = rotate(wires[a], turn) if q < 2 else rotate(wires[b], turn - (STEPS[i + 1] - STEPS[i]))
            pix.update(bracket)
        png_tiles.write_indexed(path, to_canvas(pix), palette())
        made += 1
    print("art/swing_bar: %d drawings written (%d kept)" % (made, len(names()) - made))


def preview():
    """art/swing_bar/preview.gif: the swing as the console will show it (animation 0x58, speed 2: 8 frames a drawing,
    a new drawing every 2), beside the original."""
    from PIL import Image
    _, rom = hackbuild.load_original()
    pal = palette()
    pal[0] = (0, 0, 60)
    load = lambda n: png_tiles.read_indices(os.path.join(OUT, n), palette())
    art = {key: load(n) for n, key in names()}
    frames = anim(rom, 0x58)
    seq = [PIECES.index(f[3][0][0] | 0x8000) for f in frames]
    Z = 2
    def img(px, im, ox):
        for y, row in enumerate(px):
            for x, v in enumerate(row):
                if v:
                    im.paste(pal[v], (ox + x * Z, y * Z, ox + x * Z + Z, y * Z + Z))
    out = []
    for k, i in enumerate(seq):
        j = seq[(k + 1) % len(seq)]
        for f in range(8):
            key = inbetween(i, j, f // 2)
            im = Image.new("RGB", (2 * CANVAS * Z + 10, CANVAS * Z), (0, 0, 60))
            img(art[(i, 0)], im, 0)
            img(art[key], im, CANVAS * Z + 10)
            out.append(im)
    path = os.path.join(OUT, "preview.gif")
    out[0].save(path, save_all=True, append_images=out[1:], duration=20, loop=0)
    print("wrote", path)


if __name__ == "__main__":
    if "--preview" not in sys.argv:
        make(force="--force" in sys.argv)
    preview()
