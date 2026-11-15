NAME = "intro"
DESCRIPTION = "Home console (AES): at power-on, the ending's brain-in-a-jar figure scrolls up, then the title's flash"

# The user's idea (2026-11-14, mock-up intro_mock3): after the eye catcher, at power-on only, the figure from the
# end of the ending (a brain in a jar, scrolling up - seen only after beating Professional) plays, with the
# title's PRESS START BUTTON blinking over it; at the top of its scroll the title's white flash takes over and the
# title comes up. Start during it goes to the title menu, as Start does in the attract anyway (patch 020).
#
# How: the ending is a cutscene (course step 60) whose states run from 0x1635E (state 0x10805A): 80 picks the
# sprites (176-195), 84 writes the figure's tiles (table 0x2CD06) and palettes, 88 places them, 92 scrolls the
# figure up (fading in, random zaps with sounds 110 / 114) until the top, then 96 on scrolls down with GAME OVER.
# Here the attract's scene player (0xE34E, patch 020's hook) runs states 80-92 instead at power-on; at state 96
# it hands over to the logo scene's flash (scene 276: the backdrop fades to white, 284 wipes to the title); once
# the screen is white the figure's sprites are hidden and the logo made as scenes 264-272 make it (palettes, the
# logo's objects 0x14D36, its fade-in's end), so the wipe reveals it as usual. PRESS START BUTTON is the title's own message (0x10804A =
# 2, drawn by the vblank; 1 = blank, 8 frames in 32 as the title blinks it) in the title's palette 6 (written at
# the start of each vblank: the ending's palettes differ). Music: the sound test's MUSIC 01 under it and on through the
# title (the demo after it, or a game, stops it with its own music).

SYSTEM_MODE = 0x10FD82
SCENE_STEP, MESSAGE, MESSAGE_PAL, FRAMES = 0x108052, 0x10804A, 0x10804C, 0x10A882
END_STATE = 0x10805A
END_FLAG = 0x108058                    # 0x108058 / 0x10805A: the ending's on, its state - both 0 after
GO_TITLE = 0x10EF00                    # patch 020's: set at power-on / after a game
MUSIC_SENT = 0x10EEFB                  # (spare RAM) the power-on music sent
INTRO = 0x10EEFA                       # (spare RAM) 0 not yet (power-on) / 1 playing / 2 handing over / 3 done
FIGURE_SPRITES = (176, 20)             # the ending's figure: sprites 176-195
SOUND = 0x243C
MUSIC = 0x800C                         # the sound test's MUSIC 01 (the user's pick, 2026-11-14): the intro + title,
                                       # from the attract's start (17 frames before the intro: the user's pick)
TITLE_PAL6 = [0x0000, 0x7FFF, 0x5FE1, 0x4FD1, 0x6FB1, 0x5FA0, 0x5F90, 0x6F70, 0x1557, 0x7779, 0x1AAB, 0x7CCD,
              0x1EEE, 0x000D, 0x0000, 0x7FFF]    # the title's fix palette 6 (PRESS START BUTTON), read 2026-11-14


