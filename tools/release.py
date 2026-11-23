#!/usr/bin/env python3
"""Make the release files from the last build: the web patcher, xdelta patches, and ready-to-copy packages.

    python3 tools/release.py [--name timplus-beta1] [--version "Beta 1"] [--prom-swap yes|no] [--publish]

Run tools/hackbuild.py first. Everything goes in dist/<name>/ (git-ignored):

    patcher/              the web patcher for this game alone (../neogeo-patcher's page with this release's data): a player drops in
                          their own irrmaze.zip (or Darksoft-style folder), picks a system and downloads a ready
                          package with its README. Patching happens in their browser; nothing is uploaded.
    <name>_itch_html.zip  patcher/ zipped for itch.io's "HTML" upload (index.html at its root)
    <name>_xdelta.zip     patches for the MAME set's files (236-p1.p1.xdelta ...) and a Darksoft-style folder's
                          (prom.xdelta ...), with how to apply them by hand. No game data: shareable.
    private/<system>/     each package the patcher makes, ready-patched, for testing on your own devices only -
                          they hold game data. The same layout and README the patcher's download has.

The packages are defined once, in packages(): release.py builds private/ from that list and writes the same list
into patchdata.js for the patcher, so the two can't drift apart. Ported from Blue's Journey Plus's release tool; the
Darksoft-style layout is data here (DARK), which the patcher reads.

The game is an MVS-only release for a trackball cabinet with its own BIOS; patch 280 turns the Plus on with any
other BIOS. So every package needs a usual BIOS: MAME's aes / ng_mv4f machines (not "mame irrmaze", the cabinet),
FinalBurn Neo running it under a usual game's driver (FBNEO_DRIVER: not irrmaze's trackball set-up), the
BackBit in either mode, MiSTer and the Analogue Pocket with their usual BIOS files.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "neogeo-patcher", "tools"))
import ngpatcher    # the shared web patcher's repo, next to this one: its page, and where its data goes

GAME_ID = 'timplus'                  # the shared patcher's id for this game (games.js, ?game=)
ORIGINAL = os.path.join(ROOT, "roms", "irrmaze.zip")
BUILT = os.path.join(ROOT, "build", "aes", "irrmaze.zip")
BUILT_LIST = os.path.join(ROOT, "build", "aes", "neogeo.xml")   # MAME's software list entry for the built files
GAME_FILES = ["236-p1.p1", "236-s1.s1", "236-m1.m1", "236-v1.v1", "236-v2.v2", "236-c1.c1", "236-c2.c2"]
ORIGINAL_FILES = {  # the files the patches apply to (size, CRC32, SHA-1), as listed in README.md - FBNeo's too
    "236-p1.p1": (2097152, "4c2ff660", "4a0cbd09044648ff9ec67723729f16d422c34bda"),
    "236-s1.s1": (131072, "5d1ca640", "40a9668a1742a44597a07ce72273d17119815637"),
    "236-m1.m1": (131072, "880a1abd", "905afa157aba700e798243b842792e50729b19a0"),
    "236-v1.v1": (2097152, "5f89c3b4", "dc8fd561cf8dfdd41696dcf14ea8d2d0ac4eec4b"),
    "236-v2.v2": (1048576, "72e3add7", "dc49f05274693255416d2e41ecc088027b798eb9"),
    "236-c1.c1": (4194304, "c1d47902", "727001c34f979226fc8f581113ce2aaac4fc0d42"),
    "236-c2.c2": (4194304, "e15f972e", "6a329559c57a67be73a6733513b59e9e6c8d61cc"),
}
PROM_SWAP = True    # the Darksoft-style prom: MAME's 236-p1.p1 with its halves swapped (the fixed half first) -
                    # the layout that booted on the user's Analogue Pocket (2026-11-16; --prom-swap no: the other)
DARK = {            # the Darksoft-style folder's files from the MAME set's (the patcher reads this too)
    "prom": {"file": "236-p1.p1", "swap": PROM_SWAP},
    "srom": "236-s1.s1",
    "m1rom": "236-m1.m1",
    "crom": [["236-c1.c1", "236-c2.c2"]],                       # each pair interleaved a word at a time
    "vrom": [["236-v1.v1", 0], ["236-v2.v2", 0x200000]],         # V ROMs end to end (both ADPCM-A here)
    "vromSize": 0x300000,
    "fpga": "13",   # as Blue's Journey's; the value's meaning isn't documented - unverified for this game
}
BACKBIT_FOLDER = "The Irritating Maze Plus"     # the cart's menu shows the folder's name
FBNEO_NAME = "timplus"              # the RomData set's zip and .dat
FBNEO_DRIVER = "neocup98"           # the FBNeo driver it runs under. Not irrmaze: that one sets up the trackball
                                    # (no joystick for player 1) and its own BIOS list. Neo-Geo Cup '98 has the
                                    # same 2 MB program ROM (halves swapped, HARDWARE_SNK_SWAPP), the usual BIOS
                                    # list (UniBIOS, AES / MVS) and the usual joystick (the user's RetroArch,
                                    # 2026-11-17: irrmaze's controls didn't work, and its sound was half missing)
FBNEO_TYPES = {"236-p1.p1": "1, BRF_ESS, BRF_PRG", "236-s1.s1": "2, BRF_GRA", "236-c1.c1": "3, BRF_GRA",
               "236-c2.c2": "3, BRF_GRA", "236-m1.m1": "4, BRF_ESS, BRF_PRG", "236-v1.v1": "5, BRF_SND",
               "236-v2.v2": "5, BRF_SND"}
                                    # each file's ROM type (FBNeo's order): written out, as its RetroArch core's
                                    # RomData parser needs a type on each line. Both V ROMs are ADPCM-A (type 5),
                                    # as on the cartridge and in MAME - FBNeo's irrmaze has 236-v2 as ADPCM-B (6)
POCKET_FOLDER = "timplus"           # in Assets/ng/common/: its own name, so the original irrmaze folder stays
POCKET_JSON = {                     # Mazamars312's Neo Geo core: a copy of its own Irritating Maze instance file
    "instance": {                   # (dist/Assets/ng/Mazamars312.NeoGeo/Irritating Maze.json), pointed at
        "magic": "APF_VER_1",       # POCKET_FOLDER. No memory writes there: the sound ROMs' default layout.
        "variant_select": {"id": 777, "select": False},
        "data_path": POCKET_FOLDER,
        "data_slots": [{"id": 3, "filename": "srom"}, {"id": 4, "filename": "prom"}, {"id": 5, "filename": "crom0"},
                       {"id": 6, "filename": "m1rom"}, {"id": 7, "filename": "vroma0"}],
        "memory_writes": [],
    }
}
MERGE_GAP = 32                      # patch runs closer than this are stored as one


def readme(system, version, contents, steps, trouble, private=False):
    """A package's README.txt: what it is, what's in it, where it goes, what to do if it doesn't work."""
    rule = "=" * 70
    lines = ["The Irritating Maze Plus - %s - %s" % (version, system), rule, "",
             "The Irritating Maze Plus is a fan update of The Irritating Maze (SNK / Saurus, 1997), the Neo Geo",
             "arcade game that needed its own trackball cabinet: it plays with a joystick on the home console (AES)",
             "and on any standard MVS, with a title menu, options, difficulty levels, a 2P mode and many fixes.",
             "",
             ("These files were patched for testing on your own devices. They contain the game's data: don't share"
              " them." if private else
              "This package was made from your own copy of the game, in your browser. It contains the game's data:"
              " please don't share it - point people to the patcher instead."), "",
             "WHAT'S IN IT", ""]
    lines += ["  %s" % c for c in contents]
    lines += ["", "HOW TO PLAY IT", ""]
    for i, step in enumerate(steps):                    # (a step's later lines: a command, a note, under it)
        first, *more = step.split("\n")
        lines += ["  %d. %s" % (i + 1, first)] + ["     " + m for m in more]
    lines += ["", "CONTROLS", "",
              "  Joystick  move the Zap-Rod",
              "  A         hold to steady your hand (the rod moves more slowly)",
              "  B         hold and move the joystick to look around the course",
              "  C         show or hide the hand holding the Zap-Rod",
              "  Start     pause (in a course); the title menu (home console)"]
    lines += ["", "IF SOMETHING'S WRONG", ""]
    lines += ["  - %s" % t for t in trouble]
    lines += ["", "Found a problem or a glitch? Please report it on The Irritating Maze Plus page, with where it"
              " happened and a screenshot if you can.", "",
              "The Irritating Maze (c) 1997 SNK / Saurus. The Irritating Maze Plus is an unofficial fan project by"
              " Loren Vanderbilt III, not affiliated with or endorsed by them.", ""]
    return "\n".join(_wrap(l) for l in lines)


