NAME = "voice-duck"
DESCRIPTION = "Home console (AES): the music dips while a narration voice plays, so the voices can be heard"

# The game's sound driver (the Z80 in 236-m1) plays the voices (ADPCM-A effects) on top of the music at full volume
# - nothing lowers the music for them (docs/code_map.md "Sound driver"). This patch:
#   * The driver: two new one-byte commands, 0x0B = duck on and 0x0C = duck off (both unused: kind 0 in the
#     command table 0x42EC), and while ducking, quieter music where the driver hands volumes to the YM2610 - the FM
#     operators' total level (0x2BAD: every carrier volume goes through it), the music's ADPCM-A channel volumes
#     (0x2BC7: the drums; voices and effects set theirs elsewhere, 0x0314) and the ADPCM-B volume (register 0x1B,
#     through 0x2B18). With ducking off, every value goes out as before - the arcade game sends neither command, so
#     its sound is unchanged.
#   * The game (AES only): a voice asked for (0x243C with an effect number in the voice tables) raises a request
#     and keeps it for the voice's length (+ DUCK_TAIL); the vblank's sound sender (0x1364) then sends 0x0B, and
#     0x0C when the time is up, as single bytes - between commands, never inside a two-byte one (the same way the
#     game sends its own 0x7F there).
# New code in the driver: 0x2D54-0x2DFF, zeros never read (just past the full 256-entry table at 0x2C54; read-tap
# census over every song, effect and voice, 2026-11-12). Its RAM: 0xFE00 (in an unused run, cleared at reset).

from patchlib import jmp

# ---- knobs (to tune by ear before release) ------------------------------------------------------------------------
DUCK_FM = 8          # FM music: total-level steps added while ducking (0.75 dB each: 8 = 6 dB quieter)
DUCK_DRUMS = 8       # ADPCM-A music channels: volume steps taken off (0-31 scale, 0.75 dB each)
DUCK_ADPCMB_SHIFT = 1  # ADPCM-B music: volume halved this many times (1 = 6 dB quieter)
DUCK_TAIL = 12       # frames the dip lasts after a voice's measured end (60 = a second)

# Each voice's length in seconds (effect number 0-based: list 0x24D4), measured from recordings (2026-11-12).
VOICE_SECONDS = {35: 1.25, 36: 2.25, 37: 1.5, 38: 1.75, 41: 2.35, 42: 2.5, 43: 2.75, 44: 0.8, 46: 1.8, 47: 1.9,
                 48: 1.85, 49: 2.1, 50: 1.95, 52: 2.3, 53: 2.6, 54: 2.05, 55: 2.1, 56: 2.1, 57: 2.5, 58: 1.9,
                 60: 2.15, 61: 2.4, 62: 1.95, 63: 2.1, 64: 2.3, 66: 2.4, 68: 3.4, 69: 3.4, 70: 4.0, 71: 4.8,
                 72: 1.25, 73: 2.25, 74: 1.5, 75: 1.75, 78: 2.35, 79: 2.8, 80: 3.3, 81: 0.8, 83: 3.0, 84: 2.45,
                 85: 2.9, 86: 2.45, 87: 2.45, 89: 3.4, 90: 3.0, 91: 3.65, 92: 2.1, 93: 2.8, 94: 2.8, 95: 2.9,
                 97: 2.5, 98: 1.7, 99: 3.15, 100: 2.45, 101: 2.55, 103: 3.35, 105: 3.4, 106: 3.4, 107: 4.0, 108: 4.8}
VOICE_JP, VOICE_EN, VOICE_EVENTS, SFX_TABLE = 0x211A4, 0x211EE, 37, 0x24D4

Z80_FREE = 0x2D60     # (0x2D54-0x2DFF free)
Z80_DUCK = 0xFE00
SYSTEM_MODE = 0x10FD82
DUCK_S, DUCK_T = 0x10EE00, 0x10EE02     # 68k: 0 idle / 1 duck-on to send / 2 on; frames left
SOUND_SPECIAL = 0x10E31A               # the game's own single-byte send (0x7F) waiting (a5 + 0x631A)

