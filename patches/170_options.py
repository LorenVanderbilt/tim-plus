NAME = "options"
DESCRIPTION = ("Home console (AES): the new options screen (difficulty, rod speed, steady hand, sound test, back) with "
               "the instructions' text box explaining each; the sound test on a screen of its own")

# The options are DIFFICULTY, ROD SPEED (the Zap-Rod's joystick speed; the names are in OPTION_NAMES), STEADY HAND,
# SOUND TEST (a screen of its own) and BACK TO TITLE. A row is free above BACK TO TITLE for a later option. At the
# bottom, the instructions' text box (patch 070's screen(): the game's tall font, palette 6) explains the row the
# cursor is on (DESCRIBE).
#
# Patch 020's options screen stays in place, since its code can't change size; its first instruction now jumps
# here. This screen works the way patch 020's did: the same RAM (OWN, PAL_REQ 3 / 4 for the white text and black
# backdrop, OCUR, MUSIC, SFX, VOICE, STEADY), the vblank's own screen work held off while it's up, and the text
# drawn straight onto the fix layer. The box is a fix script, run at once (queued by 0x1F14, then run by 0x1F32,
# the vblank's script runner). Its colours (fix palette 6, as on the instructions) are put in at the vblank (in
# front of 0x1292's chain), and the title's are put back on leaving.
#
# ROD SPEED goes from 1 to 9. 5 is patch 010's normal joystick speed and is stored as 0, so it's the default at
# power-on. In a maze, patch 010's speed table (start, acceleration, top) is swapped for one scaled by ROD_SPEEDS,
# by a call in place of its "lea table(pc),a1; move.w SPEED_NOW,d3". Menus and the course select's pointer keep
# the normal speeds.

from patchlib import load_patch as load, fix_vram as vram, find_all, find_once, jsr, jmp

ROD_SPEEDS = [60, 70, 80, 90, 100, 115, 130, 145, 160]   # ROD SPEED 1-9: % of the normal joystick speed

OPTION_NAMES = ["DIFFICULTY", "ROD SPEED", "STEADY HAND", "SOUND TEST", "BACK TO TITLE"]
DESCRIBE = [   # the box under the options: two lines each (34 characters at most; A-Z, space, . - ")
    ("", ""),                                                              # DIFFICULTY: patch 240's texts
    ("HOW FAST THE ZAP-ROD MOVES WITH", "THE JOYSTICK. FIVE IS NORMAL."),
    ("HOLDING <<A>> SLOWS THE ZAP-ROD TO", "THIS PERCENT OF ITS NORMAL SPEED."),
    ("HEAR ALL OF THE MUSIC - SOUND", "EFFECTS AND VOICES IN THE GAME."),
    ("RETURN TO THE TITLE SCREEN.", ""),
]
SOUND_NAMES = ["MUSIC", "SOUND EFFECT", "VOICE", "BACK"]
SOUND_DESCRIBE = [
    ("LEFT AND RIGHT PICK A NUMBER.", "<<A>> PLAYS IT - <<B>> STOPS IT."),
    ("LEFT AND RIGHT PICK A NUMBER.", "<<A>> PLAYS IT - <<B>> STOPS IT."),
    ("LEFT AND RIGHT PICK A NUMBER.", "<<A>> PLAYS IT - <<B>> STOPS IT."),
    ("RETURN TO THE OPTIONS.", ""),
]
# Button names in the box's font are written <<A>>, the way the original text styles them ('<' / '>' are the tall
# font's 0xEE / 0xEF, with bottoms 0xFE / 0xFF). The instructions' pages (patch 070's, some rewritten by patch 130)
# get the same styling: each line is padded to 34, so the lengths match, and the pages are found in the ROM and
# written over.
INSTRUCTION_PAGES = [   # (the page as it is, the new page)
    (("HOLD BUTTON A TO STEADY YOUR", "HAND AND MOVE MORE SLOWLY."),
     ("HOLD <<A>> TO STEADY YOUR HAND", "AND MOVE MORE SLOWLY.")),
    (("HOLD BUTTON B AND MOVE THE", "JOYSTICK TO LOOK AROUND."),
     ("HOLD <<B>> AND MOVE THE JOYSTICK", "TO LOOK AROUND THE COURSE.")),
    (("LET GO OF B TO RETURN TO THE", "ZAP-ROD. THE CLOCK KEEPS RUNNING."),
     ("LET GO OF <<B>> TO RETURN TO THE", "ZAP-ROD. THE CLOCK KEEPS RUNNING.")),
    (("PRESS BUTTON C TO SHOW OR HIDE", "THE HAND HOLDING THE ZAP-ROD."),
     ("PRESS <<C>> TO SHOW OR HIDE THE", "HAND HOLDING THE ZAP-ROD.")),
]
TITLE_ROW, FIRST_ROW, NAME_COL, VALUE_COL = 4, 8, 7, 31     # fix layer rows / columns (the box takes rows 22-28)

