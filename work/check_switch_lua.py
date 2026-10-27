import sys
from pathlib import Path
sys.path.insert(0,'work/python-deps')
from lupa import LuaRuntime
lua=LuaRuntime()
for name in ['dmc5_switch_input_menu.lua','dmc5_switch_loader.lua','dmc5_switch_runtime.lua','dmc5_switch_lifecycle.lua','dmc5_switch_resources.lua','dmc5_switch_core.lua','dmc5_switch_hud.lua','dmc5_live_switch.lua','dmc5_switch_progression.lua','dmc5_switch_regen.lua','dmc5_party_hud.lua','dmc5_switch_keys.lua','dmc5_switch_voice.lua','dmc5_switch_controller.lua','dmc5_switch_palace.lua']:
 lua.execute('assert(load(...))',Path('outputs/DMC5CharacterSwitch',name).read_text())
 print(name+': syntax OK')






