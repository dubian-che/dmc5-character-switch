-- Live switching for DMC5 / REFramework TDB 67.
-- Configurable next/previous keys. Prepare reserve actors as gameplay begins.
if _G.dmc5_live_switch then return _G.dmc5_live_switch end
local core=dofile('reframework/data/dmc5_switch_core.lua')
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
local loader=dofile('reframework/data/dmc5_switch_loader.lua')
local S={version=core.version or 1,build='release-46-mission-control-identity',stage='ready',current=-1,available={}}
_G.dmc5_live_switch=S
local retryOk,retryWhy=pcall(function()
 local t=sdk.find_type_definition('app.MissionSettingManager')
 local m=t and t:get_method('retryMission');assert(m,'Native retry entry unavailable')
 sdk.hook(m,function(args)
  local ok,why=pcall(runtime.prepareStoryRetry,sdk.to_managed_object(args[2]))
  if not ok then runtime.storyRetryError=tostring(why)end
 end,function(ret)return ret end)
end)
if not retryOk then S.storyRetryInstallError=tostring(retryWhy)end
dofile('reframework/data/dmc5_switch_input_menu.lua')
local request=nil
local keys={}
function S.request(id,source)
 if not core.names[id] then return false end
 if runtime.manager and not runtime.permits()then return false end
 source=source or 'user'
 -- Keep one desired selection. Explicit user choices replace an older wait;
 -- automatic Palace restoration must never replace a user's choice.
 if request and(source=='palace'or(request.id==id and request.source==source))then return false end
 request={id=id,generation=loader.manager and loader.generation or nil,elapsed=0,source=source}
 if source=='palace'then
  local palace=_G.dmc5_switch_palace
  request.run=palace and palace.run;request.phase=request.run and request.run.stage
 end
 S.stage='requested '..core.names[id];S.error=nil
 return true
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
 if not extra or extra==active then return false end
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
local function is_down(key)return reframework:is_key_down(key)end
local function advance(manager)
 local c=runtime.get(manager)
 S.current=c.id
 if not runtime.permits(manager)then request=nil;S.stage='outside party scene';return end
 if not core.names[S.current]then request=nil;return end
 if not request then return end
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
  S.current=r.id
  request=nil;S.stage='active '..core.names[S.current]
  return
 end
 S.stage='preparing '..core.names[r.id]
end
local function update(manager)
 loader.update(manager,core,request and request.id)
 S.available=loader.available
 advance(manager)
end
sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
 local ok,why=pcall(update,sdk.to_managed_object(args[2]))
 if not ok then request=nil;S.stage='error';S.error=tostring(why)end
end,function(ret)return ret end)
re.on_frame(function()
 keyModule.poll(S,keys,S.config,is_down)
end)
return S






