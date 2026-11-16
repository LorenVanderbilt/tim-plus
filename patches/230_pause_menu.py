NAME = "pause-menu"
DESCRIPTION = "Home console (AES): the pause menu redone - framed, spaced out, ROD SPEED added, the debug rows hidden"

# The menu sits in the instructions box's frame (in white) with PAUSE centred and a blank row between the rows.
# INVINCIBLE, a debugging aid, is hidden unless DEBUG is on.
#
# Patch 020's pause (Start during a course's countdown or play) is taken over at its start, found by pattern; the
# loop, the drawing and the choices are all here. The older pause code of patches 020, 040 and 130 (the old rows,
# LOOK AROUND, INVINCIBLE's row) stays in place, unused. Kept from patch 020: its RAM (cursor, INVINCIBLE, STEADY
# HAND), the borrowed fix palette 13 (PAL_REQ 1 = white text, 2 = put it back) and patch 040's black-backed letters.
#
# The frame uses the instructions box's tiles (0x5EE...: colour 10 = outline, 15 = inner line, 14 = inside) in
# palette 13. While the pause is up, that palette's colour 14 (the letters' shadow, unseen on black) is black and
# colour 10 is FRAME. The fix cells under the box are saved at SAVE. 0x10E380-0x10E9FF isn't written on any screen
# checked (title, menus, mazes, win, goal, ending), and no game code refers to it.

from patchlib import fix_vram as vram, find_once, jmp

DEBUG = False           # True: show INVINCIBLE (a debugging aid: walls stop the rod, no zap)
FRAME = 0x7FFF          # the frame's colour: white (0x1AAB is the instructions box's blue-grey)
ROWS = ["RESUME", "RESTART LEVEL", "ROD SPEED", "STEADY HAND"] + (["INVINCIBLE"] if DEBUG else []) + ["QUIT TO TITLE"]
BOX_COL, BOX_W = 9, 22  # fix columns: the box's left edge and width (9 + 22 / 2 = 20, centred)

P1_CHANGE, P2_CHANGE = 0x10FD97, 0x10FD9D
RAM = 0x10EF00                                       # patch 020's RAM
INVINC, PAL_REQ, OWN, PCUR = RAM + 5, RAM + 6, RAM + 7, RAM + 11
START_PREV, START_NEW, STEADY = RAM + 3, RAM + 4, RAM + 0x48
STEADY_DEFAULT = 5
ROD = 0x10EC20                                       # patch 170's ROD SPEED - 5
PAL_FIX = 0x10EC25                                   # spare RAM: 1 = the vblank sets the frame's colours
SAVE = 0x10E400                                      # spare RAM: the fix cells under the box
REG_STATUS_B, VBL_FLAGS, VBL_BUSY = 0x380000, 0x104B6F, 0x10A87E
PHASE, COURSE_STEP, SCENE_STEP = 0x10806E, 0x10806C, 0x108052
PLAYER_MOD, USER_MODE, SYSTEM_RETURN = 0x10FDB6, 0x10FDAF, 0xC00444
GAME_OVER = 0x363E                                   # ends the game, as after the last try (0xBA1E)
MENU_PAL = 13
FIX_FREE_RANGES = [(0xF30, 0xF3F), (0x3D5, 0x3DF), (0x3E5, 0x3F0)]
BLACK = 0xDFF0                                       # palette 13, tile 0xFF0: solid colour 15


def black_backed_tiles(rom, chars):
    """Patch 040's copies of the game's font on black (tile 0xF00 + character - '0'; '%' = '`'), found by content."""
    out = {}
    def pixels(t): return [[(rom.fix[t * 32 + rom.FIX_COLUMN_BYTE[x] + y] >> (0 if x % 2 == 0 else 4)) & 15
                            for x in range(8)] for y in range(8)]
    for c in chars:
        src = 0xF00 + (ord("`") if c == "%" else ord(c)) - 0x30
        want = [[v or 15 for v in row] for row in pixels(src)]
        found = [t for a, b in FIX_FREE_RANGES for t in range(a, b + 1) if pixels(t) == want]
        assert found, "pause: no black-backed '%s'" % c
        out[c] = 0xD000 | found[0]
    return out


