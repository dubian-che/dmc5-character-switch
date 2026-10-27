-- Original character voice events sampled from each character's Provoke01.
local V=_G.dmc5_switch_voice or {version=1,enabled=true,played=0}
_G.dmc5_switch_voice=V
V.events={[0]=3980769701,[1]=1333036904,[4]=1889147200}
local function method(typeName,name,param)
 for _,m in ipairs(sdk.find_type_definition(typeName):get_methods())do
  local ps=m:get_param_types()
  if m:get_name()==name and #ps==1 and ps[1]:get_full_name()==param then return m end
 end
end
local trigger=method('app.character.Character','triggerVoice','System.UInt32')
local exists=method('via.wwise.WwiseContainer','exists','System.UInt32')
function V.play(player)
 if not V.enabled then return false end
 local ok,result=pcall(function()
  local id=player:call('get_playerID');local event=V.events[id]
  if not event then return false end
  assert(trigger and exists,'Voice interface unavailable')
  local container=player:call('get_GameObject'):call('getComponent',sdk.typeof('app.WwiseContainerApp'))
  if not container or not exists:call(container,event)then error('Character voice event is not loaded')end
  trigger:call(player,event)
  V.lastPlayer=id;V.lastEvent=event;V.played=V.played+1;V.error=nil
  return true
 end)
 if not ok then V.error=tostring(result);return false end
 return result
end
return V