def apply(rom):
    scene_next = int.from_bytes(rom.data[0xE350:0xE354], "big")       # patch 020's scene hook (or later's)
    vbl_next = int.from_bytes(rom.data[0x1294:0x1298], "big")
    assert rom.data[0xE34E:0xE350] == b"\x4E\xB9" and rom.data[0x1292:0x1294] == b"\x4E\xB9"
    first, count = FIGURE_SPRITES
    code = f"""
    bra.w intro_scene           | +0 the attract's scene player, each frame
    bra.w intro_vbl             | +4 the vblank's first call
    bra.w backdrop_init         | +8 the start-up's backdrop (0x1566)
    bra.w palbank_init          | +12 the start-up's palette bank 0 fill (0x3350)
    bra.w attract_off           | +16 the attract's sound off (0xE258): then the music

intro_scene:
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    move.b 0x{INTRO:X},%d0
    beq.w 1f
    cmpi.b #1,%d0
    beq.w 2f
    cmpi.b #2,%d0
    bne.w 9f
    cmpi.w #284,0x{SCENE_STEP:X}        | handing over: once the flash is white, the figure goes and the logo
    bne.w 9f                            | comes (as the logo scenes 264-272 would have made it), for the wipe
    bsr.w hide_figure
    movem.l %d0-%d7/%a0-%a4/%a6,-(%sp)
    moveq #0,%d0                        | scene 264: the palettes
    jsr 0x25D6
    move.w 0x{SCENE_STEP:X},-(%sp)      | scene 268: the logo's objects (it moves the scene on: put back)
    jsr 0x14D36
    move.w (%sp)+,0x{SCENE_STEP:X}
    moveq #0,%d0                        | scene 272's fade-in, at its end: full colour (not 0x16036 - only
                                        | its pulsing backdrop, which 280 made white: called, a navy band)
    moveq #1,%d1
    jsr 0x160E0
    moveq #0x18,%d0                     | scene 280's palettes again (it came after 264's)
    jsr 0x25D6
    movem.l (%sp)+,%d0-%d7/%a0-%a4/%a6
    move.b #3,0x{INTRO:X}
    bra.w 9f
1:  cmpi.w #4,0x{SCENE_STEP:X}          | power-on, where patch 020 would go to the logo: the intro
    bne.w 9f
    tst.b 0x{GO_TITLE:X}
    beq.w 9f
    clr.b 0x{GO_TITLE:X}
    move.b #1,0x{INTRO:X}
    move.w #80,0x{END_STATE:X}          | the ending's figure states
    tst.b 0x{MUSIC_SENT:X}              | (the music, if the attract's start didn't send it)
    bne.s 2f
    move.b #1,0x{MUSIC_SENT:X}
    move.w #0x{MUSIC:X},%d0
    bsr.w sound
2:  cmpi.w #256,0x{SCENE_STEP:X}        | Start (patch 020: to the logo, the menu): the intro's over
    bne.s 3f
    bsr.w hide_figure
    clr.l 0x{END_FLAG:X}                | the ending's state off (left on, the game's screens draw blank)
    move.b #3,0x{INTRO:X}
    bra.w 9f
3:  jsr 0x1635E                         | a frame of the ending's figure
    cmpi.w #96,0x{END_STATE:X}
    bcs.s 4f
    move.b #2,0x{INTRO:X}               | the top: the title's flash
    clr.l 0x{END_FLAG:X}                | the ending's state off (left on, the game's screens draw blank)
    move.w #276,0x{SCENE_STEP:X}
    clr.w 0x{MESSAGE:X}
    lea 0x3C0000,%a0                    | PRESS START off before the flash: its 18 cells blank (at 0x7176, a
    move.w #32,4(%a0)                   | column apart, as the vblank draws the message)
    move.w #0x7176,(%a0)
    nop
    nop
    moveq #17,%d0
6:  move.w #0x00FF,2(%a0)
    nop
    dbf %d0,6b
    bra.w 9f
4:  moveq #1,%d0                        | PRESS START BUTTON, blinking as the title's (blank 8 frames in 32)
    move.w 0x{FRAMES:X},%d1
    andi.w #0x18,%d1
    beq.s 5f
    moveq #2,%d0
5:  move.w %d0,0x{MESSAGE:X}
    move.w #0xCF00,0x{MESSAGE_PAL:X}
    rts
9:  jmp 0x{scene_next:X}

sound:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr 0x{SOUND:X}
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

hide_figure:
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
    move.w #0x{0x8200 + first:X},(%a0)
    nop
    nop
    moveq #{count - 1},%d0
1:  move.w #0,2(%a0)
    nop
    dbf %d0,1b
    rts

intro_vbl:                              | the start of the vblank: the title's palette 6 while the intro plays
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    cmpi.b #1,0x{INTRO:X}
    bne.s 9f
    lea pal6(%pc),%a0
    lea 0x4000C0,%a1
    moveq #15,%d0
1:  move.w (%a0)+,(%a1)+
    dbf %d0,1b
9:  jmp 0x{vbl_next:X}
backdrop_init:                          | (patch 040's, at 0x1566, fixed: it wrote 0x7777 then 0x8000 on the
    tst.b 0x{SYSTEM_MODE:X}             | console - an interrupt between left a gray band, 37 lines, after
    bne.s 1f                            | the ranking screen; now one write of the right colour)
    move.w #0x8000,0x401FFE
    rts
1:  move.w #0x7777,0x401FFE
    rts
palbank_init:                           | (0x3350's call of 0x17EB8: the start-up fills palette bank 0 with
    tst.b 0x{SYSTEM_MODE:X}             | bank 0 on screen - mid-picture, its old gray backdrop (0x7DDD) showed
    bne.s 1f                            | as a band after the ranking screen; black first, the screen's black)
    move.b #1,0x3A001F
    move.w #0x8000,0x401FFE
    jmp 0x17EC0
1:  jmp 0x17EB8
attract_off:                            | (0xE258: the attract's start sends sound off, 0x8001 / 0x8002) then, at
    jsr 0x{SOUND:X}                     | power-on, the intro's music - as early as it can be, on the black
    tst.b 0x{SYSTEM_MODE:X}             | before the figure
    bne.s 1f
    tst.b 0x{MUSIC_SENT:X}
    bne.s 1f
    move.b #1,0x{MUSIC_SENT:X}
    move.w #0x{MUSIC:X},%d0
    jsr 0x{SOUND:X}
1:  rts
pal6: .word {", ".join("0x%04X" % c for c in TITLE_PAL6)}
"""
    base = rom.place_code(code, why="AES: the power-on intro (the ending's figure)")
    jsr = lambda a: bytes.fromhex("4EB9") + a.to_bytes(4, "big")
    rom.write(0xE34E, jsr(base), expect=jsr(scene_next), why="attract scenes: the power-on intro first")
    rom.write(0x1292, jsr(base + 4), expect=jsr(vbl_next), why="vblank: the intro's PRESS START colours")
    old = rom.data[0x1566:0x156C]
    assert old[:2] == b"\x4E\xB9"                                      # (patch 040's backdrop_init)
    rom.write(0x1566, jsr(base + 8), expect=old, why="start-up backdrop: one write (no gray band)")
    rom.write(0x3350, jsr(base + 12), expect=jsr(0x17EB8), why="start-up palette bank 0: no gray band")
    assert rom.data[0xE254:0xE258] == bytes.fromhex("303C8002")             # (the attract's 0x8002, sent on the console)
    rom.write(0xE258, jsr(base + 16), expect=jsr(SOUND), why="attract start: the power-on music, early")