SYSTEM_MODE = 0x10FD82
P1_CHANGE, P2_CHANGE = 0x10FD97, 0x10FD9D
GAME_LEVEL_DIP = 0x10FD8C
REG_STATUS_B = 0x380000
VBL_FLAGS = 0x104B6F
SOUND, COPY_DIPS, FIX_CLEAR = 0x243C, 0x36C0, 0xC004C2
FIX_QUEUE, FIX_RUN = 0x1F14, 0x1F32
DEMO_STEP, SCENE_STEP, DEMO_WAIT, CREDIT_SHOWN = 0x10805E, 0x108052, 0x108074, 0x108010
SPEED_NOW = 0x10FE00                    # patch 010
RAM20 = 0x10EF00                        # patch 020's RAM
MENU, START_PREV, PAL_REQ, OWN, OCUR = RAM20 + 1, RAM20 + 3, RAM20 + 6, RAM20 + 7, RAM20 + 8
MUSIC, SFX, VOICE, STEADY = RAM20 + 9, RAM20 + 10, RAM20 + 0x49, RAM20 + 0x48
ROD = 0x10EC20                          # spare RAM: ROD SPEED - 5 (0 at power-on)
SCUR, BOX_REQ, BOX_SHOWN = 0x10EC21, 0x10EC22, 0x10EC23   # sound test cursor; box colours in (1) / out (2); box shown
PAL6_SAVE = 0x10EC40                    # 32 bytes: fix palette 6 while the box borrows it
PAL6 = 0x400000 + 6 * 32
BOX_PAL = [0x0000, 0x7FFF, 0x5FE1, 0x4FD1, 0x6FB1, 0x5FA0, 0x5F90, 0x6F70, 0x1557, 0x7779, 0x1AAB, 0x7CCD, 0x1EEE,
           0x000D, 0x0000, 0x7FFF]      # fix palette 6 as the instructions have it


