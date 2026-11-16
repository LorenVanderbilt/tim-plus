NAME = "aes-joystick"
DESCRIPTION = "Home console (AES): the joystick steers the Zap-Rod (a virtual trackball); A / B are the cabinet's buttons"

# How the arcade game gets its trackball (docs/code_map.md): the game never reads the trackball itself. The
# cabinet's own BIOS (236-bios, 0xC1B1F6 on, called from SYSTEM_IO) reads the two 8-bit trackball counters
# (0x300000, X or Y picked by bit 0 of 0x380001) and the buttons (0x340000 bits 4-7: P1 button 1/2, P2 button 1/2)
# every frame and fills the game's input area:
#   0x10FE02 X record: previous counter, counter, movement this frame (signed: + = right)  <- the game reads 0x10FE04
#   0x10FE08 Y record: the same (+ = down)                                                 <- the game reads 0x10FE0A
#   0x10FE0E button record (BIOS style: status, previous, now, new presses, repeat, timer) <- 0x10FE10 / 0x10FE11
#   0x10FE14 a second one (P2's buttons in bits 4-5)
# On the home console the normal BIOS knows nothing of it: those bytes stay 0 and the Zap-Rod never moves.
# (The game ROM holds a copy of the cabinet BIOS's routine at 0x5BA / 0x5D8 that nothing calls - its helpers are
# used here: 0x6D0 counter -> movement, 0x722 / 0x77E movement -> direction bits, 0x688 a button record.)
#
# Fix: the vblank's SYSTEM_IO call (0x1292) goes through new code that, on the AES only, fills the input area from
# the joystick after the BIOS has read the pads - a "virtual trackball": each direction held turns a counter at the
# speed below, so the game sees exactly what a trackball rolled that way would give it. The BIOS's own copies
# (0x10FD94 / 0x10FEE8 on the cabinet) are left alone: on the AES those are the console BIOS's (0x10FD96 = the real
# pad, which the menus read just as well). Arcade (MVS): untouched (the cabinet BIOS's routine runs as before).
# RAM: 0x10FE00 (the speed now), 0x10FE06 / 0x10FE0C (the X / Y counters, 1/256 steps) - gaps between the records,
# written only by the BIOS's power-on clear (a tap over attract + a game, 2026-11-06).

from patchlib import jsr

# ---- knobs (speeds in trackball steps per frame; 1 step = 1 pixel for most of the game's pointers) ----------------
START_SPEED = 1.0       # speed the moment a direction is pressed (a tap moves just a little)
TOP_SPEED = 3.0         # speed after holding a direction ACCEL_FRAMES frames
ACCEL_FRAMES = 30       # frames (60 a second) to go from START_SPEED to TOP_SPEED; 0 = always TOP_SPEED
# Live tuning without rebuilding: tools/probes/joy_speed.lua (finds the table below by its "JOYS" tag).

VBLANK_SYSTEM_IO = 0x1292       # jsr 0xC0044A (BIOS SYSTEM_IO) in the vblank handler
SYSTEM_IO = 0xC0044A
SYSTEM_MODE = 0x10FD82          # BIOS: nonzero = arcade (MVS)
P1_NOW, P2_NOW = 0x10FD96, 0x10FD9C     # BIOS: pads now (active high: up down left right A B C D = bits 0-7)
SPEED_NOW, X_COUNT, Y_COUNT = 0x10FE00, 0x10FE06, 0x10FE0C
X_REC, Y_REC, BTN_REC, BTN2_REC = 0x10FE02, 0x10FE08, 0x10FE0E, 0x10FE14
COUNTER_STEP, X_DIRS, Y_DIRS, BUTTON_REC = 0x6D0, 0x722, 0x77E, 0x688   # the game ROM's copy of the BIOS helpers


