NAME = "menus"
DESCRIPTION = ("Home console (AES): boots to the title; Start there opens ARCADE / 2P CHALLENGE / OPTIONS; Options = "
               "difficulty, sound test, back to title; Start in a maze pauses (resume, restart, quit, invincibility)")

# How the original runs (docs/code_map.md "Game flow"):
#   * The main loop (0x1042) waits for the vblank, then runs the mode handler from the word 0x102960: 0 = attract
#     (0xE070), 8 = a game (0x43C6). Every entry into the attract from the BIOS (power-on and after each game) goes
#     through the USER request-2 handler 0x10A8 (table 0x1000).
#   * The attract steps through 0x10805E: 8 = a scene player (0x144DA, its step in 0x108052): the health warning
#     (steps 0-24), the intro scenes (28-248), the logo (256-288); then 12-20 = the title (20: PRESS START, a 600-frame
#     countdown in 0x10A8A0, then 24 = a demo game, the rankings, and round again).
#   * Start: the BIOS calls PLAYER_START (0x128 -> 0x1220), which marks player 1 started; the main loop's 0x1940
#     then starts the game (mode 8).
#   * In a game, 0x10806E is the phase (0 = the course steps; 4-24 a screen change) and 0x10806C the course step: 4
#     instructions, 8-20 character / course select, 24 the course tour, 28 the course set-up, 32 the countdown, 36
#     play, 40 a miss. Touching a wall (four places, 0x4994 / 0x4C60 / 0x4E1C / 0x5010) ends the try unless the
#     course (0x108086) is 0, the practice course, which pushes the Zap-Rod back and counts a touch off 0x108090.
#
# What this patch does, on the home console only (the arcade's flow is unchanged - every hook checks the BIOS's
# system mode first):
#   * BOOT TO TITLE: the request-2 handler sets a flag; when the scene player reaches step 4 with it set, it jumps
#     to the logo (step 256), skipping the health warning and the intro scenes. The warning (about the cabinet's air
#     blast and lamps) never shows on the console: the attract loop goes from step 4 to the intro scenes (28).
#   * TITLE MENU: Start on the title (read straight from the hardware, 0x380000, like Riding Hero Plus - the BIOS's
#     PLAYER_START is cancelled in the attract) opens ARCADE / 2P CHALLENGE / OPTIONS where PRESS START was; Up /
#     Down pick, A or Start selects. The title's countdown is held while it's open. Start anywhere else in the
#     attract jumps to the logo with the menu open.
#       ARCADE        the game's own STAGE SELECT and PRACTICE settings switched on (the course select, with the
#                     practice course), then the game starts as before. Its course select has no countdown and
#                     offers every course every time (the game drops played ones, practice too).
#       2P CHALLENGE  not made yet (does nothing).
#       OPTIONS       a black screen (sprites hidden, white text): DIFFICULTY 1-8 (the game's GAME LEVEL setting,
#                     0x10FD8C), MUSIC and SOUND EFFECT tests (the game's own sound lists, 0x2498 / 0x24D4: A plays,
#                     B stops), BACK TO TITLE (the logo again, with the menu open).
#   * PAUSE: Start during a course's countdown or play opens a box over the maze (everything stops: the game's
#     frame doesn't run): RESUME (Start does it too), RESTART LEVEL (the course set-up again, no try lost), QUIT TO
#     TITLE (ends the game the way a game over does), INVINCIBLE ON / OFF (touching a wall then works like the
#     practice course: the Zap-Rod is pushed back; the touch count never runs out).
#
# While a menu screen holds the game (options, pause) it keeps the vblank's own screen work off (0x10A87E, as the
# main loop does while it runs) and draws on the fix layer itself; colours change only in the vblank (fix palette
# 15, restored after, and the backdrop for the options), and the vblank sends the sound test's commands (0x1364 /
# 0x13F6, which it would otherwise skip).

# ---- where the text goes (fix layer: column 0-39, row 0-31; rows 2-29 are on screen)
TITLE_ROW = 21              # three rows from here, columns 11-28 (PRESS START was row 22)
OPTIONS_ROW = 8
PAUSE_COL, PAUSE_ROW = 12, 10   # the pause box: 16 columns x 8 rows

# ---- the game
SYSTEM_MODE = 0x10FD82
P1_CHANGE, P2_CHANGE = 0x10FD97, 0x10FD9D
START_FLAG, PLAYER_MOD, USER_MODE = 0x10FDB4, 0x10FDB6, 0x10FDAF
GAME_LEVEL_DIP = 0x10FD8C
REG_STATUS_B = 0x380000     # bit 0 = P1 Start, bit 2 = P2 Start (active low)
MODE = 0x102960
DEMO_STEP, SCENE_STEP, DEMO_WAIT = 0x10805E, 0x108052, 0x108074
TITLE_TIMER, TITLE_MESSAGE = 0x10A8A0, 0x10804A
PHASE, COURSE_STEP, COURSE, TOUCHES = 0x10806E, 0x10806C, 0x108086, 0x108090
STAGE_SELECT, PRACTICE, COURSES_DONE = 0x108014, 0x108016, 0x108092
CREDIT_SHOWN = 0x108010     # the LEVEL/CREDIT setting's credits half (table 0x376C): show CREDITS n
VBL_BUSY, VBL_FLAGS = 0x10A87E, 0x104B6F
SOUND = 0x243C              # d0 = a sound number (0x8000 + n: the first list)
COPY_DIPS = 0x36C0
FIX_CLEAR = 0xC004C2
SYSTEM_RETURN = 0xC00444

# ---- spare RAM (never written by the game: a write census over the attract and a game, 2026-11-07)
RAM = 0x10EF00
FIX_SAVE = 0x10EA00         # the fix cells under the pause box (256 bytes)