def _wrap(line, width=100):
    """Hard-wrap one README line, keeping its indent on the continuation lines."""
    if len(line) <= width:
        return line
    body = line.lstrip()
    indent = " " * (len(line) - len(body))
    lead = indent + ("   " if body[:2] in ("- ",) or body[:1].isdigit() else "")
    out, cur = [], indent
    for word in body.split(" "):
        if len(cur) + len(word) + 1 > width and cur.strip():
            out.append(cur.rstrip())
            cur = lead
        cur += word + " "
    out.append(cur.rstrip())
    return "\n".join(out)


def packages(version, private=False):
    """Every system's package: {id, label, note, download, entries: [[path, kind, arg]], next: [steps]}.
    kind "file": a MAME file (by its name); "darksoft": a Darksoft-style file (prom, crom0 ...); "zip": a zip of
    the MAME files named in arg; "text": arg itself; "list": MAME's software list entry; "dat": the FBNeo RomData file."""
    def pkg(id_, label, note, download, entries, system, contents, steps, trouble):
        entries = entries + [["README.txt", "text", readme(system, version, contents, steps, trouble, private)]]
        return {"id": id_, "label": label, "note": note, "download": download, "entries": entries, "next": steps}

    dark = ["prom", "srom", "m1rom", "crom0", "vroma0", "fpga"]
    return [
        pkg("retroarch", "RetroArch", "FinalBurn Neo core: Android, PC, Mac, handhelds",
            "IrritatingMazePlus-RetroArch.zip",
            [["timplus.zip", "zip", GAME_FILES], ["timplus.dat", "dat", None]],
            "RetroArch (FinalBurn Neo)",
            ["timplus.zip  the patched game",
             "timplus.dat  tells FinalBurn Neo how to run it - keep it next to timplus.zip",
             "README.txt   this file"],
            ["Copy timplus.zip and timplus.dat into the folder with your other Neo Geo games, side by side. The Neo"
             " Geo BIOS, neogeo.zip, needs to be in that folder or in RetroArch's system folder.",
             "In RetroArch, choose Load Content, pick timplus.zip and the core \"Arcade (FinalBurn Neo)\". It starts"
             " as an arcade MVS: insert a coin, then Start.",
             "For the home console version (title menu, options, 2P CHALLENGE): Quick Menu > Core Options, set the"
             " BIOS to a Universe BIOS (any version your neogeo.zip has) with its Unibios mode on AES, or"
             " to an AES BIOS. Then Quick Menu > Restart."],
            ["\"Error loading bios!\" / \"Failed initializing driver\": the BIOS chosen in the core options isn't in"
             " your neogeo.zip. Choose another (RetroArch's log lists the ones it found).",
             "\"Romset is unknown\": timplus.dat isn't in the same folder as timplus.zip, or the FinalBurn Neo core is"
             " older than mid-2024. Update it with Online Updater > Update Installed Cores.",
             "Use FinalBurn Neo, not RetroArch's MAME cores: those run the game as its trackball cabinet only.",
             "Not tested in RetroArch yet: it should work, but please report how it goes."]),
        pkg("mame", "MAME", "On a computer: Windows, Mac, Linux",
            "IrritatingMazePlus-MAME.zip",
            [["timplus/irrmaze.zip", "zip", GAME_FILES], ["timplus/neogeo.xml", "list", None]],
            "MAME",
            ["timplus/irrmaze.zip  the patched game",
             "timplus/neogeo.xml   MAME's list entry for it, so MAME accepts the patched files",
             "README.txt           this file"],
            ["Put the timplus folder somewhere handy, for example next to your MAME roms folder.",
             "Open a terminal (Command Prompt on Windows) in the folder that holds timplus, and run MAME as the Neo"
             " Geo home console, giving the path of your roms folder (the one with your Neo Geo BIOS files: neogeo.zip,"
             " and aes.zip for the home console):\n"
             "  mame aes -hash timplus -rompath \"timplus;C:\\path\\to\\your\\roms\" -cart irrmaze\n"
             "On a Mac or Linux the path looks like \"timplus;/Users/you/mame/roms\".",
             "Or as a standard arcade MVS (coin with 5, start with 1):\n"
             "  mame ng_mv4f -hash timplus -rompath \"timplus;C:\\path\\to\\your\\roms\" -cart1 irrmaze"],
            ["Don't run it with \"mame irrmaze\": that's the original trackball cabinet, with its own BIOS - the"
             " game then plays as the original, and the joystick does nothing.",
             "\"not found\" or wrong checksums: MAME isn't reading timplus/neogeo.xml. Check -hash points at the"
             " timplus folder.",
             "Tested with MAME 0.289."]),
        pkg("backbit", "BackBit Platinum", "A real Neo Geo, with the BackBit flash cart",
            "IrritatingMazePlus-BackBit.zip",
            [["%s/%s" % (BACKBIT_FOLDER, n), "file", n] for n in GAME_FILES],
            "BackBit Platinum MVS",
            ["%s/  the game's files, ready for the cart" % BACKBIT_FOLDER,
             "README.txt  this file"],
            ["Copy the \"%s\" folder into the NeoGeo folder on the cart's SD card. Putting it inside a genre"
             " folder is fine." % BACKBIT_FOLDER,
             "In the cart's menu, set Arcade Mode to AES for the home console version, or leave it on MVS: on an"
             " arcade MVS it plays as an arcade game (insert a coin, then Start).",
             "Choose %s from the cart's menu." % BACKBIT_FOLDER],
            ["Copying from a Mac adds hidden \"._\" files the cart can pick up by mistake. Eject the card properly,"
             " or run dot_clean on the folder first.",
             "Tested on a BackBit Platinum in a Neo Geo (AES and MVS modes), on a CRT TV."]),
        pkg("mister", "MiSTer", "The NeoGeo core, Darksoft-style folder",
            "IrritatingMazePlus-MiSTer.zip",
            [["irrmaze/%s" % n, "darksoft", n] for n in dark],
            "MiSTer (NeoGeo core)",
            ["irrmaze/    the patched game in the Darksoft-style layout the NeoGeo core reads",
             "README.txt  this file"],
            ["If you already have The Irritating Maze in games/NeoGeo/irrmaze, move it somewhere else first: this"
             " folder takes its place.",
             "Copy the irrmaze folder into games/NeoGeo/ on the MiSTer's SD card.",
             "Load it in the NeoGeo core and set the system type to AES in the core's menu (MVS works too)."],
            ["Not tested on a MiSTer yet: it should work, but please report how it goes."]),
        pkg("pocket", "Analogue Pocket", "Mazamars312's Neo Geo core",
            "IrritatingMazePlus-AnaloguePocket.zip",
            [["Assets/ng/common/%s/%s" % (POCKET_FOLDER, n), "darksoft", n] for n in dark if n != "fpga"]
            + [["Assets/ng/Mazamars312.NeoGeo/The Irritating Maze Plus.json", "text",
                json.dumps(POCKET_JSON, indent=4) + "\n"]],
            "Analogue Pocket (Mazamars312's Neo Geo core)",
            ["Assets/ng/common/%s/  the patched game (Darksoft-style files)" % POCKET_FOLDER,
             "Assets/ng/Mazamars312.NeoGeo/The Irritating Maze Plus.json  tells the core where the game is",
             "README.txt  this file",
             "Your original Irritating Maze (Assets/ng/common/irrmaze) is left as it is."],
            ["Set up Mazamars312's Neo Geo core first if you haven't: its BIOS files go in Assets/ng/common/.",
             "Copy the Assets folder onto the root of the Pocket's SD card. It merges with the Assets folder"
             " already there.",
             "On the Pocket, open the Neo Geo core and choose The Irritating Maze Plus.",
             "Press the Home button, then Core Settings > MVS/AES, and choose AES. The core restarts."],
            ["The game doesn't appear: check the .json file is in Assets/ng/Mazamars312.NeoGeo/ and the game's"
             " files in Assets/ng/common/%s/." % POCKET_FOLDER,
             "INSERT COIN on the title: the core is in MVS mode - it plays as an arcade game there. Set MVS/AES to"
             " AES under Core Settings for the home console version."]),
    ]


