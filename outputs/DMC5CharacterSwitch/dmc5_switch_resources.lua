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
function R.dismissSpiralSwords(player)
 if player:call('get_playerID')~=4 or player:get_field('IsDoppel')then return 0 end
 local list=player:get_field('summonedSwordsControllers')
 if not list then return 0 end
 -- Snapshot before cancellation: native cleanup may change the live list.
 local pending={}
 for i=0,list:call('get_Count')-1 do
  local controller=list:call('get_Item',i)
  if controller and controller:get_type_definition():get_name()=='SpiralSwordsController'and
   controller:call('get_owner')==player and not controller:call('get_isEnd')then
   pending[#pending+1]=controller
  end
 end
 for _,controller in ipairs(pending)do
  -- Native cancel finishes every shell, clears shellList and marks isEnd.
  -- Do this while the owner still updates; hiding alone leaves frozen shells.
  controller:call('cancel')
  assert(controller:call('get_isEnd'),'Spiral Swords cancellation did not finish')
 end
 return #pending
end
-- Finish the native V-mode sequence before parking its owner. Resetting only
-- the entry action can leave V's visibility and Vergil's material replacement
-- out of sync. Never write material flags without restoring their resources.
function R.finishWorldV(player)
 if player:call('get_playerID')~=4 or player:get_field('IsDoppel')then return false end
 local summoned=player:call('get_isSummonGilver')
 local material=player:get_field('isChangeMaterialVmode')
 local v=player:get_field('summonGilver')
 local visibleV=v and v:call('get_ownerVergilPL')==player and v:call('get_Enable')
 if not summoned and not material and not visibleV then return false end
 -- No warp: the handoff owns placement. Reset astral state and stop the
 -- native sequence so it cannot reapply a late material/visibility change.
 player:call('vModeEnd',false,true,true)
 return true
end
function R.retire(player)
 R.finishWorldV(player)
 R.dismissSpiralSwords(player)
 return R.ensureHuman(player)
end
function R.parkWorldVChild(owner,v,draw,update)
 if not owner or owner:call('get_playerID')~=4 or owner:get_field('IsDoppel')or
  owner:get_field('summonGilver')~=v or not v or v:call('get_ownerVergilPL')~=owner then return false end
 local med=v:call('get_cachedActivateMediator');if not med then return false end
 local saved=R.parkedWorldV
 if not saved or saved.owner~=owner or saved.summon~=v then
  if draw==nil then draw=med:call('get_drawSelf')end
  if update==nil then update=med:call('get_updateSelf')end
  R.parkedWorldV={owner=owner,summon=v,draw=draw,update=update}
 end
 v:call('set_Enable',false)
 med:call('set_drawSelf',false);med:call('applyDrawSelf')
 med:call('set_updateSelf',false);med:call('applyUpdateSelf')
 assert(not v:call('get_Enable')and not med:call('get_drawSelf')and not med:call('get_updateSelf'),'Reserve V did not park')
 return true
end
function R.restoreWorldVChild(owner,manager)
 local saved=R.parkedWorldV
 if not saved or saved.owner~=owner or not runtime.permits(manager)or manager:call('get_manualPlayer')~=owner then return false end
 if owner:get_field('IsDoppel')or owner:get_field('summonGilver')~=saved.summon or saved.summon:call('get_ownerVergilPL')~=owner then
  R.parkedWorldV=nil;return false
 end
 local med=saved.summon:call('get_cachedActivateMediator');if not med then return false end
 med:call('set_updateSelf',saved.update);med:call('applyUpdateSelf')
 med:call('set_drawSelf',saved.draw);med:call('applyDrawSelf')
 R.parkedWorldV=nil;R.worldVChildRestores=(R.worldVChildRestores or 0)+1
 return true
end
-- Restore only at native skill entry, not when merely selecting Vergil.
do
 local ok,why=pcall(function()
  local init=sdk.find_type_definition('app.PlayerVergilPL'):get_method('vModeInit')
  assert(init,'World of V init method unavailable')
  sdk.hook(init,function(args)
   local good,err=pcall(R.restoreWorldVChild,sdk.to_managed_object(args[2]),sdk.get_managed_singleton('app.PlayerManager'))
   if not good then R.worldVChildError=tostring(err)end
  end,function(ret)return ret end)
  R.worldVChildRestoreHook=true
 end)
 if not ok then R.worldVChildError=tostring(why)end
end
-- Native PlayerV.resetStatus re-enables drawing even for an inactive World V
-- child. Preserve its hidden state across that reset, including Palace events.
function R.captureWorldVReset(v)
 local gm=sdk.get_managed_singleton('app.GameManager')
 if not gm or gm:call('get_gameMode')~=3 or not v or v:call('get_Enable')~=false then return nil end
 local owner=v:call('get_ownerVergilPL')
 if not owner or owner:call('get_playerID')~=4 or owner:get_field('IsDoppel')or
  owner:get_field('summonGilver')~=v or owner:call('get_isSummonGilver')then return nil end
 local med=v:call('get_cachedActivateMediator')
 if not med or med:call('get_drawSelf')~=false then return nil end
 return {v=v,owner=owner,med=med}
end
function R.finishWorldVReset(saved)
 if not saved then return false end
 local v,owner=saved.v,saved.owner
 local gm=sdk.get_managed_singleton('app.GameManager')
 if not gm or gm:call('get_gameMode')~=3 or v:call('get_Enable')~=false or
  v:call('get_ownerVergilPL')~=owner or owner:get_field('summonGilver')~=v or
  owner:call('get_isSummonGilver')or v:call('get_cachedActivateMediator')~=saved.med then return false end
 if saved.med:call('get_drawSelf')~=true then return false end
 v:call('set_drawSelf',false)
 R.worldVResetRepairs=(R.worldVResetRepairs or 0)+1
 return true
end
do
 local ok,why=pcall(function()
  local method=sdk.find_type_definition('app.PlayerV'):get_method('resetStatus')
  assert(method,'World V reset method unavailable')
  sdk.hook(method,function(args)
   local storage=thread.get_hook_storage()
   local good,saved=pcall(R.captureWorldVReset,sdk.to_managed_object(args[2]))
   storage.worldVResetHidden=good and saved or nil
   if not good then R.worldVResetError=tostring(saved)end
  end,function(ret)
   local storage=thread.get_hook_storage()
   local saved=storage.worldVResetHidden;storage.worldVResetHidden=nil
   local good,why=pcall(R.finishWorldVReset,saved)
   if not good then R.worldVResetError=tostring(why)end
   return ret
  end)
  R.worldVResetHook=true
 end)
 if not ok then R.worldVResetError=tostring(why)end
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
 if not player:call('get_Enable')or player:call('get_isEventMove')then return changed end
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
 if loader then
  if loader.manager==manager and loader.ready(manager,0)then return p end
  return nil
 end
 if p==manager:call('get_manualPlayer')then return p end
 return nil
end
function R.syncActiveInput()
 local loader=_G.dmc5_switch_loader
 local manager=runtime.manager or(loader and loader.manager)
 if not manager then return end
 if not runtime.permits(manager)then return end
 local p=readyActive(manager)
 if p then R.bindPlayerChargeInputs(p)end
end
function R.tick(manager)
 if not runtime.permits(manager)then R.elapsed=0;return end
 local c=runtime.get(manager)
 if c.paused or not c.active then return end
 R.ensureWorldVSummonRunning(manager)
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
 if nero==c.active and c.id==0 and(not palace or palace.canRefill())then R.refill(nero)end
end
if not R.hooked then
 sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
  local ok,why=pcall(R.tick,sdk.to_managed_object(args[2]))
  if not ok then R.error=tostring(why)end
 end,function(ret)return ret end)
 R.hooked=true
