NAME = "rod-size"
DESCRIPTION = "Home console (AES): a smaller Zap-Rod (redrawn at 80%, its hit area to match) on easier difficulties"

# The user's idea (2026-11-15): on some lower difficulties, a smaller rod. Mock-ups: the ball redrawn (not the
# hardware shrink, which drops pixel rows) at 90% and 80%; tried both on the BackBit, the user picked 80%.
#
# The look: the rod in play is object 0 (0x100000), its looks are the animations of bank 0x38 (0x18AC0's table picks
# one): 0x1C no hand (piece entries 0x51E54-0x51E64: the ball alone, 2 x 2 tiles), 0x00 the outline hand (patch
# 020's B), 0x18 a touch (the hand shaken, then 0x1C) and others - in all 38 pictures (0x51DD0-0x51E64) the ball is
# the same 24 x 24 drawing (5 frames, exact), in the picture's palette offset 0 (224). This patch finds it in each,
# swaps in the 80% ball (art/rod/ball_80_N.png - tools/make_rod_art.py made them; touch them up freely, colours from
# the ball's palette), stores the changed tiles as new ones and, at the sprite builder (0x2D0C, chained in front of
# patch 050's hook), hands out the new lists. (The countdown's solid hands, object 5, draw their own ball: unchanged.)
# The hit area: the sprite builder (0x2BF4-0x2C42, from the animation's frame) and 0x18A4A (the rod's look each
# frame) both give the object three boxes (+0x18 / 1A / 1C: ids into the box table 0xE882E, 6 bytes each: x, y
# (words), width, height (bytes)) - a cross of boxes that makes a 24 px circle: 24 x 12, 20 x 20, 12 x 24. The
# smaller rod gets the same three, scaled, in new entries.

SMALL_ROD = [1, 1, 1, 0, 0, 0, 0, 0]   # DIFFICULTY 1-8: 1 = the 80% rod, 0 = the original

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from png_tiles import read_indices

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art", "rod")
SIZE = 80
SYSTEM_MODE, GAME_LEVEL = 0x10FD82, 0x10800A
BALL_ENTRIES = [0x51E54, 0x51E58, 0x51E5C, 0x51E60, 0x51E64]   # the ball alone: its 5 frames
PICTURES = range(0x51DD0, 0x51E68, 4)                          # every picture with the ball
PAL = [0x0000, 0x0000, 0x3211, 0x7222, 0x5343, 0x7444, 0x1554, 0x7555, 0x3666, 0x7AAA, 0x5CCC, 0x7FFF, 0x0D83,
       0x0532, 0x0888, 0x397E]           # palette 224 (as tools/make_rod_art.py)
BOX_TABLE = 0xE882E
FULL_BOXES = (0x08F4, 0x08FA, 0x0900)
NEW_BOXES_AT = 0xE9400                  # in the unused 0xFF run at 0xE938C (ids must stay under 0x8000)


def rgb(w):
    c5 = lambda v: v * 255 // 31
    return (c5(((w >> 7) & 0x1E) | ((w >> 14) & 1)), c5(((w >> 3) & 0x1E) | ((w >> 13) & 1)),
            c5(((w << 1) & 0x1E) | ((w >> 12) & 1)))


