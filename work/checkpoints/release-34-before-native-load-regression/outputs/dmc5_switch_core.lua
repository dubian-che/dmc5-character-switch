-- DMC5 live switch v33: native resource/body readiness and one-shot visibility completion.
local M={version=34,names={[0]='Nero',[1]='Dante',[4]='Vergil'}}
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
local hud=dofile('reframework/data/dmc5_switch_hud.lua')
local progression=dofile('reframework/data/dmc5_switch_progression.lua')
local regen=dofile('reframework/data/dmc5_switch_regen.lua')
local party=dofile('reframework/data/dmc5_party_hud.lua')
local voice=dofile('reframework/data/dmc5_switch_voice.lua')
local resources=dofile('reframework/data/dmc5_switch_resources.lua')
local lifecycle=dofile('reframework/data/dmc5_switch_lifecycle.lua')
local palace=dofile('reframework/data/dmc5_switch_palace.lua')
local entryAction
function M.restoreWorldCollision(player)
 -- The player/behavior-tree/attack-collider enable flags do not enable the
 -- native world CharacterController. A parked Dante can otherwise animate
 -- a root-motion dive through the floor with speedY still equal to zero.
 local controller=player:call('get_cachedCharacterController')
 assert(controller,'World CharacterController unavailable')
 controller:call('set_Enabled',true)
 assert(controller:call('get_Enabled'),'World CharacterController did not enable')
end
function M.parkWorldCollision(player)
 for _,name in ipairs({'get_cachedCharacterController','get_cachedSubCharacterController'})do
  local controller=player:call(name)
  if controller then controller:call('set_Enabled',false)end
 end
end
-- One-time handoff reset. Do not transport source action-local motion or
-- resume the reserve's old velocity. Native movement/gravity resumes next tick.
function M.clearMomentum(player)
 for _,name in ipairs({'inertiaVector','inertiaVectorNew','inertiaTmp','inertiaVectorReserved'})do
  player:call('set_'..name,Vector3f.new(0,0,0))
 end
 player:call('set_inertiaTimer',0.0)
 player:call('set_speedY',0.0)
 player:call('set_jumpMoveSpeedXZ',0.0)
end
function M.placeTarget(player,position,rotation,airborne,jumpCount)
 -- A direct warp does NOT consume RequestedWarpPos. Drain the native queue
 -- first, otherwise processWarpRequest can restore the reserve's old place.
 player:call('processWarpRequest')
 M.restoreWorldCollision(player)
 -- The last bool enters native CharacterController/collider relocation.
 -- Without it the enabled capsule remains at the reserve's old location
 -- and can write that position back across an arena barrier next update.
 player:call('warp',position,rotation,false,true)
 player:call('set_groundCheckTimer',0.0)
 player:call('checkGround')
 if airborne then
  player:call('set_jumpPhase',4);player:call('set_jumpCount',jumpCount)
 end
 M.clearMomentum(player)
end
function M.hideReserve(manager,player)
 if not runtime.permits(manager)then return false end
 if player==manager:call('get_manualPlayer')then return false end
 local med=player:call('get_cachedActivateMediator')
 if med then med:call('set_drawSelf',false);med:call('applyDrawSelf')end
 return true
end
local function showPlayer(player)
 local med=player:call('get_cachedActivateMediator')
 assert(med,'Selected player activation mediator unavailable')
 med:call('set_updateSelf',true);med:call('applyUpdateSelf')
 med:call('set_drawSelf',true);med:call('applyDrawSelf')
end
function M.parkNonParty(manager,player)
 if not runtime.permits(manager)then return false end
 -- V can already exist in the native manager without a load request from
 -- this Mod. Never initialize/unload him, or touch an actively controlled V.
 local owner=manager:call('get_manualPlayer')
 if not owner or not M.names[owner:call('get_playerID')] or player==owner then return false end
 if player:call('get_playerID')~=2 or player:call('get_isEventRun')then return false end
 player:call('pausePlayer');player:call('set_Enable',false)
 M.parkWorldCollision(player)
 local med=player:call('get_cachedActivateMediator')
 if med then
  med:call('set_updateSelf',false);med:call('applyUpdateSelf')
  med:call('set_drawSelf',false);med:call('applyDrawSelf')
 end
 return true
