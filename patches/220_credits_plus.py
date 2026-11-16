NAME = "credits-plus"
DESCRIPTION = "Home console (AES): a PLUS VERSION slide at the end of the staff roll"

# The new slide comes after SPECIAL THANKS and before THANK YOU FOR YOUR PLAYING, in the roll's own style.
#
# During the staff roll (the ending's state 44, 0x16DDE) the camera pans over the professional course along a path
# (0x172C0: x, y waypoints at 2 px a frame; -1 / n means zone n; -1 / -1 ends it and moves to state 48). The slides
# go by on their own clock (0x16B50, about 217 frames each). The slide list (0x16CCA) is a list of pointers ending
# in -1. Each slide is a word (the row its lines stop at) followed by (script, start row) byte pairs, ending in -1.
# The scripts (pointer table 0x17308) are fix-layer scripts of the kind 0x1F32 runs; each is copied to RAM and its
# row moved up a step at a time, so it scrolls up into place.
#   * Headings are 2 x 2 tiles per letter, palette byte 0x14 (tile 0x440 + 0x20 * (n / 8) + 2 * (n % 8)).
#   * Names are 1 x 2 tiles, palette byte 0x13 (A-O from 0x391, P-Z from 0x3B0; the bottom half is + 0x10).
#
# The 12 slides end about 13 frames before the path does. On the console the path gets one more pan (down EXTRA_PAN
# px and back, one slide's time) and the list a 13th slide. The new lists are in free space; the five places that
# load the old ones (pc-relative, so they can't reach) call a routine that picks the list instead.

from patchlib import jsr
import patchlib
HEADING = "PLUS VERSION"
NAME_LINE = "LOREN VANDERBILT III"
EXTRA_PAN = 218                 # px the camera pans down and back up during the new slide (2 px a frame each way)

SYSTEM_MODE = 0x10FD82
SLIDES, SCRIPTS, PATH = 0x16CCA, 0x17308, 0x172C0
N_SLIDES, N_SCRIPTS = 12, 0x2F


def heading_tiles(text):
    """The heading font's tiles, as the low bytes the roll's scripts hold (its tiles are all 0x4xx)."""
    top, bottom = patchlib.heading_tiles(text)
    return [t & 0xFF for t in top], [t & 0xFF for t in bottom]


def name_tiles(text):
    top = []
    for c in text:
        if c == " ":
            top.append(0x90)                                    # blank 0x390 (its bottom 0x3A0 too)
        elif c == "-":
            top.append(0x5D)
        elif c <= "O":
            top.append(0x91 + ord(c) - ord("A"))
        else:
            top.append(0xB0 + ord(c) - ord("P"))
    return top, [t + 0x10 for t in top]


def script(top, bottom, palette_byte):
    """A fix script: the two rows of a line from row 0 at the centred column, and a blank row under it (the row the
    line leaves as it moves up)."""
    n = len(top)
    assert n <= 38 and len(bottom) == n
    col = 20 - n // 2
    out = (0x7000 + 32 * col).to_bytes(2, "big")
    out += bytes([0x40 | (n - 1), palette_byte]) + bytes(top)
    out += bytes([0x80 | (n - 1), 0x01]) + bytes(bottom)
    out += bytes([0xC0 | (n - 1), 0x01, 0x0F]) + bytes([0xFF] * n)
    out += b"\x00"
    assert len(out) <= 128                                      # 0x16D76 copies 128 bytes of it
    return out


def apply(rom):
    def u32s(addr, n): return [rom.u32(addr + 4 * i) for i in range(n)]
    slides = u32s(SLIDES, N_SLIDES)
    assert rom.u32(SLIDES + 4 * N_SLIDES) == 0xFFFFFFFF, "credits: the slide list isn't as expected"
    scripts = u32s(SCRIPTS, N_SCRIPTS)
    path, a = [], PATH
    while rom.u32(a) != 0xFFFFFFFF:
        path.append(rom.u32(a)); a += 4
    x, y = path[-1] >> 16, path[-1] & 0xFFFF
    path += [x << 16 | (y + EXTRA_PAN), x << 16 | y]

    h_top, h_bottom = heading_tiles(HEADING)
    n_top, n_bottom = name_tiles(NAME_LINE)
    longs = lambda v: ", ".join("0x%08X" % w for w in v)
    data = lambda b: ", ".join("0x%02X" % c for c in b)
    code = f"""
    bra.w slide_list            | +0  0x16C88
    bra.w script_table          | +4  0x16D76
    bra.w path_d2               | +8  0x16E00
    bra.w path_a0_d2            | +12 0x16E64
    bra.w path_a0_d0            | +16 0x16EAA

slide_list:                     | lea slides,a1; move.w 0x289C(a5),d0 (whose flags the bmi after it uses)
    lea 0x{SLIDES:X},%a1
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    lea new_slides(%pc),%a1
1:  move.w 0x289C(%a5),%d0
    rts
script_table:                   | lea 0x28A8(a5),a0; lea scripts,a1
    lea 0x28A8(%a5),%a0
    lea 0x{SCRIPTS:X},%a1
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    lea new_scripts(%pc),%a1
1:  rts
path_d2:                        | move.w 0x289A(a5),d2; lea path,a0
    move.w 0x289A(%a5),%d2
    bra.s path
path_a0_d2:                     | lea path,a0; move.w 0x289A(a5),d2
    move.w 0x289A(%a5),%d2
    bra.s path
path_a0_d0:                     | lea path,a0; move.w 0x289A(a5),d0
    move.w 0x289A(%a5),%d0
path:
    lea 0x{PATH:X},%a0
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    lea new_path(%pc),%a0
1:  rts

new_slides: .long {longs(slides)}, plus_slide, 0xFFFFFFFF
new_scripts: .long {longs(scripts)}, heading, name
new_path: .long {longs(path)}, 0xFFFFFFFF
plus_slide: .word 0x000B        | as PRODUCE's: the heading stops at row 11, the name at 15
    .byte 0x{N_SCRIPTS:02X}, 0x1D, 0x{N_SCRIPTS + 1:02X}, 0x21
    .word 0xFFFF
heading: .byte {data(script(h_top, h_bottom, 0x14))}
name: .byte {data(script(n_top, n_bottom, 0x13))}
    .even
"""
    base = rom.place_code(code, why="AES: the staff roll's PLUS VERSION slide")
    sites = [(0x16C88, "43FA0040302D289C"), (0x16D76, "41ED28A843FA058C"), (0x16E00, "342D289A41FA04BA"),
             (0x16E64, "41FA045A342D289A"), (0x16EAA, "41FA0414302D289A")]
    for i, (site, old) in enumerate(sites):
        rom.write(site, jsr(base + 4 * i) + bytes.fromhex("4E71"),
                  expect=bytes.fromhex(old), why="staff roll: the console's slide / script / path lists")
