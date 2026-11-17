NAME = "mvs-menus"
DESCRIPTION = ("Standard MVS: the console's course select (the deck of cards) and pause menu there too, BETA 1 bottom centre "
               "(CREDIT is bottom right); the title's neon plus not over the arcade intro's scenes; the course card "
               "shown without stage select: its name at the top, the card higher; with only PRACTICE on, the console's "
               "course select with just practice and the first course")

# Step 2 of the standard MVS (patch 280 did step 1: play). The user's calls (2026-11-16): the pause on the MVS too;
# OPTIONS and 2P CHALLENGE not for now - so no title menu there (ARCADE would be its only choice): a coin and Start
# begin the game the BIOS's usual way, credits and all.
#
# The course select first: on a standard MVS with the operator's STAGE SELECT on, the original's course select came
# up - made for the trackball, slow and one-way with the joystick (and on the user's console without its heading).
# Here the console's course select (patch 020's deck, 050's maps, 040's frame size, 190 / 290's frame, 270's title)
# is switched on there too: the checks patch 280 left console-only for it are re-pointed at its PLUS_OFF switch,
# the same way (same instruction, its address only).

ENABLE = {                              # patch -> the routines whose checks follow PLUS_OFF ("all": every check)
    "020": {"course_timer", "course_select", "course_deck", "fix_queue", "arcade_select"},
    "040": {"pick_tall"},
    "050": "all",
    "190": "all",
    "290": "all",
}

# The title's neon plus (patch 160) shows while the logo's colours are up in the attract's step 8 - on the console
# that's only the logo (the intro scenes are skipped), but the arcade attract plays its intro scenes (step 8, scenes
# 28-248) with those colours too, so the plus showed over them. The one jump into 160's vblank code (from patch
# 170's) now goes through a test: during step 8 below scene 256 (the logo's), 160 is passed over.
# And the MVS's own title, after a coin (mode 4, with PRESS START BUTTON and the BIOS's countdown), had no plus:
# 160 knows only the attract's title (mode 0, steps 8-20). There the test shows 160 the attract's title (mode 0,
# step 20) for the moment it runs, and 160's way out (re-pointed the same way) puts the real ones back - all in the
# vblank, before the main loop sees anything. The logo's colours there are in palette 144, not 184 where 160 looks:
# when they're up, 160's test colour is lent across for that moment too (in the vblank's first lines, unseen), so
# the heart-condition warning still gets no plus.

# The pause: patch 020 opens it from its main-loop hook, which on an MVS returns at once (it also hides CREDIT, which
# an MVS shows) - so here a main-loop check of its own, in front of the chain at 0x1068: on a standard MVS, Start newly
# pressed in a course's countdown or play (course step 32 / 36, phase 0, no screen change) calls patch 230's pause
# menu, with the vblank's own work held off (0x10A87E) as in 020's hook.

# BETA 1 (patch 210, console only - it sits where an MVS prints CREDIT): on a standard MVS the same letters at
# BETA_AT, bottom centre. 210's code at the vblank runs the fix scripts, then 0x1666, then its label; its call to 0x1666
# now goes through a routine that calls it and then writes the label there on a standard MVS.
BETA_AT = (17, 28)                      # fix column, row of its first letter: bottom centre (the mini-map is bottom left)

# Leaving a course's play screen (a miss, back to the checkpoint; a practice miss; a win) the game clears every
# sprite with the system ROM's routine (0xC004C8), which ran from line 14 to 50 - into the picture: a frame of dark
# blue with the course still showing along the top (the user saw it after a zap, on the MVS; the console too). These
# calls now go through patch 270's black_first (its +32: the fix layer black, then every sprite's height 0, then the
# system ROM's clear) - as the character select's way in does. Console and standard MVS alike (270's switch).
PLAY_CLEARS = [0x97D4, 0x980E, 0x98F4]  # jsr 0xC004C8: after a miss, a practice miss, a win
SPRITE_CLEAR = 0xC004C8