end
function M.prepareReserve(manager,player)
 if not runtime.permits(manager)then return false end
 if player==manager:call('get_manualPlayer')then return false end
 local owner=manager:call('get_manualPlayer')
 -- Called only once the native additional-player loader reports ready.
 local ok,why=pcall(function()
  player:call('MissionInitPlayerData');player:call('resetParameters',false)
  progression.apply(player)
 end)
 -- Native additional-player initialization may change the mission control
 -- target. Restore it before parking the reserve, without a gameplay switch.
 if owner then M.restoreLoadOwner(manager,owner)end
 player:call('pausePlayer');player:call('set_Enable',false)
 M.parkWorldCollision(player)
 M.hideReserve(manager,player)
 if not ok then error(why)end
 return true
end
function M.restoreLoadOwner(manager,owner)
 assert(runtime.permits(manager),'Scene is outside party scope')
 local id=owner:call('get_playerID')
 assert(manager:call('getPlayerByID',id)==owner,'Loading owner no longer belongs to this scene')
 local setting=sdk.get_managed_singleton('app.MissionSettingManager'):call('get_Setting')
 setting:call('set_ControllPlayerID',id);manager:call('updateManualPlayer')
 assert(manager:call('get_manualPlayer')==owner,'Could not restore loading owner')
 owner:call('set_Enable',true);owner:call('resumePlayer')
 M.restoreWorldCollision(owner)
 local camera=owner:call('get_camera')
 local accessor=camera and camera:call('get_player')
 if accessor then
  accessor:call('set_player',owner)
  accessor:set_field('PlayerTransform',owner:call('get_GameObject'):call('get_Transform'))
  camera:set_field('FollowCameraPlayer',id)
 end
 M.syncInput(id,owner)
 if not owner:call('get_isEventRun')then showPlayer(owner)end
end
function M.resetEntryAction(player,airborne)
 assert(entryAction,'Player action method unavailable')
 -- Parking freezes the behavior tree as well as the animation. A new main
 -- motion alone leaves the old action continuation and overlay alive.
 -- Native -1 selects the actor's resettable trees instead of hardcoding one.
 player:call('resetThink',true,-1)
 player:call('resetBlendRateLock')
 -- TDB67 parameters are initAdd/initOverwrite/isPuppetTransition, NOT force.
 -- Reset both auxiliary layers through native action exit/entry callbacks.
 -- Keep this before momentum restoration: Fall must not add a new jump.
 entryAction:call(player,airborne and 75 or 1,true,true,false,0,0.05,1)
end
function M.syncInput(id,player)
 local gm=sdk.get_managed_singleton('app.GameManager')
 assert(gm,'GameManager unavailable for input profile')
 -- Loads saved controller bindings and keyboard links. The native function
 -- maps playable Vergil (4) to his configuration slot (3).
 runtime.withInputProfile(gm,id,function()gm:call('updatePlayerPadInput')end)
 -- Native input refresh can replace Player.padInput. ChargeChecker keeps
 -- its own reference, so repair it after the profile refresh, not before it.
 if player and resources.bindPlayerChargeInputs then resources.bindPlayerChargeInputs(player)end
 if runtime.invalidate then runtime.invalidate()end
