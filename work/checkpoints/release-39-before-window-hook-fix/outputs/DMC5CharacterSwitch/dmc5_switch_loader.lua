-- One shared load queue for automatic warm-up and explicit switch requests.
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
local B=_G.dmc5_switch_loader or {generation=0,clock=0,elapsed=0,known={},retry={},attempts={},available={},count=0,stage='waiting for gameplay'}
_G.dmc5_switch_loader=B
local ids={0,1,4}
local supported={[0]=true,[1]=true,[4]=true}
function B.reset(manager)
 B.generation=B.generation+1;B.manager=manager;B.known={};B.task=nil
 B.additional={};B.prepared={};B.observedManual=nil
 B.activation=nil
 B.sceneMode=nil;B.storyMission=nil;B.awaitNative=nil;B.arrivalReady=0
 B.retry={};B.attempts={};B.available={};B.count=0;B.clock=0;B.elapsed=0;B.error=nil
 B.stage='waiting for gameplay';B.playable=false;B.excludedV=nil
end
local function bodyReady(actor)
 local meshes=actor and actor:call('get_bodyMeshList')
 if not meshes then return false end
 for i=0,math.min(meshes:get_size(),32)-1 do
  if meshes:get_element(i)~=nil then return true end
 end
 return false
end
function B.ready(manager,id)
 local actor=manager:call('getPlayerByID',id)
 if not actor or B.known[id]~=actor or not bodyReady(actor)then return false end
 if B.additional and B.additional[id]then
  local loader=sdk.get_managed_singleton('app.AdditionalPlayerLoadManager')
  return loader~=nil and loader:call('isReadyPlayerResource',id,0,0)
 end
 return true
end
function B.selected(manager,id)
 if B.manager~=manager then return end
 local actor=manager:call('get_manualPlayer')
 if not actor or actor:call('get_playerID')~=id or B.known[id]~=actor then return end
 B.observedManual=actor
 B.activation={actor=actor,generation=B.generation,elapsed=0,updates=0,bad=0}
 if B.task then
  if B.task.id==id then B.task=nil
  else B.task.owner=actor;B.task.ownerID=id end
 end
end
local function confirmActivation(manager,core,c,requested)
 local t=B.activation;if not t then return end
 if requested or B.generation~=t.generation or c.active~=t.actor or not supported[c.id] then B.activation=nil;return end
 if c.paused or c.active:call('get_isEventRun')then t.bad=0;return end
 local p=c.active
 if B.task or not B.ready(manager,c.id)then t.bad=0;return end
 local palace=_G.dmc5_switch_palace
 if palace and palace.canRegen and not palace.canRegen(c.id)then t.bad=0;return end
 t.elapsed=t.elapsed+runtime.delta(c);t.updates=t.updates+1
 if t.elapsed>1 or t.updates>180 then B.activation=nil;return end
 if p:call('get_Enable')then t.bad=0;return end
 local med=p:call('get_cachedActivateMediator')
 -- Both captured Nero/Dante failures had an updating component but a
 -- disabled, hidden logical player. Normal action hiding keeps Enable true.
 if p:call('get_hp')<=0 or p:call('get_isDevilTrigger')or(c.id~=0 and p:call('get_isTheDevilTrigger'))or
  p:call('get_Enabled')~=true or not med or med:call('get_drawSelf')~=false or med:call('get_updateSelf')~=true then t.bad=0;return end
 t.bad=t.bad+1;if t.bad<3 then return end
 -- One attempt per successful selection, with no equipment/action/warp reset.
 B.activation=nil
 local ok,why=pcall(core.recoverSelected,manager,p)
 if ok then B.activationRepairs=(B.activationRepairs or 0)+1
 else B.activationError=tostring(why)end
end
local function recordState(loader,id)
 local list=loader:get_field('RequestedPlayerLoaderList')
 if not list then return nil end
 for i=0,list:call('get_Count')-1 do
  local item=list:call('get_Item',i)
  if item:get_field('RequestedPlayerID')==id then return item:get_field('<CurrentState>k__BackingField')end
 end