# The course card the game shows after the character select when STAGE SELECT is off (the course coming up - on a
# standard MVS; the original's too): the user (2026-11-16) wanted its name at the top centre and the card higher. The
# name is a fix script (0x30E6E... per course, rows 13-14): on that card the queue (0x1F14, in front of patch 120's
# hook) swaps in a copy NAME_ROWS_UP rows higher. The frame, its second layer and the card are made at 0x7C0E / 0x7C40
# (and 0x7CFC) / 0x7BDC (move.w #160,d1; move.w #y,d2): there a call gives y less CARD_UP. The best-time line under it (column
# 20, row 26 at 0x7D68 / 0x8272 / 0x8A7A, patch 250's hooks) comes up CARD_UP / 8 rows with it. Only while the game's
# STAGE SELECT and PRACTICE are both off (with PRACTICE on the game shows a course select of its own instead: practice
# or the first course), on the console / a standard MVS; the course select (stage select on) and the cabinet as
# they were.
# With PRACTICE on and STAGE SELECT off the game offers its own course select between practice and the first course
# - the original's trackball one (slow and backwards with the joystick). The user (2026-11-16): the console's
# course select there too, with just those two. So while that select is up, the game's STAGE SELECT is turned on
# (patch 020's deck and the rest follow it unchanged) and turned off again on leaving it (after a win the courses go
# on in order, as the operator set). The deck's choice wraps between the two (DECK_T pre-set ahead of its Left /
# Right), and the other two cards are hidden after it has placed them (its way back to the game, patch 040's jump
# to 0x89CA, goes through that).
PRACTICE_ONLY = 0x10EC94                # spare RAM: 1 while STAGE SELECT is on for this
STAGE_DIP = 0x10FD91                    # the operator's STAGE SELECT (soft dip)
DECK_INIT, DECK_T = 0x10EF0C, 0x10EF0D  # patch 020's deck: started; the chosen course 0-3
P1_CHANGE, P2_CHANGE = 0x10FD97, 0x10FD9D
DECK_SITE = 0x8836                      # 0x8834's jsr: the deck (patches 190 / 020)
AFTER_PANELS = 0x89CA                   # where the deck goes back to the game
HIDE_CARDS = [0x100180, 0x100200]       # objects 3, 4: the third and fourth courses' cards

NAME_ROWS_UP = 9                        # the course name: rows 13-14 -> 4-5
CARD_UP = 16                            # px the card and its frame go up (a multiple of 8: the best-time line follows)
NAME_SCRIPTS = [0x30E6E, 0x30EA6, 0x30EDE, 0x30F16]
CARD_SITES = {0x7BDC: 160, 0x7C0E: 144, 0x7C40: 144, 0x7CFC: 144}   # site -> the y it gives (0x7CFC: the
                                        # frame's second layer - the sheet metal - made again a state later)
RECORD_SITES = [0x7D68, 0x8272, 0x8A7A]  # jsr <patch 250's record hook>; nop
QUEUE_SITE = 0x1F14                     # jsr <patch 120's queue hook> (the fix-script queue)
STAGE_SELECT, PRACTICE = 0x108014, 0x108016   # the game's settings (from the soft dips)

SYSTEM_MODE = 0x10FD82
MAIN_SITE = 0x1068
REG_STATUS_B = 0x380000                 # bit 0: P1 Start (0 = pressed)
START_PREV = 0x10EF03                   # patch 020's: Start's last state
PHASE, COURSE_STEP, SCREEN_FADE, VBL_BUSY = 0x10806E, 0x10806C, 0x108074, 0x10A87E
MODE, DEMO_STEP, SCENE_STEP = 0x102960, 0x10805E, 0x108052
LOGO_SCENE = 256
MVS_TITLE = 4                           # the MODE the BIOS's title request sets (0x11CA)
LOGO_TEST = 0x400000 + 184 * 32 + 18    # the colour patch 160 tests for the logo (palette 184's 9: 0x4FDE)...
LOGO_MVS = 0x400000 + 144 * 32 + 18     # ... which on the MVS's title is in palette 144
LOGO_PINK = 0x4FDE
SAVED = 0x10EC92                        # spare RAM (word): palette 184's colour 9 meanwhile
FAKED = 0x10EC90                        # spare RAM: 1 while 160 runs with the attract's title shown to it
PLUS_OFF = 0x10EC63                     # patch 280's switch

