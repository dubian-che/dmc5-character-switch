import sys
from pathlib import Path
sys.path.insert(0,'work/python-deps')
from lupa import LuaRuntime
lua=LuaRuntime()
k=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_keys.lua').read_text())
for current,nxt,prev in [(0,1,4),(1,4,0),(4,0,1)]:
 assert k.next_id(current,1)==nxt
 assert k.next_id(current,-1)==prev
lua.globals().K=k
lua.execute('''
local S={current=1,request=function(id) _G.last=id end}
local request=S.request
K.install(S)
S.step(1);assert(last==4)
S.step(-1);assert(last==0)
assert(S.request==request,'normal request replaced by legacy key bridge')
S.current=2;last=nil;S.step(1);assert(last==nil)
''')
print('PASS: forward/reverse wrap for all three characters; unsupported actors ignored; no legacy key bridge.')