import os, re, subprocess, tempfile


def z80_assemble(source, org):
    """Assemble Z80 source at the absolute address org with ngdevkit's sdasz80; -> (bytes, {label: address})."""
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "a.s")
        with open(src, "w") as f:
            f.write("\t.area CODE (ABS)\n\t.org 0x%X\n" % org + source)
        subprocess.run(["z80-neogeo-ihx-sdasz80", "-o", os.path.join(d, "a.rel"), src], check=True)
        subprocess.run(["z80-neogeo-ihx-sdldz80", "-m", "-i", os.path.join(d, "a.ihx"), os.path.join(d, "a.rel")],
                       check=True, stdout=subprocess.DEVNULL)
        data = {}
        for line in open(os.path.join(d, "a.ihx")):
            n, addr, kind = int(line[1:3], 16), int(line[3:7], 16), int(line[7:9], 16)
            if kind == 0:
                for i in range(n):
                    data[addr + i] = int(line[9 + 2 * i:11 + 2 * i], 16)
        labels = {}
        for line in open(os.path.join(d, "a.map")):     # "  00002D60  duck_on   |    00002D63  duck_off"
            for m in re.finditer(r"\b([0-9A-F]{8})\s+([A-Za-z_]\w*)", line):
                labels[m.group(2)] = int(m.group(1), 16)
    lo, hi = min(data), max(data)
    assert lo == org
    return bytes(data.get(a, 0) for a in range(lo, hi + 1)), labels


