"""Preview a menu background block (art/menu_bg/*.png) as the game shows it: repeated across a screen-sized area,
in each of the six colour sets the game's screens use. Checks the size (80 or 160 wide, 96 tall) and the colours.

    python3 tools/menu_bg_preview.py art/menu_bg/template_160.png        -> ..._preview.png beside it, opened in Safari
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import png_tiles

# the six colour sets (palette data 0x4800C + 0x6A20, 6A40, 6A60, 6A80, 6AA0, 6CC0), read 2026-11-15
SETS = [
    [0x0000, 0x0000, 0x000A, 0x1006, 0x0008, 0x000A, 0x000C, 0x533E, 0x043E, 0x253E, 0x753D, 0x663D, 0x373C, 0x574C,
     0x484C, 0x194B],
    [0x0000, 0x0000, 0x2060, 0x3042, 0x3060, 0x000A, 0x000C, 0x1085, 0x2086, 0x3086, 0x1096, 0x0097, 0x3097, 0x2098,
     0x00A8, 0x10A8],
    [0x0000, 0x0000, 0x7444, 0x0666, 0x0555, 0x000A, 0x000C, 0x7666, 0x0777, 0x7777, 0x0888, 0x7888, 0x0999, 0x7999,
     0x0AAA, 0x7AAA],
    [0x0000, 0x0000, 0x0532, 0x0643, 0x0532, 0x000A, 0x000C, 0x0643, 0x7643, 0x0754, 0x0754, 0x7754, 0x0865, 0x7865,
     0x7865, 0x0976],
    [0x0000, 0x0000, 0x6730, 0x0950, 0x0B70, 0x000A, 0x000C, 0x2950, 0x0960, 0x4960, 0x6960, 0x2A60, 0x0A70, 0x0A70,
     0x6A70, 0x6A70],
    [0x0000, 0x777F, 0x188F, 0x788F, 0x199F, 0x19AF, 0x3AAF, 0x5ABF, 0x3BBF, 0x5BCF, 0x3CCF, 0x7CDF, 0x5DEF, 0x7EEF,
     0x1FFF, 0x7FFF],
]
SCREEN = (320, 224)


rgb = png_tiles.neo_to_rgb                      # a colour word -> (r, g, b)


def palette():
    """The template's palette: the first (blue) set, slot 0 magenta (unused)."""
    pal = [rgb(w) for w in SETS[0]]
    pal[0] = (255, 0, 255)
    return pal


def main(path):
    px = png_tiles.read_indices(path, palette())
    h, w = len(px), len(px[0])
    problems = []
    if (w, h) not in ((80, 96), (160, 96)):
        problems.append("size %d x %d (expected 80 x 96 or 160 x 96)" % (w, h))
    if any(v in (0, 1) for row in px for v in row):
        problems.append("colour slots 0 / 1 used (0 is see-through, 1 is black on most screens)")
    sw, sh = SCREEN
    rows = [[] for _ in range(sh * 2 + 8)]
    for k, s in enumerate(SETS):
        pal = [rgb(c) for c in s]
        ox, oy = (k % 3) * (sw + 8), (k // 3) * (sh + 8)
        for y in range(sh):
            row = rows[oy + y]
            need = ox + sw + 8 - len(row)
            if need > 0:
                row += [(0, 0, 0)] * need
            for x in range(sw):
                row[ox + x] = pal[px[(y + 37) % h][(x + 29) % w]]    # an off-grid start, as the scroll leaves it
    width = max(len(r) for r in rows)
    rows = [r + [(0, 0, 0)] * (width - len(r)) for r in rows]
    out = os.path.splitext(path)[0] + "_preview.png"
    png_tiles.write_rgb(out, rows)
    print("wrote", out)
    for p in problems:
        print("note:", p)
    subprocess.run(["open", "-a", "Safari", out])


if __name__ == "__main__":
    main(sys.argv[1])