end
local function recovering(id)
 local life=_G.dmc5_switch_lifecycle
 return life and life.recovering[id]
end
local function inspect(loader,r,actor)
 local state=recordState(loader,r.id)
 if recovering(r.id) or state==7 or state==8 or (state==6 and not actor)then
  -- Lifecycle owns cleanup of completed records with no actor. Never load
  -- through a record which is still being finished by the native engine.
  r.phase='recovery';return
 end
 if state and state>=3 and state<=6 then r.phase='load';return end
 if r.id==4 then loader:call('requestPreloadPlayerResource',0)end
 if state==nil then loader:call('requestPreloadPlayerResource',r.id)end
 r.phase='preload'
end
local function step(manager,loader,core)
 local r=B.task
 local actor=manager:call('getPlayerByID',r.id)
 if B.clock-r.start>60 then error('Character preparation timed out: '..r.id)end
 if actor and actor==manager:call('get_manualPlayer')then
  local state=recordState(loader,r.id)
  if (state==nil or state<3 or(state==6 and loader:call('isReadyPlayerResource',r.id,0,0)))and bodyReady(actor)then
   B.known[r.id]=actor;B.prepared[r.id]=actor;B.additional[r.id]=state==6;B.task=nil
   B.activation={actor=actor,generation=B.generation,elapsed=0,updates=0,bad=0}
  end
  return
 end
 if r.phase=='inspect' or r.phase=='recovery' then
  inspect(loader,r,actor)
 elseif r.phase=='preload' then
  -- Native updateState cancels an in-flight additional load while the
  -- location is busy. Wait for that same native boundary before requesting.
  local location=sdk.get_managed_singleton('app.LocationEnvManager')
  if location and location:call('get_isBusy')then return end
  if B.clock>=(r.nextLoad or 0)and not recovering(r.id) and loader:call('isReadyPreloadPlayerResource',r.id)then
   r.owner=manager:call('get_manualPlayer')
   r.ownerID=r.owner and r.owner:call('get_playerID')
   r.loadTries=(r.loadTries or 0)+1
   loader:call('requestLoadPlayerResource',r.id,0,0,false)
   -- The native void request can refuse without throwing (for example,
   -- before PlayerLoadManager is available). State 2 is only preloaded.
   local state=recordState(loader,r.id)
   if state and state>=3 and state<=6 then r.phase='load'
   else
    assert(r.loadTries<3,'Native load request was not accepted: '..r.id)
    r.nextLoad=B.clock+.5
   end
  end
 elseif r.phase=='load' then
  local state=recordState(loader,r.id)
  if not actor and state==2 then
   -- Accepted requests can later be unloaded back to Preloaded. No actor
   -- exists to publish, and the native state will not advance by waiting.
   assert((r.loadTries or 0)<3,'Native load repeatedly returned to preload: '..r.id)
   r.hidden=nil;r.phase='preload';r.nextLoad=B.clock+.5
   r.regressions=(r.regressions or 0)+1
   return
  end
  -- Rendering may start before the load is complete. Hide once, but do not
  -- pause the actor until the native loader confirms it has finished.
  if actor and r.hidden~=actor then core.hideReserve(manager,actor);r.hidden=actor end
  if actor and loader:call('isReadyPlayerResource',r.id,0,0)and bodyReady(actor)then
   if B.prepared[r.id]~=actor then core.prepareReserve(manager,actor);B.prepared[r.id]=actor end
   B.known[r.id]=actor;B.additional[r.id]=true;B.retry[r.id]=nil;B.attempts[r.id]=nil;B.task=nil
  elseif not actor and r.hidden then
   r.hidden=nil;r.phase='inspect'
  end
 end
