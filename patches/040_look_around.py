NAME = "look-around"
DESCRIPTION = ("Home console (AES): LOOK AROUND in the pause menu (timer stopped); the pause text on black; "
               "INVINCIBLE stops the rod at walls without the zap; the rod's ring pulses red in the last 10 seconds; "
               "the course select's Right = the next course; no gray flash after the eye catcher; the course maps "
               "fill their frame")

# The game's own look mode (play sub-state 0x108EC2 = 4, 0x4890): the stick moves the camera (at twice the rod's
# speed) instead of the rod; letting go goes to sub-state 8 (0x4A48), which glides the camera back to the rod, then
# 0. On the arcade machine it was "hold button 1" - and the timer ran on, and the walls still counted. On the console
# A is slow mode in a maze (patch 020), so it's offered here from the pause instead (patch 130 later put it back on
# B, and patch 230's pause menu dropped this row):
#   * Pause -> LOOK AROUND (the pause box's last row, below STEADY HAND): the box closes and the look mode starts as
#     0x4D8C starts it. A or B ends it (the camera glides back, then play goes on).
#   * While looking and gliding back: no timer (the 0x13BE8 calls in sub-states 4 and 8) and no wall check (0x17590,
#     the rod can't be hit by anything moving meanwhile).
# Patch 020's pause code is changed only in place, same sizes (found by pattern): the cursor's last row 4 -> 5, the
# last row's text, and its "INVINCIBLE?" test -> a call here that also handles LOOK AROUND.
#
# The pause text on black: the game's font has no background (colour 0 is see-through, so the maze showed through the
# letters). This patch adds copies of the pause's 33 characters with a black background (colour 15 of the borrowed
# palette 13) in free fix tiles, and draws the pause box itself (the same lines, values and cursor as patch 020's
# draw_pause, which its loop no longer calls).
#
# INVINCIBLE (pause): patch 020 made a touch work like the practice course (a blink, the zap, pushed back). Now a
# touch just doesn't happen: the rod goes back to where it was the frame before (0x108EAE / 0x108EB0, which the move
# routine 0x1B114 keeps - as the practice push-back uses them) - it stops at walls and obstacles, without a sound.
# The touch sites (patch 020's hit_check calls) at 0x4E1C (play), 0x5010 and 0x4C60 go on as "nothing touched".

from patchlib import find_once, jsr, jmp

SYSTEM_MODE = 0x10FD82
P1_CHANGE, P2_CHANGE = 0x10FD97, 0x10FD9D
COURSE_STEP, SUBSTATE = 0x10806C, 0x108EC2
LOOK = 0x10EE10                 # 0 off, 1 looking, 2 gliding back
PCUR = 0x10EF0B                 # patch 020's pause cursor
TIMER = 0x13BE8
INVINC, STEADY, STEADY_DEFAULT = 0x10EF05, 0x10EF48, 5     # patch 020's RAM / knob
PAUSE_COL, PAUSE_ROW, PAUSE_W, PAUSE_H = 11, 10, 19, 9     # patch 020's pause box
BUF = 0x10EE20                  # the box's characters (19 x 9)
ROD_X, ROD_Y, ROD_OLD_X, ROD_OLD_Y = 0x108EA6, 0x108EAA, 0x108EAE, 0x108EB0
# ---- the rod's ring pulsing red near the end (knobs) -----------------------------------------------------------
PULSE_FROM = 10        # seconds left when the pulse starts
FAST_FROM = 2          # ... and when it speeds up
SLOW_STEP = 6          # pulse speed: 256 / this = frames for one pulse (6 = about 43 frames)
FAST_STEP = 16         # (16 = 16 frames)
RING_RED = 0x4F00      # the colour it pulses to (pure red)
# The ring is colour 15 of the rod's sprite palette (the rod is object 0; its palette number is the high byte of
# its +0x16 word - 224 on the practice course); the game never rewrites it, so the vblank blends it toward red and
# puts the original back when play ends.
MODE, SECONDS = 0x102960, 0x10A856
RING_ADDR, RING_SAVE, RING_ON, RING_PHASE = 0x10EE00 + 0xE0, 0x10EE00 + 0xE4, 0x10EE00 + 0xE6, 0x10EE00 + 0xE7
# ---- after the eye catcher: a start-up routine ends by setting the backdrop to 0x7777 - mid gray (0x1566); the start-up
# sets it black again only during the next frame (0x3338), so parts of two frames showed gray. On the console it's
# set black there.
# ---- the course select (patch 020 shrinks the cards and their frame to CARD_SIZE): the frame and the maps shrink
# separately and the hardware shrinks height in whole lines, so the map came out a line short of the frame's opening
# (a line of background showed under it). The maps get a little more height than width - the frame is drawn over
# them, so the extra hides under its bars.
CARD_V_EXTRA = 3       # shrink steps (of 256) added to the maps' height
AFTER_PANELS = 0x89CA
TOUCH_SITES = {0x4E1C: 0x4ED8, 0x5010: 0x4FE0, 0x4C60: 0x4C4E}   # a touch site -> where "nothing touched" goes on
COLLIDE = 0x17590


