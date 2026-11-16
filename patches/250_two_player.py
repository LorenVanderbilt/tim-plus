NAME = "two-player"
DESCRIPTION = "Home console (AES): 2P CHALLENGE - two players take turns on one course, the first to the goal wins"

# How it plays: choosing 2P CHALLENGE on the title starts an ARCADE game with a rules screen, then goes straight to
# the course select (no instructions, no character select; player 1 is the man, player 2 the lady). Before every
# turn a PLAYER n / PRESS START box shows over the course. A turn ends on a miss (a touch, or the time running out),
# and the next player carries on from their own checkpoint. No tries are lost. The first to cross the goal line
# wins: after the game's own goal and name entry comes a winner screen with each player's misses and time in play,
# and Start goes back to the title.
#
# How it works:
#   * Title menu: patch 020's "2P CHALLENGE: not yet" (cmpi.b #2,d0; bne.s, found by pattern) calls here instead.
#   * A miss takes a try at 0x99AE (subq.w #1,0x10808E; bgt.w 0x9A50 restarts, otherwise it's game over); a time-out
#     is a miss too. In 2P no try is taken. The player's zone (0x108088; the course set-up puts the Zap-Rod at its
#     start) is kept and the other player's put in, with their character (0x108EBE: 0 = the man, 4 = the lady, as
#     the character select sets it at 0x77A0). Then the course restarts as usual, with the full time for each turn.
#   * The practice course has no tries: its miss normally ends the course (0x97F4, back to the course select). In
#     2P it goes the same way as the other courses' (0x99AE).
#   * The main loop hook (in front of patches 190 / 020's at 0x1066) handles the game start; the turn box, at course
#     step 32 (the countdown) once its fade-in is done (0x10A89A = 0); the time in play (step 36); and the winner
#     (step 44 is a goal; when the course select comes back afterwards, step 20, the winner screen shows, then the
#     game ends the way patch 230's QUIT TO TITLE ends it).
#   * The turn box works like patch 230's pause box: its frame colours (PAL_FIX), the black-backed letters, and the
#     fix cells under it saved and put back.
#   * The rules screen runs in the game's first frame, as a loop of its own inside the main loop before the
#     instructions' step runs. The vblank keeps running, so the wallpaper scrolls. START leaves the way the character
#     select does, to the course select (the wallpaper stays); BACK ends the game. In 2P the course select leaves out
#     each card's record.
#   * In 2P the practice course plays like the others. Its tour has no rules ticker (it gets its own list: the
#     other courses' sign step 0xCA5C, then practice's pans) and no PRACTICE COURSE label (0xCFF8). A touch is a miss
#     (the four wall checks at 0x4994 / 0x4C60 / 0x4E1C / 0x5010 would push the rod back on course 0). The tour can
#     be skipped from the start (0xC4A0), and a miss looks like the other courses' (0x9004), not like a time-out.
#   * On every course in 2P the spare Zap-Rods under the clock aren't shown (0x3B8E, as on practice).

from patchlib import load_patch as load, fix_vram as vram, find_once, jsr

# The rules screen: the scrolling wallpaper, the title in the instructions' heading font, a wide box (the
# tutorial's) with the mode's description, and a smaller box with START / BACK TO TITLE and an arrow at the one
# picked. The tutorial's tall font has A-Z, space . - , " < > (34 characters a line at most).
TITLE = "2P CHALLENGE"
DESCRIPTION_LINES = [
    "TWO PLAYERS TAKE TURNS ON THE",
    "SAME COURSE. YOUR TURN ENDS WHEN",
    "THE ZAP-ROD TOUCHES A WALL OR TIME",
    "RUNS OUT. FIRST TO THE GOAL WINS.",
]
CHOICES = ["START", "BACK TO TITLE"]
TITLE_ROW = 3
BIG_BOX = (2, 6, 36)                    # fix column, row, width (the height follows from the lines)
SMALL_BOX = (10, 22, 20)

SYSTEM_MODE = 0x10FD82
P1_CHANGE, P2_CHANGE = 0x10FD97, 0x10FD9D
RAM = 0x10EF00                                       # patch 020's RAM
CURSOR, START_PREV, START_NEW, PAL_REQ, OWN = RAM + 2, RAM + 3, RAM + 4, RAM + 6, RAM + 7
PAL_FIX = 0x10EC25                                   # patch 230's: 1 = its vblank sets the box frame's colours
SAVE = 0x10E400                                      # patch 230's: the fix cells under a box
TWO_P = 0x10EC28                                     # spare RAM: 0 = off, 2 = starting, 1 = on
CUR, TURN, WINNER = 0x10EC29, 0x10EC2A, 0x10EC2B
CHARS = 0x10EC2E                                     # 2 words: each player's character
ZONES = 0x10EC32                                     # 2 words: each player's zone
MISSES = 0x10EC36                                    # 2 words
FRAMES = 0x10EC3A                                    # 2 words: frames in play (up to 65535, about 18 minutes)
assert FRAMES + 4 <= 0x10EC40                        # patch 170's PAL6_SAVE starts at 0x10EC40
MODE, COURSE_STEP, ZONE, CHARACTER, TRIES = 0x102960, 0x10806C, 0x108088, 0x108EBE, 0x10808E
FADE = 0x10A89A                                      # the countdown's fade-in steps left
REG_STATUS_B, VBL_FLAGS, VBL_BUSY = 0x380000, 0x104B6F, 0x10A87E
SCENE_STEP = 0x108052
PLAYER_MOD, USER_MODE, SYSTEM_RETURN, GAME_OVER = 0x10FDB6, 0x10FDAF, 0xC00444, 0x363E
FIX_CLEAR = 0xC004C2
SCREEN_FADE = 0x108074                               # the screen change's fade: while it isn't 0, the vblank fills
                                                     # the fix layer with its shade tiles (0x3A56)
BG_REQ = 0x108072                                    # the scrolling wallpaper: n = the vblank builds it with colour
                                                     # set n (0x39BC -> 0x1B372; 1 = the character select's)
BOX_REQ = 0x10EC22                                   # patch 170's: 1 = the tutorial box's colours into palette 6, 2 = back
PAL9_REQ = 0x10EC2D                                  # spare RAM: 1 = the heading's colours into palette 9, 2 = back
RULES_UP = 0x10EC3E                                  # spare RAM: 1 = a screen of ours is up, so our vblank scrolls
                                                     # the wallpaper (0x1B45E; the game's doesn't, this early)
