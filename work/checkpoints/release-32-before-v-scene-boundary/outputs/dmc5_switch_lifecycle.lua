-- Recover additional-player records left behind by a scene/mission reload.
local L=_G.dmc5_switch_lifecycle or {missing={},recovering={},repairs=0}
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
_G.dmc5_switch_lifecycle=L
L.elapsed=0
local supported={[0]=true,[1]=true,[4]=true}
function L.update(manager)
 local c=runtime.get(manager);local id=c.id
 local S=_G.dmc5_live_switch
 if S then S.current=id end
 if not supported[id] then L.missing={};L.elapsed=0;return end
 if c.paused then return end
 L.elapsed=L.elapsed+runtime.delta(c)
 if L.elapsed<.25-1e-8 then return end
 local elapsed=L.elapsed;L.elapsed=0
 local loader=sdk.get_managed_singleton('app.AdditionalPlayerLoadManager')
 if not loader then return end
 local records={}
 local list=loader:get_field('RequestedPlayerLoaderList')
 if not list then return end
 for i=0,list:call('get_Count')-1 do
  local item=list:call('get_Item',i)
  records[item:get_field('RequestedPlayerID')]=item:get_field('<CurrentState>k__BackingField')
 end
 for _,other in ipairs({0,1,4})do
  if manager:call('getPlayerByID',other)then
   L.missing[other]=nil;L.recovering[other]=nil
  elseif L.recovering[other] then
   -- Finish is asynchronous; wait for native cleanup before requesting again.
   if records[other]==nil then
    if other==4 then loader:call('requestPreloadPlayerResource',0)end
    loader:call('requestPreloadPlayerResource',other)
    L.recovering[other]=nil;L.missing[other]=nil
    L.repairs=L.repairs+1
   end
  elseif records[other]==6 then
   -- Do not mistake ordinary loading/activation for an orphaned actor.
   L.missing[other]=(L.missing[other] or 0)+elapsed
   if L.missing[other]>=2-1e-8 then
    loader:call('requestFinishPlayerResource',other)
    L.recovering[other]=true
   end
  else L.missing[other]=nil end
 end
end
if not L.hooked then
 sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
  local ok,why=pcall(L.update,sdk.to_managed_object(args[2]))
  if not ok then L.error=tostring(why)end
 end,function(ret)return ret end)
 L.hooked=true
end
return L
