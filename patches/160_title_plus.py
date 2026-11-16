NAME = "title-plus"
DESCRIPTION = "Home console (AES): a blinking neon 'plus' by the title logo (pink, rounded lowercase)"

# The art is art/title_plus/ART_NAME.png (made by tools/make_title_plus.py; editable, up to 15 colours, colour 0
# see-through). ART_NAME.txt holds its top-left position on the screen, and X_MOVE / Y_MOVE below nudge it. The
# unlit sign is the same picture in dimmed colours (DIM), so blinking is just a palette switch, written at the
# start of the vblank.
#
# The sign shows only while the logo does: in the attract sequence (mode 0) at step 8 (the logo's scenes) or steps
# 12, 16 and 20 (the title's set-up and the title), once the logo's own colours are up (palette 184's colour 9 is
# 0x4FDE from the end of the white flash, scene 284, until the logo fades), and never on patch 020's own screens
# (OWN). The vblank hook (in front of 0x1292's chain) writes the sign's sprites from SPRITE on, as one sticky chain
# (none of the game's sprites reach that high on the title), and its colours into palette PALETTE. Nothing on the
# title uses that palette; its colours are saved when the sign comes up and put back when it goes. Like the game's
# own vblank work, it's skipped on a frame the main loop hasn't finished (0x10A87E).

ART_NAME = "plus_neon_pink"             # art/title_plus/<this>.png / .txt ("plus_neon_cyan" = idea 8)
X_MOVE, Y_MOVE = 0, -10                   # pixels right / down from the .txt's place
LIGHTNING = True                        # True: lit, flickering with the title's background lightning;
                                        # False: blink in BLINK's pattern instead
BLINK = [(0, 54), (1, 7), (0, 5), (1, 54)]   # (lit?, frames), repeated: off 0.9 s, a flicker on for 0.12 s,
                                        # off 0.08 s, on 0.9 s. [(1, 1)] = always lit
DIM = 50                                # the unlit sign's brightness, in % of the lit one's

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from png_tiles import read_rgba

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art", "title_plus")
SYSTEM_MODE = 0x10FD82
MODE, STEP, BUSY = 0x102960, 0x10805E, 0x10A87E
LOGO_COLOUR, LOGO_PINK = 0x400000 + 184 * 32 + 18, 0x4FDE
OWN = 0x10EF07                          # set while one of patch 020's own screens (options, sound test...) is up
SPRITE = 370                            # the first of the sign's sprites
PALETTE = 200
SHOWN, SAVE = 0x10EED8, 0x10EC00        # spare RAM: 1 while the sign is up; the palette's own 32 bytes meanwhile
STEP_LEFT, STEP_AT = 0x10EEDA, 0x10EEDC  # spare RAM: frames left in the blink's step; the step number x 4
BOLT_REST = 0x3BFF                      # colour 15 of the title's lightning palette (64) when no bolt is striking


def neo(rgb):
    r, g, b = (v >> 3 for v in rgb[:3])
    return ((r & 1) << 14 | (g & 1) << 13 | (b & 1) << 12 | (r >> 1) << 8 | (g >> 1) << 4 | (b >> 1))


