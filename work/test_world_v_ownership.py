"""World of V must retain native actor ownership in gameplay and floor callbacks."""
from pathlib import Path
from lupa import LuaRuntime
from autoload_fixture import make_game

# Exercise the real core, with strict native stubs recording every mutation.
lua = LuaRuntime()
lua.execute('''
allowed=true;mode=3;writes=0
sdk={find_type_definition=function()return {get_methods=function()return {}end}end,
get_managed_singleton=function()return {call=function(_,n)
 assert(n=='get_gameMode');return mode end}end}
dofile=function(p)if p:find('runtime')then return {permits=function()return allowed end}end;return {}end
function actor(id)
 local p={id=id,enabled=true,draw=true,update=true,world=true}
 local med={call=function(_,n,v)
  writes=writes+1
  if n=='set_drawSelf'then p.draw=v
  elseif n=='set_updateSelf'then p.update=v
  else assert(n=='applyDrawSelf'or n=='applyUpdateSelf')end
 end}
 local controller={call=function(_,n,v)assert(n=='set_Enabled');writes=writes+1;p.world=v end}
 function p:call(n,v)
  if n=='get_playerID'then return self.id end
  if n=='get_ownerVergilPL'then return self.owner end
  if n=='get_isEventMove'then return self.event end
  if n=='get_cachedActivateMediator'then return med end
  if n=='get_cachedCharacterController'then return controller end
  if n=='get_cachedSubCharacterController'then return nil end
  writes=writes+1
  if n=='pausePlayer'then self.paused=true
  elseif n=='set_Enable'then self.enabled=v
  else error('Unexpected mutation: '..n)end
 end
 return p
end
active=actor(4);v=actor(2);v.owner=active
manager={call=function(_,n)assert(n=='get_manualPlayer');return active end}
''')
lua.globals().M = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
lua.execute('''
for _,modeValue in ipairs({0,1,3})do
 mode=modeValue
 for _,manualID in ipairs({0,1,4})do
  active.id=manualID
  for i=1,100 do
   assert(not M.parkNonParty(manager,v));assert(not M.hideReserve(manager,v))
  end
 end
end
assert(writes==0 and v.enabled and v.update and v.draw and v.world and not v.paused)
-- Native reuse of the same ID/instance must check current ownership each time.
mode=3;v.owner=nil
assert(M.parkNonParty(manager,v))
assert(not v.enabled and not v.update and not v.draw and not v.world and v.paused)
v.owner=active;v.enabled=true;v.update=true;v.draw=true;v.world=true;v.paused=false
local before=writes
assert(not M.parkNonParty(manager,v));assert(not M.hideReserve(manager,v))
assert(writes==before and v.enabled and v.update and v.draw and v.world and not v.paused)
v.owner=nil;assert(M.hideReserve(manager,v));assert(not v.draw and v.update)
''')

# Loader must not even dispatch an owned summon to the parking stub.
for fps in (30, 60, 144):
    lua = make_game(initial=4, fps=fps)
    lua.execute('''
players[2]=actor(2);players[2].ownerVergil=active;states[2]=6
tick(fps*6)
local v=players[2]
assert(excludedCount==0 and v.visible and v.enabled and v.updating and not v.paused)
v.ownerVergil=nil;tick(fps)
assert(excludedCount==1 and not v.visible and not v.enabled)
v.ownerVergil=active;v.visible=true;v.enabled=true;v.updating=true;v.paused=false
tick(fps*3)
assert(excludedCount==1 and v.visible and v.enabled and v.updating and not v.paused)
assert(loads[2]==nil and preloads[2]==nil and v.initialized==0)
''')

for phase in ('updateBattleFinish', 'updateNextStageWait', 'updateFadeoutShowStageResult', 'updateFloorFinalize'):
    lua = make_game(initial=4)
    lua.globals().phase = phase
    lua.execute('''
tick(fps*4)
players[2]=actor(2);local v=players[2];v.ownerVergil=active;states[2]=6
bp={CurrentStageNo=20,get_field=function(self,n)return self[n]end}
dmc5_switch_palace={run={owner=bp}}
local h=nativeHooks['app.BloodyPalaceManager.'..phase]
h[1]({[2]=bp});assert(h[2](777)==777)
assert(v.visible and v.enabled and v.updating and not v.paused and v.hideCalls==nil)
assert(not S.hidePalaceExtra(bp))
v.ownerVergil=nil;assert(S.hidePalaceExtra(bp));assert(not v.visible)
''')
print('PASS: real core performs zero mutations on Vergil-owned V; loader and all four palace callbacks preserve skill ownership; same-instance ownership changes and ownerless V cleanup covered.')
