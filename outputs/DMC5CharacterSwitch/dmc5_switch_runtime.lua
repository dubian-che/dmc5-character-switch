-- Shared state for one PlayerManager update. No file I/O during normal play.
if _G.dmc5_switch_runtime then return _G.dmc5_switch_runtime end
local R={}
_G.dmc5_switch_runtime=R
function R.invalidate() R.cached=nil;R.scope=nil end
function R.withInputProfile(gm,id,fn)
 -- PlayingID is also used by native IsVergilMode. It must never retain
 -- a reserve actor's ID after the synchronous input refresh.
 local previous=gm:get_field('PlayingID')
 assert(type(previous)=='number','Native input identity unavailable')
 gm:set_field('PlayingID',id)
 local ok,result=pcall(fn)
 gm:set_field('PlayingID',previous)
 if not ok then error(result)end
 return result
end
-- MissionSetting.playerInfo is also the native battle-route identity.
-- Only the synchronous manual-player lookup may see a Mod-selected ID.
function R.withControlProfile(setting,id,fn)
 local previous=setting:call('get_ControllPlayerID')
 local native=R.nativeControl
 if (R.controlDepth or 0)==0 and native and native.setting==setting and native.retrySerial==R.storyRetrySerial then
  local loader=_G.dmc5_switch_loader
  if not loader or(native.mode==loader.sceneMode and native.mission==loader.storyMission)then previous=native.id end
 end
 assert(type(previous)=='number','Native mission identity unavailable')
 R.controlDepth=(R.controlDepth or 0)+1
 local ok,result=pcall(function()
  setting:call('set_ControllPlayerID',id)
  return fn()
 end)
 local restored,why=pcall(function()setting:call('set_ControllPlayerID',previous)end)
 R.controlDepth=R.controlDepth-1
 assert(restored,why)
 if not ok then error(result)end
 return result
end
function R.selectManual(manager,setting,id)
 local actor=manager:call('getPlayerByID',id)
 assert(actor,'Manual selection actor unavailable')
 local native=R.nativeControl
 local nativeID=native and native.manager==manager and native.setting==setting and native.id or setting:call('get_ControllPlayerID')
 R.withControlProfile(setting,id,function()manager:call('updateManualPlayer')end)
 assert(manager:call('get_manualPlayer')==actor,'Native manual selection failed')
 local loader=_G.dmc5_switch_loader
 R.controlSelection={manager=manager,setting=setting,actor=actor,id=id,nativeID=nativeID,
  generation=loader and loader.generation,mode=loader and loader.sceneMode,
  mission=loader and loader.storyMission,retrySerial=R.storyRetrySerial}
end
local function manualLookupBegin(manager)
 R.maintainStoryReload(manager)
 local storage=thread.get_hook_storage()
 storage.manualIdentityFrames=storage.manualIdentityFrames or {}
 local frame={};table.insert(storage.manualIdentityFrames,frame)
 if (R.controlDepth or 0)>0 then return end
 local loader=_G.dmc5_switch_loader
 local gm=sdk.get_managed_singleton('app.GameManager')
 local settings=sdk.get_managed_singleton('app.MissionSettingManager')
 local setting=settings and settings:call('get_Setting')
 if not gm or not setting then R.controlSelection=nil;return end
 local mode=gm:call('get_gameMode');local mission=mode==0 and gm:call('get_missionNo')or nil
 local native=R.nativeControl
 local nativeID=setting:call('get_ControllPlayerID')
 if nativeID~=0 and nativeID~=1 and nativeID~=2 and nativeID~=4 then R.nativeControl=nil;R.controlSelection=nil;return end
 if not native or native.manager~=manager or native.setting~=setting or native.mode~=mode or
  native.mission~=mission or native.retrySerial~=R.storyRetrySerial or
  (native.id~=nativeID and not(loader and loader.task))then
  R.nativeControl={manager=manager,setting=setting,id=setting:call('get_ControllPlayerID'),
   mode=mode,mission=mission,retrySerial=R.storyRetrySerial}
  R.controlSelection=nil
 end
 local s=R.controlSelection;if not s or s.manager~=manager then return end
 if not loader or loader.manager~=manager or loader.generation~=s.generation or
  R.storyRetrySerial~=s.retrySerial or not gm or gm:call('get_gameMode')~=s.mode or
  (s.mode==0 and gm:call('get_missionNo')~=s.mission)or setting~=s.setting or
  manager:call('get_manualPlayer')~=s.actor or manager:call('getPlayerByID',s.id)~=s.actor or
  not R.permits(manager)or s.actor:call('get_isEventMove')then
  R.controlSelection=nil;return
 end
 frame.setting=setting;frame.previous=setting:call('get_ControllPlayerID')
 setting:call('set_ControllPlayerID',s.id)
