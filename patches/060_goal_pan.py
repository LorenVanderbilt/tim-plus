NAME = "goal-further"
DESCRIPTION = "Home console (AES): the rod goes further into the goal before the win, so the goal box shows"

# Crossing the goal line ends the course at once (the goal is a trigger zone, event 25 -> 0x202DC; course step 44),
# with the camera stopped short and the goal box (its GOAL / GOOD sign) cut off at the screen's edge. On the console
# the first touch of the goal zone notes where the rod is and play goes on (the camera follows the rod as usual);
# the win comes once the rod has moved GOAL_EXTRA pixels on from there (across + up / down: any course's goal
# direction).
#
# Once the rod has crossed the line it doesn't wait for the stick: it zooms on (GOAL_SPEED pixels a frame, the way
# it was going as it crossed) - play's movement (0x4DA8, the trackball's dx / dy for 0x1B114) is replaced meanwhile.
#
# The timer stops while the rod is in the goal zone (each time the zone fires it holds the timer for the next two
# frames), so crossing the line in the last moment still wins; backing out of the goal lets it run again.
#
# A zone fires once: the caller (0x1FF10) marks it (bit 15 of the zone's +12 word, kept in d1 on its stack) after the
# handler returns - to fire again next frame, that saved d1's bit is cleared.

from patchlib import jsr, jmp

GOAL_EXTRA = 64         # pixels on past the goal line before the win
GOAL_SPEED = 8          # pixels a frame the rod zooms in once it's crossed

SYSTEM_MODE = 0x10FD82
ROD_X, ROD_Y = 0x108EA6, 0x108EAA
GOAL_FIRST = 0x10EEF0   # (spare RAM) the rod's x, y at the goal line; x 0 = not reached
GOAL_HANDLER = 0x202DC  # move.l 0x108EB2,0x10A7FA (6 bytes) - then the win
GOAL_HOLD = 0x10EEF4    # (spare RAM) frames the timer stays held
GOAL_DX, GOAL_DY = 0x10EEF6, 0x10EEF8   # (spare RAM) the zoom: pixels a frame
ROD_OLD_X, ROD_OLD_Y = 0x108EAE, 0x108EB0
MOVE_SITE = 0x4DA8      # play: move.w 0x10A7CE,d0; move.w 0x10A7D0,d1 (the trackball's dx, dy) -> the rod
PLAY_TIMER_CALL = 0x4D24   # play's timer call (patch 040's play_timer, then the game's 0x13BE8)


def apply(rom):
    timer_next = int.from_bytes(rom.data[PLAY_TIMER_CALL + 2:PLAY_TIMER_CALL + 6], "big")
    assert rom.data[PLAY_TIMER_CALL:PLAY_TIMER_CALL + 2] == b"\x4E\xB9"
    code = f"""
    bra.w goal_zone             | +0 the goal zone fired
    bra.w play_timer            | +4 play's timer, each frame
    bra.w play_move             | +8 play's movement, each frame

goal_zone:
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 8f
    move.b #2,0x{GOAL_HOLD:X}           | in the goal: no timer
    tst.w 0x{GOAL_FIRST:X}
    bne.w 1f
    move.w 0x{ROD_X:X},0x{GOAL_FIRST:X}       | the goal line: note it
    move.w 0x{ROD_Y:X},0x{GOAL_FIRST + 2:X}
    clr.w 0x{GOAL_DY:X}                 | ... and which way the rod was going: the zoom
    move.w 0x{ROD_X:X},%d0
    sub.w 0x{ROD_OLD_X:X},%d0
    move.w 0x{ROD_Y:X},%d1
    sub.w 0x{ROD_OLD_Y:X},%d1
    move.w %d0,%d2
    bpl.s 4f
    neg.w %d2
4:  move.w %d1,%d3
    bpl.s 5f
    neg.w %d3
5:  move.w #{GOAL_SPEED},0x{GOAL_DX:X}
    cmp.w %d3,%d2
    bcs.s 6f                            | mostly up / down
    tst.w %d0
    bpl.s 1f
    neg.w 0x{GOAL_DX:X}
    bra.s 1f
6:  clr.w 0x{GOAL_DX:X}
    move.w #{GOAL_SPEED},0x{GOAL_DY:X}
    tst.w %d1
    bpl.s 1f
    neg.w 0x{GOAL_DY:X}
1:  move.w 0x{ROD_X:X},%d0              | how far on: |dx| + |dy|
    sub.w 0x{GOAL_FIRST:X},%d0
    bpl.s 2f
    neg.w %d0
2:  move.w 0x{ROD_Y:X},%d1
    sub.w 0x{GOAL_FIRST + 2:X},%d1
    bpl.s 3f
    neg.w %d1
3:  add.w %d1,%d0
    cmpi.w #{GOAL_EXTRA},%d0
    bcc.s 7f
    bclr #7,10(%sp)                     | not yet: the zone fires again next frame (the caller's saved d1)
    rts
7:  clr.w 0x{GOAL_FIRST:X}
8:  move.l 0x108EB2,0x10A7FA            | (the instruction this jump replaced) - the win
    jmp 0x{GOAL_HANDLER + 6:X}

play_timer:
    tst.b 0x{GOAL_HOLD:X}
    beq.s 1f
    subq.b #1,0x{GOAL_HOLD:X}
    rts
1:  clr.w 0x{GOAL_FIRST:X}              | not in the goal: no goal line noted (a restart, or backed out)
    jmp 0x{timer_next:X}

play_move:
    move.w 0x10A7CE,%d0                 | (the instructions this call replaced: the trackball dx, dy - a5 + 0x27CE)
    move.w 0x10A7D0,%d1
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.b 0x{GOAL_HOLD:X}
    beq.s 1f
    tst.w 0x{GOAL_FIRST:X}
    beq.s 1f
    move.w 0x{GOAL_DX:X},%d0            | over the line: the zoom
    move.w 0x{GOAL_DY:X},%d1
1:  rts
"""
    base = rom.place_code(code, why="AES: further into the goal before the win")
    rom.write(GOAL_HANDLER, jmp(base),
              expect=bytes.fromhex("2B6D0EB227FA"), why="goal zone: the win a little further in (console)")
    rom.write(PLAY_TIMER_CALL, jsr(base + 4),
              expect=jsr(timer_next), why="play's timer: held in the goal zone")
    rom.write(MOVE_SITE, jsr(base + 8) + bytes.fromhex("4E71"),
              expect=bytes.fromhex("302D27CE322D27D0"), why="play's movement: the rod zooms into the goal")