end
function M.dismissDoppel(player)
 if player:call('get_playerID')~=4 then return false end
 local clone=player:call('get_cachedDoppel')
 local active=player:call('get_DoppelMode')
 local pending=player:call('get_isGenerateDoppelWait')
 if active then player:call('setDoppelMode',false)end
 -- Cancel a pending summon before its owner is paused.
 if pending then player:call('set_isGenerateDoppelWait',false)end
 -- Native mode-off may defer withdrawal during a special action; also repair
 -- a previously stranded clone whose owner's mode is already off.
 if clone and clone:get_field('_DoppelValid')then
  player:call('destroyDoppelGanger',false,false)
 end
 return active or pending
end
local function bindControl(p)
 p:call('set_MediationType',2)
 -- IsThinkEnable selects AI decisions, not component activation. Native
 -- Player update skips manual commands when it is true (visible in BP).
 -- Restore the human-input path on both handoff and same-actor recovery.
 p:call('set_isThinkEnable',false)
 -- Standby/StandbyWait override ForceMaster and skip player logic.
 -- Only used for the selected, loaded actor; reserve actors stay paused.
 p:call('subNetworkSubType',1)
 p:call('subNetworkSubType',2)
 p:call('updateNetworkCheckType')
 p:call('resetPadInput',false)
end
for _,m in ipairs(sdk.find_type_definition('app.Player'):get_methods())do
 if m:get_name()=='setCommandAction' then
  local ps=m:get_param_types()
  if #ps==7 and ps[1]:get_full_name()=='app.Player.Actions' then entryAction=m end
 end
end
function M.recoverSelected(manager,player)
 assert(runtime.permits(manager),'Scene is outside party scope')
 assert(manager:call('get_manualPlayer')==player,'Recovery target is no longer selected')
 assert(not player:call('get_isEventRun'),'Recovery target entered an event')
 local id=player:call('get_playerID');assert(M.names[id],'Unsupported recovery target')
 bindControl(player)
 player:call('set_Enable',true);player:call('resumePlayer')
 M.restoreWorldCollision(player);M.syncInput(id,player)
 local tree=player:call('get_cachedBehaviorTree')
 if tree then tree:call('set_Enabled',true)end
 local collider=player:call('get_cachedRequestSetCollider')
 if collider then collider:call('set_Enabled',true)end
 showPlayer(player)
