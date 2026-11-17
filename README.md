# The Irritating Maze Plus

The Irritating Maze (SNK / Saurus, 1997) is the Neo Geo's strangest arcade game: steer a Zap-Rod through an
electrified maze without touching the walls, and get a puff of air in the face when you do. It only ever ran on its
own cabinet with a trackball, so it never came to home consoles or even a standard MVS. The Irritating
Maze Plus is a romhack that makes it playable with a joystick, and adds what a home version would have had: menus,
options, a pause menu, a two-player mode and a lot of cleaned-up screens.

It's made for the **home console (AES)**, and also works on a **standard MVS** arcade board with a joystick: there
it starts with a coin as usual and has the new course select, pause and fixes, but not yet the title menu (options
and 2P CHALLENGE). On the original trackball cabinet (its own BIOS) the game plays exactly as it did in 1997.

**Status: Beta 1.** Get it from the [itch.io page](https://powerwindows.itch.io/the-irritating-maze-plus). Feedback
welcome: open an issue here, or leave a comment on the itch.io page.

## What's changed

**Controls**
- The joystick steers the Zap-Rod: it moves like a rolled trackball, starting slow for small nudges and speeding up
  as you hold a direction.
- The A button steadies your hand (the rod moves more slowly), holding the B button allows you to look around the course, the C button shows or
  hides the hand holding the rod, and Start pauses.
- Works on UniBIOS too (as on the Analogue Pocket and MiSTer).

**Menus and options**
- Boots straight to the title, with a neon PLUS sign by the logo. Start opens ARCADE, 2P CHALLENGE and OPTIONS.
- OPTIONS: difficulty (BABY, EASY, MVS, HARD, MANIAC - BABY has no clock), rod speed, steady hand and a sound test,
  each difficulty level explained on screen.
- The instructions explain the joystick and buttons instead of the trackball.

**Pause**
- Start in a course pauses it: RESUME, RESTART LEVEL, ROD SPEED, STEADY HAND and QUIT TO TITLE.

**2P CHALLENGE**
- Two players take turns on the same course; the first to reach the goal wins.

**Courses**
- A new course select: the course maps on cards, redrawn by hand, picked with left and right.
- A smaller Zap-Rod on the easier difficulties.
- The rod's ring pulses red in the last ten seconds.
- Updated victory animations.
- Smoother obstacle animations.
- The music dips while the narration plays, so you can hear it better.

**Screens**
- A power-on intro, the character select's poses played in place.
- Screen changes no longer flash or show stray graphics, and the course fades in without a bright flash.

## Playing it

You need your own copy of the MAME ROM set **irrmaze** (The Irritating Maze / Ultra Denryu Iraira Bou). No game data
is included here.

**The easy way:** the patcher on the [itch.io page](https://powerwindows.itch.io/the-irritating-maze-plus) runs in
your browser (your files are never uploaded). Drop in `irrmaze.zip` or a Darksoft-style `irrmaze` folder, pick
RetroArch, MAME, BackBit Platinum, MiSTer or Analogue Pocket, and download a zip laid out for that system, with a
README of where it goes and which settings to use.

**By hand:** the xdelta download (on the itch.io page) has a patch per file, the original files' checksums and the
same per-system steps. The patches change these files of the set; check yours match before patching:

| File | Size | CRC32 | SHA-1 |
|---|---|---|---|
| 236-p1.p1 | 2097152 | 4c2ff660 | 4a0cbd09044648ff9ec67723729f16d422c34bda |
| 236-s1.s1 | 131072 | 5d1ca640 | 40a9668a1742a44597a07ce72273d17119815637 |
| 236-m1.m1 | 131072 | 880a1abd | 905afa157aba700e798243b842792e50729b19a0 |
| 236-c1.c1 | 4194304 | c1d47902 | 727001c34f979226fc8f581113ce2aaac4fc0d42 |
| 236-c2.c2 | 4194304 | e15f972e | 6a329559c57a67be73a6733513b59e9e6c8d61cc |

The sound files aren't patched, but check them too: an older bad dump of 236-v2 makes some jingles crackle.

| File | Size | CRC32 | SHA-1 |
|---|---|---|---|
| 236-v1.v1 | 2097152 | 5f89c3b4 | dc8fd561cf8dfdd41696dcf14ea8d2d0ac4eec4b |
| 236-v2.v2 | 1048576 | 72e3add7 | dc49f05274693255416d2e41ecc088027b798eb9 |

Play it on the Neo Geo **AES** (home console) or a standard **MVS**: in MAME, `mame aes -cart irrmaze` or
`mame ng_mv4f -cart1 irrmaze`. In RetroArch's FinalBurn Neo, set the BIOS to UniBIOS: its default for this game is
the trackball cabinet's BIOS, which plays the original.

**Tested on:** a real Neo Geo on a CRT (BackBit Platinum, AES and MVS modes), the Analogue Pocket (AES and MVS
modes) and MAME on macOS. RetroArch and MiSTer should work but are untested - reports welcome.

## Building from source

You need Python 3, [ngdevkit](https://github.com/dciabrin/ngdevkit)'s `m68k-neogeo-elf` toolchain, and MAME.

1. Put the MAME set `irrmaze.zip` and the BIOS `neogeo.zip` in `roms/` (and `aes.zip`, ngdevkit's open AES BIOS,
   for the home version).
2. `./run.sh` builds `build/` from `patches/*.py` and plays it in MAME as the AES (`--std` a standard MVS, `--mvs`
   the trackball cabinet). `python3 tools/hackbuild.py` just builds.

- `patches/` - one file per change, applied in name order; each starts with what it does and how (the game's
  addresses, what was found).
- `tools/hackbuild.py` - the build. `tools/regress.py` plays every test clip and save headless and compares the
  screens with the last accepted run (`tests/clips.txt`). `tools/release.py` makes the release files: the web
  patcher (`tools/web_patcher/`), the xdelta patches and each system's package.
- `art/` - redrawn graphics the patches read. `docs/` - notes on the game's internals.

## Credits

The Irritating Maze Plus by Loren Vanderbilt III. The Irritating Maze © 1997 SNK / Saurus - no game data is
included; you need your own copy.
