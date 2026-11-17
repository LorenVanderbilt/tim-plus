NAME = "course-select-show"
DESCRIPTION = ("Home console (AES): the course select's grey frame placed at its size from the start instead of hidden "
               "(patch 190's hiding flashed white on real hardware as the cards appeared)")

# Patch 190 hides the course select's objects among 0-7 until patch 020's deck starts (the grey frame, made at its
# full size, showed through the opening wipe), and shows them again in front of the deck on its first frame. On the
# user's console (BackBit, a CRT) the course select then flashed white as its cards came in; MAME showed nothing.
# The user's test builds (2026-11-16): no flash without 190; still a flash when 190 only brought back the frame
# (the cards and arrows left to the deck, which shows / hides them itself); no flash with 190's hiding off.
#
# So on the console 190's hiding is switched off (its bank test aimed at a bank no object has: it never hides, and
# its show then has nothing to do), and the frame - the one full-size leftover - is put where and at the size the
# deck keeps it (020's CARD_SIZE, PANEL_Y) from when the game makes it until the deck takes over. The empty frame
# now shows while the course select's wipe opens, and the cards come in inside it.
#
# Hiding the frame another way also flashed: parked below the screen until the deck (PARK_Y = 400, IM Test J). Only
# a frame on screen all along didn't - so the flash seems tied to the frame appearing as the cards start. For the
# beta it stays shown (the user, 2026-11-16); hiding it without the flash is for after the beta (TODO.md).

DECK_SITE = 0x8836                      # the long of 0x8834's jsr: patch 190's show (entry +4; +0 its hide)
SYSTEM_MODE = 0x10FD82
MODE, COURSE_STEP, STAGE_SELECT = 0x102960, 0x10806C, 0x108014
DECK_INIT = 0x10EF0C                    # patch 020's: set once the deck has started
FRAME = 0x100000                        # object 0
MAIN_SITE = 0x1068                      # the main loop's chain (in front of patches 250 / 190 / 020)

PARK_Y = None                           # None: the frame in its place, shown; a y (400: below the screen) parks it
                                        # hidden until the deck - flashed on the console too (the user's IM Test J)

from patchlib import load_patch


def entry_target(rom, addr):
    """Where a bra.w at addr goes (a patch's entry table), else addr."""
    if rom.data[addr:addr + 2] == b"\x60\x00":
        return addr + 2 + int.from_bytes(rom.data[addr + 2:addr + 4], "big", signed=True)
    return addr


def apply(rom):
    show190 = rom.u32(DECK_SITE)                    # 190's entry: bra.w show

    m020 = load_patch("020_menus.py")
    # 190's hide: cmpi.w #0x18,4(a0) - aimed at a bank no object has, so it never hides anything
    hide190 = entry_target(rom, show190 - 4)
    pat = bytes.fromhex("0C6800180004")
    cmp_at = rom.data.find(pat, hide190, hide190 + 80)
    assert cmp_at > 0, "course-select-show: patch 190's bank test not found"
    rom.write(cmp_at + 2, b"\xFF\xFF", expect=b"\x00\x18", why="patch 190: no hiding (console) - the frame is placed instead")
    frame_y = m020.PANEL_Y - 16 * m020.CARD_SIZE // 256 if PARK_Y is None else PARK_Y
    code = f"""
main:                                   | each frame, in front of the main loop's chain
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    cmpi.w #8,0x{MODE:X}
    bne.s 9f
    cmpi.w #20,0x{COURSE_STEP:X}
    bne.s 9f
    tst.w 0x{STAGE_SELECT:X}
    beq.s 9f
    tst.b 0x{DECK_INIT:X}
    bne.s 9f
    cmpi.w #0x18,0x{FRAME + 4:X}        | the course select's frame (bank 0x18, animation 0x68)
    bne.s 9f
    cmpi.w #0x68,0x{FRAME + 6:X}
    bne.s 9f
    move.w #160,0x{FRAME + 12:X}        | where and how big the deck keeps it
    move.w #{frame_y},0x{FRAME + 14:X}
    move.w #{m020.CARD_SIZE},0x{FRAME + 16:X}
    move.w #{m020.CARD_SIZE},0x{FRAME + 18:X}
9:  jmp 0x{rom.u32(MAIN_SITE):X}
"""
    base = rom.place_code(code, why="the course select's frame placed from the start")
    rom.write(MAIN_SITE, base.to_bytes(4, "big"), expect=rom.data[MAIN_SITE:MAIN_SITE + 4],
              why="main loop: the course select's frame at the deck's size")
