
hooks={};mode=3;serial=0;fps=60;paused=false;storages={}
thread={get_hook_storage=function()return storages[#storages]end}
sdk={hook=function(method,pre,post)hooks[method]=hooks[method]or {};table.insert(hooks[method],{pre,post})end,to_managed_object=function(v)return v end,
 find_type_definition=function(name)return {get_method=function(_,method)return name..'.'..method end}end}
function list(values)
 local out={values={}}
 for i,v in ipairs(values)do out.values[i]=v end
 function out:call(name,a)
  if name=='get_Count'then return #self.values
  elseif name=='get_Item'then return self.values[a+1]
  elseif name=='Clear'then self.values={}
  elseif name=='Add'then self.values[#self.values+1]=a else error(name)end
 end
 return out
end
function arms(values)
 local out={values={}}
 for i=1,8 do out.values[i]=values[i]or 100 end
 function out:get_size()return 8 end
 function out:read_dword(offset)return self.values[(offset-0x20)//4+1]end
 function out:write_dword(offset,value)self.values[(offset-0x20)//4+1]=value end
 return out
end
function actor(id)
 serial=serial+1
 local p={id=id,address=serial,hp=11200+id,maxHp=20000,dt=2100+id*100,maxDt=10000,sin=3300+id*200,
  slotsS=list({2,4,7}),slotsL=list({11,13}),weaponS=4,weaponSID=0,weaponL=13,weaponLID=0,
  armList=arms({3,8,11}),count=3,stack=0,input={},hpWrites=0,dtWrites=0,weapons=0,rebuilds=0,refills=0}
 local data={MaxHP=20,MaxDT=10,IsSuperMode=false,ChargeShotLevel=3,FaustHat={set_field=function()end}}
 function data:get_address()return p.address+1000 end
 function data:get_field(name)return self[name]end
 function data:set_field(name,value)self[name]=value end
 function data:call(name)assert(name=='allOpen');self.MaxHP=20;self.MaxDT=10 end
 p.data=data
 p.charge={input=p.input,timer=0,resets=0,get_field=function(_,name)assert(name=='LimitLevel');return 5 end,call=function(self,name,arg)
  if name=='get_padInput'then return self.input
  elseif name=='set_padInput'then self.input=arg
  elseif name=='forceEnd'then self.resets=self.resets+1;self.timer=0
  else assert(name=='reset')end
 end}
 function p:get_address()return self.address end
 function p:get_field(name)
  if name=='BlueRoseCharge'then return self.charge
  elseif name=='<theDTGauge>k__BackingField'then return self.sin else return nil end
 end
 function p:set_field(name,value)assert(name=='<theDTGauge>k__BackingField');self.sin=value end
 function p:call(name,a,b)
  if name=='get_playerID'then return self.id
  elseif name=='get_Enable'then return true
  elseif name=='get_cachedHitController'then return {get_field=function()return {call=function()return 1/fps end}end}
  elseif name=='get_playerData'then return self.data
  elseif name=='get_hp'then return self.hp
  elseif name=='get_maxHp'then return self.maxHp
  elseif name=='get_devilTriggerGauge'then return self.dt
  elseif name=='get_maxDevilTriggerGauge'then return self.maxDt
  elseif name=='set_hp'then self.hp=a;self.hpWrites=self.hpWrites+1
  elseif name=='set_maxHp'then self.maxHp=a
  elseif name=='set_devilTriggerGauge'then self.dt=a;self.dtWrites=self.dtWrites+1
  elseif name=='set_maxDevilTriggerGauge'then self.maxDt=a
  elseif (name=='get_isEventMove'or name=='get_isEventRun')then return false
  elseif name=='get_isTheDevilTrigger'then return self.sinActive or false
  elseif name=='get_prevSDTWeaponS'then return self.prevS or self.weaponS
  elseif name=='get_prevSDTWeaponL'then return self.prevL or self.weaponL
  elseif name=='set_prevSDTWeaponS'then self.prevS=a
  elseif name=='set_prevSDTWeaponL'then self.prevL=a
  elseif name=='get_slotWeaponS'then return self.slotsS
  elseif name=='get_slotWeaponL'then return self.slotsL
  elseif name=='get_currentWeaponS'then return self.weaponS
  elseif name=='get_currentWeaponL'then return self.weaponL
  elseif name=='get_weaponS_ID'then return self.weaponSID
  elseif name=='get_weaponL_ID'then return self.weaponLID
  elseif name=='changeWeaponS'then
   self.weaponS=a;self.weaponSID=b;self.weapons=self.weapons+1;self.hp=9999;self.dt=0;self.sin=0
   self.slotsS.values={2,4,5};self.deferredWeapon=true
  elseif name=='changeWeaponL'then
   self.weaponL=a;self.weaponLID=b;self.weapons=self.weapons+1;self.hp=9999;self.dt=0;self.sin=0
   self.slotsL.values={11,5};self.deferredWeapon=true
  elseif name=='get_gauntletNum'then return self.count
  elseif name=='get_gauntletStackCount'then return self.stack
  elseif name=='get_gauntletList'then return self.armList
  elseif name=='rebuildGauntletList'then
   self.count=0;for i=1,8 do if a.values[i]~=100 then self.count=self.count+1 end end
   self.rebuilds=self.rebuilds+1;self.hp=100;self.dt=0
  elseif name=='get_isGauntletPickupEnabled'then return true
  elseif name=='pickupGauntlet'then self.count=1;self.armList.values[1]=a;self.refills=self.refills+1
  elseif name=='get_padInput'then return self.input
  elseif name=='resetGunShotReserve'or name=='finishBRChargeEffect'then
  else error('unsupported '..name)end
 end
 return p
end
bp={CurrentStageNo=1,get_field=function(self,name)return self[name]end,set_field=function(self,name,value)assert(name=='IsGauntletStage'or name=='CurrentGauntletStageInfo');self[name]=value end}
gm={call=function(_,name)if name=='get_gameMode'then return mode elseif name=='findManualPlayerID'then return 0 end;assert(name=='get_isPause'or name=='get_isPauseMenu'or name=='get_isShopPause');return paused end}
players={[0]=actor(0),[1]=actor(1),[4]=actor(4)};active=players[0]
manager={call=function(_,name,id)
 if name=='getPlayerByID'then return players[id]
 elseif name=='get_manualPlayer'then return active else error(name)end
end}
dmc5_switch_loader={manager=manager,known={},playable=true,ready=function(m,id)
 return m==manager and dmc5_switch_loader.known[id]==players[id]
end}
for id,p in pairs(players)do dmc5_switch_loader.known[id]=p end
sdk.get_managed_singleton=function(name)
 if name=='app.GameManager'then return gm
 elseif name=='app.BloodyPalaceManager'then return bp
 elseif name=='app.PlayerManager'then error('scene manager is not a singleton')end
end

function invoke(method,obj,native)
 local hs=hooks[method]or {};storages[#storages+1]={}
 for _,h in ipairs(hs)do if h[1]then h[1]({[2]=obj})end end
 local result=native and native()or 'native return'
 for _,h in ipairs(hs)do if h[2]then assert(h[2](result)==result,'native result changed')end end
 storages[#storages]=nil
 return result
end
function phase(name,native)return invoke('app.BloodyPalaceManager.'..name,bp,native)end
requests=0;queued=nil
function choose(id,source)
 local previous=active.id;active=players[id];dmc5_switch_runtime.invalidate()
 if source=='palace'then active.dt=0;active.sin=0 end
 Palace.selected(id,manager,previous,source or 'user')
end
dmc5_live_switch={stage='ready',request=function(id,source)
 if queued then return false end
 queued={id=id,source=source or 'user'};requests=requests+1;return true
end}
function frame()
 if queued then local q=queued;queued=nil;choose(q.id,q.source)end
 invoke('app.PlayerManager.doUpdate',manager,function()
  for _,p in pairs(players)do
   if p.deferredWeapon then
    p.slotsS.values={2,4,5};p.slotsL.values={11,5};p.dt=10000;p.sin=0;p.deferredWeapon=nil
   end
  end
 end)
end
function frames(n)for i=1,n do frame()end end
function allReady()
 if queued then return false end
 local s=Palace.run and Palace.run.stage
 if not s then return false end
 return next(s.pending)==nil and next(s.jobs)==nil and s.goal==nil
end
function settle()
 for i=1,500 do if allReady()then return end;frame()end
 error('Palace restore did not settle')
end
function reload(kind,floor,missing)
 bp.CurrentStageNo=floor;bp.IsGauntletStage=kind=='supply'
 phase(kind=='supply'and 'updateGauntletStageInit'or 'updateBattleInit',function()
  players={[0]=actor(0),[1]=actor(1),[4]=actor(4)}
  for _,p in pairs(players)do p.hp=20000;p.dt=10000;p.sin=0;p.count=0;p.armList=arms({});p.weaponS=2;p.weaponSID=0 end
  if missing then players[missing]=nil end
  active=players[4]or players[0];dmc5_switch_loader.known={}
  for id,p in pairs(players)do dmc5_switch_loader.known[id]=p end
  dmc5_switch_runtime.invalidate()
 end)
end
