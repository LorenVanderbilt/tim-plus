-- Live tuning of the AES joystick's Zap-Rod speed (patch 010 - nothing in the ROM file changes, just this run).
--   ./run.sh -- -autoboot_script tools/probes/joy_speed.lua
-- Keys (the values show at the top of the screen; speeds in trackball steps a frame, about a pixel each):
--   [ ]   START: the speed the moment a direction is pressed (what a quick tap moves)
--   ; '   TOP:   the speed after holding a while
--   , .   RAMP:  frames of holding to get from START to TOP (60 = a second; 0 = always TOP)
--   \     back to the patch's values
-- How: the patch keeps its three numbers in a little table tagged "JOYS" (start, added a frame, top, in 1/256
-- steps); this finds it and rewrites it in the running machine's ROM.
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local input = manager.machine.input
local screen = manager.machine.screens[":screen"]

local TABLE
for a = 0x0F1000, 0x0FFFF0, 2 do
  if mem:read_u32(a) == 0x4A4F5953 then TABLE = a + 4 break end   -- "JOYS"
end
if not TABLE then print("joy_speed: no JOYS table - is patch 010 in the build?") return end

local function frames_of(start, add, top) if add == 0 or top <= start then return 0 end return math.floor((top - start) / add + 0.5) end
local PATCH = { start = mem:read_u16(TABLE), top = mem:read_u16(TABLE + 4) }
PATCH.ramp = frames_of(PATCH.start, mem:read_u16(TABLE + 2), PATCH.top)
local v = { start = PATCH.start, top = PATCH.top, ramp = PATCH.ramp }

local function store()
  if v.top < v.start then v.top = v.start end
  local start, add = v.start, 0
  if v.ramp == 0 then start = v.top elseif v.top > v.start then add = math.max(1, (v.top - v.start) // v.ramp) end
  mem:write_direct_u16(TABLE, start)
  mem:write_direct_u16(TABLE + 2, add)
  mem:write_direct_u16(TABLE + 4, v.top)
end

local keys = {}
local function pressed(token)
  local now = input:code_pressed(input:code_from_token(token))
  local was = keys[token]
  keys[token] = now
  return now and not was
end

local STEP = 32   -- 1/8 of a step a frame
SUB = emu.register_frame_done(function()
  local changed = true
  if pressed("KEYCODE_OPENBRACE") then v.start = math.max(STEP, v.start - STEP)
  elseif pressed("KEYCODE_CLOSEBRACE") then v.start = math.min(16 * 256, v.start + STEP); v.top = math.max(v.top, v.start)
  elseif pressed("KEYCODE_COLON") then v.top = math.max(v.start, v.top - STEP)
  elseif pressed("KEYCODE_QUOTE") then v.top = math.min(16 * 256, v.top + STEP)
  elseif pressed("KEYCODE_COMMA") then v.ramp = math.max(0, v.ramp - 5)
  elseif pressed("KEYCODE_STOP") then v.ramp = math.min(240, v.ramp + 5)
  elseif pressed("KEYCODE_BACKSLASH") then v.start, v.top, v.ramp = PATCH.start, PATCH.top, PATCH.ramp
  else changed = false end
  if changed then store() end
  screen:draw_text(4, 2, string.format("START %.3g [ ]   TOP %.3g ; '   RAMP %d , .   (\\ = reset)",
                   v.start / 256, v.top / 256, v.ramp), 0xFFFFFFFF, 0xC0000000)
end)
