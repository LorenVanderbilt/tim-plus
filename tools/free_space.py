#!/usr/bin/env python3
"""The original program ROM's unused space and its vectors - what tools/hackbuild.py's FREE_START comes from.

    python3 tools/free_space.py

Lists the runs of unused 0xFF bytes (1 KB and up) in the CPU's view of the program ROM (the fixed 0x000000-
0x0FFFFF; a banked half after it), the biggest first, and the 68000 vectors the work starts from (reset, the vblank
and timer interrupts). New code goes in a run's tail, rounded up past the last used byte - check the run isn't data
that only looks blank (a table of 0xFF) before using it: a write tap on it over a few saves, or the poison test.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hackbuild as h  # noqa: E402


def main():
    _, rom = h.load_original()
    d = rom.orig
    runs, start = [], None
    for i in range(0, len(d), 2):
        blank = d[i] == 0xFF and d[i + 1] == 0xFF
        if blank and start is None:
            start = i
        if not blank and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(d)))
    print("program ROM: %d KB (CPU view%s)" % (len(d) // 1024, ", banked half after the first MB" if h.P_SPLIT else ""))
    for a, b in sorted(runs, key=lambda r: r[0] - r[1]):
        if b - a >= 0x400:
            print("  0xFF run 0x%06X-0x%06X  %d KB%s" % (a, b - 1, (b - a) // 1024,
                                                       "  (banked: not callable directly)" if a >= 0x100000 else ""))
    u32 = lambda a: int.from_bytes(d[a:a + 4], "big")
    print("vectors: reset 0x%06X, vblank (0x64) 0x%06X, timer (0x68) 0x%06X, cold boot (0x6C) 0x%06X" %
          (u32(4), u32(0x64), u32(0x68), u32(0x6C)))
    print("header: NGH 0x%04X, entry points USER 0x%06X PLAYER_START 0x%06X DEMO_END 0x%06X COIN_SOUND 0x%06X" %
          (int.from_bytes(d[0x108:0x10A], "big"), 0x122, 0x128, 0x12E, 0x134))


if __name__ == "__main__":
    main()
