# The Irritating Maze - code map

What's been found in the program ROM, with how it was found. (Started 2026-11-06.)

- Program ROM 2 MB: 0x000000-0x0FFFFF fixed, a 1 MB bank after (in Rom.data from 0x100000; code there can't be
  called directly). Unused 0xFF in the fixed half: 0x0F0FF6-0x0FFFFF (~60 KB, FREE_START 0x0F1000), smaller runs at
  0x0E938C (23 KB), 0x0242E4 (15 KB), 0x044B02 (13 KB). Vectors: vblank 0x1272, timer 0x1346.
- Both builds start in MAME: the arcade one (`mame irrmaze`, with MAME's trackball and control-panel artwork) and the
  AES cart (`mame aes -cart irrmaze`: its warning screen and attract mode). How the game reads the trackball, and
  what the AES gives it instead, is the first thing to find.

## Input: the trackball (2026-11-06)
- **The game never reads the trackball.** The cabinet's own BIOS (236-bios.sp1, its routine at 0xC1B1F6, run from
  SYSTEM_IO 0xC0044A, called by the vblank at 0x1292) reads it and fills the game's input area every frame
  (found with a write tap on 0x10FD80-0x10FEFF in `mame irrmaze`):
  - X counter: bit 0 of 0x380001 = 0, read 0x300000 (inverted); Y: bit 0 = 1. 8-bit counters that roll over.
  - 0x10FE02 X record: previous, now, **movement this frame (0x10FE04, signed, + = right)**, 0x10FE05 the counter's
    high nibble (for coarse direction bits). 0x10FE08 the Y record (**0x10FE0A, + = down**).
  - Buttons: 0x340000 bits 4-7 (inverted) = P1 button 1, P1 button 2, P2 button 1, P2 button 2 (MAME's
    `:edge:irrmaze:BUTTONS`), plus direction bits from the movement, into a BIOS-style record at 0x10FE0E
    (status, previous, **now 0x10FE10**, **new presses 0x10FE11** - low nibble = coarse direction bits -, repeat,
    timer) and a second at 0x10FE14 (shifted 2: P2's buttons in bits 4-5). Copied on to 0x10FD94 / 0x10FD9A (the
    BIOS's P1 / P2 bytes) and 0x10FEE8 / 0x10FEEE.
  - The game reads only 0x10FE04, 0x10FE0A, 0x10FE10, 0x10FE11 of it (a read tap, AES, attract + a game).
  - The game ROM has a byte-for-byte copy of the BIOS routine at 0x5BA (start) / 0x5D8 (every frame) that nothing
    calls (helpers: 0x6D0 counter -> movement, 0x722 / 0x77E movement -> direction bits, 0x688 a button record).
  - On the AES nothing fills the area (the console BIOS doesn't know it): the Zap-Rod never moves. 0x10FEE8+ is the
    console BIOS's own RAM there - don't copy into it.
- **Movement:** 0x1844E copies 0x10FE04 / 0x10FE0A (sign-extended) to 0x10A7CE / 0x10A7D0 (dx, dy) and the buttons
  to 0x10A7C6 (button 1: 1 held, -1 the frame it's pressed) / 0x10A7C8 (button 2) / 0x10A7C4 (either). Users of
  dx / dy: 0x4906 (the maze: doubled, plus a fraction 0x10A7EA), 0xC11C (a pointer, 1 step = 1 px), 0x181BE ...
  Button A + trackball = look around the course (the instructions).
- **0x108001 = a developer debug flag** (tested in dozens of places, 0 in both machines): with it set, 0x1844E
  steers from the BIOS joystick byte 0x10FD96 instead (a direction table at 0x1840E, 1 px a frame, C / D x2 / x4 /
  x8) - the developers' joystick mode. Not used: it switches on much else too.
- **Patch 010 (aes-joystick):** the vblank's SYSTEM_IO call goes through new code that on the AES fills the area
  from the joystick (a virtual trackball, speed knobs in the patch; RAM 0x10FE00 speed, 0x10FE06 / 0x10FE0C
  counters - gaps only the BIOS's power-on clear writes). P1 A / B = the cabinet's P1 buttons, P2 A / B its P2
  buttons; P1 C / D unused so far.

## Settings (soft dips) and difficulty (2026-11-07)
- 0x36C0 copies the BIOS's soft-dip bytes (0x10FD84 + n) to game words: 0x10FD88 LEFT PLAYER -> 0x108002,
  FD89 CONTINUE -> 108004 (>99 = -1, no limit), FD8A DEMO SOUND -> 108006, FD8B INSTRUCTION -> 108008, FD8C GAME
  LEVEL -> 10800A, FD8D COURSE BONUS -> 10800C, FD8E BONUS TIME -> 10800E (table 0x377C), FD90 LEVEL/CREDIT ->
  108010 (table 0x376C), FD91 STAGE SELECT -> 108014, FD92 PRACTICE -> 108016. (Names from the arcade manual.)
- GAME LEVEL (0-7 = levels 1-8) through the table at 0x3788 (2 words each): 0x108018 = a difficulty rank, starting
  at the level; 0x10801C = time added to each course's limit: +30 +20 +10 0 -5 -10 -15 -20 (seconds, presumably;
  used at 0x20230 etc.: limit = base + this + 50).
- The rank 0x108018 rises during a game (0xA2B8 / 0xA2EC: +1, capped at 7) and picks per-rank parameter sets for
  things in the mazes (0x213D6 and next: 8 bytes per rank - likely the moving obstacles' speeds / timings; to check).
  (2026-11-15, read from the code - docs/difficulty.xlsx) About 30 obstacle routines (0x21368-0x224AE, the course
  object lists 0x428E2 / 0x429F2) start from a standard value (= rank index 3, level 4) and, while 0x108048 is set
  and 0x10E001 bit 1 clear, take a rank-indexed one instead. 0x108048 is set at a course's start (0xB42E / 0xC442)
  and cleared by a miss (0x90B4), which also drops the rank by 1, not below GAME LEVEL (0x90B8-0x90CA). Clearing a
  course raises it by 1 (0xA2B8 / 0xA2EC, in the GOAL!!! routine 0x9E6E). Not yet watched happening in play.

## Game flow (2026-11-07 - found for patch 020 menus)
- **Main loop** 0x1042: `bset #7,0x104B6F` then waits until the vblank clears it (0x1048-0x104E = regress.lua's
  VBLANK_WAIT); then 0x15DC, 0x1940 (starts a game once PLAYER_START marked player 1: mode 8), 0x1598, sets
  0x10A87E (the vblank skips its screen, palette and sound work while it's set), runs the mode handler from the
  word **0x102960** (table 0x109C: 0 = attract 0xE070, 4 = 0xDC40 (arcade's title after a coin), 8 = a game 0x43C6),
  clears 0x10A87E. USER requests (table 0x1000): 0 0x10F6, 1 0x117C, **2 0x10A8 = the attract starts** (clears
  0x100000-0x107FFF, init 0x3308 incl. the soft-dip copy, mode 0 - at power-on and after every game), 3 0x118C.
- **Attract** (mode 0, step word **0x10805E**, wait counter 0x108074): 8 = a scene player (0x144DA, step
  **0x108052**: 0-24 the health warning, 28-248 the intro scenes, 252 a wipe, **256-288 the logo**); 12 / 16 the
  title's set-up; **20 the title** (PRESS START, a countdown 0x10A8A0 from 600, `subq` at 0xE56A); 24 a demo game;
  28-36 the rankings; then round to 0 (the warning again). Jumping the scene player to step 256 from anywhere in
  the attract gives a clean logo + title.
- **Messages on the title**: the vblank (0x1766) prints an 18-character message at fix row 22, columns 11-28 when
  0x10804A is non-zero (1 blank, 2 PRESS START BUTTON, 3 INSERT COIN, 4 FREE PLAY; table 0x17C8), then clears it;
  the title sets it every frame (the blink).
- **Font** (fix): tile 0xF00 + character - '0' ('0'-'9', ':;<=>?', 'A'-'Z'; space = 0xF10; 0xF2B (c), 0xF2C /),
  colours 1-7 (a gradient down the letter) and 14 (outline); 0xFF0 is solid colour 15. On the title fix palette
  15 is orange, 11 / 12 white-blue, 6 near black. Copyright line: font 0x300+, palette 15.
- **Sound**: 0x243C, d0 = number: 0x8000 + n = list 0x2498 n (driver commands 0-5, music / jingles 6-29), else list
  0x24D4 n (129 effects). Each is two bytes (high, low) queued (0x10E202 / 0x10E286) and sent to the Z80 by the
  vblank (0x1364 then 0x13F6). The attract starts with 0x8001 (stop?).
- **A game** (mode 8): **0x10806E** phase (0 = the course steps; 4-24 a screen change), **0x10806C** course step:
  4 instructions, 8-20 character / course select, 24 the course tour, **28 the course set-up** (per course,
  0x704A), **32 the countdown** (0xCDD0), **36 play** (0x47D8), **40 a miss** (0x8E92). Course **0x108086** (0
  practice, 1 novice, 2 expert, 3 professional); 0x108092 bits = courses taken (the course select skips them;
  0 at power-on / 1 without practice). Phase 4 + step 28 restarts the course cleanly (what a miss does after its
  animation).
- **Walls**: the Zap-Rod stays mid-screen and the maze scrolls (0x10A7CE / D0 doubled + 0x10A7EA). 0x17590 tests
  the wall; four copies of the check (0x4994, 0x4C60, 0x4E1C, 0x5010): course 0 (practice) pushes the rod back
  (0x108EA6 / AA <- the previous position 0x108EAE / B0), sets a 120-frame grace (0x108EC6) and counts a touch off
  **0x108090** (3 at a course start; at 0 the try ends); any other course: a miss (sound 6, step 40).
- **The end of a game** (0xBA1E / 0xBE70): `jsr 0x363E`, clear 0x108052, USER_MODE 0x10FDAF = 1, PLAYER_MOD
  0x10FDB6 = 0, `jmp 0xC00444` (SYSTEM_RETURN) -> the BIOS's request 2.
- **Spare RAM**: 0x10E350-0x10EFFF never written in an attract + a game (patch 020 uses 0x10EA00 and 0x10EF00).
- **Tries** 0x10808E (from LEFT PLAYER 0x108002 at the start; -1 at 0x99AE). **Extra tries** (2026-11-07): zone-end
  events per course (table 0x12D1E by course, then by zone 0x108088): Novice zone 0 -> step 80 (0x5AEE: the
  reels / wheel spin, +1 try at 0x5C62 when its counter reaches 180), Novice zone 1 -> step 88 (0x5196: three
  objects spin 300 frames, then +1 try at 0x5410 with sound 116), Expert zone 1 -> step 84 (0x543C, +1 at
  0x5A9C); none on Practice / Professional. None of them checks a result: reaching the spot always pays one try
  (the slot machine's "three kittens" is scripted). 0xAC4C: +1 at a course's end, depending on COURSE BONUS
  (0x10800C).
- **Course select** (step 20 with STAGE SELECT, 0x833E; its state 0x10A8A0: 16 = input 0x8804): cursor 0x10A89A
  (0-48, 16 a course, moved by -dx at 0x8834), 0x10A898 = course * 8; the four course pictures are objects 1-4
  (0x100080 + 128 n: +12 x (centre), +14 y 160, +16 / +18 size (255 = full; the sprite builder scales the pieces
  and shrinks the tiles), +11 bit 1 = hidden, +1 = order via 0x1E5C, from tables 0x8E72 / 0x8E32 / 0x8E52 /
  0x8E12); the grey frame is object 0 (x 160, y 144, order 241), the arrows objects 6 / 7 (242). Order: the
  list is sorted by it each frame (0x1D84), higher on top; 128+ is a front group (the frame, arrows, the front
  course). The TIME counter is the shared 0x13BE8 (0x10A856 seconds, 0x10A858, 0x10A85A frames to a step).
- **Fix-layer scripts**: `fp = script; jsr 0x1F14` queues one (0x102968, up to 32); the vblank runs them (0x1F32):
  a VRAM address word, then runs: a control byte (bit 7: a byte of address change follows - bits 7-3 signed x 4
  columns... + bits 1-0 rows; bit 6: a byte of tile-number high part follows; bits 5-0: count - 1), that many
  tile low bytes; a 0 byte ends the script. Pointer table 0x2D708: +0 the TIME box (0x3186E), +8..+20 the
  course names (0x30E6E / EA6 / EDE / F16, row 13), +0x7C the TIME box's clear (0x31802); the course select's
  COURSE SELECT is 0x3219A (row 8; 0x317AE is a copy used elsewhere). The TIME digits: 0x13BE8 each frame.
- **Button B** (from the Japanese instructions, script #12): hides the hand holding the Zap-Rod (0x108EEC bit 0,
  toggled at 0x4850 / 0xCDD0 from 0x1087C8). But the shipped ROM never shows that hand in play: 0x18A4A picks the
  Zap-Rod object's look from table 0x18AC0 (+16 = a see-through white-outline hand, +4 = no hand, +28 = a miss)
  and has `move.w #16,d0; move.w #4,d0; tst.w 0x108EEC; beq; move.w #4,d0` - always 4, so B changes nothing.
  0x18A50 = 0x0010 restores it. (The solid hands in the countdown are a different thing.)
- **Text**: all fix-layer text is in the 191 scripts of table 0x2D708; the region (0x10FD83, 0 = Japan) picks a
  Japanese script at 38 places (`move.w #jp,d0; tst.b 0x10FD83; beq; move.w #en,d0`). docs/text_export.xlsx lists
  them side by side.

## Voices / narration (2026-11-12)
- **Narration events**: 0x2115A (d1 = event 0-36) plays the event's voice from table 0x211A4 (Japanese region) or
  0x211EE (other regions; 0xFFFF = none: events 3, 4, 5, 10 have no English line). Effect numbers (0-based, list
  0x24D4) - the voices are the 0x18xx commands. Some are shared by both tables (events 0-2, 6, 9, 33-36).
- **Who triggers them**: the mazes' trigger zones (RAM list 0x10A364, 16 bytes each: x, y, w, h, ..., +12 = event
  with bit 14 set = a voice), checked at 0x1FF10 -> 0x1FF8A. Per course: practice 11-13; novice 15-20; expert 11,
  12, 21-28; professional 29-32. Plus direct calls (0x243C with a fixed number): effects 35-37 (events 0-2), 41
  (6), 44 (9), 79 / 80 (English events 7 / 8), 86 (event 14's English line).
- **Switched off by the developers**: the cutscene scripts' "play a sound" (command 0x8004 -> 0x12632 -> 0x12738,
  an rts before the real code at 0x1273A) and "play a voice" (0x8008 -> 0x12636 -> 0x1274E, an rts before
  0x12750, which plays from the same two tables). Six voice commands sit in the course tour scripts (0x28212 ev 15,
  0x28296 ev 17, 0x28472 ev 11, 0x284F2 ev 21, 0x28596 ev 23, 0x28862 ev 27) - lines the mazes play anyway.
- **The win's voice**: the goal (0x9F84) plays effect 68 + course (0x1860-0x1863 = VOICE 26-29, events 33-36's
  lines): the course's congratulations, in both regions. (Corrected 2026-11-12: first thought never played.)
- **Never played**: the
  Japanese-only lines of events 3, 7, 8, 14 (0x185C, 0x1843, 0x1844, 0x182F). Some triggered English events'
  voices are silent (16, 24, 30, 32 -> 0x184D, 0x1855, 0x185D, 0x185F; also their Japanese ones).

## Sound driver (Z80, 236-m1; 2026-11-12 - for music ducking under voices)
- Disassembly: MAME's debugger headless (`-debug -debugger none`, Lua `manager.machine.debugger:command("dasm
  FILE,0,0x10000,1,:audiocpu")`) - no Z80 disassembler is installed.
- NMI 0x0066 reads port 0 into a 64-byte queue 0xFE4A (write index 0xFEB1, read 0xFEB0; bytes 1 / 3 / 0x10 handled
  at once). The main loop 0x0133 takes one byte: 0x42EC[cmd] = kind (1 -> 0x0C6D: a jump table of commands 0x00-
  0x1C; 2 -> 0x01EC (0x20 + next byte = a song); ...). A two-byte request from the 68k (0x243C lists) is a command
  byte then a parameter byte (0x0201 waits for it).
- Commands seen: 0x04 (0x0EE9) silences and leaves the music / effects flags off (the attract's 0x8001 - mutes the
  later sound test), 0x0A + speed (0x0F5B) = fade the music out (0xFE27 = 1, speed at 0xFAC0), 0x0E + n (0x0FE4)
  = YM timer B (tempo), 0x11 (0x0F7A) = cancel a fade, 0x20 + n = play song n.
- The fade (0x1A67, each tick while 0xFE27 is set): 0xFABF (FM attenuation, added to the TL; a song sets it from
  its header at 0x134F) +1, the six ADPCM-A music channels' volumes (0xFD2C + 16 n, +2) -1, 0xFD8E -5, 0xFAC5 -6;
  the song ends past 0x5A. Voices are ADPCM-A effects (0x18xx), on top: nothing lowers the music for them.
- Poking 0xFABF +12 / 0xFAC5 -60 mid-song quietened one song by about a third and another not at all (notes
  already sounding keep their volume; drums are ADPCM-A) - a proper duck has to act where the driver writes each
  channel's volume to the chip.
- **The win's sounds** (novice, 2026-11-12): crossing the line queues 0x0A20 (fade the music); the next frame 0x000F,
  0x0020 (stop), the congratulations voice, then the win jingle (music 0x2030). No sound effect for the crossing.
- **Ducking (patch 030)**: driver commands 0x0B / 0x0C set / clear 0xFE00; hooks at 0x2BB6 (FM total level out,
  every carrier volume - 0x2B2E sets them through the 0x2BF8 algorithm table), 0x2BD8 (ADPCM-A music channel
  volume, 0x2BC7), 0x2B1D (port A writes: register 0x1B = ADPCM-B volume); code at 0x2D60 (zeros past the
  0x2C54 table, never read). The 68k: 0x243C -> a voice sets a request + its length; 0x1364 (the vblank's sender)
  sends the byte between commands (like the game's own 0x7F there, a5 + 0x631A).

## Instructions (course step 4, 2026-11-14 - patch 070)
- Text: a list of fix-script numbers typed into a box, 180 frames each (0xD864): 0xD908 on a Japanese console
  (0x98, 0x98, 0x2B, 0x9A, 0x9B, 0x2B), 0xD916 elsewhere (157, 158, 0x2B, 159, 160, 0x2B); 0x2B = the empty box.
  0xD8F8 (9, 9, 0x2B, 10, 11, 0x2B, 0x2B) is used by nothing. Script layout (157): VRAM 0x7056, a 7-row box -
  border (palette 6, tiles 0x5EE / 0x5EF / 0x5FE / 0x5FF, corners 0x600 / 0x610), line 1 top + bottom halves, a
  gap row, line 2 top + bottom, border; 34 characters a line. The tall font: tile 0xE00 + (A-O 0xC1-0xCF, P-Z
  0xE0-0xEA; bottom half + 0x10), space 0xC0, '-' 0xEB / 0xFB, '"' 0xED / 0xC0, '.' 0xC0 / 0xFD.
- Demo: an action table at 0xD924 (8 bytes: routine, parameter, frames; each called every frame of its time + 1;
  -1 ends the instructions, 0xD89A). Actions: 0xDBA0 / 0xDBC2 move the rod, 0xDA58 / 0xDA6C look on / off,
  0xDBFE the camera, 0xDC32 sets 0x108EC4 (0 = wait), 0xDC38 sets the hand flag 0x108EEC (unused: the Japanese
  B panel's), 0xDA34 on the ending. Any button (0x10A7C4) skips the instructions.

## The ending (2026-11-14)
- After Professional: step 56 (the cabinet's card dispenser prize, 0x10FE26 / 0x10E340), step 60 = a cutscene
  (0x1635E, state 0x10805A: 56-76 THANK YOU FOR YOUR PLAYING, END, PRESENTED BY ...; 80 picks sprites 176-195,
  84 the figure's tiles (table 0x2CD06, 20 x 32, palette 0x10) + palettes (0x202E), 88 places them, 92 scrolls
  it up 1 px a frame with random zaps (sounds 110 / 114) to the top, 96-116 down again with GAME OVER (sprites
  1-20, palettes 0x40-0x61)), then step 68 (white) -> the attract. Running out of tries never shows it (40, 48,
  64, 0). One ending only, as far as the code shows.
  Its flags 0x108058 (on) / 0x10805A (state) stay set afterwards; left on, the instructions' course draws black
  (patch 080 clears them).
- **Palette banks at start-up** (2026-11-14): the attract's start-up (0x3308) calls 0x17EB8 (0x3350): bank 0 on
  screen (0x3A001F), its 16 palettes from 0x4800C + the rest and the backdrop 0x7DDD, then bank 1 (0x3A000F). Run
  mid-picture, bank 0's old gray backdrop showed as a band (after the ranking screen); patch 080 blacks it first.
  Patch 040's 0x1566 backdrop (0x7777 then 0x8000) is now one write (080).
- The title's logo: scenes 256-288 (0x14506 table): 256 clears, 264 palettes (0x25D6), 268 the logo's objects
  (0x14D36), 272 fades it in (0x16036 = only the backdrop's pulsing navy, written straight to 0x401FFE; 0x160E0 the fix dither), 276 places it, 280 the backdrop to white, 284 the fix-layer
  dither wipe (0x16172), 288 ends. The title's message (0x10804A: 1 blank, 2 PRESS START BUTTON, 3 INSERT COIN,
  4 FREE PLAY; texts at 0x17C8) is drawn by the vblank (0x1766) at 0x7176 each frame it's set.

## Course finishes and the title logo (2026-11-15)
- **Each course's finish is its own trigger-zone handler**, called from 0x1FFB6 (the zone's saved d1 at 10(sp) of the
  handler): practice 0x200FA, novice 0x202DC, expert 0x207B6, professional 0x20C72 - each `move.l 0x108EB2,<rec>`
  (0x10A7F6 / 7FA / 7FE / 802), keeps the best time (0x10E31C + 12 per course), then course step 44. Patches 060 / 140.
- **The title logo is one picture**: 120 tiles (0x8D1A-0x8D8C) in sticky sprites 220-234, one palette (184), the TM
  included. The parts keep to their own colours: 1 black backing, 2 green grid, 3-4 red map, 5-9 the title text,
  10-15 the frame (greys + white) - so each recolours alone, but parts are missing where another covers them.
  Split out in art/title_plus/logo_parts/.
- **Buttons in a maze (console, patch 130)**: patch 010's P1 button record goes through patch 020's p1_buttons, then
  patch 130's: B -> the cabinet's button 1 (hold = the game's look mode, 0x4890), C -> button 2 (the hand toggle).
