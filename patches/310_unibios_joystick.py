NAME = "unibios-joystick"
DESCRIPTION = ("UniBIOS: the joystick steers as on the other BIOSes (UniBIOS's own trackball reader no longer upsets "
               "patch 010's)")

# UniBIOS (every version from 2.3 to 4.0 at least) carries a copy of the trackball cabinet's reader and runs it in
# SYSTEM_IO every frame, on the console too: it reads the player 1 port (0x300000) as if it held trackball counters
# and writes the game's input records (0x10FE02 - 0x10FE19). Patch 010 calls SYSTEM_IO and then writes those records
# from the joystick - but it takes the previous counter from the record, which UniBIOS has just overwritten with the
# joystick port's bits. So once 010's counter had moved (any push of the stick, in the menus too), every frame
# after showed that whole distance again: the Zap-Rod ran off down-right on its own (the user's Analogue Pocket,
# 2026-11-16), and holding a direction made it jump about.
#
# Fix: around that SYSTEM_IO call, the records are kept from before it and put back after - so 010 finds its own
# last values, as on the other BIOSes (which never touch them). Only where 010 runs (PLUS_OFF 0): on the trackball
# cabinet its BIOS's reader is the real one.

SYSTEM_IO = 0xC0044A
PLUS_OFF = 0x10EC63                     # patch 280's switch: 0 = the Plus (and patch 010's joystick) on
RECORDS = 0x10FE02                      # 010's X / Y / button records: 24 bytes (6 longs) to 0x10FE19

from patchlib import jsr, find_once


def apply(rom):
    # Patch 010's code starts "jsr SYSTEM_IO; tst.b PLUS_OFF" (280 re-pointed its check)
    site = find_once(rom, jsr(SYSTEM_IO) + bytes.fromhex("4A39") + PLUS_OFF.to_bytes(4, "big"),
                     "patch 010's SYSTEM_IO call")
    code = f"""
    tst.b 0x{PLUS_OFF:X}
    beq.s 1f
    jmp 0x{SYSTEM_IO:X}                 | the cabinet: as before
1:  movem.l 0x{RECORDS:X},%d0-%d5       | the records as 010 left them
    movem.l %d0-%d5,-(%sp)
    jsr 0x{SYSTEM_IO:X}
    movem.l (%sp)+,%d0-%d5
    movem.l %d0-%d5,0x{RECORDS:X}       | put back (UniBIOS rewrites them)
    rts
"""
    base = rom.place_code(code, why="UniBIOS: patch 010's input records kept through SYSTEM_IO")
    rom.write(site, jsr(base), expect=jsr(SYSTEM_IO), why="patch 010: SYSTEM_IO with its records kept")