end
-- FollowCameraV resolves ID 2 globally, which can select a cameo player's V.
-- Override only that camera call's lookup, never general gameplay lookups.
function R.worldVCameraOwner(camera,manager)
 if not camera or not manager then return nil end
 local owner=manager:call('get_manualPlayer')
 if not owner or owner:call('get_playerID')~=4 or owner:get_field('IsDoppel')then return nil end
 if owner:call('get_camera')~=camera or not owner:call('get_isSummonGilver')then return nil end
 local summon=owner:get_field('summonGilver')
 if not summon or summon:call('get_playerID')~=2 or summon:call('get_ownerVergilPL')~=owner then return nil end
 return {manager=manager,owner=owner,summon=summon}
end
function R.repairWorldVCamera(camera,manager)
 if not runtime.permits(manager)or not camera or camera:get_field('FollowCameraPlayer')~=2 then return false end
 local scope=R.worldVCameraOwner(camera,manager)
 if not scope or not scope.summon:call('get_Enable')then return false end
 local accessor=camera:call('get_player')
 if not accessor or accessor:get_type_definition():get_full_name()~='app.PlayerAccessor'then return false end
 local target=accessor:call('get_player')
 if target==scope.summon or not target or target:call('get_playerID')~=2 then return false end
 -- Correct only this camera's accessor; never move, hide or control another V.
 accessor:call('set_player',scope.summon)
 assert(accessor:call('get_player')==scope.summon,'World of V camera target did not bind')
 R.worldVCameraRepairs=(R.worldVCameraRepairs or 0)+1
 return true
end
function R.ensureWorldVSummonRunning(manager)
 if not runtime.permits(manager)then return false end
 local owner=manager:call('get_manualPlayer')
 if not owner or owner:call('get_playerID')~=4 then return false end
 local scope=R.worldVCameraOwner(owner:call('get_camera'),manager)
 if not scope or not scope.summon:call('get_Enable')then return false end
 local tree=scope.summon:call('get_cachedBehaviorTree')
 if not tree or tree:call('get_Enabled')then return false end
 -- Native World of V has enabled its summon and queued its action. The
 -- reserve lifecycle can leave the child tree disabled; resume that tree
 -- without resetting its pending native action, position, or pause state.
 tree:call('set_Enabled',true)
 assert(tree:call('get_Enabled'),'World of V summon behavior tree did not resume')
 R.worldVTreeRepairs=(R.worldVTreeRepairs or 0)+1
 return true
