NAME = "difficulty"
DESCRIPTION = ("Home console (AES): DIFFICULTY is BABY / EASY / MVS / HARD / MANIAC - the game's level underneath, no "
               "clock on BABY, and the clock runs faster while STEADY HAND is held from MVS up")

# Each difficulty picks one of the game's GAME LEVELs (0x10FD8C, 1-8 stored as 0-7), and the arcade's own rules do
# the rest: the level sets the time added to every course's limit (+30 +20 +10 0 -5 -10 -15 -20 s) and the moving
# obstacles' starting rank (docs/code_map.md, "Settings"). Patch 100's smaller rod comes with levels 1-3.
#   BABY    level 1, the small rod, and no clock in the maze: it stops and its digits show "--". (The name entry
#           after a win still gets its 15 s, which run on the same clock.)
#   EASY    level 2, the small rod
#   MVS     level 4, the arcade's own; the clock runs 1.5x while A (STEADY HAND) is held
#   HARD    level 6; the clock runs 2x while A is held
#   MANIAC  level 8; the clock runs 2x while A is held
# The penalty only counts in play (course step 36) with A held and STEADY HAND not OFF, as for patch 020's slow mode.
#
# The clock (0x13BE8, every frame) counts ticks 0-5 at 0x10A85A; past 5 a tenth comes off 0x10A858, and past 9 a
# second off 0x10A856. Here each frame adds 0 ticks (BABY), 1, alternately 1 and 2 (1.5x), or 2 (2x: the count
# starts again from 0 past 5, so a tenth goes every 3 frames). The clock's digits (0x14378, called from 0x3908) are
# big LCD digits on the fix layer (palette 1, 2 x 3 tiles, the tenths 2 x 2). On BABY they're drawn over with a dash
# (2 new tiles with only the middle bar lit; unlit parts are the S ROM's solid tile 0xFD0) and dark tenths.
#
# The options (patch 170) keep their DIFFICULTY row: Left / Right step through the five without wrapping, the value
# shown is the name, and the box under it has its own text for each level.

from patchlib import load_patch as load, fix_vram as vram, find_all, jsr

LEVELS = ["BABY", "EASY", "MVS", "HARD", "MANIAC"]
GAME_LEVEL = [1, 2, 4, 6, 8]            # the game's GAME LEVEL (1-8) for each
PENALTY = [0, 0, 3, 4, 4]               # the clock's speed while STEADY HAND is held, in halves: 2 = normal,
                                        # 3 = 1.5x, 4 = 2x (0 = no penalty, the same as 2)
STOPPED = [True, False, False, False, False]   # True = no clock
DEFAULT = 2                             # at power-on: MVS
BOXES = [   # the options' box text for each: two lines, 34 characters at most (A-Z space . - , " and <<A>>)
    ("NO CLOCK AND A SMALLER ZAP-ROD.", "TAKE ALL THE TIME YOU NEED."),
    ("A SMALLER ZAP-ROD, MORE TIME AND", "SLOWER OBSTACLES."),
    ("THE ORIGINAL ARCADE GAME. HOLDING", "<<A>> SPEEDS UP THE CLOCK."),
    ("LESS TIME, FASTER OBSTACLES.", "HOLDING <<A>> DOUBLES THE CLOCK."),
    ("THE LEAST TIME, FASTEST OBSTACLES.", "HOLDING <<A>> DOUBLES THE CLOCK."),
]


SYSTEM_MODE = 0x10FD82
GAME_LEVEL_DIP = 0x10FD8C
MODE, COURSE_STEP = 0x102960, 0x10806C
DIFF = 0x10EC26                         # spare RAM: the difficulty minus DEFAULT (0 at power-on)
STEADY = 0x10EF48                       # patch 020's STEADY HAND - 5 (-5 = OFF)
P1_HELD = 0x10FD96                      # bit 4 = A
TICKS, PLAY_FRAMES = 0x10A85A, 0x10A812
BOX_SHOWN = 0x10EC23                    # patch 170's
FIX_QUEUE, FIX_RUN = 0x1F14, 0x1F32
CLOCK_DRAW_CALL, CLOCK_DRAW = 0x3908, 0x14378
TICK_SITE = 0x13C30                     # addq.w #1,0x285A(a5); cmpi.w #5,0x285A(a5)
DIGIT_BIG = [0xDA4, 0xDA6, 0xDA8, 0xDAA, 0xDAC, 0xDAE, 0xDD0, 0xDD2, 0xDD4, 0xDD6]   # the clock's digits' first tiles
UNLIT = 0x1FD0                          # palette 1, the S ROM's solid colour-15 tile


