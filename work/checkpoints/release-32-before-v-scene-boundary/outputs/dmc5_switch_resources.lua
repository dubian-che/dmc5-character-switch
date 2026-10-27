-- Runtime-only party resource rules. Native pickup handles equip and HUD.
local R=_G.dmc5_switch_resources or {refills=0,elapsed=0}
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
_G.dmc5_switch_resources=R
function R.ensureHuman(player)
 local id=player:call('get_playerID')
 if id~=0 and id~=1 and id~=4 then return false end
 -- Clear the departing actor's held/queued transformation input as well as
 -- its form. These are input timers, not ordinary or Sin DT gauges.
 player:call('set_devilTriggerBtnOnTimer',0.0)
 player:call('set_devilTriggerPressTimer',0.0)
 if id==1 or id==4 then player:call('resetDevilTriggerPressCharge')end
 local devil=player:call('get_isDevilTrigger')
 local sin=(id==1 or id==4)and player:call('get_isTheDevilTrigger')
 if devil or sin then
  -- Use the character's native override so its model, effects and combat
  -- state all leave DT together. Human=0; immediate=true.
  player:call('setDevilTrigger',0,true)
 end
 player:call('set_isDevilTriggerTimeLineTriggered',false)
 assert(not player:call('get_isDevilTrigger'),'Devil Trigger exit failed for player '..id)
 if id==1 or id==4 then
  assert(not player:call('get_isTheDevilTrigger'),'Sin Devil Trigger exit failed for player '..id)
 end
 return devil or sin or false
end
function R.retire(player)
 return R.ensureHuman(player)
end
function R.refill(player)
 if player:call('get_playerID')~=0 or player:call('get_hp')<=0 then return false end
 if player:call('get_gauntletNum')~=0 or player:call('get_gauntletStackCount')~=0 then return false end
 if not player:call('get_isGauntletPickupEnabled')then return false end
 -- Base game's eight arms: exclude Empty and DLC-only resources.
 local id=math.random(0,7)
 player:call('pickupGauntlet',id)
 if player:call('get_gauntletNum')>0 or player:call('get_gauntletStackCount')>0 then
  R.refills=R.refills+1;R.lastArm=id;return true
 end
 return false
end
function R.resetNeroGun(player)
 if player:call('get_playerID')~=0 then return false end
 local charge=player:get_field('BlueRoseCharge')
 local input=player:call('get_padInput')
 if not charge or not input then return false end
 R.bindingAttempt={player=player,charge=charge,input=input,failed=true}
 -- Use normal native charge exit/reset. resetData/initBlueRoseCharge remove
 -- and register delegates, so they must not be used as a handoff repair.
 charge:call('forceEnd')
 charge:call('reset',false)
 charge:call('set_padInput',input)
 player:call('resetGunShotReserve')
 player:call('finishBRChargeEffect')
 R.bindingAttempt={player=player,charge=charge,input=input}
 return true
end
function R.bindNeroGunInput(player)
 if player:call('get_playerID')~=0 then return false end
 local charge=player:get_field('BlueRoseCharge')
 local input=player:call('get_padInput')
 if not charge or not input or charge:call('get_padInput')==input then return false end
 local previous=R.bindingAttempt
 if previous and previous.player==player and previous.failed and previous.charge==charge and previous.input==input then return false end
 if R.resetNeroGun(player)then R.inputRepairs=(R.inputRepairs or 0)+1;return true end
 return false