end
function B.update(manager,core,requested)
 if not runtime.permits(manager)then
  if B.manager then B.reset(nil)end
  return
 end
 local c=runtime.get(manager)
 local mode=c.gm and c.gm:call('get_gameMode')
 local mission=mode==0 and c.gm:call('get_missionNo')or nil
 local retrySerial=runtime.storyRetrySerial
 local function resetScene()
  local prepared=B.prepared or {}
  local known=B.known or {};local additional=B.additional or {}
  B.reset(manager);B.sceneMode=mode;B.storyMission=mission
  B.storyRetrySerial=retrySerial
  -- Carried native instances are already initialized. Keep that fact only
  -- when this manager still registers the exact object, never by ID alone.
  for id,p in pairs(prepared)do
   if manager:call('getPlayerByID',id)==p then
    B.prepared[id]=p
    local native=sdk.get_managed_singleton('app.AdditionalPlayerLoadManager')
    if known[id]==p and bodyReady(p)and(not additional[id]or(native and native:call('isReadyPlayerResource',id,0,0)))then
     B.known[id]=p;B.additional[id]=additional[id]
    end
   end
  end
  B.observedManual=c.active
  B.awaitNative=mode==0;B.arrivalReady=0
 end
 -- Story transitions may retain PlayerManager and the old selected actor.
 -- Cancel the old queue BEFORE its loading-owner restoration can undo the
 -- incoming mission's native control handoff.
 if B.manager~=manager or B.sceneMode~=mode or B.storyMission~=mission or B.storyRetrySerial~=retrySerial then resetScene()end
 local loading=B.task
 if B.manager==manager and loading and loading.owner and
  manager:call('getPlayerByID',loading.ownerID)==loading.owner then
  local active=manager:call('get_manualPlayer')
  local reserve=manager:call('getPlayerByID',loading.id)
  if active==reserve and active~=loading.owner then
   core.restoreLoadOwner(manager,loading.owner)
   runtime.invalidate()
  end
 end
 c=runtime.get(manager)
 if not supported[c.id] then
  if B.manager then B.reset(nil)end
  return
 end
 -- A normal handoff selects an already known actor. An unknown/replaced
 -- manual actor (even with the same ID) starts a new scene's preparation.
 if B.manager~=manager or(B.known[c.id]~=c.active and B.observedManual~=c.active)then
  resetScene()
 end
 if B.awaitNative then
  local nativeID=c.gm:call('findManualPlayerID')
  if not c.paused and c.id~=nativeID and supported[nativeID]and not c.active:call('get_isEventRun')then
   local owner=manager:call('getPlayerByID',nativeID)
   if owner and bodyReady(owner)and owner:call('get_Enable')==true and owner:call('get_Enabled')==true and
    owner:call('get_hp')>0 and not owner:call('get_isEventRun')then
    local med=owner:call('get_cachedActivateMediator')
    local object=owner:call('get_GameObject')
    local world=owner:call('get_cachedCharacterController')
    if med and med:call('get_updateSelf')==true and object and object:call('get_UpdateSelf')==true and
     world and world:call('get_Enabled')==true then
     -- Native scripts may create/enable the new hero without replacing
     -- our previous mission's manual pointer. Complete that handoff once.
     -- No load, action reset, initialization, warp or resource restoration.
     local previous=c.active
     core.restoreLoadOwner(manager,owner)
     assert(manager:call('get_manualPlayer')==owner,'Native story owner handoff failed')
     core.parkReserve(manager,previous)
     runtime.invalidate();c=runtime.get(manager);B.observedManual=c.active
    end
   end
  end
  if c.paused or c.id~=nativeID or not bodyReady(c.active)or c.active:call('get_isEventRun')then
   B.arrivalReady=0;B.observedManual=c.active;B.playable=false;B.stage='waiting for native story owner';return
  end
  B.arrivalReady=B.arrivalReady+1
  if B.arrivalReady<2 then B.observedManual=c.active;B.playable=false;B.stage='confirming native story owner';return end
  B.awaitNative=nil
 end
 -- The native owner may acquire its first body meshes after our first
 -- update. Revisit adoption rather than permanently treating it as absent.
 if B.known[c.id]~=c.active then
  local native=sdk.get_managed_singleton('app.AdditionalPlayerLoadManager')
  local state=native and recordState(native,c.id)
  if bodyReady(c.active)and(state==nil or state<3 or(state==6 and native:call('isReadyPlayerResource',c.id,0,0)))then
   B.known[c.id]=c.active;B.prepared[c.id]=c.active;B.additional[c.id]=state==6
   B.activation={actor=c.active,generation=B.generation,elapsed=0,updates=0,bad=0}
  end
 end
 B.observedManual=c.active
 -- Gameplay permission changes immediately; only background scans are throttled.
 B.playable=B.known[c.id]==c.active and bodyReady(c.active)and not c.paused and not c.active:call('get_isEventRun')
 confirmActivation(manager,core,c,requested)
 if c.paused then return end
 if not B.playable then B.excludedV=nil;return end
 local dt=runtime.delta(c);if dt<=0 then return end
 B.elapsed=B.elapsed+dt
 local interval=requested and 0 or(B.count==3 and .5 or .1)
 if B.elapsed<interval-1e-8 then return end
 local elapsed=B.elapsed;B.elapsed=0
 -- isThinkEnable is not a manual-control readiness flag: the native Nero in
 -- The Void reports false while moving/attacking normally. Pause, positive
 -- game delta and the event flag are the guards for background preparation.
 B.clock=B.clock+elapsed
 local loader=sdk.get_managed_singleton('app.AdditionalPlayerLoadManager')
 if not loader then B.stage='waiting for loader';return end
 -- Cache identity AND inspect current state: floor cleanup may show the
 -- same V again. Settled actors are read, never repeatedly paused/hidden.
 local extra=manager:call('getPlayerByID',2)
 local changed=extra~=B.excludedV
 if extra and not changed then
  local med=extra:call('get_cachedActivateMediator')
  local object=extra:call('get_GameObject')
  changed=extra:call('get_Enable')~=false or not med or med:call('get_drawSelf')~=false or med:call('get_updateSelf')~=false or
   (object and object:call('get_DrawSelf')~=false)
 end
 if changed then
  local extraState=extra and recordState(loader,2)
  if extra and (extraState==nil or extraState==6) and core.parkNonParty(manager,extra)then B.excludedV=extra
  elseif not extra then B.excludedV=nil end
 end
 B.count=0
 for _,id in ipairs(ids)do
  local ready=B.ready(manager,id)
  B.available[tostring(id)]=ready
  if ready then B.count=B.count+1 else B.known[id]=nil end
 end
 if not B.task then
  local function eligible(id)
   return supported[id] and not B.available[tostring(id)] and
    B.clock>=(B.retry[id] or 0) and ((B.attempts[id] or 0)<3 or requested==id)
  end
  local chosen
  if requested and eligible(requested)then chosen=requested end
  if not chosen then for _,id in ipairs(ids)do if eligible(id)then chosen=id;break end end end
  if chosen then B.task={id=chosen,phase='inspect',start=B.clock,owner=c.active,ownerID=c.id}end
 end
 if B.task then
  local id=B.task.id
  local ok,why=pcall(step,manager,loader,core)
  if not ok then
   B.error=tostring(why);B.attempts[id]=(B.attempts[id] or 0)+1
   B.retry[id]=B.clock+5;B.task=nil;B.stage='preparation retry pending'
  else B.stage=B.task and ('preparing '..id..' / '..B.task.phase) or 'checking party' end
 elseif B.count==3 then B.stage='party ready';B.error=nil
 else B.stage='waiting to retry preparation' end
 -- getPlayerByID exposes one slot per ID, while players can contain multiple
 -- live instances after native scripted replacements (M19 -> M20 Nero).
 -- Reconcile the bounded native list at the existing background scan cadence.
 local count=manager:call('getPlayerNum')
 if type(count)=='number'and count>=0 and count<=32 then
  for i=0,count-1 do
   local p=manager:call('getPlayer',i)
   if p and p~=c.active then
    local id=p:call('get_playerID')
    if supported[id]and B.ready(manager,id)and bodyReady(p)then core.parkReserve(manager,p)end
   end
  end
 end
end
return B