def dash_tiles(rom):
    """The big digits' middle row with only the middle bar lit. The bar is where 8 and 0 differ. Everything else is
    unlit: 8's lit colours are mapped to 1's unlit ones, taken from their left columns, where 1 has nothing lit."""
    big = lambda d, row, col: DIGIT_BIG[d] + 16 * row + col
    cmap = {}
    for row in range(3):
        a, b = rom.fix_tile(big(8, row, 0)), rom.fix_tile(big(1, row, 0))
        for y in range(8):
            for x in range(8):
                if a[y][x] != b[y][x]:
                    cmap[a[y][x]] = b[y][x]
    out = []
    for col in range(2):
        p8, p0 = rom.fix_tile(big(8, 1, col)), rom.fix_tile(big(0, 1, col))
        out.append([[p8[y][x] if p8[y][x] != p0[y][x] else cmap.get(p8[y][x], p8[y][x]) for x in range(8)]
                    for y in range(8)])
    return out


def apply(rom):
    m070, m170 = load("070_instructions.py"), load("170_options.py")
    halves070 = m070.halves
    m070.halves = lambda ch: {"<": (0xEE, 0xFE), ">": (0xEF, 0xFF), ",": (0xC0, 0xFC)}.get(ch) or halves070(ch)
    boxes = [m070.screen(*b) for b in BOXES]
    n = len(LEVELS)
    assert len(GAME_LEVEL) == len(PENALTY) == len(STOPPED) == len(BOXES) == n
    width = max(len(s) for s in LEVELS)
    dl, dr = (rom.add_fix_tile(t, why="the clock's dash (%s)" % side) for t, side in zip(dash_tiles(rom), "LR"))
    value_end = m170.VALUE_COL                                      # the options' values end in this column
    diff_at = vram(value_end - width + 1, m170.FIRST_ROW)
    names = "\n".join('    .ascii "%s"' % s.rjust(width) for s in LEVELS)

    code = f"""
    bra.w vbl                   | +0  the vblank chain: the game's level for the difficulty
    bra.w change                | +4  options: Left / Right on DIFFICULTY
    bra.w draw                  | +8  options: DIFFICULTY's value
    bra.w box                   | +12 options: the box (DIFFICULTY's shows its level's text)
    bra.w tick                  | +16 the clock's tick
    bra.w clock                 | +20 the clock's digits

level:                          | d0.w = the difficulty 0-{n - 1}
    move.b 0x{DIFF:X},%d0
    ext.w %d0
    addi.w #{DEFAULT},%d0
    rts

vbl:
    jsr 0x{rom.u32(0x1294):X}
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    bsr.w level
    move.b game_levels(%pc,%d0.w),0x{GAME_LEVEL_DIP:X}
9:  rts
game_levels: .byte {", ".join(str(g - 1) for g in GAME_LEVEL)}
    .even

change:                         | d5 = -1 / +1 (replaces patch 170's wrapping 1-8)
    move.l %d0,-(%sp)
    bsr.w level
    add.w %d5,%d0
    bpl.s 1f
    moveq #0,%d0
1:  cmpi.w #{n - 1},%d0
    ble.s 2f
    moveq #{n - 1},%d0
2:  subi.w #{DEFAULT},%d0
    move.b %d0,0x{DIFF:X}
    bsr.w level
    move.b game_levels(%pc,%d0.w),0x{GAME_LEVEL_DIP:X}
    move.l (%sp)+,%d0
    rts

draw:                           | d1 = the row's palette << 12 (patch 170's row_colour)
    movem.l %d0-%d3/%a0-%a1,-(%sp)
    bsr.w level
    mulu.w #{width},%d0
    lea names(%pc),%a1
    adda.w %d0,%a1
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
    move.w #0x{diff_at:X},(%a0)
    nop
    nop
    moveq #{width - 1},%d3
1:  moveq #0,%d2
    move.b (%a1)+,%d2
    cmpi.b #0x20,%d2
    bne.s 2f
    move.w #0xFF0,%d2                   | a space: solid black
    bra.s 3f
2:  addi.w #0xF00-0x30,%d2              | the game's font: tile 0xF00 + character - '0'
3:  add.w %d1,%d2
    move.w %d2,2(%a0)
    dbf %d3,1b
    movem.l (%sp)+,%d0-%d3/%a0-%a1
    rts
names:
{names}
    .even

box:                            | d0 = the box wanted (patch 170's: 0 = DIFFICULTY's) -> Z set = nothing more to do
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 8f
    tst.b %d0
    bne.s 8f
    move.w %d0,-(%sp)
    bsr.w level
    addi.b #0x80,%d0                    | this level's box: 0x80 + the level
    cmp.b 0x{BOX_SHOWN:X},%d0
    beq.s 7f
    move.b %d0,0x{BOX_SHOWN:X}
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    andi.w #0x7F,%d0
    lsl.w #2,%d0
    lea boxes(%pc),%a0
    movea.l (%a0,%d0.w),%a6
    lea 0x108000,%a5
    jsr 0x{FIX_QUEUE:X}
    jsr 0x{FIX_RUN:X}
    movem.l (%sp)+,%d0-%d7/%a0-%a6
7:  move.w (%sp)+,%d0
    cmp.b %d0,%d0                       | Z set: done here
    rts
8:  cmp.b 0x{BOX_SHOWN:X},%d0           | the instruction this call replaced
    rts

tick:                           | replaces addq.w #1,0x285A(a5); cmpi.w #5,0x285A(a5), leaving the flags for its ble
    move.l %a0,-(%sp)
    move.l %d0,-(%sp)
    moveq #2,%d0                        | halves of a tick: 2 = one
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 5f
    move.l %d1,-(%sp)
    bsr.w level
    move.w %d0,%d1
    moveq #2,%d0
    lea stopped(%pc),%a0
    tst.b (%a0,%d1.w)
    beq.s 1f
    cmpi.w #36,0x{COURSE_STEP:X}        | no clock: only in the maze (countdown and play), since the name entry
    beq.s 11f                           | after a win runs its 15 s on the same clock
    cmpi.w #32,0x{COURSE_STEP:X}
    bne.s 4f
11: moveq #0,%d0
    bra.s 4f
1:  cmpi.w #36,0x{COURSE_STEP:X}        | the penalty: in play, A held, STEADY HAND on
    bne.s 4f
    btst #4,0x{P1_HELD:X}
    beq.s 4f
    cmpi.b #-5,0x{STEADY:X}
    beq.s 4f
    lea penalty(%pc),%a0
    move.b (%a0,%d1.w),%d1
    beq.s 4f
    move.w %d1,%d0
4:  move.l (%sp)+,%d1
5:  btst #0,%d0                         | an odd number of halves: the extra half every other frame
    beq.s 6f
    btst #0,0x{PLAY_FRAMES + 1:X}
    beq.s 6f
    addq.w #1,%d0
6:  lsr.w #1,%d0
    add.w %d0,0x{TICKS:X}
    move.l (%sp)+,%d0
    move.l (%sp)+,%a0
    cmpi.w #5,0x{TICKS:X}
    rts
stopped: .byte {", ".join("1" if s else "0" for s in STOPPED)}
penalty: .byte {", ".join(str(p) for p in PENALTY)}
    .even

clock:                          | the game's digits, then on a stopped clock "--" over them
    jsr 0x{CLOCK_DRAW:X}
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    cmpi.w #8,0x{MODE:X}
    bne.w 9f
    movem.l %d0-%d3/%a0-%a1,-(%sp)
    bsr.w level
    lea stopped(%pc),%a0
    tst.b (%a0,%d0.w)
    beq.s 8f
    move.w 0x{COURSE_STEP:X},%d1        | in the maze only, where the game draws them there (0x14384-0x143AA)
    cmpi.w #36,%d1
    beq.s 1f
    cmpi.w #32,%d1
    bne.s 8f
1:  move.w #0x73A4+64,%d0
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
    lea dash(%pc),%a1
    moveq #3,%d3                        | four columns of the two big digits
3:  move.w %d0,(%a0)
    nop
    nop
    move.w (%a1)+,2(%a0)
    move.w (%a1)+,2(%a0)
    move.w (%a1)+,2(%a0)
    addi.w #32,%d0
    dbf %d3,3b
    addq.w #1,%d0                       | the tenths: two columns of two, unlit
    moveq #1,%d3
4:  move.w %d0,(%a0)
    nop
    nop
    move.w #0x{UNLIT:X},2(%a0)
    move.w #0x{UNLIT:X},2(%a0)
    addi.w #32,%d0
    dbf %d3,4b
8:  movem.l (%sp)+,%d0-%d3/%a0-%a1
9:  rts
dash: .word {", ".join("0x%04X" % w for w in [UNLIT, 0x1000 | dl, UNLIT, UNLIT, 0x1000 | dr, UNLIT] * 2)}

boxes: {chr(10).join("    .long box_%d" % k for k in range(n))}
{chr(10).join("box_%d: .byte %s%s    .even" % (k, ", ".join("0x%02X" % b for b in s), chr(10)) for k, s in enumerate(boxes))}
"""
    # The sites: patch 170's DIFFICULTY change, value and box (found by pattern), and the clock's
    dip = GAME_LEVEL_DIP.to_bytes(4, "big")
    chg = bytes.fromhex("1639") + dip + bytes.fromhex("D60502030007" "13C3") + dip
    chg_sites = find_all(rom, chg)
    assert len(chg_sites) == 1, "difficulty: patch 170's change not found"          # patch 020's (unused) has add.w
    drw = bytes.fromhex("76001639") + dip + bytes.fromhex("52437801303C") + diff_vram(m170)
    drw_sites = find_all(rom, drw)
    assert len(drw_sites) == 1 and rom.data[drw_sites[0] + 16:drw_sites[0] + 18] == b"\x61\x00", \
        "difficulty: patch 170's value not found"
    bx = bytes.fromhex("B039") + BOX_SHOWN.to_bytes(4, "big")
    bx_sites = [a for a in find_all(rom, bx) if rom.data[a + 6] == 0x67]
    assert len(bx_sites) == 1, "difficulty: patch 170's box not found"
    assert rom.data[0x1292:0x1294] == b"\x4E\xB9"

    base = rom.place_code(code, why="AES: the five difficulties")
    hook = lambda off: jsr(base + off)          # a call to this patch's entry at base + off
    nop = bytes.fromhex("4E71")
    rom.write(0x1294, base.to_bytes(4, "big"), expect=rom.data[0x1294:0x1298], why="vblank: the difficulty's level")
    for at in chg_sites:
        rom.write(at, hook(4) + nop * 6, expect=chg, why="options: DIFFICULTY steps the five")
    rom.write(drw_sites[0], hook(8) + nop * 7, expect=rom.data[drw_sites[0]:drw_sites[0] + 20],
              why="options: DIFFICULTY's name")
    rom.write(bx_sites[0], hook(12), expect=bx, why="options: DIFFICULTY's box per level")
    rom.write(TICK_SITE, hook(16) + nop * 2, expect=bytes.fromhex("526D285A0C6D0005285A"),
              why="the clock: stopped / faster with STEADY HAND held")
    rom.write(CLOCK_DRAW_CALL, hook(20), expect=jsr(CLOCK_DRAW),
              why="the clock's digits: -- when stopped")


def diff_vram(m170):
    return (0x7000 + 32 * m170.VALUE_COL + m170.FIRST_ROW).to_bytes(2, "big")
