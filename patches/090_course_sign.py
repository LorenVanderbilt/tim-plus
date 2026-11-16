NAME = "course-sign"
DESCRIPTION = "Home console (AES): the course's name sign at the start of the course tour blinks more slowly"

# The course tour (course step 24) opens on the course's sign (EXPERT COURSE ...), blinking: its object's routine
# (0xCA60-0xCAD2) hides it while bit 3 of the frame counter (0x10A882) is set: 8 frames on, 8 off, which felt too
# fast. On the console it follows BLINK_SHIFT below: now 0, so the sign stays on without blinking.

from patchlib import jsr

BLINK_SHIFT = 0        # 0 = no blinking (always shown), 3 = the original (8 frames on / 8 off),
                       # 4 = 16 / 16 (about twice a second), 5 = 32 / 32
SYSTEM_MODE, FRAMES = 0x10FD82, 0x10A882


def apply(rom):
    if BLINK_SHIFT == 0:                # (bit 0 of d2 clear: the sign's shown, every frame)
        code = f"""
sign_blink:                             | (replaces "move.w (0x2882,a5),d2; lsr.w #3,d2" at 0xCABE)
    move.w 0x{FRAMES:X},%d2
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    moveq #0,%d2
1:  lsr.w #3,%d2
    rts
"""
    else:
        code = f"""
sign_blink:                             | (replaces "move.w (0x2882,a5),d2; lsr.w #3,d2" at 0xCABE)
    move.w 0x{FRAMES:X},%d2
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    lsr.w #{BLINK_SHIFT - 3},%d2
1:  lsr.w #3,%d2
    rts
"""
    assert BLINK_SHIFT == 0 or 4 <= BLINK_SHIFT <= 11
    base = rom.place_code(code, why="AES: the course sign's slower blink")
    rom.write(0xCABE, jsr(base), expect=bytes.fromhex("342D2882E64A"),
              why="course sign: the blink's speed")