end
-- Native owner-input channels, described as data and handled by one lifecycle.
-- Vergil's DoppelJudgeMentCutCharge is clone-owned and remains native-managed.
local chargeFields={
 [0]={'GauntletCharge','ReinforcementCharge','RedQueenCharge'},
 [1]={'<chargeWeaponS00>k__BackingField','<chargeWeaponS01>k__BackingField','<chargeWeaponL00>k__BackingField','<chargeWeaponL01>k__BackingField','<chargeSheath>k__BackingField'},
 [4]={'<JudgeMentCutCharge>k__BackingField','<BeowulfCharge>k__BackingField','<RoundTripCharge>k__BackingField'},
}
local chargeAttempts={}
function R.bindPlayerChargeInputs(player)
 local id=player:call('get_playerID')
 if not chargeFields[id]then return false end
 -- Blue Rose also owns native shot reservations/effects; keep that cleanup.
 local changed=id==0 and R.bindNeroGunInput(player)or false
 if not player:call('get_Enable')or player:call('get_isEventRun')then return changed end
 local input=player:call('get_padInput');if not input then return changed end
 if not chargeAttempts[id]or chargeAttempts[id].player~=player then chargeAttempts[id]={player=player,fields={}}end
 local attempts=chargeAttempts[id].fields
 for _,name in ipairs(chargeFields[id])do
  local charge=player:get_field(name)
  -- Inactive weapon channels legitimately have no parameter/key. Never
  -- initialize them here or substitute a charge level, flag or callback.
  if charge and charge:call('get_padInput')~=input and charge:get_field('Enable')and
   charge:call('get_parameter')and charge:call('get_padInputFlag')~=0 then
   local previous=attempts[name]
   if not(previous and previous.player==player and previous.charge==charge and previous.input==input and previous.failed)then
    local attempt={player=player,charge=charge,input=input,failed=true};attempts[name]=attempt
    local ok,why=pcall(function()
     charge:call('forceEnd');charge:call('reset',false);charge:call('set_padInput',input)
     assert(charge:call('get_padInput')==input,'Charge input did not bind: '..name)
    end)
    if ok then
     attempt.failed=false;changed=true
     R.chargeInputRepairs=(R.chargeInputRepairs or 0)+1
    else R.chargeInputWarning=tostring(why)end
   end
  end
 end
 return changed
end
function R.captureChargeInputs(player)
 local id=player:call('get_playerID');local input=player:call('get_padInput')
 local function address(obj)return obj and tostring(obj:get_address())or nil end
 local out={ownerInput=address(input),channels={}}
 if input then out.buttonOn=input:call('get_buttonOnFlags');out.buttonTrigger=input:call('get_buttonTriggerFlags')end
 local names={}
 for _,name in ipairs(chargeFields[id]or {})do names[#names+1]=name end
 if id==0 then names[#names+1]='BlueRoseCharge'
 elseif id==4 then names[#names+1]='<DoppelJudgeMentCutCharge>k__BackingField'end
 for _,name in ipairs(names)do
  local charge=player:get_field(name)
  if charge then
   local bound=charge:call('get_padInput');local parameter=charge:call('get_parameter')
   out.channels[name]={address=address(charge),input=address(bound),ownerMatches=input~=nil and bound==input,
    policy=name=='<DoppelJudgeMentCutCharge>k__BackingField'and 'native clone input'or 'owner input',
    parameter=address(parameter),flag=charge:call('get_padInputFlag'),enabled=charge:get_field('Enable'),
    limit=charge:get_field('LimitLevel'),state=charge:get_field('<state>k__BackingField'),
    level=charge:get_field('<currentLevel>k__BackingField'),timer=charge:get_field('<timer>k__BackingField')}
  end
 end
 return out
end
local function readyActive(manager)
 local p=manager:call('get_manualPlayer');if not p then return nil end
 local id=p:call('get_playerID');if id~=0 and id~=1 and id~=4 then return nil end
 local loader=_G.dmc5_switch_loader
 if loader and(loader.manager~=manager or not loader.ready(manager,id))then return nil end
 return p
end
local function readyNero(manager)
 local p=manager:call('getPlayerByID',0)
 if not p then return nil end
 local loader=_G.dmc5_switch_loader
 -- Additional-player loading can briefly steal manual control before its
 -- input/charge objects finish initialization. Being manual is not sufficient.
 if loader and loader.manager==manager and loader.task and loader.task.id==0 and loader.known[0]~=p then return nil end
 if p==manager:call('get_manualPlayer')then return p end
 if loader and loader.manager==manager and loader.known[0]==p then return p end
 return nil
end
function R.syncActiveInput()
 local loader=_G.dmc5_switch_loader
 local manager=loader and loader.manager
 if not manager then return end
 local p=readyActive(manager)
 if p then R.bindPlayerChargeInputs(p)end
end
function R.tick(manager)
 local c=runtime.get(manager)
 if c.paused or not c.active then return end
 local dt=runtime.delta(c)
 if dt<=0 or dt>0.25 then return end
 R.elapsed=R.elapsed+dt
 if R.elapsed<0.25 then return end
 R.elapsed=0
 local nero=readyNero(manager)
 if nero then R.bindNeroGunInput(nero)end
 local p=readyActive(manager)
 if p then R.bindPlayerChargeInputs(p)end
 local palace=_G.dmc5_switch_palace
 if c.id==0 and(not palace or palace.canRefill())then R.refill(c.active)end
end
if not R.hooked then
 sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
  local ok,why=pcall(R.tick,sdk.to_managed_object(args[2]))
  if not ok then R.error=tostring(why)end
 end,function(ret)return ret end)
 R.hooked=true
end
return R