def apply(rom):
    m020, m070 = load("020_menus.py"), load("070_instructions.py")
    halves070 = m070.halves
    m070.halves = lambda ch: {"<": (0xEE, 0xFE), ">": (0xEF, 0xFF)}.get(ch) or halves070(ch)   # adds < and >
    for old, new in INSTRUCTION_PAGES:
        a, b = m070.screen(*old), m070.screen(*new)
        assert len(a) == len(b)
        at = find_once(rom, a, "instructions page %r" % (old,))
        rom.write(at, b, expect=a, why="instructions: %s / %s" % new)
    music = m020.MUSIC_LIST
    sfx, voices = m020.voice_lists(rom)
    steady_default = m020.STEADY_DEFAULT

    # Patch 020's options screen, found by its start (move.b #1,OWN; jsr FIX_CLEAR)
    entry = bytes.fromhex("13FC0001") + OWN.to_bytes(4, "big") + jsr(FIX_CLEAR)
    opt020 = find_once(rom, entry, "patch 020's options")
    # Patch 020's in_maze, found as patch 130 finds it: through p1_buttons' bsr.s
    pat = bytes.fromhex("10020200003061")
    p1 = find_once(rom, pat, "patch 020's p1_buttons")
    in_maze = p1 + 8 + int.from_bytes(rom.data[p1 + 7:p1 + 8], "big", signed=True)
    # Patch 010's speed table, from its "lea table(pc),a1; move.w SPEED_NOW,d3"
    sp = bytes.fromhex("3639") + SPEED_NOW.to_bytes(4, "big")
    found = [a for a in find_all(rom, sp) if rom.data[a - 4:a - 2] == bytes.fromhex("43FA")]
    assert found, "patch 010's speed table"
    speed_site = found[0] - 4
    table = speed_site + 2 + int.from_bytes(rom.data[speed_site + 2:speed_site + 4], "big", signed=True)
    start, accel, top = (rom.u16(table + 2 * k) for k in range(3))
    speeds = []
    for pct in ROD_SPEEDS:
        s, t = max(1, start * pct // 100), max(1, top * pct // 100)
        a = 0 if accel == 0 else max(1, accel * pct // 100)
        speeds.append((s, a, t))

    for top_line, bottom in DESCRIBE + SOUND_DESCRIBE:
        assert len(top_line) <= 34 and len(bottom) <= 34
    boxes = [m070.screen(*d) for d in DESCRIBE] + [m070.screen(*d) for d in SOUND_DESCRIBE]
    n_opt, n_snd = len(OPTION_NAMES), len(SOUND_NAMES)
    I_DIFF, I_ROD, I_STEADY, I_SOUND, I_BACK = range(5)
    asciz = lambda s: '.asciz "%s"' % s

    code = f"""
    bra.w options               | +0 the options screen (from patch 020's)
    bra.w vbl                   | +4 the vblank: the box's colours
    bra.w speed                 | +8 patch 010: the joystick's speed table

| ---- the joystick's speeds: ROD SPEED's in a maze, the normal ones elsewhere
speed:
    lea 0x{table:X},%a1
    move.l %d0,-(%sp)
    jsr 0x{in_maze:X}
    bne.s 1f
    move.b 0x{ROD:X},%d0
    ext.w %d0
    addq.w #4,%d0                       | level 1-9 -> 0-8
    mulu.w #6,%d0
    lea speeds(%pc),%a1
    adda.w %d0,%a1
1:  move.l (%sp)+,%d0
    move.w 0x{SPEED_NOW:X},%d3          | the instruction this call replaced
    rts

| ---- the vblank: put the box's colours in (1) or the title's back (2)
vbl:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    tst.b 0x{BOX_REQ:X}
    beq.s 9f
    movem.l %d0/%a0-%a1,-(%sp)
    move.b 0x{BOX_REQ:X},%d0
    lea 0x{PAL6:X},%a0
    cmpi.b #1,%d0
    bne.s 2f
    lea 0x{PAL6_SAVE:X},%a1
    moveq #7,%d0
1:  move.l (%a0)+,(%a1)+
    dbf %d0,1b
    lea box_pal(%pc),%a1
    lea 0x{PAL6:X},%a0
    bra.s 3f
2:  lea 0x{PAL6_SAVE:X},%a1
3:  moveq #7,%d0
4:  move.l (%a1)+,(%a0)+
    dbf %d0,4b
    clr.b 0x{BOX_REQ:X}
    movem.l (%sp)+,%d0/%a0-%a1
9:  jmp 0x{rom.u32(0x1294):X}

| ---- the options screen: a loop of its own, like patch 020's
options:
    move.b #1,0x{OWN:X}
    jsr 0x{FIX_CLEAR:X}
    bsr.w hide_sprites
    move.b #3,0x{PAL_REQ:X}             | white text, black backdrop (patch 020's vblank)
    move.b #1,0x{BOX_REQ:X}             | and the box's colours
    clr.b 0x{OCUR:X}
    st 0x{BOX_SHOWN:X}
oloop:
    bsr.w draw_options
    moveq #0,%d0
    move.b 0x{OCUR:X},%d0
    bsr.w box
    bsr.w wait_vbl
    bsr.w read_start
    move.b %d0,%d6
    move.b 0x{P1_CHANGE:X},%d7
    or.b 0x{P2_CHANGE:X},%d7
    lea 0x108000,%a5
    btst #0,%d7                         | Up / Down
    beq.s 1f
    subq.b #1,0x{OCUR:X}
    bpl.s 1f
    move.b #{n_opt - 1},0x{OCUR:X}
1:  btst #1,%d7
    beq.s 2f
    addq.b #1,0x{OCUR:X}
    cmpi.b #{n_opt},0x{OCUR:X}
    bcs.s 2f
    clr.b 0x{OCUR:X}
2:  bsr.w left_right                    | d5 = -1 / 0 / +1
    move.b 0x{OCUR:X},%d4
    tst.w %d5
    beq.s 6f
    cmpi.b #{I_DIFF},%d4
    bne.s 3f
    move.b 0x{GAME_LEVEL_DIP:X},%d3     | DIFFICULTY 1-8 (stored 0-7), wrapping around
    add.b %d5,%d3
    andi.b #7,%d3
    move.b %d3,0x{GAME_LEVEL_DIP:X}
    bra.s 6f
3:  cmpi.b #{I_ROD},%d4
    bne.s 4f
    move.b 0x{ROD:X},%d3                | ROD SPEED 1-9, stored minus 5
    add.b %d5,%d3
    cmpi.b #-4,%d3
    blt.s 6f
    cmpi.b #4,%d3
    bgt.s 6f
    move.b %d3,0x{ROD:X}
    bra.s 6f
4:  cmpi.b #{I_STEADY},%d4
    bne.s 6f
    bsr.w steady_change
6:  move.b %d7,%d3                      | A or Start
    andi.b #0x10,%d3
    or.b %d6,%d3
    beq.w oloop
    cmpi.b #{I_BACK},%d4
    beq.s oexit
    cmpi.b #{I_SOUND},%d4
    bne.w oloop
    bsr.w sound_test
    jsr 0x{FIX_CLEAR:X}
    st 0x{BOX_SHOWN:X}
    bra.w oloop
oexit:                                  | as patch 020's does
    jsr 0x{FIX_CLEAR:X}
    move.b #4,0x{PAL_REQ:X}
    move.b #2,0x{BOX_REQ:X}
    bsr.w wait_vbl
    clr.b 0x{OWN:X}
    lea 0x108000,%a5
    jsr 0x{COPY_DIPS:X}                 | the new difficulty into the game's settings
    clr.w 0x{CREDIT_SHOWN:X}
    move.w #8,0x{DEMO_STEP:X}           | back to the logo, then the title with the menu open
    move.w #256,0x{SCENE_STEP:X}
    clr.w 0x{DEMO_WAIT:X}
    move.b #1,0x{MENU:X}
    rts

draw_options:
    lea opt_title(%pc),%a1
    move.w #0x{vram(20 - len("OPTIONS") // 2, TITLE_ROW):X},%d0
    move.w #0xF000,%d1
    bsr.w draw_str
    lea opt_names(%pc),%a1
    move.w #0x{vram(NAME_COL, FIRST_ROW):X},%d0
    moveq #0,%d5
1:  bsr.w row_colour
    movem.l %d0/%d5,-(%sp)
    bsr.w draw_str
    movem.l (%sp)+,%d0/%d5
    addq.w #2,%d0                       | rows 8-20 have room for one more option
    addq.b #1,%d5                       | (the box starts at row 22)
    cmpi.b #{n_opt},%d5
    bne.s 1b
    moveq #{I_DIFF},%d5                 | DIFFICULTY
    bsr.w row_colour
    moveq #0,%d3
    move.b 0x{GAME_LEVEL_DIP:X},%d3
    addq.w #1,%d3
    moveq #1,%d4
    move.w #0x{vram(VALUE_COL, FIRST_ROW + 2 * I_DIFF):X},%d0
    bsr.w draw_num
    moveq #{I_ROD},%d5                  | ROD SPEED
    bsr.w row_colour
    move.b 0x{ROD:X},%d3
    ext.w %d3
    addq.w #5,%d3
    moveq #1,%d4
    move.w #0x{vram(VALUE_COL, FIRST_ROW + 2 * I_ROD):X},%d0
    bsr.w draw_num
    moveq #{I_STEADY},%d5               | STEADY HAND
    bsr.w row_colour
    move.w #0x{vram(VALUE_COL - 3, FIRST_ROW + 2 * I_STEADY):X},%d0
    bra.w draw_steady

row_colour:                             | d5 = the row -> d1 = its palette (orange on the cursor's row)
    move.w #0xD000,%d1
    cmp.b 0x{OCUR:X},%d5
    bne.s 1f
    move.w #0xF000,%d1
1:  rts

| ---- the sound test: patch 020's lists; A plays, B stops
sound_test:
    jsr 0x{FIX_CLEAR:X}
    clr.b 0x{SCUR:X}
    st 0x{BOX_SHOWN:X}
sloop:
    bsr.w draw_sound
    moveq #{n_opt},%d0
    add.b 0x{SCUR:X},%d0
    bsr.w box
    bsr.w wait_vbl
    bsr.w read_start
    move.b %d0,%d6
    move.b 0x{P1_CHANGE:X},%d7
    or.b 0x{P2_CHANGE:X},%d7
    lea 0x108000,%a5
    btst #0,%d7
    beq.s 1f
    subq.b #1,0x{SCUR:X}
    bpl.s 1f
    move.b #{n_snd - 1},0x{SCUR:X}
1:  btst #1,%d7
    beq.s 2f
    addq.b #1,0x{SCUR:X}
    cmpi.b #{n_snd},0x{SCUR:X}
    bcs.s 2f
    clr.b 0x{SCUR:X}
2:  bsr.w left_right
    moveq #0,%d4
    move.b 0x{SCUR:X},%d4
    cmpi.b #3,%d4
    bcc.s 6f
    lea counts(%pc),%a0
    move.b (%a0,%d4.w),%d2              | the list's length
    lea 0x{MUSIC:X},%a0
    tst.b %d4
    beq.s 3f
    lea 0x{SFX:X},%a0
    cmpi.b #1,%d4
    beq.s 3f
    lea 0x{VOICE:X},%a0
3:  tst.w %d5
    beq.s 6f
    moveq #0,%d3
    move.b (%a0),%d3
    add.w %d5,%d3
    bpl.s 4f
    moveq #0,%d3
    move.b %d2,%d3
    subq.w #1,%d3
4:  cmp.b %d2,%d3
    bcs.s 5f
    moveq #0,%d3
5:  move.b %d3,(%a0)
6:  move.b %d7,%d3                      | A or Start
    andi.b #0x10,%d3
    or.b %d6,%d3
    beq.s 8f
    cmpi.b #3,%d4
    beq.s 9f                            | BACK
    moveq #0,%d0
    tst.b %d4
    bne.s 61f
    move.b 0x{MUSIC:X},%d0
    lea music_list(%pc),%a0
    move.b (%a0,%d0.w),%d0
    addi.w #0x8000,%d0
    bra.s 7f
61: cmpi.b #1,%d4
    bne.s 62f
    move.b 0x{SFX:X},%d0
    lea sfx_list(%pc),%a0
    move.b (%a0,%d0.w),%d0
    bra.s 7f
62: move.b 0x{VOICE:X},%d0
    lea voice_list(%pc),%a0
    move.b (%a0,%d0.w),%d0
7:  jsr 0x{SOUND:X}
8:  btst #5,%d7                         | B stops the sound, as in patch 020
    beq.w sloop
    move.w #0x8005,%d0
    jsr 0x{SOUND:X}
    bra.w sloop
9:  rts

draw_sound:
    lea snd_title(%pc),%a1
    move.w #0x{vram(20 - len("SOUND TEST") // 2, TITLE_ROW):X},%d0
    move.w #0xF000,%d1
    bsr.w draw_str
    lea snd_names(%pc),%a1
    move.w #0x{vram(NAME_COL, FIRST_ROW):X},%d0
    moveq #0,%d5
1:  bsr.w srow_colour
    movem.l %d0/%d5,-(%sp)
    bsr.w draw_str
    movem.l (%sp)+,%d0/%d5
    addq.w #2,%d0
    addq.b #1,%d5
    cmpi.b #{n_snd},%d5
    bne.s 1b
    moveq #0,%d5                        | the numbers (from 1)
    bsr.s srow_colour
    moveq #0,%d3
    move.b 0x{MUSIC:X},%d3
    addq.w #1,%d3
    moveq #2,%d4
    move.w #0x{vram(VALUE_COL - 1, FIRST_ROW):X},%d0
    bsr.w draw_num
    moveq #1,%d5
    bsr.s srow_colour
    moveq #0,%d3
    move.b 0x{SFX:X},%d3
    addq.w #1,%d3
    moveq #3,%d4
    move.w #0x{vram(VALUE_COL - 2, FIRST_ROW + 2):X},%d0
    bsr.w draw_num
    moveq #2,%d5
    bsr.s srow_colour
    moveq #0,%d3
    move.b 0x{VOICE:X},%d3
    addq.w #1,%d3
    moveq #2,%d4
    move.w #0x{vram(VALUE_COL - 1, FIRST_ROW + 4):X},%d0
    bra.w draw_num

srow_colour:
    move.w #0xD000,%d1
    cmp.b 0x{SCUR:X},%d5
    bne.s 1f
    move.w #0xF000,%d1
1:  rts

| ---- the box: d0 = which one (options 0-{n_opt - 1}, then the sound test's); drawn only when it changes
box:
    cmp.b 0x{BOX_SHOWN:X},%d0
    beq.s 9f
    move.b %d0,0x{BOX_SHOWN:X}
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    lea boxes(%pc),%a0
    andi.w #0xFF,%d0
    lsl.w #2,%d0
    movea.l (%a0,%d0.w),%a6
    lea 0x108000,%a5
    jsr 0x{FIX_QUEUE:X}                 | queue the script and run it now (the vblank's own runner is held off)
    jsr 0x{FIX_RUN:X}
    movem.l (%sp)+,%d0-%d7/%a0-%a6
9:  rts

| ---- helpers, as in patch 020
left_right:                             | d7 = new presses -> d5 = -1 / 0 / +1
    moveq #0,%d5
    btst #3,%d7
    beq.s 1f
    moveq #1,%d5
1:  btst #2,%d7
    beq.s 2f
    moveq #-1,%d5
2:  rts

read_start:
    move.b 0x{REG_STATUS_B:X},%d0
    not.b %d0
    andi.b #0x05,%d0
    move.b 0x{START_PREV:X},%d1
    move.b %d0,0x{START_PREV:X}
    not.b %d1
    and.b %d1,%d0
    rts

wait_vbl:
    bset #7,0x{VBL_FLAGS:X}
1:  tst.b 0x{VBL_FLAGS:X}
    bmi.s 1b
    rts

hide_sprites:
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
    move.w #0x8201,(%a0)
    nop
    nop
    moveq #0,%d0
    move.w #379,%d1
1:  move.w %d0,2(%a0)
    nop
    dbf %d1,1b
    rts

draw_str:                               | a1 = string (0-terminated; left just past it), d0 = VRAM address, d1 = palette << 12
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
    move.w %d0,(%a0)
    nop
    nop
1:  moveq #0,%d3
    move.b (%a1)+,%d3
    beq.s 9f
    cmpi.b #0x20,%d3
    bne.s 2f
    move.w #0x0F10,2(%a0)
    bra.s 1b
2:  add.w %d1,%d3
    addi.w #0xF00-0x30,%d3
    move.w %d3,2(%a0)
    bra.s 1b
9:  rts

draw_num:                               | d0 = VRAM address, d1 = palette << 12, d3 = value, d4 = digits
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
    move.w %d0,(%a0)
    nop
    nop
    andi.l #0xFFFF,%d3
    subq.w #1,%d4
    move.w %d4,%d5
1:  divu.w #10,%d3
    swap %d3
    move.w %d3,-(%sp)
    clr.w %d3
    swap %d3
    dbf %d5,1b
2:  move.w (%sp)+,%d2
    add.w %d1,%d2
    addi.w #0xF00,%d2
    move.w %d2,2(%a0)
    dbf %d4,2b
    rts

steady_change:                          | d5 = -1 / 0 / +1: STEADY HAND 0 (OFF) - 9 (90%)
    move.b 0x{STEADY:X},%d0
    ext.w %d0
    addi.w #{steady_default},%d0
    add.w %d5,%d0
    bpl.s 1f
    moveq #0,%d0
1:  cmpi.w #9,%d0
    bls.s 2f
    moveq #9,%d0
2:  subi.w #{steady_default},%d0
    move.b %d0,0x{STEADY:X}
    rts

draw_steady:                            | d0 = VRAM address, d1 = palette: " 50%" / " OFF"
    move.b 0x{STEADY:X},%d3
    ext.w %d3
    addi.w #{steady_default},%d3
    lea steady_off(%pc),%a1
    tst.w %d3
    beq.w draw_str
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
    move.w %d0,(%a0)
    nop
    nop
    move.w #0x0F10,2(%a0)
    addi.w #0xF00,%d3
    add.w %d1,%d3
    move.w %d3,2(%a0)
    move.w #0xF00,%d3
    add.w %d1,%d3
    move.w %d3,2(%a0)
    move.w #0xF00 + 0x60 - 0x30,%d3     | '%' (patch 020's tile, in the '`' slot)
    add.w %d1,%d3
    move.w %d3,2(%a0)
    rts

box_pal: .word {", ".join("0x%04X" % c for c in BOX_PAL)}
speeds: {chr(10).join("    .word %d, %d, %d" % s for s in speeds)}
counts: .byte {len(music)}, {len(sfx)}, {len(voices)}
music_list: .byte {", ".join(str(n) for n in music)}
sfx_list: .byte {", ".join(str(n) for n in sfx)}
voice_list: .byte {", ".join(str(n) for n in voices)}
steady_off: {asciz(" OFF")}
opt_title: {asciz("OPTIONS")}
snd_title: {asciz("SOUND TEST")}
opt_names: {chr(10).join("    " + asciz(s) for s in OPTION_NAMES)}
snd_names: {chr(10).join("    " + asciz(s) for s in SOUND_NAMES)}
    .even
boxes: {chr(10).join("    .long box_%d" % k for k in range(len(boxes)))}
{chr(10).join("box_%d: .byte %s%s    .even" % (k, ", ".join("0x%02X" % b for b in s), chr(10)) for k, s in enumerate(boxes))}
"""
    assert len(music) < 256 and len(sfx) < 256 and len(voices) < 256
    base = rom.place_code(code, why="AES: the new options screen")
    rom.write(opt020, jmp(base), expect=entry[:6],
              why="patch 020's options screen -> the new one")
    prev = rom.u32(0x1294)
    rom.write(0x1294, (base + 4).to_bytes(4, "big"), expect=prev.to_bytes(4, "big"), why="vblank: the box's colours")
    rom.write(speed_site, jsr(base + 8) + bytes.fromhex("4E714E71"),
              expect=rom.data[speed_site:speed_site + 10], why="joystick speed: ROD SPEED in a maze")