import glob, os, re
from patchlib import load_patch

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = bytes.fromhex("4A39") + SYSTEM_MODE.to_bytes(4, "big")      # tst.b 0x10FD82
FLAG = bytes.fromhex("4A39") + PLUS_OFF.to_bytes(4, "big")          # tst.b PLUS_OFF (280's re-pointed ones)


def apply(rom):
    m280 = load_patch("280_standard_mvs.py")
    blocks = [int(m.group(1), 16) for m in (re.match(r"\s+0x([0-9A-F]+)\s+\d+ byte\(s\) of new code", l) for l in rom.log)
              if m]
    number = {}
    for path in glob.glob(os.path.join(HERE, "[0-9]*.py")):
        m = re.search(r'^NAME = "([^"]+)"', open(path).read(), re.M)
        number[m.group(1)] = os.path.basename(path)[:3]
    names = [number[n] for n in rom.applied[:-1]]
    assert len(blocks) == len(names), "mvs-menus: %d code blocks for %d patches" % (len(blocks), len(names))
    ends = blocks[1:] + [rom.next_free]
    done = 0
    for name, start, end in zip(names, blocks, ends):
        if name not in ENABLE:
            continue
        sites = sorted(a for pat in (CHECK, FLAG) for a in _find_all(rom, pat, start, end))
        labels = m280.check_labels(glob.glob(os.path.join(HERE, name + "_*.py"))[0])
        want = ENABLE[name]
        if want != "all":
            assert len(labels) == len(sites), "mvs-menus: patch %s's checks don't line up" % name
        for i, site in enumerate(sites):
            if (want == "all" or labels[i] in want) and rom.data[site:site + 6] == CHECK:
                rom.write(site, FLAG, expect=CHECK, why="standard MVS: the console's course select")
                done += 1
    assert done, "mvs-menus: nothing re-pointed"

    # the neon plus: the jump into patch 160's vblank code, through the scene test
    base160 = blocks[names.index("160")]
    end160 = ends[names.index("160")]
    into = bytes.fromhex("4EF9") + base160.to_bytes(4, "big")
    found = _find_all(rom, into, 0x0F1000, 0x100000)
    assert len(found) == 1, "mvs-menus: the jump into patch 160 not found once"
    out160 = [a for a in _find_all(rom, bytes.fromhex("4EF9"), base160, end160)
              if not base160 <= rom.u32(a + 2) < end160]
    assert len(out160) == 1, "mvs-menus: patch 160's way out not found once"
    after160 = rom.u32(out160[0] + 2)
    code = f"""
    bra.w plus                  | +0 the vblank chain, in front of patch 160
    bra.w out                   | +4 160's way out

plus:
    tst.w 0x{MODE:X}
    bne.s 1f
    cmpi.w #8,0x{DEMO_STEP:X}
    bne.s 1f
    cmpi.w #{LOGO_SCENE},0x{SCENE_STEP:X}
    bcc.s 1f
    jmp 0x{after160:X}                  | the intro's scenes: no plus
1:  cmpi.w #{MVS_TITLE},0x{MODE:X}
    bne.s 2f
    cmpi.w #{LOGO_PINK:#06x},0x{LOGO_MVS:X}
    bne.s 2f                            | (the logo isn't up: the warning)
    clr.w 0x{MODE:X}                    | the MVS's title: shown to 160 as the attract's
    move.w #20,0x{DEMO_STEP:X}
    move.w 0x{LOGO_TEST:X},0x{SAVED:X}
    move.w #{LOGO_PINK:#06x},0x{LOGO_TEST:X}
    move.b #1,0x{FAKED:X}
2:  jmp 0x{base160:X}

out:                                    | 160's way out
    tst.b 0x{FAKED:X}
    beq.s 9f
    clr.b 0x{FAKED:X}
    move.w #{MVS_TITLE},0x{MODE:X}      | the real ones back
    clr.w 0x{DEMO_STEP:X}
    move.w 0x{SAVED:X},0x{LOGO_TEST:X}
9:  jmp 0x{after160:X}
"""
    base = rom.place_code(code, why="the neon plus: not over the intro's scenes")
    rom.write(found[0] + 2, base.to_bytes(4, "big"), expect=base160.to_bytes(4, "big"),
              why="vblank chain: the neon plus only from the logo on")
    rom.write(out160[0] + 2, (base + 4).to_bytes(4, "big"), expect=after160.to_bytes(4, "big"),
              why="patch 160's way out: the MVS title's real mode back")

    # the pause on a standard MVS: patch 230's menu (its entry +0)
    pause230 = blocks[names.index("230")]
    code = f"""
main:                                   | the main loop's chain, in front of the rest
    tst.b 0x{SYSTEM_MODE:X}
    beq.s 9f                            | (the console: patch 020's hook does it)
    tst.b 0x{PLUS_OFF:X}
    bne.s 9f                            | (the trackball cabinet: the original)
    move.l %d0,-(%sp)
    move.b 0x{REG_STATUS_B:X},%d0       | Start newly pressed?
    not.b %d0
    andi.b #1,%d0
    move.b 0x{START_PREV:X},-(%sp)
    move.b %d0,0x{START_PREV:X}
    tst.b (%sp)+
    bne.s 8f
    tst.b %d0
    beq.s 8f
    cmpi.w #8,0x{MODE:X}                | in a course's countdown or play
    bne.s 8f
    tst.w 0x{PHASE:X}
    bne.s 8f
    tst.w 0x{SCREEN_FADE:X}
    bne.s 8f
    move.w 0x{COURSE_STEP:X},%d0
    cmpi.w #32,%d0
    beq.s 7f
    cmpi.w #36,%d0
    bne.s 8f
7:  move.w #1,0x{VBL_BUSY:X}            | the vblank's screen work held, as in patch 020's hook
    movem.l %d1-%d7/%a0-%a6,-(%sp)
    jsr 0x{pause230:X}
    movem.l (%sp)+,%d1-%d7/%a0-%a6
8:  move.l (%sp)+,%d0
9:  jmp 0x{rom.u32(MAIN_SITE):X}
"""
    base = rom.place_code(code, why="standard MVS: the pause menu")
    rom.write(MAIN_SITE, base.to_bytes(4, "big"), expect=rom.data[MAIN_SITE:MAIN_SITE + 4],
              why="main loop: the pause on a standard MVS")

    # leaving a course's play screen: patch 270's black_first
    black_first = blocks[names.index("270")] + 32
    for site in PLAY_CLEARS:
        rom.write(site, bytes.fromhex("4EB9") + black_first.to_bytes(4, "big"),
                  expect=bytes.fromhex("4EB9") + SPRITE_CLEAR.to_bytes(4, "big"),
                  why="leaving a course's play screen: black first, then the sprites cleared")

    # the course card without stage select: name at the top, the card higher
    assert CARD_UP % 8 == 0
    m020 = load_patch("020_menus.py")
    queue_prev = rom.u32(QUEUE_SITE + 2)
    rec_prev = [rom.u32(a + 2) for a in RECORD_SITES]
    copies = []
    for n, orig in enumerate(NAME_SCRIPTS):
        script = m020.fix_script(rom, orig)
        new = (int.from_bytes(script[:2], "big") - NAME_ROWS_UP).to_bytes(2, "big") + script[2:]
        copies.append("name%d: .byte %s\n    .even" % (n, ", ".join("0x%02X" % b for b in new)))
    swaps = "\n".join("    .long 0x%X, name%d" % (orig, n) for n, orig in enumerate(NAME_SCRIPTS))
    card_entries = "".join("    bra.w card%d\n" % k for k in range(len(CARD_SITES)))
    rec_entries = "".join("    bra.w rec%d\n" % k for k in range(len(RECORD_SITES)))
    cards = "".join(f"""
card{k}:
    move.w #160,%d1
    move.w #{y},%d2
    bsr.w on_card
    bne.s 1f
    subi.w #{CARD_UP},%d2
1:  rts
""" for k, y in enumerate(CARD_SITES.values()))
    recs = "".join(f"""
rec{k}:
    bsr.w on_card
    beq.s 1f
    jmp 0x{prev:X}                      | (patch 250's: as before)
1:  move.w #20,%d0
    move.w #{26 - CARD_UP // 8},%d1
    rts
""" for k, prev in enumerate(rec_prev))
    code = f"""
    bra.w queue                 | +0 the fix-script queue
{card_entries}{rec_entries}
on_card:                                | Z set = the course card without stage select (console / standard MVS)
    tst.b 0x{PLUS_OFF:X}
    bne.s 9f
    cmpi.w #8,0x{MODE:X}
    bne.s 9f
    cmpi.w #20,0x{COURSE_STEP:X}
    bne.s 9f
    tst.w 0x{STAGE_SELECT:X}
    bne.s 9f
    tst.w 0x{PRACTICE:X}                | (PRACTICE on: a course select of the game's own, practice or the first)
9:  rts

queue:                                  | a6 = the script queued
    bsr.w on_card
    bne.s 9f
    move.l %a0,-(%sp)
    lea swaps(%pc),%a0
1:  tst.l (%a0)
    beq.s 8f
    cmpa.l (%a0)+,%a6
    beq.s 2f
    addq.l #4,%a0
    bra.s 1b
2:  movea.l (%a0),%a6                   | the copy, higher up
8:  movea.l (%sp)+,%a0
9:  jmp 0x{queue_prev:X}
{cards}{recs}
swaps:
{swaps}
    .long 0
{chr(10).join(copies)}
"""
    base = rom.place_code(code, why="the course card without stage select: name on top, card higher")
    rom.write(QUEUE_SITE + 2, base.to_bytes(4, "big"), expect=queue_prev.to_bytes(4, "big"),
              why="fix-script queue: the course card's name higher (no stage select)")
    for k, (site, y) in enumerate(CARD_SITES.items()):
        rom.write(site, bytes.fromhex("4EB9") + (base + 4 + 4 * k).to_bytes(4, "big") + bytes.fromhex("4E71"),
                  expect=bytes.fromhex("323C00A0343C") + y.to_bytes(2, "big"),
                  why="course card: made higher (no stage select)")
    for k, site in enumerate(RECORD_SITES):
        rom.write(site + 2, (base + 4 + 4 * (len(CARD_SITES) + k)).to_bytes(4, "big"), expect=rec_prev[k].to_bytes(4, "big"),
                  why="course card: its best-time line higher (no stage select)")

    # PRACTICE on, STAGE SELECT off: the console's course select with two cards
    deck_prev = rom.u32(DECK_SITE)
    back = _find_all(rom, bytes.fromhex("4EF9") + AFTER_PANELS.to_bytes(4, "big"), 0x0F1000, 0x100000)
    assert len(back) == 1, "mvs-menus: the deck's jump back to 0x89CA not found once"
    hides = "\n".join("    ori.b #2,0x%X" % (o + 11) for o in HIDE_CARDS)
    code = f"""
    bra.w main                  | +0 the main loop's chain
    bra.w deck                  | +4 in front of the deck (0x8834)
    bra.w back                  | +8 the deck's way back to the game

main:
    tst.b 0x{PLUS_OFF:X}
    bne.s 9f
    tst.b 0x{PRACTICE_ONLY:X}
    bne.s 5f
    cmpi.w #8,0x{MODE:X}                | the course select, the game's STAGE SELECT off, PRACTICE on?
    bne.s 9f
    cmpi.w #20,0x{COURSE_STEP:X}
    bne.s 9f
    tst.w 0x{STAGE_SELECT:X}
    bne.s 9f
    tst.w 0x{PRACTICE:X}
    beq.s 9f
    move.w #1,0x{STAGE_SELECT:X}        | yes: STAGE SELECT on while it's up
    move.b #1,0x{PRACTICE_ONLY:X}
    bra.s 9f
5:  cmpi.w #8,0x{MODE:X}                | left it? STAGE SELECT off again
    bne.s 6f
    cmpi.w #20,0x{COURSE_STEP:X}
    beq.s 9f
6:  clr.w 0x{STAGE_SELECT:X}
    clr.b 0x{PRACTICE_ONLY:X}
9:  jmp 0x{rom.u32(MAIN_SITE):X}

deck:                                   | the choice wraps between the two courses
    tst.b 0x{PRACTICE_ONLY:X}
    beq.s 9f
    tst.b 0x{DECK_INIT:X}
    beq.s 9f
    move.l %d0,-(%sp)
    move.b 0x{P1_CHANGE:X},%d0
    or.b 0x{P2_CHANGE:X},%d0
    cmpi.b #1,0x{DECK_T:X}
    bne.s 1f
    btst #3,%d0                         | Right from the second: on to the first (the deck adds 1: 3 -> 0)
    beq.s 1f
    move.b #3,0x{DECK_T:X}
1:  tst.b 0x{DECK_T:X}
    bne.s 2f
    btst #2,%d0                         | Left from the first: to the second (the deck takes 1: 2 -> 1)
    beq.s 2f
    move.b #2,0x{DECK_T:X}
2:  move.l (%sp)+,%d0
9:  jmp 0x{deck_prev:X}

back:                                   | the deck has placed the cards: the other two hidden
    tst.b 0x{PRACTICE_ONLY:X}
    beq.s 9f
{hides}
9:  jmp 0x{AFTER_PANELS:X}
"""
    base = rom.place_code(code, why="PRACTICE only: the console's course select with two cards")
    rom.write(MAIN_SITE, base.to_bytes(4, "big"), expect=rom.data[MAIN_SITE:MAIN_SITE + 4],
              why="main loop: STAGE SELECT on while the practice-or-first select is up")
    rom.write(DECK_SITE, (base + 4).to_bytes(4, "big"), expect=deck_prev.to_bytes(4, "big"),
              why="course select's deck: two courses (PRACTICE only)")
    rom.write(back[0] + 2, (base + 8).to_bytes(4, "big"), expect=AFTER_PANELS.to_bytes(4, "big"),
              why="course select's deck: the other two cards hidden (PRACTICE only)")

    # BETA 1 on a standard MVS: patch 210's cells (VRAM address, tile word), moved to BETA_AT
    m210 = load_patch("210_beta_mark.py")
    base210, end210 = blocks[names.index("210")], ends[names.index("210")]
    col, row = m210.AT
    first = (0x7000 + 32 * col + row).to_bytes(2, "big")
    at = rom.data.find(first, base210, end210)
    while at >= 0 and at % 2:
        at = rom.data.find(first, at + 1, end210)
    assert at > 0, "mvs-menus: patch 210's cells not found"
    tiles = [rom.u16(at + 4 * i + 2) for i in range(len(m210.LABEL))]
    bcol, brow = BETA_AT
    cells = ", ".join("0x%04X, 0x%04X" % (0x7000 + 32 * (bcol + i) + brow, t) for i, t in enumerate(tiles))
    call = rom.data.find(bytes.fromhex("4EB81666"), base210, end210)    # jsr 0x1666.w (the assembler's short form)
    assert call > 0, "mvs-menus: patch 210's jsr 0x1666 not found"
    code = f"""
beta:                                   | in place of patch 210's jsr 0x1666 (the vblank, after the fix scripts)
    jsr 0x1666
    tst.b 0x{SYSTEM_MODE:X}
    beq.s 9f                            | (the console: patch 210 writes it, bottom right)
    tst.b 0x{PLUS_OFF:X}
    bne.s 9f
    movem.l %d0/%a0,-(%sp)
    lea cells(%pc),%a0
    moveq #{len(tiles) - 1},%d0
1:  move.w (%a0)+,0x3C0000
    nop                                 | VRAM needs a breath between address and data
    move.w (%a0)+,0x3C0002
    dbf %d0,1b
    movem.l (%sp)+,%d0/%a0
9:  rts

cells: .word {cells}
"""
    base = rom.place_code(code, why="standard MVS: BETA 1 bottom centre")
    # jsr.w can't reach patch code (above 0x8000) and jsr.l is 2 bytes longer, so the same 4 bytes become a bsr.w
    # (pc-relative: patch 210's code and this one are both near the fixed half's end)
    disp = base - (call + 2)
    assert -0x8000 <= disp < 0x8000, "mvs-menus: BETA's routine out of bsr.w reach"
    rom.write(call, bytes.fromhex("6100") + (disp & 0xFFFF).to_bytes(2, "big"), expect=bytes.fromhex("4EB81666"),
              why="vblank: BETA 1 on a standard MVS, after the bottom line (bsr.w)")


def _find_all(rom, pattern, lo, hi):
    out, at = [], rom.data.find(pattern, lo, hi)
    while at >= 0:
        out.append(at)
        at = rom.data.find(pattern, at + 1, hi)
    return out
