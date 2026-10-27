-- Owns Bloody Palace transfers. Gameplay resources and input remain separate.
if _G.dmc5_switch_palace then return _G.dmc5_switch_palace end
local P={epoch=0,sequence=0,restores=0}
_G.dmc5_switch_palace=P
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
local ids={0,1,4}
local function valid(id)return id==0 or id==1 or id==4 end
local function numeric(value,name)
 assert(type(value)=='number'and value==value and math.abs(value)<math.huge,'Invalid Palace state: '..name)
 return value
end
function P.reset()P.run=nil;P.elapsed=0 end
local function context(bp)
 local gm=sdk.get_managed_singleton('app.GameManager')
 -- Session lifetime is separate from permission to touch a live actor.
 -- Native floor teardown can temporarily remove manual control. Keep the
 -- committed transfer until the same Palace session has a ready actor again.
 if not gm then return nil end
 if gm:call('get_gameMode')~=3 then P.reset();return nil end
 bp=bp or sdk.get_managed_singleton('app.BloodyPalaceManager')
 if not bp then return nil end
 if bp:get_field('IsTrainingMode')or
  bp:get_field('IsRetryProcessing')or bp:get_field('IsRetryTrainingRequest')then P.reset();return nil end
 if P.run and P.run.owner~=bp then P.reset()end
 local manager=runtime.manager or P.manager or(_G.dmc5_switch_loader and _G.dmc5_switch_loader.manager)
 if not runtime.permits(manager)then return nil end
 if not P.run or P.run.owner~=bp then P.run={owner=bp}end
 return P.run,bp
end
local function ready(manager,id)
 local actor=manager and manager:call('getPlayerByID',id)
 if not actor then return nil end
 local loader=_G.dmc5_switch_loader
 if loader then
  if loader.manager==manager and loader.ready(manager,id)then return actor end
  return nil
 end
 if actor==manager:call('get_manualPlayer')then return actor end
 return nil
