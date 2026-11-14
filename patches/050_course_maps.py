NAME = "course-maps"
DESCRIPTION = ("Home console (AES): the course select's map pictures redrawn by the user at the console's size; "
               "no cards flashed in the game's own layout before the deck")

# Patch 020 shows the course select's four map pictures shrunk to CARD_SIZE (90%) by the hardware, which drops whole
# rows and columns (text in the pictures got hard to read). The user redraws them at that size
# (art/course_maps/NAME_90.png, 231 x 117, from the original's colours); this patch stores each as new sprite tiles
# (in the free end-of-ROM tiles, tools/free_sprite_tiles.txt) and, on the console's course select only, shows that
# card unshrunk (the course record screen etc. show the cards full size: the original pictures there).
#
# How the game draws a card: the object's frame gives a piece entry in the table at 0x5100C - for Novice 0x51B08 -
# whose low 20 bits are the offset from the entry to the tile list (3 bytes a tile: tile number, palette offset added
# to the object's palette base 0x90; 16 columns of 8, a column at a time). The sprite builder turns the entry into
# the list's address at 0x2D0C; the hook there gives the console the new list. The new picture sits in the 256 x 128
# card where the shrunk one shows (12, 6 in), the rest see-through (under the frame).
#
# Palettes: the card's own (offsets 0x15-0x18); each 16 x 16 tile takes the one that has its colours (the colours
# are matched to palette entries from the original card: art/course_maps/NAME_full.png + its original tiles).

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from png_tiles import read_rgba        # (rows of ((r, g, b), alpha))

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art", "course_maps")
SYSTEM_MODE = 0x10FD82
PIECES = {"practice": (0x51B04, 52), "novice": (0x51B08, 56), "expert": (0x51B0C, 60),
          "professional": (0x51B10, 64)}     # course: (its piece entry, its card object type)
ART_AT = (12, 6)                       # where the 90% picture sits in the 256 x 128 card
CARD_OBJECTS = 0x100080                # objects 1-4: the cards
# Before the deck (patch 020's course_deck, from state 16) the course select's set-up creates the cards (0x19A2, in
# state 8 -> 12) and they show for a frame or two in the game's own layout - a flash of the wrong card in front.
# On the console the four cards' pieces (entries 0x51B04-0x51B10) get an empty tile list until the deck has placed
# them once (patch 020's DECK_INIT).
STAGE_SELECT, SELECT_STATE, MODE, COURSE_STEP = 0x108014, 0x10A8A0, 0x102960, 0x10806C
CARD_ENTRIES = (0x51B04, 0x51B08, 0x51B0C, 0x51B10)
DECK_INIT = 0x10EF0C                   # patch 020's RAM + 12


def card_list(rom, entry):
    """The card's tile list as (tile, palette offset, flips) x 128 and its entry size: the entry's format (top 3
    bits of its first byte) - 3 = 3 bytes (tile, palette offset), 0 = 4 bytes (tile, attribute word: palette
    offset high, bit 0 / 1 = flip across / down)."""
    at = entry + (int.from_bytes(rom.data[entry:entry + 4], "big") & 0xFFFFF)
    fmt = rom.data[entry] >> 5
    if fmt == 3:
        return 3, [(rom.u16(at + 3 * k), rom.data[at + 3 * k + 2], 0) for k in range(128)]
    assert fmt == 0, "card list format %d" % fmt
    return 4, [(rom.u16(at + 4 * k), rom.data[at + 4 * k + 2], rom.data[at + 4 * k + 3] & 3) for k in range(128)]


