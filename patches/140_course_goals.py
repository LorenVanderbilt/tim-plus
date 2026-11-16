NAME = "course-goals"
DESCRIPTION = ("Home console (AES): on the expert and professional courses too, the rod goes on into the goal "
               "before the course ends")

# The expert and professional courses' finishes get what patch 060 gave the novice goal: the rod zooms on past the
# line, the camera following, the timer held, then the end. Each course's finish is
# its own trigger-zone handler - "move.l 0x108EB2,(its time record); move.w 0x108812,d0 ..." (it also keeps the best
# time): practice 0x200FA, novice 0x202DC (patch 060's), expert 0x207B6, professional 0x20C72 - all called the same
# way (from 0x1FFB6: the zone's saved d1 at 10(sp) - checked with breakpoints on practice and expert). This is patch
# 060's goal_zone for expert and professional (practice is left as it was, which played better). It uses the same
# RAM, so patch 060's play_timer (the timer held) and play_move (the zoom) do the rest.


from patchlib import load_patch, jmp

SYSTEM_MODE = 0x10FD82
ROD_X, ROD_Y = 0x108EA6, 0x108EAA
ROD_OLD_X, ROD_OLD_Y = 0x108EAE, 0x108EB0
FINISHES = {0x207B6: 0x10A7FE,  # a course's finish handler: move.l 0x108EB2,<this> (6 bytes) - then its end
            0x20C72: 0x10A802}  # (expert, professional; practice 0x200FA / 0x10A7F6 is left as it was,
                                # which played better)


def apply(rom):
    g = load_patch("060_goal_pan.py")
    first, hold, dx, dy = g.GOAL_FIRST, g.GOAL_HOLD, g.GOAL_DX, g.GOAL_DY
    entries = "".join(f"""
finish_{k}:
    bsr.w finish                        | Z set: the end now
    bne.s 1f
    move.l 0x108EB2,0x{rec:X}           | (the instruction this jump replaced) - the course's end
    jmp 0x{at + 6:X}
1:  bclr #7,10(%sp)                     | not yet: the zone fires again next frame (the caller's saved d1)
    rts
""" for k, (at, rec) in enumerate(FINISHES.items()))
    code = "\n".join("    bra.w finish_%d" % k for k in range(len(FINISHES))) + entries + f"""
finish:                                 | Z set = the end now (or the arcade), Z clear = not yet
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 8f
    move.b #2,0x{hold:X}                | in the goal: no timer
    tst.w 0x{first:X}
    bne.w 1f
    move.w 0x{ROD_X:X},0x{first:X}      | the finish line: note it
    move.w 0x{ROD_Y:X},0x{first + 2:X}
    clr.w 0x{dy:X}                      | ... and which way the rod was going: the zoom
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
5:  move.w #{g.GOAL_SPEED},0x{dx:X}
    cmp.w %d3,%d2
    bcs.s 6f                            | mostly up / down
    tst.w %d0
    bpl.s 1f
    neg.w 0x{dx:X}
    bra.s 1f
6:  clr.w 0x{dx:X}
    move.w #{g.GOAL_SPEED},0x{dy:X}
    tst.w %d1
    bpl.s 1f
    neg.w 0x{dy:X}
1:  move.w 0x{ROD_X:X},%d0              | how far on: |dx| + |dy|
    sub.w 0x{first:X},%d0
    bpl.s 2f
    neg.w %d0
2:  move.w 0x{ROD_Y:X},%d1
    sub.w 0x{first + 2:X},%d1
    bpl.s 3f
    neg.w %d1
3:  add.w %d1,%d0
    cmpi.w #{g.GOAL_EXTRA},%d0
    bcc.s 7f
    moveq #1,%d0                        | not yet (Z clear)
    rts
7:  clr.w 0x{first:X}
8:  cmp.w %d0,%d0                       | the end (Z set)
    rts
"""
    base = rom.place_code(code, why="AES: expert / professional, further into the goal")
    for k, (at, rec) in enumerate(FINISHES.items()):
        old = bytes.fromhex("2B6D0EB2") + (rec - 0x108000).to_bytes(2, "big")
        rom.write(at, jmp(base + 4 * k), expect=old,
                  why="course finish 0x%X: the end a little further in (console)" % at)
