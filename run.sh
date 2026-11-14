#!/bin/sh
# Build the patched The Irritating Maze ROM set and play it in MAME - as the AES home console by default.
#   ./run.sh                          AES (home console) mode, all patches
#   ./run.sh --mvs                    arcade (MVS) mode instead (coin = 5, start = 1)
#   ./run.sh --bios unibios40         use a different BIOS: AES machine: asia (default), japan, devel, unibios40, unibios33 ...
#                                     arcade machine (--mvs): euro (default), us, japan, unibios40 ...
#   ./run.sh --only some-patch        just that patch
#   ./run.sh --skip some-patch        everything except that patch (--skip every patch = the original game)
#   ./run.sh [options] -- [MAME options]     anything after -- goes to MAME
# Personal defaults go in local.cfg (not committed), a shell file.
# To record a play session so it can be replayed exactly later (saved to recordings/NAME.inp):
#   ./run.sh -- -record NAME.inp     (recordings are mode-specific)
# Controls: 1 = Start, 5 = Select (AES) / insert coin (MVS), arrows = move, Z X C V = A B C D
# (../neogeo-notes/tools/mame/neogeo-keys.cfg), Tab = MAME menu, Esc = quit.
# M = save for Claude (sta/aes/new_01.sta, new_02 ... - ../neogeo-notes/tools/mame/savekey.lua; new_saves.txt also
# logs the course step 0x10806C), Shift+F7 = MAME's own save.
cd "$(dirname "$0")" || exit 1
export SAVEKEY_WORD=${SAVEKEY_WORD:-10806C}
mode=aes
bios=""
build_args=""
[ -f local.cfg ] && . ./local.cfg
while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in
        --mvs) mode=mvs ;;
        --aes) mode=aes ;;
        --bios) shift; bios="-bios $1" ;;
        *) build_args="$build_args $1" ;;
    esac
    shift
done
[ "$1" = "--" ] && shift
python3 tools/hackbuild.py $build_args || exit 1
mkdir -p recordings
if [ "$mode" = aes ]; then
    [ -f build/aes/neogeo.xml ] || { echo "No AES build (need roms/aes.zip) - use --mvs, or see tools/hackbuild.py"; exit 1; }
    exec mame aes -hash build/aes -rompath build/aes -cart irrmaze $bios -ctrlrpath ../neogeo-notes/tools/mame -ctrlr neogeo-keys -autoboot_script ../neogeo-notes/tools/mame/savekey.lua -input_directory recordings -window -skip_gameinfo -nowaitvsync "$@"
fi
exec mame irrmaze -rompath build/roms $bios -ctrlrpath ../neogeo-notes/tools/mame -ctrlr neogeo-keys -autoboot_script ../neogeo-notes/tools/mame/savekey.lua -input_directory recordings -window -skip_gameinfo -nowaitvsync "$@"