def apply(rom):
    n = len(ROWS)
    h = 2 * n + 5                                    # border, blank, PAUSE, blank, rows with blanks, blank, border
    top = 16 - h // 2
    c0, w = BOX_COL, BOX_W
    cur_col, label_col, value_end = c0 + 2, c0 + 4, c0 + w - 3
    tiles = black_backed_tiles(rom, set("".join(ROWS) + "PAUSE0123456789%>ONF") - {" "})
    tile = lambda ch: BLACK if ch == " " else tiles[ch]
    grid = [[BLACK] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if r == 0: t = 0x5EE if c == 0 else (0x600 if c == w - 1 else 0x5EF)
            elif r == h - 1: t = 0x5FE if c == 0 else (0x610 if c == w - 1 else 0x5FF)
            elif c == 0: t = 0x601 if r % 2 else 0x611
            elif c == w - 1: t = 0x602 if r % 2 else 0x612
            else: continue
            grid[r][c] = 0xD000 | t
    def text(r, c, s):
        for i, ch in enumerate(s): grid[r][c + i] = tile(ch)
    text(2, (w - 5) // 2, "PAUSE")
    for i, s in enumerate(ROWS): text(4 + 2 * i, label_col - c0, s)
    row_of = lambda name: top + 4 + 2 * ROWS.index(name)
    kinds = {"RESUME": 0, "RESTART LEVEL": 1, "ROD SPEED": 2, "STEADY HAND": 3, "INVINCIBLE": 4, "QUIT TO TITLE": 5}
    digits = ", ".join("0x%04X" % tile(str(d)) for d in range(10))
    words = lambda v: ", ".join("0x%04X" % x for x in v)
    inv_lines = f"""
    move.w #0x{vram(value_end - 2, row_of("INVINCIBLE")):X},%d0
    lea word_off(%pc),%a1
    tst.b 0x{INVINC:X}
    beq.s 1f
    lea word_on(%pc),%a1
1:  bsr.w cells3""" if DEBUG else ""

    code = f"""
    .equ NUMBUF, 0x{SAVE + 2 * w * h:X}
    bra.w pause                 | +0 patch 020's pause, from its start
    bra.w vbl                   | +4 the vblank chain (0x1294)

vbl:                            | runs after the rest of the chain, so patch 020's palette work goes first
    jsr 0x{rom.u32(0x1294):X}
    tst.b 0x{PAL_FIX:X}
    beq.s 9f
    clr.b 0x{PAL_FIX:X}
    move.w #0x{FRAME:04X},0x{0x400000 + MENU_PAL * 32 + 20:X}
    move.w #0x8000,0x{0x400000 + MENU_PAL * 32 + 28:X}
9:  rts

pause:
    move.b #1,0x{OWN:X}
    move.b #1,0x{PAL_REQ:X}             | patch 020 puts in the borrowed palette's white text
    move.b #1,0x{PAL_FIX:X}             | and our vbl the frame's colours
    bsr.w wait_vbl
    bsr.w save_fix
    clr.b 0x{PCUR:X}
loop:
    bsr.w draw
    bsr.w wait_vbl
    bsr.w read_start
    move.b %d0,%d6
    move.b 0x{P1_CHANGE:X},%d7
    or.b 0x{P2_CHANGE:X},%d7
    btst #0,%d7                         | Up
    beq.s 1f
    subq.b #1,0x{PCUR:X}
    bpl.s 1f
    move.b #{n - 1},0x{PCUR:X}
1:  btst #1,%d7                         | Down
    beq.s 2f
    addq.b #1,0x{PCUR:X}
    cmpi.b #{n},0x{PCUR:X}
    bcs.s 2f
    clr.b 0x{PCUR:X}
2:  tst.b %d6                           | Start: resume
    bne.w resume
    moveq #0,%d5                        | Left / Right: -1 / +1
    btst #3,%d7
    beq.s 3f
    moveq #1,%d5
3:  btst #2,%d7
    beq.s 4f
    moveq #-1,%d5
4:  moveq #0,%d0
    move.b 0x{PCUR:X},%d0
    lea kinds(%pc),%a1
    move.b (%a1,%d0.w),%d0
    cmpi.b #2,%d0
    bne.s 5f
    lea 0x{ROD:X},%a1                   | ROD SPEED 1-9
    moveq #1,%d1
    bsr.w level_change
    bra.w loop
5:  cmpi.b #3,%d0
    bne.s 6f
    lea 0x{STEADY:X},%a1                | STEADY HAND 0 (OFF) - 9
    moveq #0,%d1
    bsr.w level_change
    bra.w loop
6:  cmpi.b #4,%d0
    bne.s 7f
    tst.w %d5                           | INVINCIBLE: Left / Right / A
    bne.s 61f
    btst #4,%d7
    beq.w loop
61: eori.b #1,0x{INVINC:X}
    bra.w loop
7:  btst #4,%d7                         | A
    beq.w loop
    tst.b %d0
    beq.s resume
    cmpi.b #1,%d0
    beq.s restart
    cmpi.b #5,%d0
    beq.s quit
    bra.w loop
kinds: .byte {", ".join(str(kinds[s]) for s in ROWS)}
    .even

resume:
    bsr.w restore_fix
    move.b #2,0x{PAL_REQ:X}             | put the borrowed palette back
    bsr.w wait_vbl
    clr.b 0x{OWN:X}
    rts
restart:                                | as patch 020's: the screen change, then the course set-up
    bsr.s resume
    move.w #4,0x{PHASE:X}
    move.w #28,0x{COURSE_STEP:X}
    rts
quit:                                   | as patch 020's
    move.b #2,0x{PAL_REQ:X}
    bsr.w wait_vbl
    clr.b 0x{OWN:X}
    clr.w 0x{VBL_BUSY:X}
    lea 0x108000,%a5
    jsr 0x{GAME_OVER:X}
    clr.w 0x{SCENE_STEP:X}
    move.b #1,0x{USER_MODE:X}
    move.w #0,0x{PLAYER_MOD:X}
    jmp 0x{SYSTEM_RETURN:X}

level_change:                           | a1 = the setting (level - 5), d1 = its lowest level, d5 = -1 / 0 / +1
    move.b (%a1),%d0
    ext.w %d0
    addi.w #{STEADY_DEFAULT},%d0
    add.w %d5,%d0
    cmp.w %d1,%d0
    bge.s 1f
    move.w %d1,%d0
1:  cmpi.w #9,%d0
    ble.s 2f
    moveq #9,%d0
2:  subi.w #{STEADY_DEFAULT},%d0
    move.b %d0,(%a1)
    rts

wait_vbl:
    bset #7,0x{VBL_FLAGS:X}
1:  tst.b 0x{VBL_FLAGS:X}
    bmi.s 1b
    rts
read_start:                             | as patch 020's: d0 = Start newly pressed
    move.b 0x{REG_STATUS_B:X},%d0
    not.b %d0
    andi.b #0x05,%d0
    move.b 0x{START_PREV:X},%d1
    move.b %d0,0x{START_PREV:X}
    not.b %d1
    and.b %d1,%d0
    move.b %d0,0x{START_NEW:X}
    rts

| ---- the box: the fixed part a row at a time, then the cursor and the values
draw:
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
    lea box(%pc),%a1
    move.w #0x{vram(c0, top):X},%d2
    moveq #{h - 1},%d1
1:  move.w %d2,(%a0)
    nop
    nop
    moveq #{w - 1},%d3
2:  move.w (%a1)+,2(%a0)
    dbf %d3,2b
    addq.w #1,%d2
    dbf %d1,1b
    moveq #0,%d0                        | the cursor
    move.b 0x{PCUR:X},%d0
    add.w %d0,%d0
    addi.w #0x{vram(cur_col, top + 4):X},%d0
    move.w #0x{tile(">"):04X},%d1
    bsr.w cell
    move.b 0x{ROD:X},%d0                | ROD SPEED: the digit
    ext.w %d0
    addi.w #{STEADY_DEFAULT},%d0
    add.w %d0,%d0
    lea digits(%pc),%a1
    move.w (%a1,%d0.w),%d1
    move.w #0x{vram(value_end, row_of("ROD SPEED")):X},%d0
    bsr.w cell
    move.b 0x{STEADY:X},%d0             | STEADY HAND: OFF / 10%-90%
    ext.w %d0
    addi.w #{STEADY_DEFAULT},%d0
    bne.s 3f
    lea word_off(%pc),%a1
    bra.s 4f
3:  lea digits(%pc),%a1
    add.w %d0,%d0
    move.w (%a1,%d0.w),%d1
    lea NUMBUF,%a1
    move.w %d1,(%a1)
    move.w #0x{tile("0"):04X},2(%a1)
    move.w #0x{tile("%"):04X},4(%a1)
4:  move.w #0x{vram(value_end - 2, row_of("STEADY HAND")):X},%d0
    bsr.w cells3{inv_lines}
    rts
digits: .word {digits}
cells3:                                 | d0 = VRAM address, a1 = 3 tile words (a column apart)
    moveq #2,%d3
1:  move.w (%a1)+,%d1
    bsr.s cell
    addi.w #32,%d0
    dbf %d3,1b
    rts
cell:                                   | d0 = VRAM address, d1 = the word
    lea 0x3C0000,%a0
    move.w %d0,(%a0)
    nop
    nop
    move.w %d1,2(%a0)
    rts
word_off: .word 0x{tile("O"):04X}, 0x{tile("F"):04X}, 0x{tile("F"):04X}
word_on: .word {words([BLACK, tile("O"), tile("N")])}

save_fix:
    lea 0x{SAVE:X},%a1
    lea 0x3C0000,%a0
    move.w #0x{vram(c0, top):X},%d1
    moveq #{w - 1},%d3
1:  move.w %d1,%d2
    moveq #{h - 1},%d4
2:  move.w %d2,(%a0)
    nop
    nop
    nop
    nop
    move.w 2(%a0),(%a1)+
    addq.w #1,%d2
    dbf %d4,2b
    addi.w #32,%d1
    dbf %d3,1b
    rts
restore_fix:
    lea 0x{SAVE:X},%a1
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
    move.w #0x{vram(c0, top):X},%d1
    moveq #{w - 1},%d3
1:  move.w %d1,(%a0)
    nop
    nop
    moveq #{h - 1},%d4
2:  move.w (%a1)+,2(%a0)
    nop
    dbf %d4,2b
    addi.w #32,%d1
    dbf %d3,1b
    rts

box: .word {words(v for row in grid for v in row)}
"""
    assert SAVE + 2 * w * h + 6 <= 0x10EA00, "pause: the save area runs past 0x10E9FF"
    pat = bytes.fromhex("13FC0001") + OWN.to_bytes(4, "big") + bytes.fromhex("13FC0001") + PAL_REQ.to_bytes(4, "big")
    at = find_once(rom, pat, "pause: patch 020's pause")
    assert rom.data[at + 16:at + 18] == b"\x61\x00", "pause: patch 020's pause isn't as expected"
    assert rom.data[0x1292:0x1294] == b"\x4E\xB9"
    base = rom.place_code(code, why="AES: the pause menu")
    rom.write(at, jmp(base) + bytes.fromhex("4E71"), expect=pat[:8],
              why="pause: the new menu")
    rom.write(0x1294, (base + 4).to_bytes(4, "big"), expect=rom.data[0x1294:0x1298],
              why="vblank: the pause frame's colours")
