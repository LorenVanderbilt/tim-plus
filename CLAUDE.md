# The Irritating Maze Plus - working notes for Claude

A polish hack of **The Irritating Maze / Ultra Denryu Iraira Bou** (SNK / Saurus, 1997; MAME `irrmaze`,
236), for the Neo Geo AES - the user's fourth hack, after Blue's Journey Plus (`../blues-journey-plus`), Joy Joy Kid
Plus (`../jjk-plus`) and Riding Hero Plus (`../rh-plus`), built the same way. Look at those (their patches, tools,
TODO.md, git history) whenever a technique is mentioned there.

**What's special:** it was an MVS-only release played with a **trackball** (and two buttons), on its own BIOS
(`236-bios.sp1`). A home console has neither - so an AES version needs joystick control (MAME's software list notes
that UniBIOS 2.2+ offers joystick play as a cheat: it can be done). Expect that to be the heart of the "Plus".

**Shared Neo Geo findings: `../neogeo-notes/findings.md`** - what all the user's Neo Geo projects have learned
(real hardware, flash carts, MAME, tools). Read it before starting work. When you learn something that would help
any Neo Geo project (not just this game), add it there, dated - and correct it where it's wrong. (It's its own git
repo with no remote, by the user's choice: commit only when the user says so, never push.)

## How the project works
- `roms/irrmaze.zip` (the user's, from their Downloads, never modified or committed - NOT MAME's naming: `.bin` files, the program ROM in the CPU's order; `tools/hackbuild.py`'s SOURCE translates it to MAME's names and layout. 236-p1 (2 MB, banked: the CPU's fixed 0x000000-0x0FFFFF is the second half of MAME's file - `P_SPLIT`), s1, m1, v1, v2 (another dump than MAME's: "wrong checksum", runs), c1-c2 (4 MB each), 236-bios (its own MVS BIOS). MAME's Japanese hack BIOS isn't in it). `roms/neogeo.zip` (MVS BIOS), `roms/aes.zip` (ngdevkit's open AES BIOS). `tools/hackbuild.py` applies
  `patches/*.py` (in name order) and writes `build/roms/` (MVS) and `build/aes/` (AES cartridge + software list - MAME's
  own entry with the patched files' checksums). `./run.sh` builds and plays (AES by default; `--mvs` the arcade).
- A patch = `NAME`, `DESCRIPTION`, `apply(rom)`: `rom.write(addr, new, expect=old, why=...)` (fails loudly if the
  ROM doesn't match), `rom.place_code(asm)` (assembles into free space, 0x0F1000+ - ~60 KB at the fixed half's end), `rom.alloc`, tile helpers.
  `tools/free_space.py` lists the original's unused space and vectors.
- Saves: `sta/aes/NAME.sta` (MAME save states, not committed - none yet). Tests: `tests/clips.txt` +
  `tests/clips/*.inp`, replayed by `python3 tools/regress.py` (crash check of every save + recorded clips, compared
  with a baseline; a test can start from power-on - save "boot"). `tools/regress.lua`'s FAULT / VBLANK_WAIT aren't
  known yet for this game - fill them in once found.
- Test on the user's BackBit flash cart: `../neogeo-notes/findings.md` ("Flash carts").

## Known so far (2026-11-06 - see docs/code_map.md)
- Program ROM 2 MB: 0x000000-0x0FFFFF fixed, a 1 MB bank after (in Rom.data from 0x100000; code there can't be
  called directly). Unused 0xFF in the fixed half: 0x0F0FF6-0x0FFFFF (~60 KB, FREE_START 0x0F1000), smaller runs at
  0x0E938C (23 KB), 0x0242E4 (15 KB), 0x044B02 (13 KB). Vectors: vblank 0x1272, timer 0x1346.
- Both builds start in MAME: the arcade one (`mame irrmaze`, with MAME's trackball and control-panel artwork) and the
  AES cart (`mame aes -cart irrmaze`: its warning screen and attract mode). How the game reads the trackball, and
  what the AES gives it instead, is the first thing to find.

## Standing rules (the user's - follow them)
- **Commit and push only after the user confirms.** Commit messages end with the Co-Authored-By line the session
  gives. Keep `TODO.md` up to date as work is done - but it's local for now (git-excluded via `.git/info/exclude`,
  the user's call 2026-10-25): never commit it until they say so. (No GitHub remote yet - the user sets one up if they want it.)
- **AES first, MVS untouched.** The AES version is the target. Avoid changing anything that affects the MVS game
  (gate new code on the machine type), and tell the user before a change does. Anything that permanently changes
  the AES version - overwriting text or graphics, rather than adding new ones in free space - needs their permission
  first.
- **New code goes in the newest / last patch. Never grow or shrink an earlier patch's code**: it moves every later
  patch's placed code, and save states (which hold return addresses into patch code) crash. Hook an old patch's
  code from the newest patch instead (find its bytes in the ROM by pattern). Text edits must keep their lengths.
- **After the user confirms a change, set up a test**: they record `./run.sh -- -state SAVE -record NAME.inp`; copy
  it from `recordings/` to `tests/clips/` (MAME overwrites recordings), add a line to `tests/clips.txt`, run
  `python3 tools/regress.py --no-build --accept NAME`, commit after they say yes.
- **The user checks visuals.** For how something looks or moves, give them `./run.sh` commands, PNGs or GIFs
  (`open -a Safari file`) rather than long headless capture loops - they're token-conscious. Mock things up
  (Python-rendered GIFs over a screenshot, or live Lua previews) before big ROM work, and get their pick.
- **Missing saves: let the user make them** - say none exists, offer the nearest; don't build Lua room-jump hacks.
  (Saves can also be made after a give-item Lua script: Shift+F7 in MAME.)
- **Show unused art before overwriting it**; free tiles only after proving them unused (census + poison test).
- **Keep charming translation quirks** - fix real typos, but ask before "correcting" fan-favourite oddities.
- **Write colours only at the start of the vblank** (palette writes during the picture streak on real hardware, not
  in MAME - `../neogeo-notes/findings.md`).
- **"Secret todo" items go in `SECRET_TODO.md`** (git-excluded via `.git/info/exclude`) - never in TODO.md, commits
  or public docs.
- Use the session scratchpad for temporary files, not /tmp. Ask before fixing anything unasked-for that changes the
  game's feel; explain options plainly (the user isn't a programmer - no jargon dumps), recommend one.
- Never send the user's email anywhere.

## Working style that went well
- Find code fast with headless MAME + Lua (write taps, VRAM reads, input injection) - see the shared findings.
- Tunable knobs at the top of each patch (with comments in plain words), and live tuning probes in
  `tools/probes/` (e.g. a Lua script that pokes ROM values with `write_direct`) so the user can feel values before
  they're fixed.
- Before a full regression, confirm the build said "Built ..." (a patch mismatch otherwise leaves the old build).
- zsh doesn't word-split `$var` - use `${=var}` (it once silently broke a whole test loop).
