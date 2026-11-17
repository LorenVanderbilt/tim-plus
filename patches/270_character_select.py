NAME = "character-select"
DESCRIPTION = ("Home console (AES): the character select - no stray graphics as it opens; picking clears the screen in "
               "one go, and the character stays put and plays their pose instead of sliding in from the right; no "
               "PRACTICE COURSE label on the practice course")

# The character select's pick (0x7784, on a press or when the timer runs out): a sound, the character
# (0x108EBE), FIX_CLEAR, the cursor box (object 0) and the other character deleted, the chosen one's object
# (1 + the pick) gets bit 2 of +11 (its animation held), and 0x10A89A = -1 starts the slide state (0x7678). That
# moves the character from x = 320 to 144, 8 px a frame (0x10A89E), releases the animation between 160 and 144, and
# at 144 holds for 0x10A89C = 180 frames (a press skips it) before the course select (0x7734).
# In the original this shows as a glitch over three frames: the text goes at once (FIX_CLEAR in the main loop) but
# the cursor box's sprite stays a frame longer, then the clock's digits come back for a frame (the clock queued its
# redraw earlier that frame), then the character jumps from the middle to the right edge to slide in.
#
# On the console:
#   * The text is cleared in the pick's own vblank instead of at once, so it goes on the same picture as the box.
#     It runs at the vblank's start (the 0x1292 chain), ahead of the game's own fix work. The clock's request to
#     redraw its digits (made that frame - the original's reappearing digits) is cancelled, and the bottom band
#     (0x7804 asked for it) is asked for again, so the vblank draws the band and BETA 1 on the cleared layer.
#   * The character stays where they stood on the select (the man at x = 136, the lady at 184 - the original's
#     slide ends at 144 for both) and plays their pose at once, for POSE_FRAMES (shorter than the original's
#     slide and hold). A press can't skip the
#     hold during those first frames (in the original the slide ignored presses, and the pick's own press still
#     counts on the next frame).

# Opening the character select (from the instructions), two one-frame strips at the top of the screen, both the
# original's - work that runs on into the picture, so its top lines are drawn before the work gets there:
#   * The set-up (0xD5E0, and the instructions' end, 0xD8B2) clears the sprites with the system ROM's routine
#     (0xC004C8), which takes from line 4 to about 40: the instructions' sprites showed along the top. On the
#     console every sprite's height is zeroed first, in about 4 lines.
#   * 0x17D20 covers the fix layer with a black tile (the screen-change wipe, called from 10 places) column by column
#     from the left; called from the main loop as the picture starts, the right-hand columns' top was drawn
#     uncovered (the wallpaper showed). On the console it fills a row at a time from the top (a row takes about a
#     line, and is 8 lines tall).

# The select's own opening (its state 0, 0x7842: the fix layer black; state 4: rows cleared from the middle out over
# 8 frames; state 8, 0x78F6: the set-up) showed in pieces: MAN / LADY first (the set-up writes them straight to the
# fix layer, 0x1803A a letter, in the main loop), then the characters, the box, the title and the clock's frame
# (objects and queued fix scripts, a frame later), then the clock's digits (requested a frame later still). On the
# console MAN / LADY are held back to the next vblank, which also runs the queued scripts early and asks for the
# clock's digits after them, so all of it shows on one picture. Coming in from the instructions, the screen goes straight to black (the instructions' end and the
# select's set-up clear the fix layer to black, not to see-through - the blue backdrop showed - and do it before
# their slow sprite clears, which ran into the next picture).

# Also on the console: the select's opening leaves the bottom band's rows (28-31) black - its last two steps cleared
# them, and the band (the same black tile, 0x17D50) only came back with the rest, so the wallpaper showed there; now
# the band is there from the start. And the course select's title (script 14, queued every frame at 0x7B22) waits
# until its opening wipe (select states 4: closing, 8: opening) is done, and shows with the cards (patch 020's deck)
# - it showed through the black.

# The practice course's orange PRACTICE COURSE label in the top left (script 120, queued at 0xCFF8 when the course
# is 0) is left off on the console, as patch 250 already did in 2P: its hook there is chained to (the arcade, and
# patch 250's own test, as before).

