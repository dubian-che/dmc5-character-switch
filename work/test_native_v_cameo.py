"""Story-owned V must survive both the event and its native cleanup frames."""
from pathlib import Path
from lupa import LuaRuntime
from autoload_fixture import make_game

# Exercise the loader, including a V whose event flag clears after the cameo.
for fps in (30,60,144):
    for selected in (0,1,4):
        lua=make_game(initial=selected,fps=fps)
        lua.execute('''
        mode=0;missionNo=2;campaignID=initial_id
        players[2]=actor(2);states[2]=6
        local v=players[2];v.eventRun=true
        tick(fps*5)
        assert(dmc5_switch_loader.count==3 and excludedCount==0)
        v.eventRun=false;tick(fps*10)
        assert(v.visible and v.enabled and v.updating and not v.paused and excludedCount==0)
        assert(not loads[2] and not preloads[2] and v.initialized==0)
        for _,id in ipairs({0,1,4})do S.request(id);tick(2)end
        assert(v.visible and v.enabled and v.updating and excludedCount==0)
        players[2]=actor(2);local nextV=players[2];tick(fps*3)
        assert(nextV.visible and nextV.enabled and nextV.updating and excludedCount==0)
        assert(S.error==nil and dmc5_switch_loader.error==nil)
        ''')

# Exercise the actual core entry points as well, not only the loader's gate.
lua=LuaRuntime()
lua.execute('''
mode=0;writes=0
sdk={find_type_definition=function()return {get_methods=function()return {}end}end,
 get_managed_singleton=function(name)
  assert(name=='app.GameManager');return {call=function(_,n)assert(n=='get_gameMode');return mode end}
 end}
dofile=function(path)if path:find('runtime')then return {permits=function()return true end}end;return {}end
function actor(id)
 local p={id=id,visible=true,enabled=true,updating=true,paused=false,world=true,event=false}
 local med={call=function(_,name,value)
  writes=writes+1
  if name=='set_drawSelf'then p.visible=value
  elseif name=='set_updateSelf'then p.updating=value
  else assert(name=='applyDrawSelf'or name=='applyUpdateSelf')end
 end}
 function p:call(name,value)
  if name=='get_playerID'then return self.id end
  if name=='get_isEventMove'then return self.event end
  if name=='get_cachedActivateMediator'then return med end
  if name=='get_cachedCharacterController'then return {call=function(_,n,v)assert(n=='set_Enabled');writes=writes+1;p.world=v end}end
  if name=='get_cachedSubCharacterController'then return nil end
  writes=writes+1
  if name=='pausePlayer'then self.paused=true elseif name=='set_Enable'then self.enabled=value
  else error('Unexpected mutation '..name)end
 end
 return p
end
active=actor(0);manager={call=function(_,name)assert(name=='get_manualPlayer');return active end}
''')
lua.globals().M=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
lua.execute('''
for _,id in ipairs({0,1,4})do
 active=actor(id);local v=actor(2);writes=0
 for _,event in ipairs({true,false})do
  v.event=event
  assert(not M.parkNonParty(manager,v))
  assert(not M.hideReserve(manager,v))
 end
 assert(writes==0 and v.visible and v.enabled and v.updating and not v.paused and v.world)
end
-- Existing Palace/Void reserve behavior is intentionally unchanged.
for _,gameMode in ipairs({3,4})do
 mode=gameMode;active=actor(0);local v=actor(2);writes=0
 assert(M.parkNonParty(manager,v))
 assert(writes>0 and not v.visible and not v.enabled and not v.updating and v.paused)
end
''')
print('PASS: M2 native V untouched before/during/after cameo, replacements and hero switches at 30/60/144 FPS; actual core hide/park do zero story mutations; Palace/Void behavior retained')