end
function R.prepareWorldVAction(summon,action,manager)
 -- Native vModeInvocation requests PlayerV action 28. Standby (bits 1/2)
 -- makes isNonMasterSetAction reject it before the FSM receives the request.
 if action~=28 or not summon or not runtime.permits(manager)then return false end
 local owner=manager:call('get_manualPlayer')
 if not owner or owner:call('get_playerID')~=4 then return false end
 local scope=R.worldVCameraOwner(owner:call('get_camera'),manager)
 if not scope or scope.summon~=summon or not summon:call('get_Enable')then return false end
 summon:call('subNetworkSubType',1)
 summon:call('subNetworkSubType',2)
 summon:call('updateNetworkCheckType')
 R.ensureWorldVSummonRunning(manager)
 R.worldVActionPrepares=(R.worldVActionPrepares or 0)+1
 return true
end
if not R.worldVActionHooked then
 local ok,why=pcall(function()
  local action=sdk.find_type_definition('app.PlayerV'):get_method('setAction')
  assert(action,'World of V action method unavailable')
  sdk.hook(action,function(args)
   local good,err=pcall(R.prepareWorldVAction,sdk.to_managed_object(args[2]),sdk.to_int64(args[3]),sdk.get_managed_singleton('app.PlayerManager'))
   if not good then R.worldVActionError=tostring(err)end
  end,function(ret)return ret end)
  R.worldVActionHooked=true
 end)
 if not ok then R.worldVActionError=tostring(why)end
end
if not R.worldVCameraGuardHooked then
 local ok,why=pcall(function()
  local update=sdk.find_type_definition('app.PlayerCameraController'):get_method('updateCamera')
  assert(update,'World of V camera update unavailable')
  sdk.hook(update,function(args)
   local good,err=pcall(R.repairWorldVCamera,sdk.to_managed_object(args[2]),sdk.get_managed_singleton('app.PlayerManager'))
   if not good then R.worldVCameraError=tostring(err)end
  end,function(ret)return ret end)
  R.worldVCameraGuardHooked=true
 end)
 if not ok then R.worldVCameraError=tostring(why)end
end
if not R.worldVCameraHooked then
 local scopesByThread={}
 local ok,why=pcall(function()
  local follow=sdk.find_type_definition('app.PlayerCameraController'):get_method('FollowCameraV(System.Boolean)')
  local late=sdk.find_type_definition('app.PlayerCameraController'):get_method('lateUpdate')
  local lookup=sdk.find_type_definition('app.PlayerManager'):get_method('getPlayerByID(app.PlayerID)')
  assert(follow and late and lookup and type(thread.get_id)=='function','World of V camera methods unavailable')
  local function enter(args)
   local storage=thread.get_hook_storage()
   local id=thread.get_id();storage.worldVCameraThread=id
   scopesByThread[id]=scopesByThread[id]or{}
   local frame={};table.insert(scopesByThread[id],frame)
   local good,scope=pcall(R.worldVCameraOwner,sdk.to_managed_object(args[2]),sdk.get_managed_singleton('app.PlayerManager'))
   if good then frame.scope=scope else R.worldVCameraError=tostring(scope)end
  end
  local function leave(ret)
   local id=thread.get_hook_storage().worldVCameraThread
   local frames=id and scopesByThread[id]
   if frames then table.remove(frames);if #frames==0 then scopesByThread[id]=nil end end
   return ret
  end
  sdk.hook(follow,enter,leave)
  -- lateUpdate selects FollowCameraPlayer again every frame, using the shared
  -- getPlayerByID call at C05A3C (the ID-2 branch jumps there from C05C3D).
  -- Scope that lookup before native camera position calculation as well.
  sdk.hook(late,enter,leave)
  R.worldVCameraLateHooked=true
  sdk.hook(lookup,function(args)
   local storage=thread.get_hook_storage()
   local scopes=scopesByThread[thread.get_id()]
   local scope=scopes and scopes[#scopes]and scopes[#scopes].scope
   if scope and sdk.to_int64(args[3])==2 and sdk.to_managed_object(args[2])==scope.manager then
    storage.worldVCameraSummon=scope.summon
   end
  end,function(ret)
   local summon=thread.get_hook_storage().worldVCameraSummon
   if summon then
    R.worldVCameraSelections=(R.worldVCameraSelections or 0)+1
    return sdk.to_ptr(summon)
   end
   return ret
  end)
  R.worldVCameraHooked=true
 end)
 if not ok then R.worldVCameraError=tostring(why)end
end
return R
