NAME = "smooth-swing"
DESCRIPTION = ("Home console (AES): the swinging bars (the professional course's robot-face 'eyebrows') turn smoothly, "
               "with three in-between drawings for each of the game's")

# The swinging bars on the professional course's robot face are object animations 0x54 / 0x58 of bank 0x0C:
# 29 frames, each showing one of 11 drawings (piece words 0x86DA-0x8702, about 18 degrees apart) for 24 ticks.
# The obstacle routines (0x1A4C4 / 0x1A528) take their speed off the frame's countdown (object +0x0A) every
# frame and the sprite builder takes 1 more, so at speed 2 the drawing changed every 8 frames and looked choppy.
#
# The animation itself is untouched: its timing, its sounds (the obstacle routines test the frame number) and its
# hit boxes (which come from the frame). Only the picture changes. While a drawing is up, the builder is handed
# an in-between drawing chosen by how far the countdown has run towards the next frame, a quarter at a time,
# so a new drawing shows every 2 frames.
#   * The art: art/swing_bar/pose_NN.png and pose_NN_Q.png, made by tools/make_swing_art.py and safe to touch
#     up by hand. Each is 128 x 128 pixels centred on the bolt, stored as new tiles in an 8 x 8-tile list
#     (format 1, palette offset 4, like the originals).
#   * Two hooks in the sprite builder, both in front of patch 100's: the piece loop (0x2C44) swaps the frame's
#     single piece for this patch's record (an existing 8 x 8 format-1 entry at the canvas's position) and
#     notes which list to use; the piece-to-list step (0x2D0C) then hands that list out.

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from patchlib import jsr
import make_swing_art as art
from png_tiles import read_indices

SYSTEM_MODE = 0x10FD82
LIST = 0x10EED0                 # spare RAM (long): the list to hand out next, 0 = none
SIZE_ENTRY = 0x51330            # an existing format-1 piece entry of 8 x 8 tiles; only its size is used
QUARTER = 6                     # a quarter of a drawing's 24 ticks


def apply(rom):
    v = rom.u32(SIZE_ENTRY)
    assert v >> 29 == 1 and ((v >> 24) & 31) == 7 and ((v >> 20) & 15) == 7, "the 8 x 8 entry"
    pal = art.palette()
    blank = [[0] * 16 for _ in range(16)]
    lists = {}                                  # (pose, quarter) -> the list's bytes
    for name, key in art.names():
        px = read_indices(os.path.join(art.OUT, name), pal)
        assert len(px) == art.CANVAS and len(px[0]) == art.CANVAS, name
        words = []
        for c in range(art.CANVAS // 16):
            for r in range(art.CANVAS // 16):
                block = [row[16 * c:16 * c + 16] for row in px[16 * r:16 * r + 16]]
                words.append(rom.add_sprite_tile(block if any(any(x) for x in block) else blank,
                                                 why="swinging bar", share=True))
        lists[key] = b"\x04\x00" + b"".join(w.to_bytes(2, "big") for w in words)

    # The list for each animation, frame and quarter
    tables = {}
    for idx in art.ANIMS:
        frames = art.anim(rom, idx)
        seq = []
        for dur, flags, boxes, pieces in frames:
            assert dur == 4 * QUARTER and len(pieces) == 1, "animation 0x%X: a frame not as expected" % idx
            seq.append(art.PIECES.index(pieces[0][0] | 0x8000))
        rows = []
        for k, i in enumerate(seq):
            j = seq[(k + 1) % len(seq)]
            for q in range(4):
                rows.append(art.inbetween(i, j, q))
        tables[idx] = rows
    keys = sorted(lists)
    label = lambda key: "list_%d_%d" % key

    prev_loop = rom.u32(0x2C46)                 # patch 100's hooks: builder_boxes
    prev_list = rom.u32(0x2D0E)                 # and piece_list
    assert rom.data[0x2C44:0x2C46] == b"\x4E\xB9" and rom.data[0x2D0C:0x2D0E] == b"\x4E\xB9"
    code = f"""
    bra.w piece                 | +0 the builder's piece loop (0x2C44): a3 = the frame's next piece, a2 = the object
    bra.w handout               | +4 a piece entry (a1) -> its list (0x2D0C)

piece:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    clr.l 0x{LIST:X}                    | drop any list left by a piece that wasn't drawn (off screen)
    cmpi.w #0x{art.BANK:X},4(%a2)
    bne.s 9f
    lea tab_{art.ANIMS[0]:X}(%pc),%a1
    cmpi.w #0x{art.ANIMS[0]:X},6(%a2)
    beq.s 1f
    lea tab_{art.ANIMS[1]:X}(%pc),%a1
    cmpi.w #0x{art.ANIMS[1]:X},6(%a2)
    bne.s 9f
1:  move.l %d0,-(%sp)
    move.w 8(%a2),%d0                   | the frame number x 4
    andi.w #0x7FFC,%d0
    lsl.w #2,%d0                        | x 16: 4 lists per frame
    adda.w %d0,%a1
    move.b 10(%a2),%d0                  | the countdown, to see how far into the drawing we are
    ext.w %d0
    neg.w %d0
    addi.w #{4 * QUARTER},%d0           | ticks gone
    bpl.s 2f
    moveq #0,%d0
2:  ext.l %d0
    divu.w #{QUARTER},%d0
    cmpi.w #3,%d0
    bls.s 3f
    moveq #3,%d0
3:  lsl.w #2,%d0
    move.l (%a1,%d0.w),0x{LIST:X}
    move.l (%sp)+,%d0
    lea record(%pc),%a3                 | swap the frame's only piece for ours
9:  jmp 0x{prev_loop:X}

handout:
    tst.l 0x{LIST:X}
    beq.s 9f
    cmpa.l #0x{SIZE_ENTRY:X},%a1
    bne.s 9f
    movea.l 0x{LIST:X},%a1
    clr.l 0x{LIST:X}
    rts
9:  jmp 0x{prev_list:X}

record: .word 0x{0x8000 | (SIZE_ENTRY - 0x5100C) | (2 if art.ORIGIN[0] < 0 else 0) | (1 if -art.ORIGIN[1] < 0 else 0):04X}
    .byte {art.ORIGIN[0] & 0xFF}, {(-art.ORIGIN[1]) & 0xFF}    | the builder takes these bytes' signs from bits 1 / 0 above
{chr(10).join("tab_%X:%s" % (idx, "".join(chr(10) + "    .long " + label(k) for k in rows)) for idx, rows in tables.items())}
{chr(10).join("%s: .byte %s%s    .even" % (label(k), ", ".join("0x%02X" % b for b in lists[k]), chr(10)) for k in keys)}
"""
    base = rom.place_code(code, why="AES: the swinging bars, smooth")
    rom.write(0x2C44, jsr(base), expect=jsr(prev_loop), why="sprite builder: the swinging bars' in-betweens")
    rom.write(0x2D0C, jsr(base + 4), expect=jsr(prev_list), why="sprite builder: the in-betweens' lists")