end
function M.switch(manager,id,source)
 assert(runtime.permits(manager),'Scene is outside party scope')
 assert(M.names[id],'Unsupported playable character')
 local target=manager:call('getPlayerByID',id)
 assert(target,'Character resources are not loaded')
 local previous=manager:call('get_manualPlayer')
 assert(previous,'No active gameplay player')
 progression.apply(target)
 if palace.beforeSwitch then palace.beforeSwitch(manager,id)end
 -- Additional Dante can retain a disabled collision request component.
 local collider=target:call('get_cachedRequestSetCollider')
 if collider then collider:call('set_Enabled',true)end
 if previous==target then
  M.recoverSelected(manager,target)
  if palace.selected then palace.selected(id,manager,id,source)end
  hud.request(manager,id);return {id=id,name=M.names[id],unchanged=true,version=M.version}
 end
 local transform=previous:call('get_GameObject'):call('get_Transform')
 local position=transform:call('get_Position')
 position=Vector3f.new(position.x,position.y,position.z)
 local rotation=transform:call('get_Rotation')
 local camera=previous:call('get_camera')
 local accessor=camera and camera:call('get_player')
 local air={speedY=previous:call('get_speedY'),height=previous:call('get_groundHeight'),count=previous:call('get_jumpCount')}
 -- A grounded actor may still expose a downward gravity/contact speed.
 -- Do not turn that contact velocity into a fresh Fall on the new actor.
 local airborne=not previous:call('isGround') or air.speedY>0.01
 local setting=sdk.get_managed_singleton('app.MissionSettingManager'):call('get_Setting')
 local previousID=previous:call('get_playerID')
 local function activate(p)
  bindControl(p)
  p:call('set_Enable',true);p:call('resumePlayer')
  M.restoreWorldCollision(p)
  -- Component activation is separate from the AI/manual-input decision.
  local tree=p:call('get_cachedBehaviorTree')
  if tree then tree:call('set_Enabled',true)end
  local collision=p:call('get_cachedRequestSetCollider')
  if collision then collision:call('set_Enabled',true)end
  showPlayer(p)
 end
 local function retarget(p,pid)
  if camera and accessor then
   accessor:call('set_player',p)
   accessor:set_field('PlayerTransform',p:call('get_GameObject'):call('get_Transform'))
   camera:set_field('FollowCameraPlayer',pid)
   p:call('set_camera',camera)
  else p:call('findCamera');p:call('changeFollowCamera',pid)end
 end
 local ok,why=pcall(function()
  -- Vergil's Doppel mode participates in his ordinary DT state. Withdraw
  -- it before checking that native Human mode has completed, otherwise the
  -- DT assertion can abort the handoff before dismissal is ever reached.
  M.dismissDoppel(previous)
  resources.retire(previous)
  activate(target)
  -- Repair both summons and transformations retained by earlier versions.
  M.dismissDoppel(target)
  resources.ensureHuman(target)
  -- Additional Dante's runtime PlayerData can omit Air Hike in The Void.
  if id==1 then
   local data=target:call('get_playerData')
   if data then data:set_field('IsDoubleJumpEnabled',true)end
  end
  M.resetEntryAction(target,airborne)
  -- Old action exit callbacks run during reset. Warp afterwards so their
  -- final transform/physics changes cannot overwrite the handoff position.
  M.placeTarget(target,position,rotation,airborne,air.count)
  setting:call('set_ControllPlayerID',id);manager:call('updateManualPlayer')
  M.syncInput(id,target)
  retarget(target,id)
  -- Apply last: warp, Wait/Fall entry and control rebinding may reset motion.
  -- Include zero vectors on the ground to erase a reserve's parked inertia.
  M.clearMomentum(target)
  previous:call('pausePlayer');previous:call('set_Enable',false)
  M.parkWorldCollision(previous)
  local med=previous:call('get_cachedActivateMediator')
  med:call('set_drawSelf',false);med:call('applyDrawSelf')
 end)
 if not ok then
  pcall(function()
   setting:call('set_ControllPlayerID',previousID);manager:call('updateManualPlayer')
   M.syncInput(previousID,previous)
   activate(previous);retarget(previous,previousID)
   target:call('pausePlayer');target:call('set_Enable',false)
   M.parkWorldCollision(target)
   local med=target:call('get_cachedActivateMediator')
   if med then med:call('set_drawSelf',false);med:call('applyDrawSelf')end
  end)
  error(why)
 end
 -- Deferred action/control updates can still write the parked position in
 -- this native update. Finalize once after it, never pin the actor per frame.
 M.placementSerial=(M.placementSerial or 0)+1
 local serial=M.placementSerial
 local loader=_G.dmc5_switch_loader
 local generation=loader and loader.generation
 runtime.afterUpdate(function()
  if not runtime.permits(manager)then return end
  if M.placementSerial~=serial or manager:call('get_manualPlayer')~=target or
   manager:call('getPlayerByID',id)~=target then return end
  if loader and (loader.manager~=manager or loader.generation~=generation)then return end
  if target:call('get_isEventRun')then return end
  M.placeTarget(target,position,rotation,airborne,air.count)
  -- Native activation in this update can reapply the reserve's draw flags.
  -- Complete visibility once with placement; never pin ordinary actions.
  showPlayer(target)
 end)
 if palace.selected then palace.selected(id,manager,previousID,source)end
 hud.request(manager,id)
 voice.play(target)
 return {hudStage=hud.stage,hudError=hud.error,id=id,name=M.names[id],version=M.version,airborne=airborne,speedYBefore=air.speedY,speedYAfter=target:call('get_speedY'),height=air.height,cameraPreserved=camera~=nil and accessor~=nil}
end
return M