def apply(rom):
    px = read_rgba(os.path.join(ART, ART_NAME + ".png"))
    x0, y0 = (int(v) for v in open(os.path.join(ART, ART_NAME + ".txt")).read().split())
    x0, y0 = x0 + X_MOVE, y0 + Y_MOVE
    h, w = len(px), len(px[0])
    colours = []
    idx = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            c, alpha = px[y][x]
            if alpha < 128 or tuple(c) == (255, 0, 255):
                continue
            n = neo(c)
            if n not in colours:
                colours.append(n)
            idx[y][x] = colours.index(n) + 1
    assert len(colours) <= 15, "the sign: %d colours (15 at most)" % len(colours)
    cols, rows = (w + 15) // 16, (h + 15) // 16
    pairs = []                                  # (VRAM address, value)
    for c in range(cols):
        n = SPRITE + c
        for r in range(rows):
            block = [[idx[y][x] if y < h and x < w else 0 for x in range(16 * c, 16 * c + 16)]
                     for y in range(16 * r, 16 * r + 16)]
            t = rom.add_sprite_tile(block, why="title plus", share=True)
            pairs += [(64 * n + 2 * r, t & 0xFFFF), (64 * n + 2 * r + 1, PALETTE << 8 | (t >> 16) << 4)]
        pairs += [(0x8000 + n, 0x0FFF),
                  (0x8200 + n, ((480 - y0) & 511) << 7 | rows if c == 0 else 0x40),
                  (0x8400 + n, (x0 & 511) << 7)]
    pal = [0] + colours + [0] * (15 - len(colours))
    def dim(word):
        r = ((word >> 7) & 0x1E) | ((word >> 14) & 1)
        g = ((word >> 3) & 0x1E) | ((word >> 13) & 1)
        b = ((word << 1) & 0x1E) | ((word >> 12) & 1)
        return neo(tuple((v * DIM // 100) << 3 for v in (r, g, b)))
    unlit = [0] + [dim(c) for c in colours] + [0] * (15 - len(colours))
    if LIGHTNING:
        # Palette 64's colour 15 is 0x3BFF at rest (0 before it's loaded). A strike steps the palette dark, middle,
        # bright over ~10 frames as the bolts flash; the sign goes unlit on the dark and middle steps.
        lit_test = f"""    move.w 0x{0x400000 + 64 * 32 + 30:X},%d0
    beq.s 6f
    cmpi.w #0x{BOLT_REST:X},%d0
    beq.s 6f"""
    else:
        lit_test = f"""    move.w 0x{STEP_AT:X},%d0
    lea blink(%pc),%a1
    tst.w (%a1,%d0.w)
    bne.s 6f"""
    pal_addr = 0x400000 + 32 * PALETTE

    code = f"""
    bra.w vbl                   | +0 the vblank (0x1292's chain)

vbl:
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    tst.b 0x{BUSY:X}
    bne.w 9f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    tst.w 0x{MODE:X}                    | is the logo up?
    bne.w 5f
    move.w 0x{STEP:X},%d0
    cmpi.w #8,%d0
    beq.s 1f
    cmpi.w #12,%d0
    beq.s 1f
    cmpi.w #16,%d0
    beq.s 1f
    cmpi.w #20,%d0
    bne.w 5f
1:  cmpi.w #0x{LOGO_PINK:X},0x{LOGO_COLOUR:X}
    bne.w 5f
    tst.b 0x{OWN:X}
    bne.w 5f
    tst.b 0x{SHOWN:X}                   | yes: show the sign
    bne.s 2f
    lea 0x{pal_addr:X},%a0              | keep the palette's own colours
    lea 0x{SAVE:X},%a1
    moveq #7,%d0
3:  move.l (%a0)+,(%a1)+
    dbf %d0,3b
    move.b #1,0x{SHOWN:X}
    clr.w 0x{STEP_AT:X}                 | start the blink from its first step
    move.w blink+2(%pc),0x{STEP_LEFT:X}
2:  subq.w #1,0x{STEP_LEFT:X}           | the blink's next step once this one's frames are up
    bne.s 7f
    move.w 0x{STEP_AT:X},%d0
    addq.w #4,%d0
    cmpi.w #{4 * len(BLINK)},%d0
    bcs.s 6f
    moveq #0,%d0
6:  move.w %d0,0x{STEP_AT:X}
    lea blink(%pc),%a0
    move.w 2(%a0,%d0.w),0x{STEP_LEFT:X}
7:  lea colours(%pc),%a0
{lit_test}
    lea unlit(%pc),%a0
6:
    lea 0x{pal_addr:X},%a1
    moveq #7,%d0
3:  move.l (%a0)+,(%a1)+
    dbf %d0,3b
    lea sprites(%pc),%a0
    move.w #{len(pairs) - 1},%d0
4:  move.w (%a0)+,0x3C0000
    nop                                 | VRAM needs a breath between address and data (as in patch 020)
    move.w (%a0)+,0x3C0002
    dbf %d0,4b
    bra.w 8f
5:  tst.b 0x{SHOWN:X}                   | no: take the sign away if it's up
    beq.w 8f
    clr.b 0x{SHOWN:X}
    lea 0x{SAVE:X},%a0
    lea 0x{pal_addr:X},%a1
    moveq #7,%d0
3:  move.l (%a0)+,(%a1)+
    dbf %d0,3b
    move.w #0x{0x8200 + SPRITE:X},%d1
    moveq #{cols - 1},%d0
6:  move.w %d1,0x3C0000
    nop
    move.w #0,0x3C0002
    addq.w #1,%d1
    dbf %d0,6b
8:  movem.l (%sp)+,%d0-%d1/%a0-%a1
9:  jmp 0x{rom.u32(0x1294):X}

colours: .word {", ".join("0x%04X" % c for c in pal)}
unlit: .word {", ".join("0x%04X" % c for c in unlit)}
blink: .word {", ".join("%d, %d" % (lit, n) for lit, n in BLINK)}
sprites: .word {", ".join("0x%04X, 0x%04X" % p for p in pairs)}
"""
    assert rom.data[0x1292:0x1294] == b"\x4E\xB9"
    prev = rom.u32(0x1294)
    base = rom.place_code(code, why="AES: the title's neon plus")
    rom.write(0x1294, base.to_bytes(4, "big"), expect=prev.to_bytes(4, "big"), why="vblank: the title's neon plus")
