NAME = "standard-mvs"
DESCRIPTION = ("Standard MVS (a joystick, the usual BIOS): the Plus features in play, as on the console; the trackball "
               "cabinet (its own BIOS) keeps the original game")

# The original game ran only on its own cabinet: a trackball, read by that cabinet's BIOS (236-bios). On any other
# MVS the Zap-Rod can't move. Every earlier patch tells the console from the arcade with "tst.b 0x10FD82" (the
# BIOS's system mode: 0 = AES), so on a standard MVS all of them stayed off too.
#
# This patch adds a second switch, PLUS_OFF: 0 on the console and on a standard MVS, 0x80 only on the trackball
# cabinet - told apart by its BIOS (its trackball reader at 0xC1B1F6 starts CABINET_BIOS; no other BIOS has it). The
# earlier patches' checks are re-pointed at it in place (the address in the same instruction, so no code moves),
# except the ones in HOME_ONLY: the attract and title flow (boot to title, the intro, the title menu and what hangs
# off it - options, 2P, the course select's console look), the pause, the difficulty levels and BETA 1. Those stay
# console-only for now, so on a standard MVS a coin and Start begin the original arcade game (credits, the
# operator's settings), played with the joystick and the Plus fixes.
#
# PLUS_OFF is set at every way into the game: the four USER requests (table 0x1000). (Not in the vblank too: a few
# more cycles there moved the cabinet's own screen-change wipe race - its picture must stay the original's.)

CABINET_BIOS = (0xC1B1F6, bytes.fromhex("4BF90010F3004EBA"))
HOME_ONLY = {
    "020": {"attract_start", "scene_hook", "player_start", "main_hook", "title_frame", "course_timer",
            "course_select", "course_deck", "fix_queue", "arcade_select"},
    "040": {"pick_tall"},
    "050": "all",
    "080": "all",
    "110": "all",
    "190": "all",
    "210": "all",
    "240": "all",
    "250": "all",
}

SYSTEM_MODE = 0x10FD82
PLUS_OFF = 0x10EC63                     # spare RAM: 0 = the Plus features on (console, standard MVS), 0x80 = cabinet
USER_TABLE = 0x1000                     # USER requests 0-3: their handlers (longs)

import glob, os, re
from patchlib import FREE_START, FIXED_END

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = bytes.fromhex("4A39") + SYSTEM_MODE.to_bytes(4, "big")     # tst.b 0x10FD82


def check_labels(path):
    """The label each SYSTEM_MODE check of a patch's assembly sits under, in source order."""
    out, label = [], "?"
    for line in open(path).read().split("\n"):
        m = re.match(r"^\s*([a-z_][a-z0-9_]*):", line)
        if m and not line.strip().startswith("#"):
            label = m.group(1)
        if re.search(r"tst\.b 0x\{SYSTEM_MODE:X\}", line):
            out.append(label)
    return out


def apply(rom):
    # The earlier patches' code blocks, one each, in order (the build's log)
    blocks = [int(m.group(1), 16) for m in (re.match(r"\s+0x([0-9A-F]+)\s+\d+ byte\(s\) of new code", l) for l in rom.log)
              if m]
    number = {}                                     # NAME -> the file's number
    for path in glob.glob(os.path.join(HERE, "[0-9]*.py")):
        m = re.search(r'^NAME = "([^"]+)"', open(path).read(), re.M)
        number[m.group(1)] = os.path.basename(path)[:3]
    names = [number[n] for n in rom.applied[:-1]]   # the patches applied before this one (a test build may skip some)
    assert len(blocks) == len(names), "standard-mvs: %d code blocks for %d patches" % (len(blocks), len(names))
    ends = blocks[1:] + [rom.next_free]
    repoint, kept = [], []
    for name, start, end in zip(names, blocks, ends):
        sites = []
        at = rom.data.find(CHECK, start, end)
        while at >= 0:
            sites.append(at)
            at = rom.data.find(CHECK, at + 1, end)
        path = glob.glob(os.path.join(HERE, name + "_*.py"))[0]
        labels = check_labels(path)
        home = HOME_ONLY.get(name, set())
        if home == "all":
            kept += sites
            continue
        if len(labels) != len(sites):       # (a check in code a setting leaves out - fine if they all agree)
            assert not any(l in home for l in labels), "standard-mvs: patch %s's checks don't line up" % name
            labels = ["?"] * len(sites)
        for site, label in zip(sites, labels):
            (kept if label in home else repoint).append(site)
    assert len(repoint) + len(kept) == rom.data.count(CHECK, FREE_START, FIXED_END), "standard-mvs: a check unaccounted"

    sig_hi, sig_lo = CABINET_BIOS[1][:4], CABINET_BIOS[1][4:]
    prev_user = [rom.u32(USER_TABLE + 4 * i) for i in range(4)]
    code = f"""
    bra.w user0                 | +0 .. +12 USER requests 0-3
    bra.w user1
    bra.w user2
    bra.w user3

set_flag:                               | PLUS_OFF: 0 unless an MVS on the trackball cabinet's BIOS
    clr.b 0x{PLUS_OFF:X}
    tst.b 0x{SYSTEM_MODE:X}
    beq.s 9f
    cmpi.l #0x{int.from_bytes(sig_hi, "big"):08X},0x{CABINET_BIOS[0]:X}
    bne.s 9f
    cmpi.l #0x{int.from_bytes(sig_lo, "big"):08X},0x{CABINET_BIOS[0] + 4:X}
    bne.s 9f
    move.b #0x80,0x{PLUS_OFF:X}
9:  rts

user0:
    bsr.s set_flag
    jmp 0x{prev_user[0]:X}
user1:
    bsr.s set_flag
    jmp 0x{prev_user[1]:X}
user2:
    bsr.s set_flag
    jmp 0x{prev_user[2]:X}
user3:
    bsr.s set_flag
    jmp 0x{prev_user[3]:X}
"""
    base = rom.place_code(code, why="standard MVS: the Plus switch")
    for i in range(4):
        rom.write(USER_TABLE + 4 * i, (base + 4 * i).to_bytes(4, "big"), expect=prev_user[i].to_bytes(4, "big"),
                  why="USER request %d: the Plus switch first" % i)
    flag = bytes.fromhex("4A39") + PLUS_OFF.to_bytes(4, "big")
    for site in repoint:
        rom.write(site, flag, expect=CHECK, why="standard MVS: Plus on unless the trackball cabinet")
