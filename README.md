# The Irritating Maze Plus

A polish hack of SNK / Saurus's **The Irritating Maze** (1997) for the Neo Geo AES (and MVS), as
patches applied to the original ROM set - which you supply; it is not included.

- Put the original `irrmaze.zip` in `roms/`, with `neogeo.zip` (BIOS) and `aes.zip` (ngdevkit's open AES BIOS,
  from any ngdevkit example's `build/rom/`).
- `./run.sh` builds `build/` from `patches/*.py` and plays it in MAME as the AES (`./run.sh --mvs` for the arcade).
- Needs Python 3 and ngdevkit's `m68k-neogeo-elf` toolchain (for patches that add code).
