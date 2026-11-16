NAME = "instructions"
DESCRIPTION = "Home console (AES): the instructions explain the console's controls (joystick, A, Start, B)"

# The instructions (course step 4, 0xD7xx) type out a list of text scripts in a box, 3 seconds each (0xD864):
# 0xD908 on a Japanese console, 0xD916 elsewhere (157, 158, 0x2B, 159, 160, 0x2B: two panels, two screens each,
# 0x2B the blank box between). The English talked about the trackball and "button A" to look around; on the
# console that's the joystick, A = Steady Hand, the pause's LOOK AROUND - and the Japanese third panel (B hides the
# hand holding the Zap-Rod) was never in the English. On the console, outside Japan, the list is this patch's own,
# of new scripts (numbers 0x100 on, which the hook at 0xD878 finds here instead of in the table 0x2D708).
#
# The demo under the text is its own table of actions (0xD924: routine, parameter, frames - each called every frame
# of its time); the instructions end when it runs out, after 1080 frames, as the original six screens do. The
# console's longer text (nine screens, 1620 frames) gets a longer table: the original's actions, then for the B
# panel the hand shown / hidden twice (0xDC38 sets the hand flag 0x108EEC - the game's own action, never used: the
# Japanese third panel's), a pause (0xDC32 with 0), then the original's ending (0xDA34 on). The table is stepped
# through by this patch's copy of 0xD81A-0xD84F, which picks the table.
#
# Each screen shows a page of two lines of the tall font (34 characters a line) - a fresh page each time (the
# original scrolled a line at a time, which was disorienting). Every panel lasts two pages (a one-page
# panel stays up twice as long). Characters: A-Z, space, '.', '-', '"'.

from patchlib import jsr

PANELS = [             # each panel: pages of two lines (34 characters at most), 3 seconds a page
    [("MOVE THE ZAP-ROD ON THE SCREEN", "WITH THE JOYSTICK."),
     ("HOLD BUTTON A TO STEADY YOUR", "HAND AND MOVE MORE SLOWLY.")],
    [("PRESS START TO PAUSE THE GAME", "AND CHOOSE LOOK AROUND"),
     ("TO REVIEW THE WHOLE COURSE", "WITH THE JOYSTICK.")],
    [("PRESS BUTTON B TO SHOW OR HIDE", "THE HAND HOLDING THE ZAP-ROD.")],
]
WIDTH = 34
SYSTEM_MODE, REGION = 0x10FD82, 0x10FD83
BLANK = 0x2B            # the game's empty box
DEMO = 0xD924           # the demo's action table (8 bytes an action; -1 ends it)
DEMO_FINALE = 0xDA34    # its ending (4 actions, 56 frames)
WAIT, HAND = 0xDC32, 0xDC38
STEP_TIMER, STEP_INDEX = 0x10A8A0, 0x10A89E    # the current action's frames left, its offset in the table


def halves(ch):
    """The tall font's top and bottom tile (low bytes; tile 0xE00 + this, palette 6)."""
    if "A" <= ch <= "O":
        t = 0xC0 + ord(ch) - 64
    elif "P" <= ch <= "Z":
        t = 0xE0 + ord(ch) - 80
    elif ch == " ":
        return 0xC0, 0xC0
    elif ch == "-":
        return 0xEB, 0xFB
    elif ch == '"':
        return 0xED, 0xC0
    elif ch == ".":
        return 0xC0, 0xFD
    else:
        raise SystemExit("instructions: no tile for %r" % ch)
    return t, t + 0x10


def screen(top, bottom):
    """A text box script as script 157's: border, line 1 (top / bottom half), a gap, line 2, border."""
    def row(text, half):
        assert len(text) <= WIDTH, "instructions line too long: %r" % text
        return bytes(halves(c)[half] for c in text.ljust(WIDTH))
    b = bytearray([0x70, 0x56])
    b += bytes([0x62, 0x65, 0xEE]) + bytes([0xEF] * 34)          # top border (palette 6, tiles 0x5xx)
    b += bytes([0x40, 0x66, 0x00]) + bytes([0x80, 0x01, 0x01])
    b += bytes([0x61, 0x6E]) + row(top, 0)
    b += bytes([0x40, 0x66, 0x02]) + bytes([0x80, 0x01, 0x11])
    b += bytes([0x61, 0x6E]) + row(top, 1)
    b += bytes([0x40, 0x66, 0x12]) + bytes([0x80, 0x01, 0x01])
    b += bytes([0x61, 0x6E]) + bytes([0xC0] * 34)                # the gap between the lines
    b += bytes([0x40, 0x66, 0x02]) + bytes([0x80, 0x01, 0x11])
    b += bytes([0x61, 0x6E]) + row(bottom, 0)
    b += bytes([0x40, 0x66, 0x02]) + bytes([0x80, 0x01, 0x11])
    b += bytes([0x61, 0x6E]) + row(bottom, 1)
    b += bytes([0x40, 0x66, 0x12])
    b += bytes([0xE2, 0x01, 0x65, 0xFE]) + bytes([0xFF] * 34)    # bottom border
    b += bytes([0x40, 0x66, 0x10, 0x00])
    return bytes(b)


