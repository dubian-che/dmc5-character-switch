import sys
from pathlib import Path
sys.path.insert(0, 'work/python-deps')
from lupa import LuaRuntime
from lua_test_support import install_input_profile_helper

lua = LuaRuntime()
lua.execute('''
sdk={find_type_definition=function()return {get_methods=function()return {}end}end}
sdk.get_managed_singleton=function(name)
 assert(name=='app.GameManager')
 return {get_field=function(_,n)assert(n=='PlayingID');return profile or 0 end,set_field=function(_,key,value)assert(key=='PlayingID');profile=value end,
 call=function(_,name)assert(name=='updatePlayerPadInput');assert(profile==1)end}
end
dofile=function(path)
 if path:find('runtime')then return {withInputProfile=function(...)return realInputProfile(...)end,withControlProfile=function(...)return realControlProfile(...)end,selectManual=function(...)return realSelectManual(...)end,permits=function()return true end}end
 if path:find('hud') then return {request=function()end}end
 return {apply=function()end}
end
function scenario(bits)
 state={sub=bits,master=false,pad='cached',tree=false,think=true,world=false,draw=false,enabled=false,paused=true}
 local tree={call=function(_,name,value)
  if name=='set_Enabled' then state.tree=value end
 end}
 player={call=function(_,name,value)
  if name=='set_MediationType' then state.mediation=value
  elseif name=='set_isThinkEnable' then state.think=value
  elseif name=='subNetworkSubType' then state.sub=state.sub&(~value)
  elseif name=='updateNetworkCheckType' then state.master=state.sub&3==0
  elseif name=='resetPadInput' then state.pad=state.mediation==2 and 'live' or 'cached'
  elseif name=='get_cachedBehaviorTree' then return tree
  elseif name=='get_playerID' then return 1
  elseif (name=='get_isEventMove'or name=='get_isEventRun')then return false
  elseif name=='get_cachedRequestSetCollider' then return nil
  elseif name=='set_Enable'then state.enabled=value
  elseif name=='resumePlayer'then state.paused=false
  elseif name=='get_cachedActivateMediator'then return {call=function(_,key,v)
   if key=='set_drawSelf'then state.draw=v
   elseif key=='set_updateSelf'then state.updating=v
   else assert(key=='applyDrawSelf'or key=='applyUpdateSelf')end
  end}
  elseif name=='get_cachedCharacterController'then return {call=function(_,key,value)
   if key=='set_Enabled'then state.world=value else assert(key=='get_Enabled');return state.world end
  end}
  else error('Unexpected player call '..name)end
 end}
 manager={call=function(_,name)
  assert(name=='getPlayerByID' or name=='get_manualPlayer')
  return player
 end}
end
''')
install_input_profile_helper(lua)
core = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
for bits in (129, 130, 131, 16384):
    lua.globals().scenario(bits)
    core.switch(lua.globals().manager, 1)
    s = lua.globals().state
    assert s.master and s.pad == 'live' and s.tree and s.world
    assert s.draw and s.updating and s.enabled and not s.paused
    assert not s.think, 'native AI decision path still bypasses manual input'
    assert s.sub == (bits & ~3), 'unrelated native flags changed'
    core.switch(lua.globals().manager, 1)
    assert s.master and not s.think and s.sub == (bits & ~3)
print('PASS: current actor recovers human input from AI + Standby/StandbyWait, retains unrelated flags, and tolerates repeated handoff.')
