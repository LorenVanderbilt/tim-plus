NAME = "course-fade"
DESCRIPTION = "Home console (AES): no bright flash as a course fades in for its countdown"

# The original game flashes white as a course comes up for its countdown, whether the tour was skipped or ran to its
# end. The course set-up loads the course's colours at full strength (0x22F40 etc.) while the screen is empty. At
# the countdown's start (course step 32, 0xD05C on) a fade-in brings them up from dark, but it takes turns, one
# group of palettes per frame: an even step does the course's main palettes (0x22F96, from palette 16), an odd step
# the rest (0x22FB2 / 0x22FF4). The first step is odd and the course's graphics appear on that frame, so the main
# palettes show at full strength for two or three frames before their first turn, then drop to dark and fade in.
#
# On the console both groups fade on every step: the same fade over the same time, just without the wait. The
# professional course (3) has a fade of its own (0xD06A: 0x23010...) that this doesn't touch.

from patchlib import jsr

SYSTEM_MODE = 0x10FD82
SITE = 0xD0A2                   # btst #0,d1; bne.w 0xD0B6 (odd steps go to the other group)
EVEN, ODD, DONE = 0xD0AA, 0xD0B6, 0xD0CC
MAIN, OTHER1, OTHER2 = 0x22F96, 0x22FB2, 0x22FF4


def apply(rom):
    code = f"""
fade:                                   | d1 = the fade's step (from 0xD094-0xD0A0)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 8f
    addq.l #4,%sp                       | don't return to the site
    add.w %d1,%d1
    movem.w %d1,-(%sp)
    jsr 0x{MAIN:X}                      | the course's main palettes
    movem.w (%sp),%d1
    jsr 0x{OTHER1:X}                    | and the rest, the same step
    movem.w (%sp)+,%d1
    jsr 0x{OTHER2:X}
    jmp 0x{DONE:X}
8:  btst #0,%d1                         | arcade: unchanged
    beq.s 9f
    addq.l #4,%sp
    jmp 0x{ODD:X}
9:  rts                                 | on to 0x{EVEN:X}
"""
    base = rom.place_code(code, why="AES: the course fade-in without the flash")
    rom.write(SITE, jsr(base) + bytes.fromhex("4E71"),
              expect=bytes.fromhex("080100006600000E"), why="countdown fade: every group every step (console)")
