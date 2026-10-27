import sys
from pathlib import Path
sys.path.insert(0, 'work/python-deps')
from lupa import LuaRuntime
from lua_test_support import install_input_profile_helper

lua = LuaRuntime()
lua.execute('''
sdk={find_type_definition=function()return {get_methods=function()return {}end}end}
unlocks=0
dofile=function(path)if path:find('runtime')then return {withInputProfile=function(...)return realInputProfile(...)end,withControlProfile=function(...)return realControlProfile(...)end,selectManual=function(...)return realSelectManual(...)end,permits=function()return true end}end;return {apply=function()unlocks=unlocks+1 end}end
function actor(id)
 local p={id=id,calls={},draw=true,enabled=true,position='unchanged',action='unchanged',world=true,sub=true}
 local med={call=function(_,name,value)
  if name=='set_drawSelf'then p.draw=value
  elseif name=='set_updateSelf'then p.updating=value
  elseif name~='applyDrawSelf'and name~='applyUpdateSelf'then error(name)end
 end}
 function p:call(name,value)
  self.calls[#self.calls+1]=name
  if name=='get_playerID'then return self.id
  elseif (name=='get_isEventMove'or name=='get_isEventRun')then return false
  elseif name=='get_camera'then return nil
  elseif name=='get_cachedActivateMediator'then return med
  elseif name=='get_cachedCharacterController'or name=='get_cachedSubCharacterController'then
   local key=name=='get_cachedCharacterController'and 'world'or 'sub'
   return {call=function(_,method,value)
    if method=='set_Enabled'then p[key]=value else assert(method=='get_Enabled');return p[key]end
   end}
  elseif name=='set_Enable'then self.enabled=value
  elseif name=='pausePlayer'then self.paused=true
  elseif name=='resumePlayer'then self.paused=false
  elseif name=='MissionInitPlayerData'then self.initialized=true;active=self;controlID=self.id
  elseif name=='resetParameters'then assert(value==false)
  else error('Unexpected preparation mutation: '..name)end
 end
 return p
end
current=actor(0);reserve=actor(1);active=current;controlID=0
manager={call=function(_,name,id)
 if name=='get_manualPlayer'then return active
 elseif name=='getPlayerByID'then return id==0 and current or reserve
 else assert(name=='updateManualPlayer');active=controlID==0 and current or reserve end
end}
local setting={call=function(_,name,id)if name=='get_ControllPlayerID'then return controlID end;assert(name=='set_ControllPlayerID');controlID=id end}
sdk.get_managed_singleton=function(name)
 if name=='app.MissionSettingManager'then return {call=function()return setting end}end
 assert(name=='app.GameManager')
 return {get_field=function(_,n)assert(n=='PlayingID');return profile or 0 end,set_field=function(_,name,id)assert(name=='PlayingID');profile=id end,
 call=function(_,name)assert(name=='updatePlayerPadInput')end}
end
''')
install_input_profile_helper(lua)
core = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
lua.globals().M = core
lua.execute('''
assert(not M.hideReserve(manager,current))
assert(not M.prepareReserve(manager,current))
assert(#current.calls==0 and current.draw and current.enabled and unlocks==0)
assert(M.hideReserve(manager,reserve))
assert(not reserve.draw and reserve.enabled and not reserve.paused and not reserve.initialized)
assert(M.prepareReserve(manager,reserve))
assert(reserve.initialized and reserve.paused and not reserve.enabled and not reserve.draw)
assert(not reserve.world and not reserve.sub and current.world)
assert(unlocks==1 and active==current and controlID==0 and profile==0)
assert(current.enabled and not current.paused and current.draw)
assert(current.position=='unchanged' and current.action=='unchanged')
current.draw=false;current.updating=false
M.restoreLoadOwner(manager,current)
assert(current.draw and current.updating,'restored load owner remained invisible')
''')
print('PASS: native initialization control steal restored; original position/action retained; ready reserve parked/hidden; early hide does not pause loading.')