TIME_ROUTINE, TIMER_TICKS = 0x13BE8, 0x10A85A   # the TIME counter (shared with the mazes); its frames
# The course select deck (ARCADE): panel width, where each place in the deck is, the easing.
CARD_SIZE = 230             # the course cards' and frame's size (255 = the game's full size; the console shrinks by
                            # leaving out rows and columns of pixels)
SLIDE_GAP = 285             # from one course card's centre to the next (a card is 271 px wide)
DECK_EASE = 2               # each frame the shown position moves 1/2**DECK_EASE of the way left (bigger = slower)
DECK_SNAP = 8               # ... but at least this much (1/256 course), and snaps when this close
PANEL_Y = 152               # the cards' height (the game's was 160; smaller = higher)
ARROW_Y = 64                # the white arrows (objects 6 / 7; the game's 80), level with the course names
TRACK_DX, CURSOR_POS, CURSOR_COURSE, SELECT_STATE = 0x10A7CE, 0x10A89A, 0x10A898, 0x10A8A0
AFTER_PANELS = 0x89CA       # the course select's frame after it has placed the four panels


def deck_table():
    """(x, size, order) for each 1/32 course of place from -1 to 3 (the strip: -1 left, 0 middle, 1 right;
    2 and up are round the other side, not shown)."""
    rows = []
    for k in range(128):
        r = (k * 8 - 256) / 256
        if r <= 1:
            x, size = 160 + r * SLIDE_GAP * CARD_SIZE / 255, CARD_SIZE
            # order: higher on top. 128+ is the game's front group (the frame 241, the arrows 242): only the
            # course at rest in the middle goes there (with a moving card in it too, the frame went missing)
            order = 240 if k == 32 else 100
        else:
            x, size, order = 160, 0, 1
        rows.append("    .word %d, %d, %d" % (round(x), size, order))
    return "\n".join(rows)


# The course select's text (fix-layer scripts, table 0x2D708): rows to move up, None = not drawn.
FIX_MOVES = {
    0x3186E: None,          # the TIME box
    0x3219A: 4,             # COURSE SELECT (rows 8-9 -> 4-5, where the TIME box was; 0x317AE is another copy)
    0x30E6E: 6, 0x30EA6: 6, 0x30EDE: 6, 0x30F16: 6,   # the course names (rows 13-14 -> 7-8, above the cards)
}
FIX_QUEUE_LEN, FRAME_COUNT = 0x1029E8, 0x10A812
BAND_REQUEST, BAND_SITES = 0x10807C, [0x7804, 0x7A4A]   # the black band's request (0x39E2 in the vblank)


def fix_script(rom, at):
    """The bytes of the fix-layer script at `at`, as the vblank's runner (0x1F32) reads them."""
    i = at + 2
    while True:
        ctrl = rom.data[i]; i += 1
        if ctrl & 0x80:
            i += 1
        if ctrl & 0x40:
            i += 1
        i += (ctrl & 0x3F) + 1
        if rom.data[i] == 0:
            return bytes(rom.data[at:i + 1])


HIT_SITES = [0x4994, 0x4C60, 0x4E1C, 0x5010]
MUSIC_FIRST, MUSIC_COUNT = 6, 24    # the first list's entries 6-29 (0-5 are driver commands)
SFX_COUNT = 129
WHITE, SHADOW, BLACK = 0x7FFF, 0x0333, 0x8000
MENU_PAL = 13               # fix palette borrowed (saved, then put back) for the options' and the pause's text
MENU_PAL_ADDR = 0x400000 + MENU_PAL * 32


def vram(col, row):
    return 0x7000 + col * 32 + row


def asciz(s):
    return '.asciz "%s"' % s


