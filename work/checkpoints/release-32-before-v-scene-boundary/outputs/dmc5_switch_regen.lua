-- Reserve regeneration: one HP segment / 2 sec, one ordinary DT segment / 5 sec.
if _G.dmc5_switch_regen then return _G.dmc5_switch_regen end
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
local R={version=3,secondsPerBar=5,healthSecondsPerBar=2,enabled=true,restored=0,healthRestored=0,stage='ready',elapsed=0,pending={}}
_G.dmc5_switch_regen=R
local ids={0,1,4}
local function allowed(id)
 local palace=_G.dmc5_switch_palace
 return not palace or palace.canRegen(id)
end
function R.flush(manager)
 for _,id in ipairs(ids)do
  local credit=R.pending[id] or 0;R.pending[id]=nil
  if credit>0 and allowed(id)then
   local p=manager:call('getPlayerByID',id)
   local hp=p and p:call('get_hp')
   if hp and hp>0 then
    local gauge=p:call('get_devilTriggerGauge');local cap=p:call('get_maxDevilTriggerGauge')
    if gauge>=0 and cap>0 and gauge<cap then
     local value=math.min(cap,gauge+credit)
     p:call('set_devilTriggerGauge',value);R.restored=R.restored+value-gauge
    end
    -- Share the earned background-time credit so handoff and Palace flushes
    -- account for HP/DT together without a second timer or stale scene credit.
    local maxHp=p:call('get_maxHp')
    if maxHp>0 and hp<maxHp then
     local value=math.min(maxHp,hp+credit*R.secondsPerBar/R.healthSecondsPerBar)
     p:call('set_hp',value);R.healthRestored=R.healthRestored+value-hp
    end
   end
  end
 end
end
function R.update(manager,seconds,paused,active)
 if not R.enabled or paused then R.stage=paused and 'paused' or 'disabled';return end
 if seconds<=0 or seconds>0.25 then return end
 active=active or manager:call('get_manualPlayer');if not active then R.stage='no player';R.pending={};R.elapsed=0;R.lastActive=nil;return end
 local id=active:call('get_playerID')
 if id~=0 and id~=1 and id~=4 then R.pending={};R.elapsed=0;R.lastActive=nil;return end
 if not allowed(id)then R.pending={};R.elapsed=0;R.lastActive=nil;R.stage='Palace loading';return end
 if R.lastActive and (R.manager~=manager or R.lastActive~=active) then
  -- Flush earned fractions before changing which character is excluded.
  -- A replaced actor with the same ID indicates a new scene, not a handoff.
  if R.manager~=manager or R.lastID==id then R.pending={};R.elapsed=0 else R.flush(manager)end
 end
 R.lastActive=active;R.lastID=id;R.manager=manager
 R.stage='running'
 local increment=1000.0/R.secondsPerBar*seconds
 for _,otherID in ipairs(ids)do
  if otherID~=id and allowed(otherID)then
   R.pending[otherID]=(R.pending[otherID] or 0)+increment
  end
 end
 R.elapsed=R.elapsed+seconds
 if R.elapsed>=.1-1e-8 then R.flush(manager);R.elapsed=0 end
end
function R.tick(manager)
 local c=runtime.get(manager)
 if not c.active or (c.id~=0 and c.id~=1 and c.id~=4) then
  R.pending={};R.elapsed=0;R.lastActive=nil;R.stage='no player';return
 end
 R.update(manager,runtime.delta(c),c.paused,c.active)
end
sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
 local ok,why=pcall(R.tick,sdk.to_managed_object(args[2]))
 if not ok then R.error=tostring(why);R.stage='error'end
end,function(ret)return ret end)
return R