def apply(rom):
    start = int(START_SPEED * 256)
    top = int(TOP_SPEED * 256)
    accel = 0 if ACCEL_FRAMES <= 0 else max(1, (top - start) // ACCEL_FRAMES)
    if ACCEL_FRAMES <= 0:
        start = top
    assert 0 < start <= top < 64 * 256
    helpers = {COUNTER_STEP: "122800011081114000019001114000024E75",
               X_DIRS: "1228000310280001020000F0", Y_DIRS: "1228000310280001020000F0",
               BUTTON_REC: "42280003422800041228000211410001"}
    for addr, hexs in helpers.items():
        assert rom.data[addr:addr + len(hexs) // 2] == bytes.fromhex(hexs), "helper not as expected at 0x%X" % addr
    code = f"""
    jsr 0x{SYSTEM_IO:X}
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f                            | arcade: the cabinet BIOS did it all
    move.b 0x{P1_NOW:X},%d2             | P1 pad now
    lea 8f(%pc),%a1                     | the knobs: start, accel, top
    move.w 0x{SPEED_NOW:X},%d3          | this frame's speed
    move.b %d2,%d0
    andi.b #0x0F,%d0
    bne.s 1f
    move.w (%a1),0x{SPEED_NOW:X}        | no direction held: back to the start speed
    bra.s 2f
1:  cmp.w (%a1),%d3                     | (from power-on / a save: at least the start speed)
    bcc.s 3f
    move.w (%a1),%d3
3:  move.w %d3,%d0
    add.w 2(%a1),%d0
    cmp.w 4(%a1),%d0
    bls.s 4f
    move.w 4(%a1),%d0
4:  move.w %d0,0x{SPEED_NOW:X}
2:
    moveq #0,%d0                        | X: right +, left -
    btst #3,%d2
    beq.s 5f
    add.w %d3,%d0
5:  btst #2,%d2
    beq.s 6f
    sub.w %d3,%d0
6:  add.w %d0,0x{X_COUNT:X}
    move.b 0x{X_COUNT:X},%d0            | whole steps
    lea 0x{X_REC:X},%a0
    jsr 0x{COUNTER_STEP:X}
    moveq #0,%d0                        | Y: down +, up -
    btst #1,%d2
    beq.s 5f
    add.w %d3,%d0
5:  btst #0,%d2
    beq.s 6f
    sub.w %d3,%d0
6:  add.w %d0,0x{Y_COUNT:X}
    move.b 0x{Y_COUNT:X},%d0
    lea 0x{Y_REC:X},%a0
    jsr 0x{COUNTER_STEP:X}
    moveq #0,%d6                        | the button records, as the cabinet BIOS builds them
    moveq #0,%d7
    lea 0x{X_REC:X},%a0
    jsr 0x{X_DIRS:X}
    lea 0x{Y_REC:X},%a0
    jsr 0x{Y_DIRS:X}
    move.b %d2,%d0                      | P1 A / B = the cabinet's P1 buttons 1 / 2
    andi.b #0x30,%d0
    or.b %d0,%d7
    move.b 0x{P2_NOW:X},%d0             | P2 A / B = its P2 buttons 1 / 2
    andi.b #0x30,%d0
    lsl.b #2,%d0
    or.b %d0,%d7
    move.b %d7,%d0
    lea 0x{BTN_REC:X},%a0
    jsr 0x{BUTTON_REC:X}
    andi.b #0xF0,3(%a0)
    or.b %d6,3(%a0)
    move.b %d7,%d0
    lsr.b #2,%d0
    lea 0x{BTN2_REC:X},%a0
    jsr 0x{BUTTON_REC:X}
    lsr.b #2,%d6
    andi.b #0xF0,3(%a0)
    or.b %d6,3(%a0)
    move.b #0xFF,0x{BTN_REC:X}
9:  rts
    .ascii "JOYS"                       | tag for tools/probes/joy_speed.lua
8:  .word {start}, {accel}, {top}
"""
    new = rom.place_code(code, why="AES: joystick -> virtual trackball (after SYSTEM_IO in the vblank)")
    rom.write(VBLANK_SYSTEM_IO, jsr(new),
              expect=bytes.fromhex("4EB900C0044A"), why="vblank SYSTEM_IO -> + the AES joystick")