def apply(rom):
    # check the template against the game's own script 157 (its borders and line structure)
    p157 = int.from_bytes(rom.data[0x2D708 + 4 * 157:0x2D708 + 4 * 157 + 4], "big")
    assert rom.data[p157:p157 + 2] == b"\x70\x56" and rom.data[p157 + 2:p157 + 5] == bytes([0x62, 0x65, 0xEE])
    scripts, order = [], []
    for panel in PANELS:
        assert len(panel) in (1, 2), "a panel is one or two pages"
        for top, bottom in panel:
            order.append(0x100 + len(scripts))
            scripts.append(screen(top, bottom))
        if len(panel) == 1:
            order.append(order[-1])            # a one-page panel stays up as long as the others
        order.append(BLANK)
    order.append(0xFFFF)
    # the demo: the original's actions up to its ending, the B panel's, then the ending
    orig = [rom.data[a:a + 8] for a in range(DEMO, DEMO_FINALE, 8)]
    finale = []
    a = DEMO_FINALE
    while rom.data[a] & 0x80 == 0:
        finale.append(rom.data[a:a + 8]); a += 8
    act = lambda r, p, t: r.to_bytes(4, "big") + p.to_bytes(2, "big") + t.to_bytes(2, "big")
    screens = len(order) - 1
    frames = lambda e: int.from_bytes(e[6:8], "big") + 1     # (an action runs its time + 1 frames)
    orig_frames = sum(frames(e) for e in orig)
    fin_frames = sum(frames(e) for e in finale)
    b_start = 180 * (screens - 3)                # the B panel's text comes up here
    extra = [act(WAIT, 0, b_start - orig_frames - 1)]
    extra += [act(HAND, 1, 89), act(HAND, 0, 89), act(HAND, 1, 89), act(HAND, 0, 89)]
    extra += [act(WAIT, 0, 180 * screens - fin_frames - b_start - 360 - 1)]
    assert b_start > orig_frames and 180 * screens - fin_frames - b_start - 360 > 0
    demo = b"".join(orig + extra + finale) + b"\xFF\xFF\xFF\xFF\x00\x00\x00\x00"
    demo_words = ", ".join("0x%04X" % int.from_bytes(demo[i:i + 2], "big") for i in range(0, len(demo), 2))
    data = "\n".join("script_%d: .byte %s\n    .even" % (k, ", ".join("0x%02X" % x for x in s))
                     for k, s in enumerate(scripts))
    ptrs = "\n".join("    .long script_%d" % k for k in range(len(scripts)))
    code = f"""
    bra.w pick_list             | +0 which list (replaces 0xD854-0xD863)
    bra.w script_ptr            | +4 a script number -> its address (replaces 0xD878-0xD885)
    bra.w demo_frame            | +8 the demo's frame: next action, call it (replaces 0xD81A-0xD84F)

pick_list:
    lea 0xD908,%a0                      | (the game's: Japan's list, else the English)
    tst.b 0x{REGION:X}
    beq.s 1f
    lea 0xD916,%a0
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    lea our_list(%pc),%a0               | the console outside Japan: this patch's
1:  rts

script_ptr:                             | d0 = the number -> fp = the script
    cmpi.w #0x100,%d0
    bcc.s 1f
    lea 0x2D708,%fp
    add.w %d0,%d0
    add.w %d0,%d0
    movea.l (%fp,%d0.w),%fp
    rts
1:  subi.w #0x100,%d0
    add.w %d0,%d0
    add.w %d0,%d0
    lea our_scripts(%pc),%fp
    movea.l (%fp,%d0.w),%fp
    rts

demo_table:                             | a0 = the demo's table (the console's outside Japan: this patch's)
    lea 0x{DEMO:X},%a0
    tst.b 0x{REGION:X}
    beq.s 1f
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    lea our_demo(%pc),%a0
1:  rts
demo_frame:                             | (the game's 0xD81A-0xD84F, with the table picked)
    subq.w #1,0x{STEP_TIMER:X}
    bpl.s 2f
    bsr.s demo_table                    | the next action
    move.w 0x{STEP_INDEX:X},%d0
    addq.w #8,%d0
    tst.l (%a0,%d0.w)
    bpl.s 1f
    addq.l #4,%sp                       | the table's end: the instructions are over
    jmp 0xD89A
1:  move.w %d0,0x{STEP_INDEX:X}
    move.w 6(%a0,%d0.w),0x{STEP_TIMER:X}
2:  bsr.s demo_table                    | this frame of the action
    move.w 0x{STEP_INDEX:X},%d1
    move.w 4(%a0,%d1.w),%d0
    movea.l (%a0,%d1.w),%a0
    jmp (%a0)
our_demo: .word {demo_words}
our_list: .word {", ".join("0x%04X" % n for n in order)}
our_scripts:
{ptrs}
{data}
"""
    base = rom.place_code(code, why="AES: the instructions' new text")
    rom.write(0xD854, jsr(base) + bytes.fromhex("4E71") * 5,
              expect=bytes.fromhex("41FA00B24A2D7D83670000064" + "1FA00B4"), why="instructions: the console's list")
    rom.write(0xD878, jsr(base + 4) + bytes.fromhex("4E71") * 4,
              expect=bytes.fromhex("4DF90002D708D040D0402C760000"), why="instructions: the console's scripts")
    block = rom.data[0xD81A:0xD850]
    assert block[:4] == bytes.fromhex("536D28A0") and block[-2:] == bytes.fromhex("4E90")
    rom.write(0xD81A, jsr(base + 8) + bytes.fromhex("4E71") * 24, expect=block,
              why="instructions: the console's longer demo (the B panel)")
