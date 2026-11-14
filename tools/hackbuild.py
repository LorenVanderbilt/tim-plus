#!/usr/bin/env python3
"""Build a patched The Irritating Maze ROM set for MAME from roms/irrmaze.zip plus patches/*.py.

    tools/hackbuild.py                     apply every patch in patches/
    tools/hackbuild.py --only some-patch   apply just the named patch(es)
    tools/hackbuild.py --skip some-patch   apply everything except the named patch(es)
    tools/hackbuild.py --list              list the available patches

Output goes to build/roms/ (the arcade/MVS machine: GAME.zip = the patched game, neogeo.zip = the BIOS) and
build/aes/ (the home-console machine: the game as a cartridge plus a software-list file, and roms/aes.zip as the
BIOS), which run.sh points MAME at. roms/ is never modified.

roms/aes.zip is ngdevkit's open-source AES BIOS (copied from any ngdevkit example's build/rom/aes.zip); the official
AES BIOS is not needed. Without it only the arcade build is produced.

A patch is a Python file in patches/ defining NAME, DESCRIPTION and apply(rom). `rom` is a Rom (below) holding the
program ROM in normal 68000 byte order, as the CPU sees it; patches change it with rom.write(), and add new code with
rom.place_code(), which assembles it into unused space (FREE_START on). rom.add_fix_tile() / rom.add_sprite_tile()
add 8x8 fix / 16x16 sprite tiles in slots proven unused (FIX_FREE_RANGES, tools/free_sprite_tiles.txt - empty until
a census proves some), rom.sprite_tile() reads an original tile.

The cartridge's layout (which files, where they load) comes from MAME's own software list (hash/neogeo.xml): the
AES set's list entry is MAME's, with the patched files' sizes and checksums. Files are matched by checksum, so the
arcade set's names and the list's can differ (see SOURCE for this game's zip).

(Made from Joy Joy Kid Plus's hackbuild, 2026-11-06 - the shared parts, the game's settings collected here.)
"""
import argparse, glob, hashlib, importlib.util, os, re, shutil, subprocess, sys, tempfile, zipfile, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- the game -------------------------------------------------------------------------------------------------
GAME = "irrmaze"                    # MAME's name for the set (and the software list's)
TITLE = "The Irritating Maze (hack)"
PREFIX = "236-"                     # the cart's ROM files (236 - an MVS-only release)
P1_NAME = "236-p1.p1"
S1_NAME = "236-s1.s1"
M1_NAME = "236-m1.m1"               # the sound driver's Z80 ROM
C_NAMES = ["236-c1.c1", "236-c2.c2"]   # one pair: sprite tiles 0-0xFFFF (4 MB each)
P_SPLIT = 0x100000                  # the 2 MB program ROM: MAME's file has the banked half first (the list's
                                    # "continue"): the CPU's fixed 0x000000-0x0FFFFF is its second half
FREE_START = 0x0F1000              # ~60 KB of 0xFF to 0x0FFFFF, the fixed half's end (tools/free_space.py, 2026-11-06)
FIX_FREE_RANGES = [(0xF30, 0xF3F), (0x3D5, 0x3DF), (0x3E5, 0x3F0)]   # blank, at the ends of the game's two
# fonts: never drawn in 30000 attract frames + the recorded games (census 2026-11-07 / -12), in no text script
FREE_SPRITE_TILES = os.path.join(ROOT, "tools", "free_sprite_tiles.txt")
# roms/irrmaze.zip: MAME's set exactly (the user's "irrmaze (1).zip", 2026-11-07). The first zip (kept as
# roms/irrmaze-old-v2-dump.zip) had .bin names, the program ROM's halves swapped and a scrambled 236-v2 (over half
# its bytes differ from MAME's): its ADPCM samples crackled (the character select and course-clear jingles, MAME and
# the BackBit). SOURCE maps a zip that isn't MAME's naming: {MAME's name: (the zip's name, how)}; empty = MAME's.
SOURCE = {}
# ---------------------------------------------------------------------------------------------------------------

ORIG_ZIP = os.path.join(ROOT, "roms", GAME + ".zip")
OUT_DIR = os.path.join(ROOT, "build", "roms")
AES_DIR = os.path.join(ROOT, "build", "aes")
AS, LD, OBJCOPY = "m68k-neogeo-elf-as", "m68k-neogeo-elf-ld", "m68k-neogeo-elf-objcopy"


