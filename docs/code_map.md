# The Irritating Maze - code map

What's been found in the program ROM, with how it was found. (Started 2026-11-06.)

- Program ROM 2 MB: 0x000000-0x0FFFFF fixed, a 1 MB bank after (in Rom.data from 0x100000; code there can't be
  called directly). Unused 0xFF in the fixed half: 0x0F0FF6-0x0FFFFF (~60 KB, FREE_START 0x0F1000), smaller runs at
  0x0E938C (23 KB), 0x0242E4 (15 KB), 0x044B02 (13 KB). Vectors: vblank 0x1272, timer 0x1346.
- Both builds start in MAME: the arcade one (`mame irrmaze`, with MAME's trackball and control-panel artwork) and the
  AES cart (`mame aes -cart irrmaze`: its warning screen and attract mode). How the game reads the trackball, and
  what the AES gives it instead, is the first thing to find.