def boxes(size):
    """The original's three boxes (each centred on the 24 px ball's middle, 12, 12) scaled: even sizes, centred."""
    out = b""
    for w, h in ((24, 12), (20, 20), (12, 24)):
        w2, h2 = [2 * round(v * size / 200) for v in (w, h)]
        out += (12 - w2 // 2).to_bytes(2, "big") + (12 - h2 // 2).to_bytes(2, "big") + bytes([w2, h2])
    return out


class Picture:
    """A piece entry's picture: format 1 (a word, then tile words) or 5 (palette offset byte + tile word each);
    columns of rows tiles, a column at a time."""
    def __init__(self, rom, entry):
        v = rom.u32(entry)
        self.rom, self.fmt = rom, v >> 29
        self.at = entry + (v & 0xFFFFF)
        self.cols, self.rows = ((v >> 24) & 31) + 1, ((v >> 20) & 15) + 1
        assert self.fmt in (1, 5), "piece 0x%X: format %d" % (entry, self.fmt)
        n = self.cols * self.rows
        self.size = 2 + 2 * n if self.fmt == 1 else 3 * n + 2
        self.tiles = [self.tile(k) for k in range(n)]
        self.px = [[0] * (16 * self.cols) for _ in range(16 * self.rows)]
        for k, (p, t) in enumerate(self.tiles):
            c, r = divmod(k, self.rows)
            for y, row in enumerate(rom.sprite_tile(t)):
                self.px[16 * r + y][16 * c:16 * c + 16] = row

    def tile(self, k):
        if self.fmt == 1:
            return 0, self.rom.u16(self.at + 2 + 2 * k)
        return self.rom.data[self.at + 3 * k], self.rom.u16(self.at + 3 * k + 1)

    def find(self, balls):
        """(frame, x, y) of the exact 24 x 24 ball, or None."""
        for n, b in enumerate(balls):
            for y in range(len(self.px) - 23):
                for x in range(len(self.px[0]) - 23):
                    if self.px[y][x + 8] == b[0][8] and all(
                            self.px[y + j][x + i] == b[j][i] for j in range(24) for i in range(24) if b[j][i]):
                        return n, x, y
        return None


def apply(rom):
    for e, b in zip(FULL_BOXES, (bytes.fromhex("00000006180C"), bytes.fromhex("000200021414"),
                                 bytes.fromhex("000600000C18"))):
        assert rom.data[BOX_TABLE + e:BOX_TABLE + e + 6] == b, "the rod's boxes"
    pal = [rgb(w) for w in PAL]
    pal[0] = (255, 0, 255)
    balls = [[row[:24] for row in Picture(rom, e).px[:24]] for e in BALL_ENTRIES]
    small = [read_indices(os.path.join(ART, "ball_%d_%d.png" % (SIZE, n)), pal) for n in range(5)]

    pairs, data = [], []
    for entry in PICTURES:
        pic = Picture(rom, entry)
        hit = pic.find(balls)
        assert hit, "piece 0x%X: no ball" % entry
        n, bx, by = hit
        px = [row[:] for row in pic.px]
        for j in range(24):                     # the ball out
            for i in range(24):
                if balls[n][j][i]:
                    px[by + j][bx + i] = 0
        for j in range(32):                     # the small one in (it sits in its 32 x 32 as the ball in its own)
            for i in range(32):
                v = small[n][j][i]
                if v and by + j < len(px) and bx + i < len(px[0]) and not px[by + j][bx + i]:
                    px[by + j][bx + i] = v
        new = bytearray(rom.data[pic.at:pic.at + pic.size])
        for k, (p, t) in enumerate(pic.tiles):
            c, r = divmod(k, pic.rows)
            block = [row[16 * c:16 * c + 16] for row in px[16 * r:16 * r + 16]]
            if block == [row[16 * c:16 * c + 16] for row in pic.px[16 * r:16 * r + 16]]:
                continue
            assert p == 0, "piece 0x%X: the ball in palette offset %d" % (entry, p)
            t2 = rom.add_sprite_tile(block, why="rod %d%%" % SIZE, share=True)
            at = 2 + 2 * k if pic.fmt == 1 else 3 * k + 1
            new[at:at + 2] = t2.to_bytes(2, "big")
        pairs.append(entry)
        data.append(bytes(new))

    new = boxes(SIZE)
    rom.write(NEW_BOXES_AT, new, expect=b"\xFF" * len(new), why="the smaller rod's hit boxes")
    ids = list(FULL_BOXES) + [NEW_BOXES_AT - BOX_TABLE + 6 * j for j in range(3)]
    assert max(ids) < 0x8000

    prev = rom.u32(0x2D0E)                                  # patch 050's piece-list hook
    assert rom.data[0x2D0C:0x2D0E] == b"\x4E\xB9"
    code = f"""
    bra.w piece_list            | +0 the sprite builder: a piece entry (a1) -> its tile list
    bra.w rod_boxes             | +4 the rod's hit boxes (0x18AAC, a1 = the rod)
    bra.w builder_boxes         | +8 the sprite builder, after an object's boxes from its animation (0x2C44)
small: .byte {", ".join(str(s) for s in SMALL_ROD)}     | per difficulty: 1 = the small rod
    .even

piece_list:                             | (d0 is the builder's: keep it)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    cmpa.l #0x{PICTURES[0]:X},%a1
    bcs.s 9f
    cmpa.l #0x{PICTURES[-1]:X},%a1
    bhi.s 9f
    move.w 0x{GAME_LEVEL:X},%d1
    andi.w #7,%d1
    move.b small(%pc,%d1.w),%d1
    beq.s 9f
    move.l %a0,-(%sp)
    lea pairs(%pc),%a0
1:  cmpa.l (%a0)+,%a1
    beq.s 2f
    addq.l #4,%a0
    tst.l (%a0)
    bne.s 1b
    move.l (%sp)+,%a0
    bra.s 9f
2:  movea.l (%a0),%a1
    move.l (%sp)+,%a0
    rts
9:  jmp 0x{prev:X}

rod_boxes:
    movem.l %d0/%a0,-(%sp)
    lea box_ids(%pc),%a0
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    move.w 0x{GAME_LEVEL:X},%d0
    andi.w #7,%d0
    move.b small(%pc,%d0.w),%d0
    beq.s 1f
    addq.l #6,%a0
1:  move.w (%a0)+,0x18(%a1)
    move.w (%a0)+,0x1A(%a1)
    move.w (%a0)+,0x1C(%a1)
    movem.l (%sp)+,%d0/%a0
    rts

builder_boxes:                          | (replaces "pea 0x2C44; move.w (a3)+,d6" - the flags of that move go on)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    cmpi.w #0x{FULL_BOXES[0]:04X},0x18(%a2)       | the rod's boxes: by size
    bne.s 1f
    cmpi.l #0x{FULL_BOXES[1]:04X}{FULL_BOXES[2]:04X},0x1A(%a2)
    bne.s 1f
    move.l %a1,-(%sp)
    move.l %a2,%a1
    bsr.s rod_boxes
    move.l (%sp)+,%a1
1:  move.l #0x2C44,(%sp)
    move.w (%a3)+,%d6
    jmp 0x2C4A

box_ids: .word {", ".join("0x%04X" % i for i in ids)}
pairs:
{chr(10).join("    .long 0x%X, list_%d" % (e, k) for k, e in enumerate(pairs))}
    .long 0
{chr(10).join("list_%d: .byte %s%s    .even" % (k, ", ".join("0x%02X" % b for b in l), chr(10)) for k, l in enumerate(data))}
"""
    base = rom.place_code(code, why="AES: the smaller rod")
    jsr = lambda a: bytes.fromhex("4EB9") + a.to_bytes(4, "big")
    rom.write(0x2D0C, jsr(base), expect=jsr(prev), why="sprite builder: the smaller rod's pictures")
    rom.write(0x18AAC, bytes.fromhex("4EF9") + (base + 4).to_bytes(4, "big"), expect=bytes.fromhex("337C08F40018"),
              why="the rod's hit boxes: by size")
    rom.write(0x2C44, jsr(base + 8), expect=bytes.fromhex("487AFFFE3C1B"),
              why="sprite builder: the rod's animation boxes by size")