def swap_pairs(b):
    """The .p1 file stores every 16-bit word byte-swapped; this converts either direction."""
    out = bytearray(len(b))
    out[0::2], out[1::2] = b[1::2], b[0::2]
    return bytes(out)


def p1_to_cpu(p1):
    """The program ROM file -> the CPU's view (0x000000 on; with P_SPLIT, the banked half after the fixed one)."""
    d = swap_pairs(p1)
    return d[P_SPLIT:] + d[:P_SPLIT] if P_SPLIT else d


def cpu_to_p1(data):
    d = bytes(data)
    if P_SPLIT:
        fixed = len(d) - P_SPLIT
        d = d[fixed:] + d[:fixed]
    return swap_pairs(d)


class Rom:
    def __init__(self, data, fix=b"", sprites=None, sound=b""):
        self.data = bytearray(data)
        self.orig = bytes(data)
        self.sound = bytearray(sound)      # the M1 ROM (Z80): write_sound() changes it
        self.sound_orig = bytes(sound)
        self.fix = bytearray(fix)          # the fix-layer ROM (S ROM): 32 bytes per 8x8 tile, 4 bits per pixel
        self.fix_orig = bytes(fix)
        self.sprites = {n: bytearray(d) for n, d in (sprites or {}).items()}     # {file name: contents}
        self.sprites_orig = {n: bytes(d) for n, d in (sprites or {}).items()}
        self.next_free = FREE_START
        self.free_fix_tiles = [t for a, b in FIX_FREE_RANGES for t in range(a, b + 1)]
        self.tile_pool = []                # proven free sprite tiles, "FIRST-LAST count" a line
        if os.path.exists(FREE_SPRITE_TILES):
            for line in open(FREE_SPRITE_TILES):
                if line.strip() and not line.startswith("#"):
                    first, last = (int(x, 16) for x in line.split()[0].split("-"))
                    self.tile_pool.extend(range(first, last + 1))
        self.log = []

    def u16(self, addr): return int.from_bytes(self.data[addr:addr + 2], "big")
    def u32(self, addr): return int.from_bytes(self.data[addr:addr + 4], "big")

    def write(self, addr, new, expect=None, why=""):
        """Overwrite bytes at addr. expect= is the bytes that must be there now, so a patch that no longer matches
        the ROM fails loudly instead of corrupting it."""
        new = bytes(new)
        if expect is not None and bytes(self.data[addr:addr + len(expect)]) != bytes(expect):
            raise SystemExit("patch mismatch at 0x%X: expected %s, found %s" % (
                addr, bytes(expect).hex(), bytes(self.data[addr:addr + len(expect)]).hex()))
        if expect is not None and len(new) > len(expect):
            raise SystemExit("patch at 0x%X writes %d bytes over the %d expected (%s)" % (addr, len(new), len(expect), why))
        self.data[addr:addr + len(new)] = new
        self.log.append("  0x%06X  %d byte(s)  %s" % (addr, len(new), why))

    def write_sound(self, addr, new, expect=None, why=""):
        """Overwrite bytes of the M1 (sound) ROM at file offset addr, as write() does for the program ROM."""
        new = bytes(new)
        if expect is not None and bytes(self.sound[addr:addr + len(expect)]) != bytes(expect):
            raise SystemExit("sound patch mismatch at 0x%X: expected %s, found %s" % (
                addr, bytes(expect).hex(), bytes(self.sound[addr:addr + len(expect)]).hex()))
        if expect is not None and len(new) > len(expect):
            raise SystemExit("sound patch at 0x%X writes %d bytes over the %d expected (%s)" % (addr, len(new), len(expect), why))
        self.sound[addr:addr + len(new)] = new
        self.log.append("  m1 0x%05X  %d byte(s)  %s" % (addr, len(new), why))

    def alloc(self, size, align=2):
        if self.next_free is None:
            raise SystemExit("no free space known yet: set FREE_START in tools/hackbuild.py (tools/free_space.py)")
        addr = (self.next_free + align - 1) & ~(align - 1)
        end = addr + size
        if end > len(self.data) or any(b != 0xFF for b in self.orig[addr:end]):
            raise SystemExit("out of free space in the program ROM")
        self.next_free = end
        return addr

    def _assemble(self, source, origin):
        with tempfile.TemporaryDirectory() as d:
            s, o, e, b = (os.path.join(d, n) for n in ("a.s", "a.o", "a.elf", "a.bin"))
            open(s, "w").write(source + "\n")
            subprocess.run([AS, "-m68000", "-o", o, s], check=True)
            subprocess.run([LD, "-e", "0", "-Ttext=0x%X" % origin, "-o", e, o], check=True)
            subprocess.run([OBJCOPY, "-O", "binary", "-j", ".text", e, b], check=True)
            return open(b, "rb").read()

    def place_code(self, source, why=""):
        """Assemble 68000 source into free space and return the address it was placed at."""
        # Assembled at the address it will live at (branch / immediate sizes can depend on it); 4-byte aligned (the
        # linker aligns the code to 4 and would pad a 2-aligned start with a NOP, shifting every label by 2).
        if self.next_free is None:
            raise SystemExit("no free space known yet: set FREE_START in tools/hackbuild.py (tools/free_space.py)")
        addr = (self.next_free + 3) & ~3
        code = self._assemble(source, addr)
        assert self.alloc(len(code), align=4) == addr
        self.data[addr:addr + len(code)] = code
        self.log.append("  0x%06X  %d byte(s) of new code  %s" % (addr, len(code), why))
        return addr

    # Byte and nibble holding fix-tile pixel (x, y): columns 0-1 are in bytes 16-23, 2-3 in 24-31, 4-5 in
    # 0-7, 6-7 in 8-15 (one byte per row); the even column is the low nibble.
    FIX_COLUMN_BYTE = (16, 16, 24, 24, 0, 0, 8, 8)

    def fix_tile(self, index):
        """The original 8x8 fix tile at tile number index, as pixels[y][x]."""
        at = index * 32
        return [[(self.fix_orig[at + self.FIX_COLUMN_BYTE[x] + y] >> (0 if x % 2 == 0 else 4)) & 15
                 for x in range(8)] for y in range(8)]

    def put_fix_tile(self, index, pixels, why=""):
        """Store an 8x8 fix-layer tile (pixels[y][x] = color index 0-15, 0 = transparent) at tile number index. The
        slot must be blank (all zero) in the original S ROM."""
        at = index * 32
        if any(self.fix_orig[at:at + 32]):
            raise SystemExit("fix tile 0x%X is not blank in the original S ROM" % index)
        tile = bytearray(32)
        for y in range(8):
            for x in range(8):
                tile[self.FIX_COLUMN_BYTE[x] + y] |= (pixels[y][x] & 15) << (0 if x % 2 == 0 else 4)
        self.fix[at:at + 32] = tile
        self.log.append("  fix 0x%03X  tile  %s" % (index, why))

    def add_fix_tile(self, pixels, why=""):
        """Store an 8x8 fix tile in the next proven-free slot and return its tile number."""
        if not self.free_fix_tiles:
            raise SystemExit("out of free fix tiles (none proven free yet: see FIX_FREE_RANGES)")
        n = self.free_fix_tiles.pop(0)
        self.put_fix_tile(n, pixels, why)
        return n

    # A 16x16 sprite tile is 128 bytes, 64 in each ROM of its pair (c1/c2 first, then c3/c4 ...), in four 8x8 blocks
    # of 16 bytes: x 8-15 y 0-7, x 8-15 y 8-15, x 0-7 y 0-7, x 0-7 y 8-15. Each block row is 2 bytes in each ROM -
    # bitplanes 0 and 1 in the first ROM, 2 and 3 in the second - with bit x of a plane = pixel x.
    def _sprite_at(self, index):
        per_pair = len(self.sprites_orig[C_NAMES[0]]) // 64
        pair = index // per_pair
        return C_NAMES[2 * pair], C_NAMES[2 * pair + 1], (index % per_pair) * 64

    def sprite_tile(self, index):
        """The original 16x16 sprite tile at tile number index, as pixels[y][x] (color indices)."""
        a, b, at = self._sprite_at(index)
        A, B = self.sprites_orig[a], self.sprites_orig[b]
        px = [[0] * 16 for _ in range(16)]
        for blk in range(4):
            bx, by = (8 if blk < 2 else 0), (0 if blk % 2 == 0 else 8)
            for y in range(8):
                o = at + blk * 16 + y * 2
                p = (A[o], A[o + 1], B[o], B[o + 1])
                for x in range(8):
                    px[by + y][bx + x] = sum(((p[k] >> x) & 1) << k for k in range(4))
        return px

    def put_sprite_tile(self, index, pixels, why="", redraw=False):
        """Store a 16x16 sprite tile (pixels[y][x] = color index 0-15, 0 = transparent) at tile number index. The
        slot must be blank in the original C ROMs, unless redraw (drawing over an original tile on purpose)."""
        a, b, at = self._sprite_at(index)
        if not redraw and (any(self.sprites_orig[a][at:at + 64]) or any(self.sprites_orig[b][at:at + 64])):
            raise SystemExit("sprite tile 0x%X is not blank in the original C ROMs" % index)
        for blk in range(4):
            bx, by = (8 if blk < 2 else 0), (0 if blk % 2 == 0 else 8)
            for y in range(8):
                planes = [0, 0, 0, 0]
                for x in range(8):
                    v = pixels[by + y][bx + x] & 15
                    for p in range(4):
                        planes[p] |= ((v >> p) & 1) << x
                o = at + blk * 16 + y * 2
                self.sprites[a][o:o + 2] = bytes(planes[0:2])
                self.sprites[b][o:o + 2] = bytes(planes[2:4])
        self.log.append("  sprite 0x%04X  tile  %s" % (index, why))

    def add_sprite_tile(self, pixels, why="", share=False):
        """Store a 16x16 sprite tile in the next proven-free slot and return its tile number. share: if a tile with
        the same pixels was added with share before, return that one instead."""
        if share:
            key = bytes(v for row in pixels for v in row)
            shared = self.__dict__.setdefault("shared_tiles", {})
            if key not in shared:
                shared[key] = self.add_sprite_tile(pixels, why)
            return shared[key]
        if not self.tile_pool:
            raise SystemExit("out of free sprite tiles (none proven free yet: tools/free_sprite_tiles.txt)")
        n = self.tile_pool.pop(0)
        self.put_sprite_tile(n, pixels, why)
        return n

    def patched_files(self):
        """The ROM files this build changes: {file name: new contents}."""
        files = {}
        if bytes(self.data) != self.orig:
            files[P1_NAME] = cpu_to_p1(self.data)
        if bytes(self.fix) != self.fix_orig:
            files[S1_NAME] = bytes(self.fix)
        if bytes(self.sound) != self.sound_orig:
            files[M1_NAME] = bytes(self.sound)
        for name, d in self.sprites.items():
            if bytes(d) != self.sprites_orig[name]:
                files[name] = bytes(d)
        return files


