"""Reproduce native IsVergilMode's PlayingID >= 3 fallback across refreshes."""
from pathlib import Path
from lupa import LuaRuntime

source=Path('outputs/DMC5CharacterSwitch')

def fixture(core_source):
    lua=LuaRuntime()
    lua.execute('''
    sdk={hook=function()end,find_type_definition=function()return {
      get_method=function()return {}end,get_methods=function()return {}end}end}
    gm={PlayingID=1,get_field=function(s,n)assert(n=='PlayingID');return s.PlayingID end,
      set_field=function(s,n,v)assert(n=='PlayingID');s.PlayingID=v end,
      call=function(s,n)assert(n=='updatePlayerPadInput');loaded=s.PlayingID
        if fail then error('native refresh failure')end
      end}
    sdk.get_managed_singleton=function(n)assert(n=='app.GameManager');return gm end
    function nativeOpponent()return gm.PlayingID>=3 and 'Dante' or 'Vergil'end
    ''')
    runtime=lua.execute((source/'dmc5_switch_runtime.lua').read_text())
    lua.globals().runtime=runtime
    lua.execute("dofile=function(p)if p:find('runtime')then return runtime end;return {}end")
    core=lua.execute(core_source)
    lua.globals().M=core
    return lua

old=Path('work/checkpoints/release-33-before-loader-ack/outputs/dmc5_switch_core.lua').read_text()
lua=fixture(old)
lua.execute("M.syncInput(4);assert(loaded==4 and nativeOpponent()=='Dante','old bug not reproduced')")
lua=fixture((source/'dmc5_switch_core.lua').read_text())
lua.execute('''
for _,nativeID in ipairs({0,1,2,4})do
 for _,actorID in ipairs({0,1,4})do
  gm.PlayingID=nativeID
  local opponent=nativeOpponent()
  M.syncInput(actorID)
  assert(loaded==actorID and gm.PlayingID==nativeID)
  assert(nativeOpponent()==opponent,'input refresh changed native campaign branch')
  fail=true
  assert(not pcall(M.syncInput,actorID));fail=false
  assert(gm.PlayingID==nativeID,'exception leaked actor identity')
 end
end
gm.PlayingID=1
runtime.withInputProfile(gm,4,function()
 assert(gm.PlayingID==4)
 runtime.withInputProfile(gm,0,function()assert(gm.PlayingID==0)end)
 assert(gm.PlayingID==4)
end)
assert(gm.PlayingID==1)
''')
print('PASS: old story branch corruption reproduced; actor profiles load without changing normal/Vergil campaign identity; native errors and nesting restore identity')