end
local function manualLookupEnd()
 local storage=thread.get_hook_storage();local frames=storage.manualIdentityFrames
 local frame=frames and table.remove(frames)
 if frame and frame.setting then frame.setting:call('set_ControllPlayerID',frame.previous)end
 if frames and #frames==0 then storage.manualIdentityFrames=nil end
end
sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('updateManualPlayer'),function(args)
 local ok,why=pcall(manualLookupBegin,sdk.to_managed_object(args[2]))
 if not ok then R.controlIdentityError=tostring(why)end
end,function(ret)
 local ok,why=pcall(manualLookupEnd)
 if not ok then R.controlIdentityError=tostring(why)end
 return ret
end)
function R.prepareStoryRetry(settingManager)
 if not settingManager or not R.manager then return false end
 local gm=sdk.get_managed_singleton('app.GameManager')
 if not gm or gm:call('get_gameMode')~=0 or not settingManager:call('get_isEntered')then return false end
 local active=R.manager:call('get_manualPlayer')
 local activeID=active and active:call('get_playerID')
 if activeID~=0 and activeID~=1 and activeID~=4 then return false end
 local setting=settingManager:call('get_Setting')
 if not setting then return false end
 local native=R.nativeControl
 local id=gm:call('findManualPlayerID')
 if native and native.manager==R.manager and native.setting==setting and native.mode==0 and native.mission==gm:call('get_missionNo')then id=native.id end
 if id~=0 and id~=1 and id~=4 then return false end
 -- Retry reconstructs the primary actor from this value. A Mod selection
 -- must not become the incoming story's native spawn identity.
 if setting:call('get_ControllPlayerID')~=id then setting:call('set_ControllPlayerID',id)end
 R.storyRetrySerial=(R.storyRetrySerial or 0)+1
 R.storyReload={owner=settingManager,setting=setting,id=id,mission=gm:call('get_missionNo'),serial=R.storyRetrySerial,
  manager=R.manager,actor=R.manager:call('getPlayerByID',id),readyFrames=0,phase='scheduled'}
 R.controlSelection=nil
 R.storyRetryID=id;R.storyRetryError=nil
 return true
end
function R.finishStoryRetry(settingManager,serial)
 local reload=R.storyReload;local gm=sdk.get_managed_singleton('app.GameManager')
 if not reload or reload.postDone or reload.owner~=settingManager or reload.serial~=serial or R.storyRetrySerial~=serial or
  not gm or gm:call('get_gameMode')~=0 or gm:call('get_missionNo')~=reload.mission then return false end
 if settingManager:call('get_Setting')~=reload.setting then return false end
 -- Checkpoint restart schedules the reconstruction. Native code can rewrite
 -- the selected ID while scheduling; restore the captured route after it too.
 if reload.setting:call('get_ControllPlayerID')~=reload.id then reload.setting:call('set_ControllPlayerID',reload.id)end
 R.controlSelection=nil;reload.postDone=true;reload.phase='waiting for teardown'
 return true
