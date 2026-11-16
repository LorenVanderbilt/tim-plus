"""Helpers shared by the patches (patches/*.py). tools/hackbuild.py runs from this folder, so a patch can just
`import patchlib`. Nothing here writes to the ROM by itself."""
import importlib.util, os

PATCHES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "patches")
FREE_START, FIXED_END = 0x0F1000, 0x100000      # where the patches' own code goes (hackbuild's FREE_START)


def load_patch(filename):
    """Another patch's module (e.g. "070_instructions.py"), to use its settings and helpers."""
    spec = importlib.util.spec_from_file_location(filename.split(".")[0], os.path.join(PATCHES, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def jsr(addr):
    """The bytes of jsr addr (absolute long)."""
    return bytes.fromhex("4EB9") + addr.to_bytes(4, "big")


def jmp(addr):
    """The bytes of jmp addr (absolute long)."""
    return bytes.fromhex("4EF9") + addr.to_bytes(4, "big")


def fix_vram(col, row):
    """The fix layer's VRAM address of a cell (columns 0-39, rows 0-31)."""
    return 0x7000 + 32 * col + row


def find_all(rom, pattern, lo=FREE_START, hi=FIXED_END):
    """Every place pattern appears in rom.data[lo:hi]."""
    at, out = rom.data.find(pattern, lo, hi), []
    while at >= 0:
        out.append(at)
        at = rom.data.find(pattern, at + 1, hi)
    return out


def find_once(rom, pattern, what, lo=FREE_START, hi=FIXED_END):
    """Where pattern appears in rom.data[lo:hi]; fails the build unless it's there exactly once. By default it
    searches the earlier patches' code."""
    found = find_all(rom, pattern, lo, hi)
    assert len(found) == 1, "%s: found %d times, not once" % (what, len(found))
    return found[0]


def heading_tiles(text):
    """The instructions' / staff roll's heading font: 2 x 2 tiles per character, 0-9 from tile 0x400 and A-Z from
    0x440, 8 characters to a row of 0x20 tiles (the bottom halves at + 0x10); a space is the blank tiles 0x4C0 / 0x4C1
    over 0x4DA / 0x4DB. Returns the (top, bottom) rows of tile numbers."""
    top, bottom = [], []
    for c in text:
        if c == " ":
            top += [0x4C0, 0x4C1]; bottom += [0x4DA, 0x4DB]
            continue
        n = ord(c) - ord("0") if c.isdigit() else ord(c) - ord("A")
        t = (0x400 if c.isdigit() else 0x440) + 0x20 * (n // 8) + 2 * (n % 8)
        top += [t, t + 1]; bottom += [t + 0x10, t + 0x11]
    return top, bottom
