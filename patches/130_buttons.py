NAME = "buttons"
DESCRIPTION = ("Home console (AES): in a maze B = the original look around (hold B, move the stick), C = show / hide "
               "the hand; the character select's black band back")

# 1. The black bar at the bottom of the character select is back: patch 020 had taken it off on the console (its
#    no_band calls at 0x7804 / 0x7A4A); the game's own instructions go back there (patch 020's no_band code stays,
#    unused).
# 2. B is the original's look around and C the hand toggle:
#    patch 010 turns the pad into the cabinet's button record; patch 020's p1_buttons (called from there) passed only
#    B in a maze (A is slow mode / STEADY HAND, read straight from the pad). Now, in a maze, B goes in as the cabinet's
#    button 1 (hold = the game's own look mode: the stick moves the camera, letting go glides it back - the timer
#    runs, as on the arcade) and C as button 2 (the game's hand toggle, 0x4850). Elsewhere A / B stay as they were.
#    * Patch 040's pause LOOK AROUND ends with A or B; with B it undid the hand toggle B used to make - now B makes
#      none, so that undo is taken out (same size, nops). And a B that ended it doesn't start the game's own look
#      straight after: B counts again once it's been let go.
#    * The instructions (patch 070's pages, same lengths) say so.

from patchlib import load_patch, find_once, jsr

PAUSE_LOOK = False      # the pause's LOOK AROUND (patch 040): True = shown (a debugging aid), False = left out of
                        # the release, since B in a maze is the look around

PCUR = 0x10EF0B                 # patch 020's pause cursor
LOOK = 0x10EE10                 # patch 040: 0 off, 1 the pause's look, 2 gliding back
B_HELD_OFF = 0x10EEFE           # this patch: 1 = B ignored until it's let go
BAND_SITES = [0x7804, 0x7A4A]
BAND_ORIG = bytes.fromhex("3B7C0001007C")          # move.w #1,0x7C(a5): the black band's request

PAGES = [   # (old page) -> (new page), patch 070's: lines of 34 characters at most
    (("PRESS START TO PAUSE THE GAME", "AND CHOOSE LOOK AROUND"),
     ("HOLD BUTTON B AND MOVE THE", "JOYSTICK TO LOOK AROUND.")),
    (("TO REVIEW THE WHOLE COURSE", "WITH THE JOYSTICK."),
     ("OR PAUSE AND CHOOSE LOOK AROUND", "TO STOP THE CLOCK WHILE LOOKING.") if PAUSE_LOOK else
     ("LET GO OF B TO RETURN TO THE", "ZAP-ROD. THE CLOCK KEEPS RUNNING.")),
    (("PRESS BUTTON B TO SHOW OR HIDE", "THE HAND HOLDING THE ZAP-ROD."),
     ("PRESS BUTTON C TO SHOW OR HIDE", "THE HAND HOLDING THE ZAP-ROD.")),
]



def apply(rom):

    # 1. the black band
    for site in BAND_SITES:
        cur = bytes(rom.data[site:site + 6])
        assert cur[:2] == b"\x4E\xB9" and rom.orig[site:site + 6] == BAND_ORIG
        rom.write(site, BAND_ORIG, expect=cur, why="character select: the black bottom band back")

    # 2. patch 020's p1_buttons: "move.b d2,d0; andi.b #0x30,d0; bsr.s in_maze; bne.s 1f; andi.b #0x20,d0; 1: rts" (bsr.s: in_maze from its byte)
    pat = bytes.fromhex("10020200003061")
    p1 = find_once(rom, pat, "patch 020's p1_buttons")
    assert rom.data[p1 + 8:p1 + 16] == bytes.fromhex("660402000020" "4E75")
    in_maze = p1 + 8 + int.from_bytes(rom.data[p1 + 7:p1 + 8], "big", signed=True)
    # its entry in patch 020's table ("bra.w p1_buttons"), and the call to that from patch 010's joystick code
    entries = [a for a in range(0xF1000, p1, 4) if rom.data[a:a + 2] == b"\x60\x00"
               and a + 2 + int.from_bytes(rom.data[a + 2:a + 4], "big", signed=True) == p1]
    assert len(entries) == 1, "patch 020's p1_buttons entry"
    entry = entries[0]
    call = find_once(rom, jsr(entry), "the call to p1_buttons")

    # patch 040's look_check: "btst #5,d0; beq.s 2f; eori.w #1,0x108EEC" (B undid the game's hand toggle)
    undo = bytes.fromhex("08000005" "6708" "0A790001" "00108EEC")
    u = find_once(rom, undo, "patch 040's hand undo")

    code = f"""
    bra.w buttons               | +0 the pad's P1 buttons -> the cabinet's (d2 = the pad, d0 = the result)

buttons:
    jsr 0x{in_maze:X}                   | Z set = a maze (countdown or play)
    bne.s 8f
    move.b %d2,%d0
    lsr.b #1,%d0                        | B -> button 1 (look), C -> button 2 (the hand)
    andi.b #0x30,%d0
    tst.b 0x{LOOK:X}                    | the pause's look (or its glide back): B is ending it
    beq.s 1f
    move.b #1,0x{B_HELD_OFF:X}
1:  tst.b 0x{B_HELD_OFF:X}
    beq.s 2f
    btst #5,%d2                         | B still held: not yet
    bne.s 3f
    clr.b 0x{B_HELD_OFF:X}
    bra.s 2f
3:  andi.b #0x20,%d0                    | (C still counts)
2:  rts
8:  move.b %d2,%d0                      | elsewhere: A / B as before
    andi.b #0x30,%d0
    rts
"""
    base = rom.place_code(code, why="AES: B = look around, C = the hand")
    rom.write(call, jsr(base), expect=jsr(entry), why="P1 buttons: in a maze B = look, C = the hand")
    rom.write(u + 6, bytes.fromhex("4E71" * 4), expect=undo[6:], why="pause look: B no longer undoes a hand toggle")

    # the pause's LOOK AROUND (patch 040's in-place changes to patch 020's pause, undone): five rows again
    if not PAUSE_LOOK:
        pcur = PCUR.to_bytes(4, "big")
        for old, new, what in ((bytes.fromhex("13FC0005") + pcur, bytes.fromhex("13FC0004") + pcur, "Up from the top"),
                               (bytes.fromhex("0C390006") + pcur, bytes.fromhex("0C390005") + pcur, "Down past the end")):
            at = find_once(rom, old, "pause: %s" % what)
            rom.write(at, new, expect=old, why="pause: no LOOK AROUND (%s)" % what)
        text = b"  LOOK AROUND      "
        at = rom.data.find(b"  STEADY HAND      \x00" + text, 0xF1000, 0x100000)
        assert at > 0, "pause: LOOK AROUND's text"
        rom.write(at + 20, b" " * len(text), expect=text, why="pause: no LOOK AROUND")

    # 3. the instructions' pages
    ins = load_patch("070_instructions.py")
    for old, new in PAGES:
        a, b = ins.screen(*old), ins.screen(*new)
        assert len(a) == len(b)
        at = find_once(rom, a, "instructions page %r" % (old,))
        rom.write(at, b, expect=a, why="instructions: %s / %s" % new)