PAL9_SAVE = 0x10E800                                 # spare RAM, 32 bytes
PAL9 = [0x0000, 0x7FFF, 0x4900, 0x4A00, 0x4B00, 0x4C00, 0x4D30, 0x4E30, 0x6E40, 0x4F60, 0x6F70, 0x6F90, 0x4FB0,
        0x4FD0, 0x6FE7, 0x0000]                      # palette 9 as the instructions' INSTRUCTION heading has it
RECORD_SITES = {0x7D68: 0x7D9C, 0x8272: 0x82A6, 0x8A7A: 0x8AAE}   # the course select's record under a card
                                                     # (initials 0x1803A x 3, time 0x18296), from its move.w #20,d0;
                                                     # move.w #26,d1 -> the address after it
PRACTICE_SITE = 0x97F4                               # tst.w 0x86(a5); bne.w 0x99AE (practice has no tries: its miss
                                                     # ends the course, back to the course select)
CHAR_SELECT_EXIT = 0x7734                            # the character select's way out (to course step 20); its bra is now an rts
MISS_SITE = 0x99AE                                   # subq.w #1,0x8E(a5); bgt.w 0x9A50
RESTART = 0x9A50
WALL_SITES = [0x4994, 0x4C60, 0x4E1C, 0x5010]       # jsr <020's hit_check / 040's touch>; beq.s (Z set = practice's
                                                    # push back), in place of the original's tst.w 0x86(a5); beq.w
TOUR_LIST = 0xC4CC                                  # move.w 0x86(a5),d0 ... movea.l (a0,d0.w),a0: the tour's list
TOUR_SKIP = 0xC4A0                                  # tst.w 0x86(a5); bne.w 0xC4B2 (practice: no skip before its 6th step)
LABEL_SITE = 0xCFF8                                 # tst.w 0x86(a5); bne.w 0xD018 (practice: the PRACTICE COURSE label)
MISS_LOOK = 0x9004                                  # tst.w 0x86(a5); bne.w 0x9012 (on practice a miss looks like a
                                                    # time-out, 0x10A85C = 4: no smoke, no fade; in 2P as on the others)
FADE_PAL = 0x22FC4                                  # move.w #0x800,d0; jsr 0x22584: the countdown's fade-in of the
                                                    # course's colours. It always fades palette 64 on, but practice's
                                                    # are at 80 (0x2302E loads them there). This original bug only
                                                    # shows when practice restarts in place (a miss clears palettes
                                                    # 16-253): in 2P its start area came back black
SPARES_SITE = 0x3B8E                                # tst.w 0x86(a5); bne.w 0x3B9C (practice: no spare rods shown)
BOX_COL, BOX_W, BOX_H = 9, 22, 7

# The winner screen: the scrolling wallpaper and the winner's portrait from the screen after a course win, with a
# dithered shadow. Player 1 (the man) is on the left with the stats box on the right; player 2 (the lady) is on the
# right with the box on the left. The box is the tutorial's: PLAYER n / WINS in the heading font, MISSES / TIME /
# PRESS START in the tall font, and the numbers in the game font (the tall font has no digits).
PORTRAITS = {1: 0xC30, 2: 0xC2C}                     # sprite pieces (table 0x5100C) from the screen after a course
                                                     # win: the man, the lady (in palettes 224 + the piece's offset)
PORTRAIT_PALS = {1: [(224, 0x4EF0C), (228, 0x4EF8C), (229, 0x4EFCC), (230, 0x4EFAC)],
                 2: [(224, 0x4EF0C), (225, 0x4EF2C), (226, 0x4EF4C), (227, 0x4EF6C)]}   # (palette, its colours)
PORTRAIT_BASE = 224
PORTRAIT_MARGIN = 6                                  # px from the screen's side (the bottom sits on the screen's bottom)
SHADOW = (8, 6)                                      # the shadow's offset in px: toward the box, and down
SHADOW_PAL = 240                                     # unused by the game; colour 1 = black
SPR_SHADOW, SPR_PORTRAIT, SPR_BACKING = 170, 180, 190  # sprite numbers, clear of the ranges whose heights the vblank
                                                     # (0x12E0) rewrites every frame: 41-168 and 220-347
WIN_BOX_COL = {1: 21, 2: 1}                          # the box takes fix columns c to c + 17, rows 3 to 24
PORT_REQ = 0x10EC3F                                  # spare RAM: n = the vblank loads winner n's portrait colours
SMALL = 0x6F00                                       # the game font (tile 0xF00 + char - 0x30) in the box's palette 6

import patchlib


def heading(text):
    """The instructions' heading font (patchlib.heading_tiles) in its palette byte, 0x94."""
    top, bottom = patchlib.heading_tiles(text)
    return [0x9000 | x for x in top], [0x9000 | x for x in bottom]


def tall_halves():
    """The tutorial's tall font: a character's (top, bottom) tiles' low bytes (tile 0xE00 + these)."""
    halves070 = load("070_instructions.py").halves
    return lambda ch: {"<": (0xEE, 0xFE), ">": (0xEF, 0xFF), ",": (0xC0, 0xFC)}.get(ch) or halves070(ch)


class Fix:
    """Fix cells {(column, row): word}, written out as runs: (VRAM, count - 1, words...) repeated, then 0."""
    def __init__(self):
        self.cells, self.halves = {}, tall_halves()

    def box(self, col, row, w, h):                  # the tutorial's box (palette 6), inside = the tall font's space
        for r in range(h):
            for k in range(w):
                if r == 0: t = 0x5EE if k == 0 else (0x600 if k == w - 1 else 0x5EF)
                elif r == h - 1: t = 0x5FE if k == 0 else (0x610 if k == w - 1 else 0x5FF)
                elif k == 0: t = 0x601 if r % 2 else 0x611
                elif k == w - 1: t = 0x602 if r % 2 else 0x612
                else: t = 0xEC0
                self.cells[(col + k, row + r)] = 0x6000 | t

    def tall(self, col, row, text):
        for i, ch in enumerate(text):
            a, b = self.halves(ch)
            self.cells[(col + i, row)], self.cells[(col + i, row + 1)] = 0x6E00 | a, 0x6E00 | b

    def heading(self, col, row, text):
        top, bottom = heading(text)
        for i, (a, b) in enumerate(zip(top, bottom)):
            self.cells[(col + i, row)], self.cells[(col + i, row + 1)] = a, b

    def small(self, col, row, text):
        for i, ch in enumerate(text):
            self.cells[(col + i, row)] = SMALL + ord(ch) - 0x30

    def runs(self):
        out = []
        for row in range(32):
            cols = sorted(c for c, r in self.cells if r == row)
            while cols:
                start = cols[0]; n = 1
                while n < len(cols) and cols[n] == start + n: n += 1
                out += [vram(start, row), n - 1] + [self.cells[(start + k, row)] for k in range(n)]
                cols = cols[n:]
        return ", ".join("0x%04X" % w for w in out + [0])


