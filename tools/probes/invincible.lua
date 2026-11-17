-- Invincible all the time (walls stop the Zap-Rod, no zap) - for making saves and screenshots. The M save key
-- still works. Use: ./run.sh -- -autoboot_script tools/probes/invincible.lua
-- (patch 230's hidden INVINCIBLE row: patch 020's RAM 0x10EF05, 1 = on)
dofile("../neogeo-notes/tools/mame/savekey.lua")

local mem = manager.machine.devices[":maincpu"].spaces["program"]
emu.register_frame_done(function()
    mem:write_u8(0x10EF05, 1)
end)
