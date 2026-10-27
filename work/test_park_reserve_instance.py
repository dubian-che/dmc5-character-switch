from pathlib import Path
from lupa import LuaRuntime

lua=LuaRuntime()
lua.execute('''
sdk={find_type_definition=function()return {get_methods=function()return {}end}end}
dofile=function(path)
 if path:find('runtime')then return {permits=function()return allowed end}end
 return {}
end
allowed=true;writes=0
function actor(id)
 local p={id=id,enabled=true,draw=true,update=true,event=false,fields={},world=true}
 local controller={call=function(_,n,v)
  assert(n=='set_Enabled');writes=writes+1;p.world=v
 end}
 local med={call=function(_,n,v)
  if n=='get_drawSelf'then return p.draw end
  if n=='get_updateSelf'then return p.update end
  writes=writes+1
  if n=='set_drawSelf'then p.draw=v
  elseif n=='set_updateSelf'then p.update=v
  else assert(n=='applyDrawSelf'or n=='applyUpdateSelf')end
 end}
 local object={call=function(_,n)
  if n=='get_DrawSelf'then return p.draw end
  assert(n=='get_UpdateSelf');return p.update
 end}
 function p:get_field(n)return self.fields[n]end
 function p:call(n,v)
  if n=='get_playerID'then return self.id end
  if (n=='get_isEventMove'or n=='get_isEventRun')then return self.event end
  if n=='get_Enable'then return self.enabled end
  if n=='get_cachedActivateMediator'then return med end
  if n=='get_GameObject'then return object end
  if n=='get_cachedCharacterController'then return controller end
  if n=='get_cachedSubCharacterController'then return nil end
  writes=writes+1
  if n=='pausePlayer'then self.paused=true
  elseif n=='set_Enable'then self.enabled=v
  else error('Forbidden resource/input/action call: '..n)end
 end
 return p
end
active=actor(4)
manager={call=function(_,n)assert(n=='get_manualPlayer');return active end}
''')
lua.globals().M=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
lua.execute('''
for _,id in ipairs({0,1,4})do
 local duplicate=actor(id)
 assert(M.parkReserve(manager,duplicate))
 assert(not duplicate.enabled and not duplicate.draw and not duplicate.update and not duplicate.world and duplicate.paused)
 local previous=writes
 for i=1,100 do assert(M.parkReserve(manager,duplicate))end
 assert(writes==previous,'settled instance was rewritten')
end
local before=writes
assert(not M.parkReserve(manager,active))
assert(not M.parkReserve(manager,actor(3)))
assert(not M.parkReserve(manager,actor(2)))
local clone=actor(4);clone.fields.IsDoppel=true
assert(not M.parkReserve(manager,clone))
local boss=actor(1);boss.fields.IsEnemyDante=true
assert(not M.parkReserve(manager,boss))
local eventActor=actor(0);eventActor.event=true
assert(not M.parkReserve(manager,eventActor))
allowed=false;assert(not M.parkReserve(manager,actor(0)))
assert(writes==before)
''')
print('PASS: real per-instance parking uses no resource, input, action or unload calls; manual player, NPCs, clone, native Dante boss, events and outside scope untouched; no repeated settled writes')