def apply(rom):
    joy_code = int.from_bytes(rom.data[0x1294:0x1298], "big")
    assert rom.data[0x1292:0x1294] == bytes.fromhex("4EB9") and 0x0F1000 <= joy_code < 0x100000, \
        "the vblank's SYSTEM_IO call should go to patch 010's code"
    title_lines = ["      ARCADE      ", "   2P CHALLENGE   ", "     OPTIONS      "]
    pause_lines = ["                ", "     PAUSE      ", "                ", "  RESUME        ",
                   "  RESTART LEVEL ", "  QUIT TO TITLE ", "  INVINCIBLE    ", "                "]
    assert all(len(s) == 18 for s in title_lines) and all(len(s) == 16 for s in pause_lines)
    pal = [0] + [WHITE] * 13 + [SHADOW, BLACK]
    deck_tab = deck_table()
    swaps, copies = [], []
    for n, (orig, rows_up) in enumerate(FIX_MOVES.items()):
        if rows_up is None:
            swaps.append("    .long 0x%X, 0" % orig)
            continue
        script = fix_script(rom, orig)
        new = (int.from_bytes(script[:2], "big") - rows_up).to_bytes(2, "big") + script[2:]
        swaps.append("    .long 0x%X, fix_copy%d" % (orig, n))
        copies.append("fix_copy%d: .byte %s\n    .even" % (n, ", ".join("0x%02X" % b for b in new)))   # word reads
    fix_swaps, fix_copies = "\n".join(swaps), "\n".join(copies)
    code = f"""
    .equ GO_TITLE, {RAM}
    .equ MENU, {RAM + 1}
    .equ CURSOR, {RAM + 2}
    .equ START_PREV, {RAM + 3}
    .equ START_NEW, {RAM + 4}
    .equ INVINC, {RAM + 5}
    .equ PAL_REQ, {RAM + 6}
    .equ OWN, {RAM + 7}
    .equ OCUR, {RAM + 8}
    .equ MUSIC, {RAM + 9}
    .equ SFX, {RAM + 10}
    .equ PCUR, {RAM + 11}
    .equ DECK_INIT, {RAM + 12}
    .equ DECK_T, {RAM + 13}
    .equ DECK_P, {RAM + 14}
    .equ NUMBUF, {RAM + 0x10}
    .equ PAL_SAVE, {RAM + 0x20}

| ---- entry points (fixed offsets from the start: apply() points the hooks here)
    bra.w attract_start         | +0  USER request 2 (the attract starts)
    bra.w scene_hook            | +4  the attract's scene player, each frame of step 8
    bra.w title_frame           | +8  the title's countdown, each frame
    bra.w player_start          | +12 PLAYER_START
    bra.w main_hook             | +16 the main loop, before the mode handler
    bra.w vbl_hook              | +20 the vblank's SYSTEM_IO call
    bra.w hit_check             | +24 a wall touched: Z set = the practice course's way
    bra.w course_timer          | +28 the course select's TIME
    bra.w course_select         | +32 step 20 (character / course select), each frame: Z set = no stage select
    bra.w course_deck           | +36 the course select's cursor and panels, each frame
    bra.w fix_queue             | +40 a fix-layer script queued (fp = it): ARCADE's course select moves / drops some
    bra.w no_band               | +44 the character select asks for a black band along the bottom
    bra.w pick_start            | +48 a course picked: the card starts its grow (a0 = it)
    bra.w pick_wide             | +52 ... it has grown across (a0 = it)
    bra.w pick_full             | +56 ... and down (a0 = it)
    bra.w hand_look             | +60 the Zap-Rod's look in play: d0 = 4 (no hand) or 16 (the outline hand)

attract_start:
    jsr 0x10A8
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    clr.w 0x{CREDIT_SHOWN:X}            | (before the first vblank prints it)
    move.b #1,GO_TITLE
    clr.b MENU
    clr.b OWN
1:  rts

scene_hook:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.b GO_TITLE
    bne.s 3f
    cmpi.w #252,0x{SCENE_STEP:X}
    bcs.s 2f
3:  clr.w 0x{TITLE_MESSAGE:X}           | no PRESS START blinking on black before / while the logo comes in
2:
    cmpi.w #4,0x{SCENE_STEP:X}
    bne.s 1f
    move.w #28,0x{SCENE_STEP:X}        | the health warning (steps 4-24, drawn from 4): never on the console
    tst.b GO_TITLE
    beq.s 1f
    move.w #256,0x{SCENE_STEP:X}       | after power-on / a game: the intro scenes too, to the logo
    clr.b GO_TITLE
1:  jmp 0x144DA

player_start:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.w 0x{MODE:X}
    bne.s 1f
    clr.b 0x{START_FLAG:X}              | the attract: the menu decides (main_hook / title_frame)
    rts
1:  jmp 0x1220

read_start:                             | d0 = Start buttons newly pressed (bit 0 P1, bit 2 P2)
    move.b 0x{REG_STATUS_B:X},%d0
    not.b %d0
    andi.b #0x05,%d0
    move.b START_PREV,%d1
    move.b %d0,START_PREV
    not.b %d1
    and.b %d1,%d0
    move.b %d0,START_NEW
    rts

main_hook:
    move.w #1,0x{VBL_BUSY:X}            | (the instruction this call replaced)
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    clr.w 0x{CREDIT_SHOWN:X}            | no CREDITS n on the console (the vblank's 0x16BA prints it when set)
    bsr.w read_start
    tst.w 0x{MODE:X}
    bne.s 5f
    tst.b %d0                           | the attract: Start opens the title menu
    beq.w 9f
    tst.b MENU
    bne.w 9f
    move.b #1,MENU
    cmpi.w #20,0x{DEMO_STEP:X}
    beq.w 9f                            | on the title already
    cmpi.w #8,0x{DEMO_STEP:X}
    bne.s 3f
    cmpi.w #252,0x{SCENE_STEP:X}
    bcc.w 9f                            | the logo is on its way
3:  move.w #8,0x{DEMO_STEP:X}           | anywhere else: to the logo, then the title with the menu
    move.w #256,0x{SCENE_STEP:X}
    clr.w 0x{DEMO_WAIT:X}
    bra.w 9f
5:  cmpi.w #8,0x{MODE:X}
    bne.w 9f
    tst.b %d0                           | a game: Start in a course's countdown or play pauses
    beq.w 9f
    tst.w 0x{PHASE:X}
    bne.w 9f
    tst.w 0x{DEMO_WAIT:X}
    bne.w 9f
    move.w 0x{COURSE_STEP:X},%d1
    cmpi.w #32,%d1
    beq.s 6f
    cmpi.w #36,%d1
    bne.w 9f
6:  bsr.w pause
9:  rts

wait_vbl:
    bset #7,0x{VBL_FLAGS:X}
1:  tst.b 0x{VBL_FLAGS:X}
    bmi.s 1b
    rts

| ---- text: a1 = string (0 ends it, advanced past), d0 = VRAM address, d1 = palette << 12, d2 = the word for a space
draw_str:
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
    move.w %d0,(%a0)
    nop
    nop
1:  moveq #0,%d3
    move.b (%a1)+,%d3
    beq.s 9f
    cmpi.b #0x20,%d3
    bne.s 2f
    move.w %d2,2(%a0)
    bra.s 1b
2:  add.w %d1,%d3
    addi.w #0xF00-0x30,%d3              | the game's font: tile 0xF00 + character - '0'
    move.w %d3,2(%a0)
    bra.s 1b
9:  rts

| d0 = VRAM address, d1 = palette << 12, d3 = value, d4 = digits
draw_num:
    lea NUMBUF,%a2
    move.w %d4,%d5
    subq.w #1,%d5
    andi.l #0xFFFF,%d3
1:  divu.w #10,%d3
    swap %d3
    move.b %d3,(%a2,%d5.w)
    clr.w %d3
    swap %d3
    dbf %d5,1b
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
    move.w %d0,(%a0)
    nop
    nop
    subq.w #1,%d4
2:  moveq #0,%d2
    move.b (%a2)+,%d2
    add.w %d1,%d2
    addi.w #0xF00,%d2
    move.w %d2,2(%a0)
    dbf %d4,2b
    rts

| d0 = VRAM address, d1 = the word to write there
put_cell:
    lea 0x3C0000,%a0
    move.w %d0,(%a0)
    nop
    nop
    move.w %d1,2(%a0)
    rts

hide_sprites:                           | every sprite's height to 0 (SCB3)
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
    move.w #0x8201,(%a0)
    nop
    nop
    moveq #0,%d0
    move.w #379,%d1
1:  move.w %d0,2(%a0)
    nop
    dbf %d1,1b
    rts

| ---- the title
title_frame:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.b MENU
    bne.s 2f
1:  subq.w #1,0x{TITLE_TIMER:X}         | (the instructions this call replaced; the caller branches on N)
    rts
2:  clr.w 0x{TITLE_MESSAGE:X}           | no PRESS START while the menu is up
    cmpi.b #2,MENU
    beq.s 3f
    move.b #2,MENU                      | the frame it opens: just draw it
    clr.b CURSOR
    bra.w 8f
3:  move.b 0x{P1_CHANGE:X},%d0
    or.b 0x{P2_CHANGE:X},%d0
    btst #0,%d0
    beq.s 4f
    subq.b #1,CURSOR
    bpl.s 4f
    move.b #2,CURSOR
4:  btst #1,%d0
    beq.s 5f
    addq.b #1,CURSOR
    cmpi.b #3,CURSOR
    bcs.s 5f
    clr.b CURSOR
5:  andi.b #0x10,%d0                    | A or Start selects
    or.b START_NEW,%d0
    beq.s 8f
    move.b CURSOR,%d0
    beq.w arcade
    cmpi.b #2,%d0
    bne.s 8f                            | 2P CHALLENGE: not yet
    bsr.w options
    bra.s 9f
8:  bsr.w draw_title_menu
9:  move #0,%ccr                        | N clear: the countdown isn't up
    rts

arcade:
    clr.b MENU
    lea 0x108000,%a5
    jsr 0x{COPY_DIPS:X}                 | the settings again (the difficulty the options set)
    clr.w 0x{CREDIT_SHOWN:X}
    move.w #1,0x{STAGE_SELECT:X}
    move.w #1,0x{PRACTICE:X}
    clr.b 0x{COURSES_DONE:X}            | every course on the course select, practice too
    move.b #1,0x{START_FLAG:X}
    jsr 0x1220                          | player 1 starts, as the BIOS would have done
    move #0,%ccr
    rts

draw_title_menu:
    lea title_lines(%pc),%a1
    move.w #0x{vram(11, TITLE_ROW):X},%d0
    moveq #0,%d5
1:  move.w #0xC000,%d1                  | the title's white (fix palette 12)
    cmp.b CURSOR,%d5
    bne.s 2f
    move.w #0xF000,%d1                  | the selected line in its orange (15)
2:  move.w #0x0F10,%d2
    movem.l %d0/%d5,-(%sp)
    bsr.w draw_str
    movem.l (%sp)+,%d0/%d5
    addq.w #1,%d0
    addq.b #1,%d5
    cmpi.b #3,%d5
    bne.s 1b
    rts

| ---- the options screen (a loop of its own until BACK TO TITLE)
options:
    move.b #1,OWN
    jsr 0x{FIX_CLEAR:X}
    bsr.w hide_sprites
    move.b #3,PAL_REQ                   | white text, black backdrop
    clr.b OCUR
oloop:
    bsr.w draw_options
    bsr.w wait_vbl
    bsr.w read_start
    move.b %d0,%d6
    move.b 0x{P1_CHANGE:X},%d7
    or.b 0x{P2_CHANGE:X},%d7
    lea 0x108000,%a5
    btst #0,%d7
    beq.s 1f
    subq.b #1,OCUR
    bpl.s 1f
    move.b #3,OCUR
1:  btst #1,%d7
    beq.s 2f
    addq.b #1,OCUR
    cmpi.b #4,OCUR
    bcs.s 2f
    clr.b OCUR
2:  moveq #0,%d5
    btst #3,%d7
    beq.s 3f
    moveq #1,%d5
3:  btst #2,%d7
    beq.s 4f
    moveq #-1,%d5
4:  move.b OCUR,%d4
    tst.w %d5
    beq.w 6f
    moveq #0,%d3
    tst.b %d4
    bne.s 41f
    move.b 0x{GAME_LEVEL_DIP:X},%d3     | DIFFICULTY 1-8 (stored 0-7)
    add.w %d5,%d3
    andi.b #7,%d3
    move.b %d3,0x{GAME_LEVEL_DIP:X}
    bra.w 6f
41: cmpi.b #1,%d4
    bne.s 42f
    move.b MUSIC,%d3
    add.w %d5,%d3
    bpl.s 411f
    moveq #{MUSIC_COUNT - 1},%d3
411: cmpi.w #{MUSIC_COUNT},%d3
    bcs.s 412f
    moveq #0,%d3
412: move.b %d3,MUSIC
    bra.s 6f
42: cmpi.b #2,%d4
    bne.s 6f
    move.b SFX,%d3
    add.w %d5,%d3
    bpl.s 421f
    move.w #{SFX_COUNT - 1},%d3
421: cmpi.w #{SFX_COUNT},%d3
    bcs.s 422f
    moveq #0,%d3
422: move.b %d3,SFX
6:  move.b %d7,%d3
    andi.b #0x10,%d3
    or.b %d6,%d3
    beq.s 7f
    cmpi.b #3,%d4
    beq.s oexit
    cmpi.b #1,%d4
    bne.s 61f
    moveq #0,%d0
    move.b MUSIC,%d0
    addi.w #0x8000+{MUSIC_FIRST},%d0
    jsr 0x{SOUND:X}
    bra.s 7f
61: cmpi.b #2,%d4
    bne.s 7f
    moveq #0,%d0
    move.b SFX,%d0
    jsr 0x{SOUND:X}
7:  btst #5,%d7
    beq.w oloop
    move.w #0x8001,%d0                  | B: stop (the attract's own first command)
    jsr 0x{SOUND:X}
    bra.w oloop
oexit:
    jsr 0x{FIX_CLEAR:X}
    move.b #4,PAL_REQ
    bsr.w wait_vbl
    clr.b OWN
    lea 0x108000,%a5
    jsr 0x{COPY_DIPS:X}                 | the new difficulty into the game's settings
    clr.w 0x{CREDIT_SHOWN:X}
    move.w #8,0x{DEMO_STEP:X}           | back to the logo, then the title with the menu open
    move.w #256,0x{SCENE_STEP:X}
    clr.w 0x{DEMO_WAIT:X}
    move.b #1,MENU
    rts

draw_options:
    lea opt_title(%pc),%a1
    move.w #0x{vram(16, OPTIONS_ROW):X},%d0
    move.w #0xF000,%d1
    move.w #0x0F10,%d2
    bsr.w draw_str
    lea opt_lines(%pc),%a1
    move.w #0x{vram(8, OPTIONS_ROW + 4):X},%d0
    moveq #0,%d5
1:  move.w #0xD000,%d1
    cmp.b OCUR,%d5
    bne.s 2f
    move.w #0xF000,%d1
2:  move.w #0x0F10,%d2
    movem.l %d0/%d5,-(%sp)
    bsr.w draw_str
    movem.l (%sp)+,%d0/%d5
    addq.w #2,%d0
    addq.b #1,%d5
    cmpi.b #4,%d5
    bne.s 1b
    moveq #0,%d3
    move.b 0x{GAME_LEVEL_DIP:X},%d3
    addq.w #1,%d3
    move.w #0xD000,%d1
    tst.b OCUR
    bne.s 3f
    move.w #0xF000,%d1
3:  moveq #1,%d4
    move.w #0x{vram(30, OPTIONS_ROW + 4):X},%d0
    bsr.w draw_num
    moveq #0,%d3
    move.b MUSIC,%d3
    addq.w #1,%d3
    move.w #0xD000,%d1
    cmpi.b #1,OCUR
    bne.s 4f
    move.w #0xF000,%d1
4:  moveq #2,%d4
    move.w #0x{vram(29, OPTIONS_ROW + 6):X},%d0
    bsr.w draw_num
    moveq #0,%d3
    move.b SFX,%d3
    addq.w #1,%d3
    move.w #0xD000,%d1
    cmpi.b #2,OCUR
    bne.s 5f
    move.w #0xF000,%d1
5:  moveq #3,%d4
    move.w #0x{vram(28, OPTIONS_ROW + 8):X},%d0
    bsr.w draw_num
    lea opt_help(%pc),%a1
    move.w #0x{vram(8, OPTIONS_ROW + 13):X},%d0
    move.w #0xD000,%d1
    move.w #0x0F10,%d2
    bsr.w draw_str
    move.w #0x{vram(8, OPTIONS_ROW + 14):X},%d0
    bra.w draw_str

| ---- the pause (a loop of its own; returns to the game's frame)
pause:
    move.b #1,OWN
    move.b #1,PAL_REQ                   | the borrowed palette: white text, black box
    bsr.w wait_vbl
    bsr.w save_fix
    clr.b PCUR
ploop:
    bsr.w draw_pause
    bsr.w wait_vbl
    bsr.w read_start
    move.b %d0,%d6
    move.b 0x{P1_CHANGE:X},%d7
    or.b 0x{P2_CHANGE:X},%d7
    btst #0,%d7
    beq.s 1f
    subq.b #1,PCUR
    bpl.s 1f
    move.b #3,PCUR
1:  btst #1,%d7
    beq.s 2f
    addq.b #1,PCUR
    cmpi.b #4,PCUR
    bcs.s 2f
    clr.b PCUR
2:  tst.b %d6
    bne.s presume                       | Start: resume
    btst #4,%d7
    beq.s ploop
    move.b PCUR,%d0
    beq.s presume
    cmpi.b #1,%d0
    beq.s prestart
    cmpi.b #2,%d0
    beq.s pquit
    eori.b #1,INVINC
    bra.s ploop
presume:
    bsr.w restore_fix
    move.b #2,PAL_REQ
    bsr.w wait_vbl
    clr.b OWN
    rts
prestart:
    bsr.s presume
    move.w #4,0x{PHASE:X}               | the screen change, then the course set-up (as after a miss)
    move.w #28,0x{COURSE_STEP:X}
    rts
pquit:
    move.b #2,PAL_REQ
    bsr.w wait_vbl
    clr.b OWN
    clr.w 0x{VBL_BUSY:X}
    lea 0x108000,%a5
    jsr 0x363E                          | the end of a game, as after the last try (0xBA1E)
    clr.w 0x{SCENE_STEP:X}
    move.b #1,0x{USER_MODE:X}
    move.w #0,0x{PLAYER_MOD:X}
    jmp 0x{SYSTEM_RETURN:X}

draw_pause:
    lea pause_lines(%pc),%a1
    move.w #0x{vram(PAUSE_COL, PAUSE_ROW):X},%d0
    moveq #0,%d5
1:  move.w #0xD000,%d1
    move.w #0xDFF0,%d2                  | a solid tile in the borrowed palette's black
    movem.l %d0/%d5,-(%sp)
    bsr.w draw_str
    movem.l (%sp)+,%d0/%d5
    addq.w #1,%d0
    addq.b #1,%d5
    cmpi.b #8,%d5
    bne.s 1b
    lea inv_off(%pc),%a1
    tst.b INVINC
    beq.s 2f
    lea inv_on(%pc),%a1
2:  move.w #0x{vram(PAUSE_COL + 13, PAUSE_ROW + 6):X},%d0
    move.w #0xD000,%d1
    move.w #0xDFF0,%d2
    bsr.w draw_str
    moveq #0,%d0
    move.b PCUR,%d0
    addi.w #0x{vram(PAUSE_COL + 1, PAUSE_ROW + 3):X},%d0
    move.w #0xDF0E,%d1                  | '>'
    bra.w put_cell

save_fix:
    lea {FIX_SAVE},%a1
    lea 0x3C0000,%a0
    move.w #0x{vram(PAUSE_COL, PAUSE_ROW):X},%d1
    moveq #15,%d3
1:  move.w %d1,%d2
    moveq #7,%d4
2:  move.w %d2,(%a0)
    nop
    nop
    nop
    nop
    move.w 2(%a0),(%a1)+
    addq.w #1,%d2
    dbf %d4,2b
    addi.w #32,%d1
    dbf %d3,1b
    rts

restore_fix:
    lea {FIX_SAVE},%a1
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
    move.w #0x{vram(PAUSE_COL, PAUSE_ROW):X},%d1
    moveq #15,%d3
1:  move.w %d1,(%a0)
    nop
    nop
    moveq #7,%d4
2:  move.w (%a1)+,2(%a0)
    nop
    dbf %d4,2b
    addi.w #32,%d1
    dbf %d3,1b
    rts

| ---- the vblank: colours, the sound test's commands, then patch 010's SYSTEM_IO + joystick
vbl_hook:
    move.b PAL_REQ,%d0
    beq.s 5f
    clr.b PAL_REQ
    lea 0x{MENU_PAL_ADDR:X},%a0          | the borrowed fix palette
    lea PAL_SAVE,%a1
    btst #0,%d0
    beq.s 3f
    moveq #15,%d1                       | 1 / 3: save it, then white text (3: and a black backdrop)
1:  move.w (%a0)+,(%a1)+
    dbf %d1,1b
    move.w 0x401FFE,(%a1)
    lea 0x{MENU_PAL_ADDR:X},%a0
    lea text_pal(%pc),%a1
    moveq #15,%d1
2:  move.w (%a1)+,(%a0)+
    dbf %d1,2b
    cmpi.b #3,%d0
    bne.s 5f
    move.w #0x{BLACK:X},0x401FFE
    bra.s 5f
3:  moveq #15,%d1                       | 2 / 4: put it back (4: and the backdrop)
4:  move.w (%a1)+,(%a0)+
    dbf %d1,4b
    cmpi.b #4,%d0
    bne.s 5f
    move.w (%a1),0x401FFE
5:  tst.b OWN
    beq.s 6f
    lea 0x108000,%a5
    jsr 0x13F6                          | the second byte of last frame's sound command (the sound CPU needs
    jsr 0x1364                          | time between the two), then the first byte of the next one
6:  jmp 0x{joy_code:X}

| ---- ARCADE's course select (the game's STAGE SELECT is only on through the menu): no countdown, and every
| course on offer every time (the game marks a played course in 0x108092 and leaves it off the next select)
course_timer:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.w 0x{STAGE_SELECT:X}
    beq.s 1f
    addq.w #1,0x{FRAME_COUNT:X}         | no TIME at all (its box isn't drawn either: fix_queue): just the
    rts                                 | routine's frame count
1:  jmp 0x{TIME_ROUTINE:X}

course_select:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.w 0x{STAGE_SELECT:X}
    beq.s 1f
    clr.b 0x{COURSES_DONE:X}
    cmpi.w #16,0x{SELECT_STATE:X}
    bcc.s 1f
    clr.b DECK_INIT                     | the course select is still setting up: the deck starts afresh
1:  tst.w 0x{STAGE_SELECT:X}            | (the instruction this call replaced)
    rts

| ---- ARCADE's course select as a sliding strip (each frame of its input state, 0x8834): Left / Right move one
| course (round and round); the shown position DECK_P (1/256 course) eases toward the chosen one DECK_T, and each
| of the four course pictures (objects 1-4) takes its place from deck_table: left of the middle (-1..0), the
| middle (0), right (0..1); the rest aren't shown. The grey frame (object 0) stays in the middle.
course_deck:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.w 0x{STAGE_SELECT:X}
    bne.s 2f
1:  move.w 0x{TRACK_DX:X},%d0           | (the instructions this call replaced)
    neg.w %d0
    rts
2:  tst.b DECK_INIT
    bne.s 3f
    move.b #1,DECK_INIT
    move.w 0x{CURSOR_POS:X},%d0         | start on the course the game had picked
    lsr.w #4,%d0
    andi.w #3,%d0
    move.b %d0,DECK_T
    lsl.w #8,%d0
    move.w %d0,DECK_P
3:  move.b 0x{P1_CHANGE:X},%d1
    or.b 0x{P2_CHANGE:X},%d1
    move.b DECK_T,%d0
    btst #2,%d1                         | Left: the next course (the trackball's way round)
    beq.s 4f
    addq.b #1,%d0
4:  btst #3,%d1                         | Right: the one before
    beq.s 5f
    subq.b #1,%d0
5:  andi.b #3,%d0
    cmp.b DECK_T,%d0
    beq.s 6f
    move.b %d0,DECK_T
    moveq #0,%d0                        | the game's click when the course changes
    jsr 0x{SOUND:X}
6:  moveq #0,%d0                        | ease DECK_P toward DECK_T the short way round
    move.b DECK_T,%d0
    lsl.w #8,%d0
    sub.w DECK_P,%d0
    addi.w #512,%d0
    andi.w #1023,%d0
    subi.w #512,%d0                     | d0 = -512..511
    move.w %d0,%d1
    bpl.s 7f
    neg.w %d1
7:  cmpi.w #{DECK_SNAP},%d1
    bhi.s 8f
    add.w %d0,DECK_P                    | close enough: there
    bra.s 9f
8:  asr.w #{DECK_EASE},%d0              | a share of the way each frame (fast, then settling)
    move.w %d0,%d2
    bpl.s 81f
    neg.w %d2
81: cmpi.w #{DECK_SNAP},%d2
    bcc.s 82f
    tst.w %d0
    bpl.s 83f
    move.w #-{DECK_SNAP},%d0
    bra.s 82f
83: move.w #{DECK_SNAP},%d0
82: add.w %d0,DECK_P
9:  andi.w #1023,DECK_P
    moveq #0,%d0                        | the game's cursor: on the chosen course
    move.b DECK_T,%d0
    lsl.w #4,%d0
    move.w %d0,0x{CURSOR_POS:X}
    lsr.w #1,%d0
    move.w %d0,0x{CURSOR_COURSE:X}
    move.w %d0,-(%sp)
    lea 0x100080,%a0                    | the four panels
    moveq #0,%d3                        | panel i at i*256
10: move.w %d3,%d0
    sub.w DECK_P,%d0
    addi.w #256,%d0
    andi.w #1023,%d0                    | 0..1023 = deck place -1..3
    lsr.w #3,%d0
    mulu.w #6,%d0
    lea deck_table(%pc),%a1
    adda.w %d0,%a1
    move.w (%a1)+,12(%a0)               | x
    move.w #{PANEL_Y},14(%a0)
    move.w (%a1)+,%d1                   | size (0 = not shown)
    move.w %d1,16(%a0)
    move.w %d1,18(%a0)
    andi.b #0xFD,11(%a0)
    tst.w %d1
    bne.s 11f
    ori.b #2,11(%a0)
11: move.w (%a1)+,%d0                   | draw order
    jsr 0x1E5C
    lea 128(%a0),%a0
    addi.w #256,%d3
    cmpi.w #1024,%d3
    bcs.w 10b
    lea 0x100000,%a0                    | the grey frame stays in the middle: a window the cards slide past
    move.w #160,12(%a0)
    move.w #{PANEL_Y - 16 * CARD_SIZE // 256},14(%a0)  | (its centre is 16 px above the cards', scaled)
    move.w #{CARD_SIZE},16(%a0)
    move.w #{CARD_SIZE},18(%a0)
    move.w #241,%d0
    jsr 0x1E5C
    move.w #{ARROW_Y},0x{0x100300 + 14:X}       | the arrows: level with the course names, and both always
    move.w #{ARROW_Y},0x{0x100380 + 14:X}       | there (the courses go round; the game hid one at each end)
    andi.b #0xFD,0x{0x100300 + 11:X}
    andi.b #0xFD,0x{0x100380 + 11:X}
    move.w (%sp)+,%d0                   | d0 = the course * 8, as the game's own placement leaves it
    addq.l #4,%sp
    jmp 0x{AFTER_PANELS:X}


| ---- ARCADE's course select: no TIME box, COURSE SELECT up in its place, the course names above the cards.
| The game draws this text with fix-layer scripts (a VRAM address, then tile runs) queued by 0x1F14 and run in the
| vblank; here the queue swaps in copies that start higher up, or leaves the TIME box out.
fix_queue:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 9f
    tst.w 0x{STAGE_SELECT:X}
    beq.s 9f
    cmpi.w #8,0x{MODE:X}
    bne.s 9f
    cmpi.w #20,0x{COURSE_STEP:X}
    bne.s 9f
    move.l %a0,-(%sp)
    lea fix_swaps(%pc),%a0
1:  tst.l (%a0)
    beq.s 8f
    cmpa.l (%a0)+,%a6
    beq.s 2f
    addq.l #4,%a0
    bra.s 1b
2:  move.l (%a0),%a6                    | its replacement (0 = none: don't draw it)
    move.l (%sp)+,%a0
    cmpa.w #0,%a6
    bne.s 9f
    addq.l #4,%sp                       | out of 0x1F14 altogether
    rts
8:  move.l (%sp)+,%a0
9:  cmpi.w #128,0x{FIX_QUEUE_LEN:X}     | (the instruction this call replaced)
    rts

| ---- the character select's black band along the screen's bottom (rows 28-31, 0x17D50): not on the console -
| the wallpaper goes all the way down, as on the course select
no_band:
    tst.b 0x{SYSTEM_MODE:X}
    beq.s 1f
    move.w #1,0x{BAND_REQUEST:X}        | (the instruction this call replaced)
1:  rts

| ---- A course picked in ARCADE: the game grows the card from a line to its full size (255) and puts a full-size
| highlight frame (object 5) over it; on the console they stop at the cards' size (CARD_SIZE) instead.
pick_start:
    move.w #31,16(%a0)                  | (the instructions this call replaced)
    move.w #1,18(%a0)
    bsr.s arcade_select
    bne.s 1f
    move.w #{CARD_SIZE - 224},16(%a0)   | (it grows 32 a frame for 7 frames: to CARD_SIZE)
    move.w #{PANEL_Y - 16 * CARD_SIZE // 256},0x{0x100280 + 14:X}   | the highlight frame, like the grey one
    move.w #{CARD_SIZE},0x{0x100280 + 16:X}
    move.w #{CARD_SIZE},0x{0x100280 + 18:X}
1:  rts
pick_wide:
    move.w #255,16(%a0)
    bsr.s arcade_select
    bne.s 1f
    move.w #{CARD_SIZE},16(%a0)
1:  rts
pick_full:
    move.w #255,16(%a0)
    move.w #255,18(%a0)
    bsr.s arcade_select
    bne.s 1f
    move.w #{CARD_SIZE},16(%a0)
    move.w #{CARD_SIZE},18(%a0)
1:  rts
| ---- Button B in play: the game was made to show a see-through outline hand holding the Zap-Rod, B hiding it, but
| the released code always picks "no hand". On the console it's back, the other way round: no hand at first (as
| the game has always looked), B shows it, B again hides it (0x108EEC bit 0, toggled by the game; 0 at each game).
hand_look:
    move.w #4,%d0                       | no hand (always, on the arcade machine)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    btst #0,0x108EED
    beq.s 1f
    move.w #16,%d0                      | the outline hand
1:  rts

arcade_select:                          | Z set = the console's ARCADE (stage select on)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.w 0x{STAGE_SELECT:X}
    beq.s 2f
    cmp.w %d0,%d0
    rts
2:  moveq #1,%d0                        | (d0 isn't used by the callers after: Z clear)
1:  rts

| ---- a wall touched (a5 = 0x108000): Z set = carry on like the practice course
hit_check:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    tst.b INVINC
    beq.s 1f
    cmpi.w #2,0x{TOUCHES:X}            | the practice way counts a touch off (not in its grace time after
    bge.s 2f                            | one) and ends the try at 0: keep it from getting there
    move.w #2,0x{TOUCHES:X}
2:  ori.b #4,%ccr
    rts
1:  tst.w 0x{COURSE:X}
    rts

deck_table:
{deck_tab}
fix_swaps:
{fix_swaps}
    .long 0
{fix_copies}
    .even
text_pal: .word {", ".join("0x%04X" % c for c in pal)}
title_lines:
{chr(10).join("    " + asciz(s) for s in title_lines)}
pause_lines:
{chr(10).join("    " + asciz(s) for s in pause_lines)}
inv_on: {asciz("ON ")}
inv_off: {asciz("OFF")}
opt_title: {asciz("OPTIONS")}
opt_lines:
    {asciz("DIFFICULTY            ")}
    {asciz("MUSIC                 ")}
    {asciz("SOUND EFFECT          ")}
    {asciz("BACK TO TITLE         ")}
opt_help:
    {asciz("LEFT RIGHT  CHANGE")}
    {asciz("A  PLAY     B  STOP")}
    .even
"""
    base = rom.place_code(code, why="AES menus: boot to title, title menu, options, pause")
    entry = {name: base + 4 * i for i, name in enumerate(
        ["attract_start", "scene_hook", "title_frame", "player_start", "main_hook", "vbl_hook", "hit_check",
         "course_timer", "course_select", "course_deck", "fix_queue", "no_band", "pick_start", "pick_wide",
         "pick_full", "hand_look"])}

    def jsr(a):
        return bytes.fromhex("4EB9") + a.to_bytes(4, "big")

    rom.write(0x1008, entry["attract_start"].to_bytes(4, "big"), expect=bytes.fromhex("000010A8"),
              why="USER request 2 (the attract starts) -> + boot-to-title flag")
    rom.write(0xE34E, jsr(entry["scene_hook"]), expect=bytes.fromhex("4EB9000144DA"),
              why="attract scene player -> skip to the logo after boot / a game")
    rom.write(0xE56A, jsr(entry["title_frame"]) + bytes.fromhex("6A10"), expect=bytes.fromhex("536D28A06A000012"),
              why="title countdown -> the title menu")
    rom.write(0x128, bytes.fromhex("4EF9") + entry["player_start"].to_bytes(4, "big"),
              expect=bytes.fromhex("4EF900001220"), why="PLAYER_START -> the menu decides in the attract")
    rom.write(0x1066, jsr(entry["main_hook"]), expect=bytes.fromhex("3B7C0001287E"),
              why="main loop -> Start: title menu / pause")
    rom.write(0x1292, jsr(entry["vbl_hook"]), expect=jsr(joy_code),
              why="vblank SYSTEM_IO (+ joystick) -> + menu colours and sounds")
    for site in HIT_SITES:
        rom.write(site, jsr(entry["hit_check"]) + bytes.fromhex("672C"), expect=bytes.fromhex("4A6D00866700002E"),
                  why="wall touched -> invincibility like the practice course")
    rom.write(0x8810, jsr(entry["course_timer"]), expect=jsr(TIME_ROUTINE),
              why="course select's TIME -> no countdown in ARCADE")
    rom.write(0x7AF8, jsr(entry["course_select"]) + bytes.fromhex("6734"), expect=bytes.fromhex("4A6D001467000036"),
              why="character / course select -> every course on offer in ARCADE")
    rom.write(0x8834, jsr(entry["course_deck"]), expect=bytes.fromhex("302D27CE4440"),
              why="course select's cursor and panels -> a deck of cards in ARCADE")
    rom.write(0x1F14, jsr(entry["fix_queue"]), expect=bytes.fromhex("0C6D0080A9E8"),
              why="fix-layer script queue -> ARCADE's course select text moved")
    for site in BAND_SITES:
        rom.write(site, jsr(entry["no_band"]), expect=bytes.fromhex("3B7C0001007C"),
                  why="character select's black bottom band -> not on the console")
    rom.write(0x8B54, jsr(entry["pick_start"]) + bytes.fromhex("4E714E714E71"),
              expect=bytes.fromhex("317C001F0010317C00010012"), why="course picked -> the card grows to CARD_SIZE")
    rom.write(0x8BAC, jsr(entry["pick_wide"]), expect=bytes.fromhex("317C00FF0010"),
              why="course picked, grown across -> CARD_SIZE")
    rom.write(0x8BEA, jsr(entry["pick_full"]) + bytes.fromhex("4E714E714E71"),
              expect=bytes.fromhex("317C00FF0010317C00FF0012"), why="course picked, grown down -> CARD_SIZE")
    rom.write(0x18A4A, jsr(entry["hand_look"]) + bytes.fromhex("600C"),   # bra.s 0x18A5E
              expect=bytes.fromhex("303C0010303C0004"), why="the Zap-Rod's look -> B shows the outline hand")
