"""The title's neon "plus" as game art for patch 160, drawn by tools/neon_plus_ideas.py. Idea 3 (rounded lowercase,
pink; the one in use) makes art/title_plus/plus_neon_pink.png, idea 8 (cyan, dithered glow) plus_neon_cyan.png.
Each is indexed (0 see-through, then the glow, tube and core colours), with a .txt beside it giving its top-left
position on the 320 x 224 screen. The PNG can be edited freely (up to 15 colours, transparent around the sign);
the patch reads it.

    /opt/homebrew/bin/python3 tools/make_title_plus.py [--idea 3|8] [--force]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neon_plus_ideas as N
import png_tiles
from PIL import Image

IDEAS = {3: ("plus_neon_pink", N.idea_lower, N.PINK), 8: ("plus_neon_cyan", N.idea_glow, N.CYAN)}


def main():
    idea = int(sys.argv[sys.argv.index("--idea") + 1]) if "--idea" in sys.argv else 3
    name, draw, colours = IDEAS[idea]
    OUT = os.path.join(N.ROOT, "art", "title_plus", name + ".png")
    WHERE = os.path.join(N.ROOT, "art", "title_plus", name + ".txt")
    if os.path.exists(OUT) and "--force" not in sys.argv:
        print("kept", OUT, "(--force to redraw)")
        return
    key = (255, 0, 255)
    img = Image.new("RGB", (320, 224), key)
    draw(img)
    px = img.load()
    xs = [x for x in range(320) for y in range(224) if px[x, y] != key]
    ys = [y for x in range(320) for y in range(224) if px[x, y] != key]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs) + 1, max(ys) + 1
    tube, core, glow = colours
    pal = [key, glow, tube, core]
    rows = [[pal.index(px[x, y]) if px[x, y] != key else 0 for x in range(x0, x1)] for y in range(y0, y1)]
    png_tiles.write_indexed(OUT, rows, pal + [(0, 0, 0)] * 12)
    open(WHERE, "w").write("%d %d\n" % (x0, y0))
    print("wrote", OUT, "%d x %d at %d, %d" % (x1 - x0, y1 - y0, x0, y0))


if __name__ == "__main__":
    main()