def apply(rom):
    # ---- the driver ----
    z80 = f"""
duck_on::
	ld a,#1
	ld (0x{Z80_DUCK:X}),a
	ret
duck_off::
	xor a
	ld (0x{Z80_DUCK:X}),a
	ret
fm_out::                ; FM total level: port c, value b (0 loud - 0x7F silent); AF kept (the caller's)
	push af
	ld a,(0x{Z80_DUCK:X})
	or a
	jr z,1$
	ld a,b
	add a,#{DUCK_FM}
	cp #0x80
	jr c,2$
	ld a,#0x7F
2$:	out (c),a
	pop af
	rst 0x10
	ret
1$:	out (c),b
	pop af
	rst 0x10
	ret
drum_vol::              ; ADPCM-A music channel: e = b (pan bits 6-7, volume 0-4), kept in (ix+8) as before
	ld e,b
	ld 8(ix),e
	ld a,(0x{Z80_DUCK:X})
	or a
	ret z
	ld a,b
	and #0x1F
	sub #{DUCK_DRUMS}
	jr nc,3$
	xor a
3$:	ld e,a
	ld a,b
	and #0xE0
	or e
	ld e,a
	ret
b_vol::                 ; port A register d gets e: ADPCM-B's volume (0x1B) quieter while ducking
	ld a,(0x{Z80_DUCK:X})
	or a
	jr z,4$
	ld a,d
	cp #0x1B
	jr nz,4$
	ld a,e
{chr(10).join(chr(9) + "srl a" for _ in range(DUCK_ADPCMB_SHIFT))}
	out (5),a
	ret
4$:	ld a,e
	out (5),a
	ret
"""
    code, lab = z80_assemble(z80, Z80_FREE)
    assert Z80_FREE + len(code) <= 0x2E00, "driver code past its free space"
    rom.write_sound(Z80_FREE, code, expect=bytes(len(code)), why="voice duck: driver code (free zeros)")
    le = lambda a: a.to_bytes(2, "little")
    rom.write_sound(0x42EC + 0x0B, b"\x01\x01", expect=b"\x00\x00", why="commands 0x0B / 0x0C: on")
    rom.write_sound(0x0C9B, b"\xC3" + le(lab["duck_on"]), expect=bytes.fromhex("C38B0F"), why="command 0x0B = duck on")
    rom.write_sound(0x0C9E, b"\xC3" + le(lab["duck_off"]), expect=bytes.fromhex("C3970F"), why="command 0x0C = duck off")
    rom.write_sound(0x2BB6, b"\xC3" + le(lab["fm_out"]) + b"\x00", expect=bytes.fromhex("ED41D7C9"),
                    why="FM total level out -> ducked")
    rom.write_sound(0x2BD8, b"\xCD" + le(lab["drum_vol"]) + b"\x00", expect=bytes.fromhex("58DD7308"),
                    why="ADPCM-A music volume -> ducked")
    rom.write_sound(0x2B1D, b"\xCD" + le(lab["b_vol"]), expect=bytes.fromhex("7BD305"),
                    why="port A write -> ADPCM-B volume ducked")

    # ---- the game ----
    code_of = lambda n: rom.u16(SFX_TABLE + 2 * n)
    voice_codes = {code_of(n) for t in (VOICE_JP, VOICE_EN) for e in range(VOICE_EVENTS)
                   for n in [rom.u16(t + 2 * e)] if n != 0xFFFF}
    lengths = []
    for n in range(129):
        secs = VOICE_SECONDS.get(n, 0) if code_of(n) in voice_codes else 0
        frames = int(secs * 60) + DUCK_TAIL if secs else 0
        lengths.append(min(255, (frames + 1) // 2))         # in 2-frame units
    code68 = f"""
    bra.w snd_hook              | +0 0x243C's start
    bra.w send_hook             | +4 0x1364's start

| ---- a sound asked for (0x243C, d0): a voice raises the duck request for its length
snd_hook:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    cmpi.w #128,%d0                     | (unsigned: also skips 0x8000+ - the music list)
    bhi.s 9f
    movem.l %d1/%a0,-(%sp)
    lea duck_len(%pc),%a0
    moveq #0,%d1
    move.b (%a0,%d0.w),%d1
    beq.s 8f
    add.w %d1,%d1                       | frames
    cmp.w 0x{DUCK_T:X},%d1
    bls.s 7f
    move.w %d1,0x{DUCK_T:X}
7:  tst.b 0x{DUCK_S:X}
    bne.s 8f
    move.b #1,0x{DUCK_S:X}
8:  movem.l (%sp)+,%d1/%a0
9:  movem.l %d1-%d2/%a0-%a1,-(%sp)      | (the instructions this jump replaced)
    add.w %d0,%d0
    jmp 0x2442

| ---- the vblank's sound sender (0x1364, a5 = 0x108000): a duck command goes first, as a byte of its own
send_hook:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    tst.w 0x{SOUND_SPECIAL:X}           | the game's own byte waiting: it goes first
    bne.s 9f
    cmpi.b #1,0x{DUCK_S:X}
    bne.s 2f
    move.b #0x0B,0x320000               | duck on
    move.b #2,0x{DUCK_S:X}
    rts
2:  cmpi.b #2,0x{DUCK_S:X}
    bne.s 9f
    tst.w 0x{DUCK_T:X}
    beq.s 3f
    subq.w #1,0x{DUCK_T:X}
    bne.s 9f
3:  move.b #0x0C,0x320000               | duck off
    clr.b 0x{DUCK_S:X}
    rts
9:  tst.w 0x{SOUND_SPECIAL:X}           | (the instructions this jump replaced)
    bne.s 1f
    jmp 0x137A
1:  jmp 0x136C

duck_len: .byte {", ".join(str(x) for x in lengths)}
    .even
"""
    base = rom.place_code(code68, why="AES: the music dips under voices")
    rom.write(0x243C, jmp(base), expect=bytes.fromhex("48E760C0D040"), why="sound request -> a voice ducks the music")
    rom.write(0x1364, jmp(base + 4) + bytes.fromhex("4E71"), expect=bytes.fromhex("4A6D631A67000010"),
              why="vblank sound sender -> duck on / off bytes")
