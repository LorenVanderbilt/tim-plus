NAME = "intro-every-time"
DESCRIPTION = "Home console (AES): the power-on intro plays at every start of the attract (for now: after games too)"

# On the BackBit the intro (patch 080) played only once: going back to the cart's menu and loading the game again
# skipped it. Patch 080 plays it while its flag INTRO is 0 and leaves it at 3. MAME (and the AES BIOS there) clears
# work RAM at a reset, but on the cart the RAM survived, so the flag stayed 3. A first fix (a mark left at every
# hand-back to the BIOS, so a start without it counted as fresh) still skipped it there. So the intro now plays at
# every start of the attract: at power-on, on a reload, and after each game.
# Two places clear its flags (and the ending's, in case a reset came mid-intro), so it doesn't hang on one way in:
#   * USER request 2 (the attract starts), before patch 020's handler - early enough for the music's early start;
#   * the attract's scene player, at step 4 with patch 020's GO_TITLE set (where patch 080 starts the intro), in front
#     of patch 080's hook - in case the start came another way.

SYSTEM_MODE = 0x10FD82
USER_REQ2 = 0x1008                      # USER's request table: request 2's routine (patch 020's attract_start)
SCENE_HOOK = 0xE34E                     # the attract's scene player (patch 080's jsr)
SCENE_STEP, GO_TITLE = 0x108052, 0x10EF00
INTRO, MUSIC_SENT, END_FLAG = 0x10EEFA, 0x10EEFB, 0x108058      # patch 080's flags, the ending's state (long)


def apply(rom):
    prev_req2 = rom.u32(USER_REQ2)
    assert rom.data[SCENE_HOOK:SCENE_HOOK + 2] == b"\x4E\xB9"
    prev_scene = rom.u32(SCENE_HOOK + 2)
    code = f"""
    bra.w request2              | +0 USER request 2
    bra.w scene                 | +4 the attract's scene player

request2:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    bsr.s clear
9:  jmp 0x{prev_req2:X}

scene:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    cmpi.w #4,0x{SCENE_STEP:X}
    bne.s 9f
    tst.b 0x{GO_TITLE:X}
    beq.s 9f
    cmpi.b #3,0x{INTRO:X}               | (a stale flag: the intro again; the music then comes with it)
    bne.s 9f
    bsr.s clear
9:  jmp 0x{prev_scene:X}

clear:
    clr.b 0x{INTRO:X}
    clr.b 0x{MUSIC_SENT:X}
    clr.l 0x{END_FLAG:X}
    rts
"""
    base = rom.place_code(code, why="AES: the intro at every start")
    rom.write(USER_REQ2, base.to_bytes(4, "big"), expect=prev_req2.to_bytes(4, "big"),
              why="USER request 2: the intro's flags cleared")
    rom.write(SCENE_HOOK + 2, (base + 4).to_bytes(4, "big"), expect=prev_scene.to_bytes(4, "big"),
              why="attract scenes: a stale intro flag cleared")
