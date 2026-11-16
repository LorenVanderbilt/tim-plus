NAME = "miss-chimes"
DESCRIPTION = "Home console (AES): every miss plays the two chimes the original kept for time-outs and practice"

# In the original, a miss (course step 40) plays jingle 0x8019 (sound list 0x19, command 0x202C) twice: once at its
# start (0x956E) and once as the Zap-Rod falls past 350 (0x979C). Both only happen when the time-up flag (0x10A85C)
# is set, which is on a time-out or any practice miss (step 40 sets the flag for course 0 at 0x900C), so a wall
# touch on the other courses had no chimes. On the console both checks pass on every miss. The flag's other uses
# (how the miss looks, its voice) are untouched.

from patchlib import jsr

SYSTEM_MODE = 0x10FD82
TIME_UP = 0x10A85C
START_SITE = 0x956E             # tst.w 0x285C(a5); beq.w 0x9580 (the chime at the miss's start)
FALL_SITE = 0x979C              # tst.w 0x285C(a5); beq.w 0x9B16 (the chime as the rod falls past 350)
FALL_SKIP = 0x9B16


def apply(rom):
    code = f"""
    bra.w at_start              | +0
fall:                           | +4: returns to the 350 check, or skips it as the original's beq did
    tst.b 0x{SYSTEM_MODE:X}
    beq.s 1f
    tst.w 0x{TIME_UP:X}
    bne.s 1f
    addq.l #4,%sp
    jmp 0x{FALL_SKIP:X}
1:  rts
at_start:                       | Z clear = play the chime
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    move #0,%ccr
    rts
1:  tst.w 0x{TIME_UP:X}
    rts
"""
    base = rom.place_code(code, why="AES: the miss's two chimes on every miss")
    hook = lambda off: jsr(base + off)          # a call to this patch's entry at base + off
    rom.write(START_SITE, hook(0) + bytes.fromhex("670A"), expect=bytes.fromhex("4A6D285C6700000C"),
              why="miss: the first chime on every miss (console)")
    rom.write(FALL_SITE, hook(4) + bytes.fromhex("4E71"), expect=bytes.fromhex("4A6D285C67000374"),
              why="miss: the second chime on every miss (console)")
