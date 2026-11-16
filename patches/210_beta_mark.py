NAME = "beta-mark"
DESCRIPTION = "Home console (AES): BETA 1 in the lower right corner of every screen"

# LABEL is written on the fix layer at AT in every vblank, right after the game's own fix-layer work (its queued
# scripts, 0x1F32, and 0x1666, which redraws the staff roll's bars as each slide moves), so whatever a screen draws
# there is covered again at once. The letters are the title's copyright font (tiles 0x300 + character, palette 15:
# a yellow ramp in colours 1-7, shadow 14) copied onto black (colour 15 is 0x0000 on every screen checked) as new
# fix tiles, so the label reads the same over any background. A space is the S ROM's solid colour-15 tile 0xFD0.
# On a frame the main loop hasn't finished (0x10A87E) the vblank skips all of this work, the label included.

from patchlib import jsr

LABEL = "BETA 1"
AT = (31, 28)                   # fix column and row of its first character (the bottom line; columns up to 36)

SYSTEM_MODE = 0x10FD82
SITE = 0x132E                   # the vblank: jsr 0x1F32 (the queued fix scripts); jsr 0x1666
PALETTE = 15
BLACK = 15                      # the palette's colour behind the letters
SPACE_TILE = 0xFD0              # solid colour 15


def apply(rom):
    col, row = AT
    assert col + len(LABEL) - 1 <= 36 and row <= 28, "beta-mark: LABEL outside the safe area"
    tile_of = {" ": SPACE_TILE}
    for c in LABEL:
        if c not in tile_of:
            px = [[v or BLACK for v in line] for line in rom.fix_tile(0x300 + ord(c) - 0x30)]
            tile_of[c] = rom.add_fix_tile(px, why="beta mark: '%s' on black" % c)
    cells = ", ".join("0x%04X, 0x%04X" % (0x7000 + (col + i) * 32 + row, PALETTE << 12 | tile_of[c])
                      for i, c in enumerate(LABEL))
    code = f"""
vbl:
    jsr 0x1F32
    jsr 0x1666
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    movem.l %d0/%a0,-(%sp)
    lea cells(%pc),%a0
    moveq #{len(LABEL) - 1},%d0
1:  move.w (%a0)+,0x3C0000
    nop                                 | VRAM needs a breath between address and data
    move.w (%a0)+,0x3C0002
    dbf %d0,1b
    movem.l (%sp)+,%d0/%a0
9:  rts

cells: .word {cells}
"""
    base = rom.place_code(code, why="AES: BETA 1 in the corner")
    rom.write(SITE, jsr(base) + bytes.fromhex("4E71"),
              expect=bytes.fromhex("4EBA0C024EBA0332"), why="vblank: BETA 1 in the corner, after the fix scripts")