def mame_list_entry():
    """MAME's software-list entry for GAME (the installed MAME's hash/neogeo.xml)."""
    mame = shutil.which("mame")
    candidates = []
    if mame:
        real = os.path.realpath(mame)
        candidates += [os.path.join(os.path.dirname(os.path.dirname(real)), "share", "mame", "hash", "neogeo.xml"),
                       os.path.join(os.path.dirname(real), "hash", "neogeo.xml")]
    candidates += glob.glob("/opt/homebrew/Cellar/mame/*/share/mame/hash/neogeo.xml")
    for path in candidates:
        if os.path.exists(path):
            m = re.search(r'\t<software name="%s"[ >].*?</software>' % GAME, open(path, encoding="utf-8").read(), re.S)
            if m:
                return m.group(0)
    return None


def write_aes_set(entries, patched):
    """Write build/aes/: the game as an AES cartridge (MAME's software-list entry, patched files' checksums) plus the
    BIOS."""
    src_bios = os.path.join(ROOT, "roms", "aes.zip")
    if not os.path.exists(src_bios):
        print("(no roms/aes.zip - skipping the AES build; copy one from an ngdevkit example's build/rom/)")
        return
    entry = mame_list_entry()
    if entry is None:
        print("(MAME's software list has no %s - skipping the AES build)" % GAME)
        return
    by_crc, by_name, orig_by_crc, orig_by_name = {}, {}, {}, {}
    for info, data in entries:
        new = by_name[info.filename] = patched.get(info.filename, data)
        by_crc["%08x" % (zlib.crc32(data) & 0xFFFFFFFF)] = new
        orig_by_crc["%08x" % (zlib.crc32(data) & 0xFFFFFFFF)] = orig_by_name[info.filename] = len(data)

    game = {}

    def fix_rom(m):
        tag = m.group(0)
        name, crc = re.search(r'name="([^"]+)"', tag), re.search(r'crc="([0-9a-f]{8})"', tag)
        if not name or not crc:
            return tag
        if crc.group(1) in by_crc:
            d, size = by_crc[crc.group(1)], orig_by_crc[crc.group(1)]
        elif name.group(1) in by_name:          # (another dump of the same file: matched by name)
            d, size = by_name[name.group(1)], orig_by_name[name.group(1)]
        else:
            raise SystemExit("roms/%s.zip has no file with crc %s (%s)" % (GAME, crc.group(1), name.group(1)))
        game[name.group(1)] = d
        if len(d) != size:      # (a grown file; a split one's halves keep the list's sizes)
            tag = re.sub(r'size="0x[0-9a-fA-F]+"', 'size="0x%06x"' % len(d), tag, count=1)
        tag = re.sub(r'crc="[0-9a-f]{8}"', 'crc="%08x"' % (zlib.crc32(d) & 0xFFFFFFFF), tag)
        return re.sub(r'sha1="[0-9a-f]{40}"', 'sha1="%s"' % hashlib.sha1(d).hexdigest(), tag)

    entry = re.sub(r"<rom [^>]*/>", fix_rom, entry)
    entry = re.sub(r"<description>.*?</description>", "<description>%s</description>" % TITLE, entry)
    entry = re.sub(r'<sharedfeat name="(release|compatibility)" value="[^"]*" />',
                   r'<sharedfeat name="\1" value="MVS,AES" />', entry)
    os.makedirs(AES_DIR, exist_ok=True)
    with zipfile.ZipFile(os.path.join(AES_DIR, GAME + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(game.items()):
            z.writestr(name, data)
    xml = ('<?xml version="1.0"?>\n<!DOCTYPE softwarelist SYSTEM "softwarelist.dtd">\n'
           '<softwarelist name="neogeo" description="Neo-Geo cartridges">\n%s\n</softwarelist>\n' % entry)
    open(os.path.join(AES_DIR, "neogeo.xml"), "w").write(xml)
    shutil.copy(src_bios, os.path.join(AES_DIR, "aes.zip"))
    shutil.copy(os.path.join(ROOT, "roms", "neogeo.zip"), os.path.join(AES_DIR, "neogeo.zip"))
    print("Built build/aes/ (home-console set)")


def load_patches():
    found = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "patches", "*.py"))):
        spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        found[mod.NAME] = mod
    return found


