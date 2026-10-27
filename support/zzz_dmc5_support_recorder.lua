-- Optional support recorder. Reads state only; no gameplay setters or hooks.
if _G.dmc5_support_recorder then return end
local D={version='support-47.1',samples=0,writes=0,buffer={}}
_G.dmc5_support_recorder=D
local folder='dmc5_support/'
local session=tostring(os.time())..'-'..tostring(math.floor((os.clock()%1)*1000000))
local last,lastFlush,lastMark,keyWasDown=nil,0,0,false
local methods,fields={},{}
local frames=0
local changes,lastSignature={},nil
local function typeName(o)
 local ok,v=pcall(function()return o:get_type_definition():get_full_name()end)
 if ok then return v end
end
local function copy(t)
 local out={};for k,v in pairs(t or{})do if type(v)=='number'or type(v)=='boolean'or type(v)=='string'then out[k]=v end end
 return out
end
local function call(o,n,...)
 if not o then return nil end
 local ok,t=pcall(function()return o:get_type_definition()end)
 if not ok or not t then return nil end
 local key=t:get_full_name()..':'..n
 if methods[key]==nil then methods[key]=t:get_method(n)~=nil end
 if not methods[key]then return nil end
 local success,v=pcall(function(...)return o:call(n,...)end,...)
 if success then return v end
end
local function field(o,n)
 if not o then return nil end
 local ok,v=pcall(function()
  local t=o:get_type_definition();local key=t:get_full_name()..':'..n
  if fields[key]==nil then fields[key]=t:get_field(n)~=nil end
  if fields[key]then return o:get_field(n)end
 end)
 if ok then return v end
end
local function address(o)
 if not o then return nil end
 local ok,v=pcall(function()return tostring(o:get_address())end)
 if ok then return v end
end
local function text(v)
 if v==nil then return nil end
 return tostring(v):sub(1,600)
end
local function singleton(n)
 local ok,v=pcall(sdk.get_managed_singleton,n)
 if ok then return v end
