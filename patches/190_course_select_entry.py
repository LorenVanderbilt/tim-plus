NAME = "course-select-entry"
DESCRIPTION = "Home console (AES): the course select comes up without full-size leftovers before its cards"

# Coming back to the course select after winning a course, its objects (bank 0x18) are still there from the last
# visit: the picked card grown to full size, the arrows, the highlight. They're drawn while the screen opens. The
# game then makes the frame (select state 8) and the cards (12) at full size, and only at the input state (16) does
# patch 020's deck (0x8834) size and place them. So for about 36 frames there's a full-size frame and stale pieces,
# and then everything jumps into the deck. (The game's own select does this too with stage select on.)
#
# On the console, in ARCADE's course select (course step 20) until the deck has started (select state below 16, or
# patch 020's DECK_INIT not yet set), the course select's objects among 0-7 are hidden. The sprite builder skips an
# object with bit 1 of +11 set, which is the deck's own "not shown". On the deck's first frame, the objects this
# patch hid are shown again and the deck places them. The hiding runs from the main loop (in front of patch 020's
# hook there, 0x1066), the showing in front of the deck (0x8834).

SYSTEM_MODE = 0x10FD82
MODE, COURSE_STEP, STAGE_SELECT = 0x102960, 0x10806C, 0x108014
SELECT_STATE = 0x10A8A0
DECK_INIT = 0x10EF0C                    # patch 020's: set once the deck has started
HIDDEN = 0x10EC24                       # spare RAM: the objects 0-7 this patch hid, one bit each
BANK = 0x18                             # the course select's objects


def apply(rom):
    assert rom.data[0x1066:0x1068] == b"\x4E\xB9" and rom.data[0x8834:0x8836] == b"\x4E\xB9"
    prev_main, prev_deck = rom.u32(0x1068), rom.u32(0x8836)
    code = f"""
    bra.w hide                  | +0 the main loop, each frame (before patch 020's main_hook)
    bra.w show                  | +4 the course select's input state, each frame (before patch 020's deck)

hide:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    cmpi.w #8,0x{MODE:X}
    bne.s 9f
    cmpi.w #20,0x{COURSE_STEP:X}
    bne.s 9f
    tst.w 0x{STAGE_SELECT:X}
    beq.s 9f
    cmpi.w #16,0x{SELECT_STATE:X}
    bcs.s 1f
    tst.b 0x{DECK_INIT:X}
    bne.s 9f
1:  movem.l %d1/%a0,-(%sp)
    lea 0x100000,%a0
    moveq #0,%d1
2:  cmpi.w #0x{BANK:X},4(%a0)
    bne.s 3f
    btst #1,11(%a0)
    bne.s 3f                            | already hidden, by the game or by us
    bset #1,11(%a0)
    bset %d1,0x{HIDDEN:X}
3:  lea 128(%a0),%a0
    addq.w #1,%d1
    cmpi.w #8,%d1
    bne.s 2b
    movem.l (%sp)+,%d1/%a0
9:  jmp 0x{prev_main:X}

show:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    tst.b 0x{HIDDEN:X}
    beq.s 9f
    movem.l %d1/%a0,-(%sp)
    lea 0x100000,%a0
    moveq #0,%d1
2:  btst %d1,0x{HIDDEN:X}
    beq.s 3f
    bclr #1,11(%a0)
3:  lea 128(%a0),%a0
    addq.w #1,%d1
    cmpi.w #8,%d1
    bne.s 2b
    clr.b 0x{HIDDEN:X}
    movem.l (%sp)+,%d1/%a0
9:  jmp 0x{prev_deck:X}
"""
    base = rom.place_code(code, why="AES: the course select without leftovers")
    rom.write(0x1068, base.to_bytes(4, "big"), expect=prev_main.to_bytes(4, "big"),
              why="main loop: the course select's objects hidden until its deck starts")
    rom.write(0x8836, (base + 4).to_bytes(4, "big"), expect=prev_deck.to_bytes(4, "big"),
              why="course select's deck: the hidden objects shown")
