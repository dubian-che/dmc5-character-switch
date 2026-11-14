from pathlib import Path
from lupa import LuaRuntime
source=Path('outputs/DMC5CharacterSwitch/dmc5_switch_keys.lua').read_text()
l=LuaRuntime();l.execute('''
_VERSION='Lua 5.4';focused=true;down={};reads=0
package.loadlib=function()return function(k)reads=reads+1;if fail then error('native unavailable')end;return focused,down[k]or false end end
reframework={is_key_down=function()error('stale RF path must never be read')end}
''');l.globals().K=l.execute(source)
l.execute('''
assert(K.input.source=='windows-poll')
down[9]=true;assert(not K.read_key(9),'held on startup')
down[9]=false;assert(not K.read_key(9));down[9]=true;assert(K.read_key(9))
focused=false;assert(not K.read_key(9));focused=true;assert(not K.read_key(9),'held across focus regain')
down[9]=false;K.read_key(9);down[9]=true;assert(K.read_key(9))
local cfg={nextKey=9,previousKey=192,neroKey=118,danteKey=119,vergilKey=120}
local S={current=0,step=function()switches=switches+1 end,requestDirect=function()switches=switches+1 end}
local state={};switches=0;down={};K.poll(S,state,cfg,K.read_key)
down[9]=true;K.poll(S,state,cfg,K.read_key);K.poll(S,state,cfg,K.read_key);assert(switches==1)
down[192]=true;K.poll(S,state,cfg,K.read_key);down[9]=false;K.poll(S,state,cfg,K.read_key);assert(switches==1)
down={};K.poll(S,state,cfg,K.read_key);down[118]=true;K.poll(S,state,cfg,K.read_key);assert(switches==2)
down[121]=false;K.read_key(121);down[121]=true;assert(K.read_key(121))
fail=true;assert(not K.read_key(121) and K.input.source=='error')
''')
# A missing DLL must not silently fall back to broken or stale window-message keys.
l2=LuaRuntime();l2.execute("_VERSION='Lua 5.4';package.loadlib=function()return nil,'missing DLL'end")
k=l2.execute(source);assert not k.read_key(9) and k.input.error and k.input.source=='unavailable'
print('PASS: message-independent polling; initial/focus-held suppression; one edge; cancelled chords; direct keys; F10; fail-closed missing/faulted DLL.')