def rules_screen(rom):
    """The rules screen's fix runs; the arrows' VRAM addresses (the last choice's first); the blank, arrow top and
    arrow bottom tiles."""
    fx = Fix()
    fx.heading(20 - len(TITLE), TITLE_ROW, TITLE)
    bc, br, bw = BIG_BOX
    fx.box(bc, br, bw, 3 * len(DESCRIPTION_LINES) + 2)
    for i, line in enumerate(DESCRIPTION_LINES):
        assert len(line) <= bw - 2, "2P rules: line too long: %r" % line
        fx.tall(bc + 1 + (bw - 2 - len(line)) // 2, br + 2 + 3 * i, line)
    sc, sr, sw = SMALL_BOX
    fx.box(sc, sr, sw, 3 * len(CHOICES) + 1)
    arrows = []
    for i, choice in enumerate(CHOICES):
        col = sc + 1 + (sw - 2 - len(choice)) // 2
        fx.tall(col, sr + 1 + 3 * i, choice)
        arrows.append(vram(col - 2, sr + 1 + 3 * i))
    a_top, a_bottom = fx.halves(">")
    return fx.runs(), list(reversed(arrows)), 0x6E00 | 0xC0, 0x6E00 | a_top, 0x6E00 | a_bottom


def win_screen(winner):
    """Winner n's fix runs, and the VRAM addresses its numbers go to: the misses' last digit (P1, P2) and the
    minutes (P1, P2)."""
    fx, c = Fix(), WIN_BOX_COL[winner]
    fx.box(c, 3, 18, 22)
    fx.heading(c + 1, 5, "PLAYER %d" % winner)
    fx.heading(c + 5, 8, "WINS")
    fx.tall(c + 2, 12, "MISSES")
    fx.small(c + 3, 15, "P1"); fx.small(c + 11, 15, "P2")
    fx.tall(c + 2, 17, "TIME")
    fx.small(c + 2, 20, "P1"); fx.small(c + 6, 20, ":"); fx.small(c + 10, 20, "P2"); fx.small(c + 14, 20, ":")
    fx.tall(c + 3, 22, "PRESS START")
    return fx.runs(), [vram(c + 7, 15), vram(c + 15, 15), vram(c + 5, 20), vram(c + 13, 20)]


def piece_cells(rom, w):
    """A sprite piece's tiles as [(column, row, tile, attribute)], decoded from any of the 8 formats in table
    0x5100C (as the sprite writer, 0x2ED2-0x324E, reads them). The attribute's high byte is the palette offset; its
    low byte holds tile bits 16-19 (in bits 4-7) and the flips."""
    e = 0x5100C + (w & 0x7FFC)
    v = rom.u32(e)
    fmt, cols, rows = v >> 29, ((v >> 24) & 31) + 1, ((v >> 20) & 15) + 1
    a, d, out = e + (v & 0xFFFFF), rom.data, []
    if fmt in (1, 2, 4, 6): h = rom.u16(a); a += 2
    if fmt in (5, 7): h = d[a]; a += 1
    for k in range(cols * rows):
        if fmt == 0: t, at = rom.u16(a), rom.u16(a + 2); a += 4
        elif fmt == 1: t, at = rom.u16(a), h; a += 2
        elif fmt == 2: t, at = (h & 0xFF00) | d[a], (h & 0xFF) << 8; a += 1
        elif fmt == 3: t, at = rom.u16(a), d[a + 2] << 8; a += 3
        elif fmt == 4: t, at = (h & 0xFF00) | d[a], d[a + 1] << 8; a += 2
        elif fmt == 5: t, at = rom.u16(a), (h << 8) | d[a + 2]; a += 3
        elif fmt == 6: t, at = (h & 0xFF00) | d[a], ((h & 0xFF) << 8) | d[a + 1]; a += 2
        else: t, at = (h << 8) | d[a], (d[a + 1] << 8) | d[a + 2]; a += 3
        out.append((k // rows, k % rows, t, at))
    return out, cols, rows


def sprite_block(first, x, y, cols, rows, words):
    """An entry for put_blocks: first sprite, columns - 1, rows, SCB4 (x), SCB3 (y and rows), then the SCB1 words
    (tile, attribute) column by column."""
    return [first, cols - 1, rows, (x & 0x1FF) << 7, (((496 - y) & 0x1FF) << 7) | rows] + words


def win_sprites(rom, winner):
    """Winner n's sprites: the shadow, the portrait, and the box's black backing (behind the fonts' see-through
    parts)."""
    cells, cols, rows = piece_cells(rom, PORTRAITS[winner])
    mask = set()
    for c, r, t, at in cells:
        for y, line in enumerate(rom.sprite_tile(t & 0xFFFF)):
            for x, v in enumerate(line):
                if v:
                    mask.add((16 * c + (15 - x if at & 1 else x), 16 * r + (15 - y if at & 2 else y)))
    xs, ys = [p[0] for p in mask], [p[1] for p in mask]
    width = max(xs) - min(xs) + 1
    x0 = PORTRAIT_MARGIN - min(xs) if winner == 1 else 320 - PORTRAIT_MARGIN - width - min(xs)
    y0 = 224 - (max(ys) + 1)
    sx, sy = x0 + (SHADOW[0] if winner == 1 else -SHADOW[0]), y0 + SHADOW[1]
    portrait, shadow = [], []
    for c, r, t, at in cells:                       # (column by column, as the piece)
        portrait += [t & 0xFFFF, ((PORTRAIT_BASE + (at >> 8)) << 8) | (at & 0xFF)]
        dots = [[1 if (16 * c + x, 16 * r + y) in mask and (sx + 16 * c + x + sy + 16 * r + y) % 2 == 0 else 0
                 for x in range(16)] for y in range(16)]
        n = rom.add_sprite_tile(dots, why="2P winner screen: the portrait's dithered shadow", share=True)
        shadow += [n & 0xFFFF, (SHADOW_PAL << 8) | ((n >> 16) << 4)]
    solid = rom.add_sprite_tile([[1] * 16 for _ in range(16)], why="2P winner screen: the box's black backing",
                                share=True)
    bc = WIN_BOX_COL[winner]
    backing = [solid & 0xFFFF, (SHADOW_PAL << 8) | ((solid >> 16) << 4)] * (8 * 10)
    out = (sprite_block(SPR_SHADOW, sx, sy, cols, rows, shadow) + sprite_block(SPR_PORTRAIT, x0, y0, cols, rows, portrait)
           + sprite_block(SPR_BACKING, 8 * (bc + 1), 16, 8, 10, backing) + [0])
    assert SPR_SHADOW + cols <= SPR_PORTRAIT and SPR_PORTRAIT + cols <= SPR_BACKING and SPR_BACKING + 8 <= 220
    return ", ".join("0x%04X" % w for w in out)


def apply(rom):
    m230 = load("230_pause_menu.py")
    tiles = m230.black_backed_tiles(rom, set("PLAYERPRESSTART12") - {" "})
    tile = lambda ch: m230.BLACK if ch == " " else tiles[ch]
    # the turn box
    w, h, c0 = BOX_W, BOX_H, BOX_COL
    top = 16 - h // 2
    grid = [[m230.BLACK] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if r == 0: t = 0x5EE if c == 0 else (0x600 if c == w - 1 else 0x5EF)
            elif r == h - 1: t = 0x5FE if c == 0 else (0x610 if c == w - 1 else 0x5FF)
            elif c == 0: t = 0x601 if r % 2 else 0x611
            elif c == w - 1: t = 0x602 if r % 2 else 0x612
            else: continue
            grid[r][c] = 0xD000 | t
    def text(r, s):
        c = (w - len(s)) // 2
        for i, ch in enumerate(s): grid[r][c + i] = tile(ch)
        return c
    pcol = text(2, "PLAYER 1") + 7                   # the player's digit
    text(4, "PRESS START")
    words = lambda v: ", ".join("0x%04X" % x for x in v)
    screen_words, ARROWS, BLANK, ARROW_TOP, ARROW_BOTTOM = rules_screen(rom)
    win = {n: win_screen(n) for n in (1, 2)}
    win_blocks = {n: win_sprites(rom, n) for n in (1, 2)}
    for n in (1, 2):
        for pal, at in PORTRAIT_PALS[n]:
            assert rom.u16(at) == 0 and rom.u16(at + 2) == 0x0333, "2P winner: palette %d's colours?" % pal
    m020 = load("020_menus.py")
    pat_title = bytes.fromhex("1039") + CURSOR.to_bytes(4, "big") + bytes.fromhex("6700")
    at = find_once(rom, pat_title, "2P: patch 020's title menu not found")
    arcade = at + 8 + int.from_bytes(rom.data[at + 8:at + 10], "big", signed=True)
    title_site = at + 10
    assert rom.data[title_site:title_site + 4] == bytes.fromhex("0C000002") and rom.data[title_site + 4] == 0x66
    assert rom.data[CHAR_SELECT_EXIT:CHAR_SELECT_EXIT + 6] == bytes.fromhex("4EB900018BA4") and \
        rom.data[0x7780:0x7784] == bytes.fromhex("60000094"), "2P: the character select's end isn't as expected"
    assert rom.data[MISS_SITE:MISS_SITE + 8] == bytes.fromhex("536D008E6E00009C")
    assert rom.data[0x1066:0x1068] == b"\x4E\xB9"
    prev_main = rom.u32(0x1068)

    # The practice course's tour list, with its first two steps (the sign, then 4 rules ticker lines and the sign's
    # end) swapped for the other courses' sign step
    lst = rom.u32(0xC544)
    tour0 = [rom.u32(lst + 4 * i) for i in range(30)]
    tour0 = tour0[:tour0.index(0xFFFFFFFF) + 2]
    assert tour0[0] == 0xCAD4 and tour0[2:12:2] == [0xC88A, 0xC8B6, 0xC914, 0xC972, 0xC9D0], "2P: practice tour?"
    tour0 = tour0[:2] + [0xCA5C, 0] + tour0[12:]
    for site in WALL_SITES:
        assert rom.data[site:site + 2] == b"\x4E\xB9" and rom.data[site + 6:site + 8] == b"\x67\x2C", "2P: wall?"
    wall_prev = [rom.u32(site + 2) for site in WALL_SITES]

    code = f"""
    bra.w title                 | +0 patch 020's title menu: 2P CHALLENGE chosen (d0 = the cursor 1 / 2)
    bra.w miss                  | +4 a miss takes a try (0x99AE)
    bra.w main                  | +8 the main loop
    bra.w practice              | +12 a miss on the practice course
    bra.w vbl                   | +16 the vblank chain: palette 9 for the rules screen's heading
    bra.w record_7D68           | +20 the course select's record under a card
    bra.w record_8272           | +24 the course select's record under a card
    bra.w record_8A7A           | +28 the course select's record under a card
    bra.w not_practice          | +32 tst.w course: in 2P always "not practice" (Z clear)
    bra.w no_spares             | +36 tst.w course: in 2P always "practice" (Z set), so no spare rods show
    bra.w tour_list             | +40 a0 = the course tour's list
{"".join(f"    bra.w wall_{i}               | +{44 + 4 * i} a wall touched (0x{site:X})" + chr(10) for i, site in enumerate(WALL_SITES))}
    bra.w fade_pal              | +60 the countdown's fade-in: practice's colours to palette 80 in 2P
fade_pal:
    move.w #0x800,%d0
    cmpi.b #1,0x{TWO_P:X}
    bne.s 1f
    tst.w 0x108086
    bne.s 1f
    move.w #0xA00,%d0
1:  jmp 0x22584
{"".join(f"wall_{i}:" + chr(10) + f"    cmpi.b #1,0x{TWO_P:X}" + chr(10) + "    bne.s 1f" + chr(10) + "    tst.w 0x108086" + chr(10) + "    bne.s 1f" + chr(10) + "    move #0,%ccr                | 2P, the practice course: a touch is a miss" + chr(10) + "    rts" + chr(10) + f"1:  jmp 0x{prev:X}" + chr(10) for i, prev in enumerate(wall_prev))}

not_practice:
    cmpi.b #1,0x{TWO_P:X}
    beq.s 1f
    tst.w 0x108086
    rts
1:  move #0,%ccr
    rts
no_spares:
    cmpi.b #1,0x{TWO_P:X}
    beq.s 1f
    tst.w 0x108086
    rts
1:  move #4,%ccr
    rts
tour_list:                      | in 2P the practice course's tour: the others' sign, no rules ticker
    move.w 0x108086,%d0
    bne.s 1f
    cmpi.b #1,0x{TWO_P:X}
    bne.s 1f
    lea tour0(%pc),%a0
    rts
1:  add.w %d0,%d0
    add.w %d0,%d0
    lea 0xC544,%a0
    movea.l (%a0,%d0.w),%a0
    rts
tour0: .long {", ".join("0x%08X" % v for v in tour0)}

vbl:
    jsr 0x{rom.u32(0x1294):X}
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    tst.b 0x{RULES_UP:X}
    beq.s 0f
    lea 0x108000,%a5
    jsr 0x1B45E                         | the wallpaper's scroll (its first sprite's place and height)
0:  move.b 0x{PAL9_REQ:X},%d0
    beq.s 5f
    clr.b 0x{PAL9_REQ:X}
    lea 0x{0x400000 + 9 * 32:X},%a0
    cmpi.b #1,%d0
    bne.s 2f
    lea 0x{PAL9_SAVE:X},%a1
    moveq #7,%d0
1:  move.l (%a0)+,(%a1)+
    dbf %d0,1b
    lea pal9(%pc),%a1
    lea 0x{0x400000 + 9 * 32:X},%a0
    bra.s 3f
2:  lea 0x{PAL9_SAVE:X},%a1
3:  moveq #7,%d0
4:  move.l (%a1)+,(%a0)+
    dbf %d0,4b
5:  moveq #0,%d0                        | the winner's portrait colours (and the shadow's)
    move.b 0x{PORT_REQ:X},%d0
    beq.s 9f
    clr.b 0x{PORT_REQ:X}
    subq.w #1,%d0
    add.w %d0,%d0
    add.w %d0,%d0
    lea port_pals(%pc),%a1
    movea.l (%a1,%d0.w),%a1             | (palette RAM, its colours) pairs, then 0
    move.l %a2,-(%sp)
6:  move.l (%a1)+,%d0
    beq.s 8f
    movea.l %d0,%a0
    movea.l (%a1)+,%a2
    moveq #7,%d0
7:  move.l (%a2)+,(%a0)+
    dbf %d0,7b
    bra.s 6b
8:  move.l (%sp)+,%a2
9:  rts
port_pals: .long port_pals_1, port_pals_2
{"".join(f"port_pals_{n}: .long " + ", ".join(f"0x{0x400000 + 32 * pal:X}, 0x{at:X}" for pal, at in PORTRAIT_PALS[n]) + f", 0x{0x400000 + 32 * SHADOW_PAL:X}, shadow_pal, 0" + chr(10) for n in (1, 2))}
shadow_pal: .word 0, 0x8000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
pal9: .word {", ".join("0x%04X" % c for c in PAL9)}
record_7D68:                    | in 2P: no record under the card (on after it); else the instructions replaced
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    cmpi.b #1,0x{TWO_P:X}
    bne.s 1f
    move.l #0x7D9C,(%sp)
    rts
1:  move.w #20,%d0
    move.w #26,%d1
    rts
record_8272:                    | in 2P: no record under the card (on after it); else the instructions replaced
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    cmpi.b #1,0x{TWO_P:X}
    bne.s 1f
    move.l #0x82A6,(%sp)
    rts
1:  move.w #20,%d0
    move.w #26,%d1
    rts
record_8A7A:                    | in 2P: no record under the card (on after it); else the instructions replaced
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    cmpi.b #1,0x{TWO_P:X}
    bne.s 1f
    move.l #0x8AAE,(%sp)
    rts
1:  move.w #20,%d0
    move.w #26,%d1
    rts

practice:                       | in 2P its miss passes the turn too (on to 0x99AE)
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 1f
    cmpi.b #1,0x{TWO_P:X}
    bne.s 1f
    move.l #0x99AE,(%sp)
    rts
1:  tst.w 0x108086                      | the instruction this call replaced
    beq.s 2f
    move.l #0x99AE,(%sp)
2:  rts

| ---- the title menu: 1 = 2P CHALLENGE (here), 2 = OPTIONS (on to patch 020's call after this one)
title:
    cmpi.b #1,%d0
    beq.s 1f
    rts
1:  addq.l #4,%sp                       | title_frame returns from here
    move.b #1,0x{OWN:X}                 | black (palette, OWN) until the game is under way
    jsr 0x{FIX_CLEAR:X}
    bsr.w hide_sprites
    move.b #3,0x{PAL_REQ:X}
    bsr.w wait_vbl
    move.b #2,0x{TWO_P:X}               | the game starts as ARCADE, in 2P (the rules screen first)
    jsr 0x{arcade:X}
    move #0,%ccr                        | title_frame's result: N clear
    rts

| ---- the rules screen, in the game's first frame (the vblank keeps running the wallpaper and the colour requests)
rules:
    lea 0x108000,%a5
    jsr 0x{FIX_CLEAR:X}
    bsr.w hide_sprites
    bsr.w wallpaper_on
    lea screen(%pc),%a1
    bsr.w draw_runs
    bra.w rules_choice

wallpaper_on:                           | the scrolling wallpaper, plus the tutorial box's and the heading's colours
    move.w #1,0x{BG_REQ:X}
    move.b #1,0x{RULES_UP:X}
    move.b #1,0x{BOX_REQ:X}
    move.b #1,0x{PAL9_REQ:X}
    bsr.w wait_vbl
    bsr.w wait_vbl
    lea 0x3C0000,%a0                    | the wallpaper's columns (sprites 1-30) fill 30 of their 32 tiles; the
    move.w #1,4(%a0)                    | last two still hold the title's, so copy the pattern's first two there
    move.w #0x40,%d1                    | too (tile and attribute words 0-3 to 60-63)
    moveq #29,%d3
1:  moveq #3,%d2
2:  move.w %d1,(%a0)
    nop
    nop
    nop
    nop
    move.w 2(%a0),%d0
    addi.w #60,%d1
    move.w %d1,(%a0)
    nop
    nop
    move.w %d0,2(%a0)
    subi.w #59,%d1
    dbf %d2,2b
    addi.w #60,%d1
    dbf %d3,1b
    lea 0x102160,%a0                    | the sprite heights the vblank uploads each frame (0x12E0: two 1 KB lists
    move.w #511,%d0                     | used in turn, a5 - 0x5EA0 / - 0x5AA0) still hold the title's last frame:
3:  clr.l (%a0)+                        | empty them (the game rebuilds them once it runs on)
    dbf %d0,3b
    rts

draw_runs:                              | a1 = fix runs: (VRAM, count - 1, words...) repeated, then 0
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
1:  move.w (%a1)+,%d1
    beq.s 3f
    move.w %d1,(%a0)
    nop
    nop
    move.w (%a1)+,%d2
2:  move.w (%a1)+,2(%a0)
    dbf %d2,2b
    bra.s 1b
3:  rts

rules_choice:
    moveq #0,%d4                        | the choice: 0 START, 1 BACK TO TITLE
    bsr.w read_start
4:  lea arrows(%pc),%a1                 | the arrow at the choice, blanks at the other
    moveq #{len(CHOICES) - 1},%d3
5:  move.w (%a1)+,%d1
    move.w #0x{BLANK:X},%d0
    move.w #0x{BLANK:X},%d2
    cmp.w %d3,%d4
    bne.s 6f
    move.w #0x{ARROW_TOP:X},%d0
    move.w #0x{ARROW_BOTTOM:X},%d2
6:  bsr.w cell
    addq.w #1,%d1
    move.w %d2,%d0
    bsr.w cell
    dbf %d3,5b
    bsr.w wait_vbl
    bsr.w read_start
    move.b %d0,%d6
    move.b 0x{P1_CHANGE:X},%d7
    or.b 0x{P2_CHANGE:X},%d7
    andi.b #3,%d7                       | Up / Down: the other choice
    beq.s 7f
    eori.w #1,%d4
7:  move.b 0x{P1_CHANGE:X},%d7
    or.b 0x{P2_CHANGE:X},%d7
    btst #5,%d7                         | B: back to the title
    beq.s 71f
    moveq #1,%d4
    bra.s 8f
71: btst #4,%d7                         | A or Start: this one
    bne.s 8f
    tst.b %d6
    beq.s 4b
8:  clr.b 0x{RULES_UP:X}
    move.b #2,0x{BOX_REQ:X}
    move.b #2,0x{PAL9_REQ:X}
    jsr 0x{FIX_CLEAR:X}
    bsr.w wait_vbl
    tst.w %d4
    bne.w end_game                      | BACK TO TITLE
    rts
arrows: .word {", ".join("0x%04X" % a for a in ARROWS)}    | the last choice's first, as d3 counts down

| ---- a miss: in 2P the next player's turn instead of a try off
miss:
    tst.b 0x{SYSTEM_MODE:X}
    bne.s 8f
    cmpi.b #1,0x{TWO_P:X}
    bne.s 8f
    movem.l %d0/%a0,-(%sp)
    moveq #0,%d0
    move.b 0x{CUR:X},%d0
    add.w %d0,%d0
    lea 0x{ZONES:X},%a0
    move.w 0x{ZONE:X},(%a0,%d0.w)       | this player's checkpoint kept
    lea 0x{MISSES:X},%a0
    addq.w #1,(%a0,%d0.w)
    eori.b #1,0x{CUR:X}                 | the other player
    eori.w #2,%d0
    lea 0x{ZONES:X},%a0
    move.w (%a0,%d0.w),0x{ZONE:X}
    lea 0x{CHARS:X},%a0
    move.w (%a0,%d0.w),0x{CHARACTER:X}
    move.b #1,0x{TURN:X}
    movem.l (%sp)+,%d0/%a0
    move.l #0x{RESTART:X},(%sp)         | restart, with no try taken
    rts
8:  subq.w #1,0x{TRIES:X}               | the instruction this call replaced
    bgt.s 9f
    rts                                 | on to the game over
9:  move.l #0x{RESTART:X},(%sp)
    rts

| ---- each frame of the main loop
main:
    tst.b 0x{SYSTEM_MODE:X}
    bne.w 9f
    tst.b 0x{TWO_P:X}
    beq.w 9f
    movem.l %d0-%d1/%a0,-(%sp)
    cmpi.w #8,0x{MODE:X}
    beq.s 1f
    cmpi.b #1,0x{TWO_P:X}               | out of the game: 2P is over (but not while it's starting)
    bne.w 8f
    clr.b 0x{TWO_P:X}
    bra.w 8f
1:  cmpi.b #2,0x{TWO_P:X}               | the game has started
    bne.s 2f
    move.b #1,0x{TWO_P:X}
    lea 0x{CUR:X},%a0
    moveq #(0x{FRAMES + 4:X} - 0x{CUR:X}) - 1,%d0
11: clr.b (%a0)+
    dbf %d0,11b
    move.w #0,0x{CHARS:X}               | player 1 the man, player 2 the lady (no character select in 2P)
    move.w #4,0x{CHARS + 2:X}
    move.w #0,0x{CHARACTER:X}
    move.b #1,0x{TURN:X}
    move.b #4,0x{PAL_REQ:X}             | put the title's colours back, and OWN off
    clr.b 0x{OWN:X}
    movem.l %d2-%d7/%a1-%a6,-(%sp)
    bsr.w rules                         | BACK TO TITLE doesn't return
    lea 0x108000,%a5                    | straight on to the course select, the character select's own way out
    jsr 0x{CHAR_SELECT_EXIT:X}          | (0x7734-0x777A: clears the screen, sets tries and counters, course step 20)
    movem.l (%sp)+,%d2-%d7/%a1-%a6
    bra.w 8f
2:  move.w 0x{COURSE_STEP:X},%d0
    cmpi.w #32,%d0                      | the countdown
    bne.s 3f
    tst.b 0x{TURN:X}
    beq.s 3f
    tst.w 0x{FADE:X}                    | once the course has faded in
    bne.s 3f
    clr.b 0x{TURN:X}
    bsr.w turn_box
    bra.s 8f
3:  cmpi.w #36,%d0                      | play: the player's time
    bne.s 4f
    moveq #0,%d1
    move.b 0x{CUR:X},%d1
    add.w %d1,%d1
    lea 0x{FRAMES:X},%a0
    cmpi.w #0xFFFF,(%a0,%d1.w)
    beq.s 8f
    addq.w #1,(%a0,%d1.w)
    bra.s 8f
4:  cmpi.w #44,%d0                      | a goal: this player wins
    bne.s 5f
    tst.b 0x{WINNER:X}
    bne.s 8f
    move.b 0x{CUR:X},%d1
    addq.b #1,%d1
    move.b %d1,0x{WINNER:X}
    bra.s 8f
5:  cmpi.w #20,%d0                      | after it, back at the course select: the winner screen
    bne.s 8f
    tst.b 0x{WINNER:X}
    beq.s 8f
    bsr.w winner                        | doesn't return: the game ends there
8:  movem.l (%sp)+,%d0-%d1/%a0
9:  jmp 0x{prev_main:X}

| ---- before a turn: PLAYER n / PRESS START over the course, like patch 230's pause box
turn_box:
    movem.l %d2-%d7/%a1-%a2,-(%sp)
    move.w #1,0x{VBL_BUSY:X}            | hold the game's vblank work, as the pause does
    move.b #1,0x{OWN:X}
    move.b #1,0x{PAL_REQ:X}
    move.b #1,0x{PAL_FIX:X}
    bsr.w wait_vbl
    bsr.w save_fix
    lea 0x3C0000,%a0
    move.w #32,4(%a0)
    lea box(%pc),%a1
    move.w #0x{vram(c0, top):X},%d2
    moveq #{h - 1},%d1
1:  move.w %d2,(%a0)
    nop
    nop
    moveq #{w - 1},%d3
2:  move.w (%a1)+,2(%a0)
    dbf %d3,2b
    addq.w #1,%d2
    dbf %d1,1b
    move.w #0x{vram(c0 + pcol, top + 2):X},(%a0)    | the player's number
    nop
    nop
    move.w #0x{tile("1"):04X},%d0
    tst.b 0x{CUR:X}
    beq.s 3f
    move.w #0x{tile("2"):04X},%d0
3:  move.w %d0,2(%a0)
    bsr.w read_start                    | so a Start already held doesn't count
4:  bsr.w wait_vbl
    bsr.w read_start
    tst.b %d0
    beq.s 4b
    bsr.w restore_fix
    move.b #2,0x{PAL_REQ:X}
    bsr.w wait_vbl
    clr.b 0x{OWN:X}
    movem.l (%sp)+,%d2-%d7/%a1-%a2
    rts

| ---- the winner screen: the wallpaper, the winner's portrait and its shadow, the stats box; Start -> the title
winner:
    lea 0x108000,%a5
0:  tst.w 0x{SCREEN_FADE:X}              | wait for the goal's fade-out (the vblank's, over the fix layer) to end
    beq.s 1f
    bsr.w wait_vbl
    bra.s 0b
1:  jsr 0x{FIX_CLEAR:X}
    bsr.w hide_from31                   | hide the course select's objects; the wallpaper's 1-30 stay
    move.b 0x{WINNER:X},0x{PORT_REQ:X}
    bsr.w wallpaper_on
    moveq #0,%d0
    move.b 0x{WINNER:X},%d0
    subq.w #1,%d0
    add.w %d0,%d0
    add.w %d0,%d0
    move.w %d0,%d7
    lea win_blocks(%pc),%a1
    movea.l (%a1,%d7.w),%a1
    bsr.w put_blocks
    lea win_screens(%pc),%a1
    movea.l (%a1,%d7.w),%a1
    bsr.w draw_runs
    lea win_places(%pc),%a2
    movea.l (%a2,%d7.w),%a2             | VRAM: the misses' last digit P1, P2; the minutes P1, P2
    moveq #0,%d4
1:  move.w %d4,%d5
    add.w %d5,%d5
    lea 0x{MISSES:X},%a0
    moveq #0,%d0
    move.w (%a0,%d5.w),%d0
    move.w (%a2,%d5.w),%d1
    bsr.w number
    lea 0x{FRAMES:X},%a0
    moveq #0,%d0
    move.w (%a0,%d5.w),%d0
    divu.w #60,%d0                      | seconds
    andi.l #0xFFFF,%d0
    divu.w #60,%d0                      | minutes (low word), seconds (high word)
    move.l %d0,%d7
    move.w 4(%a2,%d5.w),%d1
    cmpi.w #9,%d0
    bls.s 2f
    moveq #9,%d0
2:  addi.w #0x{SMALL:X},%d0
    bsr.w cell
    swap %d7
    moveq #0,%d0
    move.w %d7,%d0
    divu.w #10,%d0                      | the seconds' tens (low word), ones (high word)
    move.l %d0,%d2
    addi.w #64,%d1                      | skip past the ':'
    addi.w #0x{SMALL:X},%d0
    bsr.w cell
    swap %d2
    move.w %d2,%d0
    addi.w #0x{SMALL:X},%d0
    addi.w #32,%d1
    bsr.w cell
    addq.w #1,%d4
    cmpi.w #2,%d4
    bne.w 1b
    bsr.w read_start
3:  bsr.w wait_vbl
    bsr.w read_start
    tst.b %d0
    beq.s 3b
    clr.b 0x{RULES_UP:X}
    move.b #2,0x{BOX_REQ:X}
    move.b #2,0x{PAL9_REQ:X}
    bsr.w hide_sprites
end_game:                               | end the game, as patch 230's QUIT TO TITLE does
    jsr 0x{FIX_CLEAR:X}
    bsr.w wait_vbl
    clr.b 0x{OWN:X}
    clr.b 0x{TWO_P:X}
    clr.w 0x{VBL_BUSY:X}
    lea 0x108000,%a5
    jsr 0x{GAME_OVER:X}
    clr.w 0x{SCENE_STEP:X}
    move.b #1,0x{USER_MODE:X}
    move.w #0,0x{PLAYER_MOD:X}
    jmp 0x{SYSTEM_RETURN:X}
number:                                 | d0.l = 0-999, right-aligned; d1 = VRAM of its last digit
    movem.l %d0-%d2,-(%sp)
1:  divu.w #10,%d0
    move.l %d0,%d2
    swap %d2
    addi.w #0x{SMALL:X},%d2
    exg %d0,%d2
    bsr.s cell
    exg %d0,%d2
    subi.w #32,%d1
    andi.l #0xFFFF,%d0
    bne.s 1b
    movem.l (%sp)+,%d0-%d2
    rts
cell:                                   | d0 = the word, d1 = VRAM
    move.l %a0,-(%sp)
    lea 0x3C0000,%a0
    move.w %d1,(%a0)
    nop
    nop
    move.w %d0,2(%a0)
    move.l (%sp)+,%a0
    rts

put_blocks:                             | a1 = sprite blocks (see sprite_block above), then 0
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
1:  move.w (%a1)+,%d1                   | the first sprite
    beq.s 9f
    move.w (%a1)+,%d2                   | columns - 1
    move.w (%a1)+,%d3                   | rows
    move.w (%a1)+,%d4                   | SCB4: x
    move.w (%a1)+,%d5                   | SCB3: y, rows (sticky from the second column)
2:  move.w %d1,%d0
    lsl.w #6,%d0                        | SCB1: the column's tiles
    move.w %d0,(%a0)
    nop
    nop
    move.w %d3,%d6
    add.w %d6,%d6
    subq.w #1,%d6
3:  move.w (%a1)+,2(%a0)
    dbf %d6,3b
    move.w %d1,%d0
    addi.w #0x8000,%d0                  | SCB2: full size
    move.w %d0,(%a0)
    nop
    nop
    move.w #0x0FFF,2(%a0)
    addi.w #0x200,%d0
    move.w %d0,(%a0)
    nop
    nop
    move.w %d5,2(%a0)
    addi.w #0x200,%d0
    move.w %d0,(%a0)
    nop
    nop
    move.w %d4,2(%a0)
    ori.w #0x40,%d5
    addq.w #1,%d1
    dbf %d2,2b
    bra.s 1b
9:  rts

hide_from31:                            | sprites 31-380's heights to 0 (the wallpaper, 1-30, stays)
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
    move.w #0x821F,(%a0)
    nop
    nop
    move.w #349,%d0
1:  move.w #0,2(%a0)
    dbf %d0,1b
    rts

hide_sprites:                           | every sprite's height to 0, as patch 020's
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
    move.w #0x8201,(%a0)
    nop
    nop
    move.w #380,%d0
1:  move.w #0,2(%a0)
    dbf %d0,1b
    rts
wait_vbl:
    bset #7,0x{VBL_FLAGS:X}
1:  tst.b 0x{VBL_FLAGS:X}
    bmi.s 1b
    rts
read_start:                             | as patch 020's: d0 = Start newly pressed
    move.b 0x{REG_STATUS_B:X},%d0
    not.b %d0
    andi.b #0x05,%d0
    move.b 0x{START_PREV:X},%d1
    move.b %d0,0x{START_PREV:X}
    not.b %d1
    and.b %d1,%d0
    move.b %d0,0x{START_NEW:X}
    rts
save_fix:
    lea 0x{SAVE:X},%a1
    lea 0x3C0000,%a0
    move.w #0x{vram(c0, top):X},%d1
    moveq #{w - 1},%d3
1:  move.w %d1,%d2
    moveq #{h - 1},%d4
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
    lea 0x{SAVE:X},%a1
    lea 0x3C0000,%a0
    move.w #1,4(%a0)
    move.w #0x{vram(c0, top):X},%d1
    moveq #{w - 1},%d3
1:  move.w %d1,(%a0)
    nop
    nop
    moveq #{h - 1},%d4
2:  move.w (%a1)+,2(%a0)
    nop
    dbf %d4,2b
    addi.w #32,%d1
    dbf %d3,1b
    rts

box: .word {words(v for row in grid for v in row)}
screen: .word {screen_words}
win_screens: .long win_screen_1, win_screen_2
win_places: .long win_places_1, win_places_2
win_blocks: .long win_blocks_1, win_blocks_2
{"".join(f"win_screen_{n}: .word {win[n][0]}" + chr(10) + f"win_places_{n}: .word " + ", ".join("0x%04X" % v for v in win[n][1]) + chr(10) + f"win_blocks_{n}: .word {win_blocks[n]}" + chr(10) for n in (1, 2))}
"""
    base = rom.place_code(code, why="AES: 2P CHALLENGE")
    hook = lambda off: jsr(base + off)          # a call to this patch's entry at base + off
    rom.write(title_site, hook(0), expect=rom.data[title_site:title_site + 6], why="title menu: 2P CHALLENGE")
    rom.write(MISS_SITE, hook(4) + bytes.fromhex("4E71"), expect=bytes.fromhex("536D008E6E00009C"),
              why="a miss: in 2P the other player's turn")
    rom.write(PRACTICE_SITE, hook(12) + bytes.fromhex("4E71"), expect=bytes.fromhex("4A6D0086660001B4"),
              why="a miss on the practice course: in 2P a turn")
    assert rom.data[0x1292:0x1294] == b"\x4E\xB9"
    rom.write(0x1294, (base + 16).to_bytes(4, "big"), expect=rom.data[0x1294:0x1298],
              why="vblank: palette 9 for the 2P rules screen's heading")
    for i, site in enumerate(RECORD_SITES):
        rom.write(site, hook(20 + 4 * i) + bytes.fromhex("4E71"), expect=bytes.fromhex("303C0014323C001A"),
                  why="course select: no record under the cards in 2P")
    for i, site in enumerate(WALL_SITES):
        rom.write(site + 2, (base + 44 + 4 * i).to_bytes(4, "big"), expect=wall_prev[i].to_bytes(4, "big"),
                  why="wall touch: in 2P the practice course's touch is a miss")
    rom.write(TOUR_LIST, hook(40) + bytes.fromhex("4E71") * 5, expect=bytes.fromhex("302D0086D040D04041FA006E20700000"),
              why="course tour: in 2P no rules ticker on the practice course")
    rom.write(TOUR_SKIP, hook(32) + bytes.fromhex("660A"), expect=bytes.fromhex("4A6D00866600000C"),
              why="course tour: in 2P the practice course's tour can be skipped from the start")
    rom.write(LABEL_SITE, hook(32) + bytes.fromhex("6618"), expect=bytes.fromhex("4A6D00866600001A"),
              why="countdown: in 2P no PRACTICE COURSE label")
    rom.write(MISS_LOOK, hook(32) + bytes.fromhex("6606"), expect=bytes.fromhex("4A6D008666000008"),
              why="a miss: in 2P the practice course's looks like the others' (smoke, fade)")
    rom.write(FADE_PAL, hook(60) + bytes.fromhex("4E71"), expect=bytes.fromhex("303C08004EBAF5BA"),
              why="countdown fade-in: in 2P the practice course's colours to its own palettes")
    rom.write(SPARES_SITE, hook(36) + bytes.fromhex("6606"), expect=bytes.fromhex("4A6D008666000008"),
              why="spare Zap-Rods under the clock: none in 2P")
    rom.write(0x1068, (base + 8).to_bytes(4, "big"), expect=prev_main.to_bytes(4, "big"),
              why="main loop: 2P's turns and winner")