def load_original():
    """(entries, Rom) from roms/GAME.zip - for the build and for tools that read the original."""
    if not os.path.exists(ORIG_ZIP):
        raise SystemExit("missing %s - put your %s.zip in roms/" % (ORIG_ZIP, GAME))
    with zipfile.ZipFile(ORIG_ZIP) as z:
        entries = [(i, z.read(i)) for i in z.infolist()]
    if SOURCE:                              # the zip's files under MAME's names, in MAME's layout
        have = {i.filename: d for i, d in entries}
        entries = []
        for name, (src, how) in SOURCE.items():
            if src not in have:
                raise SystemExit("roms/%s.zip has no %s (for %s)" % (GAME, src, name))
            d = have[src]
            if how == "halves":             # stored in the CPU's order: MAME's file has the halves swapped
                d = d[len(d) // 2:] + d[:len(d) // 2]
            entries.append((zipfile.ZipInfo(name), d))
    files = {i.filename: d for i, d in entries}
    rom = Rom(p1_to_cpu(files[P1_NAME]), files[S1_NAME], {n: files[n] for n in C_NAMES}, files[M1_NAME])
    return entries, rom


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", metavar="NAME", help="apply only these patches")
    ap.add_argument("--skip", nargs="+", metavar="NAME", default=[], help="apply all but these patches")
    ap.add_argument("--list", action="store_true", help="list available patches and exit")
    args = ap.parse_args()

    patches = load_patches()
    if args.list:
        for name, m in patches.items():
            print("%-16s %s" % (name, m.DESCRIPTION))
        return
    for n in (args.only or []) + args.skip:
        if n not in patches:
            raise SystemExit("unknown patch %r (see --list)" % n)
    chosen = [n for n in patches if (not args.only or n in args.only) and n not in args.skip]

    entries, rom = load_original()
    print("Applying %d patch(es): %s" % (len(chosen), ", ".join(chosen) or "(none)"))
    for n in chosen:
        print("* %s - %s" % (n, patches[n].DESCRIPTION))
        patches[n].apply(rom)
    for line in rom.log:
        print(line)

    patched = rom.patched_files()
    os.makedirs(OUT_DIR, exist_ok=True)
    with zipfile.ZipFile(os.path.join(OUT_DIR, GAME + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in entries:
            z.writestr(info.filename, patched.get(info.filename, data)[:len(data)])
    shutil.copy(os.path.join(ROOT, "roms", "neogeo.zip"), os.path.join(OUT_DIR, "neogeo.zip"))
    print("Built build/roms/%s.zip" % GAME)
    write_aes_set(entries, patched)


if __name__ == "__main__":
    main()