def sha1(data):
    return hashlib.sha1(data).hexdigest()


def crc(data):
    return "%08x" % (zlib.crc32(data) & 0xFFFFFFFF)


def darksoft(files):
    """The Darksoft-style folder's files from a MAME set's (DARK): {name: bytes}."""
    def interleave(a, b):
        return b"".join(a[i:i + 2] + b[i:i + 2] for i in range(0, len(a), 2))
    p = files[DARK["prom"]["file"]]
    if DARK["prom"]["swap"]:
        p = p[len(p) // 2:] + p[:len(p) // 2]
    vrom = bytearray(DARK["vromSize"])
    for name, at in DARK["vrom"]:
        vrom[at:at + len(files[name])] = files[name]
    return {
        "prom": p,
        "srom": files[DARK["srom"]],
        "m1rom": files[DARK["m1rom"]],
        "crom0": b"".join(interleave(files[a], files[b]) for a, b in DARK["crom"]),
        "vroma0": bytes(vrom),
        "fpga": DARK["fpga"].encode(),
    }


def xdelta(old, new, out, work):
    """Write an xdelta patch from old to new (bytes) at out, and check it applies."""
    a, b, back = (os.path.join(work, n) for n in ("old", "new", "back"))
    open(a, "wb").write(old)
    open(b, "wb").write(new)
    subprocess.run(["xdelta3", "-e", "-9", "-f", "-s", a, b, out], check=True)
    subprocess.run(["xdelta3", "-d", "-f", "-s", a, out, back], check=True)
    assert open(back, "rb").read() == new, "%s doesn't apply" % out


def write_zip(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


def zip_bytes(files):
    path = os.path.join(ROOT, "dist", ".zip_tmp")
    write_zip(path, files)
    data = open(path, "rb").read()
    os.remove(path)
    return data


def fbneo_dat(files):
    """FBNeo's RomData file for the built files: run under FBNEO_DRIVER, from timplus.zip."""
    lines = ["// The Irritating Maze Plus: Final Burn Neo RomData (load %s.zip, this file next to it)" % FBNEO_NAME,
             "ZipName:  " + FBNEO_NAME, "DrvName:  " + FBNEO_DRIVER, "FullName: \"The Irritating Maze Plus\""]
    lines.append("")
    lines += ["%-12s 0x%06x, 0x%08x, %s" % (n + ",", len(files[n]), zlib.crc32(files[n]), FBNEO_TYPES[n])
              for n in FBNEO_TYPES]           # (in the driver's order)
    return "\n".join(lines) + "\n"


def runs(old, new):
    """Where new differs from old (or runs past its end), as [offset, length] runs merged across small gaps."""
    def same(a, b):
        return b <= len(old) and old[a:b] == new[a:b]
    out, i, n, step = [], 0, len(new), 64
    while i < n:
        j = min(i + step, n)
        if same(i, j):
            i = j
            continue
        s = i
        while s < len(old) and old[s] == new[s]:
            s += 1
        e = j
        while e < n and not same(e, min(e + step, n)):
            e = min(e + step, n)
        while e > s and e <= len(old) and old[e - 1] == new[e - 1]:
            e -= 1
        if out and s - (out[-1][0] + out[-1][1]) < MERGE_GAP:
            out[-1][1] = e - out[-1][0]
        else:
            out.append([s, e - s])
        i = max(e, j)
    return out


def patch_data(original, built, version, packages_list):
    """patchdata.js for the web patcher: the original files' checksums (MAME and Darksoft names), each patched
    file's runs (their bytes deflated together, from the file's "at" in that blob), the Darksoft layout, the texts
    the packages need, and the packages."""
    blob, files = bytearray(), {}
    for name in GAME_FILES:
        new, rs = built[name], runs(original[name], built[name])
        files[name] = {"size": len(new), "crc32": crc(new), "runs": rs, "at": len(blob)}
        for off, length in rs:
            blob += new[off:off + length]
        back = bytearray(original[name][:len(new)].ljust(len(new), b"\0"))     # (rebuilt the patcher's way)
        at = files[name]["at"]
        for off, length in rs:
            back[off:off + length] = blob[at:at + length]
            at += length
        assert bytes(back) == new, "runs of %s don't rebuild it" % name
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = comp.compress(bytes(blob)) + comp.flush()
    data = {
        "version": version,
        "order": GAME_FILES,
        "source": {n: {"size": len(original[n]), "crc32": crc(original[n])} for n in GAME_FILES},
        "darksource": {n: {"size": len(d), "crc32": crc(d)} for n, d in darksoft(original).items()},
        "dark": DARK,
        "target": files,
        "blobSize": len(blob),
        "texts": {"dat": fbneo_dat(built), "list": open(BUILT_LIST).read()},
        "packages": packages_list,
        "blob": base64.b64encode(packed).decode(),
    }
    return ngpatcher.patchdata_js(GAME_ID, data)


def build_package(pkg, built, dark_built, texts):
    """The files a package holds: {path: bytes} (the same thing the web patcher builds)."""
    out = {}
    for path, kind, arg in pkg["entries"]:
        if kind == "file":
            out[path] = built[arg]
        elif kind == "darksoft":
            out[path] = dark_built[arg]
        elif kind == "zip":
            out[path] = zip_bytes({n: built[n] for n in arg})
        elif kind in ("dat", "list"):
            out[path] = texts[kind].encode()
        else:
            out[path] = arg.encode()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--name", default="timplus-beta1")
    ap.add_argument("--version", default="Beta 1")
    ap.add_argument("--prom-swap", choices=["yes", "no"], help="the Darksoft-style prom's halves swapped or not "
                    "(default: PROM_SWAP)")
    ap.add_argument("--publish", action="store_true", help="also write this release's data into ../neogeo-patcher "
                    "(games/%s/patchdata.js), the live page's - only for a release going out" % GAME_ID)
    args = ap.parse_args()
    if args.prom_swap:
        DARK["prom"]["swap"] = args.prom_swap == "yes"
    if not shutil.which("xdelta3"):
        sys.exit("xdelta3 not found (brew install xdelta)")
    original = {n: zipfile.ZipFile(ORIGINAL).read(n) for n in GAME_FILES}
    built = {n: zipfile.ZipFile(BUILT).read(n) for n in GAME_FILES}
    for name, (size, crc32, want) in ORIGINAL_FILES.items():
        if sha1(original[name]) != want or len(original[name]) != size or crc(original[name]) != crc32:
            sys.exit("roms/irrmaze.zip: %s isn't the expected file" % name)
    dark_original, dark_built = darksoft(original), darksoft(built)
    texts = {"dat": fbneo_dat(built), "list": open(BUILT_LIST).read()}

    out = os.path.join(ROOT, "dist", args.name)
    shutil.rmtree(out, ignore_errors=True)
    work = os.path.join(out, "_work")
    os.makedirs(work)

    patches, checksums = {}, ["MAME set (irrmaze.zip):"]
    for sets, folder in ((zip(GAME_FILES, (original[n] for n in GAME_FILES), (built[n] for n in GAME_FILES)), "mame"),
                         (((n, dark_original[n], dark_built[n]) for n in dark_original), "darksoft")):
        if folder == "darksoft":
            checksums.append("\nDarksoft-style folder (prom %s):" % ("halves swapped" if DARK["prom"]["swap"]
                                                                      else "as MAME's 236-p1.p1"))
        for name, old, new in sets:
            checksums.append("  %-12s %8d bytes  crc32 %s  sha1 %s" % (name, len(old), crc(old), sha1(old)))
            if old != new:
                path = os.path.join(work, "patch")
                xdelta(old, new, path, work)
                patches["%s/%s.xdelta" % (folder, name)] = open(path, "rb").read()
    patches["fbneo/%s.dat" % FBNEO_NAME] = texts["dat"]
    patches["mame/neogeo.xml"] = texts["list"]
    patches["README.txt"] = XDELTA_README % {"version": args.version}
    patches["CHECKSUMS.txt"] = "\n".join(checksums) + "\n"
    write_zip(os.path.join(out, "%s_xdelta.zip" % args.name), patches)

    for pkg in packages(args.version, private=True):       # private/<system>/: unpacked, ready to copy
        for path, data in build_package(pkg, built, dark_built, texts).items():
            dest = os.path.join(out, "private", pkg["id"], path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(data)

    web = os.path.join(out, "patcher")
    js = patch_data(original, built, args.version, packages(args.version))
    ngpatcher.page_copy(GAME_ID, js, web)
    with zipfile.ZipFile(os.path.join(out, "%s_itch_html.zip" % args.name), "w", zipfile.ZIP_DEFLATED) as z:
        for path, _, names in sorted(os.walk(web)):
            for n in sorted(names):
                z.write(os.path.join(path, n), os.path.relpath(os.path.join(path, n), web))
    if args.publish:
        print("published: %s" % ngpatcher.publish(GAME_ID, js))
    shutil.rmtree(work)

    for path, _, names in sorted(os.walk(out)):
        for n in sorted(names):
            p = os.path.join(path, n)
            print("%9d  %s" % (os.path.getsize(p), os.path.relpath(p, ROOT)))


XDELTA_README = """The Irritating Maze Plus - %(version)s - patches
======================================================================

The easy way: use The Irritating Maze Plus patcher on its page. Drop in your irrmaze.zip, pick your system and
download a ready package. These patches are for doing it by hand.

You need the MAME ROM set irrmaze (The Irritating Maze / Ultra Denryu Iraira Bou). Check your files match the
checksums in CHECKSUMS.txt before patching. The game's own trackball BIOS (236-bios.sp1) isn't patched or needed:
play it with a usual Neo Geo BIOS (AES, MVS or the Universe BIOS).

MAME set (MAME, RetroArch, most emulators)
  1. Unzip irrmaze.zip into a folder.
  2. Apply each file in mame/ to the ROM file it's named after, with an xdelta patcher (Delta Patcher, or
     xdelta3 -d -s 236-p1.p1 236-p1.p1.xdelta 236-p1.p1.new and then replace the original with the .new file).
  3. Zip the files back up as irrmaze.zip.
  MAME: put the patched irrmaze.zip in a folder of its own (timplus) with mame/neogeo.xml from this zip, and run
  (with the folder's path) the home console:
      mame aes -hash timplus -rompath "timplus;roms" -cart irrmaze
  or a standard arcade MVS:
      mame ng_mv4f -hash timplus -rompath "timplus;roms" -cart1 irrmaze
  (roms being where your neogeo.zip / aes.zip BIOS files are). Not "mame irrmaze": that's the trackball cabinet.

RetroArch, Final Burn Neo core
  Patch the MAME set's files as above, but zip them as timplus.zip instead, and put it in your ROMs folder with
  fbneo/timplus.dat from this zip next to it (and neogeo.zip). Load timplus.zip: it starts as an arcade MVS. For
  the home console version, set the core options' BIOS to a Universe BIOS (any version, its mode AES) or an AES
  BIOS, and restart.

Darksoft-style set (MiSTer, Analogue Pocket)
  If you have the game as a Darksoft-style folder (prom, srom, m1rom, crom0, vroma0, fpga), apply the files in
  darksoft/ the same way. vroma0 and fpga don't change.

BackBit Platinum MVS
  Patch the MAME set's files as above and put them (no zip, no BIOS files) in a folder of their own inside
  NeoGeo/ on the card. Arcade Mode AES for the home console version, MVS for the arcade one.
"""


if __name__ == "__main__":
    main()