end
function R.maintainStoryReload(manager)
 local reload=R.storyReload;if not reload then return false end
 local gm=sdk.get_managed_singleton('app.GameManager')
 if not gm or gm:call('get_gameMode')~=0 or gm:call('get_missionNo')~=reload.mission then R.storyReload=nil;return false end
 local lookup=gm:call('findManualPlayerID')
 if (lookup==0 or lookup==1 or lookup==2 or lookup==4)and lookup~=reload.id then R.storyReload=nil;return false end
 local settings=sdk.get_managed_singleton('app.MissionSettingManager')
 local setting=settings and settings:call('get_Setting')
 if not setting then reload.boundary=true;reload.phase='waiting for settings';return true end
 if setting~=reload.setting then reload.boundary=true end
 -- The asynchronous checkpoint states may install a different setting object
 -- after the original request returns. Keep the captured route through that gap.
 if setting:call('get_ControllPlayerID')~=reload.id then
  setting:call('set_ControllPlayerID',reload.id);reload.repairs=(reload.repairs or 0)+1
 end
 R.controlSelection=nil
 if not manager then return true end
 local active=manager:call('get_manualPlayer');local actor=manager:call('getPlayerByID',reload.id)
 if not active then reload.teardown=true end
 if manager~=reload.manager or actor~=reload.actor or not active then reload.boundary=true end
 if not reload.boundary then return true end -- Never accept the outgoing actor as the new arrival.
 if not reload.teardown and manager==reload.manager and actor==reload.actor then reload.readyFrames=0;return true end
 reload.phase='waiting for native arrival'
 local mesh=actor and actor:call('get_bodyMeshList')
 local bound=mesh and mesh:get_size()>0 and mesh:get_element(0)
 if active==actor and actor and bound and actor:call('get_Enable')and actor:call('get_Enabled')and
  actor:call('get_hp')>0 and not actor:call('get_isEventMove')and not gm:call('get_isPause')then
  reload.readyFrames=reload.readyFrames+1
 else reload.readyFrames=0 end
 if reload.readyFrames<2 then return true end
 R.nativeControl={manager=manager,setting=setting,id=reload.id,mode=0,mission=reload.mission,retrySerial=R.storyRetrySerial}
 R.storyReload=nil;R.storyRetryError=nil;R.invalidate()
 return false
end
function R.begin(manager)
 R.invalidate();R.pending=nil;R.updating=true;if manager then R.manager=manager end
 local ok,why=pcall(R.maintainStoryReload,manager)
 if not ok then R.storyRetryError=tostring(why)end
end
function R.permits(manager)
 manager=manager or R.manager;if not manager then return false end
 local active=manager:call('get_manualPlayer')
 local id=active and active:call('get_playerID')
 local allowed=false;local nativeID
 if id==0 or id==1 or id==4 then
  local gm=sdk.get_managed_singleton('app.GameManager')
  nativeID=gm and gm:call('findManualPlayerID')
  -- Multi-hero missions can have a native V selection even though the
  -- mission asset's default hero is Nero. Preserve that selected route.
  local native=R.nativeControl
  if gm and native and native.manager==manager and native.id==2 and native.mode==gm:call('get_gameMode')and
   (native.mode~=0 or native.mission==gm:call('get_missionNo'))then nativeID=2 end
  allowed=nativeID==0 or nativeID==1 or nativeID==4
 end
 if R.updating then R.scope={manager=manager,active=active,allowed=allowed,nativeID=nativeID}end
 return allowed
end
function R.afterUpdate(fn)
 if R.updating then R.pending=R.pending or {};R.pending[#R.pending+1]=fn else fn()end
end
function R.finish()
 local pending=R.pending;R.pending=nil;R.updating=false;R.invalidate()
 if pending then
  for _,fn in ipairs(pending)do
   local ok,why=pcall(fn)
   if not ok then R.error=tostring(why)end
  end
 end
end
function R.get(manager)
 if R.cached and R.cached.manager==manager then return R.cached end
 local c={manager=manager,active=manager:call('get_manualPlayer')}
 c.id=c.active and c.active:call('get_playerID') or -1
 c.gm=sdk.get_managed_singleton('app.GameManager')
 c.menuPaused=c.gm and (c.gm:call('get_isPauseMenu') or c.gm:call('get_isShopPause')) or false
 c.paused=not c.gm or c.menuPaused or c.gm:call('get_isPause')
 R.cached=c;return c
end
function R.delta(c)
 if c.dt~=nil then return c.dt end
 c.dt=0
 if not c.active or c.paused then return 0 end
 local hit=c.active:call('get_cachedHitController')
 local work=hit and hit:get_field('<cachedWorkRate>k__BackingField')
 local dt=work and work:call('getRateDeltaSec') or 0
 if dt>0 and dt<=0.25 then c.dt=dt end
 return c.dt
end
sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)R.begin(sdk.to_managed_object(args[2]))end,function(ret)R.finish();return ret end)
return R
