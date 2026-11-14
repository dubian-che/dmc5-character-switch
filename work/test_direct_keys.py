from pathlib import Path
from lupa import LuaRuntime
from autoload_fixture import make_game
lua=LuaRuntime(unpack_returned_tuples=True)
k=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_keys.lua').read_text())
lua.globals().K=k
lua.execute("""
json={load_file=function()return supplied end}
supplied={nextKey=118,previousKey=119}
local cfg=K.load_config();assert(cfg.nextKey==118 and cfg.previousKey==119 and cfg.neroKey==0 and cfg.danteKey==0 and cfg.vergilKey==120)
supplied={neroKey=128};local cfg,why=K.load_config();assert(why and cfg.neroKey==118)
supplied={neroKey=0,danteKey=0,vergilKey=0};local cfg,why=K.load_config();assert(not why and cfg.neroKey==0)
""")
lua=make_game()
lua.execute("""
tick(fps*5)
local function press(key)key_down={};tick(1);key_down[key]=true;tick(1)end
press(120);assert(active.id==4)
press(118);assert(active.id==0)
press(119);assert(active.id==1)
local n=switches;tick(fps);assert(switches==n,'held direct key repeats')
press(119);assert(active.id==0 and switches==n+1,'same-character key did not return to previous actor')
n=switches
key_down={};tick(1);key_down[118]=true;key_down[120]=true;tick(1);assert(switches==n)
key_down[120]=nil;tick(1);assert(switches==n,'chord release selects actor')
key_down={};tick(1);key_down[128]=true;key_down[118]=true;tick(1);assert(switches==n)
press(118);assert(active.id==1,'return history did not toggle')
press(128);assert(active.id==4,'cycle broken')
""")
print('PASS: direct startup switching, hold, same actor, chord cancellation, cycles, old config collision and disabled keys.')
