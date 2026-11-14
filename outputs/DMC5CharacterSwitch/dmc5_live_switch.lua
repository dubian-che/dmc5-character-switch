-- Live switching for DMC5 / REFramework TDB 67.
-- Configurable next/previous keys. Prepare reserve actors as gameplay begins.
-- Check before loading any module: older loaders must not install partial hooks.
if type(thread)~='table'or type(thread.get_hook_storage)~='function'then
 local message='Incompatible REFramework: thread.get_hook_storage is unavailable. Install the complete pre-0.0.4 package and restart the game.'
 local blocked={build='release-50-native-v-reload',stage='incompatible REFramework',current=-1,available={},error=message}
 _G.dmc5_live_switch=blocked
 if log and log.error then pcall(log.error,message)end
 return blocked
end
if _G.dmc5_live_switch then return _G.dmc5_live_switch end
local core=dofile('reframework/data/dmc5_switch_core.lua')
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
local loader=dofile('reframework/data/dmc5_switch_loader.lua')
local S={version=core.version or 1,build='release-50-native-v-reload',stage='ready',current=-1,available={}}
_G.dmc5_live_switch=S
S.revision='checkpoint-v-input-audio-2.custom-controls-1.world-v-1.lock-return-1.presentation-1.world-v-end-1.keyboard-1.world-v-camera-5.palace-v-4.costume-1.dante-round-trip-1'
local retryOk,retryWhy=pcall(function()
 local t=sdk.find_type_definition('app.MissionSettingManager')
 for _,name in ipairs({'retryMission','restartMissionCheckPoint'})do
  local m=t and t:get_method(name);assert(m,'Native reload entry unavailable: '..name)
  local key='partyReload_'..name
  sdk.hook(m,function(args)
   local owner=sdk.to_managed_object(args[2])
   local ok,prepared=pcall(runtime.prepareStoryRetry,owner)
   if not ok then runtime.storyRetryError=tostring(prepared)
   elseif prepared then thread.get_hook_storage()[key]={owner=owner,serial=runtime.storyRetrySerial}end
  end,function(ret)
   local storage=thread.get_hook_storage();local reload=storage[key];storage[key]=nil
   if reload then
    local ok,why=pcall(runtime.finishStoryRetry,reload.owner,reload.serial)
    if not ok then runtime.storyRetryError=tostring(why)end
   end
   return ret
  end)
 end
end)
if not retryOk then S.storyRetryInstallError=tostring(retryWhy)end
dofile('reframework/data/dmc5_switch_input_menu.lua')
local request=nil
local history=nil
local keys={}
local function clearHistory()
 history=nil;S.previousCharacter=nil
end
function S.request(id,source)
 S.requestCount=(S.requestCount or 0)+1
 local function reject(reason)S.lastRequest={id=id,source=source or 'user',accepted=false,reason=reason};return false end
 if runtime.storyReload then return reject('checkpoint reload')end
 if not core.names[id] then return reject('unsupported character')end
 if runtime.manager and not runtime.permits()then return reject('outside party scene')end
 source=source or 'user'
 -- Keep one desired selection. Explicit user choices replace an older wait;
 -- automatic Palace restoration must never replace a user's choice.
 if request and(source=='palace'or(request.id==id and request.source==source))then return reject('request already pending')end
 request={id=id,generation=loader.manager and loader.generation or nil,elapsed=0,source=source}
 if source=='palace'then
  local palace=_G.dmc5_switch_palace
  request.run=palace and palace.run;request.phase=request.run and request.run.stage
 end
 S.stage='requested '..core.names[id];S.error=nil
 S.lastRequest={id=id,source=source,accepted=true}
 return true
end
function S.requestDirect(id)
 if not core.names[id]then return false end
 local manager=loader.manager
 if not manager or runtime.storyReload or not runtime.permits(manager)then return false end
 local active=manager:call('get_manualPlayer')
 local current=active and active:call('get_playerID')
 if not core.names[current]then return false end
 if history and(history.manager~=manager or history.generation~=loader.generation or history.current~=current)then clearHistory()end
 if id==current then
  if not history then return false end
  id=history.id
 end
 return S.request(id)
