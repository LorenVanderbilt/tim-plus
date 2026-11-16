NAME = "tour-skip"
DESCRIPTION = "Home console (AES): a shorter black pause after a course's tour (skipped or not)"

# In the original, skipping the course tour (0xC528) fades the screen out (about 17 frames) and then waits 60 frames
# (0x10A8A2) before the course set-up (step 28). The screen sits black for about 40 frames, plus the set-up and the
# countdown's fade-in. (Patch 180 isn't involved: there are 70 black frames with or without it.) The tour's own end
# (0xC51E) has the same fade-out, wait and set-up. On the console both waits are WAIT frames.

from patchlib import jsr

WAIT = 22                       # frames from the tour's end or skip to the course set-up (originally 60; the
                                # fade-out takes about 17, so don't go much lower)

SYSTEM_MODE = 0x10FD82
SITES = [0xC51E, 0xC538]        # move.w #60,0x28A2(a5) at the tour's end and at a skip, after the fade-out starts


def apply(rom):
    code = f"""
    move.w #60,0x28A2(%a5)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    move.w #{WAIT},0x28A2(%a5)
9:  rts
"""
    base = rom.place_code(code, why="AES: a shorter wait after the course tour")
    for site in SITES:
        rom.write(site, jsr(base), expect=bytes.fromhex("3B7C003C28A2"),
                  why="course tour's end: the wait before the course set-up (console)")