SLIDE_FRAMES = (320 - 144) // 8 - 1     # the original's frames before the hold began (x 312-152), added to it
HOLD = 180                              # the original's hold after the slide
POSE_FRAMES = 100                       # console: frames the pose shows before the course select (the original's
                                        # slide + hold took 201)

SYSTEM_MODE = 0x10FD82
FIX_CLEAR = 0xC004C2
FIX_QUEUE = 0x1F14
FIX_RUN = 0x1F32                        # the vblank's fix-script runner (empties the queue)
CLEAR_NEXT = 0x10EC2C                   # spare RAM: vblanks until the delayed clear (0 = none waiting)
NO_SKIP = 0x10EC27                      # spare RAM: frames left in which a press doesn't skip the hold
LETTERS_N = 0x10EC62                    # spare RAM: MAN / LADY letters held back (byte)
LETTERS = 0x10EC64                      # spare RAM: their (column, row, character) words, 7 at most
PICK_X = 0x10EC60                       # spare RAM (word): the picked character's x on the select
PRESSED = 0x10A7C4                      # 0x27C4(a5): a button newly pressed this frame (-1)
CLOCK_REDRAW = 0x10A860                 # long: not -1 = the vblank redraws the clock's digits (0x3908), then -1;
                                        # its first word is the seconds shown
CLOCK_SECONDS = 0x10A856                # the clock's seconds
BAND_REQ = 0x10807C                     # 0x7C(a5) = 1: the vblank draws the bottom band's fix tiles once (0x17D50)
PICK = 0x10A898                         # the pick: 0 = the man, 1 = the lady (objects 1 / 2)
CLEAR_SITE = 0x77A8                     # the pick: jsr FIX_CLEAR
HOLD_SITE = 0x7810                      # the pick: move.w #180,0x289C(a5)
SLIDE_SITE = 0x7686                     # each slide state frame: jsr 0x1F14 (a6 = its script)
HOLD_X_SITE = 0x7726                    # each hold frame: move.w #144,12(a0) (a0 = the character)
SPRITE_CLEAR = 0xC004C8                 # the system ROM's: every sprite cleared
LETTER = 0x1803A                        # d0 = column, d1 = row, d2 = character: a tall-font letter on the fix layer
LETTER_SITES = [0x7A1E, 0x7A38]         # the set-up's jsr LETTER: MAN, LADY
OPEN_SITES = [0x78C6, 0x78E0]           # the select's opening: jsr 0x1F14 for its lower rows' scripts (a6)
BAND_ROW = 28                           # the bottom band's first fix row
TITLE_SITE = 0x7B22                     # the course select: jsr 0x1F14 (a6 = its COURSE SELECT script)
SELECT_STATE = 0x10A8A0                 # the course select's state: 12 once its opening wipe is done, 16 input
LABEL_SITE = 0xCFF8                     # patch 250's: jsr <its not_practice>; bne.s (the label when course 0)
BLACK_SITES = [0xD8D2, 0xD5F0]          # jsr FIX_CLEAR: the instructions' end, the character select's set-up
CLEAR_SITES = [0xD5E0, 0xD8B2]          # jsr SPRITE_CLEAR: the character select's set-up, the instructions' end
WIPE = 0x17D20                          # movem.l d0-d1/a0,-(sp); lea 0x3C0002,a0; ... (the fix layer black)

from patchlib import jsr, jmp