def apply(rom):
    lists = {}
    for name, (entry, _) in PIECES.items():
        path = os.path.join(ART, name + "_90.png")
        if not os.path.exists(path):
            continue
        size, old = card_list(rom, entry)
        full = read_rgba(os.path.join(ART, name + "_full.png"))
        # (palette offset, index) -> colour, from the original card
        colour = {}
        for k, (tile, pal, flip) in enumerate(old):
            c, r = divmod(k, 8)
            px = rom.sprite_tile(tile)
            if flip & 1:
                px = [row[::-1] for row in px]
            if flip & 2:
                px = px[::-1]
            for y in range(16):
                for x in range(16):
                    if px[y][x]:
                        colour[(pal, px[y][x])] = full[r * 16 + y][c * 16 + x][0]
        pals = sorted({p for p, _ in colour})
        pic = read_rgba(path)
        canvas = [[((0, 0, 0), 0)] * 256 for _ in range(128)]
        for y, row in enumerate(pic):
            for x, v in enumerate(row):
                canvas[ART_AT[1] + y][ART_AT[0] + x] = v
        dist = lambda a, b: sum((a[i] - b[i]) ** 2 for i in range(3))
        new = bytearray()
        for c in range(16):
            for r in range(8):
                block = [[canvas[r * 16 + y][c * 16 + x] for x in range(16)] for y in range(16)]
                cols = {v[0] for row in block for v in row if v[1]}
                best, cost = pals[0], None
                for p in pals:
                    entries = [(i, rgb) for (q, i), rgb in colour.items() if q == p]
                    s = sum(min(dist(col, rgb) for _, rgb in entries) for col in cols)
                    if cost is None or s < cost:
                        best, cost = p, s
                entries = [(i, rgb) for (q, i), rgb in colour.items() if q == best]
                px = [[0 if not v[1] else min(entries, key=lambda e: dist(v[0], e[1]))[0] for v in row]
                      for row in block]
                t = rom.add_sprite_tile(px, why="%s map (console)" % name, share=True)
                new += bytes([t >> 8, t & 0xFF, best]) if size == 3 else bytes([t >> 8, t & 0xFF, best, 0])
        lists[name] = (entry, new)

    blank_checks = "\n".join("""    cmpa.l #0x%X,%%a1
    beq.s 7f""" % e for e in CARD_ENTRIES) + """
    bra.w 6f
7:  lea blank_list(%pc),%a1
    rts"""
    data = "\n".join("list_%s: .byte %s" % (n, ", ".join("0x%02X" % b for b in l)) for n, (_, l) in lists.items())
    checks = "\n".join("""    cmpa.l #0x%X,%%a1
    bne.s 1f
    lea list_%s(%%pc),%%a1
    rts
1:""" % (e, n) for n, (e, _) in lists.items())
    types = "\n".join("""    cmpi.w #%d,2(%%a0)
    beq.s 2f""" % PIECES[n][1] for n in lists)
    code = f"""
    bra.w piece_list            | +0 the sprite builder: a piece entry (a1) -> its tile list
    bra.w cards_size            | +4 the course select, after placing the cards (then patch 040's)
    bra.w pick_size             | +8 a course picked: the card's last size (then patch 040's)

piece_list:
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    cmpi.w #8,0x{MODE:X}                | only on the course select (the course record etc. show the card at
    bne.w 9f                            | its full size: the original picture there)
    cmpi.w #20,0x{COURSE_STEP:X}
    bne.w 9f
    tst.w 0x{STAGE_SELECT:X}
    beq.w 9f
    tst.b 0x{DECK_INIT:X}               | (patch 020's: set once the deck has placed the cards)
    bne.w 6f
{blank_checks}
6:
{checks}
9:  move.l (%a1),%d1                    | (the instructions this call replaced)
    andi.l #0xFFFFF,%d1
    adda.l %d1,%a1
    rts

| a redrawn card is shown unshrunk (its picture is already the console's size)
is_redrawn:                             | a0 = a card object: Z set = redrawn
{types}
    rts
2:  rts
cards_size:
    move.l %a0,-(%sp)
    lea 0x{CARD_OBJECTS:X},%a0
    moveq #3,%d1
1:  tst.w 18(%a0)
    beq.s 3f
    bsr.s is_redrawn
    bne.s 3f
    move.w #255,16(%a0)
    move.w #255,18(%a0)
3:  lea 128(%a0),%a0
    dbf %d1,1b
    move.l (%sp)+,%a0
    jmp 0x@CARDS_NEXT@
pick_size:
    jsr 0x@PICK_NEXT@
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    bsr.s is_redrawn
    bne.s 1f
    move.w #255,16(%a0)
    move.w #255,18(%a0)
1:  rts
{data}
    .even
blank_list: .space 512
"""
    # patch 040's hooks, to chain in front of: the course select's end jump and the pick's last size
    a_after = rom.data.find(b"\x4E\xF9\x00\x0F", 0x0F1000, 0x100000)
    while a_after >= 0:     # patch 020's "jmp patch 040 cards_tall" - the one that lands on cards_tall's code
        tgt = int.from_bytes(rom.data[a_after + 2:a_after + 6], "big")
        if rom.data[tgt:tgt + 2] == b"\x60\x00":           # an entry table's bra.w: follow it
            tgt += 2 + int.from_bytes(rom.data[tgt + 2:tgt + 4], "big", signed=True)
        if rom.data[tgt:tgt + 4] == bytes.fromhex("48E74040"):   # movem.l d1/a1,-(sp): cards_tall
            break
        a_after = rom.data.find(b"\x4E\xF9\x00\x0F", a_after + 2, 0x100000)
    assert a_after >= 0, "patch 040's cards_tall jump"
    cards_next = int.from_bytes(rom.data[a_after + 2:a_after + 6], "big")
    pick_next = int.from_bytes(rom.data[0x8BEC:0x8BF0], "big")

    code = code.replace("@CARDS_NEXT@", "%X" % cards_next).replace("@PICK_NEXT@", "%X" % pick_next)

    base = rom.place_code(code, why="AES: the redrawn course maps")
    jsr = lambda a: bytes.fromhex("4EB9") + a.to_bytes(4, "big")
    rom.write(0x2D0C, jsr(base) + bytes.fromhex("4E714E71"), expect=bytes.fromhex("22110281000FFFFFD3C1"),
              why="sprite builder: a redrawn card's tile list (console)")
    rom.write(a_after + 2, (base + 4).to_bytes(4, "big"), expect=cards_next.to_bytes(4, "big"),
              why="course select: a redrawn card unshrunk")
    rom.write(0x8BEC, (base + 8).to_bytes(4, "big"), expect=pick_next.to_bytes(4, "big"),
              why="course picked: a redrawn card unshrunk")