end
local function weaponSlots(actor,kind)
 local list=actor:call('get_slotWeapon'..kind)
 assert(list,'Palace weapon list unavailable')
 local count=list:call('get_Count');assert(count>=0 and count<=32,'Invalid Palace weapon count')
 local values={}
 for i=0,count-1 do values[#values+1]=numeric(list:call('get_Item',i),'weapon slot')end
 return values
end
local function stock(actor)
 if actor:call('get_gauntletStackCount')~=0 then return nil end
 local count=actor:call('get_gauntletNum');local list=actor:call('get_gauntletList')
 if not list or count<0 or count>8 or list:get_size()<count then return nil end
 local values={}
 for i=0,count-1 do
  local id=list:read_dword(0x20+i*4)
  if id<0 or id>=13 then return nil end
  values[#values+1]=id
 end
 return values
end
function P.captureActor(actor)
 local id=actor:call('get_playerID')
 local row={id=id,hp=numeric(actor:call('get_hp'),'hp'),maxHp=numeric(actor:call('get_maxHp'),'maxHp'),
  dt=numeric(actor:call('get_devilTriggerGauge'),'dt'),maxDt=numeric(actor:call('get_maxDevilTriggerGauge'),'maxDt')}
 if id==0 then row.stock=stock(actor)
 else
  row.sin=numeric(actor:get_field('<theDTGauge>k__BackingField'),'sin')
  row.slotsS=weaponSlots(actor,'S');row.weaponS=actor:call('get_currentWeaponS');row.weaponSID=actor:call('get_weaponS_ID')
  local sin=actor:call('get_isTheDevilTrigger')
  if sin then row.weaponS=actor:call('get_prevSDTWeaponS')end
  if id==1 then
   row.slotsL=weaponSlots(actor,'L');row.weaponL=actor:call('get_currentWeaponL');row.weaponLID=actor:call('get_weaponL_ID')
   if sin then row.weaponL=actor:call('get_prevSDTWeaponL')end
  end
 end
 return row
end
local function vitals(actor,row)
 actor:call('set_maxHp',row.maxHp);actor:call('set_maxDevilTriggerGauge',row.maxDt)
 actor:call('set_hp',row.hp);actor:call('set_devilTriggerGauge',row.dt)
 if row.sin~=nil then actor:set_field('<theDTGauge>k__BackingField',row.sin)end
end
local function setSlots(actor,kind,values)
 local list=actor:call('get_slotWeapon'..kind);assert(list,'Loaded Palace weapon list unavailable')
 list:call('Clear');for _,value in ipairs(values)do list:call('Add',value)end
end
local function finishEquipment(actor,row)
 if row.slotsS then setSlots(actor,'S',row.slotsS)end
 if row.slotsL then setSlots(actor,'L',row.slotsL)end
 local progression=_G.dmc5_switch_progression
 if row.id==1 and progression and progression.lockRedBike then progression.lockRedBike(actor)end
end
function P.pendingVitals(id)
 local run=context();local stage=run and run.stage
 if not stage then return false end
 return (stage.closed and stage.snapshot and stage.snapshot.rows[id]~=nil)or
  (stage.pending and stage.pending[id]~=nil)or false
end
function P.canRegen(id)
 local run=P.run;local s=run and run.stage
 if not s then return true end
 return s.ready and not s.closed and s.goal==nil and not(s.pending and s.pending[id])or false
end
function P.canRefill()
 local run=P.run;local s=run and run.stage
 if not s then return true end
 if s.closed or(s.source and not s.ready)then return false end
 return not(s.pending and s.pending[0])
end
function P.capture(bp,phase)
 local run=context(bp);local s=run and run.stage
 if not s or not s.ready or s.closed then return false end
 local manager=P.manager or(_G.dmc5_switch_loader and _G.dmc5_switch_loader.manager)
 if not manager then return false end
 local regen=_G.dmc5_switch_regen
 if regen and regen.flush then regen.flush(manager)end
 if regen then regen.pending={};regen.elapsed=0;regen.lastActive=nil end
 local rows={}
 for _,id in ipairs(ids)do
  if s.pending and s.pending[id]then rows[id]=s.pending[id]
  else
   local actor=ready(manager,id)
   if actor then
    local ok,row=pcall(P.captureActor,actor)
    if ok then rows[id]=row else P.error=tostring(row)end
   end
  end
 end
 local active=manager:call('get_manualPlayer');local actual=active and active:call('get_playerID')
 s.snapshot={rows=rows,choice=run.preferred or actual,phase=phase,floor=s.floor,kind=s.kind}
 s.closed=true;s.jobs={}
 if rows[0]and rows[0].stock==nil then s.stockActor=ready(manager,0)end
 return true
end
function P.open(bp,kind)
 local run=context(bp);if not run then return end
 local floor=bp:get_field('CurrentStageNo')
 if type(floor)~='number'or floor<0 or floor>101 then return end
 local old=run.stage
 if old and not old.closed and old.floor==floor and old.kind==kind then return end
 local incoming=old and old.closed and old.snapshot
 if incoming and floor~=old.floor and floor~=old.floor+1 then incoming=nil end
 local pending={}
 if incoming then for id,row in pairs(incoming.rows)do pending[id]=row end end
 P.epoch=P.epoch+1
 run.stage={epoch=P.epoch,floor=floor,kind=kind,ready=true,source=incoming,pending=pending,jobs={},attempted={},restored={},
  goal=incoming and(run.preferred or incoming.choice)or nil}
 P.urgent=true
end
local function equip(manager,id,s)
 local row=s.pending[id];if not row or s.jobs[id]then return false end
 local actor=ready(manager,id)
 if not actor or actor:call('get_isEventMove')then return false end
 if s.goal~=nil and s.goal~=id and actor==manager:call('get_manualPlayer')then return false end
 if s.attempted[id]==actor then return false end
 if id==0 and row.stock and actor:call('get_gauntletStackCount')~=0 then return false end
 s.attempted[id]=actor
 local progression=_G.dmc5_switch_progression
 if progression then progression.apply(actor)end
 if row.stock then
  local list=actor:call('get_gauntletList');assert(list and list:get_size()>=8,'Palace arm list unavailable')
  for i=0,7 do list:write_dword(0x20+i*4,row.stock[i+1]or 100)end
  actor:call('rebuildGauntletList',list)
  assert(actor:call('get_gauntletNum')==#row.stock,'Palace arm count did not restore')
 end
 if row.slotsS then
  setSlots(actor,'S',row.slotsS)
  if actor:call('get_isTheDevilTrigger')then
   actor:call('set_prevSDTWeaponS',row.weaponS)
   if row.slotsL then actor:call('set_prevSDTWeaponL',row.weaponL)end
  else
   actor:call('changeWeaponS',row.weaponS,row.weaponSID)
   if row.slotsL then setSlots(actor,'L',row.slotsL);actor:call('changeWeaponL',row.weaponL,row.weaponLID)end
  end
 end
 -- Finalize on the next native update, after deferred weapon entry. Gauges
 -- are written there once, rather than being pinned during ordinary combat.
 s.jobs[id]={actor=actor,row=row,after=P.sequence+1}
 return true
end
function P.beforeSwitch(manager,id)
 local run=context();local s=run and run.stage
 if s and s.ready and not s.closed and s.pending[id]then equip(manager,id,s)end
end
function P.selected(id,manager,previous,source)
 local run=context();if not run then return end
 local s=run.stage
 if source~='palace'then
  run.preferred=id
  if s and not s.closed then s.goal=nil;s.requested=nil end
 elseif s and s.goal==id then
  s.goal=nil;s.requested=nil;s.handoff={id=id,previous=previous}
 end
end
local function finishJobs(manager,s)
 for _,id in ipairs(ids)do
  local job=s.jobs[id]
  if job and P.sequence>=job.after then
   s.jobs[id]=nil
   if manager:call('getPlayerByID',id)==job.actor and ready(manager,id)==job.actor then
    local ok,why=pcall(function()
     finishEquipment(job.actor,job.row);vitals(job.actor,job.row)
    end)
    if ok then s.pending[id]=nil;s.restored[id]=job.actor;P.restores=P.restores+1
    else P.error=tostring(why)end
   else s.attempted[id]=nil end
  end
 end
 if s.handoff then
  local h=s.handoff;s.handoff=nil
  for _,id in ipairs({h.id,h.previous or h.id})do
   local actor=manager:call('getPlayerByID',id);local row=s.source and s.source.rows[id]
   if actor and s.restored[id]==actor and row then vitals(actor,row)end
  end
 end
end
local function selectGoal(manager,s)
 if s.goal==nil then return end
 local active=manager:call('get_manualPlayer')
 if active and active:call('get_playerID')==s.goal then s.goal=nil;return end
 local loader=_G.dmc5_switch_loader;local live=_G.dmc5_live_switch
 if s.requested and loader and s.requestGeneration~=loader.generation then s.requested=nil end
 if s.requested and live and live.stage=='error'then P.error='Palace selection: '..tostring(live.error);s.goal=nil;return end
 if s.requested or s.pending[s.goal]then return end
 local target=ready(manager,s.goal)
 if target and loader and loader.manager==manager and loader.known[s.goal]==target and active and
  loader.known[active:call('get_playerID')]==active and loader.playable and not active:call('get_isEventMove')and live then
  s.requested=live.request(s.goal,'palace')==true
  if s.requested then s.requestGeneration=loader.generation end
 end
end
function P.update(manager)
 P.manager=manager;P.sequence=P.sequence+1
 local run=context();local s=run and run.stage
 if not s then return end
 if s.closed then
  if s.stockActor and manager:call('getPlayerByID',0)==s.stockActor then
   local settled=stock(s.stockActor)
   if settled then s.snapshot.rows[0].stock=settled;s.stockActor=nil end
  end
  return
 end
 local c=runtime.get(manager);if c.paused or not s.ready then return end
 finishJobs(manager,s)
 if P.urgent then P.urgent=false;P.elapsed=0
 else
  P.elapsed=(P.elapsed or 0)+runtime.delta(c)
  if P.elapsed<.1 then selectGoal(manager,s);return end
  P.elapsed=0
 end
 for _,id in ipairs(ids)do
  local ok,why=pcall(equip,manager,id,s)
  if not ok then P.error=tostring(why)end
 end
 selectGoal(manager,s)
end
function P.finishGauntletStage(bp,manager,gm)
 if not runtime.permits(manager)then return false end
 if not bp or not manager or not gm or gm:call('get_gameMode')~=3 then return false end
 if not bp:get_field('IsGauntletStage')or bp:get_field('IsTrainingMode')or bp:get_field('IsRetryProcessing')then return false end
 local actor=manager:call('get_manualPlayer');local id=actor and actor:call('get_playerID')
 if id~=1 and id~=4 then return false end
 -- Verified v25 native adapter: reproduce only the Nero-only exit cleanup.
 bp:set_field('CurrentGauntletStageInfo',nil);bp:set_field('IsGauntletStage',false)
 P.gauntletExits=(P.gauntletExits or 0)+1;P.lastGauntletExit={id=id,floor=bp:get_field('CurrentStageNo')}
 return true
end
local function guard(fn,...)
 local ok,why=pcall(fn,...);if not ok then P.error=tostring(why)end
end
local t=sdk.find_type_definition('app.BloodyPalaceManager')
for _,name in ipairs({'updateFadeout','updateFadeoutShowStageResult','updateFloorFinalize','updateGauntletStageFinalize'})do
 local method=t and t:get_method(name);local phase=name
 if method then sdk.hook(method,function(args)guard(P.capture,sdk.to_managed_object(args[2]),phase)end,function(ret)return ret end)end
end
for _,entry in ipairs({{'updateBattleInit','battle'},{'updateGauntletStageInit','supply'}})do
 local method=t and t:get_method(entry[1]);local key='palace_'..entry[1];local kind=entry[2]
 if method then sdk.hook(method,function(args)thread.get_hook_storage()[key]=sdk.to_managed_object(args[2])end,function(ret)
  guard(P.open,thread.get_hook_storage()[key],kind);return ret
 end)end
end
for _,name in ipairs({'updateGameOver','updateGameClear'})do
 local method=t and t:get_method(name)
 if method then sdk.hook(method,function(args)
  if P.run and P.run.owner==sdk.to_managed_object(args[2])then P.reset()end
 end,function(ret)return ret end)end
end
local check=t and t:get_method('updateCheckGaunletStage')
if check then sdk.hook(check,function(args)
 local loader=_G.dmc5_switch_loader;local manager=P.manager or(loader and loader.manager)
 if loader and manager and loader.manager~=manager then return end
 guard(P.finishGauntletStage,sdk.to_managed_object(args[2]),manager,sdk.get_managed_singleton('app.GameManager'))
end,function(ret)return ret end)end
sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
 local manager=sdk.to_managed_object(args[2]);P.manager=manager
 thread.get_hook_storage().palaceManager=manager
end,function(ret)guard(P.update,thread.get_hook_storage().palaceManager);return ret end)
return P