end
local function list(o,max,array)
 local out={};if not o then return out end
 local count=array and call(o,'get_Length')or call(o,'get_Count')
 if array then local ok,v=pcall(function()return o:get_size()end);if ok then count=v end end
 if type(count)~='number'or count<0 or count>4096 then return out end
 for i=0,math.min(count,max)-1 do
  local v
  if array then local ok,x=pcall(function()return o:get_element(i)end);if ok then v=x end
  else v=call(o,'get_Item',i)end
  out[#out+1]=v or false
 end
 return out
end
local function charge(o)
 if not o then return nil end
 return {address=address(o),enabled=field(o,'Enable'),autoCharge=call(o,'get_AutoCharge'),
  state=call(o,'get_state'),level=call(o,'get_currentLevel'),limit=field(o,'LimitLevel'),
  timer=call(o,'get_timer'),key=call(o,'get_padInputFlag'),input=address(call(o,'get_padInput'))}
end
local chargeNames={
 [0]={'BlueRoseCharge','GauntletCharge','ReinforcementCharge','RedQueenCharge'},
 [1]={'<chargeWeaponS00>k__BackingField','<chargeWeaponS01>k__BackingField','<chargeWeaponL00>k__BackingField','<chargeWeaponL01>k__BackingField','<chargeSheath>k__BackingField'},
 [4]={'<JudgeMentCutCharge>k__BackingField','<BeowulfCharge>k__BackingField','<RoundTripCharge>k__BackingField'}}
local function actor(p,manual)
 local id=call(p,'get_playerID');local mesh=call(p,'get_bodyMeshList');local bound=0
 for _,v in ipairs(list(mesh,32,true))do if v then bound=bound+1 end end
 local med=call(p,'get_cachedActivateMediator');local world=call(p,'get_cachedCharacterController')
 local hit=call(p,'get_cachedHitController');local input=call(p,'get_padInput')
 local go=call(p,'get_GameObject');local tr=call(go,'get_Transform');local pos=call(tr,'get_Position')
 local row={id=id,type=typeName(p),address=address(p),manual=p==manual,enabled=call(p,'get_Enable'),componentEnabled=call(p,'get_Enabled'),
  draw=call(med,'get_drawSelf'),update=call(med,'get_updateSelf'),bodyMeshes=bound,
  worldCollision=call(world,'get_Enabled'),useAttack=call(hit,'get_isUseAttack'),
  hp=call(p,'get_hp'),maxHp=call(p,'get_maxHp'),dt=call(p,'get_devilTriggerGauge'),
  maxDt=call(p,'get_maxDevilTriggerGauge'),sin=field(p,'<theDTGauge>k__BackingField'),
  devil=call(p,'get_isDevilTrigger'),sinActive=call(p,'get_isTheDevilTrigger'),
  concentration=call(p,'get_concentrationGauge'),automatic=call(p,'get_isEasyAutomatic'),
  running=call(p,'get_isEventRun'),scriptedMove=call(p,'get_isEventMove'),
  action=text(call(p,'get_nowActionNameFull')),mediation=call(p,'get_MediationType'),
  masterLockRestricted=call(p,'get_isMasterLockOnRestricted'),input=address(input)}
 if pos then pcall(function()row.position={x=pos.x,y=pos.y,z=pos.z}end)end
 -- Only game action masks, never keyboard text or system-wide key history.
 row.inputOn=call(input,'get_buttonOnFlags')
 row.inputTrigger=call(input,'get_buttonTriggerFlags');row.inputRelease=call(input,'get_buttonReleaseFlags')
 row.weaponS=call(p,'get_currentWeaponS');row.weaponL=call(p,'get_currentWeaponL')
 row.weaponSlotsS=list(call(p,'get_slotWeaponS'),16,false);row.weaponSlotsL=list(call(p,'get_slotWeaponL'),16,false)
 if id==0 then
  row.armCount=call(p,'get_gauntletNum');row.pendingArms=call(p,'get_gauntletStackCount')
  row.arms={};local arms=call(p,'get_gauntletList')
  if arms and type(row.armCount)=='number'and row.armCount>=0 and row.armCount<=8 then
   pcall(function()for i=0,math.min(row.armCount,arms:get_size())-1 do row.arms[#row.arms+1]=arms:read_dword(0x20+i*4)end end)
  end
 end
 row.charges={}
 for _,name in ipairs(chargeNames[id]or{})do row.charges[name]=charge(field(p,name))end
 return row
end
local function capture(now,kind)
 local S=_G.dmc5_live_switch or {};local B=_G.dmc5_switch_loader or {}
 local R=_G.dmc5_switch_runtime or {};local P=_G.dmc5_switch_palace or {}
 local H=_G.dmc5_party_hud or {};local gm=singleton('app.GameManager')
 local manager=B.manager or R.manager or singleton('app.PlayerManager')
 local manual=call(manager,'get_manualPlayer');local bp=singleton('app.BloodyPalaceManager')
 local setting=call(singleton('app.MissionSettingManager'),'get_Setting')
 local row={schema=1,utc=now,session=session,kind=kind,recorder=D.version,build=text(S.build),
  mission=call(gm,'get_missionNo'),mode=call(gm,'get_gameMode'),paused=call(gm,'get_isPause'),recorderError=D.error,
  menuPaused=call(gm,'get_isPauseMenu'),nativePlayer=call(setting,'get_ControllPlayerID'),
  manual=call(manual,'get_playerID'),modCurrent=S.current,modStage=text(S.stage),error=text(S.error),
  loader={stage=text(B.stage),error=text(B.error),generation=B.generation,available=copy(B.available),
   task=B.task and {id=B.task.id,phase=B.task.phase},playable=B.playable},
  control={selected=R.controlSelection and R.controlSelection.id,native=R.nativeControl and R.nativeControl.id,
   error=text(R.controlIdentityError),retry=R.storyRetrySerial},
  palace={floor=field(bp,'CurrentStageNo'),supply=field(bp,'IsGauntletStage'),
   restores=P.restores,error=text(P.error)},hud={active=H.active,error=text(H.error),stage=text(H.stage)},players={}}
 local count=call(manager,'getPlayerNum')
 if type(count)=='number'and count>=0 and count<=64 then
  for i=0,math.min(count,16)-1 do
   local p=call(manager,'getPlayer',i)
   if p then
    local id=call(p,'get_playerID');local ready=false
    if B.manager==manager and B.ready and call(manager,'getPlayerByID',id)==p then local ok,v=pcall(B.ready,manager,id);ready=ok and v==true end
    if ready then
     local ok,v=pcall(actor,p,manual);if ok then v.ready=true;row.players[#row.players+1]=v else row.actorError=text(v)end
    else row.players[#row.players+1]={id=id,type=typeName(p),address=address(p),manual=p==manual,ready=false}end
   end
  end
 end
 local em=singleton('app.EnemyManager');row.enemies={}
 for _,e in ipairs(list(field(em,'EnemyList'),8,false))do
  if e then row.enemies[#row.enemies+1]={type=typeName(e),address=address(e),hp=call(e,'get_hp'),
   enabled=call(e,'get_Enable'),mediation=call(e,'get_MediationType'),
   masterLockRestricted=call(e,'get_isMasterLockOnRestricted'),replayLockRestricted=call(e,'get_isReplayLockOnRestricted')}end
 end
 return row
end
local function flush()
 if #D.buffer==0 then return end
 local minute=math.floor(D.buffer[1].utc/60);local path=folder..string.format('slot-%02d.jsonl',minute%32)
 -- One file per minute, fixed 32 slots. Exporter filters exact last 30 min.
 local mode=D.minute==minute and 'a'or'w'
 if mode=='w'then
  local previous=io.open(path,'r')
  if previous then
   local first=previous:read(65536);previous:close()
   if first then
    local ok,row=pcall(json.load_string,first:match('[^\n]+')or'')
    if ok and row and type(row.utc)=='number'and math.floor(row.utc/60)==minute then mode='a'end
   end
  end
 end
 local f,why=io.open(path,mode);assert(f,why)
 local ok,err=pcall(function()
  for _,row in ipairs(D.buffer)do f:write(json.dump_string(row,-1),'\n')end
  f:flush()
 end)
 f:close();assert(ok,err)
 D.minute=minute;D.buffer={};D.writes=D.writes+1
end
re.on_frame(function()
 frames=frames+1
 local now=os.time()
 local S=_G.dmc5_live_switch or {};local B=_G.dmc5_switch_loader or {}
 local signature=tostring(S.current)..'|'..tostring(S.stage)..'|'..tostring(S.error)..'|'..tostring(B.generation)
 if signature~=lastSignature then
  if #changes<20 then changes[#changes+1]={utc=now,frame=frames,current=S.current,stage=text(S.stage),error=text(S.error),generation=B.generation}end
  lastSignature=signature
 end
 local down=reframework:is_key_down(119)
 local mark=down and not keyWasDown and now-lastMark>=3;keyWasDown=down
 if now==last and not mark then return end
 if mark then lastMark=now end
 local ok,why=pcall(function()
  if #D.buffer>0 and math.floor(D.buffer[1].utc/60)~=math.floor(now/60)then flush()end
  local row=capture(now,mark and 'F8' or 'sample')
  row.changes=changes;changes={}
  row.frameCallbacks=frames;row.wallSeconds=last and now-last or 0;frames=0
  D.buffer[#D.buffer+1]=row;D.samples=D.samples+1;last=now
  if mark or now-lastFlush>=5 or #D.buffer>=6 then flush();lastFlush=now end
 end)
 if not ok then
  D.error=text(why);D.buffer={};last=now
  if not D.reported and log and log.error then log.error('DMC5 support recorder: '..D.error);D.reported=true end
 end
end)