end
function S.getCycleID()return request and request.id or S.current end
function S.hidePalaceExtra(bp)
 local palace=_G.dmc5_switch_palace;local manager=loader.manager
 if not runtime.permits(manager)then return false end
 local gm=sdk.get_managed_singleton('app.GameManager')
 if not manager or not bp or not gm or gm:call('get_gameMode')~=3 or gm:call('get_isPause')then return false end
 if not palace or not palace.run or palace.run.owner~=bp then return false end
 local floor=bp:get_field('CurrentStageNo')
 if type(floor)~='number'or floor<0 or floor>100 or bp:get_field('IsTrainingMode')or bp:get_field('IsRetryProcessing')or bp:get_field('IsRetryTrainingRequest')then return false end
 local active=manager:call('get_manualPlayer')
 if not active or not core.names[active:call('get_playerID')]then return false end
 local extra=manager:call('getPlayerByID',2)
 if not extra or extra==active or extra:call('get_ownerVergilPL')then return false end
 local med=extra:call('get_cachedActivateMediator');local object=extra:call('get_GameObject')
 if med and med:call('get_drawSelf')==false and object and object:call('get_DrawSelf')==false then return false end
 -- Clear/result events may own actor updates. Change display only here;
 -- native pause, loading, enemies and flow remain with the original callback.
 if core.hideReserve(manager,extra)then S.extraVHides=(S.extraVHides or 0)+1;return true end
 return false
end
local visibilityOk,visibilityWhy=pcall(function()
 local t=sdk.find_type_definition('app.BloodyPalaceManager')
 for _,name in ipairs({'updateBattleFinish','updateNextStageWait','updateFadeoutShowStageResult','updateFloorFinalize'})do
  local method=t and t:get_method(name);assert(method,'Palace visibility callback unavailable: '..name)
  local key='partyVisibility_'..name
  sdk.hook(method,function(args)thread.get_hook_storage()[key]=sdk.to_managed_object(args[2])end,function(ret)
   local storage=thread.get_hook_storage();local bp=storage[key];storage[key]=nil
   local ok,why=pcall(S.hidePalaceExtra,bp)
   if not ok then S.extraVError=tostring(why)end
   return ret
  end)
 end
end)
if not visibilityOk then S.extraVError=tostring(visibilityWhy)end
local keyModule=dofile('reframework/data/dmc5_switch_keys.lua')
keyModule.install(S)
S.config,S.configWarning=keyModule.load_config()
-- Disabled controller switching needs no pad or manager hooks.
if S.config.controllerCombo then dofile('reframework/data/dmc5_switch_controller.lua')end
local function is_down(key)return keyModule.read_key(key)end
local function advance(manager)
 local c=runtime.get(manager)
 S.current=c.id
 if history and(history.manager~=manager or history.generation~=loader.generation or history.current~=c.id)then clearHistory()end
 if runtime.storyReload then clearHistory();request=nil;S.stage='checkpoint reload in progress';return end
 if not runtime.permits(manager)then clearHistory();request=nil;S.stage='outside party scene';return end
 if not core.names[S.current]then clearHistory();request=nil;return end
 if not request then
  S.stage=loader.playable and('active '..core.names[S.current])or 'waiting for gameplay'
  return
 end
 local r=request
 if r.source=='palace'then
  local palace=_G.dmc5_switch_palace
  if not palace or palace.run~=r.run or not palace.run or palace.run.stage~=r.phase then
   request=nil;S.stage='Palace phase changed';return
  end
 end
 if r.generation and r.generation~=loader.generation then request=nil;S.stage='scene changed';return end
 r.generation=loader.generation
 if c.paused or not loader.playable then return end
 r.elapsed=r.elapsed+runtime.delta(c)
 if r.elapsed>90 then request=nil;error('Loading timed out; retry switching')end
 if loader.ready(manager,r.id)then
  core.switch(manager,r.id,r.source)
  loader.selected(manager,r.id)
  if r.id~=c.id then
   history={id=c.id,current=r.id,manager=manager,generation=loader.generation}
   S.previousCharacter=c.id
  end
  S.current=r.id
  S.switchCount=(S.switchCount or 0)+1
  request=nil;S.stage='active '..core.names[S.current]
  return
 end
 S.stage='preparing '..core.names[r.id]
end
local function update(manager)
 loader.update(manager,core,request and request.id)
 S.available=loader.available
 S.storyVGuards=core.storyVGuards
 S.presentationError=core.presentationError
 advance(manager)
end
sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
 local ok,why=pcall(update,sdk.to_managed_object(args[2]))
 if not ok then request=nil;S.stage='error';S.error=tostring(why)end
end,function(ret)return ret end)
re.on_frame(function()
 local ok,why=pcall(runtime.maintainStoryReload)
 if not ok then runtime.storyRetryError=tostring(why)end
 S.keyboardSource=keyModule.input.source;S.keyboardError=keyModule.input.error
 keyModule.poll(S,keys,S.config,is_down)
end)
return S