def apply(rom):
    assert rom.data[0x1292:0x1294] == b"\x4E\xB9"
    assert rom.data[LABEL_SITE:LABEL_SITE + 2] == b"\x4E\xB9" and rom.data[LABEL_SITE + 6:LABEL_SITE + 8] == b"\x66\x18", \
        "the practice label: patch 250's hook not found"
    label_prev = rom.u32(LABEL_SITE + 2)
    code = f"""
    bra.w pick_clear            | +0 the pick's FIX_CLEAR
    bra.w pick_end              | +4 the pick's last step (the hold's length)
    bra.w slide_frame           | +8 each frame of the slide state
    bra.w hold_x                | +12 each hold frame: the character's x
    bra.w vbl                   | +16 the vblank chain (0x1292): the delayed clear
    bra.w sprites_off           | +20 before the system ROM's sprite clear
    bra.w wipe                  | +24 the fix layer black
    bra.w to_black              | +28 FIX_CLEAR going into the character select
    bra.w black_first           | +32 the sprite clears going into the character select
    bra.w hold_letter           | +36 the set-up's MAN / LADY letters
    bra.w open_row              | +40 the select's opening: a row's script
    bra.w title                 | +44 the course select's title
    bra.w no_label              | +48 the practice course's label

pick_clear:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    move.b #1,0x{CLEAR_NEXT:X}          | console: in this frame's vblank, with the sprites
    rts
1:  jmp 0x{FIX_CLEAR:X}

pick_end:
    move.w #{HOLD},0x289C(%a5)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    move.w #{POSE_FRAMES},0x289C(%a5)   | console: no slide; the pose's own length
    move.w #144,0x289E(%a5)             | already at the slide's end
    move.b #{SLIDE_FRAMES},0x{NO_SKIP:X}
    move.l %d0,-(%sp)
    move.w 0x{PICK:X},%d0
    addq.w #1,%d0
    lsl.w #7,%d0
    movea.l #0x100000,%a0
    adda.w %d0,%a0
    andi.b #0xFB,11(%a0)                | the pose plays at once
    move.w 12(%a0),0x{PICK_X:X}         | and where they stand now
    move.l (%sp)+,%d0
9:  rts

slide_frame:
    tst.b 0x{NO_SKIP:X}
    beq.s 1f
    subq.b #1,0x{NO_SKIP:X}
    clr.w 0x{PRESSED:X}                 | (tested later this frame, at 0x76FE)
1:  jmp 0x{FIX_QUEUE:X}

vbl:
    tst.b 0x{LETTERS_N:X}
    beq.s 5f
    movem.l %d0-%d3/%a0-%a1,-(%sp)      | the set-up's letters, now with everything else
    lea 0x{LETTERS:X},%a1
    moveq #0,%d3
    move.b 0x{LETTERS_N:X},%d3
    subq.w #1,%d3
1:  move.w (%a1)+,%d0
    move.w (%a1)+,%d1
    move.w (%a1)+,%d2
    jsr 0x{LETTER:X}
    dbf %d3,1b
    clr.b 0x{LETTERS_N:X}
    movem.l %d4-%d7/%a2-%a6,-(%sp)      | the queued fix scripts now (the clock's frame), so the digits go on top
    lea 0x108000,%a5
    jsr 0x{FIX_RUN:X}
    movem.l (%sp)+,%d4-%d7/%a2-%a6
    move.w 0x{CLOCK_SECONDS:X},0x{CLOCK_REDRAW:X}   | and the clock's digits this vblank too (the word is what's shown)
    movem.l (%sp)+,%d0-%d3/%a0-%a1
5:  tst.b 0x{CLEAR_NEXT:X}
    beq.s 9f
    subq.b #1,0x{CLEAR_NEXT:X}
    bne.s 9f
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr 0x{FIX_CLEAR:X}
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    move.l #-1,0x{CLOCK_REDRAW:X}       | no clock digits drawn back
    move.w #1,0x{BAND_REQ:X}            | the bottom band again
9:  jmp 0x{rom.u32(0x1294):X}

black_first:
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    jsr 0x{WIPE:X}                      | console: black first (a few lines), it covers the rest of the work

sprites_off:
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    move.l %a0,-(%sp)
    move.w %d0,-(%sp)
    lea 0x3C0002,%a0
    move.w #0x8200,-2(%a0)              | console: every height 0 first (unrolled - before the picture)
    move.w #1,2(%a0)
    moveq #0,%d0
    .rept 512
    move.w %d0,(%a0)
    .endr
    move.w (%sp)+,%d0
    movea.l (%sp)+,%a0
9:  jmp 0x{SPRITE_CLEAR:X}

wipe:
    movem.l %d0-%d2/%a0,-(%sp)
    lea 0x3C0002,%a0
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 5f
    move.w #32,2(%a0)                   | console: a row at a time from the top
    move.w #0x7000,%d2
    move.w #0xBFD0,%d0
    moveq #31,%d1
1:  move.w %d2,-2(%a0)
    .rept 40
    move.w %d0,(%a0)
    .endr
    addq.w #1,%d2
    dbf %d1,1b
    bra.s 6f
5:  move.w #0x7000,-2(%a0)              | arcade: the original's
    move.w #1,2(%a0)
    move.w #0xBFD0,%d0
    move.w #1279,%d1
2:  move.w %d0,(%a0)
    dbf %d1,2b
6:  move.w #0xBFC0,0x38(%a5)            | as the original (the bottom line's text tiles)
    movem.l (%sp)+,%d0-%d2/%a0
    rts

to_black:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    jmp 0x{WIPE:X}                      | console: black, not see-through (the blue backdrop showed)
9:  jmp 0x{FIX_CLEAR:X}

hold_letter:                            | as LETTER: d0 = column, d1 = row, d2 = character
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    move.l %a0,-(%sp)
    move.w %d3,-(%sp)
    moveq #0,%d3
    move.b 0x{LETTERS_N:X},%d3
    cmpi.b #7,%d3
    bcc.s 8f
    lea 0x{LETTERS:X},%a0
    mulu.w #6,%d3
    adda.w %d3,%a0
    move.w %d0,(%a0)+
    move.w %d1,(%a0)+
    move.w %d2,(%a0)+
    addq.b #1,0x{LETTERS_N:X}
8:  move.w (%sp)+,%d3
    movea.l (%sp)+,%a0
    rts
9:  jmp 0x{LETTER:X}

open_row:                               | a6 = a row's clearing script (its first word: the row's VRAM address)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    move.w %d0,-(%sp)
    move.w (%a6),%d0
    andi.w #31,%d0
    cmpi.w #{BAND_ROW},%d0
    bcs.s 8f
    move.w (%sp)+,%d0
    rts                                 | console: the band's rows stay black
8:  move.w (%sp)+,%d0
9:  jmp 0x{FIX_QUEUE:X}

title:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    cmpi.w #16,0x{SELECT_STATE:X}       | from the input state on (queued there, it shows two frames later -
    bcc.s 9f                            | with the cards)
    rts                                 | console: not while the wipe closes and opens
9:  jmp 0x{FIX_QUEUE:X}

no_label:                               | Z clear = no label (as patch 250's not_practice)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    move #0,%ccr                        | console: never the label
    rts
9:  jmp 0x{label_prev:X}

hold_x:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    move.w 0x{PICK_X:X},12(%a0)         | console: where they stood
    rts
1:  move.w #144,12(%a0)
    rts
"""
    base = rom.place_code(code, why="AES: the character pick without its glitch or slide")
    rom.write(CLEAR_SITE, jsr(base), expect=jsr(FIX_CLEAR), why="character pick: the text cleared with the sprites")
    rom.write(HOLD_SITE, jsr(base + 4), expect=bytes.fromhex("3B7C00B4289C"),
              why="character pick: no slide, the pose at once")
    rom.write(SLIDE_SITE, jsr(base + 8), expect=jsr(FIX_QUEUE), why="character pick: no skip while it would slide")
    rom.write(HOLD_X_SITE, jsr(base + 12), expect=bytes.fromhex("317C0090000C"),
              why="character pick: the character stays where they stood")
    rom.write(0x1294, (base + 16).to_bytes(4, "big"), expect=rom.data[0x1294:0x1298],
              why="vblank: the character pick's delayed clear")
    for site in CLEAR_SITES:
        rom.write(site, jsr(base + 32), expect=jsr(SPRITE_CLEAR), why="into the character select: black, sprite heights off (console)")
    for site in LETTER_SITES:
        rom.write(site, jsr(base + 36), expect=jsr(LETTER), why="character select: MAN / LADY with the rest (console)")
    for site in OPEN_SITES:
        rom.write(site, jsr(base + 40), expect=jsr(FIX_QUEUE), why="character select's opening: the band stays (console)")
    rom.write(TITLE_SITE, jsr(base + 44), expect=jsr(FIX_QUEUE), why="course select: the title after its wipe (console)")
    rom.write(LABEL_SITE + 2, (base + 48).to_bytes(4, "big"), expect=label_prev.to_bytes(4, "big"),
              why="practice course: no PRACTICE COURSE label (console)")
    for site in BLACK_SITES:
        rom.write(site, jsr(base + 28), expect=jsr(FIX_CLEAR), why="into the character select: one cut to black (console)")
    rom.write(WIPE, jmp(base + 24), expect=bytes.fromhex("48E7C08041F9"), why="fix-layer wipe: row by row from the top (console)")
