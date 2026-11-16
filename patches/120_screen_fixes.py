NAME = "screen-fixes"
DESCRIPTION = ("Home console (AES): no colour streaks at the attract's start (palette writes kept in the vblank); "
               "the title's copyright line one row lower")

# 1. Colour streaks: on the BackBit, two thin static lines showed mid-screen for a second right before the intro.
#    Palette writes during the picture show on real hardware (../neogeo-notes/findings.md),
#    not in MAME. At every attract start the start-up 0x3308 runs with interrupts off for about a frame and a half:
#    * its palette bank 0 fill (0x3350 -> 0x17EB8, patch 080's palbank_init) ran at lines 91-128 - now it waits for
#      the vblank (the LSPC line counter, 0x3C0006 >> 7 = 0x100 + the screen line; the picture is lines 16-239,
#      0x110-0x1EF) and fills faster (movem, 12 longs at a time), bank switches included, inside it;
#    * the vblank it held off then ran at line ~163 and its palette upload (0x1FE8: the queue at 0x10AAEA) wrote 68
#      colours there - now the upload waits (the queue stays) when it is called inside the picture.
# 2. The copyright line (SNK CORP. OF AMERICA ... 1997, fix script 190 at 0x2DA04, row 25) one row lower: on the
#    console the fix-script queue (0x1F14, patch 020's fix_queue) gets a copy of the script starting at row 26 (the
#    arcade's script is untouched).

from patchlib import jsr, jmp

SYSTEM_MODE = 0x10FD82
LINE_REG = 0x3C0006
PIC_FIRST, PIC_END = 0x110, 0x1F0                 # line counter: the picture
FILL = 0x17EB8                                    # the start-up's bank 0 fill (original)
FILL_TABLE, FILL_SRC = 0x17F14, 0x4800C           # its 16 palettes: offsets into the source
UPLOAD = 0x1FE8                                   # the vblank's palette upload
COPYRIGHT = 0x2DA04                               # fix script 190
ROWS_DOWN = 1


def apply(rom):
    # the fill as the original has it (checked, so the copy below does the same)
    assert rom.data[FILL:FILL + 0x5C] == bytes.fromhex(
        "13FC0001003A001F41F90040000043FA004C45F90004800C720F301947F2000020DB20DB20DB20DB20DB20DB20DB20DB51C9FFE8"
        "203C7DDD7DDD323C00EF20C020C020C020C020C020C020C020C051C9FFEE13FC0001003A000F4E75")
    assert rom.data[UPLOAD:UPLOAD + 8] == bytes.fromhex("4A6D007A6600003E")
    assert rom.data[0x3350:0x3352] == b"\x4E\xB9" and rom.data[0x1F14:0x1F16] == b"\x4E\xB9"
    palbank_prev = rom.u32(0x3352)                # patch 080's palbank_init
    queue_prev = rom.u32(0x1F16)                  # patch 020's fix_queue
    end = rom.data.index(b"\x00", COPYRIGHT + 2)  # the script: an address word, runs, a 0 byte
    script = rom.data[COPYRIGHT:end + 1]
    assert script[:2] == b"\x70\x99"
    moved = (int.from_bytes(script[:2], "big") + ROWS_DOWN).to_bytes(2, "big") + script[2:]

    code = f"""
    bra.w fill                  | +0 the start-up's bank 0 fill (0x3350)
    bra.w upload                | +4 the vblank's palette upload (0x1FE8)
    bra.w queue                 | +8 a fix script queued (0x1F14)

fill:
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    movem.l %d0-%d7/%a0-%a6,-(%sp)
1:  move.w 0x{LINE_REG:X},%d0           | into the picture...
    lsr.w #7,%d0
    cmpi.w #0x{PIC_FIRST:X},%d0
    bcs.s 1b
    cmpi.w #0x{PIC_END:X},%d0
    bcc.s 1b
2:  move.w 0x{LINE_REG:X},%d0           | ...and out of it: the vblank's start
    lsr.w #7,%d0
    cmpi.w #0x{PIC_END:X},%d0
    bcs.s 2b
    move.b #1,0x3A001F                  | bank 0
    lea 0x400000,%a0
    lea 0x{FILL_TABLE:X},%a1
    lea 0x{FILL_SRC:X},%a2
    moveq #15,%d1
3:  move.w (%a1)+,%d0
    lea (%a2,%d0.w),%a3
    move.l (%a3)+,(%a0)+
    move.l (%a3)+,(%a0)+
    move.l (%a3)+,(%a0)+
    move.l (%a3)+,(%a0)+
    move.l (%a3)+,(%a0)+
    move.l (%a3)+,(%a0)+
    move.l (%a3)+,(%a0)+
    move.l (%a3)+,(%a0)+
    dbf %d1,3b
    move.l #0x7DDD7DDD,%d1              | the other 240 palettes: grey, 48 bytes a write
    move.l %d1,%d2
    move.l %d1,%d3
    move.l %d1,%d4
    move.l %d1,%d5
    move.l %d1,%d6
    move.l %d1,%d7
    movea.l %d1,%a1
    movea.l %d1,%a2
    movea.l %d1,%a3
    movea.l %d1,%a4
    movea.l %d1,%a5
    move.w #159,%d0
4:  movem.l %d1-%d7/%a1-%a5,(%a0)
    lea 48(%a0),%a0
    dbf %d0,4b
    move.b #1,0x3A000F                  | bank 1 again
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts
9:  jmp 0x{palbank_prev:X}

upload:                                 | (replaces "tst.w 0x7A(a5); bne.w 0x202C"; d7 is free here)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    move.w 0x{LINE_REG:X},%d7
    lsr.w #7,%d7
    cmpi.w #0x{PIC_FIRST:X},%d7
    bcs.s 1f
    cmpi.w #0x{PIC_END:X},%d7
    bcs.s 2f                            | inside the picture: not now (the queue waits for the next vblank)
1:  tst.w 0x7A(%a5)
    bne.s 2f
    jmp 0x{UPLOAD + 8:X}
2:  rts

queue:                                  | a6 = the script
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    cmpa.l #0x{COPYRIGHT:X},%a6
    bne.s 9f
    lea copyright(%pc),%a6
9:  jmp 0x{queue_prev:X}

copyright: .byte {", ".join("0x%02X" % b for b in moved)}
    .even
"""
    base = rom.place_code(code, why="AES: screen fixes")
    rom.write(0x3350, jsr(base), expect=jsr(palbank_prev), why="start-up bank 0 fill: in the vblank")
    rom.write(UPLOAD, jmp(base + 4), expect=bytes.fromhex("4A6D007A6600"),
              why="palette upload: never inside the picture")
    rom.write(0x1F16, (base + 8).to_bytes(4, "big"), expect=queue_prev.to_bytes(4, "big"),
              why="fix scripts: the copyright line a row lower")
