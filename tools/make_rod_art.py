"""Make the smaller Zap-Rod balls (art/rod/): the ball's 5 animation frames (piece entries 0x51E54-0x51E64, 2 x 2
tiles each, palette 224) redrawn at 80% (90% was tried too), as indexed PNGs the user can touch up. Patch 100 reads them.

Needs Pillow (the shell's python3 has a broken one here): /opt/homebrew/bin/python3 tools/make_rod_art.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import hackbuild
from png_tiles import write_indexed

ROOT = hackbuild.ROOT
OUT = os.path.join(ROOT, "art", "rod")
ENTRIES = [0x51E54, 0x51E58, 0x51E5C, 0x51E60, 0x51E64]
# palette 224 in play (read 2026-11-15)
PAL = [0x0000, 0x0000, 0x3211, 0x7222, 0x5343, 0x7444, 0x1554, 0x7555, 0x3666, 0x7AAA, 0x5CCC, 0x7FFF, 0x0D83,
       0x0532, 0x0888, 0x397E]
SIZES = (80,)


def rgb(w):
    c5 = lambda v: v * 255 // 31
    return (c5(((w >> 7) & 0x1E) | ((w >> 14) & 1)), c5(((w >> 3) & 0x1E) | ((w >> 13) & 1)),
            c5(((w << 1) & 0x1E) | ((w >> 12) & 1)))


def frame_pixels(rom, entry):
    at = entry + (rom.u32(entry) & 0xFFFFF) + 2           # the list: a word, then 4 tiles (columns, top first)
    tiles = [rom.u16(at + 2 * k) for k in range(4)]
    px = [[0] * 32 for _ in range(32)]
    for k, t in enumerate(tiles):
        tx, ty = 16 * (k // 2), 16 * (k % 2)
        for y, row in enumerate(rom.sprite_tile(t)):
            px[ty + y][tx:tx + 16] = row
    return px


def main():
    os.makedirs(OUT, exist_ok=True)
    _, rom = hackbuild.load_original()
    pal = [rgb(w) for w in PAL]
    pal[0] = (255, 0, 255)
    for n, entry in enumerate(ENTRIES):
        px = frame_pixels(rom, entry)
        write_indexed(os.path.join(OUT, "ball_full_%d.png" % n), px, pal)
        used = sorted({v for row in px for v in row if v})
        ys = [y for y in range(32) if any(px[y])]
        xs = [x for x in range(32) if any(px[y][x] for y in range(32))]
        x0, x1, y0, y1 = xs[0], xs[-1] + 1, ys[0], ys[-1] + 1
        img = Image.new("RGBA", (x1 - x0, y1 - y0))
        for y in range(y0, y1):
            for x in range(x0, x1):
                v = px[y][x]
                img.putpixel((x - x0, y - y0), pal[v] + (255,) if v else (0, 0, 0, 0))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for size in SIZES:
            w, h = round(img.width * size / 100), round(img.height * size / 100)
            small = img.resize((w, h), Image.LANCZOS)
            out = [[0] * 32 for _ in range(32)]
            ox, oy = round(cx - w / 2), round(cy - h / 2)
            for y in range(h):
                for x in range(w):
                    r, g, b, a = small.getpixel((x, y))
                    if a > 110:
                        out[oy + y][ox + x] = min(used, key=lambda i: sum((p - q) ** 2 for p, q in zip(pal[i], (r, g, b))))
            write_indexed(os.path.join(OUT, "ball_%d_%d.png" % (size, n)), out, pal)
        print("frame %d: ball %dx%d at %d,%d" % (n, x1 - x0, y1 - y0, x0, y0))


if __name__ == "__main__":
    main()
