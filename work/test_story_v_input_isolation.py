"""Shared local input must not drive non-manual idle V instances."""
from pathlib import Path
from lupa import LuaRuntime

lua = LuaRuntime()
lua.execute('''
mode=0;mission=3
R={nativeControl={id=0},storyRetrySerial=1}
sdk={find_type_definition=function()return {get_methods=function()return {}end}end,
get_managed_singleton=function()return {call=function(_,n)
 if n=='get_gameMode'then return mode end
 assert(n=='get_missionNo');return mission
end}end}
dofile=function(p)if p:find('runtime')then return R end;return {}end
pad={}
function actor(id,input)
 local p={id=id,input=input,draw=true,think=false,writes=0,enabled=true,updating=true}
 local med={call=function(_,n,v)
  if n=='get_drawSelf'then return p.draw end
  if n=='set_drawSelf'then p.draw=v;p.writes=p.writes+1;return end
  assert(n=='applyDrawSelf')
 end}
 function p:call(n,v)
  if n=='get_playerID'then return self.id end
  if n=='get_padInput'then return self.input end
  if n=='get_isEventMove'then return self.event or false end
  if n=='get_ownerVergilPL'then return self.owner end
  if n=='get_isThinkEnable'then return self.think end
  if n=='set_isThinkEnable'then self.think=v;self.writes=self.writes+1;return end
  if n=='get_cachedActivateMediator'then return self.noMediator and nil or med end
  error('Forbidden operation on native V: '..n)
 end
 return p
end
main=actor(1,pad);v1=actor(2,pad);v2=actor(2,pad)
players={main,v1,v2};active=main
manager={call=function(_,n,i)
 if n=='get_manualPlayer'then return active end
 if n=='getPlayerNum'then return #players end
 assert(n=='getPlayer');return players[i+1]
end}
''')
lua.globals().M = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
lua.execute('''
M.guardStoryV(manager)
assert(v1.think and v2.think and not v1.draw and not v2.draw)
assert(v1.enabled and v1.updating and v2.enabled and v2.updating)
local writes=v1.writes+v2.writes
for i=1,1000 do M.guardStoryV(manager)end
assert(v1.writes+v2.writes==writes,'settled echo rewritten each frame')
-- A real event regains its original input/draw flags without stopping audio.
v1.event=true;M.guardStoryV(manager)
assert(v1.draw and not v1.think and v2.think and not v2.draw)
v2.input={};M.guardStoryV(manager)
assert(v2.draw and not v2.think,'non-local input remained gated')
v1.event=false;R.nativeControl.id=2;M.guardStoryV(manager)
assert(v1.draw and not v1.think,'native V campaign was gated')
R.nativeControl.id=0;v1.owner=main;M.guardStoryV(manager)
assert(v1.draw and not v1.think,'Vergil-owned V was gated')
v1.owner=nil;v1.think=true;M.guardStoryV(manager)
assert(v1.draw,'native AI V was unnecessarily hidden')
v1.think=false;active=v1;M.guardStoryV(manager)
assert(v1.draw and not v1.think,'manual V was gated')
active=main;M.guardStoryV(manager)
assert(not v1.draw)
-- A new scene owns its old objects; never restore torn-down instances.
local oldWrites=v1.writes;mission=4;players={main};M.guardStoryV(manager)
assert(v1.writes==oldWrites and next(M.storyVState.actors)==nil)
active=nil;M.guardStoryV(manager);assert(M.storyVState==nil)
''')
print('PASS: two same-pad idle V actors isolated without pausing/disabling native update/audio; event, manual/native V, independent input, AI, Vergil ownership, settled writes and scene teardown covered')