def apply(rom):
    # ---- patch 020's pause, in place
    pcur = PCUR.to_bytes(4, "big")
    up = bytes.fromhex("13FC0004") + pcur                 # move.b #4,PCUR (Up from the top: the last row)
    down = bytes.fromhex("0C390005") + pcur               # cmpi.b #5,PCUR (Down past the last row: the top)
    invinc = bytes.fromhex("0C0000036600")                # cmpi.b #3,d0; bne.w ploop (then eori INVINC)
    a_up, a_down = find_once(rom, up, "pause up"), find_once(rom, down, "pause down")
    a_inv = find_once(rom, invinc, "pause dispatch")
    ploop = a_inv + 6 + int.from_bytes(rom.data[a_inv + 6:a_inv + 8], "big", signed=True)
    assert rom.data[a_inv + 8:a_inv + 10] == bytes.fromhex("0A39"), "eori INVINC should follow"
    presume = a_inv + 8 + 8 + 4                          # after eori.b #1,INVINC (8) and bra.w ploop (4)
    last = b"  STEADY HAND      \x00" + b" " * 19 + b"\x00"
    a_text = find_once(rom, last, "pause text") + 20
    lines = find_once(rom, b" " * 19 + b"\x00" + b"PAUSE".center(19) + b"\x00", "pause lines")
    # the pause loop: bsr.w draw_pause; bsr.w wait_vbl
    assert rom.data[ploop:ploop + 2] == b"\x61\x00" and rom.data[ploop + 4:ploop + 6] == b"\x61\x00"
    wait_vbl = ploop + 6 + int.from_bytes(rom.data[ploop + 6:ploop + 8], "big", signed=True)
    # black-backed copies of the pause's characters (the font: tile 0xF00 + character - '0'; '`' = the '%' tile)
    chars = sorted(set("PAUSERESUMERESTARTLEVELQUITTOTITLEINVINCIBLEONOFFSTEADYHANDLOOKAROUND0123456789`>"))
    tile_of = {}
    for c in chars:
        src = 0xF00 + ord(c) - 0x30
        px = [[(rom.fix[src * 32 + rom.FIX_COLUMN_BYTE[x] + y] >> (0 if x % 2 == 0 else 4)) & 15 for x in range(8)]
              for y in range(8)]
        px = [[v if v else 15 for v in row] for row in px]
        tile_of[c] = rom.add_fix_tile(px, why="pause: '%s' on black" % c)
    words = []
    for c in range(0x20, 0x61):
        t = tile_of.get(chr(c))
        words.append("0x%04X" % ((0xD000 | t) if t is not None else 0xDFF0))   # palette 13; else solid black
    char_tiles = ", ".join(words)

    hit_check = int.from_bytes(rom.data[0x4E1E:0x4E22], "big")      # patch 020's, as its sites call it
    vbl_next = int.from_bytes(rom.data[0x1294:0x1298], "big")         # patch 020's vblank hook
    pick_full = int.from_bytes(rom.data[0x8BEC:0x8BF0], "big")        # patch 020's course-picked size
    assert rom.data[0x8BEA:0x8BEC] == b"\x4E\xB9" and pick_full >= 0x0F1000
    after = jmp(AFTER_PANELS)
    a_after = find_once(rom, after, "patch 020's course select end")
    assert rom.data[0x1292:0x1294] == b"\x4E\xB9" and vbl_next >= 0x0F1000
    assert all(rom.data[t:t + 2] == b"\x4E\xB9" and rom.data[t + 2:t + 6] == hit_check.to_bytes(4, "big")
               for t in TOUCH_SITES), "patch 020's touch sites"
    code = f"""
    bra.w pause_pick            | +0  the pause's A on rows 3-5
    bra.w look_check            | +4  sub-state 4: still looking?
    bra.w look_timer            | +8  sub-states 4 / 8: the timer
    bra.w play_timer            | +12 sub-state 0: the timer
    bra.w look_collide          | +16 sub-states 4 / 8: the wall check
    bra.w pause_draw            | +20 the pause loop's drawing + vblank wait
    bra.w touch_4e1c            | +24 a touch (patch 020's hit_check calls)
    bra.w touch_5010            | +28
    bra.w touch_4c60            | +32
    bra.w vbl_pulse             | +36 the vblank's first call (then patch 020's)
    bra.w backdrop_init         | +40 the start-up's backdrop
    bra.w cards_tall            | +44 patch 020's course select, after it places the cards
    bra.w pick_tall             | +48 a course picked: the card's last size

| ---- the pause's A on INVINCIBLE (3) / STEADY HAND (4) / LOOK AROUND (5); returns to toggle INVINCIBLE
pause_pick:
    cmpi.b #3,%d0
    beq.s 9f                            | (INVINCIBLE: the code after the call toggles it)
    cmpi.b #5,%d0
    bne.s 8f
    cmpi.w #36,0x{COURSE_STEP:X}        | look only in play, from the rod's normal state
    bne.s 8f
    tst.w 0x{SUBSTATE:X}
    bne.s 8f
    move.w #4,0x{SUBSTATE:X}            | as 0x4D8C starts the look
    move.w #3,0x108EC4
    move.w 0x108B8E,0x108ED4
    move.w 0x108B90,0x108ED6
    move.b #1,0x{LOOK:X}
    addq.l #4,%sp
    jmp 0x{presume:X}                   | close the pause, back to the game
8:  addq.l #4,%sp
    jmp 0x{ploop:X}
9:  rts

| ---- replaces "tst.w 0x10A7C6; bne 0x4906" (button 1 held = keep looking): Z clear = keep looking
look_check:
    tst.b 0x{LOOK:X}
    beq.s 1f
    cmpi.b #1,0x{LOOK:X}
    bne.s 2f
    move.b 0x{P1_CHANGE:X},%d0
    or.b 0x{P2_CHANGE:X},%d0
    andi.b #0x30,%d0                    | A or B: done
    beq.s 3f
    move.b #2,0x{LOOK:X}
    btst #5,%d0                         | B: the game toggled the outline hand this frame (0x4850) - undo it
    beq.s 2f
    eori.w #1,0x108EEC
2:  moveq #0,%d0                        | Z set: glide back
    rts
3:  moveq #1,%d0                        | Z clear: keep looking
    rts
1:  tst.w 0x10A7C6                      | (the instruction this call replaced: a5 + 0x27C6)
    rts

look_timer:
    tst.b 0x{LOOK:X}
    bne.s 1f
    jmp 0x{TIMER:X}
1:  rts

play_timer:
    clr.b 0x{LOOK:X}                    | back in normal play: the look is over
    jmp 0x{TIMER:X}

look_collide:
    tst.b 0x{LOOK:X}
    bne.s 1f
    jmp 0x{COLLIDE:X}
1:  moveq #0,%d0                        | nothing touched
    rts

| ---- the pause box, on black (patch 020's draw_pause, with the black-backed characters), then the vblank wait
pause_draw:
    lea 0x{lines:X},%a0                 | patch 020's lines (19 characters and a 0 each)
    lea 0x{BUF:X},%a1
    moveq #{PAUSE_H - 1},%d1
1:  moveq #{PAUSE_W - 1},%d0
2:  move.b (%a0)+,(%a1)+
    dbf %d0,2b
    addq.l #1,%a0
    dbf %d1,1b
    lea 0x{BUF + 6 * PAUSE_W + 15:X},%a1      | INVINCIBLE: " ON" / "OFF" (columns 15-17)
    tst.b 0x{INVINC:X}
    beq.s 3f
    move.b #0x20,(%a1)+
    move.b #0x4F,(%a1)+                 | 'O'
    move.b #0x4E,(%a1)                  | 'N'
    bra.s 4f
3:  move.b #0x4F,(%a1)+
    move.b #0x46,(%a1)+                 | 'F'
    move.b #0x46,(%a1)
4:  lea 0x{BUF + 7 * PAUSE_W + 15:X},%a1      | STEADY HAND: OFF / 10%-90%
    move.b 0x{STEADY:X},%d0
    ext.w %d0
    addi.w #{STEADY_DEFAULT},%d0
    bne.s 5f
    move.b #0x4F,(%a1)+
    move.b #0x46,(%a1)+
    move.b #0x46,(%a1)
    bra.s 6f
5:  addi.b #0x30,%d0
    move.b %d0,(%a1)+
    move.b #0x30,(%a1)+
    move.b #0x60,(%a1)                  | '%' ('`': its tile)
6:  moveq #0,%d0                        | the cursor
    move.b 0x{PCUR:X},%d0
    addq.w #3,%d0
    mulu.w #{PAUSE_W},%d0
    lea 0x{BUF + 1:X},%a1
    move.b #0x3E,(%a1,%d0.w)            | '>'
    lea 0x{BUF:X},%a1                   | out to the fix layer, a row at a time (a column apart: VRAM + 32)
    lea char_tiles(%pc),%a2
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
    move.w #0x{0x7000 + PAUSE_COL * 32 + PAUSE_ROW:X},%d2
    moveq #{PAUSE_H - 1},%d1
7:  move.w %d2,(%a0)
    nop
    nop
    moveq #{PAUSE_W - 1},%d3
8:  moveq #0,%d0
    move.b (%a1)+,%d0
    subi.w #0x20,%d0
    add.w %d0,%d0
    move.w (%a2,%d0.w),2(%a0)
    dbf %d3,8b
    addq.w #1,%d2
    dbf %d1,7b
    jmp 0x{wait_vbl:X}
char_tiles: .word {char_tiles}

| ---- a touch: with INVINCIBLE on (the console), the rod goes back a frame and nothing happened
touch_4e1c:
    move.l #0x4ED8,%d0
    bra.s touch
touch_5010:
    move.l #0x4FE0,%d0
    bra.s touch
touch_4c60:
    move.l #0x4C4E,%d0
touch:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.b 0x{INVINC:X}
    beq.s 1f
    move.w 0x{ROD_OLD_X:X},0x{ROD_X:X}
    move.w 0x{ROD_OLD_Y:X},0x{ROD_Y:X}
    move.l %d0,(%sp)                    | return to "nothing touched"
    rts
1:  jmp 0x{hit_check:X}                 | patch 020's (the practice-course way, or a try lost)

| ---- the vblank (its first call): the rod's ring pulses red in the last seconds of play
vbl_pulse:
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    cmpi.w #8,0x{MODE:X}
    bne.w 7f
    cmpi.w #36,0x{COURSE_STEP:X}
    bne.w 7f
    cmpi.w #{PULSE_FROM},0x{SECONDS:X}
    bcc.w 7f
    tst.b 0x{RING_ON:X}
    bne.s 1f
    moveq #0,%d0                        | starting: find the ring, keep its colour
    move.b 0x100016,%d0
    lsl.w #5,%d0
    addi.l #0x40001E,%d0
    move.l %d0,0x{RING_ADDR:X}
    move.l %d0,%a0
    move.w (%a0),0x{RING_SAVE:X}
    move.b #1,0x{RING_ON:X}
    clr.b 0x{RING_PHASE:X}
1:  moveq #{SLOW_STEP},%d0
    cmpi.w #{FAST_FROM},0x{SECONDS:X}
    bcc.s 2f
    moveq #{FAST_STEP},%d0
2:  add.b %d0,0x{RING_PHASE:X}
    moveq #0,%d4
    move.b 0x{RING_PHASE:X},%d4         | 0-255 -> up and down: 0-15
    bpl.s 3f
    not.b %d4
3:  lsr.w #3,%d4
    move.w 0x{RING_SAVE:X},%d5          | blend each 5-bit channel: c + (red - c) * t / 16
    move.w #{RING_RED},%d6
    moveq #0,%d7
    moveq #8,%d3                        | red: bits 11-8 + bit 14
    moveq #14,%d2
    bsr.w 5f
    moveq #4,%d3                        | green: 7-4 + 13
    moveq #13,%d2
    bsr.w 5f
    moveq #0,%d3                        | blue: 3-0 + 12
    moveq #12,%d2
    bsr.w 5f
    move.l 0x{RING_ADDR:X},%a0
    move.w %d7,(%a0)
    bra.s 9f
5:  move.w %d5,%d0                      | channel of d5 -> d0 (0-31)
    lsr.w %d3,%d0
    andi.w #15,%d0
    add.w %d0,%d0
    btst %d2,%d5
    beq.s 51f
    addq.w #1,%d0
51: move.w %d6,%d1                      | of d6 -> d1
    lsr.w %d3,%d1
    andi.w #15,%d1
    add.w %d1,%d1
    btst %d2,%d6
    beq.s 52f
    addq.w #1,%d1
52: sub.w %d0,%d1
    muls.w %d4,%d1
    asr.w #4,%d1
    add.w %d1,%d0                       | the blend, 0-31
    btst #0,%d0
    beq.s 53f
    bset %d2,%d7
53: lsr.w #1,%d0
    lsl.w %d3,%d0
    or.w %d0,%d7
    rts
7:  tst.b 0x{RING_ON:X}                 | play's over (or more time): the ring as it was
    beq.s 9f
    clr.b 0x{RING_ON:X}
    move.l 0x{RING_ADDR:X},%a0
    move.w 0x{RING_SAVE:X},(%a0)
9:  jmp 0x{vbl_next:X}

| ---- the start-up's backdrop: black on the console (the game's was mid gray, 0x7777)
backdrop_init:
    move.w #0x7777,0x401FFE
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    move.w #0x8000,0x401FFE
1:  rts

| ---- the course maps a little taller than wide (under the frame's bars: no line of background below them)
cards_tall:
    movem.l %d1/%a1,-(%sp)
    lea 0x100080,%a1                    | objects 1-4
    moveq #3,%d1
1:  tst.w 18(%a1)
    beq.s 2f
    cmpi.w #{255 - CARD_V_EXTRA},18(%a1)
    bhi.s 2f
    addi.w #{CARD_V_EXTRA},18(%a1)
2:  lea 128(%a1),%a1
    dbf %d1,1b
    movem.l (%sp)+,%d1/%a1
    jmp 0x{AFTER_PANELS:X}
pick_tall:
    jsr 0x{pick_full:X}                 | patch 020's (CARD_SIZE on the console)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    cmpi.w #{255 - CARD_V_EXTRA},18(%a0)
    bhi.s 1f
    addi.w #{CARD_V_EXTRA},18(%a0)
1:  rts
"""
    base = rom.place_code(code, why="AES: LOOK AROUND from the pause")

    rom.write(a_up, bytes.fromhex("13FC0005") + pcur, expect=up, why="pause: Up from the top -> LOOK AROUND")
    rom.write(a_down, bytes.fromhex("0C390006") + pcur, expect=down, why="pause: six rows")
    rom.write(a_inv, jsr(base) + bytes.fromhex("4E71"), expect=invinc + rom.data[a_inv + 6:a_inv + 8],
              why="pause: A -> INVINCIBLE / LOOK AROUND")
    rom.write(a_text, b"  LOOK AROUND      ", expect=b" " * 19, why="pause: LOOK AROUND (same length)")
    # the game's look mode
    rom.write(0x48F4, jsr(base + 4) + bytes.fromhex("660A"), expect=bytes.fromhex("4A6D27C66600000C"),
              why="look mode: held from the pause until A / B")          # bne.s 0x4906
    for site in (0x48A0, 0x4A58):
        rom.write(site, jsr(base + 8), expect=jsr(TIMER), why="look / glide back: no timer from the pause")
    rom.write(0x4D24, jsr(base + 12), expect=jsr(TIMER), why="play: the look is over")
    for site in (0x4940, 0x4C0C):
        rom.write(site, jsr(base + 16), expect=jsr(COLLIDE), why="look / glide back: no wall touches")
    rom.write(ploop, jsr(base + 20) + bytes.fromhex("4E71"), expect=rom.data[ploop:ploop + 8],
              why="pause: drawn here, on black")
    for site, name in ((0x4E1C, 24), (0x5010, 28), (0x4C60, 32)):
        rom.write(site + 2, (base + name).to_bytes(4, "big"), expect=hit_check.to_bytes(4, "big"),
                  why="a touch: INVINCIBLE stops the rod at the wall, no zap")
    rom.write(0x1292, jsr(base + 36), expect=jsr(vbl_next), why="vblank: + the rod's ring pulsing red")
    # the course select: Right = the next course (patch 020 had Left: btst #2 / #3 swapped, in place)
    lr = bytes.fromhex("08010002670252000801000367025300")
    at = find_once(rom, lr, "course select left / right")
    rom.write(at, bytes.fromhex("08010003670252000801000267025300"), expect=lr,
              why="course select: Right = the next course, Left = the one before")
    rom.write(0x1566, jsr(base + 40) + bytes.fromhex("4E71"), expect=bytes.fromhex("33FC777700401FFE"),
              why="start-up backdrop: black, not gray (no gray flash after the eye catcher)")
    rom.write(a_after, jmp(base + 44), expect=after,
              why="course select: the maps a little taller (fill the frame)")
    rom.write(0x8BEC, (base + 48).to_bytes(4, "big"), expect=pick_full.to_bytes(4, "big"),
              why="course picked: the map a little taller too")
